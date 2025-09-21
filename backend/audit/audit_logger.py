"""
Comprehensive Audit Logging System for Legal Document Classification.

This module provides comprehensive audit logging functionality for all classification
decisions, evidence trails, and system operations with complete traceability.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from uuid import uuid4
from enum import Enum
import json

from pydantic import BaseModel, Field, field_validator
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from models.legal_models import (
    FirestoreSerializable, ClassificationResult, ClassificationEvidence,
    Document, Bucket, Rule, SeverityLevel, FIRESTORE_COLLECTIONS
)
from storage.firestore_client import get_firestore_client

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events that can be logged."""
    CLASSIFICATION_STARTED = "classification_started"
    CLASSIFICATION_COMPLETED = "classification_completed"
    CLASSIFICATION_FAILED = "classification_failed"
    CONTEXT_RETRIEVED = "context_retrieved"
    BUCKET_SELECTED = "bucket_selected"
    EVIDENCE_COLLECTED = "evidence_collected"
    RULE_APPLIED = "rule_applied"
    RULE_OVERRIDE = "rule_override"
    CONFIDENCE_WARNING = "confidence_warning"
    RESULT_STORED = "result_stored"
    HUMAN_REVIEW_REQUESTED = "human_review_requested"
    HUMAN_REVIEW_COMPLETED = "human_review_completed"
    REPROCESSING_STARTED = "reprocessing_started"
    REPROCESSING_COMPLETED = "reprocessing_completed"
    SYSTEM_ERROR = "system_error"
    DOCUMENT_UPLOADED = "document_uploaded"
    BUCKET_CREATED = "bucket_created"
    BUCKET_UPDATED = "bucket_updated"
    RULE_CREATED = "rule_created"
    RULE_UPDATED = "rule_updated"
    RULE_DELETED = "rule_deleted"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EvidenceTrail(BaseModel):
    """Complete evidence trail for a classification decision."""
    
    bucket_id: str
    bucket_name: str
    selected_documents: List[Dict[str, Any]] = Field(default_factory=list)
    similarity_scores: List[float] = Field(default_factory=list)
    context_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    total_context_length: int = 0
    selection_criteria: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('similarity_scores')
    @classmethod
    def validate_similarity_scores(cls, v):
        for score in v:
            if not 0.0 <= score <= 1.0:
                raise ValueError('Similarity scores must be between 0.0 and 1.0')
        return v


class ClassificationDecisionTrail(BaseModel):
    """Complete decision trail for a classification."""
    
    input_document: Dict[str, Any]
    selected_buckets: List[str] = Field(default_factory=list)
    evidence_trails: List[EvidenceTrail] = Field(default_factory=list)
    applied_rules: List[Dict[str, Any]] = Field(default_factory=list)
    rule_overrides: List[Dict[str, Any]] = Field(default_factory=list)
    model_response: Dict[str, Any] = Field(default_factory=dict)
    confidence_factors: Dict[str, Any] = Field(default_factory=dict)
    final_decision: Dict[str, Any] = Field(default_factory=dict)
    processing_time_ms: Optional[int] = None
    
    def get_complete_context(self) -> Dict[str, Any]:
        """Get complete context used in classification."""
        return {
            'buckets_used': len(self.selected_buckets),
            'evidence_documents': sum(len(trail.selected_documents) for trail in self.evidence_trails),
            'total_context_chunks': sum(len(trail.context_chunks) for trail in self.evidence_trails),
            'rules_evaluated': len(self.applied_rules),
            'rules_triggered': len(self.rule_overrides),
            'processing_time_ms': self.processing_time_ms
        }


