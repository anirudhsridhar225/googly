"""
Legal Document Severity Classification System - Core Data Models

This module contains Pydantic models for the legal document classification system,
including Document, Bucket, Rule, and ClassificationResult classes with Firestore
serialization and validation logic.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from uuid import uuid4, UUID
from enum import Enum
import json

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Annotated


class SeverityLevel(str, Enum):
    """Enumeration for document severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DocumentType(str, Enum):
    """Enumeration for document types."""
    REFERENCE = "reference"
    CLASSIFICATION = "classification"


class RoutingDecision(str, Enum):
    """Enumeration for routing decisions based on confidence."""
    AUTO_ACCEPT = "auto_accept"
    HUMAN_REVIEW = "human_review"
    HUMAN_TRIAGE = "human_triage"


class RuleConditionOperator(str, Enum):
    """Enumeration for rule condition operators."""
    CONTAINS = "contains"
    REGEX_MATCH = "regex_match"
    WORD_COUNT_GT = "word_count_gt"
    WORD_COUNT_LT = "word_count_lt"
    AND = "and"
    OR = "or"
    NOT = "not"


class FirestoreSerializable(BaseModel):
    """Base class for models that can be serialized to/from Firestore."""
    
    def to_firestore_dict(self) -> Dict[str, Any]:
        """
        Convert the model to a dictionary suitable for Firestore storage.
        
        Returns:
            Dict[str, Any]: Firestore-compatible dictionary
        """
        data = self.model_dump()
        
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, UUID):
                data[key] = str(value)
        
        return data
    
    @classmethod
    def from_firestore_dict(cls, data: Dict[str, Any]) -> "FirestoreSerializable":
        """
        Create a model instance from a Firestore dictionary.
        
        Args:
            data: Dictionary from Firestore document
            
        Returns:
            Model instance
        """
        # Convert ISO strings back to datetime objects
        for key, value in data.items():
            if isinstance(value, str) and key.endswith(('_at', '_date')):
                try:
                    data[key] = datetime.fromisoformat(value)
                except ValueError:
                    pass  # Keep as string if not a valid ISO format
        
        return cls(**data)


class DocumentMetadata(BaseModel):
    """Metadata for documents."""
    filename: str
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    file_size: Optional[int] = None
    content_hash: Optional[str] = None
    uploader_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v):
        if not v or not v.strip():
            raise ValueError('Filename cannot be empty')
        return v.strip()


class Document(FirestoreSerializable):
    """
    Core document model for both reference and classification documents.
    
    Attributes:
        id: Unique document identifier
        text: Extracted document text content
        embedding: Document embedding vector from Gemini
        metadata: Document metadata including filename, upload date, etc.
        created_at: Document creation timestamp
        document_type: Type of document (reference or classification)
        severity_label: Severity label for reference documents
    """
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str = Field(..., min_length=1, max_length=1000000)
    embedding: List[float] = Field(..., min_length=1, max_length=10000)
    metadata: DocumentMetadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    document_type: DocumentType
    severity_label: Optional[SeverityLevel] = None
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError('Document text cannot be empty')
        return v.strip()
    
    @field_validator('embedding')
    @classmethod
    def validate_embedding(cls, v):
        if not v:
            raise ValueError('Embedding vector cannot be empty')
        
        # Check for valid float values
        for i, val in enumerate(v):
            if not isinstance(val, (int, float)) or not (-1.0 <= val <= 1.0):
                raise ValueError(f'Embedding value at index {i} must be a float between -1.0 and 1.0')
        
        return v
    
    @model_validator(mode='before')
    @classmethod
    def validate_severity_label_for_reference(cls, values):
        if isinstance(values, dict):
            document_type = values.get('document_type')
            severity_label = values.get('severity_label')
            
            if document_type == DocumentType.REFERENCE and severity_label is None:
                raise ValueError('Reference documents must have a severity label')
            
            if document_type == DocumentType.CLASSIFICATION and severity_label is not None:
                raise ValueError('Classification documents should not have a severity label')
        
        return values


