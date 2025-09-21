"""
Classification API endpoints for Legal Document Severity Classification System.

This module provides FastAPI endpoints for document classification including:
- Single document classification
- Batch document classification  
- File upload handling with validation
- Classification status and result retrieval
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from models.legal_models import (
    ClassificationResult, SeverityLevel, DocumentType,
    Document, DocumentMetadata, FIRESTORE_COLLECTIONS
)
from processing.document_processing import DocumentProcessor
from ai.classification_engine import ClassificationEngine
from storage.document_store import DocumentStore
from storage.firestore_client import get_firestore_client
from services.response_formatter import (
    ResponseFormatter, StandardResponse, ClassificationResponseData,
    BatchResponseData, ErrorCode, ErrorDetail, StatusCodeMapper
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services (will be properly initialized in startup)
document_processor = None
classification_engine = None
document_store = None

# Request/Response Models
class ClassificationRequest(BaseModel):
    """Request model for document classification."""
    document_text: str = Field(..., min_length=1, max_length=1000000)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    priority: Optional[str] = Field(default="normal", pattern="^(low|normal|high|urgent)$")

class BatchClassificationRequest(BaseModel):
    """Request model for batch document classification."""
    documents: List[ClassificationRequest] = Field(..., min_items=1, max_items=50)
    batch_id: Optional[str] = Field(default_factory=lambda: str(uuid4()))

class ClassificationResponse(BaseModel):
    """Response model for document classification."""
    classification_id: str
    document_id: str
    label: SeverityLevel
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str
    evidence_ids: List[str] = Field(default_factory=list)
    bucket_id: Optional[str] = None
    rule_overrides: List[str] = Field(default_factory=list)
    confidence_warning: Optional[Dict[str, Any]] = None
    processing_time_ms: Optional[int] = None
    created_at: str

class BatchClassificationResponse(BaseModel):
    """Response model for batch document classification."""
    batch_id: str
    total_documents: int
    successful_classifications: int
    failed_classifications: int
    results: List[ClassificationResponse] = Field(default_factory=list)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    processing_time_ms: Optional[int] = None

class ClassificationStatusResponse(BaseModel):
    """Response model for classification status."""
    classification_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: Optional[float] = Field(None, ge=0.0, le=1.0)
    estimated_completion: Optional[str] = None
    error_message: Optional[str] = None

class FileUploadResponse(BaseModel):
    """Response model for file upload."""
    document_id: str
    filename: str
    file_size: int
    content_hash: str
    processing_status: str
    message: str

# Global storage for tracking classification status
classification_status_store: Dict[str, Dict[str, Any]] = {}

async def get_services():
    """Get initialized services."""
    global document_processor, classification_engine, document_store
    
    if not document_processor:
        document_processor = DocumentProcessor()
    if not classification_engine:
        classification_engine = ClassificationEngine()
    if not document_store:
        document_store = DocumentStore()
    
    return document_processor, classification_engine, document_store

@router.get("/health")
async def classification_health():
    """Health check endpoint for classification service."""
    return {
        "status": "healthy",
        "service": "classification",
        "version": "1.0.0"
    }

@router.post(
    "/classify",
    response_model=ClassificationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Bad Request - Invalid input"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"}
    }
)
async def classify_document(request: ClassificationRequest) -> ClassificationResponse:
    """
    Classify a single document for severity level.
    
    Args:
        request: Classification request with document text and metadata
        
    Returns:
        Classification result with severity label, confidence, and evidence
        
    Raises:
        HTTPException: For validation errors or processing failures
    """
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Get services
        doc_processor, classifier, doc_store = await get_services()
        
        # Create document metadata
        metadata = DocumentMetadata(
            filename=request.metadata.get("filename", "text_input.txt"),
            upload_date=datetime.utcnow(),
            file_size=len(request.document_text.encode('utf-8')),
            uploader_id=request.metadata.get("uploader_id"),
            tags=request.metadata.get("tags", [])
        )
        
        # Process document for classification
        processed_doc = await doc_processor.process_text_for_classification(
            text=request.document_text,
            metadata=metadata
        )
        
        # Perform classification
        classification_result = await classifier.classify_document(processed_doc)
        
        # Calculate processing time
        processing_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        # Format response using standardized formatter
        response_data = ResponseFormatter.format_classification_response(
            classification_result=classification_result,
            processing_time_ms=processing_time
        )
        
        # Check for confidence warnings
        warnings = []
        if response_data.confidence_warning:
            warnings.append({
                "type": "confidence_warning",
                "details": response_data.confidence_warning.model_dump()
            })
        
        # Create standardized response
        if warnings:
            standard_response = ResponseFormatter.warning_response(
                data=response_data.model_dump(),
                warnings=warnings,
                message="Document classified successfully with confidence warnings",
                metadata={
                    "processing_time_ms": processing_time,
                    "model_version": classification_result.model_version
                }
            )
        else:
            standard_response = ResponseFormatter.success_response(
                data=response_data.model_dump(),
                message="Document classified successfully",
                metadata={
                    "processing_time_ms": processing_time,
                    "model_version": classification_result.model_version
                }
            )
        
        logger.info(f"Document classified successfully: {classification_result.classification_id}")
        return ResponseFormatter.create_json_response(standard_response)
        
    except ValidationError as e:
        logger.error(f"Validation error in document classification: {e}")
        raise ResponseFormatter.handle_validation_error(e)
    except Exception as e:
        logger.error(f"Error classifying document: {e}")
        raise ResponseFormatter.create_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.PROCESSING_ERROR,
            message="Classification failed",
            context={"error": str(e)}
        )

@router.post(
    "/classify/file",
    response_model=ClassificationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Bad Request - Invalid file"},
        413: {"description": "File too large"},
        415: {"description": "Unsupported file type"},
        500: {"description": "Internal Server Error"}
    }
)
async def classify_file(
    file: UploadFile = File(...),
    priority: str = Query(default="normal", pattern="^(low|normal|high|urgent)$")
) -> ClassificationResponse:
    """
    Classify a document file for severity level.
    
    Args:
        file: Uploaded document file (PDF, DOCX, TXT)
        priority: Processing priority level
        
    Returns:
        Classification result with severity label, confidence, and evidence
        
    Raises:
        HTTPException: For file validation errors or processing failures
    """
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Validate file
        if not file.filename:
            raise ResponseFormatter.create_http_exception(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code=ErrorCode.VALIDATION_ERROR,
                message="No filename provided",
                field="filename"
            )
        
        # Check file size (10MB limit)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:
            raise ResponseFormatter.create_http_exception(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                error_code=ErrorCode.FILE_TOO_LARGE,
                message="File size exceeds 10MB limit",
                context={"max_size_mb": 10, "actual_size_mb": len(file_content) / (1024 * 1024)}
            )
        
        # Reset file pointer
        await file.seek(0)
        
        # Get services
        doc_processor, classifier, doc_store = await get_services()
        
        # Process uploaded file
        processed_doc = await doc_processor.process_uploaded_file(
            file=file,
            document_type=DocumentType.CLASSIFICATION
        )
        
        # Perform classification
        classification_result = await classifier.classify_document(processed_doc)
        
        # Calculate processing time
        processing_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        # Format response using standardized formatter
        response_data = ResponseFormatter.format_classification_response(
            classification_result=classification_result,
            processing_time_ms=processing_time
        )
        
        # Check for confidence warnings
        warnings = []
        if response_data.confidence_warning:
            warnings.append({
                "type": "confidence_warning",
                "details": response_data.confidence_warning.model_dump()
            })
        
        # Create standardized response
        if warnings:
            standard_response = ResponseFormatter.warning_response(
                data=response_data.model_dump(),
                warnings=warnings,
                message=f"File {file.filename} classified successfully with confidence warnings",
                metadata={
                    "processing_time_ms": processing_time,
                    "filename": file.filename,
                    "file_size": len(file_content),
                    "model_version": classification_result.model_version
                }
            )
        else:
            standard_response = ResponseFormatter.success_response(
                data=response_data.model_dump(),
                message=f"File {file.filename} classified successfully",
                metadata={
                    "processing_time_ms": processing_time,
                    "filename": file.filename,
                    "file_size": len(file_content),
                    "model_version": classification_result.model_version
                }
            )
        
        logger.info(f"File classified successfully: {file.filename} -> {classification_result.classification_id}")
        return ResponseFormatter.create_json_response(standard_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error classifying file {file.filename}: {e}")
        raise ResponseFormatter.create_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.PROCESSING_ERROR,
            message="File classification failed",
            context={"filename": file.filename, "error": str(e)}
        )

@router.post(
    "/classify/batch",
    response_model=BatchClassificationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"description": "Bad Request - Invalid batch"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"}
    }
)
async def classify_batch(
    request: BatchClassificationRequest,
    background_tasks: BackgroundTasks
) -> BatchClassificationResponse:
    """
    Classify multiple documents in batch.
    
    Args:
        request: Batch classification request with multiple documents
        background_tasks: FastAPI background tasks for async processing
        
    Returns:
        Batch classification response with results and status
        
    Raises:
        HTTPException: For validation errors or processing failures
    """
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Initialize batch status
        batch_id = request.batch_id
        classification_status_store[batch_id] = {
            "status": "processing",
            "total": len(request.documents),
            "completed": 0,
            "failed": 0,
            "results": [],
            "errors": []
        }
        
        # Process batch in background
        background_tasks.add_task(
            process_batch_classification,
            batch_id,
            request.documents
        )
        
        # Create initial batch response data
        batch_data = BatchResponseData(
            batch_id=batch_id,
            total_documents=len(request.documents),
            successful_classifications=0,
            failed_classifications=0,
            results=[],
            errors=[],
            processing_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
        )
        
        # Create standardized response
        standard_response = ResponseFormatter.success_response(
            data=batch_data.model_dump(),
            message=f"Batch classification started with {len(request.documents)} documents",
            metadata={
                "batch_id": batch_id,
                "status": "processing",
                "estimated_completion": "Processing in background"
            }
        )
        
        logger.info(f"Batch classification started: {batch_id} with {len(request.documents)} documents")
        return ResponseFormatter.create_json_response(standard_response, status.HTTP_202_ACCEPTED)
        
    except ValidationError as e:
        logger.error(f"Validation error in batch classification: {e}")
        raise ResponseFormatter.handle_validation_error(e)
    except Exception as e:
        logger.error(f"Error starting batch classification: {e}")
        raise ResponseFormatter.create_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.PROCESSING_ERROR,
            message="Batch classification failed to start",
            context={"error": str(e)}
        )

async def process_batch_classification(batch_id: str, documents: List[ClassificationRequest]):
    """
    Process batch classification in background.
    
    Args:
        batch_id: Unique batch identifier
        documents: List of documents to classify
    """
    try:
        # Get services
        doc_processor, classifier, doc_store = await get_services()
        
        results = []
        errors = []
        
        for i, doc_request in enumerate(documents):
            try:
                # Create document metadata
                metadata = DocumentMetadata(
                    filename=doc_request.metadata.get("filename", f"batch_doc_{i}.txt"),
                    upload_date=datetime.utcnow(),
                    file_size=len(doc_request.document_text.encode('utf-8')),
                    uploader_id=doc_request.metadata.get("uploader_id"),
                    tags=doc_request.metadata.get("tags", [])
                )
                
                # Process document
                processed_doc = await doc_processor.process_text_for_classification(
                    text=doc_request.document_text,
                    metadata=metadata
                )
                
                # Classify document
                classification_result = await classifier.classify_document(processed_doc)
                
                # Convert to response format
                result = ClassificationResponse(
                    classification_id=classification_result.classification_id,
                    document_id=classification_result.document_id,
                    label=classification_result.label,
                    confidence=classification_result.confidence,
                    rationale=classification_result.rationale,
                    evidence_ids=[ev.document_id for ev in classification_result.evidence],
                    bucket_id=classification_result.bucket_id,
                    rule_overrides=classification_result.rule_overrides,
                    confidence_warning=classification_result.confidence_warning,
                    created_at=classification_result.created_at.isoformat()
                )
                
                results.append(result)
                classification_status_store[batch_id]["completed"] += 1
                
            except Exception as e:
                error = {
                    "document_index": i,
                    "error": str(e),
                    "document_preview": doc_request.document_text[:100] + "..." if len(doc_request.document_text) > 100 else doc_request.document_text
                }
                errors.append(error)
                classification_status_store[batch_id]["failed"] += 1
                logger.error(f"Error processing document {i} in batch {batch_id}: {e}")
        
        # Update final status
        classification_status_store[batch_id].update({
            "status": "completed",
            "results": results,
            "errors": errors
        })
        
        logger.info(f"Batch classification completed: {batch_id} - {len(results)} successful, {len(errors)} failed")
        
    except Exception as e:
        classification_status_store[batch_id].update({
            "status": "failed",
            "error": str(e)
        })
        logger.error(f"Batch classification failed: {batch_id} - {e}")

@router.get(
    "/status/{classification_id}",
    response_model=ClassificationStatusResponse,
    responses={
        404: {"description": "Classification not found"},
        500: {"description": "Internal Server Error"}
    }
)
async def get_classification_status(classification_id: str) -> ClassificationStatusResponse:
    """
    Get the status of a classification request.
    
    Args:
        classification_id: Unique classification identifier
        
    Returns:
        Classification status information
        
    Raises:
        HTTPException: If classification not found
    """
    try:
        # Check if it's a batch classification
        if classification_id in classification_status_store:
            batch_status = classification_status_store[classification_id]
            progress = batch_status["completed"] / batch_status["total"] if batch_status["total"] > 0 else 0.0
            
            return ClassificationStatusResponse(
                classification_id=classification_id,
                status=batch_status["status"],
                progress=progress,
                error_message=batch_status.get("error")
            )
        
        # Check individual classification in Firestore
        doc_processor, classifier, doc_store = await get_services()
        firestore_client = get_firestore_client()
        
        # Query classifications collection
        classifications_ref = firestore_client.collection(FIRESTORE_COLLECTIONS['classifications'])
        query = classifications_ref.where('classification_id', '==', classification_id).limit(1)
        docs = query.stream()
        
        classification_doc = None
        for doc in docs:
            classification_doc = doc
            break
        
        if not classification_doc:
            raise ResponseFormatter.create_http_exception(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Classification {classification_id} not found",
                context={"classification_id": classification_id}
            )
        
        # Create standardized response
        status_data = {
            "classification_id": classification_id,
            "status": "completed",
            "progress": 1.0
        }
        
        standard_response = ResponseFormatter.success_response(
            data=status_data,
            message="Classification status retrieved successfully"
        )
        
        return ResponseFormatter.create_json_response(standard_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting classification status {classification_id}: {e}")
        raise ResponseFormatter.create_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.PROCESSING_ERROR,
            message="Failed to get classification status",
            context={"classification_id": classification_id, "error": str(e)}
        )

@router.get(
    "/result/{classification_id}",
    response_model=ClassificationResponse,
    responses={
        404: {"description": "Classification result not found"},
        500: {"description": "Internal Server Error"}
    }
)
async def get_classification_result(classification_id: str) -> ClassificationResponse:
    """
    Get the result of a completed classification.
    
    Args:
        classification_id: Unique classification identifier
        
    Returns:
        Complete classification result
        
    Raises:
        HTTPException: If classification not found
    """
    try:
        # Get services
        doc_processor, classifier, doc_store = await get_services()
        firestore_client = get_firestore_client()
        
        # Query classifications collection
        classifications_ref = firestore_client.collection(FIRESTORE_COLLECTIONS['classifications'])
        query = classifications_ref.where('classification_id', '==', classification_id).limit(1)
        docs = query.stream()
        
        classification_doc = None
        for doc in docs:
            classification_doc = doc
            break
        
        if not classification_doc:
            raise ResponseFormatter.create_http_exception(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Classification {classification_id} not found",
                context={"classification_id": classification_id}
            )
        
        # Convert Firestore document to ClassificationResult
        classification_data = classification_doc.to_dict()
        classification_result = ClassificationResult.from_firestore_dict(classification_data)
        
        # Format response using standardized formatter
        response_data = ResponseFormatter.format_classification_response(
            classification_result=classification_result
        )
        
        # Check for confidence warnings
        warnings = []
        if response_data.confidence_warning:
            warnings.append({
                "type": "confidence_warning",
                "details": response_data.confidence_warning.model_dump()
            })
        
        # Create standardized response
        if warnings:
            standard_response = ResponseFormatter.warning_response(
                data=response_data.model_dump(),
                warnings=warnings,
                message="Classification result retrieved successfully with confidence warnings"
            )
        else:
            standard_response = ResponseFormatter.success_response(
                data=response_data.model_dump(),
                message="Classification result retrieved successfully"
            )
        
        return ResponseFormatter.create_json_response(standard_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting classification result {classification_id}: {e}")
        raise ResponseFormatter.create_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.PROCESSING_ERROR,
            message="Failed to get classification result",
            context={"classification_id": classification_id, "error": str(e)}
        )

@router.get(
    "/batch/{batch_id}",
    response_model=BatchClassificationResponse,
    responses={
        404: {"description": "Batch not found"},
        500: {"description": "Internal Server Error"}
    }
)
async def get_batch_result(batch_id: str) -> BatchClassificationResponse:
    """
    Get the result of a batch classification.
    
    Args:
        batch_id: Unique batch identifier
        
    Returns:
        Complete batch classification result
        
    Raises:
        HTTPException: If batch not found
    """
    try:
        if batch_id not in classification_status_store:
            raise ResponseFormatter.create_http_exception(
                status_code=status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Batch {batch_id} not found",
                context={"batch_id": batch_id}
            )
        
        batch_status = classification_status_store[batch_id]
        
        # Create batch response data
        batch_data = BatchResponseData(
            batch_id=batch_id,
            total_documents=batch_status["total"],
            successful_classifications=batch_status["completed"],
            failed_classifications=batch_status["failed"],
            results=batch_status.get("results", []),
            errors=batch_status.get("errors", [])
        )
        
        # Determine response type based on results
        if batch_status["failed"] > 0 and batch_status["completed"] > 0:
            # Partial success
            errors = [ErrorDetail(
                code=ErrorCode.PROCESSING_ERROR,
                message=f"{batch_status['failed']} documents failed to process",
                context={"failed_count": batch_status["failed"]}
            )]
            standard_response = ResponseFormatter.partial_response(
                data=batch_data.model_dump(),
                errors=errors,
                message=f"Batch processing completed with {batch_status['failed']} failures"
            )
        elif batch_status["failed"] > 0:
            # All failed
            errors = [ErrorDetail(
                code=ErrorCode.PROCESSING_ERROR,
                message="All documents in batch failed to process",
                context={"failed_count": batch_status["failed"]}
            )]
            standard_response = ResponseFormatter.error_response(
                errors=errors,
                message="Batch processing failed",
                data=batch_data.model_dump()
            )
        else:
            # All successful
            standard_response = ResponseFormatter.success_response(
                data=batch_data.model_dump(),
                message="Batch processing completed successfully"
            )
        
        return ResponseFormatter.create_json_response(standard_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch result {batch_id}: {e}")
        raise ResponseFormatter.create_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.PROCESSING_ERROR,
            message="Failed to get batch result",
            context={"batch_id": batch_id, "error": str(e)}
        )


# Document Analysis Models
class ClauseData(BaseModel):
    """Model for identified problematic clause."""
    clause_text: str
    start_position: int
    end_position: int
    severity: str = Field(..., pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    category: str
    explanation: str
    suggested_action: str

class BucketContext(BaseModel):
    """Model for bucket context information."""
    bucket_id: str
    bucket_name: str
    similarity_score: float
    document_count: int
    relevant_documents: List[str] = Field(default_factory=list)

class DocumentAnalysisResponse(BaseModel):
    """Response model for document analysis."""
    structured_text: str
    clauses: List[ClauseData] = Field(default_factory=list)
    bucket_context: Optional[BucketContext] = None
    analysis_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


@router.post(
    "/analyze/document",
    response_model=DocumentAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Legal Document for Predatory Clauses",
    description="""
    Analyze a legal document (PDF) for predatory or unfair clauses using AI with bucket-enhanced context.
    
    This endpoint processes PDF uploads through a comprehensive AI pipeline:
    1. Text Extraction: OCR/text extraction from PDF
    2. Document Bucketing: Find similar reference documents using semantic buckets
    3. Context Enrichment: Use bucket context to enhance clause analysis
    4. Text Restructuring: AI converts raw PDF text into clean, readable markdown
    5. Clause Analysis: AI identifies predatory clauses using tool calls with bucket-informed context
    
    The response provides structured data for frontend highlighting and modal interactions.
    
    **Processing Pipeline:**
    - Extract text using OCR/text extraction
    - Find most relevant semantic bucket based on document similarity
    - Retrieve context from similar reference documents in the bucket
    - AI restructuring for clean markdown with context awareness
    - AI clause analysis with tool calling enhanced by bucket context
    - Position validation and data collection
    
    **Expected processing time:** 30-90 seconds for large documents
    **Memory usage:** 200-500MB for large documents
    """
)
async def analyze_document(
    file: UploadFile = File(..., description="PDF document file to analyze")
) -> DocumentAnalysisResponse:
    """
    Analyze a legal document for predatory clauses and return structured analysis.
    
    Args:
        file: PDF document file to analyze
        
    Returns:
        DocumentAnalysisResponse with structured text and identified clauses
        
    Raises:
        HTTPException: If file processing or analysis fails
    """
    
    # Validate file
    if not file.filename:
        raise ResponseFormatter.create_http_exception(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Filename is required"
        )
    
    if not file.content_type or file.content_type != "application/pdf":
        raise ResponseFormatter.create_http_exception(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            error_code=ErrorCode.UNSUPPORTED_FORMAT,
            message="Only PDF files are supported",
            context={"content_type": file.content_type}
        )
    
    logger.info(f"Starting document analysis for file: {file.filename}")
    start_time = datetime.utcnow()
    
    try:
        # Phase 1: Document Processing - Extract text
        file_content = await file.read()
        
        # Use existing OCR system from utils
        from processing.utils import extract_text_auto
        raw_text = extract_text_auto(
            file_bytes=file_content,
            content_type=file.content_type,
            filename=file.filename
        )
        
        if not raw_text or not raw_text.strip():
            raise ResponseFormatter.create_http_exception(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ErrorCode.PROCESSING_ERROR,
                message="Could not extract text from PDF document"
            )
        
        logger.info(f"Extracted {len(raw_text)} characters from document")
        
        # Phase 2: Bucket-Enhanced Context Retrieval
        # Get services
        doc_processor, classifier, doc_store = await get_services()
        
        if not classifier or not classifier.gemini_classifier:
            raise ResponseFormatter.create_http_exception(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Classification service not available"
            )
        
        # Create a temporary document object for bucket analysis
        from services.embedding_service import EmbeddingGenerator
        from legal_models import DocumentMetadata
        
        temp_metadata = DocumentMetadata(
            filename=file.filename,
            file_size=len(file_content),
            content_hash="temp_analysis",
            upload_date=datetime.utcnow(),
            uploader_id="analysis_user"
        )
        
        # Generate embedding for the document text
        embedding_generator = EmbeddingGenerator()
        document_embedding = await embedding_generator.generate_embedding(raw_text[:1000])  # Use first 1000 chars for embedding
        
        temp_document = Document(
            text=raw_text,
            embedding=document_embedding,
            document_type=DocumentType.CLASSIFICATION,
            metadata=temp_metadata
        )
        
        # Get bucket context using the classification engine's context retriever
        bucket_context_info = None
        context_information = ""
        
        try:
            # Get available buckets
            available_buckets = await classifier.bucket_store.list_buckets()
            logger.info(f"Found {len(available_buckets)} available buckets")
            
            if available_buckets:
                # Retrieve context from most relevant bucket with lower similarity threshold
                # Temporarily lower the similarity threshold for better bucket matching
                original_threshold = classifier.context_retriever.bucket_manager.similarity_threshold
                classifier.context_retriever.bucket_manager.similarity_threshold = 0.3  # Lower threshold for better matching
                
                context_block = await classifier.context_retriever.retrieve_context(
                    temp_document, available_buckets[:2]  # Use only top 2 buckets for speed
                )
                
                # Restore original threshold
                classifier.context_retriever.bucket_manager.similarity_threshold = original_threshold
                
                # Format context for AI analysis
                context_chunks = []
                if context_block and context_block.retrieved_chunks:
                    for chunk in context_block.retrieved_chunks[:5]:  # Top 5 most relevant chunks
                        similarity_score = chunk.get('similarity_score', 0.0)
                        chunk_text = chunk.get('text', '')
                        context_chunks.append(f"**Reference Example ({similarity_score:.2f} similarity):**\n{chunk_text}\n")
                
                context_information = "\n".join(context_chunks) if context_chunks else ""
                
                # Create bucket context info for response
                if context_block and context_block.bucket_info:
                    bucket_info = context_block.bucket_info
                    bucket_context_info = BucketContext(
                        bucket_id=bucket_info.get('bucket_id', ''),
                        bucket_name=bucket_info.get('bucket_name', ''),
                        similarity_score=context_block.total_similarity_score,
                        document_count=bucket_info.get('document_count', 0),
                        relevant_documents=[chunk.get('document_id', '') for chunk in context_block.retrieved_chunks[:5]]
                    )
                    logger.info(f"Using bucket context: {bucket_info.get('bucket_name', 'Unknown')} with {len(context_chunks)} relevant examples")
                
        except Exception as e:
            logger.warning(f"Could not retrieve bucket context: {e}")
            context_information = ""
        
        gemini_classifier = classifier.gemini_classifier
        
        # Phase 3: AI Processing - Context-Enhanced Text Restructuring
        structured_text = await gemini_classifier.restructure_document_text(raw_text)
        logger.info(f"Restructured text into {len(structured_text)} characters")
        
        # Phase 4: AI Processing - Bucket-Enhanced Clause Analysis with Tool Calls
        # Enhance the clause analysis with bucket context
        enhanced_analysis_prompt = f"""You are an expert legal advisor helping someone review their contract. Your role is to protect their interests by identifying problematic, unfair, or predatory clauses that could harm them.