class AuditLogEntry(FirestoreSerializable):
    """
    Comprehensive audit log entry for classification system events.
    
    Attributes:
        log_id: Unique audit log identifier
        event_type: Type of event being logged
        severity: Severity level of the event
        timestamp: When the event occurred
        user_id: ID of the user who triggered the event (if applicable)
        session_id: Session ID for grouping related events
        document_id: ID of the document involved (if applicable)
        classification_id: ID of the classification involved (if applicable)
        bucket_id: ID of the bucket involved (if applicable)
        rule_id: ID of the rule involved (if applicable)
        event_details: Detailed information about the event
        decision_trail: Complete decision trail for classification events
        system_context: System context at time of event
        error_details: Error details if event represents an error
        performance_metrics: Performance metrics for the operation
    """
    
    log_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: AuditEventType
    severity: AuditSeverity = Field(default=AuditSeverity.INFO)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    document_id: Optional[str] = None
    classification_id: Optional[str] = None
    bucket_id: Optional[str] = None
    rule_id: Optional[str] = None
    event_details: Dict[str, Any] = Field(default_factory=dict)
    decision_trail: Optional[ClassificationDecisionTrail] = None
    system_context: Dict[str, Any] = Field(default_factory=dict)
    error_details: Optional[Dict[str, Any]] = None
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('event_details')
    @classmethod
    def validate_event_details(cls, v):
        # Ensure event details are JSON serializable
        try:
            json.dumps(v)
        except (TypeError, ValueError) as e:
            raise ValueError(f'Event details must be JSON serializable: {e}')
        return v
    
    def add_performance_metric(self, metric_name: str, value: Union[int, float]) -> None:
        """Add a performance metric to the audit log."""
        self.performance_metrics[metric_name] = value
    
    def add_system_context(self, context_key: str, context_value: Any) -> None:
        """Add system context information."""
        self.system_context[context_key] = context_value
    
    def set_error_details(self, error: Exception, additional_context: Optional[Dict[str, Any]] = None) -> None:
        """Set error details from an exception."""
        self.severity = AuditSeverity.ERROR
        self.error_details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'additional_context': additional_context or {}
        }


