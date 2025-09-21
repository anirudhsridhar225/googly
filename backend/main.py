from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import traceback
from datetime import datetime
from typing import Union

from routes import text_ocr, user, classification, reference_documents
from startup import startup_checks
from response_formatter import ResponseFormatter, ErrorCode, ErrorDetail, StatusCodeMapper
from exceptions import (
    BaseCustomException, ErrorSeverity,
    DocumentProcessingException, UnsupportedDocumentFormatException, DocumentTooLargeException,
    GeminiAPIException, GeminiRateLimitException, GeminiServiceUnavailableException,
    FirestoreException, FirestoreConnectionException, DocumentNotFoundException,
    ClassificationException, InsufficientContextException, LowConfidenceClassificationException,
    BucketException, RuleEngineException, RuleConflictException,
    ConfigurationException, ValidationException, AuthenticationException,
    UnauthorizedException, ForbiddenException, SystemException, ServiceUnavailableException
)
from middleware import (
    RequestTrackingMiddleware, ErrorMonitoringMiddleware, 
    PerformanceMonitoringMiddleware, SecurityHeadersMiddleware
)
# Settings will be imported when needed

# Configure basic logging (will be reconfigured in startup)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting Legal Document Severity Classification System...")
    
    try:
        startup_success = await startup_checks()
        if not startup_success:
            logger.error("Startup checks failed. Application may not function correctly.")
            # Continue anyway for development, but log the error
    except Exception as e:
        logger.error(f"Startup checks failed with error: {e}")
        logger.error("Application will continue but may not function correctly.")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Legal Document Severity Classification System...")


