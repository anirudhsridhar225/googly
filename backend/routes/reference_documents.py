"""
Reference Document Management API endpoints for Legal Document Severity Classification System.

This module provides FastAPI endpoints for managing reference documents including:
- Reference document upload and management
- Bucket management API endpoints for administrative operations
- Rule management endpoints for CRUD operations
- Audit log retrieval endpoints for system transparency
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, File, UploadFile, HTTPException, status, Query, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from models.legal_models import (
    Document, DocumentType, SeverityLevel, DocumentMetadata,
    Bucket, Rule, RuleCondition, RuleConditionOperator,
    FIRESTORE_COLLECTIONS
)
from processing.document_processing import DocumentProcessor
from storage.document_store import DocumentStore
from storage.bucket_manager import BucketManager
from storage.bucket_store import BucketStore
from rules.rule_store import RuleStore
from audit.audit_interface import AuditInterfaceService
from storage.firestore_client import get_firestore_client

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services (will be properly initialized in startup)
document_processor = None
document_store = None
bucket_manager = None
bucket_store = None
rule_store = None
audit_interface = None

# Request/Response Models
class ReferenceDocumentUploadRequest(BaseModel):
    """Request model for reference document upload."""
    severity_label: SeverityLevel
    tags: Optional[List[str]] = Field(default_factory=list)
    uploader_id: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)

class ReferenceDocumentResponse(BaseModel):
    """Response model for reference document."""
    document_id: str
    filename: str
    severity_label: SeverityLevel
    file_size: int
    content_hash: str
    tags: List[str]
    created_at: str
    uploader_id: Optional[str] = None
    description: Optional[str] = None

class BucketResponse(BaseModel):
    """Response model for bucket information."""
    bucket_id: str
    bucket_name: str
    document_count: int
    description: Optional[str] = None
    created_at: str
    updated_at: str

class BucketCreateRequest(BaseModel):
    """Request model for creating a bucket."""
    bucket_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    document_ids: Optional[List[str]] = Field(default_factory=list)

class RuleCreateRequest(BaseModel):
    """Request model for creating a rule."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    conditions: List[Dict[str, Any]] = Field(..., min_items=1)
    condition_logic: str = Field(default="AND", pattern="^(AND|OR)$")
    severity_override: SeverityLevel
    priority: int = Field(default=1, ge=1, le=100)
    active: bool = Field(default=True)

class RuleResponse(BaseModel):
    """Response model for rule information."""
    rule_id: str
    name: str
    description: Optional[str] = None
    conditions: List[Dict[str, Any]]
    condition_logic: str
    severity_override: SeverityLevel
    priority: int
    active: bool
    created_at: str
    updated_at: str
    created_by: Optional[str] = None