class Bucket(FirestoreSerializable):
    """
    Semantic bucket model for grouping similar documents.
    
    Attributes:
        bucket_id: Unique bucket identifier
        bucket_name: Human-readable bucket name
        centroid_embedding: Centroid embedding vector for the bucket
        document_ids: List of document IDs in this bucket
        created_at: Bucket creation timestamp
        updated_at: Last update timestamp
        document_count: Number of documents in the bucket
        description: Optional description of the bucket's semantic meaning
    """
    
    bucket_id: str = Field(default_factory=lambda: str(uuid4()))
    bucket_name: str = Field(..., min_length=1, max_length=100)
    centroid_embedding: List[float] = Field(..., min_length=1, max_length=10000)
    document_ids: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    document_count: int = Field(default=0, ge=0)
    description: Optional[str] = Field(None, max_length=500)
    
    @field_validator('bucket_name')
    @classmethod
    def validate_bucket_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Bucket name cannot be empty')
        return v.strip()
    
    @field_validator('centroid_embedding')
    @classmethod
    def validate_centroid_embedding(cls, v):
        if not v:
            raise ValueError('Centroid embedding vector cannot be empty')
        
        # Check for valid float values
        for i, val in enumerate(v):
            if not isinstance(val, (int, float)) or not (-1.0 <= val <= 1.0):
                raise ValueError(f'Centroid embedding value at index {i} must be a float between -1.0 and 1.0')
        
        return v
    
    @model_validator(mode='before')
    @classmethod
    def validate_document_count_consistency(cls, values):
        if isinstance(values, dict):
            document_ids = values.get('document_ids', [])
            document_count = values.get('document_count', 0)
            
            if len(document_ids) != document_count:
                values['document_count'] = len(document_ids)
        
        return values


class RuleCondition(BaseModel):
    """
    Individual rule condition for document evaluation.
    
    Attributes:
        operator: The condition operator (contains, regex_match, etc.)
        field: The document field to evaluate (text, metadata.filename, etc.)
        value: The value to compare against
        case_sensitive: Whether string comparisons should be case sensitive
    """
    
    operator: RuleConditionOperator
    field: str = Field(..., min_length=1)
    value: Union[str, int, float, bool]
    case_sensitive: bool = Field(default=False)
    
    @field_validator('field')
    @classmethod
    def validate_field(cls, v):
        allowed_fields = ['text', 'metadata.filename', 'metadata.tags', 'document_type']
        if v not in allowed_fields:
            raise ValueError(f'Field must be one of: {allowed_fields}')
        return v


class Rule(FirestoreSerializable):
    """
    Deterministic rule model for classification overrides.
    
    Attributes:
        rule_id: Unique rule identifier
        name: Human-readable rule name
        description: Rule description
        conditions: List of conditions that must be met
        condition_logic: Logic for combining conditions (AND/OR)
        severity_override: Severity level to apply when rule matches
        priority: Rule priority for conflict resolution (higher = more priority)
        active: Whether the rule is currently active
        created_at: Rule creation timestamp
        updated_at: Last update timestamp
        created_by: User who created the rule
    """
    
    rule_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    conditions: List[RuleCondition] = Field(..., min_length=1)
    condition_logic: RuleConditionOperator = Field(default=RuleConditionOperator.AND)
    severity_override: SeverityLevel
    priority: int = Field(default=1, ge=1, le=100)
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Rule name cannot be empty')
        return v.strip()
    
    @field_validator('condition_logic')
    @classmethod
    def validate_condition_logic(cls, v):
        if v not in [RuleConditionOperator.AND, RuleConditionOperator.OR]:
            raise ValueError('Condition logic must be AND or OR')
        return v


