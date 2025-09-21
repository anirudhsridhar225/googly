"""
Classification API endpoints for Legal Document Severity Classification System.

This module provides FastAPI endpoints for document classification including:
- Single document classification
- Batch document classification  
- File upload handling with validation
- Classification status and result retrieval
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import uuid4
import asyncio

from fastapi import APIRouter, File, UploadFile, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime

from legal_models import (
    ClassificationResult, SeverityLevel, DocumentType, 
    Document, DocumentMetadata, FIRESTORE_COLLECTIONS
)
from document_processing import DocumentProcessor
from classification_engine import ClassificationEngine
from document_store import DocumentStore
from firestore_client import get_firestore_client
from response_formatter import (
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
        firestore_client = get_firestore_client()
        document_store = DocumentStore(firestore_client)
    
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