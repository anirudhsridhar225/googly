"""
Confidence Warning System for Legal Document Severity Classification.

This module implements the confidence warning system that detects low-confidence
classifications, generates warning flags, and maintains audit trails for
confidence-related decisions.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
from uuid import uuid4

from legal_models import (
    ClassificationResult, SeverityLevel, RoutingDecision,
    FIRESTORE_COLLECTIONS
)
from confidence_calculator import ConfidenceFactors
from firestore_client import get_firestore_client

logger = logging.getLogger(__name__)


class WarningLevel(str, Enum):
    """Enumeration for confidence warning levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WarningReason(str, Enum):
    """Enumeration for confidence warning reasons."""
    LOW_MODEL_CONFIDENCE = "low_model_confidence"
    LOW_CHUNK_SIMILARITY = "low_chunk_similarity"
    POOR_EVIDENCE_QUALITY = "poor_evidence_quality"
    INCONSISTENT_EVIDENCE = "inconsistent_evidence"
    NO_RULE_SUPPORT = "no_rule_support"
    CONFLICTING_RULES = "conflicting_rules"
    HISTORICAL_INACCURACY = "historical_inaccuracy"
    EXTREME_SEVERITY_PREDICTION = "extreme_severity_prediction"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    MODEL_UNCERTAINTY = "model_uncertainty"


