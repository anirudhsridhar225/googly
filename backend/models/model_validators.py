"""
Model Validation Utilities

This module provides additional validation functions and utilities for the
legal document classification system data models.
"""

import re
import hashlib
from typing import List, Dict, Any, Optional, Union
import numpy as np
from datetime import datetime

from models.legal_models import (
    Document, Bucket, Rule, ClassificationResult, 
    SeverityLevel, DocumentType, RuleConditionOperator,
    DocumentMetadata, RuleCondition
)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class EmbeddingValidator:
    """Validator for embedding vectors."""
    
    @staticmethod
    def validate_embedding_dimensions(embedding: List[float], expected_dim: int = 768) -> bool:
        """
        Validate embedding vector dimensions.
        
        Args:
            embedding: Embedding vector to validate
            expected_dim: Expected dimension count
            
        Returns:
            bool: True if valid, False otherwise
            
        Raises:
            ValidationError: If embedding is invalid
        """
        if not embedding:
            raise ValidationError("Embedding vector cannot be empty")
        
        if len(embedding) != expected_dim:
            raise ValidationError(f"Embedding must have {expected_dim} dimensions, got {len(embedding)}")
        
        return True
    
    @staticmethod
    def validate_embedding_values(embedding: List[float]) -> bool:
        """
        Validate embedding vector values are within expected range.
        
        Args:
            embedding: Embedding vector to validate
            
        Returns:
            bool: True if valid, False otherwise
            
        Raises:
            ValidationError: If embedding values are invalid
        """
        if not embedding:
            raise ValidationError("Embedding vector cannot be empty")
        
        for i, value in enumerate(embedding):
            if not isinstance(value, (int, float)):
                raise ValidationError(f"Embedding value at index {i} must be numeric, got {type(value)}")
            
            if not (-1.0 <= value <= 1.0):
                raise ValidationError(f"Embedding value at index {i} must be between -1.0 and 1.0, got {value}")
        
        return True
    
    @staticmethod
    def validate_embedding_similarity(embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate and validate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            float: Cosine similarity score
            
        Raises:
            ValidationError: If embeddings are incompatible
        """
        if len(embedding1) != len(embedding2):
            raise ValidationError("Embeddings must have the same dimensions for similarity calculation")
        
        # Convert to numpy arrays for calculation
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            raise ValidationError("Cannot calculate similarity for zero vectors")
        
        similarity = dot_product / (norm1 * norm2)
        return float(similarity)


class DocumentValidator:
    """Validator for Document models."""
    
    @staticmethod
    def validate_document_text(text: str, min_length: int = 10, max_length: int = 1000000) -> bool:
        """
        Validate document text content.
        
        Args:
            text: Document text to validate
            min_length: Minimum text length
            max_length: Maximum text length
            
        Returns:
            bool: True if valid, False otherwise
            
        Raises:
            ValidationError: If text is invalid
        """
        if not text or not text.strip():
            raise ValidationError("Document text cannot be empty")
        
        text_length = len(text.strip())
        if text_length < min_length:
            raise ValidationError(f"Document text must be at least {min_length} characters, got {text_length}")
        
        if text_length > max_length:
            raise ValidationError(f"Document text must be at most {max_length} characters, got {text_length}")
        
        return True
    
    @staticmethod
    def validate_document_metadata(metadata: DocumentMetadata) -> bool:
        """
        Validate document metadata.
        
        Args:
            metadata: Document metadata to validate
            
        Returns:
            bool: True if valid, False otherwise
            
        Raises:
            ValidationError: If metadata is invalid
        """
        # Validate filename
        if not metadata.filename or not metadata.filename.strip():
            raise ValidationError("Filename cannot be empty")
        
        # Check for valid filename characters
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        if any(char in metadata.filename for char in invalid_chars):
            raise ValidationError(f"Filename contains invalid characters: {invalid_chars}")
        
        # Validate file size if provided
        if metadata.file_size is not None and metadata.file_size < 0:
            raise ValidationError("File size cannot be negative")
        
        # Validate upload date
        if metadata.upload_date > datetime.utcnow():
            raise ValidationError("Upload date cannot be in the future")
        
        return True
    
    @staticmethod
    def generate_content_hash(text: str) -> str:
        """
        Generate a content hash for duplicate detection.
        
        Args:
            text: Document text content
            
        Returns:
            str: SHA-256 hash of the content
        """
        # Normalize text for consistent hashing
        normalized_text = text.strip().lower()
        return hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()


class RuleValidator:
    """Validator for Rule models."""
    
    @staticmethod
    def validate_rule_condition(condition: RuleCondition) -> bool:
        """
        Validate a rule condition.
        
        Args:
            condition: Rule condition to validate
            
        Returns:
            bool: True if valid, False otherwise
            
        Raises:
            ValidationError: If condition is invalid
        """
        # Validate operator-specific requirements
        if condition.operator == RuleConditionOperator.REGEX_MATCH:
            try:
                re.compile(str(condition.value))
            except re.error as e:
                raise ValidationError(f"Invalid regex pattern: {e}")
        
        elif condition.operator in [RuleConditionOperator.WORD_COUNT_GT, RuleConditionOperator.WORD_COUNT_LT]:
            if not isinstance(condition.value, int) or condition.value < 0:
                raise ValidationError("Word count conditions require non-negative integer values")
        
        elif condition.operator == RuleConditionOperator.CONTAINS:
            if not isinstance(condition.value, str) or not condition.value.strip():
                raise ValidationError("Contains condition requires non-empty string value")
        
        return True
    
    @staticmethod
    def validate_rule_priority(priority: int, existing_rules: List[Rule]) -> bool:
        """
        Validate rule priority against existing rules.
        
        Args:
            priority: Priority to validate
            existing_rules: List of existing rules
            
        Returns:
            bool: True if valid, False otherwise
            
        Raises:
            ValidationError: If priority conflicts exist
        """
        if priority < 1 or priority > 100:
            raise ValidationError("Rule priority must be between 1 and 100")
        
        # Check for priority conflicts with same severity
        # (This is a business rule - multiple rules can have same priority but should be documented)
        high_priority_count = sum(1 for rule in existing_rules if rule.priority >= 90 and rule.active)
        if priority >= 90 and high_priority_count >= 5:
            raise ValidationError("Too many high-priority rules (>=90). Consider consolidating rules.")
        
        return True


class ClassificationValidator:
    """Validator for ClassificationResult models."""
    
    @staticmethod
    def validate_confidence_score(confidence: float, routing_decision: str) -> bool:
        """
        Validate confidence score against routing decision.
        
        Args:
            confidence: Confidence score to validate
            routing_decision: Routing decision made
            
        Returns:
            bool: True if valid, False otherwise
            
        Raises:
            ValidationError: If confidence and routing are inconsistent
        """
        if not (0.0 <= confidence <= 1.0):
            raise ValidationError("Confidence score must be between 0.0 and 1.0")
        
        # Validate consistency with routing decision
        if routing_decision == "auto_accept" and confidence < 0.85:
            raise ValidationError("Auto-accept routing requires confidence >= 0.85")
        
        elif routing_decision == "human_review" and not (0.60 <= confidence < 0.85):
            raise ValidationError("Human review routing requires confidence between 0.60 and 0.85")
        
        elif routing_decision == "human_triage" and confidence >= 0.60:
            raise ValidationError("Human triage routing requires confidence < 0.60")
        
        return True
    
    @staticmethod
    def validate_evidence_consistency(evidence: List[Dict[str, Any]], bucket_id: Optional[str]) -> bool:
        """
        Validate evidence consistency with bucket selection.
        
        Args:
            evidence: List of evidence items
            bucket_id: Selected bucket ID
            
        Returns:
            bool: True if valid, False otherwise
            
        Raises:
            ValidationError: If evidence is inconsistent
        """
        if not evidence and bucket_id:
            raise ValidationError("Evidence must be provided when bucket is selected")
        
        if evidence and not bucket_id:
            raise ValidationError("Bucket ID must be provided when evidence exists")
        
        # Validate evidence items
        for i, item in enumerate(evidence):
            required_fields = ['document_id', 'chunk_text', 'similarity_score', 'bucket_id']
            for field in required_fields:
                if field not in item:
                    raise ValidationError(f"Evidence item {i} missing required field: {field}")
            
            # Validate similarity score
            if not (0.0 <= item['similarity_score'] <= 1.0):
                raise ValidationError(f"Evidence item {i} similarity score must be between 0.0 and 1.0")
            
            # Validate bucket consistency
            if bucket_id and item['bucket_id'] != bucket_id:
                raise ValidationError(f"Evidence item {i} bucket_id inconsistent with classification bucket_id")
        
        return True


class BucketValidator:
    """Validator for Bucket models."""
    
    @staticmethod
    def validate_bucket_consistency(bucket: Bucket) -> bool:
        """
        Validate internal consistency of bucket data.
        
        Args:
            bucket: Bucket to validate
            
        Returns:
            bool: True if valid, False otherwise
            
        Raises:
            ValidationError: If bucket data is inconsistent
        """
        # Validate document count consistency
        if len(bucket.document_ids) != bucket.document_count:
            raise ValidationError(f"Document count mismatch: {bucket.document_count} vs {len(bucket.document_ids)}")
        
        # Validate unique document IDs
        if len(set(bucket.document_ids)) != len(bucket.document_ids):
            raise ValidationError("Bucket contains duplicate document IDs")
        
        # Validate timestamps
        if bucket.updated_at < bucket.created_at:
            raise ValidationError("Updated timestamp cannot be before created timestamp")
        
        return True
    
    @staticmethod
    def validate_centroid_calculation(documents: List[Document], centroid: List[float]) -> bool:
        """
        Validate that centroid is correctly calculated from documents.
        
        Args:
            documents: List of documents in the bucket
            centroid: Calculated centroid embedding
            
        Returns:
            bool: True if valid, False otherwise
            
        Raises:
            ValidationError: If centroid calculation is incorrect
        """
        if not documents:
            raise ValidationError("Cannot validate centroid for empty document list")
        
        # Calculate expected centroid
        embeddings = np.array([doc.embedding for doc in documents])
        expected_centroid = np.mean(embeddings, axis=0)
        
        # Compare with provided centroid (allow small floating point differences)
        centroid_array = np.array(centroid)
        if not np.allclose(expected_centroid, centroid_array, rtol=1e-5):
            raise ValidationError("Provided centroid does not match calculated centroid from documents")
        
        return True


def validate_model_instance(instance: Union[Document, Bucket, Rule, ClassificationResult]) -> bool:
    """
    Comprehensive validation for any model instance.
    
    Args:
        instance: Model instance to validate
        
    Returns:
        bool: True if valid, False otherwise
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        # Run Pydantic validation first
        instance.dict()
        
        # Run additional custom validations based on model type
        if isinstance(instance, Document):
            DocumentValidator.validate_document_text(instance.text)
            DocumentValidator.validate_document_metadata(instance.metadata)
            EmbeddingValidator.validate_embedding_values(instance.embedding)
        
        elif isinstance(instance, Bucket):
            BucketValidator.validate_bucket_consistency(instance)
            EmbeddingValidator.validate_embedding_values(instance.centroid_embedding)
        
        elif isinstance(instance, Rule):
            for condition in instance.conditions:
                RuleValidator.validate_rule_condition(condition)
        
        elif isinstance(instance, ClassificationResult):
            ClassificationValidator.validate_confidence_score(instance.confidence, instance.routing_decision)
            ClassificationValidator.validate_evidence_consistency(
                [evidence.dict() for evidence in instance.evidence], 
                instance.bucket_id
            )
        
        return True
        
    except Exception as e:
        raise ValidationError(f"Model validation failed: {e}")


# Export validation functions
__all__ = [
    'ValidationError',
    'EmbeddingValidator',
    'DocumentValidator', 
    'RuleValidator',
    'ClassificationValidator',
    'BucketValidator',
    'validate_model_instance'
]