**IMPORTANT CONTEXT FROM SIMILAR CONTRACTS:**
The following examples are from similar legal documents that have been analyzed previously. Use these as reference patterns to identify similar issues in the current document:

{context_information}

**YOUR ANALYSIS APPROACH:**
1. **Comprehensive Review**: Examine every clause for potential issues, not just obvious red flags
2. **User Protection Focus**: Always consider how each clause could disadvantage the person uploading this contract
3. **Practical Impact**: Explain real-world consequences, not just legal theory
4. **Actionable Advice**: Provide specific negotiation points and alternatives
5. **Reference Comparison**: Compare problematic clauses with the patterns shown in the reference examples above

**PRIORITY AREAS TO EXAMINE:**
- Financial obligations and hidden costs
- Termination and cancellation rights
- Liability and indemnification clauses
- Intellectual property ownership
- Confidentiality and non-compete restrictions
- Dispute resolution and arbitration
- Automatic renewals and extensions
- Unilateral modification rights
- Data privacy and usage rights
- Force majeure and exceptional circumstances

**ANALYSIS INSTRUCTIONS:**
For each problematic clause you identify, consider how it compares to the reference patterns above and provide advice as if you're personally helping this person negotiate a fair contract.

Now analyze this document:"""
        
        clauses_data = await gemini_classifier.analyze_document_clauses(
            enhanced_analysis_prompt + "\n\n" + structured_text if context_information else structured_text
        )
        logger.info(f"Identified {len(clauses_data)} problematic clauses with bucket-enhanced analysis")
        
        # Phase 4: Response Assembly - Validate and format clauses
        validated_clauses = []
        for clause_data in clauses_data:
            try:
                # Validate positions are within bounds
                start_pos = clause_data.get('start_position', 0)
                end_pos = clause_data.get('end_position', len(structured_text))
                
                if start_pos < 0:
                    start_pos = 0
                if end_pos > len(structured_text):
                    end_pos = len(structured_text)
                if start_pos >= end_pos:
                    # Try to find the clause text in the document
                    clause_text = clause_data.get('clause_text', '')
                    text_index = structured_text.find(clause_text)
                    if text_index >= 0:
                        start_pos = text_index
                        end_pos = text_index + len(clause_text)
                    else:
                        continue  # Skip invalid clause
                
                clause = ClauseData(
                    clause_text=clause_data.get('clause_text', ''),
                    start_position=start_pos,
                    end_position=end_pos,
                    severity=clause_data.get('severity', 'MEDIUM'),
                    category=clause_data.get('category', ''),
                    explanation=clause_data.get('explanation', ''),
                    suggested_action=clause_data.get('suggested_action', '')
                )
                validated_clauses.append(clause)
                
            except Exception as e:
                logger.warning(f"Failed to validate clause: {e}")
                continue
        
        logger.info(f"Analysis completed: {len(validated_clauses)} validated clauses")
        
        # Prepare analysis metadata
        analysis_metadata = {
            "processing_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
            "text_length": len(raw_text),
            "structured_text_length": len(structured_text),
            "clauses_identified": len(validated_clauses),
            "bucket_enhanced": bucket_context_info is not None,
            "context_chunks_used": len(context_information.split("**Reference Example")) - 1 if context_information else 0
        }
        
        return DocumentAnalysisResponse(
            structured_text=structured_text,
            clauses=validated_clauses,
            bucket_context=bucket_context_info,
            analysis_metadata=analysis_metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing document {file.filename}: {e}")
        raise ResponseFormatter.create_http_exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.PROCESSING_ERROR,
            message="Failed to analyze document",
            context={"filename": file.filename, "error": str(e)}
        )