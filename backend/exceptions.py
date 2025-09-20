"""
Custom Exception Classes for Legal Document Severity Classification System.

This module defines custom exception classes for different error types,
providing structured error handling throughout the application.
"""

import logging
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels for logging and monitoring."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BaseCustomException(Exception):
    """
    Base class for all custom exceptions in the system.
    
    Provides common functionality for error tracking, logging, and monitoring.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.context = context or {}
        self.cause = cause
        
        # Log the exception based on severity
        self._log_exception()
    
    def _log_exception(self):
        """Log the exception based on its severity."""
        log_data = {
            "error_code": self.error_code,
            "message": self.message,
            "severity": self.severity.value,
            "context": self.context
        }
        
        if self.cause:
            log_data["cause"] = str(self.cause)
        
        if self.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error: {self.message}", extra=log_data, exc_info=self.cause)
        elif self.severity == ErrorSeverity.HIGH:
            logger.error(f"High severity error: {self.message}", extra=log_data, exc_info=self.cause)
        elif self.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity error: {self.message}", extra=log_data)
        else:
            logger.info(f"Low severity error: {self.message}", extra=log_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "severity": self.severity.value,
            "context": self.context
        }


# Document Processing Exceptions
class DocumentProcessingException(BaseCustomException):
    """Base exception for document processing errors."""
    
    def __init__(self, message: str, document_id: Optional[str] = None, **kwargs):
        super().__init__(message, "DOCUMENT_PROCESSING_ERROR", **kwargs)
        if document_id:
            self.context["document_id"] = document_id


class UnsupportedDocumentFormatException(DocumentProcessingException):
    """Raised when document format is not supported."""
    
    def __init__(self, format_type: str, supported_formats: List[str], **kwargs):
        message = f"Unsupported document format: {format_type}. Supported formats: {', '.join(supported_formats)}"
        super().__init__(message, **kwargs)
        self.context.update({
            "format_type": format_type,
            "supported_formats": supported_formats
        })
        self.error_code = "UNSUPPORTED_FORMAT"


class DocumentTooLargeException(DocumentProcessingException):
    """Raised when document exceeds size limits."""
    
    def __init__(self, file_size: int, max_size: int, **kwargs):
        message = f"Document size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)"
        super().__init__(message, **kwargs)
        self.context.update({
            "file_size": file_size,
            "max_size": max_size
        })
        self.error_code = "FILE_TOO_LARGE"


class TextExtractionException(DocumentProcessingException):
    """Raised when text extraction fails."""
    
    def __init__(self, message: str, extraction_method: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        if extraction_method:
            self.context["extraction_method"] = extraction_method
        self.error_code = "TEXT_EXTRACTION_ERROR"


# Gemini API Exceptions
class GeminiAPIException(BaseCustomException):
    """Base exception for Gemini API errors."""
    
    def __init__(self, message: str, api_endpoint: Optional[str] = None, **kwargs):
        super().__init__(message, "GEMINI_API_ERROR", **kwargs)
        if api_endpoint:
            self.context["api_endpoint"] = api_endpoint


class GeminiRateLimitException(GeminiAPIException):
    """Raised when Gemini API rate limit is exceeded."""
    
    def __init__(self, retry_after: Optional[int] = None, **kwargs):
        message = "Gemini API rate limit exceeded"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(message, **kwargs)
        self.error_code = "RATE_LIMITED"
        if retry_after:
            self.context["retry_after"] = retry_after


class GeminiServiceUnavailableException(GeminiAPIException):
    """Raised when Gemini API service is unavailable."""
    
    def __init__(self, **kwargs):
        super().__init__("Gemini API service is currently unavailable", **kwargs)
        self.error_code = "SERVICE_UNAVAILABLE"
        self.severity = ErrorSeverity.HIGH


class GeminiResponseParsingException(GeminiAPIException):
    """Raised when Gemini API response cannot be parsed."""
    
    def __init__(self, response_content: str, expected_format: str, **kwargs):
        message = f"Failed to parse Gemini API response. Expected format: {expected_format}"
        super().__init__(message, **kwargs)
        self.context.update({
            "response_content": response_content[:500],  # Truncate for logging
            "expected_format": expected_format
        })
        self.error_code = "RESPONSE_PARSING_ERROR"


# Firestore Exceptions
class FirestoreException(BaseCustomException):
    """Base exception for Firestore errors."""
    
    def __init__(self, message: str, collection: Optional[str] = None, document_id: Optional[str] = None, **kwargs):
        super().__init__(message, "FIRESTORE_ERROR", **kwargs)
        if collection:
            self.context["collection"] = collection
        if document_id:
            self.context["document_id"] = document_id


class FirestoreConnectionException(FirestoreException):
    """Raised when Firestore connection fails."""
    
    def __init__(self, **kwargs):
        super().__init__("Failed to connect to Firestore", **kwargs)
        self.error_code = "FIRESTORE_CONNECTION_ERROR"
        self.severity = ErrorSeverity.HIGH


class FirestoreTransactionException(FirestoreException):
    """Raised when Firestore transaction fails."""
    
    def __init__(self, operation: str, **kwargs):
        message = f"Firestore transaction failed for operation: {operation}"
        super().__init__(message, **kwargs)
        self.context["operation"] = operation
        self.error_code = "FIRESTORE_TRANSACTION_ERROR"


class DocumentNotFoundException(FirestoreException):
    """Raised when a document is not found in Firestore."""
    
    def __init__(self, collection: str, document_id: str, **kwargs):
        message = f"Document not found: {document_id} in collection {collection}"
        super().__init__(message, collection=collection, document_id=document_id, **kwargs)
        self.error_code = "NOT_FOUND"
        self.severity = ErrorSeverity.LOW


# Classification Exceptions
class ClassificationException(BaseCustomException):
    """Base exception for classification errors."""
    
    def __init__(self, message: str, document_id: Optional[str] = None, **kwargs):
        super().__init__(message, "CLASSIFICATION_ERROR", **kwargs)
        if document_id:
            self.context["document_id"] = document_id


class InsufficientContextException(ClassificationException):
    """Raised when insufficient context is available for classification."""
    
    def __init__(self, available_buckets: int, required_buckets: int, **kwargs):
        message = f"Insufficient context for classification. Available buckets: {available_buckets}, Required: {required_buckets}"
        super().__init__(message, **kwargs)
        self.context.update({
            "available_buckets": available_buckets,
            "required_buckets": required_buckets
        })
        self.error_code = "INSUFFICIENT_CONTEXT"


class LowConfidenceClassificationException(ClassificationException):
    """Raised when classification confidence is below acceptable thresholds."""
    
    def __init__(self, confidence: float, threshold: float, **kwargs):
        message = f"Classification confidence ({confidence:.3f}) below threshold ({threshold:.3f})"
        super().__init__(message, **kwargs)
        self.context.update({
            "confidence": confidence,
            "threshold": threshold
        })
        self.error_code = "INSUFFICIENT_CONFIDENCE"
        self.severity = ErrorSeverity.LOW  # This is more of a warning than an error


# Bucket Management Exceptions
class BucketException(BaseCustomException):
    """Base exception for bucket management errors."""
    
    def __init__(self, message: str, bucket_id: Optional[str] = None, **kwargs):
        super().__init__(message, "BUCKET_ERROR", **kwargs)
        if bucket_id:
            self.context["bucket_id"] = bucket_id


class BucketNotFoundException(BucketException):
    """Raised when a bucket is not found."""
    
    def __init__(self, bucket_id: str, **kwargs):
        message = f"Bucket not found: {bucket_id}"
        super().__init__(message, bucket_id=bucket_id, **kwargs)
        self.error_code = "BUCKET_NOT_FOUND"


class ClusteringException(BucketException):
    """Raised when document clustering fails."""
    
    def __init__(self, message: str, document_count: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        if document_count:
            self.context["document_count"] = document_count
        self.error_code = "CLUSTERING_ERROR"


# Rule Engine Exceptions
class RuleEngineException(BaseCustomException):
    """Base exception for rule engine errors."""
    
    def __init__(self, message: str, rule_id: Optional[str] = None, **kwargs):
        super().__init__(message, "RULE_ENGINE_ERROR", **kwargs)
        if rule_id:
            self.context["rule_id"] = rule_id


class RuleEvaluationException(RuleEngineException):
    """Raised when rule evaluation fails."""
    
    def __init__(self, rule_id: str, condition: str, **kwargs):
        message = f"Failed to evaluate rule {rule_id}: {condition}"
        super().__init__(message, rule_id=rule_id, **kwargs)
        self.context["condition"] = condition
        self.error_code = "RULE_EVALUATION_ERROR"


class RuleConflictException(RuleEngineException):
    """Raised when multiple rules conflict."""
    
    def __init__(self, conflicting_rules: List[str], **kwargs):
        message = f"Rule conflict detected between rules: {', '.join(conflicting_rules)}"
        super().__init__(message, **kwargs)
        self.context["conflicting_rules"] = conflicting_rules
        self.error_code = "RULE_CONFLICT"


# Configuration Exceptions
class ConfigurationException(BaseCustomException):
    """Base exception for configuration errors."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(message, "CONFIGURATION_ERROR", **kwargs)
        if config_key:
            self.context["config_key"] = config_key
        self.severity = ErrorSeverity.CRITICAL  # Config errors are critical