class RuleUpdateRequest(BaseModel):
    """Request model for updating a rule."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    conditions: Optional[List[Dict[str, Any]]] = Field(None, min_items=1)
    condition_logic: Optional[str] = Field(None, pattern="^(AND|OR)$")
    severity_override: Optional[SeverityLevel] = None
    priority: Optional[int] = Field(None, ge=1, le=100)
    active: Optional[bool] = None

class AuditLogResponse(BaseModel):
    """Response model for audit log entries."""
    audit_id: str
    event_type: str
    severity: str
    timestamp: str
    user_id: Optional[str] = None
    document_id: Optional[str] = None
    classification_id: Optional[str] = None
    details: Dict[str, Any]
    evidence_trail: Optional[Dict[str, Any]] = None

async def get_services():
    """Get initialized services."""
    global document_processor, document_store, bucket_manager, bucket_store, rule_store, audit_interface
    
    if not document_processor:
        document_processor = DocumentProcessor()
    if not document_store:
        firestore_client = get_firestore_client()
        document_store = DocumentStore(firestore_client)
    if not bucket_manager:
        bucket_manager = BucketManager()
    if not bucket_store:
        firestore_client = get_firestore_client()
        bucket_store = BucketStore(firestore_client)
    if not rule_store:
        firestore_client = get_firestore_client()
        rule_store = RuleStore(firestore_client)
    if not audit_interface:
        audit_interface = AuditInterfaceService()
    
    return document_processor, document_store, bucket_manager, bucket_store, rule_store, audit_interface

@router.get("/health")
async def reference_documents_health():
    """Health check endpoint for reference documents service."""
    return {
        "status": "healthy",
        "service": "reference-documents",
        "version": "1.0.0"
    }

# Reference Document Management Endpoints

@router.post(
    "/documents",
    response_model=ReferenceDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Bad Request - Invalid file or parameters"},
        413: {"description": "File too large"},
        415: {"description": "Unsupported file type"},
        500: {"description": "Internal Server Error"}
    }
)
async def upload_reference_document(
    file: UploadFile = File(...),
    severity_label: SeverityLevel = Query(...),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    uploader_id: Optional[str] = Query(None),
    description: Optional[str] = Query(None, max_length=500)
) -> ReferenceDocumentResponse:
    """
    Upload a reference document for training the classification system.
    
    Args:
        file: Reference document file (PDF, DOCX, TXT)
        severity_label: Severity level of the document
        tags: Optional comma-separated tags
        uploader_id: ID of the user uploading the document
        description: Optional description of the document
        
    Returns:
        Reference document information
        
    Raises:
        HTTPException: For file validation errors or processing failures
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )
        
        # Check file size (50MB limit for reference documents)
        file_content = await file.read()
        if len(file_content) > 50 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds 50MB limit"
            )
        
        # Reset file pointer
        await file.seek(0)
        
        # Parse tags
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # Get services
        doc_processor, doc_store, bucket_mgr, bucket_st, rule_st, audit_int = await get_services()
        
        # Process uploaded file
        text, chunks, metadata = await doc_processor.process_uploaded_file(
            file=file,
            document_type=DocumentType.REFERENCE,
            severity_label=severity_label,
            uploader_id=uploader_id,
            tags=tag_list
        )
        
        # Generate embedding (this would typically be done by embedding service)
        # For now, we'll create a placeholder - this should be integrated with embedding service
        from services.embedding_service import EmbeddingService
        embedding_service = EmbeddingService()
        embedding = await embedding_service.generate_embedding(text)
        
        # Create document model
        document = await doc_processor.create_document_model(
            text=text,
            embedding=embedding,
            metadata=metadata,
            document_type=DocumentType.REFERENCE,
            severity_label=severity_label
        )
        
        # Store document
        document_id = await doc_store.store_document(document)
        
        # Trigger bucket recomputation in background
        # This would typically be done asynchronously
        try:
            await bucket_mgr.update_buckets_with_new_document(document)
        except Exception as e:
            logger.warning(f"Failed to update buckets after document upload: {e}")
        
        # Create response
        response = ReferenceDocumentResponse(
            document_id=document_id,
            filename=metadata.filename,
            severity_label=severity_label,
            file_size=metadata.file_size or 0,
            content_hash=metadata.content_hash or "",
            tags=metadata.tags,
            created_at=metadata.upload_date.isoformat(),
            uploader_id=uploader_id,
            description=description
        )
        
        logger.info(f"Reference document uploaded successfully: {document_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading reference document {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reference document upload failed: {str(e)}"
        )

@router.get(
    "/documents",
    response_model=List[ReferenceDocumentResponse],
    responses={
        500: {"description": "Internal Server Error"}
    }
)
async def list_reference_documents(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    severity_filter: Optional[SeverityLevel] = Query(None),
    tag_filter: Optional[str] = Query(None, description="Filter by tag")
) -> List[ReferenceDocumentResponse]:
    """
    List reference documents with optional filtering.
    
    Args:
        limit: Maximum number of documents to return
        offset: Number of documents to skip
        severity_filter: Filter by severity level
        tag_filter: Filter by tag
        
    Returns:
        List of reference documents
        
    Raises:
        HTTPException: For query failures
    """
    try:
        # Get services
        doc_processor, doc_store, bucket_mgr, bucket_st, rule_st, audit_int = await get_services()
        
        # Query documents
        documents = await doc_store.list_reference_documents(
            limit=limit,
            offset=offset,
            severity_filter=severity_filter,
            tag_filter=tag_filter
        )
        
        # Convert to response format
        responses = []
        for doc in documents:
            response = ReferenceDocumentResponse(
                document_id=doc.id,
                filename=doc.metadata.filename,
                severity_label=doc.severity_label,
                file_size=doc.metadata.file_size or 0,
                content_hash=doc.metadata.content_hash or "",
                tags=doc.metadata.tags,
                created_at=doc.created_at.isoformat(),
                uploader_id=doc.metadata.uploader_id
            )
            responses.append(response)
        
        return responses
        
    except Exception as e:
        logger.error(f"Error listing reference documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list reference documents: {str(e)}"
        )

