"""
Gemini Classification Service for Legal Document Severity Classification.

This module implements the GeminiClassifier class that uses Google's Gemini API
for document severity classification with structured prompts and JSON response parsing.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import re

import google.generativeai as genai
from google.api_core import exceptions as gcp_exceptions
from google.api_core import retry

from config import get_gemini_config
from legal_models import SeverityLevel, ClassificationResult, RoutingDecision
from retry_mechanisms import (
    RetryMechanism, CircuitBreaker, gemini_retry_config, gemini_circuit_breaker,
    fallback_strategy
)
from exceptions import (
    GeminiAPIException, GeminiRateLimitException, GeminiServiceUnavailableException,
    GeminiResponseParsingException
)
from fallback_classifier import fallback_classifier
from error_logger import error_logger

logger = logging.getLogger(__name__)


class ClassificationResponse:
    """Structured response from Gemini classification."""
    
    def __init__(
        self,
        label: SeverityLevel,
        confidence: float,
        rationale: str,
        routing_decision: RoutingDecision,
        raw_response: str
    ):
        self.label = label
        self.confidence = confidence
        self.rationale = rationale
        self.routing_decision = routing_decision
        self.raw_response = raw_response


class GeminiClassifier:
    """
    Gemini-based document severity classifier with structured prompts and JSON parsing.
    
    Handles classification requests with retry logic, confidence scoring,
    and routing decisions based on classification confidence.
    """
    
    def __init__(
        self,
        model_name: str = "gemini-1.5-pro",
        max_retries: int = 3,
        base_delay: float = 1.0,
        confidence_thresholds: Optional[Dict[str, float]] = None
    ):
        """
        Initialize the Gemini classifier.
        
        Args:
            model_name: Gemini model to use for classification
            max_retries: Maximum number of retry attempts (deprecated - using retry_mechanisms)
            base_delay: Base delay for exponential backoff (deprecated - using retry_mechanisms)
            confidence_thresholds: Thresholds for routing decisions
        """
        self.model_name = model_name
        self.max_retries = max_retries  # Keep for backward compatibility
        self.base_delay = base_delay    # Keep for backward compatibility
        
        # Default confidence thresholds for routing decisions
        self.confidence_thresholds = confidence_thresholds or {
            'auto_accept': 0.85,  # Auto-accept if confidence >= 85%
            'human_review': 0.60,  # Human review if confidence >= 60%
            # Below 60% goes to human triage
        }
        
        # Initialize Gemini client
        try:
            config = get_gemini_config()
            genai.configure(api_key=config["api_key"])
            
            # Initialize the model
            self.model = genai.GenerativeModel(self.model_name)
            
            # Register fallback handler
            fallback_strategy.register_fallback("gemini_classification", self._fallback_classification)
            
            logger.info(f"Initialized GeminiClassifier with model: {self.model_name}")
            
        except Exception as e:
            error_logger.log_exception(
                e,
                context={"operation": "gemini_classifier_init", "model_name": model_name}
            )
            raise GeminiAPIException(f"Failed to initialize Gemini classifier: {str(e)}", cause=e)
    
    async def _fallback_classification(
        self,
        document_text: str,
        context_information: str,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> ClassificationResponse:
        """
        Fallback classification method when Gemini API is unavailable.
        
        Args:
            document_text: Text content of the document
            context_information: Context information (ignored in fallback)
            document_metadata: Document metadata
            
        Returns:
            ClassificationResponse using fallback classifier
        """
        document_id = document_metadata.get('document_id', 'unknown') if document_metadata else 'unknown'
        
        # Use fallback classifier
        fallback_result = fallback_classifier.classify_document(
            document_text, document_id, document_metadata
        )
        
        # Convert to ClassificationResponse
        routing_decision = self._determine_routing_decision(fallback_result.confidence)
        
        return ClassificationResponse(
            label=fallback_result.label,
            confidence=fallback_result.confidence,
            rationale=f"FALLBACK: {fallback_result.rationale}",
            routing_decision=routing_decision,
            raw_response="Fallback classification - Gemini API unavailable"
        )
    
    def _create_classification_prompt(
        self,
        document_text: str,
        context_information: str,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a structured prompt for document classification.
        
        Args:
            document_text: Text content of the document to classify
            context_information: Formatted context from similar documents
            document_metadata: Optional metadata about the document
            
        Returns:
            Structured prompt string for Gemini
        """
        metadata_info = ""
        if document_metadata:
            metadata_info = f"""
DOCUMENT METADATA:
- Filename: {document_metadata.get('filename', 'unknown')}
- Upload Date: {document_metadata.get('upload_date', 'unknown')}
- File Size: {document_metadata.get('file_size', 'unknown')} bytes
"""
        
        prompt = f"""You are an expert legal document classifier specializing in severity assessment. Your task is to classify the severity level of legal documents based on their content and similar reference examples.

CLASSIFICATION LEVELS:
- CRITICAL: Immediate legal action required, severe violations, regulatory breaches with significant penalties
- HIGH: Important legal matters requiring prompt attention, compliance issues with moderate penalties
- MEDIUM: Standard legal matters requiring review, minor compliance issues, routine legal processes
- LOW: Administrative matters, informational documents, low-priority legal items

{metadata_info}

DOCUMENT TO CLASSIFY:
{document_text}

{context_information}

INSTRUCTIONS:
1. Analyze the document content carefully
2. Compare it with the reference examples provided in the context
3. Consider the severity patterns shown in similar documents
4. Classify the document into one of the four severity levels
5. Provide a confidence score between 0.0 and 1.0
6. Explain your reasoning clearly

RESPONSE FORMAT:
You must respond with a valid JSON object in exactly this format:
{{
    "label": "CRITICAL|HIGH|MEDIUM|LOW",
    "confidence": 0.XX,
    "rationale": "Detailed explanation of your classification decision, referencing specific content and context examples"
}}

Ensure your response is valid JSON and includes all required fields."""
        
        return prompt
    
    def _parse_classification_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Gemini's response and extract classification information.
        
        Args:
            response_text: Raw response text from Gemini
            
        Returns:
            Dictionary with parsed classification data
            
        Raises:
            ValueError: If response cannot be parsed or is invalid
        """
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON object found in response")
            
            json_str = json_match.group(0)
            parsed_response = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['label', 'confidence', 'rationale']
            for field in required_fields:
                if field not in parsed_response:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate label
            label_str = parsed_response['label'].upper()
            if label_str not in [level.value for level in SeverityLevel]:
                raise ValueError(f"Invalid severity label: {label_str}")
            
            # Validate confidence
            confidence = float(parsed_response['confidence'])
            if not 0.0 <= confidence <= 1.0:
                raise ValueError(f"Confidence must be between 0.0 and 1.0, got: {confidence}")
            
            # Validate rationale
            rationale = parsed_response['rationale'].strip()
            if not rationale or len(rationale) < 10:
                raise ValueError("Rationale must be at least 10 characters long")
            
            return {
                'label': SeverityLevel(label_str),
                'confidence': confidence,
                'rationale': rationale
            }
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in response: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing response: {e}")
    
    def _determine_routing_decision(self, confidence: float) -> RoutingDecision:
        """
        Determine routing decision based on classification confidence.
        
        Args:
            confidence: Classification confidence score
            
        Returns:
            Routing decision enum value
        """
        if confidence >= self.confidence_thresholds['auto_accept']:
            return RoutingDecision.AUTO_ACCEPT
        elif confidence >= self.confidence_thresholds['human_review']:
            return RoutingDecision.HUMAN_REVIEW
        else:
            return RoutingDecision.HUMAN_TRIAGE
    
    async def classify_document(
        self,
        document_text: str,
        context_information: str,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> ClassificationResponse:
        """
        Classify a document using Gemini with retry logic and error handling.
        
        Args:
            document_text: Text content of the document to classify
            context_information: Formatted context from similar documents
            document_metadata: Optional metadata about the document
            
        Returns:
            ClassificationResponse with classification results
            
        Raises:
            Exception: If classification fails after all retries
        """
        if not document_text or not document_text.strip():
            raise ValueError("Document text cannot be empty")
        
        document_id = document_metadata.get('document_id', 'unknown') if document_metadata else 'unknown'
        
        logger.info(f"Starting document classification (text length: {len(document_text)} chars)")
        
        # Use circuit breaker and retry mechanism
        try:
            return await self._classify_with_retry_and_circuit_breaker(
                document_text, context_information, document_metadata
            )
        except Exception as e:
            # If all retries and circuit breaker fail, use fallback
            error_logger.log_error(
                f"Gemini classification failed, using fallback: {str(e)}",
                "GEMINI_CLASSIFICATION_FALLBACK",
                context={
                    "document_id": document_id,
                    "exception_type": type(e).__name__
                }
            )
            
            # Use fallback classifier
            fallback_result = fallback_classifier.classify_document(
                document_text, document_id, document_metadata
            )
            
            # Convert fallback result to ClassificationResponse
            routing_decision = self._determine_routing_decision(fallback_result.confidence)
            
            return ClassificationResponse(
                label=fallback_result.label,
                confidence=fallback_result.confidence,
                rationale=f"FALLBACK: {fallback_result.rationale}",
                routing_decision=routing_decision,
                raw_response=f"Fallback classification used due to Gemini API failure: {str(e)}"
            )
    
    async def _classify_with_retry_and_circuit_breaker(
        self,
        document_text: str,
        context_information: str,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> ClassificationResponse:
        """
        Internal method to classify with retry and circuit breaker protection.
        """
        prompt = self._create_classification_prompt(
            document_text, context_information, document_metadata
        )
        
        # Create retry mechanism
        retry_mechanism = RetryMechanism(gemini_retry_config)
        
        # Execute with circuit breaker and retry
        async def _gemini_api_call():
            try:
                # Generate response using Gemini
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,  # Low temperature for consistent results
                        top_p=0.8,
                        top_k=40,
                        max_output_tokens=1000,
                    )
                )
                
                if not response.text:
                    raise GeminiAPIException("Empty response from Gemini API")
                
                return response.text
                
            except gcp_exceptions.ResourceExhausted as e:
                # Convert to our custom exception with retry-after info
                retry_after = getattr(e, 'retry_after', None)
                raise GeminiRateLimitException(retry_after=retry_after, cause=e)
                
            except gcp_exceptions.ServiceUnavailable as e:
                raise GeminiServiceUnavailableException(cause=e)
                
            except gcp_exceptions.GoogleAPIError as e:
                raise GeminiAPIException(f"Gemini API error: {str(e)}", cause=e)
                
            except Exception as e:
                raise GeminiAPIException(f"Unexpected error calling Gemini API: {str(e)}", cause=e)
        
        # Execute with circuit breaker protection
        response_text = await gemini_circuit_breaker.execute(_gemini_api_call)
        
        # Execute response parsing with retry
        async def _parse_response():
            try:
                return self._parse_classification_response(response_text)
            except Exception as e:
                raise GeminiResponseParsingException(
                    response_content=response_text,
                    expected_format="JSON with label, confidence, rationale",
                    cause=e
                )
        
        parsed_data = await retry_mechanism.execute_with_retry(
            _parse_response,
            context={"operation": "response_parsing"}
        )
        
        # Determine routing decision
        routing_decision = self._determine_routing_decision(parsed_data['confidence'])
        
        classification_response = ClassificationResponse(
            label=parsed_data['label'],
            confidence=parsed_data['confidence'],
            rationale=parsed_data['rationale'],
            routing_decision=routing_decision,
            raw_response=response_text
        )
        
        logger.info(f"Classification completed: {parsed_data['label'].value} "
                   f"(confidence: {parsed_data['confidence']:.3f}, "
                   f"routing: {routing_decision.value})")
        
        return classification_response
    
    async def batch_classify_documents(
        self,
        documents_data: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None
    ) -> List[ClassificationResponse]:
        """
        Classify multiple documents in batch with progress tracking.
        
        Args:
            documents_data: List of dictionaries with document data
                Each dict should contain: 'text', 'context', 'metadata' (optional)
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of ClassificationResponse objects
        """
        if not documents_data:
            return []
        
        results = []
        total_docs = len(documents_data)
        
        logger.info(f"Starting batch classification for {total_docs} documents")
        
        for i, doc_data in enumerate(documents_data):
            try:
                result = await self.classify_document(
                    document_text=doc_data['text'],
                    context_information=doc_data['context'],
                    document_metadata=doc_data.get('metadata')
                )
                results.append(result)
                
                # Call progress callback if provided
                if progress_callback:
                    progress = (i + 1) / total_docs
                    progress_callback(progress, i + 1, total_docs)
                
                # Small delay between requests to be respectful to the API
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Failed to classify document {i}: {e}")
                # Create a failed classification response
                failed_response = ClassificationResponse(
                    label=SeverityLevel.MEDIUM,  # Default fallback
                    confidence=0.0,
                    rationale=f"Classification failed: {str(e)}",
                    routing_decision=RoutingDecision.HUMAN_TRIAGE,
                    raw_response=""
                )
                results.append(failed_response)
        
        logger.info(f"Completed batch classification for {total_docs} documents")
        return results
    
    async def restructure_document_text(self, raw_text: str) -> str:
        """
        Convert raw PDF text into clean, readable markdown using Gemini.
        
        Args:
            raw_text: Raw text extracted from PDF
            
        Returns:
            Clean markdown-formatted text
        """
        if not raw_text or not raw_text.strip():
            raise ValueError("Document text cannot be empty")
        
        prompt = f"""You are an expert document formatter. Your task is to convert raw, unstructured text from a PDF document into clean, well-formatted markdown.