class ClassificationEvidence(BaseModel):
    """
    Evidence used in classification decision.
    
    Attributes:
        document_id: ID of the evidence document
        chunk_text: Relevant text chunk from the document
        similarity_score: Similarity score to the query document
        bucket_id: ID of the bucket this evidence came from
    """
    
    document_id: str
    chunk_text: str = Field(..., min_length=1, max_length=5000)
    similarity_score: Annotated[float, Field(ge=0.0, le=1.0)]
    bucket_id: str
    
    @field_validator('chunk_text')
    @classmethod
    def validate_chunk_text(cls, v):
        if not v or not v.strip():
            raise ValueError('Chunk text cannot be empty')
        return v.strip()


class ClassificationResult(FirestoreSerializable):
    """
    Result of document classification.
    
    Attributes:
        classification_id: Unique classification identifier
        document_id: ID of the classified document
        label: Predicted severity label
        confidence: Model confidence score
        rationale: Human-readable explanation of the classification
        evidence: List of evidence used in classification
        bucket_id: Primary bucket used for classification
        rule_overrides: List of rule IDs that were applied
        routing_decision: Routing decision based on confidence
        model_version: Version of the classification model used
        created_at: Classification timestamp
        human_reviewed: Whether this classification was human reviewed
        human_reviewer_id: ID of the human reviewer (if applicable)
        final_label: Final label after human review (if different from original)
    """
    
    classification_id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    label: SeverityLevel
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    rationale: str = Field(..., min_length=1, max_length=2000)
    evidence: List[ClassificationEvidence] = Field(default_factory=list)
    bucket_id: Optional[str] = None
    rule_overrides: List[str] = Field(default_factory=list)
    routing_decision: RoutingDecision
    model_version: str = Field(default="gemini-1.0")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    human_reviewed: bool = Field(default=False)
    human_reviewer_id: Optional[str] = None
    final_label: Optional[SeverityLevel] = None
    confidence_warning: Optional[Dict[str, Any]] = None
    
    @field_validator('rationale')
    @classmethod
    def validate_rationale(cls, v):
        if not v or not v.strip():
            raise ValueError('Rationale cannot be empty')
        return v.strip()
    
    @model_validator(mode='before')
    @classmethod
    def validate_human_review_fields(cls, values):
        if isinstance(values, dict):
            human_reviewed = values.get('human_reviewed', False)
            human_reviewer_id = values.get('human_reviewer_id')
            final_label = values.get('final_label')
            
            if human_reviewed and not human_reviewer_id:
                raise ValueError('Human reviewer ID is required when human_reviewed is True')
            
            if not human_reviewed and (human_reviewer_id or final_label):
                raise ValueError('Human review fields should only be set when human_reviewed is True')
        
        return values


class ContextBlock(BaseModel):
    """
    Context block for classification containing bucket info and retrieved chunks.
    
    Attributes:
        bucket_info: Information about the selected bucket
        retrieved_chunks: List of relevant document chunks
        applicable_rules: List of rules that apply to this context
        total_similarity_score: Aggregate similarity score for the context
    """
    
    bucket_info: Dict[str, Any]
    retrieved_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    applicable_rules: List[Rule] = Field(default_factory=list)
    total_similarity_score: Annotated[float, Field(ge=0.0, le=1.0)] = Field(default=0.0)
    
    @field_validator('bucket_info')
    @classmethod
    def validate_bucket_info(cls, v):
        required_fields = ['bucket_id', 'bucket_name']
        for field in required_fields:
            if field not in v:
                raise ValueError(f'Bucket info must contain {field}')
        return v


# Collection names for Firestore
FIRESTORE_COLLECTIONS = {
    'documents': 'legal_documents',
    'buckets': 'semantic_buckets',
    'rules': 'classification_rules',
    'classifications': 'document_classifications',
    'review_queue': 'human_review_queue',
    'audit_logs': 'classification_audit_logs'
}


# Export all models and enums
__all__ = [
    'SeverityLevel',
    'DocumentType', 
    'RoutingDecision',
    'RuleConditionOperator',
    'FirestoreSerializable',
    'DocumentMetadata',
    'Document',
    'Bucket',
    'RuleCondition',
    'Rule',
    'ClassificationEvidence',
    'ClassificationResult',
    'ContextBlock',
    'FIRESTORE_COLLECTIONS'
]