class ConfidenceWarning:
    """Container for confidence warning information."""
    
    def __init__(
        self,
        warning_id: str,
        warning_level: WarningLevel,
        warning_reasons: List[WarningReason],
        confidence_score: float,
        threshold_violated: float,
        message: str,
        recommendations: List[str],
        created_at: Optional[datetime] = None
    ):
        self.warning_id = warning_id
        self.warning_level = warning_level
        self.warning_reasons = warning_reasons
        self.confidence_score = confidence_score
        self.threshold_violated = threshold_violated
        self.message = message
        self.recommendations = recommendations
        self.created_at = created_at or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert warning to dictionary format."""
        return {
            'warning_id': self.warning_id,
            'warning_level': self.warning_level.value,
            'warning_reasons': [reason.value for reason in self.warning_reasons],
            'confidence_score': self.confidence_score,
            'threshold_violated': self.threshold_violated,
            'message': self.message,
            'recommendations': self.recommendations,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfidenceWarning':
        """Create warning from dictionary."""
        return cls(
            warning_id=data['warning_id'],
            warning_level=WarningLevel(data['warning_level']),
            warning_reasons=[WarningReason(reason) for reason in data['warning_reasons']],
            confidence_score=data['confidence_score'],
            threshold_violated=data['threshold_violated'],
            message=data['message'],
            recommendations=data['recommendations'],
            created_at=datetime.fromisoformat(data['created_at'])
        )


class ConfidenceThresholds:
    """Configuration for confidence warning thresholds."""
    
    def __init__(
        self,
        critical_threshold: float = 0.3,
        high_threshold: float = 0.5,
        medium_threshold: float = 0.7,
        low_threshold: float = 0.85,
        model_confidence_threshold: float = 0.6,
        chunk_similarity_threshold: float = 0.5,
        evidence_quality_threshold: float = 0.4,
        rule_support_threshold: float = 0.6
    ):
        """
        Initialize confidence thresholds.
        
        Args:
            critical_threshold: Below this triggers critical warnings
            high_threshold: Below this triggers high warnings
            medium_threshold: Below this triggers medium warnings
            low_threshold: Below this triggers low warnings
            model_confidence_threshold: Minimum acceptable model confidence
            chunk_similarity_threshold: Minimum acceptable chunk similarity
            evidence_quality_threshold: Minimum acceptable evidence quality
            rule_support_threshold: Minimum acceptable rule support
        """
        self.critical_threshold = critical_threshold
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold
        self.low_threshold = low_threshold
        self.model_confidence_threshold = model_confidence_threshold
        self.chunk_similarity_threshold = chunk_similarity_threshold
        self.evidence_quality_threshold = evidence_quality_threshold
        self.rule_support_threshold = rule_support_threshold
        
        # Validate thresholds are in ascending order
        thresholds = [critical_threshold, high_threshold, medium_threshold, low_threshold]
        if not all(thresholds[i] <= thresholds[i+1] for i in range(len(thresholds)-1)):
            raise ValueError("Thresholds must be in ascending order")


class ConfidenceWarningSystem:
    """
    System for detecting and managing confidence warnings.
    
    Analyzes classification results and confidence factors to identify
    low-confidence classifications and generate appropriate warnings.
    """
    
    def __init__(
        self,
        thresholds: Optional[ConfidenceThresholds] = None,
        enable_audit_logging: bool = True
    ):
        """
        Initialize the confidence warning system.
        
        Args:
            thresholds: Confidence thresholds configuration
            enable_audit_logging: Whether to enable audit logging
        """
        self.thresholds = thresholds or ConfidenceThresholds()
        self.enable_audit_logging = enable_audit_logging
        
        # Firestore client for logging
        self.firestore_client = get_firestore_client()
        
        logger.info("Initialized ConfidenceWarningSystem")
    
    def _determine_warning_level(self, confidence_score: float) -> WarningLevel:
        """
        Determine warning level based on confidence score.
        
        Args:
            confidence_score: Overall confidence score
            
        Returns:
            WarningLevel enum value
        """
        if confidence_score < self.thresholds.critical_threshold:
            return WarningLevel.CRITICAL
        elif confidence_score < self.thresholds.high_threshold:
            return WarningLevel.HIGH
        elif confidence_score < self.thresholds.medium_threshold:
            return WarningLevel.MEDIUM
        elif confidence_score < self.thresholds.low_threshold:
            return WarningLevel.LOW
        else:
            return WarningLevel.NONE
    
    def _analyze_confidence_factors(
        self,
        confidence_factors: ConfidenceFactors,
        classification_result: ClassificationResult
    ) -> List[WarningReason]:
        """
        Analyze confidence factors to identify specific warning reasons.
        
        Args:
            confidence_factors: Detailed confidence factors
            classification_result: Classification result to analyze
            
        Returns:
            List of warning reasons
        """
        warning_reasons = []
        
        # Check model confidence
        if confidence_factors.model_confidence < self.thresholds.model_confidence_threshold:
            warning_reasons.append(WarningReason.LOW_MODEL_CONFIDENCE)
        
        # Check chunk similarity
        if confidence_factors.chunk_similarity_score < self.thresholds.chunk_similarity_threshold:
            warning_reasons.append(WarningReason.LOW_CHUNK_SIMILARITY)
        
        # Check evidence quality
        if confidence_factors.evidence_quality_score < self.thresholds.evidence_quality_threshold:
            warning_reasons.append(WarningReason.POOR_EVIDENCE_QUALITY)
        
        # Check rule support
        if confidence_factors.rule_override_score < self.thresholds.rule_support_threshold:
            if not classification_result.rule_overrides:
                warning_reasons.append(WarningReason.NO_RULE_SUPPORT)
            else:
                warning_reasons.append(WarningReason.CONFLICTING_RULES)
        
        # Check historical calibration
        if confidence_factors.historical_calibration_score < 0.8:
            warning_reasons.append(WarningReason.HISTORICAL_INACCURACY)
        
        # Check for extreme severity predictions
        if classification_result.label in [SeverityLevel.CRITICAL, SeverityLevel.LOW]:
            if confidence_factors.model_confidence < 0.8:
                warning_reasons.append(WarningReason.EXTREME_SEVERITY_PREDICTION)
        
        # Check for insufficient context
        if len(classification_result.evidence) < 2:
            warning_reasons.append(WarningReason.INSUFFICIENT_CONTEXT)
        
        # Check for model uncertainty (very low or very high confidence can indicate uncertainty)
        if confidence_factors.model_confidence < 0.2 or confidence_factors.model_confidence > 0.98:
            warning_reasons.append(WarningReason.MODEL_UNCERTAINTY)
        
        # Check for inconsistent evidence
        if len(classification_result.evidence) > 1:
            similarity_scores = [e.similarity_score for e in classification_result.evidence]
            if max(similarity_scores) - min(similarity_scores) > 0.4:
                warning_reasons.append(WarningReason.INCONSISTENT_EVIDENCE)
        
        return warning_reasons
    
    def _generate_warning_message(
        self,
        warning_level: WarningLevel,
        warning_reasons: List[WarningReason],
        confidence_score: float,
        classification_result: ClassificationResult
    ) -> str:
        """
        Generate human-readable warning message.
        
        Args:
            warning_level: Level of the warning
            warning_reasons: Specific reasons for the warning
            confidence_score: Overall confidence score
            classification_result: Classification result
            
        Returns:
            Warning message string
        """
        severity = classification_result.label.value
        
        base_message = (
            f"{warning_level.value.upper()} confidence warning for {severity} classification "
            f"(confidence: {confidence_score:.2f}). "
        )
        
        if WarningReason.LOW_MODEL_CONFIDENCE in warning_reasons:
            base_message += "Model confidence is below acceptable threshold. "
        
        if WarningReason.LOW_CHUNK_SIMILARITY in warning_reasons:
            base_message += "Retrieved evidence has low similarity to input document. "
        
        if WarningReason.POOR_EVIDENCE_QUALITY in warning_reasons:
            base_message += "Evidence quality is insufficient for reliable classification. "
        
        if WarningReason.INSUFFICIENT_CONTEXT in warning_reasons:
            base_message += "Insufficient contextual evidence available. "
        
        if WarningReason.NO_RULE_SUPPORT in warning_reasons:
            base_message += "No deterministic rules support this classification. "
        
        if WarningReason.HISTORICAL_INACCURACY in warning_reasons:
            base_message += "Historical data suggests lower accuracy for similar cases. "
        
        if WarningReason.EXTREME_SEVERITY_PREDICTION in warning_reasons:
            base_message += "Extreme severity prediction requires additional verification. "
        
        return base_message.strip()
    
    def _generate_recommendations(
        self,
        warning_level: WarningLevel,
        warning_reasons: List[WarningReason],
        classification_result: ClassificationResult
    ) -> List[str]:
        """
        Generate recommendations based on warning reasons.
        
        Args:
            warning_level: Level of the warning
            warning_reasons: Specific reasons for the warning
            classification_result: Classification result
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if warning_level in [WarningLevel.CRITICAL, WarningLevel.HIGH]:
            recommendations.append("Consider manual review by legal expert")
        
        if WarningReason.LOW_MODEL_CONFIDENCE in warning_reasons:
            recommendations.append("Review document content for clarity and completeness")
            recommendations.append("Consider additional context or reference documents")
        
        if WarningReason.LOW_CHUNK_SIMILARITY in warning_reasons:
            recommendations.append("Verify document type matches expected legal domain")
            recommendations.append("Consider expanding reference document collection")
        
        if WarningReason.POOR_EVIDENCE_QUALITY in warning_reasons:
            recommendations.append("Add more high-quality reference documents to relevant buckets")
            recommendations.append("Review and improve document preprocessing")
        
        if WarningReason.INSUFFICIENT_CONTEXT in warning_reasons:
            recommendations.append("Ensure sufficient reference documents are available")
            recommendations.append("Consider manual context addition")
        
        if WarningReason.NO_RULE_SUPPORT in warning_reasons:
            recommendations.append("Review and potentially add deterministic rules")
            recommendations.append("Verify rule conditions are properly configured")
        
        if WarningReason.EXTREME_SEVERITY_PREDICTION in warning_reasons:
            recommendations.append("Double-check classification against known precedents")
            recommendations.append("Consider escalation to senior legal reviewer")
        
        if WarningReason.HISTORICAL_INACCURACY in warning_reasons:
            recommendations.append("Review historical classification accuracy")
            recommendations.append("Consider model retraining or calibration")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return unique_recommendations
    
    def evaluate_confidence_warning(
        self,
        confidence_score: float,
        confidence_factors: ConfidenceFactors,
        classification_result: ClassificationResult
    ) -> Optional[ConfidenceWarning]:
        """
        Evaluate whether a confidence warning should be generated.
        
        Args:
            confidence_score: Overall confidence score
            confidence_factors: Detailed confidence factors
            classification_result: Classification result to evaluate
            
        Returns:
            ConfidenceWarning if warning needed, None otherwise
        """
        try:
            # Determine warning level
            warning_level = self._determine_warning_level(confidence_score)
            
            if warning_level == WarningLevel.NONE:
                return None
            
            # Analyze specific warning reasons
            warning_reasons = self._analyze_confidence_factors(confidence_factors, classification_result)
            
            if not warning_reasons:
                # No specific reasons found, but confidence is low
                warning_reasons = [WarningReason.LOW_MODEL_CONFIDENCE]
            
            # Determine which threshold was violated
            threshold_violated = self.thresholds.low_threshold
            if warning_level == WarningLevel.CRITICAL:
                threshold_violated = self.thresholds.critical_threshold
            elif warning_level == WarningLevel.HIGH:
                threshold_violated = self.thresholds.high_threshold
            elif warning_level == WarningLevel.MEDIUM:
                threshold_violated = self.thresholds.medium_threshold
            
            # Generate warning message and recommendations
            message = self._generate_warning_message(
                warning_level, warning_reasons, confidence_score, classification_result
            )
            recommendations = self._generate_recommendations(
                warning_level, warning_reasons, classification_result
            )
            
            # Create warning
            warning = ConfidenceWarning(
                warning_id=str(uuid4()),
                warning_level=warning_level,
                warning_reasons=warning_reasons,
                confidence_score=confidence_score,
                threshold_violated=threshold_violated,
                message=message,
                recommendations=recommendations
            )
            
            logger.info(f"Generated {warning_level.value} confidence warning for "
                       f"classification {classification_result.classification_id}")
            
            return warning
            
        except Exception as e:
            logger.error(f"Failed to evaluate confidence warning: {e}")
            return None
    
    async def log_confidence_warning(
        self,
        warning: ConfidenceWarning,
        classification_id: str,
        document_id: str
    ) -> bool:
        """
        Log confidence warning to audit trail.
        
        Args:
            warning: Confidence warning to log
            classification_id: ID of the classification
            document_id: ID of the document
            
        Returns:
            True if logging succeeded, False otherwise
        """
        if not self.enable_audit_logging:
            return True
        
        try:
            # Create audit log entry
            audit_entry = {
                'log_id': str(uuid4()),
                'classification_id': classification_id,
                'document_id': document_id,
                'operation': 'confidence_warning_generated',
                'warning_data': warning.to_dict(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Store in Firestore
            collection_name = FIRESTORE_COLLECTIONS['audit_logs']
            doc_ref = self.firestore_client.collection(collection_name).document(audit_entry['log_id'])
            doc_ref.set(audit_entry)
            
            logger.debug(f"Logged confidence warning {warning.warning_id} for "
                        f"classification {classification_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log confidence warning: {e}")
            return False
    
    def should_trigger_human_review(self, warning: Optional[ConfidenceWarning]) -> bool:
        """
        Determine if a confidence warning should trigger human review.
        
        Args:
            warning: Confidence warning (None if no warning)
            
        Returns:
            True if human review should be triggered
        """
        if not warning:
            return False
        
        # Critical and high warnings always trigger review
        if warning.warning_level in [WarningLevel.CRITICAL, WarningLevel.HIGH]:
            return True
        
        # Medium warnings trigger review for extreme severity predictions
        if (warning.warning_level == WarningLevel.MEDIUM and
            WarningReason.EXTREME_SEVERITY_PREDICTION in warning.warning_reasons):
            return True
        
        # Multiple warning reasons in medium level trigger review
        if (warning.warning_level == WarningLevel.MEDIUM and
            len(warning.warning_reasons) >= 3):
            return True
        
        return False
    
    def update_routing_decision(
        self,
        classification_result: ClassificationResult,
        warning: Optional[ConfidenceWarning]
    ) -> RoutingDecision:
        """
        Update routing decision based on confidence warning.
        
        Args:
            classification_result: Original classification result
            warning: Confidence warning (None if no warning)
            
        Returns:
            Updated routing decision
        """
        if not warning:
            return RoutingDecision.AUTO_ACCEPT
        
        if self.should_trigger_human_review(warning):
            if warning.warning_level == WarningLevel.CRITICAL:
                return RoutingDecision.HUMAN_TRIAGE
            else:
                return RoutingDecision.HUMAN_REVIEW
        
        return RoutingDecision.AUTO_ACCEPT
    
    async def get_warning_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get confidence warning statistics.
        
        Args:
            start_date: Start date for statistics
            end_date: End date for statistics
            
        Returns:
            Dictionary with warning statistics
        """
        try:
            collection_name = FIRESTORE_COLLECTIONS['audit_logs']
            query = (self.firestore_client.collection(collection_name)
                    .where('operation', '==', 'confidence_warning_generated'))
            
            # Apply date filters
            if start_date:
                query = query.where('timestamp', '>=', start_date.isoformat())
            if end_date:
                query = query.where('timestamp', '<=', end_date.isoformat())
            
            docs = query.stream()
            
            total_warnings = 0
            warning_level_counts = {}
            warning_reason_counts = {}
            confidence_scores = []
            
            for doc in docs:
                doc_data = doc.to_dict()
                warning_data = doc_data.get('warning_data', {})
                
                total_warnings += 1
                
                # Count warning levels
                warning_level = warning_data.get('warning_level', 'unknown')
                warning_level_counts[warning_level] = warning_level_counts.get(warning_level, 0) + 1
                
                # Count warning reasons
                warning_reasons = warning_data.get('warning_reasons', [])
                for reason in warning_reasons:
                    warning_reason_counts[reason] = warning_reason_counts.get(reason, 0) + 1
                
                # Collect confidence scores
                confidence_score = warning_data.get('confidence_score', 0.0)
                confidence_scores.append(confidence_score)
            
            # Calculate statistics
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            return {
                'total_warnings': total_warnings,
                'warning_level_distribution': warning_level_counts,
                'warning_reason_distribution': warning_reason_counts,
                'avg_confidence_with_warnings': avg_confidence,
                'min_confidence_with_warnings': min(confidence_scores) if confidence_scores else 0.0,
                'max_confidence_with_warnings': max(confidence_scores) if confidence_scores else 0.0,
                'date_range': {
                    'start_date': start_date.isoformat() if start_date else None,
                    'end_date': end_date.isoformat() if end_date else None
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get warning statistics: {e}")
            return {'error': str(e)}


# Export the main classes
__all__ = [
    'ConfidenceWarningSystem', 'ConfidenceWarning', 'ConfidenceThresholds',
    'WarningLevel', 'WarningReason'
]