app = FastAPI(
    title="Legal Document Severity Classification System",
    description="""
    ## AI-Powered Legal Document Severity Classification
    
    This system provides sophisticated severity classification for legal documents using a bucketed context mechanism. 
    The system organizes reference documents into semantic buckets and uses the most relevant bucket at inference 
    time to guide severity tagging of incoming documents.
    
    ### Key Features
    - **Semantic Bucketing**: Documents are automatically clustered into semantic buckets for efficient retrieval
    - **AI-Powered Classification**: Uses Google's Gemini model for embeddings and classification
    - **Rule Engine**: Deterministic rules can override AI classifications for critical legal requirements
    - **Comprehensive Audit**: Full audit trails and transparency for all classification decisions
    - **Performance Monitoring**: Built-in performance tracking and evaluation metrics
    
    ### Severity Levels
    - **LOW**: Minimal legal risk or impact
    - **MEDIUM**: Moderate legal risk requiring attention
    - **HIGH**: Significant legal risk requiring prompt action
    - **CRITICAL**: Severe legal risk requiring immediate action
    
    ### Authentication
    Include the API key in the request header: `X-API-Key: your_api_key`
    
    ### Rate Limits
    - Classification requests: 60 per minute
    - Reference document uploads: 30 per minute
    - Bulk operations: 10 per minute
    
    ### Support
    For technical support or questions about the API, please contact the development team.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Legal Document Classification Team",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        },
        {
            "url": "https://your-service.onrender.com",
            "description": "Production server"
        }
    ]
)

# Add middleware (order matters - first added is outermost)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(PerformanceMonitoringMiddleware, slow_request_threshold=5.0)
app.add_middleware(ErrorMonitoringMiddleware)
app.add_middleware(RequestTrackingMiddleware)

app.include_router(text_ocr.router, prefix="/api/ocr", tags=["ocr"])
app.include_router(user.router, prefix="/api/user", tags=["user"])
app.include_router(classification.router, prefix="/api/classification", tags=["classification"])
app.include_router(reference_documents.router, prefix="/api/reference", tags=["reference-documents"])


# Global exception handlers for standardized responses

@app.exception_handler(BaseCustomException)
async def custom_exception_handler(request: Request, exc: BaseCustomException):
    """Handle custom exceptions with standardized response format."""
    logger.info(f"Handling custom exception: {exc.error_code} - {exc.message}")
    
    error_detail = ErrorDetail(
        code=ErrorCode(exc.error_code) if exc.error_code in [e.value for e in ErrorCode] else ErrorCode.INTERNAL_ERROR,
        message=exc.message,
        context=exc.context
    )
    
    error_response = ResponseFormatter.error_response(
        errors=[error_detail],
        message=exc.message,
        metadata={
            "severity": exc.severity.value,
            "error_type": type(exc).__name__,
            "request_id": getattr(request.state, 'request_id', None)
        }
    )
    
    # Map custom error codes to HTTP status codes
    status_code = StatusCodeMapper.get_status_code(error_detail.code)
    
    return ResponseFormatter.create_json_response(error_response, status_code)


@app.exception_handler(DocumentProcessingException)
async def document_processing_exception_handler(request: Request, exc: DocumentProcessingException):
    """Handle document processing exceptions."""
    logger.warning(f"Document processing error: {exc.message}")
    
    error_detail = ErrorDetail(
        code=ErrorCode.PROCESSING_ERROR,
        message=exc.message,
        context=exc.context
    )
    
    error_response = ResponseFormatter.error_response(
        errors=[error_detail],
        message="Document processing failed"
    )
    
    return ResponseFormatter.create_json_response(error_response, status.HTTP_422_UNPROCESSABLE_ENTITY)


@app.exception_handler(UnsupportedDocumentFormatException)
async def unsupported_format_exception_handler(request: Request, exc: UnsupportedDocumentFormatException):
    """Handle unsupported document format exceptions."""
    logger.info(f"Unsupported document format: {exc.message}")
    
    error_detail = ErrorDetail(
        code=ErrorCode.UNSUPPORTED_FORMAT,
        message=exc.message,
        context=exc.context
    )
    
    error_response = ResponseFormatter.error_response(
        errors=[error_detail],
        message="Unsupported document format"
    )
    
    return ResponseFormatter.create_json_response(error_response, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)


@app.exception_handler(DocumentTooLargeException)
async def document_too_large_exception_handler(request: Request, exc: DocumentTooLargeException):
    """Handle document too large exceptions."""
    logger.info(f"Document too large: {exc.message}")
    
    error_detail = ErrorDetail(
        code=ErrorCode.FILE_TOO_LARGE,
        message=exc.message,
        context=exc.context
    )
    
    error_response = ResponseFormatter.error_response(
        errors=[error_detail],
        message="Document size exceeds limit"
    )
    
    return ResponseFormatter.create_json_response(error_response, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)


@app.exception_handler(GeminiRateLimitException)
async def gemini_rate_limit_exception_handler(request: Request, exc: GeminiRateLimitException):
    """Handle Gemini API rate limit exceptions."""
    logger.warning(f"Gemini API rate limit exceeded: {exc.message}")
    
    error_detail = ErrorDetail(
        code=ErrorCode.RATE_LIMITED,
        message=exc.message,
        context=exc.context
    )
    
    error_response = ResponseFormatter.error_response(
        errors=[error_detail],
        message="API rate limit exceeded"
    )
    
    # Add retry-after header if available
    headers = {}
    if "retry_after" in exc.context:
        headers["Retry-After"] = str(exc.context["retry_after"])
    
    return JSONResponse(
        content=error_response.model_dump(),
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        headers=headers
    )


@app.exception_handler(GeminiServiceUnavailableException)
async def gemini_service_unavailable_exception_handler(request: Request, exc: GeminiServiceUnavailableException):
    """Handle Gemini API service unavailable exceptions."""
    logger.error(f"Gemini API service unavailable: {exc.message}")
    
    error_detail = ErrorDetail(
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message=exc.message,
        context=exc.context
    )
    
    error_response = ResponseFormatter.error_response(
        errors=[error_detail],
        message="AI service temporarily unavailable"
    )
    
    return ResponseFormatter.create_json_response(error_response, status.HTTP_503_SERVICE_UNAVAILABLE)


@app.exception_handler(FirestoreConnectionException)
async def firestore_connection_exception_handler(request: Request, exc: FirestoreConnectionException):
    """Handle Firestore connection exceptions."""
    logger.error(f"Firestore connection error: {exc.message}")
    
    error_detail = ErrorDetail(
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message="Database connection failed",
        context={"service": "firestore"}
    )
    
    error_response = ResponseFormatter.error_response(
        errors=[error_detail],
        message="Database service temporarily unavailable"
    )
    
    return ResponseFormatter.create_json_response(error_response, status.HTTP_503_SERVICE_UNAVAILABLE)


@app.exception_handler(DocumentNotFoundException)
async def document_not_found_exception_handler(request: Request, exc: DocumentNotFoundException):
    """Handle document not found exceptions."""
    logger.info(f"Document not found: {exc.message}")
    
    error_detail = ErrorDetail(
        code=ErrorCode.NOT_FOUND,
        message=exc.message,
        context=exc.context
    )
    
    error_response = ResponseFormatter.error_response(
        errors=[error_detail],
        message="Requested resource not found"
    )
    
    return ResponseFormatter.create_json_response(error_response, status.HTTP_404_NOT_FOUND)


@app.exception_handler(LowConfidenceClassificationException)
async def low_confidence_exception_handler(request: Request, exc: LowConfidenceClassificationException):
    """Handle low confidence classification exceptions."""
    logger.info(f"Low confidence classification: {exc.message}")
    
    # For low confidence, we still return success but with warnings
    warning = {
        "type": "low_confidence",
        "message": exc.message,
        "context": exc.context
    }
    
    response = ResponseFormatter.warning_response(
        data=None,
        warnings=[warning],
        message="Classification completed with low confidence"
    )
    
    return ResponseFormatter.create_json_response(response, status.HTTP_200_OK)


@app.exception_handler(RuleConflictException)
async def rule_conflict_exception_handler(request: Request, exc: RuleConflictException):
    """Handle rule conflict exceptions."""
    logger.warning(f"Rule conflict: {exc.message}")
    
    error_detail = ErrorDetail(
        code=ErrorCode.RULE_CONFLICT,
        message=exc.message,
        context=exc.context
    )
    
    error_response = ResponseFormatter.error_response(
        errors=[error_detail],
        message="Rule conflict detected"
    )
    
    return ResponseFormatter.create_json_response(error_response, status.HTTP_409_CONFLICT)


@app.exception_handler(UnauthorizedException)
async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
    """Handle unauthorized exceptions."""
    logger.info(f"Unauthorized access attempt: {exc.message}")
    
    error_detail = ErrorDetail(
        code=ErrorCode.UNAUTHORIZED,
        message=exc.message,
        context=exc.context
    )
    
    error_response = ResponseFormatter.error_response(
        errors=[error_detail],
        message="Authentication required"
    )
    
    return ResponseFormatter.create_json_response(error_response, status.HTTP_401_UNAUTHORIZED)


@app.exception_handler(ForbiddenException)
async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
    """Handle forbidden exceptions."""
    logger.info(f"Forbidden access attempt: {exc.message}")
    
    error_detail = ErrorDetail(
        code=ErrorCode.FORBIDDEN,
        message=exc.message,
        context=exc.context
    )
    
    error_response = ResponseFormatter.error_response(
        errors=[error_detail],
        message="Access forbidden"
    )
    
    return ResponseFormatter.create_json_response(error_response, status.HTTP_403_FORBIDDEN)


@app.exception_handler(ConfigurationException)
async def configuration_exception_handler(request: Request, exc: ConfigurationException):
    """Handle configuration exceptions."""
    logger.critical(f"Configuration error: {exc.message}")
    
    error_detail = ErrorDetail(
        code=ErrorCode.INTERNAL_ERROR,
        message="System configuration error",
        context={"config_issue": True}
    )
    
    error_response = ResponseFormatter.error_response(
        errors=[error_detail],
        message="System configuration error"
    )
    
    return ResponseFormatter.create_json_response(error_response, status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with standardized response format."""
    logger.info(f"HTTP exception: {exc.status_code} - {exc.detail}")
    
    # If the detail is already a standardized response, return it as-is
    if isinstance(exc.detail, dict) and "status" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    
    # Otherwise, create a standardized error response
    error_detail = ErrorDetail(
        code=ErrorCode.INTERNAL_ERROR,
        message=str(exc.detail)
    )
    
    error_response = ResponseFormatter.error_response(
        errors=[error_detail],
        message=str(exc.detail)
    )
    
    return ResponseFormatter.create_json_response(error_response, exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with standardized response format."""
    logger.info(f"Request validation error: {exc.errors()}")
    
    errors = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        error_detail = ErrorDetail(
            code=ErrorCode.VALIDATION_ERROR,
            message=error["msg"],
            field=field_path,
            value=error.get("input"),
            context={"type": error["type"]}
        )
        errors.append(error_detail)
    
    error_response = ResponseFormatter.error_response(
        errors=errors,
        message="Request validation failed"
    )
    
    return ResponseFormatter.create_json_response(error_response, status.HTTP_422_UNPROCESSABLE_ENTITY)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with standardized response format."""
    # Log the full traceback for debugging
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Create error detail with exception type for debugging
    error_detail = ErrorDetail(
        code=ErrorCode.INTERNAL_ERROR,
        message="An internal server error occurred",
        context={
            "exception_type": type(exc).__name__,
            "request_id": getattr(request.state, 'request_id', None)
        }
    )
    
    error_response = ResponseFormatter.error_response(
        errors=[error_detail],
        message="Internal server error"
    )
    
    return ResponseFormatter.create_json_response(error_response, status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/")
async def hello():
    """Root endpoint with system information."""
    data = {
        "service": "Legal Document Severity Classification System",
        "version": "1.0.0",
        "status": "running"
    }
    
    response = ResponseFormatter.success_response(
        data=data,
        message="Legal Document Severity Classification System is running"
    )
    
    return ResponseFormatter.create_json_response(response)


@app.get("/health")
async def health_check_endpoint():
    """
    Health check endpoint for system monitoring.
    """
    from startup import health_check
    
    health_data = await health_check()
    
    if health_data["overall_healthy"]:
        response = ResponseFormatter.success_response(
            data=health_data,
            message="System is healthy"
        )
        return ResponseFormatter.create_json_response(response)
    else:
        response = ResponseFormatter.error_response(
            errors=[],
            message="System health check failed",
            metadata=health_data
        )
        return ResponseFormatter.create_json_response(response, status.HTTP_503_SERVICE_UNAVAILABLE)


@app.get("/health/ready")
async def readiness_check_endpoint():
    """
    Readiness check endpoint for deployment orchestration.
    """
    from startup import readiness_check
    
    readiness_data = await readiness_check()
    
    if readiness_data["ready"]:
        response = ResponseFormatter.success_response(
            data=readiness_data,
            message="Service is ready"
        )
        return ResponseFormatter.create_json_response(response)
    else:
        response = ResponseFormatter.error_response(
            errors=[],
            message="Service is not ready",
            metadata=readiness_data
        )
        return ResponseFormatter.create_json_response(response, status.HTTP_503_SERVICE_UNAVAILABLE)


@app.get("/health/live")
async def liveness_check_endpoint():
    """
    Liveness check endpoint for basic service availability.
    """
    data = {
        "alive": True,
        "service": "legal-document-classification",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    response = ResponseFormatter.success_response(
        data=data,
        message="Service is alive"
    )
    
    return ResponseFormatter.create_json_response(response)


@app.get("/system/info")
async def system_info_endpoint():
    """
    System information endpoint for monitoring and debugging.
    """
    from startup import get_system_info
    
    system_data = get_system_info()
    
    response = ResponseFormatter.success_response(
        data=system_data,
        message="System information retrieved"
    )
    
    return ResponseFormatter.create_json_response(response)