@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "Document not found"},
        500: {"description": "Internal Server Error"}
    }
)
async def delete_reference_document(document_id: str = Path(...)):
    """
    Delete a reference document.
    
    Args:
        document_id: ID of the document to delete
        
    Raises:
        HTTPException: If document not found or deletion fails
    """
    try:
        # Get services
        doc_processor, doc_store, bucket_mgr, bucket_st, rule_st, audit_int = await get_services()
        
        # Delete document
        success = await doc_store.delete_document(document_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        # Trigger bucket recomputation in background
        try:
            await bucket_mgr.recompute_buckets_after_document_deletion(document_id)
        except Exception as e:
            logger.warning(f"Failed to update buckets after document deletion: {e}")
        
        logger.info(f"Reference document deleted successfully: {document_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting reference document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete reference document: {str(e)}"
        )

# Bucket Management Endpoints

@router.get(
    "/buckets",
    response_model=List[BucketResponse],
    responses={
        500: {"description": "Internal Server Error"}
    }
)
async def list_buckets(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0)
) -> List[BucketResponse]:
    """
    List all semantic buckets.
    
    Args:
        limit: Maximum number of buckets to return
        offset: Number of buckets to skip
        
    Returns:
        List of buckets
        
    Raises:
        HTTPException: For query failures
    """
    try:
        # Get services
        doc_processor, doc_store, bucket_mgr, bucket_st, rule_st, audit_int = await get_services()
        
        # Query buckets
        buckets = await bucket_st.list_buckets(limit=limit, offset=offset)
        
        # Convert to response format
        responses = []
        for bucket in buckets:
            response = BucketResponse(
                bucket_id=bucket.bucket_id,
                bucket_name=bucket.bucket_name,
                document_count=bucket.document_count,
                description=bucket.description,
                created_at=bucket.created_at.isoformat(),
                updated_at=bucket.updated_at.isoformat()
            )
            responses.append(response)
        
        return responses
        
    except Exception as e:
        logger.error(f"Error listing buckets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list buckets: {str(e)}"
        )

@router.post(
    "/buckets/recompute",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        500: {"description": "Internal Server Error"}
    }
)
async def recompute_buckets():
    """
    Trigger recomputation of all semantic buckets.
    
    Returns:
        Acknowledgment that recomputation has started
        
    Raises:
        HTTPException: For processing failures
    """
    try:
        # Get services
        doc_processor, doc_store, bucket_mgr, bucket_st, rule_st, audit_int = await get_services()
        
        # Trigger bucket recomputation (this would typically be done in background)
        await bucket_mgr.recompute_all_buckets()
        
        logger.info("Bucket recomputation triggered successfully")
        return {"message": "Bucket recomputation started", "status": "accepted"}
        
    except Exception as e:
        logger.error(f"Error triggering bucket recomputation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger bucket recomputation: {str(e)}"
        )

@router.get(
    "/buckets/{bucket_id}",
    response_model=BucketResponse,
    responses={
        404: {"description": "Bucket not found"},
        500: {"description": "Internal Server Error"}
    }
)
async def get_bucket(bucket_id: str = Path(...)) -> BucketResponse:
    """
    Get details of a specific bucket.
    
    Args:
        bucket_id: ID of the bucket to retrieve
        
    Returns:
        Bucket details
        
    Raises:
        HTTPException: If bucket not found
    """
    try:
        # Get services
        doc_processor, doc_store, bucket_mgr, bucket_st, rule_st, audit_int = await get_services()
        
        # Get bucket
        bucket = await bucket_st.get_bucket(bucket_id)
        
        if not bucket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket {bucket_id} not found"
            )
        
        # Convert to response format
        response = BucketResponse(
            bucket_id=bucket.bucket_id,
            bucket_name=bucket.bucket_name,
            document_count=bucket.document_count,
            description=bucket.description,
            created_at=bucket.created_at.isoformat(),
            updated_at=bucket.updated_at.isoformat()
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bucket {bucket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bucket: {str(e)}"
        )

# Rule Management Endpoints

@router.post(
    "/rules",
    response_model=RuleResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Bad Request - Invalid rule data"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"}
    }
)
async def create_rule(request: RuleCreateRequest) -> RuleResponse:
    """
    Create a new classification rule.
    
    Args:
        request: Rule creation request
        
    Returns:
        Created rule information
        
    Raises:
        HTTPException: For validation errors or creation failures
    """
    try:
        # Get services
        doc_processor, doc_store, bucket_mgr, bucket_st, rule_st, audit_int = await get_services()
        
        # Convert conditions to RuleCondition objects
        rule_conditions = []
        for cond_data in request.conditions:
            condition = RuleCondition(
                operator=RuleConditionOperator(cond_data["operator"]),
                field=cond_data["field"],
                value=cond_data["value"],
                case_sensitive=cond_data.get("case_sensitive", False)
            )
            rule_conditions.append(condition)
        
        # Create rule
        rule = Rule(
            name=request.name,
            description=request.description,
            conditions=rule_conditions,
            condition_logic=RuleConditionOperator(request.condition_logic),
            severity_override=request.severity_override,
            priority=request.priority,
            active=request.active
        )
        
        # Store rule
        rule_id = await rule_st.store_rule(rule)
        
        # Convert to response format
        response = RuleResponse(
            rule_id=rule_id,
            name=rule.name,
            description=rule.description,
            conditions=[cond.model_dump() for cond in rule.conditions],
            condition_logic=rule.condition_logic.value,
            severity_override=rule.severity_override,
            priority=rule.priority,
            active=rule.active,
            created_at=rule.created_at.isoformat(),
            updated_at=rule.updated_at.isoformat(),
            created_by=rule.created_by
        )
        
        logger.info(f"Rule created successfully: {rule_id}")
        return response
        
    except ValidationError as e:
        logger.error(f"Validation error creating rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error creating rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rule creation failed: {str(e)}"
        )