class MissingConfigurationException(ConfigurationException):
    """Raised when required configuration is missing."""
    
    def __init__(self, config_key: str, **kwargs):
        message = f"Missing required configuration: {config_key}"
        super().__init__(message, config_key=config_key, **kwargs)
        self.error_code = "MISSING_CONFIGURATION"


class InvalidConfigurationException(ConfigurationException):
    """Raised when configuration value is invalid."""
    
    def __init__(self, config_key: str, value: Any, expected_type: str, **kwargs):
        message = f"Invalid configuration for {config_key}: expected {expected_type}, got {type(value).__name__}"
        super().__init__(message, config_key=config_key, **kwargs)
        self.context.update({
            "value": str(value),
            "expected_type": expected_type
        })
        self.error_code = "INVALID_CONFIGURATION"


# Validation Exceptions
class ValidationException(BaseCustomException):
    """Base exception for validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None, **kwargs):
        super().__init__(message, "VALIDATION_ERROR", **kwargs)
        if field:
            self.context["field"] = field
        if value is not None:
            self.context["value"] = str(value)
        self.severity = ErrorSeverity.LOW


class SchemaValidationException(ValidationException):
    """Raised when data doesn't match expected schema."""
    
    def __init__(self, schema_name: str, validation_errors: List[str], **kwargs):
        message = f"Schema validation failed for {schema_name}: {'; '.join(validation_errors)}"
        super().__init__(message, **kwargs)
        self.context.update({
            "schema_name": schema_name,
            "validation_errors": validation_errors
        })
        self.error_code = "SCHEMA_VALIDATION_ERROR"


