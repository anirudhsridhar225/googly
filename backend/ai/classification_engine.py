"""
Classification Engine for Legal Document Severity Classification.

This module implements the main classification orchestration system that coordinates
context retrieval, Gemini classification, result storage, and audit logging.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio
from uuid import uuid4

from models.legal_models import (
    Document, Bucket, ClassificationResult, ClassificationEvidence,
    SeverityLevel, RoutingDecision, FIRESTORE_COLLECTIONS
)
from services.context_retriever import ContextRetriever
from gemini_classifier import GeminiClassifier, ClassificationResponse
from storage.bucket_store import BucketStore
from storage.document_store import DocumentStore
from storage.firestore_client import get_firestore_client
from services.confidence_calculator import ConfidenceCalculator
from services.confidence_warning_system import ConfidenceWarningSystem
from audit.audit_logger import (
    AuditLogger, AuditEventType, AuditSeverity, 
    EvidenceTrail, ClassificationDecisionTrail
)

logger = logging.getLogger(__name__)


class ClassificationEngine:
    """
    Main classification orchestration engine.
    
    Coordinates the end-to-end classification pipeline from document input
    to classification result storage and audit logging.
    """
    
    def __init__(
        self,
        context_retriever: Optional[ContextRetriever] = None,
        gemini_classifier: Optional[GeminiClassifier] = None,
        bucket_store: Optional[BucketStore] = None,
        document_store: Optional[DocumentStore] = None,
        confidence_calculator: Optional[ConfidenceCalculator] = None,
        confidence_warning_system: Optional[ConfidenceWarningSystem] = None,
        audit_logger: Optional[AuditLogger] = None,
        enable_audit_logging: bool = True
    ):
        """
        Initialize the classification engine.
        
        Args:
            context_retriever: Context retrieval system
            gemini_classifier: Gemini classification system
            bucket_store: Bucket storage system
            document_store: Document storage system
            confidence_calculator: Confidence calculation system
            confidence_warning_system: Confidence warning system
            audit_logger: Comprehensive audit logging system
            enable_audit_logging: Whether to enable audit logging
        """
        self.context_retriever = context_retriever or ContextRetriever()
        self.gemini_classifier = gemini_classifier or GeminiClassifier()
        self.bucket_store = bucket_store or BucketStore()
        self.document_store = document_store or DocumentStore()
        self.confidence_calculator = confidence_calculator or ConfidenceCalculator()
        self.confidence_warning_system = confidence_warning_system or ConfidenceWarningSystem()
        self.audit_logger = audit_logger or AuditLogger()
        self.enable_audit_logging = enable_audit_logging
        
        # Firestore client for storing results
        self.firestore_client = get_firestore_client()
        
        logger.info("Initialized ClassificationEngine with comprehensive audit logging")
    
    async def _log_audit_event(
        self, 
        event_type: AuditEventType,
        event_details: Dict[str, Any],
        document_id: Optional[str] = None,
        classification_id: Optional[str] = None,
        session_id: Optional[str] = None,
        decision_trail: Optional[ClassificationDecisionTrail] = None,
        error: Optional[Exception] = None
    ) -> str:
        """
        Log an audit event using the comprehensive audit logger.
        
        Args:
            event_type: Type of audit event
            event_details: Event details
            document_id: Document ID
            classification_id: Classification ID
            session_id: Session ID for grouping events
            decision_trail: Complete decision trail
            error: Exception if this is an error event
            
        Returns:
            Log ID of the created audit entry
        """
        if not self.enable_audit_logging:
            return ""
        
        return await self.audit_logger.log_event(
            event_type=event_type,
            event_details=event_details,
            document_id=document_id,
            classification_id=classification_id,
            session_id=session_id,
            decision_trail=decision_trail,
            error=error
        )
    
    async def _store_classification_result(self, result: ClassificationResult) -> bool:
        """
        Store classification result in Firestore.
        
        Args:
            result: Classification result to store
            
        Returns:
            True if storage succeeded, False otherwise
        """
        try:
            collection_name = FIRESTORE_COLLECTIONS['classifications']
            doc_ref = self.firestore_client.collection(collection_name).document(result.classification_id)
            doc_ref.set(result.to_firestore_dict())
            
            logger.info(f"Stored classification result {result.classification_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store classification result: {e}")
            return False
    
    async def _retrieve_classification_result(self, classification_id: str) -> Optional[ClassificationResult]:
        """
        Retrieve classification result from Firestore.
        
        Args:
            classification_id: ID of the classification result
            
        Returns:
            ClassificationResult if found, None otherwise
        """
        try:
            collection_name = FIRESTORE_COLLECTIONS['classifications']
            doc_ref = self.firestore_client.collection(collection_name).document(classification_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            doc_data = doc.to_dict()
            return ClassificationResult.from_firestore_dict(doc_data)
            
        except Exception as e:
            logger.error(f"Failed to retrieve classification result {classification_id}: {e}")
            return None
    
    async def _create_classification_evidence(
        self,
        context_block,
        bucket_id: Optional[str] = None
    ) -> List[ClassificationEvidence]:
        """
        Create classification evidence from context block.
        
        Args:
            context_block: Context block with retrieved chunks
            bucket_id: Primary bucket ID used for classification
            
        Returns:
            List of ClassificationEvidence objects
        """
        evidence_list = []
        
        for chunk in context_block.retrieved_chunks:
            evidence = ClassificationEvidence(
                document_id=chunk['document_id'],
                chunk_text=chunk['chunk_text'],
                similarity_score=chunk['similarity_score'],
                bucket_id=bucket_id or chunk.get('bucket_id', 'unknown')
            )
            evidence_list.append(evidence)
        
        return evidence_list
    
    async def _create_evidence_trail(
        self,
        context_block,
        bucket_id: Optional[str] = None
    ) -> EvidenceTrail:
        """
        Create evidence trail for audit logging.
        
        Args:
            context_block: Context block with retrieved chunks
            bucket_id: Primary bucket ID used for classification
            
        Returns:
            EvidenceTrail object for audit logging
        """
        selected_documents = []
        similarity_scores = []
        context_chunks = []
        
        for chunk in context_block.retrieved_chunks:
            selected_documents.append({
                'document_id': chunk['document_id'],
                'filename': chunk.get('filename', 'unknown')
            })
            similarity_scores.append(chunk['similarity_score'])
            context_chunks.append({
                'chunk_id': chunk.get('chunk_id', str(uuid4())),
                'text': chunk['chunk_text'][:200] + '...' if len(chunk['chunk_text']) > 200 else chunk['chunk_text']
            })
        
        return EvidenceTrail(
            bucket_id=bucket_id or context_block.bucket_info.get('bucket_id', 'unknown'),
            bucket_name=context_block.bucket_info.get('bucket_name', 'Unknown Bucket'),
            selected_documents=selected_documents,
            similarity_scores=similarity_scores,
            context_chunks=context_chunks,
            total_context_length=sum(len(chunk['chunk_text']) for chunk in context_block.retrieved_chunks),
            selection_criteria={
                'min_similarity_threshold': 0.7,  # Default threshold
                'max_chunks_per_bucket': len(context_chunks)
            }
        )
    
    async def classify_document(
        self,
        document: Document,
        available_buckets: Optional[List[Bucket]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> ClassificationResult:
        """
        Perform end-to-end classification of a document with comprehensive audit logging.
        
        Args:
            document: Document to classify
            available_buckets: Available buckets (fetched if None)
            session_id: Session ID for grouping audit events
            user_id: User ID who initiated the classification
            
        Returns:
            ClassificationResult with classification details
            
        Raises:
            Exception: If classification pipeline fails
        """
        classification_id = str(uuid4())
        session_id = session_id or str(uuid4())
        start_time = datetime.utcnow()
        
        # Log classification start
        await self._log_audit_event(
            event_type=AuditEventType.CLASSIFICATION_STARTED,
            event_details={
                'document_type': document.document_type.value,
                'text_length': len(document.text),
                'filename': document.metadata.filename,
                'user_id': user_id
            },
            document_id=document.id,
            classification_id=classification_id,
            session_id=session_id
        )
        
        try:
            logger.info(f"Starting classification for document {document.id}")
            
            # Step 1: Get available buckets if not provided
            if available_buckets is None:
                available_buckets = await self.bucket_store.get_all_buckets()
                logger.debug(f"Retrieved {len(available_buckets)} buckets from storage")
            
            # Step 2: Retrieve context from relevant buckets
            context_block = await self.context_retriever.retrieve_context(
                document, available_buckets
            )
            
            # Create evidence trail for audit logging
            evidence_trail = await self._create_evidence_trail(context_block)
            
            # Log evidence collection
            await self.audit_logger.log_evidence_collection(
                document_id=document.id,
                classification_id=classification_id,
                evidence_trails=[evidence_trail],
                session_id=session_id
            )
            
            # Log context retrieval
            context_stats = await self.context_retriever.get_context_statistics(context_block)
            await self._log_audit_event(
                event_type=AuditEventType.CONTEXT_RETRIEVED,
                event_details=context_stats,
                document_id=document.id,
                classification_id=classification_id,
                session_id=session_id
            )
            
            # Step 3: Format context for classification
            formatted_context = await self.context_retriever.format_context_for_classification(
                context_block
            )
            
            # Step 4: Perform Gemini classification
            document_metadata = {
                'filename': document.metadata.filename,
                'upload_date': document.metadata.upload_date.isoformat(),
                'file_size': document.metadata.file_size
            }
            
            classification_response = await self.gemini_classifier.classify_document(
                document.text,
                formatted_context,
                document_metadata
            )
            
            # Step 5: Create classification evidence
            primary_bucket_id = context_block.bucket_info.get('bucket_id')
            evidence = await self._create_classification_evidence(
                context_block, primary_bucket_id
            )
            
            # Step 6: Calculate enhanced confidence score
            final_confidence, confidence_factors = await self.confidence_calculator.calculate_confidence(
                model_confidence=classification_response.confidence,
                evidence=evidence,
                rule_overrides=classification_response.rule_overrides if hasattr(classification_response, 'rule_overrides') else [],
                applied_rules=[],  # TODO: Get applied rules from rule engine
                predicted_label=classification_response.label
            )
            
            # Step 7: Evaluate confidence warnings
            confidence_warning = self.confidence_warning_system.evaluate_confidence_warning(
                final_confidence, confidence_factors, None  # Will create temp result below
            )
            
            # Step 8: Update routing decision based on confidence warning
            routing_decision = self.confidence_warning_system.update_routing_decision(
                None, confidence_warning  # Will use temp result below
            )
            
            # Step 9: Create classification result with enhanced confidence
            classification_result = ClassificationResult(
                classification_id=classification_id,
                document_id=document.id,
                label=classification_response.label,
                confidence=final_confidence,  # Use enhanced confidence
                rationale=classification_response.rationale,
                evidence=evidence,
                bucket_id=primary_bucket_id,
                routing_decision=routing_decision,  # Use updated routing decision
                model_version="gemini-1.5-pro",
                created_at=datetime.utcnow(),
                confidence_warning=confidence_warning.to_dict() if confidence_warning else None
            )
            
            # Step 10: Create complete decision trail for audit logging
            processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            decision_trail = ClassificationDecisionTrail(
                input_document={
                    'document_id': document.id,
                    'text_length': len(document.text),
                    'document_type': document.document_type.value,
                    'filename': document.metadata.filename
                },
                selected_buckets=[primary_bucket_id] if primary_bucket_id else [],
                evidence_trails=[evidence_trail],
                applied_rules=[],  # TODO: Get from rule engine
                rule_overrides=[],  # TODO: Get from rule engine
                model_response={
                    'label': classification_response.label.value,
                    'confidence': classification_response.confidence,
                    'rationale': classification_response.rationale
                },
                confidence_factors=confidence_factors,
                final_decision={
                    'label': classification_result.label.value,
                    'confidence': classification_result.confidence,
                    'routing_decision': classification_result.routing_decision.value
                },
                processing_time_ms=processing_time_ms
            )
            
            # Step 11: Log complete classification decision
            await self.audit_logger.log_classification_decision(
                classification_result=classification_result,
                decision_trail=decision_trail,
                session_id=session_id,
                user_id=user_id
            )
            
            # Step 12: Log confidence warning if present
            if confidence_warning:
                await self._log_audit_event(
                    event_type=AuditEventType.CONFIDENCE_WARNING,
                    event_details={
                        'warning_type': confidence_warning.warning_type,
                        'confidence_score': confidence_warning.confidence_score,
                        'threshold': confidence_warning.threshold,
                        'message': confidence_warning.message
                    },
                    document_id=document.id,
                    classification_id=classification_id,
                    session_id=session_id
                )
            
            # Step 13: Store classification result
            storage_success = await self._store_classification_result(classification_result)
            
            if storage_success:
                await self._log_audit_event(
                    event_type=AuditEventType.RESULT_STORED,
                    event_details={'storage_location': 'firestore'},
                    document_id=document.id,
                    classification_id=classification_id,
                    session_id=session_id
                )
            else:
                logger.warning(f"Failed to store classification result {classification_id}")
            
            logger.info(f"Classification completed for document {document.id}: "
                       f"{classification_response.label.value} "
                       f"(confidence: {final_confidence:.3f}, processing_time: {processing_time_ms}ms)")
            
            return classification_result
            
        except Exception as e:
            # Log classification failure with comprehensive error details
            await self._log_audit_event(
                event_type=AuditEventType.CLASSIFICATION_FAILED,
                event_details={
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'processing_time_ms': int((datetime.utcnow() - start_time).total_seconds() * 1000)
                },
                document_id=document.id,
                classification_id=classification_id,
                session_id=session_id,
                error=e
            )
            
            logger.error(f"Classification failed for document {document.id}: {e}")
            raise
    
    async def batch_classify_documents(
        self,
        documents: List[Document],
        progress_callback: Optional[callable] = None
    ) -> List[ClassificationResult]:
        """
        Classify multiple documents in batch.
        
        Args:
            documents: List of documents to classify
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of ClassificationResult objects
        """
        if not documents:
            return []
        
        logger.info(f"Starting batch classification for {len(documents)} documents")
        
        # Get buckets once for all classifications
        available_buckets = await self.bucket_store.get_all_buckets()
        
        results = []
        total_docs = len(documents)
        
        for i, document in enumerate(documents):
            try:
                result = await self.classify_document(document, available_buckets)
                results.append(result)
                
                # Call progress callback if provided
                if progress_callback:
                    progress = (i + 1) / total_docs
                    progress_callback(progress, i + 1, total_docs)
                
                # Small delay between classifications
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed to classify document {document.id}: {e}")
                # Create a failed classification result
                failed_result = ClassificationResult(
                    classification_id=str(uuid4()),
                    document_id=document.id,
                    label=SeverityLevel.MEDIUM,  # Default fallback
                    confidence=0.0,
                    rationale=f"Classification failed: {str(e)}",
                    evidence=[],
                    routing_decision=RoutingDecision.HUMAN_TRIAGE,
                    model_version="gemini-1.5-pro",
                    created_at=datetime.utcnow()
                )
                results.append(failed_result)
        
        logger.info(f"Completed batch classification for {len(documents)} documents")
        return results
    
    async def get_classification_history(
        self,
        document_id: str,
        limit: int = 10
    ) -> List[ClassificationResult]:
        """
        Get classification history for a document.
        
        Args:
            document_id: ID of the document
            limit: Maximum number of results to return
            
        Returns:
            List of ClassificationResult objects, newest first
        """
        try:
            collection_name = FIRESTORE_COLLECTIONS['classifications']
            query = (self.firestore_client.collection(collection_name)
                    .where('document_id', '==', document_id)
                    .order_by('created_at', direction='DESCENDING')
                    .limit(limit))
            
            docs = query.stream()
            results = []
            
            for doc in docs:
                doc_data = doc.to_dict()
                result = ClassificationResult.from_firestore_dict(doc_data)
                results.append(result)
            
            logger.debug(f"Retrieved {len(results)} classification results for document {document_id}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to get classification history for {document_id}: {e}")
            return []
    
    async def get_classification_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get classification statistics for a date range.
        
        Args:
            start_date: Start date for statistics (optional)
            end_date: End date for statistics (optional)
            
        Returns:
            Dictionary with classification statistics
        """
        try:
            collection_name = FIRESTORE_COLLECTIONS['classifications']
            query = self.firestore_client.collection(collection_name)
            
            # Apply date filters if provided
            if start_date:
                query = query.where('created_at', '>=', start_date.isoformat())
            if end_date:
                query = query.where('created_at', '<=', end_date.isoformat())
            
            docs = query.stream()
            
            # Calculate statistics
            total_classifications = 0
            label_counts = {}
            routing_counts = {}
            confidence_scores = []
            model_versions = {}
            
            for doc in docs:
                doc_data = doc.to_dict()
                total_classifications += 1
                
                # Count labels
                label = doc_data.get('label', 'UNKNOWN')
                label_counts[label] = label_counts.get(label, 0) + 1
                
                # Count routing decisions
                routing = doc_data.get('routing_decision', 'UNKNOWN')
                routing_counts[routing] = routing_counts.get(routing, 0) + 1
                
                # Collect confidence scores
                confidence = doc_data.get('confidence', 0.0)
                confidence_scores.append(confidence)
                
                # Count model versions
                model_version = doc_data.get('model_version', 'unknown')
                model_versions[model_version] = model_versions.get(model_version, 0) + 1
            
            # Calculate average confidence
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            return {
                'total_classifications': total_classifications,
                'label_distribution': label_counts,
                'routing_distribution': routing_counts,
                'avg_confidence': avg_confidence,
                'max_confidence': max(confidence_scores) if confidence_scores else 0.0,
                'min_confidence': min(confidence_scores) if confidence_scores else 0.0,
                'model_versions': model_versions,
                'date_range': {
                    'start_date': start_date.isoformat() if start_date else None,
                    'end_date': end_date.isoformat() if end_date else None
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get classification statistics: {e}")
            return {'error': str(e)}
    
    async def reprocess_classification(
        self,
        classification_id: str,
        force_reprocess: bool = False
    ) -> Optional[ClassificationResult]:
        """
        Reprocess an existing classification.
        
        Args:
            classification_id: ID of the classification to reprocess
            force_reprocess: Whether to force reprocessing even if recent
            
        Returns:
            New ClassificationResult if successful, None otherwise
        """
        try:
            # Get existing classification
            existing_result = await self._retrieve_classification_result(classification_id)
            if not existing_result:
                logger.warning(f"Classification {classification_id} not found for reprocessing")
                return None
            
            # Check if reprocessing is needed
            if not force_reprocess:
                time_since_classification = datetime.utcnow() - existing_result.created_at
                if time_since_classification.total_seconds() < 3600:  # Less than 1 hour
                    logger.info(f"Classification {classification_id} is recent, skipping reprocessing")
                    return existing_result
            
            # Get the original document
            document = await self.document_store.get_document(existing_result.document_id)
            if not document:
                logger.error(f"Document {existing_result.document_id} not found for reprocessing")
                return None
            
            # Log reprocessing start
            await self._log_audit_event(
                event_type=AuditEventType.REPROCESSING_STARTED,
                event_details={'original_label': existing_result.label.value},
                document_id=document.id,
                classification_id=classification_id
            )
            
            # Perform new classification
            new_result = await self.classify_document(document)
            
            # Log reprocessing completion
            await self._log_audit_event(
                event_type=AuditEventType.REPROCESSING_COMPLETED,
                event_details={
                    'original_label': existing_result.label.value,
                    'new_label': new_result.label.value,
                    'confidence_change': new_result.confidence - existing_result.confidence
                },
                document_id=document.id,
                classification_id=classification_id
            )
            
            logger.info(f"Reprocessed classification {classification_id}: "
                       f"{existing_result.label.value} -> {new_result.label.value}")
            
            return new_result
            
        except Exception as e:
            logger.error(f"Failed to reprocess classification {classification_id}: {e}")
            return None


# Export the main classes
__all__ = ['ClassificationEngine']