@router.get(
    "/rules",
    response_model=List[RuleResponse],
    responses={
        500: {"description": "Internal Server Error"}
    }
)
async def list_rules(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    active_only: bool = Query(default=False)
) -> List[RuleResponse]:
    """
    List classification rules.
    
    Args:
        limit: Maximum number of rules to return
        offset: Number of rules to skip
        active_only: Only return active rules
        
    Returns:
        List of rules
        
    Raises:
        HTTPException: For query failures
    """
    try:
        # Get services
        doc_processor, doc_store, bucket_mgr, bucket_st, rule_st, audit_int = await get_services()
        
        # Query rules
        rules = await rule_st.list_rules(
            limit=limit,
            offset=offset,
            active_only=active_only
        )
        
        # Convert to response format
        responses = []
        for rule in rules:
            response = RuleResponse(
                rule_id=rule.rule_id,
                name=rule.name,
                description=rule.description,
                conditions=[cond.model_dump() for cond in rule.conditions],
                condition_logic=rule.condition_logic.value,
                severity_override=rule.severity_override,
                priority=rule.priority,
                active=rule.active,
                created_at=rule.created_at.isoformat(),
                updated_at=rule.updated_at.isoformat(),
                created_by=rule.created_by
            )
            responses.append(response)
        
        return responses
        
    except Exception as e:
        logger.error(f"Error listing rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list rules: {str(e)}"
        )

@router.put(
    "/rules/{rule_id}",
    response_model=RuleResponse,
    responses={
        404: {"description": "Rule not found"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"}
    }
)
async def update_rule(
    rule_id: str = Path(...),
    request: RuleUpdateRequest = ...
) -> RuleResponse:
    """
    Update an existing classification rule.
    
    Args:
        rule_id: ID of the rule to update
        request: Rule update request
        
    Returns:
        Updated rule information
        
    Raises:
        HTTPException: If rule not found or update fails
    """
    try:
        # Get services
        doc_processor, doc_store, bucket_mgr, bucket_st, rule_st, audit_int = await get_services()
        
        # Get existing rule
        existing_rule = await rule_st.get_rule(rule_id)
        if not existing_rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule {rule_id} not found"
            )
        
        # Update rule fields
        update_data = request.model_dump(exclude_unset=True)
        
        # Handle conditions update
        if "conditions" in update_data:
            rule_conditions = []
            for cond_data in update_data["conditions"]:
                condition = RuleCondition(
                    operator=RuleConditionOperator(cond_data["operator"]),
                    field=cond_data["field"],
                    value=cond_data["value"],
                    case_sensitive=cond_data.get("case_sensitive", False)
                )
                rule_conditions.append(condition)
            update_data["conditions"] = rule_conditions
        
        # Handle condition_logic update
        if "condition_logic" in update_data:
            update_data["condition_logic"] = RuleConditionOperator(update_data["condition_logic"])
        
        # Update rule
        updated_rule = await rule_st.update_rule(rule_id, update_data)
        
        # Convert to response format
        response = RuleResponse(
            rule_id=updated_rule.rule_id,
            name=updated_rule.name,
            description=updated_rule.description,
            conditions=[cond.model_dump() for cond in updated_rule.conditions],
            condition_logic=updated_rule.condition_logic.value,
            severity_override=updated_rule.severity_override,
            priority=updated_rule.priority,
            active=updated_rule.active,
            created_at=updated_rule.created_at.isoformat(),
            updated_at=updated_rule.updated_at.isoformat(),
            created_by=updated_rule.created_by
        )
        
        logger.info(f"Rule updated successfully: {rule_id}")
        return response
        
    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"Validation error updating rule {rule_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error updating rule {rule_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rule update failed: {str(e)}"
        )