class AuditLogger:
    """
    Comprehensive audit logging system for legal document classification.
    
    Provides methods to log all classification decisions, evidence trails,
    and system operations with complete traceability and compliance support.
    """
    
    def __init__(self, firestore_client: Optional[firestore.Client] = None):
        """
        Initialize the audit logger.
        
        Args:
            firestore_client: Firestore client instance
        """
        self.firestore_client = firestore_client or get_firestore_client()
        self.collection_name = FIRESTORE_COLLECTIONS['audit_logs']
        
        logger.info("Initialized AuditLogger")
    
    async def log_event(
        self,
        event_type: AuditEventType,
        event_details: Dict[str, Any],
        document_id: Optional[str] = None,
        classification_id: Optional[str] = None,
        bucket_id: Optional[str] = None,
        rule_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        decision_trail: Optional[ClassificationDecisionTrail] = None,
        error: Optional[Exception] = None
    ) -> str:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event to log
            event_details: Detailed information about the event
            document_id: ID of involved document
            classification_id: ID of involved classification
            bucket_id: ID of involved bucket
            rule_id: ID of involved rule
            user_id: ID of user who triggered the event
            session_id: Session ID for grouping events
            severity: Severity level of the event
            decision_trail: Complete decision trail for classification events
            error: Exception if this is an error event
            
        Returns:
            The log ID of the created audit entry
        """
        try:
            # Create audit log entry
            audit_entry = AuditLogEntry(
                event_type=event_type,
                severity=severity,
                user_id=user_id,
                session_id=session_id,
                document_id=document_id,
                classification_id=classification_id,
                bucket_id=bucket_id,
                rule_id=rule_id,
                event_details=event_details,
                decision_trail=decision_trail
            )
            
            # Add error details if provided
            if error:
                audit_entry.set_error_details(error, event_details)
            
            # Add system context
            audit_entry.add_system_context('firestore_collection', self.collection_name)
            audit_entry.add_system_context('logger_version', '1.0')
            
            # Store in Firestore
            doc_ref = self.firestore_client.collection(self.collection_name).document(audit_entry.log_id)
            doc_ref.set(audit_entry.to_firestore_dict())
            
            logger.debug(f"Logged audit event: {event_type.value} with ID {audit_entry.log_id}")
            return audit_entry.log_id
            
        except Exception as e:
            logger.error(f"Failed to log audit event {event_type.value}: {e}")
            # Don't raise exception to avoid breaking the main flow
            return ""
    
    async def log_classification_decision(
        self,
        classification_result: ClassificationResult,
        decision_trail: ClassificationDecisionTrail,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Log a complete classification decision with full evidence trail.
        
        Args:
            classification_result: The classification result
            decision_trail: Complete decision trail
            session_id: Session ID for grouping events
            user_id: User ID who initiated the classification
            
        Returns:
            The log ID of the created audit entry
        """
        event_details = {
            'classification_summary': {
                'label': classification_result.label.value,
                'confidence': classification_result.confidence,
                'routing_decision': classification_result.routing_decision.value,
                'model_version': classification_result.model_version
            },
            'evidence_summary': {
                'evidence_count': len(classification_result.evidence),
                'primary_bucket': classification_result.bucket_id,
                'rule_overrides_count': len(classification_result.rule_overrides)
            },
            'context_summary': decision_trail.get_complete_context()
        }
        
        return await self.log_event(
            event_type=AuditEventType.CLASSIFICATION_COMPLETED,
            event_details=event_details,
            document_id=classification_result.document_id,
            classification_id=classification_result.classification_id,
            bucket_id=classification_result.bucket_id,
            user_id=user_id,
            session_id=session_id,
            decision_trail=decision_trail
        )
    
    async def log_evidence_collection(
        self,
        document_id: str,
        classification_id: str,
        evidence_trails: List[EvidenceTrail],
        session_id: Optional[str] = None
    ) -> str:
        """
        Log evidence collection for a classification.
        
        Args:
            document_id: ID of the document being classified
            classification_id: ID of the classification
            evidence_trails: List of evidence trails collected
            session_id: Session ID for grouping events
            
        Returns:
            The log ID of the created audit entry
        """
        event_details = {
            'evidence_collection_summary': {
                'buckets_searched': len(evidence_trails),
                'total_documents_considered': sum(len(trail.selected_documents) for trail in evidence_trails),
                'total_context_chunks': sum(len(trail.context_chunks) for trail in evidence_trails),
                'average_similarity': sum(sum(trail.similarity_scores) / len(trail.similarity_scores) 
                                        if trail.similarity_scores else 0 for trail in evidence_trails) / len(evidence_trails) if evidence_trails else 0
            },
            'bucket_details': [
                {
                    'bucket_id': trail.bucket_id,
                    'bucket_name': trail.bucket_name,
                    'documents_selected': len(trail.selected_documents),
                    'context_chunks': len(trail.context_chunks),
                    'max_similarity': max(trail.similarity_scores) if trail.similarity_scores else 0
                }
                for trail in evidence_trails
            ]
        }
        
        return await self.log_event(
            event_type=AuditEventType.EVIDENCE_COLLECTED,
            event_details=event_details,
            document_id=document_id,
            classification_id=classification_id,
            session_id=session_id
        )
    
    async def log_rule_application(
        self,
        document_id: str,
        classification_id: str,
        rule: Rule,
        rule_result: Dict[str, Any],
        is_override: bool = False,
        session_id: Optional[str] = None
    ) -> str:
        """
        Log rule application or override.
        
        Args:
            document_id: ID of the document
            classification_id: ID of the classification
            rule: The rule that was applied
            rule_result: Result of rule evaluation
            is_override: Whether this was a rule override
            session_id: Session ID for grouping events
            
        Returns:
            The log ID of the created audit entry
        """
        event_type = AuditEventType.RULE_OVERRIDE if is_override else AuditEventType.RULE_APPLIED
        
        event_details = {
            'rule_details': {
                'rule_name': rule.name,
                'rule_description': rule.description,
                'severity_override': rule.severity_override.value,
                'priority': rule.priority,
                'conditions_count': len(rule.conditions)
            },
            'rule_evaluation': rule_result,
            'is_override': is_override
        }
        
        return await self.log_event(
            event_type=event_type,
            event_details=event_details,
            document_id=document_id,
            classification_id=classification_id,
            rule_id=rule.rule_id,
            session_id=session_id
        )
    
    async def get_audit_trail(
        self,
        document_id: Optional[str] = None,
        classification_id: Optional[str] = None,
        session_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_types: Optional[List[AuditEventType]] = None,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """
        Retrieve audit trail entries based on filters.
        
        Args:
            document_id: Filter by document ID
            classification_id: Filter by classification ID
            session_id: Filter by session ID
            start_time: Filter by start time
            end_time: Filter by end time
            event_types: Filter by event types
            limit: Maximum number of entries to return
            
        Returns:
            List of audit log entries
        """
        try:
            query = self.firestore_client.collection(self.collection_name)
            
            # Apply filters
            if document_id:
                query = query.where(filter=FieldFilter('document_id', '==', document_id))
            
            if classification_id:
                query = query.where(filter=FieldFilter('classification_id', '==', classification_id))
            
            if session_id:
                query = query.where(filter=FieldFilter('session_id', '==', session_id))
            
            if start_time:
                query = query.where(filter=FieldFilter('timestamp', '>=', start_time.isoformat()))
            
            if end_time:
                query = query.where(filter=FieldFilter('timestamp', '<=', end_time.isoformat()))
            
            if event_types:
                event_type_values = [et.value for et in event_types]
                query = query.where(filter=FieldFilter('event_type', 'in', event_type_values))
            
            # Order by timestamp descending and limit
            query = query.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
            
            # Execute query
            docs = query.stream()
            
            # Convert to AuditLogEntry objects
            audit_entries = []
            for doc in docs:
                doc_data = doc.to_dict()
                audit_entry = AuditLogEntry.from_firestore_dict(doc_data)
                audit_entries.append(audit_entry)
            
            logger.debug(f"Retrieved {len(audit_entries)} audit trail entries")
            return audit_entries
            
        except Exception as e:
            logger.error(f"Failed to retrieve audit trail: {e}")
            return []
    
    async def get_classification_audit_trail(
        self,
        classification_id: str
    ) -> Dict[str, Any]:
        """
        Get complete audit trail for a specific classification.
        
        Args:
            classification_id: ID of the classification
            
        Returns:
            Dictionary with complete audit trail and analysis
        """
        try:
            # Get all audit entries for this classification
            audit_entries = await self.get_audit_trail(
                classification_id=classification_id,
                limit=1000  # Get all entries
            )
            
            if not audit_entries:
                return {'error': 'No audit trail found for classification'}
            
            # Group entries by event type
            events_by_type = {}
            for entry in audit_entries:
                event_type = entry.event_type.value
                if event_type not in events_by_type:
                    events_by_type[event_type] = []
                events_by_type[event_type].append(entry)
            
            # Extract decision trail if available
            decision_trail = None
            for entry in audit_entries:
                if entry.decision_trail:
                    decision_trail = entry.decision_trail
                    break
            
            # Calculate timeline
            timeline = []
            for entry in sorted(audit_entries, key=lambda x: x.timestamp):
                timeline.append({
                    'timestamp': entry.timestamp.isoformat(),
                    'event_type': entry.event_type.value,
                    'severity': entry.severity.value,
                    'summary': self._get_event_summary(entry)
                })
            
            # Compile complete audit trail
            audit_trail = {
                'classification_id': classification_id,
                'total_events': len(audit_entries),
                'events_by_type': {k: len(v) for k, v in events_by_type.items()},
                'timeline': timeline,
                'decision_trail': decision_trail.model_dump() if decision_trail else None,
                'evidence_summary': self._extract_evidence_summary(audit_entries),
                'performance_summary': self._extract_performance_summary(audit_entries),
                'error_summary': self._extract_error_summary(audit_entries)
            }
            
            return audit_trail
            
        except Exception as e:
            logger.error(f"Failed to get classification audit trail: {e}")
            return {'error': str(e)}
    
    def _get_event_summary(self, entry: AuditLogEntry) -> str:
        """Get a human-readable summary of an audit event."""
        summaries = {
            AuditEventType.CLASSIFICATION_STARTED: "Classification process initiated",
            AuditEventType.CLASSIFICATION_COMPLETED: f"Classification completed: {entry.event_details.get('classification_summary', {}).get('label', 'Unknown')}",
            AuditEventType.CONTEXT_RETRIEVED: f"Context retrieved from {entry.event_details.get('context_summary', {}).get('buckets_used', 0)} buckets",
            AuditEventType.EVIDENCE_COLLECTED: f"Evidence collected: {entry.event_details.get('evidence_collection_summary', {}).get('total_documents_considered', 0)} documents",
            AuditEventType.RULE_APPLIED: f"Rule applied: {entry.event_details.get('rule_details', {}).get('rule_name', 'Unknown')}",
            AuditEventType.RULE_OVERRIDE: f"Rule override: {entry.event_details.get('rule_details', {}).get('rule_name', 'Unknown')}",
            AuditEventType.RESULT_STORED: "Classification result stored",
            AuditEventType.CLASSIFICATION_FAILED: f"Classification failed: {entry.error_details.get('error_message', 'Unknown error') if entry.error_details else 'Unknown error'}"
        }
        
        return summaries.get(entry.event_type, f"Event: {entry.event_type.value}")
    
    def _extract_evidence_summary(self, audit_entries: List[AuditLogEntry]) -> Dict[str, Any]:
        """Extract evidence summary from audit entries."""
        evidence_events = [e for e in audit_entries if e.event_type == AuditEventType.EVIDENCE_COLLECTED]
        
        if not evidence_events:
            return {}
        
        # Get the most recent evidence collection event
        latest_evidence = max(evidence_events, key=lambda x: x.timestamp)
        return latest_evidence.event_details.get('evidence_collection_summary', {})
    
    def _extract_performance_summary(self, audit_entries: List[AuditLogEntry]) -> Dict[str, Any]:
        """Extract performance summary from audit entries."""
        performance_metrics = {}
        
        for entry in audit_entries:
            if entry.performance_metrics:
                for metric, value in entry.performance_metrics.items():
                    if metric not in performance_metrics:
                        performance_metrics[metric] = []
                    performance_metrics[metric].append(value)
        
        # Calculate aggregated metrics
        aggregated_metrics = {}
        for metric, values in performance_metrics.items():
            aggregated_metrics[metric] = {
                'count': len(values),
                'average': sum(values) / len(values),
                'min': min(values),
                'max': max(values)
            }
        
        return aggregated_metrics
    
    def _extract_error_summary(self, audit_entries: List[AuditLogEntry]) -> Dict[str, Any]:
        """Extract error summary from audit entries."""
        error_entries = [e for e in audit_entries if e.severity in [AuditSeverity.ERROR, AuditSeverity.CRITICAL]]
        
        if not error_entries:
            return {'error_count': 0}
        
        error_types = {}
        for entry in error_entries:
            if entry.error_details:
                error_type = entry.error_details.get('error_type', 'Unknown')
                if error_type not in error_types:
                    error_types[error_type] = 0
                error_types[error_type] += 1
        
        return {
            'error_count': len(error_entries),
            'error_types': error_types,
            'latest_error': error_entries[0].error_details if error_entries else None
        }


# Export main classes
__all__ = [
    'AuditEventType',
    'AuditSeverity', 
    'EvidenceTrail',
    'ClassificationDecisionTrail',
    'AuditLogEntry',
    'AuditLogger'
]