Instructions:
1. Structure the text with appropriate headings and sections
2. Clean up formatting issues, line breaks, and spacing
3. Preserve all original content - do not summarize or omit information
4. Use markdown formatting (headers, lists, emphasis) to improve readability
5. Fix obvious OCR errors or formatting artifacts
6. Maintain the logical flow and organization of the document

Raw Document Text:
{raw_text}

Please return the restructured text in clean markdown format:"""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    top_p=0.8,
                    top_k=40,
                    max_output_tokens=4000,
                )
            )
            
            if not response.text:
                raise GeminiAPIException("Empty response from Gemini API")
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Failed to restructure document text: {e}")
            # Fallback: return original text with basic markdown formatting
            return f"# Document\n\n{raw_text}"
    
    async def analyze_document_clauses(self, structured_text: str) -> List[Dict[str, Any]]:
        """
        Analyze document for predatory clauses using Gemini tool calling.
        
        Args:
            structured_text: Clean, structured markdown text
            
        Returns:
            List of identified problematic clauses
        """
        if not structured_text or not structured_text.strip():
            return []
        
        # Define the tool for clause identification
        clause_analysis_tool = {
            "function_declarations": [{
                "name": "identify_problematic_clause",
                "description": "Identify and analyze a predatory or unfair clause",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "clause_text": {
                            "type": "string", 
                            "description": "Exact clause text from document"
                        },
                        "start_position": {
                            "type": "integer", 
                            "description": "Character position in structured text"
                        },
                        "end_position": {
                            "type": "integer", 
                            "description": "Character position in structured text"
                        },
                        "severity": {
                            "type": "string", 
                            "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                            "description": "Severity level of the problematic clause"
                        },
                        "category": {
                            "type": "string", 
                            "description": "Type: unfair_fees, hidden_terms, auto_renewal, etc."
                        },
                        "explanation": {
                            "type": "string", 
                            "description": "Detailed explanation of why problematic"
                        },
                        "suggested_action": {
                            "type": "string", 
                            "description": "Recommended action for user"
                        }
                    },
                    "required": [
                        "clause_text", "start_position", "end_position", 
                        "severity", "category", "explanation", "suggested_action"
                    ]
                }
            }]
        }
        
        prompt = f"""Analyze this legal document for predatory or unfair clauses. Use the identify_problematic_clause tool for each problematic clause you find.