@router.delete(
    "/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "Rule not found"},
        500: {"description": "Internal Server Error"}
    }
)
async def delete_rule(rule_id: str = Path(...)):
    """
    Delete a classification rule.
    
    Args:
        rule_id: ID of the rule to delete
        
    Raises:
        HTTPException: If rule not found or deletion fails
    """
    try:
        # Get services
        doc_processor, doc_store, bucket_mgr, bucket_st, rule_st, audit_int = await get_services()
        
        # Delete rule
        success = await rule_st.delete_rule(rule_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule {rule_id} not found"
            )
        
        logger.info(f"Rule deleted successfully: {rule_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting rule {rule_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete rule: {str(e)}"
        )

# Audit Log Endpoints

@router.get(
    "/audit/logs",
    response_model=List[AuditLogResponse],
    responses={
        500: {"description": "Internal Server Error"}
    }
)
async def get_audit_logs(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, description="ISO format date"),
    end_date: Optional[str] = Query(None, description="ISO format date"),
    document_id: Optional[str] = Query(None),
    classification_id: Optional[str] = Query(None)
) -> List[AuditLogResponse]:
    """
    Retrieve audit logs with optional filtering.
    
    Args:
        limit: Maximum number of logs to return
        offset: Number of logs to skip
        event_type: Filter by event type
        severity: Filter by severity level
        start_date: Filter by start date (ISO format)
        end_date: Filter by end date (ISO format)
        document_id: Filter by document ID
        classification_id: Filter by classification ID
        
    Returns:
        List of audit log entries
        
    Raises:
        HTTPException: For query failures
    """
    try:
        # Get services
        doc_processor, doc_store, bucket_mgr, bucket_st, rule_st, audit_int = await get_services()
        
        # Parse date filters
        start_datetime = None
        end_datetime = None
        if start_date:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Query audit logs
        audit_logs = await audit_int.get_audit_logs(
            limit=limit,
            offset=offset,
            event_type=event_type,
            severity=severity,
            start_date=start_datetime,
            end_date=end_datetime,
            document_id=document_id,
            classification_id=classification_id
        )
        
        # Convert to response format
        responses = []
        for log in audit_logs:
            response = AuditLogResponse(
                audit_id=log.audit_id,
                event_type=log.event_type.value,
                severity=log.severity.value,
                timestamp=log.timestamp.isoformat(),
                user_id=log.user_id,
                document_id=log.document_id,
                classification_id=log.classification_id,
                details=log.details,
                evidence_trail=log.evidence_trail.model_dump() if log.evidence_trail else None
            )
            responses.append(response)
        
        return responses
        
    except ValueError as e:
        logger.error(f"Invalid date format in audit log query: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error retrieving audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve audit logs: {str(e)}"
        )

@router.get(
    "/audit/classification/{classification_id}",
    response_model=AuditLogResponse,
    responses={
        404: {"description": "Audit log not found"},
        500: {"description": "Internal Server Error"}
    }
)
async def get_classification_audit_trail(classification_id: str = Path(...)) -> AuditLogResponse:
    """
    Get the complete audit trail for a specific classification.
    
    Args:
        classification_id: ID of the classification
        
    Returns:
        Complete audit trail for the classification
        
    Raises:
        HTTPException: If audit trail not found
    """
    try:
        # Get services
        doc_processor, doc_store, bucket_mgr, bucket_st, rule_st, audit_int = await get_services()
        
        # Get classification audit trail
        audit_log = await audit_int.get_classification_audit_trail(classification_id)
        
        if not audit_log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audit trail for classification {classification_id} not found"
            )
        
        # Convert to response format
        response = AuditLogResponse(
            audit_id=audit_log.audit_id,
            event_type=audit_log.event_type.value,
            severity=audit_log.severity.value,
            timestamp=audit_log.timestamp.isoformat(),
            user_id=audit_log.user_id,
            document_id=audit_log.document_id,
            classification_id=audit_log.classification_id,
            details=audit_log.details,
            evidence_trail=audit_log.evidence_trail.model_dump() if audit_log.evidence_trail else None
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting classification audit trail {classification_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get classification audit trail: {str(e)}"
        )