# Authentication and Authorization Exceptions
class AuthenticationException(BaseCustomException):
    """Base exception for authentication errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, "AUTHENTICATION_ERROR", **kwargs)
        self.severity = ErrorSeverity.MEDIUM


class UnauthorizedException(AuthenticationException):
    """Raised when user is not authenticated."""
    
    def __init__(self, **kwargs):
        super().__init__("Authentication required", **kwargs)
        self.error_code = "UNAUTHORIZED"


class ForbiddenException(AuthenticationException):
    """Raised when user lacks required permissions."""
    
    def __init__(self, required_permission: Optional[str] = None, **kwargs):
        message = "Access forbidden"
        if required_permission:
            message += f". Required permission: {required_permission}"
        super().__init__(message, **kwargs)
        if required_permission:
            self.context["required_permission"] = required_permission
        self.error_code = "FORBIDDEN"


# System Exceptions
class SystemException(BaseCustomException):
    """Base exception for system-level errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, "SYSTEM_ERROR", **kwargs)
        self.severity = ErrorSeverity.HIGH


class ServiceUnavailableException(SystemException):
    """Raised when a required service is unavailable."""
    
    def __init__(self, service_name: str, **kwargs):
        message = f"Service unavailable: {service_name}"
        super().__init__(message, **kwargs)
        self.context["service_name"] = service_name
        self.error_code = "SERVICE_UNAVAILABLE"


class ResourceExhaustedException(SystemException):
    """Raised when system resources are exhausted."""
    
    def __init__(self, resource_type: str, **kwargs):
        message = f"Resource exhausted: {resource_type}"
        super().__init__(message, **kwargs)
        self.context["resource_type"] = resource_type
        self.error_code = "RESOURCE_EXHAUSTED"


# Export all exception classes
__all__ = [
    'ErrorSeverity',
    'BaseCustomException',
    'DocumentProcessingException',
    'UnsupportedDocumentFormatException',
    'DocumentTooLargeException',
    'TextExtractionException',
    'GeminiAPIException',
    'GeminiRateLimitException',
    'GeminiServiceUnavailableException',
    'GeminiResponseParsingException',
    'FirestoreException',
    'FirestoreConnectionException',
    'FirestoreTransactionException',
    'DocumentNotFoundException',
    'ClassificationException',
    'InsufficientContextException',
    'LowConfidenceClassificationException',
    'BucketException',
    'BucketNotFoundException',
    'ClusteringException',
    'RuleEngineException',
    'RuleEvaluationException',
    'RuleConflictException',
    'ConfigurationException',
    'MissingConfigurationException',
    'InvalidConfigurationException',
    'ValidationException',
    'SchemaValidationException',
    'AuthenticationException',
    'UnauthorizedException',
    'ForbiddenException',
    'SystemException',
    'ServiceUnavailableException',
    'ResourceExhaustedException'
]