Focus on: unfair fees, hidden terms, automatic renewals, unilateral changes, excessive penalties, arbitration clauses, liability issues, data collection overreach, termination clauses, dispute resolution limitations.

For each problematic clause:
1. Find the exact text and character positions in the document
2. Classify severity: CRITICAL (immediate danger), HIGH (significant risk), MEDIUM (moderate concern), LOW (minor issue)
3. Categorize the type of problem
4. Explain why it's problematic
5. Suggest specific actions

Document to analyze:
{structured_text}"""

        try:
            # Create model with tools
            model_with_tools = genai.GenerativeModel(
                model_name=self.model_name,
                tools=[clause_analysis_tool]
            )
            
            response = await asyncio.to_thread(
                model_with_tools.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    top_p=0.8,
                    top_k=40,
                    max_output_tokens=2000,
                )
            )
            
            clauses = []
            
            # Process function calls from the response
            if hasattr(response, 'candidates') and response.candidates:
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'function_call'):
                                func_call = part.function_call
                                if func_call.name == "identify_problematic_clause":
                                    # Extract arguments from function call
                                    args = func_call.args
                                    
                                    # Validate positions are within bounds
                                    start_pos = int(args.get('start_position', 0))
                                    end_pos = int(args.get('end_position', len(structured_text)))
                                    
                                    if start_pos < 0:
                                        start_pos = 0
                                    if end_pos > len(structured_text):
                                        end_pos = len(structured_text)
                                    if start_pos >= end_pos:
                                        end_pos = start_pos + len(args.get('clause_text', ''))
                                    
                                    clause_data = {
                                        "clause_text": str(args.get('clause_text', '')),
                                        "start_position": start_pos,
                                        "end_position": end_pos,
                                        "severity": str(args.get('severity', 'MEDIUM')),
                                        "category": str(args.get('category', '')),
                                        "explanation": str(args.get('explanation', '')),
                                        "suggested_action": str(args.get('suggested_action', ''))
                                    }
                                    clauses.append(clause_data)
            
            logger.info(f"Identified {len(clauses)} problematic clauses")
            return clauses
            
        except Exception as e:
            logger.error(f"Failed to analyze document clauses: {e}")
            return []
    
    def validate_classification_result(self, result: ClassificationResponse) -> bool:
        """
        Validate a classification result for consistency and quality.
        
        Args:
            result: Classification result to validate
            
        Returns:
            True if result is valid, False otherwise
        """
        try:
            # Check basic field validity
            if not isinstance(result.label, SeverityLevel):
                return False
            
            if not 0.0 <= result.confidence <= 1.0:
                return False
            
            if not result.rationale or len(result.rationale.strip()) < 10:
                return False
            
            if not isinstance(result.routing_decision, RoutingDecision):
                return False
            
            # Check consistency between confidence and routing decision
            expected_routing = self._determine_routing_decision(result.confidence)
            if result.routing_decision != expected_routing:
                logger.warning(f"Routing decision inconsistency: expected {expected_routing}, "
                             f"got {result.routing_decision}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating classification result: {e}")
            return False
    
    def get_classification_statistics(self, results: List[ClassificationResponse]) -> Dict[str, Any]:
        """
        Get statistics about a batch of classification results.
        
        Args:
            results: List of classification results
            
        Returns:
            Dictionary with classification statistics
        """
        if not results:
            return {
                'total_classifications': 0,
                'avg_confidence': 0.0,
                'label_distribution': {},
                'routing_distribution': {},
                'failed_classifications': 0
            }
        
        # Calculate statistics
        confidences = [r.confidence for r in results]
        avg_confidence = sum(confidences) / len(confidences)
        
        # Count label distribution
        label_counts = {}
        for result in results:
            label = result.label.value
            label_counts[label] = label_counts.get(label, 0) + 1
        
        # Count routing distribution
        routing_counts = {}
        for result in results:
            routing = result.routing_decision.value
            routing_counts[routing] = routing_counts.get(routing, 0) + 1
        
        # Count failed classifications (confidence = 0.0)
        failed_count = sum(1 for r in results if r.confidence == 0.0)
        
        return {
            'total_classifications': len(results),
            'avg_confidence': avg_confidence,
            'max_confidence': max(confidences),
            'min_confidence': min(confidences),
            'label_distribution': label_counts,
            'routing_distribution': routing_counts,
            'failed_classifications': failed_count,
            'success_rate': (len(results) - failed_count) / len(results)
        }


# Export the main classes
__all__ = ['GeminiClassifier', 'ClassificationResponse']