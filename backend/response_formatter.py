"""
Response Formatting System for Legal Document Severity Classification System.

This module provides standardized JSON response formatting, proper HTTP status code handling,
and response validation with confidence warning flags according to the specification.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from legal_models import SeverityLevel, ClassificationResult

logger = logging.getLogger(__name__)


class ResponseStatus(str, Enum):
    """Standard response status values."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PARTIAL = "partial"


class ErrorCode(str, Enum):
    """Standard error codes for the system."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    RATE_LIMITED = "RATE_LIMITED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    INSUFFICIENT_CONFIDENCE = "INSUFFICIENT_CONFIDENCE"
    RULE_CONFLICT = "RULE_CONFLICT"


class ConfidenceWarning(BaseModel):
    """Model for confidence warning information."""
    warning_type: str = Field(..., description="Type of confidence warning")
    threshold: float = Field(..., ge=0.0, le=1.0, description="Confidence threshold that triggered warning")
    actual_confidence: float = Field(..., ge=0.0, le=1.0, description="Actual confidence score")
    message: str = Field(..., description="Human-readable warning message")
    recommendation: Optional[str] = Field(None, description="Recommended action")


class StandardResponse(BaseModel):
    """Standard response format for all API endpoints."""
    status: ResponseStatus = Field(..., description="Response status")
    message: str = Field(..., description="Human-readable message")
    data: Optional[Any] = Field(None, description="Response data")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="Error details")
    warnings: Optional[List[Dict[str, Any]]] = Field(None, description="Warning details")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Response timestamp")


class ClassificationResponseData(BaseModel):
    """Standardized classification response data."""
    classification_id: str
    document_id: str
    label: SeverityLevel
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str
    evidence_ids: List[str] = Field(default_factory=list)
    bucket_id: Optional[str] = None
    rule_overrides: List[str] = Field(default_factory=list)
    confidence_warning: Optional[ConfidenceWarning] = None
    processing_time_ms: Optional[int] = None
    created_at: str


class BatchResponseData(BaseModel):
    """Standardized batch response data."""
    batch_id: str
    total_documents: int
    successful_classifications: int
    failed_classifications: int
    results: List[ClassificationResponseData] = Field(default_factory=list)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    processing_time_ms: Optional[int] = None


class ErrorDetail(BaseModel):
    """Detailed error information."""
    code: ErrorCode
    message: str
    field: Optional[str] = None
    value: Optional[Any] = None
    context: Optional[Dict[str, Any]] = None


class ResponseFormatter:
    """
    Centralized response formatting system.
    
    Provides methods to create standardized responses with proper HTTP status codes,
    error handling, and confidence warnings.
    """
    
    # Confidence thresholds for warnings
    LOW_CONFIDENCE_THRESHOLD = 0.7
    VERY_LOW_CONFIDENCE_THRESHOLD = 0.5
    
    @classmethod
    def success_response(
        cls,
        data: Any,
        message: str = "Operation completed successfully",
        warnings: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StandardResponse:
        """
        Create a success response.
        
        Args:
            data: Response data
            message: Success message
            warnings: Optional warnings
            metadata: Optional metadata
            
        Returns:
            Standardized success response
        """
        return StandardResponse(
            status=ResponseStatus.SUCCESS,
            message=message,
            data=data,
            warnings=warnings,
            metadata=metadata
        )
    
    @classmethod
    def error_response(
        cls,
        errors: List[ErrorDetail],
        message: str = "Operation failed",
        data: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StandardResponse:
        """
        Create an error response.
        
        Args:
            errors: List of error details
            message: Error message
            data: Optional partial data
            metadata: Optional metadata
            
        Returns:
            Standardized error response
        """
        error_dicts = [error.model_dump() for error in errors]
        
        return StandardResponse(
            status=ResponseStatus.ERROR,
            message=message,
            data=data,
            errors=error_dicts,
            metadata=metadata
        )
    
    @classmethod
    def warning_response(
        cls,
        data: Any,
        warnings: List[Dict[str, Any]],
        message: str = "Operation completed with warnings",
        metadata: Optional[Dict[str, Any]] = None
    ) -> StandardResponse:
        """
        Create a warning response.
        
        Args:
            data: Response data
            warnings: List of warnings
            message: Warning message
            metadata: Optional metadata
            
        Returns:
            Standardized warning response
        """
        return StandardResponse(
            status=ResponseStatus.WARNING,
            message=message,
            data=data,
            warnings=warnings,
            metadata=metadata
        )
    
    @classmethod
    def partial_response(
        cls,
        data: Any,
        errors: List[ErrorDetail],
        message: str = "Operation partially completed",
        warnings: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StandardResponse:
        """
        Create a partial success response.
        
        Args:
            data: Partial response data
            errors: List of errors for failed parts
            message: Partial success message
            warnings: Optional warnings
            metadata: Optional metadata
            
        Returns:
            Standardized partial response
        """
        error_dicts = [error.model_dump() for error in errors]
        
        return StandardResponse(
            status=ResponseStatus.PARTIAL,
            message=message,
            data=data,
            errors=error_dicts,
            warnings=warnings,
            metadata=metadata
        )
    
    @classmethod
    def create_confidence_warning(
        cls,
        confidence: float,
        classification_result: ClassificationResult
    ) -> Optional[ConfidenceWarning]:
        """
        Create confidence warning if confidence is below thresholds.
        
        Args:
            confidence: Confidence score
            classification_result: Classification result
            
        Returns:
            Confidence warning if applicable, None otherwise
        """
        if confidence >= cls.LOW_CONFIDENCE_THRESHOLD:
            return None
        
        if confidence < cls.VERY_LOW_CONFIDENCE_THRESHOLD:
            warning_type = "very_low_confidence"
            threshold = cls.VERY_LOW_CONFIDENCE_THRESHOLD
            message = f"Very low confidence classification ({confidence:.2f}). Strong recommendation for human review."
            recommendation = "Human review strongly recommended due to very low confidence."
        else:
            warning_type = "low_confidence"
            threshold = cls.LOW_CONFIDENCE_THRESHOLD
            message = f"Low confidence classification ({confidence:.2f}). Consider human review."
            recommendation = "Human review recommended due to low confidence."
        
        return ConfidenceWarning(
            warning_type=warning_type,
            threshold=threshold,
            actual_confidence=confidence,
            message=message,
            recommendation=recommendation
        )
    
    @classmethod
    def format_classification_response(
        cls,
        classification_result: ClassificationResult,
        processing_time_ms: Optional[int] = None
    ) -> ClassificationResponseData:
        """
        Format a classification result into standardized response data.
        
        Args:
            classification_result: Classification result from engine
            processing_time_ms: Processing time in milliseconds
            
        Returns:
            Formatted classification response data
        """
        # Create confidence warning if needed
        confidence_warning = cls.create_confidence_warning(
            classification_result.confidence,
            classification_result
        )
        
        return ClassificationResponseData(
            classification_id=classification_result.classification_id,
            document_id=classification_result.document_id,
            label=classification_result.label,
            confidence=classification_result.confidence,
            rationale=classification_result.rationale,
            evidence_ids=[ev.document_id for ev in classification_result.evidence],
            bucket_id=classification_result.bucket_id,
            rule_overrides=classification_result.rule_overrides,
            confidence_warning=confidence_warning,
            processing_time_ms=processing_time_ms,
            created_at=classification_result.created_at.isoformat()
        )
    
    @classmethod
    def format_batch_response(
        cls,
        batch_id: str,
        results: List[ClassificationResult],
        errors: List[Dict[str, Any]],
        processing_time_ms: Optional[int] = None
    ) -> BatchResponseData:
        """
        Format batch classification results into standardized response data.
        
        Args:
            batch_id: Batch identifier
            results: List of successful classification results
            errors: List of errors for failed classifications
            processing_time_ms: Total processing time in milliseconds
            
        Returns:
            Formatted batch response data
        """
        formatted_results = []
        for result in results:
            formatted_result = cls.format_classification_response(result)
            formatted_results.append(formatted_result)
        
        return BatchResponseData(
            batch_id=batch_id,
            total_documents=len(results) + len(errors),
            successful_classifications=len(results),
            failed_classifications=len(errors),
            results=formatted_results,
            errors=errors,
            processing_time_ms=processing_time_ms
        )
    
    @classmethod
    def create_http_exception(
        cls,
        status_code: int,
        error_code: ErrorCode,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> HTTPException:
        """
        Create an HTTPException with standardized error format.
        
        Args:
            status_code: HTTP status code
            error_code: Standard error code
            message: Error message
            field: Optional field name that caused the error
            value: Optional field value that caused the error
            context: Optional additional context
            
        Returns:
            HTTPException with standardized error detail
        """
        error_detail = ErrorDetail(
            code=error_code,
            message=message,
            field=field,
            value=value,
            context=context
        )
        
        error_response = cls.error_response(
            errors=[error_detail],
            message=message
        )
        
        return HTTPException(
            status_code=status_code,
            detail=error_response.model_dump()
        )
    
    @classmethod
    def handle_validation_error(cls, validation_error: ValidationError) -> HTTPException:
        """
        Convert Pydantic validation error to standardized HTTP exception.
        
        Args:
            validation_error: Pydantic validation error
            
        Returns:
            HTTPException with validation error details
        """
        errors = []
        for error in validation_error.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            error_detail = ErrorDetail(
                code=ErrorCode.VALIDATION_ERROR,
                message=error["msg"],
                field=field_path,
                value=error.get("input"),
                context={"type": error["type"]}
            )
            errors.append(error_detail)
        
        error_response = cls.error_response(
            errors=errors,
            message="Validation failed"
        )
        
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_response.model_dump()
        )
    
    @classmethod
    def create_json_response(
        cls,
        response: StandardResponse,
        status_code: int = status.HTTP_200_OK
    ) -> JSONResponse:
        """
        Create a JSONResponse with standardized format.
        
        Args:
            response: Standardized response object
            status_code: HTTP status code
            
        Returns:
            JSONResponse with proper headers and formatting
        """
        return JSONResponse(
            content=response.model_dump(),
            status_code=status_code,
            headers={
                "Content-Type": "application/json",
                "X-Response-Format": "standard-v1",
                "X-Timestamp": response.timestamp
            }
        )


class StatusCodeMapper:
    """Maps error codes to appropriate HTTP status codes."""
    
    ERROR_CODE_TO_HTTP_STATUS = {
        ErrorCode.VALIDATION_ERROR: status.HTTP_422_UNPROCESSABLE_ENTITY,
        ErrorCode.PROCESSING_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorCode.NOT_FOUND: status.HTTP_404_NOT_FOUND,
        ErrorCode.UNAUTHORIZED: status.HTTP_401_UNAUTHORIZED,
        ErrorCode.FORBIDDEN: status.HTTP_403_FORBIDDEN,
        ErrorCode.RATE_LIMITED: status.HTTP_429_TOO_MANY_REQUESTS,
        ErrorCode.SERVICE_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
        ErrorCode.INTERNAL_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ErrorCode.FILE_TOO_LARGE: status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        ErrorCode.UNSUPPORTED_FORMAT: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        ErrorCode.INSUFFICIENT_CONFIDENCE: status.HTTP_200_OK,  # Still success, but with warning
        ErrorCode.RULE_CONFLICT: status.HTTP_409_CONFLICT,
    }
    
    @classmethod
    def get_status_code(cls, error_code: ErrorCode) -> int:
        """
        Get appropriate HTTP status code for error code.
        
        Args:
            error_code: Standard error code
            
        Returns:
            HTTP status code
        """
        return cls.ERROR_CODE_TO_HTTP_STATUS.get(error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


# Response validation schemas
class ResponseValidator:
    """Validates response data against schemas."""
    
    @classmethod
    def validate_classification_response(cls, data: Dict[str, Any]) -> bool:
        """
        Validate classification response data.
        
        Args:
            data: Response data to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            ClassificationResponseData(**data)
            return True
        except ValidationError as e:
            logger.error(f"Classification response validation failed: {e}")
            return False
    
    @classmethod
    def validate_batch_response(cls, data: Dict[str, Any]) -> bool:
        """
        Validate batch response data.
        
        Args:
            data: Response data to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            BatchResponseData(**data)
            return True
        except ValidationError as e:
            logger.error(f"Batch response validation failed: {e}")
            return False
    
    @classmethod
    def validate_standard_response(cls, data: Dict[str, Any]) -> bool:
        """
        Validate standard response format.
        
        Args:
            data: Response data to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            StandardResponse(**data)
            return True
        except ValidationError as e:
            logger.error(f"Standard response validation failed: {e}")
            return False


# Export all classes and functions
__all__ = [
    'ResponseStatus',
    'ErrorCode',
    'ConfidenceWarning',
    'StandardResponse',
    'ClassificationResponseData',
    'BatchResponseData',
    'ErrorDetail',
    'ResponseFormatter',
    'StatusCodeMapper',
    'ResponseValidator'
]