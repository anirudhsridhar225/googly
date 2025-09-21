"""
Fallback Classification Strategies for Legal Document Severity Classification System.

This module provides fallback classification strategies when AI services are unavailable,
including rule-based classification and keyword-based severity detection.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime

from models.legal_models import SeverityLevel, ClassificationResult, ClassificationEvidence
from core.exceptions import ClassificationException, InsufficientContextException
from audit.error_logger import error_logger

logger = logging.getLogger(__name__)


class KeywordClassifier:
    """
    Keyword-based classification fallback.
    
    Uses predefined keyword patterns to classify document severity
    when AI services are unavailable.
    """
    
    def __init__(self):
        # Define severity keywords (can be loaded from configuration)
        self.severity_keywords = {
            SeverityLevel.CRITICAL: {
                'keywords': [
                    'immediate termination', 'breach of contract', 'lawsuit', 'litigation',
                    'criminal charges', 'felony', 'fraud', 'embezzlement', 'bankruptcy',
                    'cease and desist', 'injunction', 'restraining order', 'emergency',
                    'urgent legal action', 'court order', 'subpoena', 'warrant',
                    'class action', 'punitive damages', 'criminal liability'
                ],
                'patterns': [
                    r'must\s+respond\s+within\s+\d+\s+days?',
                    r'legal\s+action\s+will\s+be\s+taken',
                    r'violation\s+of\s+federal\s+law',
                    r'criminal\s+prosecution',
                    r'immediate\s+compliance\s+required'
                ],
                'weight': 1.0
            },
            SeverityLevel.HIGH: {
                'keywords': [
                    'contract violation', 'breach', 'default', 'non-compliance',
                    'penalty', 'fine', 'damages', 'liability', 'dispute',
                    'arbitration', 'mediation', 'settlement', 'claim',
                    'intellectual property', 'copyright infringement', 'trademark',
                    'confidentiality breach', 'data breach', 'privacy violation',
                    'employment law', 'discrimination', 'harassment'
                ],
                'patterns': [
                    r'breach\s+of\s+\w+\s+agreement',
                    r'failure\s+to\s+comply',
                    r'legal\s+consequences',
                    r'monetary\s+damages',
                    r'regulatory\s+violation'
                ],
                'weight': 0.8
            },
            SeverityLevel.MEDIUM: {
                'keywords': [
                    'contract amendment', 'policy update', 'compliance review',
                    'audit', 'inspection', 'notification', 'reminder',
                    'renewal', 'extension', 'modification', 'addendum',
                    'terms and conditions', 'service agreement', 'license',
                    'permit', 'registration', 'filing requirement'
                ],
                'patterns': [
                    r'requires?\s+your\s+attention',
                    r'please\s+review',
                    r'action\s+required',
                    r'compliance\s+update',
                    r'policy\s+change'
                ],
                'weight': 0.6
            },
            SeverityLevel.LOW: {
                'keywords': [
                    'information', 'notice', 'announcement', 'update',
                    'newsletter', 'bulletin', 'advisory', 'guidance',
                    'recommendation', 'suggestion', 'best practice',
                    'educational', 'informational', 'reference'
                ],
                'patterns': [
                    r'for\s+your\s+information',
                    r'informational\s+purposes',
                    r'no\s+action\s+required',
                    r'reference\s+only',
                    r'educational\s+material'
                ],
                'weight': 0.4
            }
        }
        
        # Compile regex patterns for efficiency
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for efficient matching."""
        for severity, data in self.severity_keywords.items():
            data['compiled_patterns'] = [
                re.compile(pattern, re.IGNORECASE) 
                for pattern in data['patterns']
            ]
    
    def classify_document(
        self,
        document_text: str,
        document_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ClassificationResult:
        """
        Classify document using keyword-based approach.
        
        Args:
            document_text: Text content of the document
            document_id: Document identifier
            context: Additional context information
            
        Returns:
            Classification result with fallback rationale
        """
        context = context or {}
        
        # Calculate scores for each severity level
        severity_scores = {}
        matched_keywords = {}
        matched_patterns = {}
        
        document_lower = document_text.lower()
        
        for severity, data in self.severity_keywords.items():
            score = 0.0
            keywords_found = []
            patterns_found = []
            
            # Check keywords
            for keyword in data['keywords']:
                if keyword.lower() in document_lower:
                    score += data['weight']
                    keywords_found.append(keyword)
            
            # Check patterns
            for pattern in data['compiled_patterns']:
                matches = pattern.findall(document_text)
                if matches:
                    score += data['weight'] * len(matches)
                    patterns_found.extend(matches)
            
            severity_scores[severity] = score
            matched_keywords[severity] = keywords_found
            matched_patterns[severity] = patterns_found
        
        # Determine final classification
        if not any(severity_scores.values()):
            # No keywords matched, default to LOW
            final_severity = SeverityLevel.LOW
            confidence = 0.3
            rationale = "No specific legal keywords detected. Defaulting to LOW severity."
        else:
            # Choose severity with highest score
            final_severity = max(severity_scores.keys(), key=lambda k: severity_scores[k])
            max_score = severity_scores[final_severity]
            
            # Calculate confidence based on score and keyword matches
            total_keywords = sum(len(keywords) for keywords in matched_keywords.values())
            confidence = min(0.8, max_score / 5.0 + (total_keywords * 0.1))  # Cap at 0.8 for fallback
            
            # Build rationale
            rationale_parts = []
            if matched_keywords[final_severity]:
                rationale_parts.append(f"Keywords detected: {', '.join(matched_keywords[final_severity][:3])}")
            if matched_patterns[final_severity]:
                rationale_parts.append(f"Patterns matched: {len(matched_patterns[final_severity])}")
            
            rationale = f"Keyword-based classification (fallback). {'. '.join(rationale_parts)}."
        
        # Create evidence from matched keywords and patterns
        evidence = []
        if matched_keywords[final_severity] or matched_patterns[final_severity]:
            evidence_text = f"Keywords: {', '.join(matched_keywords[final_severity][:5])}"
            if matched_patterns[final_severity]:
                evidence_text += f". Patterns: {', '.join(matched_patterns[final_severity][:3])}"
            
            evidence.append(ClassificationEvidence(
                document_id=f"fallback_keywords_{document_id}",
                chunk_text=evidence_text,
                similarity_score=confidence,
                bucket_id="keyword_classifier"
            ))
        
        # Log fallback classification
        error_logger.log_error(
            f"Fallback keyword classification: {final_severity.value} (confidence: {confidence:.2f})",
            "FALLBACK_CLASSIFICATION",
            level=error_logger.LogLevel.INFO,
            context={
                "document_id": document_id,
                "severity": final_severity.value,
                "confidence": confidence,
                "matched_keywords": len(matched_keywords[final_severity]),
                "matched_patterns": len(matched_patterns[final_severity])
            }
        )
        
        return ClassificationResult(
            classification_id=f"fallback_{document_id}_{int(datetime.utcnow().timestamp())}",
            document_id=document_id,
            label=final_severity,
            confidence=confidence,
            rationale=rationale,
            evidence=evidence,
            bucket_id="fallback_classifier",
            rule_overrides=[],
            created_at=datetime.utcnow(),
            processing_metadata={
                "classifier_type": "keyword_fallback",
                "keywords_matched": sum(len(kw) for kw in matched_keywords.values()),
                "patterns_matched": sum(len(pt) for pt in matched_patterns.values()),
                "fallback_reason": "AI service unavailable"
            }
        )


class RuleBasedFallback:
    """
    Rule-based fallback classifier.
    
    Uses deterministic rules when AI services are unavailable.
    """
    
    def __init__(self):
        self.fallback_rules = [
            {
                'name': 'Legal Action Keywords',
                'condition': lambda text: any(keyword in text.lower() for keyword in [
                    'lawsuit', 'litigation', 'court', 'judge', 'attorney', 'legal action'
                ]),
                'severity': SeverityLevel.CRITICAL,
                'confidence': 0.7,
                'rationale': 'Document contains legal action keywords'
            },
            {
                'name': 'Contract Breach',
                'condition': lambda text: any(keyword in text.lower() for keyword in [
                    'breach of contract', 'contract violation', 'default'
                ]),
                'severity': SeverityLevel.HIGH,
                'confidence': 0.6,
                'rationale': 'Document indicates contract breach'
            },
            {
                'name': 'Compliance Issues',
                'condition': lambda text: any(keyword in text.lower() for keyword in [
                    'non-compliance', 'violation', 'regulatory'
                ]),
                'severity': SeverityLevel.HIGH,
                'confidence': 0.6,
                'rationale': 'Document indicates compliance issues'
            },
            {
                'name': 'Policy Updates',
                'condition': lambda text: any(keyword in text.lower() for keyword in [
                    'policy update', 'terms change', 'amendment'
                ]),
                'severity': SeverityLevel.MEDIUM,
                'confidence': 0.5,
                'rationale': 'Document contains policy updates'
            },
            {
                'name': 'Informational Content',
                'condition': lambda text: any(keyword in text.lower() for keyword in [
                    'for your information', 'informational', 'newsletter'
                ]),
                'severity': SeverityLevel.LOW,
                'confidence': 0.4,
                'rationale': 'Document appears to be informational'
            }
        ]
    
    def classify_document(
        self,
        document_text: str,
        document_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ClassificationResult:
        """
        Classify document using rule-based approach.
        
        Args:
            document_text: Text content of the document
            document_id: Document identifier
            context: Additional context information
            
        Returns:
            Classification result with rule-based rationale
        """
        context = context or {}
        
        # Apply rules in order of severity (highest first)
        applied_rules = []
        
        for rule in self.fallback_rules:
            try:
                if rule['condition'](document_text):
                    applied_rules.append(rule)
            except Exception as e:
                logger.warning(f"Rule '{rule['name']}' failed: {e}")
                continue
        
        if applied_rules:
            # Use the first (highest severity) matching rule
            selected_rule = applied_rules[0]
            final_severity = selected_rule['severity']
            confidence = selected_rule['confidence']
            rationale = f"Rule-based classification (fallback): {selected_rule['rationale']}"
            
            # Add information about other matching rules
            if len(applied_rules) > 1:
                other_rules = [rule['name'] for rule in applied_rules[1:]]
                rationale += f" Additional rules matched: {', '.join(other_rules)}"
        else:
            # No rules matched, default to LOW
            final_severity = SeverityLevel.LOW
            confidence = 0.3
            rationale = "Rule-based classification (fallback): No specific rules matched, defaulting to LOW severity"
        
        # Create evidence from applied rules
        evidence = []
        if applied_rules:
            evidence_text = f"Applied rules: {', '.join([rule['name'] for rule in applied_rules])}"
            evidence.append(ClassificationEvidence(
                document_id=f"fallback_rules_{document_id}",
                chunk_text=evidence_text,
                similarity_score=confidence,
                bucket_id="rule_based_fallback"
            ))
        
        # Log fallback classification
        error_logger.log_error(
            f"Fallback rule-based classification: {final_severity.value} (confidence: {confidence:.2f})",
            "FALLBACK_RULE_CLASSIFICATION",
            level=error_logger.LogLevel.INFO,
            context={
                "document_id": document_id,
                "severity": final_severity.value,
                "confidence": confidence,
                "rules_applied": len(applied_rules),
                "selected_rule": applied_rules[0]['name'] if applied_rules else None
            }
        )
        
        return ClassificationResult(
            classification_id=f"fallback_rule_{document_id}_{int(datetime.utcnow().timestamp())}",
            document_id=document_id,
            label=final_severity,
            confidence=confidence,
            rationale=rationale,
            evidence=evidence,
            bucket_id="rule_based_fallback",
            rule_overrides=[],
            created_at=datetime.utcnow(),
            processing_metadata={
                "classifier_type": "rule_based_fallback",
                "rules_applied": len(applied_rules),
                "selected_rule": applied_rules[0]['name'] if applied_rules else None,
                "fallback_reason": "AI service unavailable"
            }
        )


class HybridFallbackClassifier:
    """
    Hybrid fallback classifier combining keyword and rule-based approaches.
    
    Provides the most robust fallback classification when AI services are unavailable.
    """
    
    def __init__(self):
        self.keyword_classifier = KeywordClassifier()
        self.rule_classifier = RuleBasedFallback()
    
    def classify_document(
        self,
        document_text: str,
        document_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ClassificationResult:
        """
        Classify document using hybrid approach.
        
        Args:
            document_text: Text content of the document
            document_id: Document identifier
            context: Additional context information
            
        Returns:
            Classification result combining both approaches
        """
        context = context or {}
        
        try:
            # Get classifications from both approaches
            keyword_result = self.keyword_classifier.classify_document(
                document_text, document_id, context
            )
            rule_result = self.rule_classifier.classify_document(
                document_text, document_id, context
            )
            
            # Combine results using weighted approach
            keyword_weight = 0.6
            rule_weight = 0.4
            
            # Calculate combined confidence
            combined_confidence = (
                keyword_result.confidence * keyword_weight +
                rule_result.confidence * rule_weight
            )
            
            # Determine final severity (use higher severity if confidence is close)
            keyword_severity_value = self._severity_to_numeric(keyword_result.label)
            rule_severity_value = self._severity_to_numeric(rule_result.label)
            
            if abs(keyword_result.confidence - rule_result.confidence) < 0.2:
                # Confidences are close, use higher severity
                final_severity = keyword_result.label if keyword_severity_value >= rule_severity_value else rule_result.label
            else:
                # Use result from more confident classifier
                final_severity = keyword_result.label if keyword_result.confidence > rule_result.confidence else rule_result.label
            
            # Combine rationales
            rationale = f"Hybrid fallback classification: Keyword-based: {keyword_result.label.value} ({keyword_result.confidence:.2f}), Rule-based: {rule_result.label.value} ({rule_result.confidence:.2f}). Final: {final_severity.value}"
            
            # Combine evidence
            evidence = keyword_result.evidence + rule_result.evidence
            
            # Log hybrid classification
            error_logger.log_error(
                f"Hybrid fallback classification: {final_severity.value} (confidence: {combined_confidence:.2f})",
                "HYBRID_FALLBACK_CLASSIFICATION",
                level=error_logger.LogLevel.INFO,
                context={
                    "document_id": document_id,
                    "final_severity": final_severity.value,
                    "combined_confidence": combined_confidence,
                    "keyword_severity": keyword_result.label.value,
                    "keyword_confidence": keyword_result.confidence,
                    "rule_severity": rule_result.label.value,
                    "rule_confidence": rule_result.confidence
                }
            )
            
            return ClassificationResult(
                classification_id=f"hybrid_fallback_{document_id}_{int(datetime.utcnow().timestamp())}",
                document_id=document_id,
                label=final_severity,
                confidence=combined_confidence,
                rationale=rationale,
                evidence=evidence,
                bucket_id="hybrid_fallback",
                rule_overrides=[],
                created_at=datetime.utcnow(),
                processing_metadata={
                    "classifier_type": "hybrid_fallback",
                    "keyword_result": {
                        "severity": keyword_result.label.value,
                        "confidence": keyword_result.confidence
                    },
                    "rule_result": {
                        "severity": rule_result.label.value,
                        "confidence": rule_result.confidence
                    },
                    "fallback_reason": "AI service unavailable"
                }
            )
            
        except Exception as e:
            error_logger.log_exception(
                e,
                context={
                    "document_id": document_id,
                    "operation": "hybrid_fallback_classification"
                }
            )
            
            # Ultimate fallback - return LOW severity with minimal confidence
            return ClassificationResult(
                classification_id=f"emergency_fallback_{document_id}_{int(datetime.utcnow().timestamp())}",
                document_id=document_id,
                label=SeverityLevel.LOW,
                confidence=0.1,
                rationale="Emergency fallback: All classification methods failed, defaulting to LOW severity",
                evidence=[],
                bucket_id="emergency_fallback",
                rule_overrides=[],
                created_at=datetime.utcnow(),
                processing_metadata={
                    "classifier_type": "emergency_fallback",
                    "fallback_reason": "All classification methods failed"
                }
            )
    
    def _severity_to_numeric(self, severity: SeverityLevel) -> int:
        """Convert severity level to numeric value for comparison."""
        severity_values = {
            SeverityLevel.LOW: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.HIGH: 3,
            SeverityLevel.CRITICAL: 4
        }
        return severity_values.get(severity, 1)


# Global fallback classifier instance
fallback_classifier = HybridFallbackClassifier()

# Export classes and instances
__all__ = [
    'KeywordClassifier',
    'RuleBasedFallback',
    'HybridFallbackClassifier',
    'fallback_classifier'
]