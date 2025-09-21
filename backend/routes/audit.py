"""
API Routes for Audit Interface.

This module provides FastAPI routes for audit log retrieval, analysis,
evidence presentation, report generation, and audit analytics.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from audit.audit_interface import AuditInterfaceService, ReportFormat, AuditAnalyticsTimeframe

router = APIRouter(prefix="/audit", tags=["audit"])


# Request/Response Models
class AuditLogFilter(BaseModel):
    """Filter parameters for audit log queries."""
    document_id: Optional[str] = None
    classification_id: Optional[str] = None
    session_id: Optional[str] = None
    event_types: Optional[List[str]] = None
    severity_levels: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class AuditLogResponse(BaseModel):
    """Response model for audit log queries."""
    audit_logs: List[Dict[str, Any]]
    total_count: int
    limit: int
    offset: int
    has_more: bool
    filters_applied: Dict[str, Any]


class ClassificationAuditResponse(BaseModel):
    """Response model for classification audit details."""
    classification_id: str
    total_events: int
    events_by_type: Dict[str, int]
    timeline: List[Dict[str, Any]]
    decision_trail: Optional[Dict[str, Any]] = None
    evidence_groups: List[Dict[str, Any]] = Field(default_factory=list)
    traceability: Dict[str, Any] = Field(default_factory=dict)
    performance_analysis: Dict[str, Any] = Field(default_factory=dict)
    evidence_summary: Dict[str, Any] = Field(default_factory=dict)
    performance_summary: Dict[str, Any] = Field(default_factory=dict)
    error_summary: Dict[str, Any] = Field(default_factory=dict)


class ReportRequest(BaseModel):
    """Request model for audit report generation."""
    report_format: str = Field(default="json", description="Report format (json, csv, html)")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    document_ids: Optional[List[str]] = None
    classification_ids: Optional[List[str]] = None
    include_evidence: bool = True
    include_performance: bool = True


class ReportResponse(BaseModel):
    """Response model for audit reports."""
    report_metadata: Dict[str, Any]
    report_content: Any
    success: bool


class AnalyticsRequest(BaseModel):
    """Request model for audit analytics."""
    timeframe: str = Field(default="last_week", description="Timeframe for analytics")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class AnalyticsResponse(BaseModel):
    """Response model for audit analytics."""
    timeframe: Dict[str, Any]
    event_statistics: Dict[str, Any]
    classification_trends: Dict[str, Any]
    performance_trends: Dict[str, Any]
    error_analysis: Dict[str, Any]
    system_health: Dict[str, Any]


# Dependency to get audit interface service
async def get_audit_service() -> AuditInterfaceService:
    """Get audit interface service instance."""
    return AuditInterfaceService()


@router.get("/logs", response_model=AuditLogResponse)
async def get_audit_logs(
    document_id: Optional[str] = Query(None, description="Filter by document ID"),
    classification_id: Optional[str] = Query(None, description="Filter by classification ID"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    event_types: Optional[str] = Query(None, description="Comma-separated list of event types"),
    severity_levels: Optional[str] = Query(None, description="Comma-separated list of severity levels"),
    start_time: Optional[datetime] = Query(None, description="Start time for filtering"),
    end_time: Optional[datetime] = Query(None, description="End time for filtering"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    audit_service: AuditInterfaceService = Depends(get_audit_service)
):
    """
    Retrieve audit logs with filtering and pagination.
    
    Returns paginated audit logs based on the provided filters.
    """
    try:
        # Parse comma-separated lists
        event_types_list = event_types.split(',') if event_types else None
        severity_levels_list = severity_levels.split(',') if severity_levels else None
        
        result = await audit_service.get_audit_logs(
            document_id=document_id,
            classification_id=classification_id,
            session_id=session_id,
            event_types=event_types_list,
            severity_levels=severity_levels_list,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset
        )
        
        if 'error' in result:
            raise HTTPException(status_code=500, detail=result['error'])
        
        return AuditLogResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit logs: {str(e)}")


@router.get("/classification/{classification_id}", response_model=ClassificationAuditResponse)
async def get_classification_audit_details(
    classification_id: str,
    audit_service: AuditInterfaceService = Depends(get_audit_service)
):
    """
    Get detailed audit trail for a specific classification.
    
    Returns complete audit details including evidence trails, traceability,
    and performance analysis for the specified classification.
    """
    try:
        result = await audit_service.get_classification_audit_details(classification_id)
        
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
        
        return ClassificationAuditResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get classification audit details: {str(e)}")


@router.post("/reports/generate", response_model=ReportResponse)
async def generate_audit_report(
    request: ReportRequest,
    audit_service: AuditInterfaceService = Depends(get_audit_service)
):
    """
    Generate comprehensive audit report.
    
    Generates audit reports in various formats (JSON, CSV, HTML) with
    customizable content and filtering options.
    """
    try:
        # Validate report format
        if request.report_format.lower() not in [f.value for f in ReportFormat]:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid report format. Supported formats: {[f.value for f in ReportFormat]}"
            )
        
        result = await audit_service.generate_audit_report(
            report_format=request.report_format,
            start_time=request.start_time,
            end_time=request.end_time,
            document_ids=request.document_ids,
            classification_ids=request.classification_ids,
            include_evidence=request.include_evidence,
            include_performance=request.include_performance
        )
        
        if not result.get('success', False):
            raise HTTPException(status_code=500, detail=result.get('error', 'Report generation failed'))
        
        return ReportResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate audit report: {str(e)}")


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_audit_analytics(
    timeframe: str = Query("last_week", description="Timeframe for analytics"),
    start_time: Optional[datetime] = Query(None, description="Custom start time (required for 'custom' timeframe)"),
    end_time: Optional[datetime] = Query(None, description="Custom end time (required for 'custom' timeframe)"),
    audit_service: AuditInterfaceService = Depends(get_audit_service)
):
    """
    Get audit analytics and insights.
    
    Returns comprehensive analytics including event statistics, classification trends,
    performance metrics, error analysis, and system health assessment.
    """
    try:
        # Validate timeframe
        if timeframe not in [t.value for t in AuditAnalyticsTimeframe]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid timeframe. Supported timeframes: {[t.value for t in AuditAnalyticsTimeframe]}"
            )
        
        result = await audit_service.get_audit_analytics(
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time
        )
        
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return AnalyticsResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get audit analytics: {str(e)}")


@router.get("/events/types")
async def get_available_event_types():
    """
    Get list of available audit event types.
    
    Returns all supported audit event types for filtering purposes.
    """
    try:
        from audit.audit_logger import AuditEventType
        
        event_types = [
            {
                'value': event_type.value,
                'name': event_type.name,
                'description': _get_event_type_description(event_type)
            }
            for event_type in AuditEventType
        ]
        
        return {
            'event_types': event_types,
            'total_count': len(event_types)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get event types: {str(e)}")


@router.get("/severity/levels")
async def get_available_severity_levels():
    """
    Get list of available audit severity levels.
    
    Returns all supported audit severity levels for filtering purposes.
    """
    try:
        from audit.audit_logger import AuditSeverity
        
        severity_levels = [
            {
                'value': severity.value,
                'name': severity.name,
                'description': _get_severity_description(severity)
            }
            for severity in AuditSeverity
        ]
        
        return {
            'severity_levels': severity_levels,
            'total_count': len(severity_levels)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get severity levels: {str(e)}")


@router.get("/health")
async def get_audit_system_health(
    audit_service: AuditInterfaceService = Depends(get_audit_service)
):
    """
    Get audit system health status.
    
    Returns current health status of the audit logging system.
    """
    try:
        # Get recent analytics for health assessment
        analytics = await audit_service.get_audit_analytics(timeframe="last_day")
        
        if 'error' in analytics:
            return {
                'status': 'unknown',
                'message': 'Unable to assess system health',
                'error': analytics['error']
            }
        
        system_health = analytics.get('system_health', {})
        
        return {
            'status': system_health.get('health_status', 'unknown'),
            'success_rate': system_health.get('success_rate', 0),
            'error_rate': system_health.get('error_rate', 0),
            'warning_rate': system_health.get('warning_rate', 0),
            'total_events_analyzed': system_health.get('total_events_analyzed', 0),
            'recommendations': system_health.get('recommendations', []),
            'last_assessed': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get audit system health: {str(e)}")


@router.get("/traceability/{classification_id}")
async def get_classification_traceability(
    classification_id: str,
    audit_service: AuditInterfaceService = Depends(get_audit_service)
):
    """
    Get complete traceability chain for a classification.
    
    Returns detailed traceability information including data lineage,
    decision points, and system interactions.
    """
    try:
        result = await audit_service.get_classification_audit_details(classification_id)
        
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
        
        traceability = result.get('traceability', {})
        
        if not traceability:
            raise HTTPException(status_code=404, detail="Traceability information not found")
        
        return {
            'classification_id': classification_id,
            'traceability': traceability,
            'retrieved_at': datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get traceability: {str(e)}")


@router.get("/evidence/{classification_id}")
async def get_classification_evidence(
    classification_id: str,
    audit_service: AuditInterfaceService = Depends(get_audit_service)
):
    """
    Get evidence presentation for a classification.
    
    Returns evidence grouped by buckets with detailed similarity scores
    and context information.
    """
    try:
        result = await audit_service.get_classification_audit_details(classification_id)
        
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
        
        evidence_groups = result.get('evidence_groups', [])
        
        return {
            'classification_id': classification_id,
            'evidence_groups': evidence_groups,
            'total_buckets': len(evidence_groups),
            'total_documents': sum(group.get('document_count', 0) for group in evidence_groups),
            'total_chunks': sum(group.get('chunk_count', 0) for group in evidence_groups),
            'retrieved_at': datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get evidence: {str(e)}")


def _get_event_type_description(event_type) -> str:
    """Get human-readable description for an event type."""
    descriptions = {
        'CLASSIFICATION_STARTED': 'Classification process initiated',
        'CLASSIFICATION_COMPLETED': 'Classification process completed successfully',
        'CLASSIFICATION_FAILED': 'Classification process failed',
        'CONTEXT_RETRIEVED': 'Context retrieved from semantic buckets',
        'BUCKET_SELECTED': 'Semantic bucket selected for classification',
        'EVIDENCE_COLLECTED': 'Evidence collected from reference documents',
        'RULE_APPLIED': 'Deterministic rule applied to document',
        'RULE_OVERRIDE': 'Rule override applied to classification',
        'CONFIDENCE_WARNING': 'Confidence warning triggered',
        'RESULT_STORED': 'Classification result stored in database',
        'HUMAN_REVIEW_REQUESTED': 'Human review requested for classification',
        'HUMAN_REVIEW_COMPLETED': 'Human review completed',
        'REPROCESSING_STARTED': 'Classification reprocessing initiated',
        'REPROCESSING_COMPLETED': 'Classification reprocessing completed',
        'SYSTEM_ERROR': 'System error occurred',
        'DOCUMENT_UPLOADED': 'Document uploaded to system',
        'BUCKET_CREATED': 'Semantic bucket created',
        'BUCKET_UPDATED': 'Semantic bucket updated',
        'RULE_CREATED': 'Classification rule created',
        'RULE_UPDATED': 'Classification rule updated',
        'RULE_DELETED': 'Classification rule deleted'
    }
    return descriptions.get(event_type.name, 'Unknown event type')


def _get_severity_description(severity) -> str:
    """Get human-readable description for a severity level."""
    descriptions = {
        'INFO': 'Informational event',
        'WARNING': 'Warning event that may require attention',
        'ERROR': 'Error event that indicates a problem',
        'CRITICAL': 'Critical event that requires immediate attention'
    }
    return descriptions.get(severity.name, 'Unknown severity level')


# Export router
__all__ = ['router']