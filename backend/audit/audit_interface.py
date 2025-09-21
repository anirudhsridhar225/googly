"""
Audit Interface Backend for Legal Document Classification System.

This module provides API endpoints and services for audit log retrieval, analysis,
evidence presentation, report generation, and audit analytics with traceability tracking.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from uuid import uuid4
import json
import csv
import io
from enum import Enum

from audit.audit_logger import (
    AuditLogger, AuditLogEntry, AuditEventType, AuditSeverity,
    EvidenceTrail, ClassificationDecisionTrail
)
from models.legal_models import (
    ClassificationResult, SeverityLevel, RoutingDecision,
    FIRESTORE_COLLECTIONS
)

logger = logging.getLogger(__name__)


class ReportFormat(str, Enum):
    """Supported report formats."""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    HTML = "html"


class AuditAnalyticsTimeframe(str, Enum):
    """Timeframes for audit analytics."""
    LAST_HOUR = "last_hour"
    LAST_DAY = "last_day"
    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"
    CUSTOM = "custom"


class EvidenceBucketGroup:
    """Groups evidence by bucket for audit trail presentation."""
    
    def __init__(self, bucket_id: str, bucket_name: str):
        self.bucket_id = bucket_id
        self.bucket_name = bucket_name
        self.evidence_items: List[Dict[str, Any]] = []
        self.total_similarity_score = 0.0
        self.document_count = 0
        self.chunk_count = 0
    
    def add_evidence(self, evidence_item: Dict[str, Any]) -> None:
        """Add an evidence item to this bucket group."""
        self.evidence_items.append(evidence_item)
        self.total_similarity_score += evidence_item.get('similarity_score', 0.0)
        self.document_count = len(set(item.get('document_id') for item in self.evidence_items))
        self.chunk_count = len(self.evidence_items)
    
    def get_average_similarity(self) -> float:
        """Get average similarity score for this bucket."""
        return self.total_similarity_score / len(self.evidence_items) if self.evidence_items else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'bucket_id': self.bucket_id,
            'bucket_name': self.bucket_name,
            'evidence_items': self.evidence_items,
            'total_similarity_score': self.total_similarity_score,
            'average_similarity_score': self.get_average_similarity(),
            'document_count': self.document_count,
            'chunk_count': self.chunk_count
        }


class AuditInterfaceService:
    """
    Service class for audit interface operations.
    
    Provides methods for audit log retrieval, analysis, evidence presentation,
    report generation, and audit analytics with complete traceability.
    """
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """
        Initialize the audit interface service.
        
        Args:
            audit_logger: Audit logger instance
        """
        self.audit_logger = audit_logger or AuditLogger()
        logger.info("Initialized AuditInterfaceService")
    
    async def get_audit_logs(
        self,
        document_id: Optional[str] = None,
        classification_id: Optional[str] = None,
        session_id: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        severity_levels: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Retrieve audit logs with filtering and pagination.
        
        Args:
            document_id: Filter by document ID
            classification_id: Filter by classification ID
            session_id: Filter by session ID
            event_types: Filter by event types
            severity_levels: Filter by severity levels
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            
        Returns:
            Dictionary with audit logs and metadata
        """
        try:
            # Convert string event types to enum
            event_type_enums = None
            if event_types:
                event_type_enums = [AuditEventType(et) for et in event_types if et in AuditEventType.__members__.values()]
            
            # Get audit trail
            audit_entries = await self.audit_logger.get_audit_trail(
                document_id=document_id,
                classification_id=classification_id,
                session_id=session_id,
                start_time=start_time,
                end_time=end_time,
                event_types=event_type_enums,
                limit=limit + offset  # Get extra for pagination
            )
            
            # Apply severity filter if specified
            if severity_levels:
                severity_enums = [AuditSeverity(sl) for sl in severity_levels if sl in AuditSeverity.__members__.values()]
                audit_entries = [entry for entry in audit_entries if entry.severity in severity_enums]
            
            # Apply pagination
            total_count = len(audit_entries)
            paginated_entries = audit_entries[offset:offset + limit]
            
            # Convert to dictionaries
            audit_logs = [entry.to_firestore_dict() for entry in paginated_entries]
            
            return {
                'audit_logs': audit_logs,
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count,
                'filters_applied': {
                    'document_id': document_id,
                    'classification_id': classification_id,
                    'session_id': session_id,
                    'event_types': event_types,
                    'severity_levels': severity_levels,
                    'start_time': start_time.isoformat() if start_time else None,
                    'end_time': end_time.isoformat() if end_time else None
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve audit logs: {e}")
            return {
                'error': str(e),
                'audit_logs': [],
                'total_count': 0
            }
    
    async def get_classification_audit_details(
        self,
        classification_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed audit trail for a specific classification.
        
        Args:
            classification_id: ID of the classification
            
        Returns:
            Dictionary with complete audit details
        """
        try:
            # Get complete audit trail
            audit_trail = await self.audit_logger.get_classification_audit_trail(classification_id)
            
            if 'error' in audit_trail:
                return audit_trail
            
            # Enhance with evidence presentation
            evidence_groups = await self._group_evidence_by_bucket(audit_trail)
            audit_trail['evidence_groups'] = evidence_groups
            
            # Add traceability information
            traceability = await self._build_traceability_chain(classification_id)
            audit_trail['traceability'] = traceability
            
            # Add performance analysis
            performance_analysis = await self._analyze_performance_metrics(audit_trail)
            audit_trail['performance_analysis'] = performance_analysis
            
            return audit_trail
            
        except Exception as e:
            logger.error(f"Failed to get classification audit details: {e}")
            return {'error': str(e)}
    
    async def _group_evidence_by_bucket(
        self,
        audit_trail: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Group evidence by bucket for better presentation.
        
        Args:
            audit_trail: Complete audit trail
            
        Returns:
            List of evidence groups by bucket
        """
        try:
            evidence_groups = {}
            
            # Extract evidence from decision trail
            decision_trail = audit_trail.get('decision_trail')
            if decision_trail and 'evidence_trails' in decision_trail:
                for evidence_trail in decision_trail['evidence_trails']:
                    bucket_id = evidence_trail.get('bucket_id', 'unknown')
                    bucket_name = evidence_trail.get('bucket_name', 'Unknown Bucket')
                    
                    if bucket_id not in evidence_groups:
                        evidence_groups[bucket_id] = EvidenceBucketGroup(bucket_id, bucket_name)
                    
                    # Add evidence items
                    for i, doc in enumerate(evidence_trail.get('selected_documents', [])):
                        similarity_score = evidence_trail.get('similarity_scores', [0.0])[i] if i < len(evidence_trail.get('similarity_scores', [])) else 0.0
                        context_chunk = evidence_trail.get('context_chunks', [{}])[i] if i < len(evidence_trail.get('context_chunks', [])) else {}
                        
                        evidence_item = {
                            'document_id': doc.get('document_id'),
                            'filename': doc.get('filename'),
                            'similarity_score': similarity_score,
                            'context_chunk': context_chunk.get('text', ''),
                            'chunk_id': context_chunk.get('chunk_id')
                        }
                        
                        evidence_groups[bucket_id].add_evidence(evidence_item)
            
            # Convert to list and sort by average similarity
            grouped_evidence = [group.to_dict() for group in evidence_groups.values()]
            grouped_evidence.sort(key=lambda x: x['average_similarity_score'], reverse=True)
            
            return grouped_evidence
            
        except Exception as e:
            logger.error(f"Failed to group evidence by bucket: {e}")
            return []
    
    async def _build_traceability_chain(
        self,
        classification_id: str
    ) -> Dict[str, Any]:
        """
        Build complete traceability chain for a classification.
        
        Args:
            classification_id: ID of the classification
            
        Returns:
            Dictionary with traceability information
        """
        try:
            # Get all related audit entries
            audit_entries = await self.audit_logger.get_audit_trail(
                classification_id=classification_id,
                limit=1000
            )
            
            # Build traceability chain
            traceability = {
                'classification_id': classification_id,
                'total_events': len(audit_entries),
                'event_chain': [],
                'data_lineage': {},
                'decision_points': [],
                'system_interactions': []
            }
            
            # Process each audit entry
            for entry in sorted(audit_entries, key=lambda x: x.timestamp):
                event_info = {
                    'timestamp': entry.timestamp.isoformat(),
                    'event_type': entry.event_type.value,
                    'severity': entry.severity.value,
                    'details': entry.event_details
                }
                
                traceability['event_chain'].append(event_info)
                
                # Track decision points
                if entry.event_type in [
                    AuditEventType.CLASSIFICATION_COMPLETED,
                    AuditEventType.RULE_OVERRIDE,
                    AuditEventType.CONFIDENCE_WARNING
                ]:
                    traceability['decision_points'].append(event_info)
                
                # Track system interactions
                if entry.event_type in [
                    AuditEventType.CONTEXT_RETRIEVED,
                    AuditEventType.EVIDENCE_COLLECTED,
                    AuditEventType.RESULT_STORED
                ]:
                    traceability['system_interactions'].append(event_info)
            
            # Build data lineage
            traceability['data_lineage'] = await self._build_data_lineage(audit_entries)
            
            return traceability
            
        except Exception as e:
            logger.error(f"Failed to build traceability chain: {e}")
            return {'error': str(e)}
    
    async def _build_data_lineage(
        self,
        audit_entries: List[AuditLogEntry]
    ) -> Dict[str, Any]:
        """
        Build data lineage from audit entries.
        
        Args:
            audit_entries: List of audit entries
            
        Returns:
            Dictionary with data lineage information
        """
        lineage = {
            'input_documents': set(),
            'buckets_used': set(),
            'rules_applied': set(),
            'models_used': set(),
            'output_classifications': set()
        }
        
        for entry in audit_entries:
            # Track input documents
            if entry.document_id:
                lineage['input_documents'].add(entry.document_id)
            
            # Track buckets used
            if entry.bucket_id:
                lineage['buckets_used'].add(entry.bucket_id)
            
            # Track rules applied
            if entry.rule_id:
                lineage['rules_applied'].add(entry.rule_id)
            
            # Track models used
            if entry.event_details and 'model_version' in entry.event_details:
                lineage['models_used'].add(entry.event_details['model_version'])
            
            # Track output classifications
            if entry.classification_id:
                lineage['output_classifications'].add(entry.classification_id)
        
        # Convert sets to lists for JSON serialization
        return {k: list(v) for k, v in lineage.items()}
    
    async def _analyze_performance_metrics(
        self,
        audit_trail: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze performance metrics from audit trail.
        
        Args:
            audit_trail: Complete audit trail
            
        Returns:
            Dictionary with performance analysis
        """
        try:
            performance_summary = audit_trail.get('performance_summary', {})
            
            analysis = {
                'processing_time_analysis': {},
                'resource_usage_analysis': {},
                'efficiency_metrics': {},
                'bottleneck_identification': []
            }
            
            # Analyze processing times
            if 'processing_time_ms' in performance_summary:
                processing_times = performance_summary['processing_time_ms']
                analysis['processing_time_analysis'] = {
                    'average_ms': processing_times.get('average', 0),
                    'min_ms': processing_times.get('min', 0),
                    'max_ms': processing_times.get('max', 0),
                    'total_samples': processing_times.get('count', 0)
                }
                
                # Identify bottlenecks
                if processing_times.get('max', 0) > processing_times.get('average', 0) * 2:
                    analysis['bottleneck_identification'].append({
                        'type': 'processing_time',
                        'description': 'High processing time variance detected',
                        'max_time': processing_times.get('max', 0),
                        'average_time': processing_times.get('average', 0)
                    })
            
            # Analyze resource usage
            decision_trail = audit_trail.get('decision_trail')
            if decision_trail:
                context_summary = decision_trail.get('get_complete_context', {})
                analysis['resource_usage_analysis'] = {
                    'buckets_used': context_summary.get('buckets_used', 0),
                    'evidence_documents': context_summary.get('evidence_documents', 0),
                    'context_chunks': context_summary.get('total_context_chunks', 0),
                    'rules_evaluated': context_summary.get('rules_evaluated', 0)
                }
            
            # Calculate efficiency metrics
            total_events = audit_trail.get('total_events', 0)
            error_count = audit_trail.get('error_summary', {}).get('error_count', 0)
            
            analysis['efficiency_metrics'] = {
                'success_rate': (total_events - error_count) / total_events if total_events > 0 else 0,
                'error_rate': error_count / total_events if total_events > 0 else 0,
                'total_events': total_events,
                'error_count': error_count
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze performance metrics: {e}")
            return {'error': str(e)}
    
    async def generate_audit_report(
        self,
        report_format: str = "json",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        document_ids: Optional[List[str]] = None,
        classification_ids: Optional[List[str]] = None,
        include_evidence: bool = True,
        include_performance: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive audit report.
        
        Args:
            report_format: Format for the report (json, csv, pdf, html)
            start_time: Start time for report period
            end_time: End time for report period
            document_ids: Specific document IDs to include
            classification_ids: Specific classification IDs to include
            include_evidence: Whether to include evidence details
            include_performance: Whether to include performance metrics
            
        Returns:
            Dictionary with report data and metadata
        """
        try:
            report_id = str(uuid4())
            report_timestamp = datetime.utcnow()
            
            # Set default time range if not provided
            if not start_time:
                start_time = datetime.utcnow() - timedelta(days=7)  # Last 7 days
            if not end_time:
                end_time = datetime.utcnow()
            
            # Collect audit data
            audit_data = []
            
            if classification_ids:
                # Get specific classifications
                for classification_id in classification_ids:
                    audit_trail = await self.get_classification_audit_details(classification_id)
                    if 'error' not in audit_trail:
                        audit_data.append(audit_trail)
            else:
                # Get all audit logs in time range
                audit_logs = await self.get_audit_logs(
                    start_time=start_time,
                    end_time=end_time,
                    limit=10000  # Large limit for reports
                )
                
                # Group by classification ID
                classifications = {}
                for log in audit_logs.get('audit_logs', []):
                    classification_id = log.get('classification_id')
                    if classification_id:
                        if classification_id not in classifications:
                            classifications[classification_id] = []
                        classifications[classification_id].append(log)
                
                # Get detailed audit trails for each classification
                for classification_id in classifications.keys():
                    audit_trail = await self.get_classification_audit_details(classification_id)
                    if 'error' not in audit_trail:
                        audit_data.append(audit_trail)
            
            # Generate report based on format
            if report_format.lower() == ReportFormat.JSON:
                report_content = await self._generate_json_report(
                    audit_data, include_evidence, include_performance
                )
            elif report_format.lower() == ReportFormat.CSV:
                report_content = await self._generate_csv_report(
                    audit_data, include_evidence, include_performance
                )
            elif report_format.lower() == ReportFormat.HTML:
                report_content = await self._generate_html_report(
                    audit_data, include_evidence, include_performance
                )
            else:
                return {'error': f'Unsupported report format: {report_format}'}
            
            # Generate report metadata
            report_metadata = {
                'report_id': report_id,
                'generated_at': report_timestamp.isoformat(),
                'format': report_format,
                'time_range': {
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat()
                },
                'filters': {
                    'document_ids': document_ids,
                    'classification_ids': classification_ids
                },
                'options': {
                    'include_evidence': include_evidence,
                    'include_performance': include_performance
                },
                'statistics': {
                    'total_classifications': len(audit_data),
                    'total_events': sum(trail.get('total_events', 0) for trail in audit_data),
                    'error_count': sum(trail.get('error_summary', {}).get('error_count', 0) for trail in audit_data)
                }
            }
            
            return {
                'report_metadata': report_metadata,
                'report_content': report_content,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Failed to generate audit report: {e}")
            return {'error': str(e), 'success': False}
    
    async def _generate_json_report(
        self,
        audit_data: List[Dict[str, Any]],
        include_evidence: bool,
        include_performance: bool
    ) -> Dict[str, Any]:
        """Generate JSON format audit report."""
        report = {
            'summary': {
                'total_classifications': len(audit_data),
                'classification_distribution': {},
                'routing_distribution': {},
                'error_summary': {}
            },
            'classifications': []
        }
        
        # Process each classification
        for audit_trail in audit_data:
            classification_data = {
                'classification_id': audit_trail.get('classification_id'),
                'total_events': audit_trail.get('total_events', 0),
                'timeline': audit_trail.get('timeline', [])
            }
            
            if include_evidence:
                classification_data['evidence_groups'] = audit_trail.get('evidence_groups', [])
                classification_data['traceability'] = audit_trail.get('traceability', {})
            
            if include_performance:
                classification_data['performance_analysis'] = audit_trail.get('performance_analysis', {})
            
            report['classifications'].append(classification_data)
        
        return report
    
    async def _generate_csv_report(
        self,
        audit_data: List[Dict[str, Any]],
        include_evidence: bool,
        include_performance: bool
    ) -> str:
        """Generate CSV format audit report."""
        output = io.StringIO()
        
        # Define CSV headers
        headers = [
            'classification_id', 'total_events', 'start_time', 'end_time',
            'final_label', 'confidence_score', 'routing_decision'
        ]
        
        if include_evidence:
            headers.extend(['evidence_buckets', 'total_evidence_documents', 'avg_similarity'])
        
        if include_performance:
            headers.extend(['processing_time_ms', 'error_count', 'success_rate'])
        
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        
        # Write data rows
        for audit_trail in audit_data:
            row = {
                'classification_id': audit_trail.get('classification_id', ''),
                'total_events': audit_trail.get('total_events', 0),
                'start_time': '',
                'end_time': '',
                'final_label': '',
                'confidence_score': '',
                'routing_decision': ''
            }
            
            # Extract timeline information
            timeline = audit_trail.get('timeline', [])
            if timeline:
                row['start_time'] = timeline[0].get('timestamp', '')
                row['end_time'] = timeline[-1].get('timestamp', '')
            
            # Extract decision information
            decision_trail = audit_trail.get('decision_trail', {})
            if decision_trail:
                final_decision = decision_trail.get('final_decision', {})
                row['final_label'] = final_decision.get('label', '')
                row['confidence_score'] = final_decision.get('confidence', '')
                row['routing_decision'] = final_decision.get('routing_decision', '')
            
            if include_evidence:
                evidence_groups = audit_trail.get('evidence_groups', [])
                row['evidence_buckets'] = len(evidence_groups)
                row['total_evidence_documents'] = sum(g.get('document_count', 0) for g in evidence_groups)
                avg_similarities = [g.get('average_similarity_score', 0) for g in evidence_groups]
                row['avg_similarity'] = sum(avg_similarities) / len(avg_similarities) if avg_similarities else 0
            
            if include_performance:
                performance = audit_trail.get('performance_analysis', {})
                processing_time = performance.get('processing_time_analysis', {})
                efficiency = performance.get('efficiency_metrics', {})
                row['processing_time_ms'] = processing_time.get('average_ms', '')
                row['error_count'] = efficiency.get('error_count', 0)
                row['success_rate'] = efficiency.get('success_rate', '')
            
            writer.writerow(row)
        
        return output.getvalue()
    
    async def _generate_html_report(
        self,
        audit_data: List[Dict[str, Any]],
        include_evidence: bool,
        include_performance: bool
    ) -> str:
        """Generate HTML format audit report."""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Legal Document Classification Audit Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
                .summary { margin: 20px 0; }
                .classification { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
                .timeline { margin: 10px 0; }
                .event { margin: 5px 0; padding: 5px; background-color: #f9f9f9; border-radius: 3px; }
                .evidence { margin: 10px 0; }
                .bucket { margin: 5px 0; padding: 10px; background-color: #e9f4ff; border-radius: 3px; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Legal Document Classification Audit Report</h1>
                <p>Generated: {timestamp}</p>
                <p>Total Classifications: {total_classifications}</p>
            </div>
            
            <div class="summary">
                <h2>Summary</h2>
                <p>This report contains detailed audit trails for {total_classifications} classifications.</p>
            </div>
            
            {classifications_html}
        </body>
        </html>
        """
        
        # Generate classifications HTML
        classifications_html = ""
        for i, audit_trail in enumerate(audit_data, 1):
            classification_id = audit_trail.get('classification_id', f'Unknown-{i}')
            total_events = audit_trail.get('total_events', 0)
            
            classification_html = f"""
            <div class="classification">
                <h3>Classification {i}: {classification_id}</h3>
                <p>Total Events: {total_events}</p>
                
                <div class="timeline">
                    <h4>Event Timeline</h4>
            """
            
            # Add timeline events
            for event in audit_trail.get('timeline', []):
                classification_html += f"""
                    <div class="event">
                        <strong>{event.get('timestamp', '')}</strong> - 
                        {event.get('event_type', '')} 
                        ({event.get('severity', '')})
                        <br><small>{event.get('summary', '')}</small>
                    </div>
                """
            
            classification_html += "</div>"
            
            # Add evidence if requested
            if include_evidence:
                classification_html += """
                <div class="evidence">
                    <h4>Evidence Groups</h4>
                """
                
                for evidence_group in audit_trail.get('evidence_groups', []):
                    classification_html += f"""
                    <div class="bucket">
                        <strong>{evidence_group.get('bucket_name', 'Unknown Bucket')}</strong>
                        <br>Documents: {evidence_group.get('document_count', 0)}
                        <br>Chunks: {evidence_group.get('chunk_count', 0)}
                        <br>Avg Similarity: {evidence_group.get('average_similarity_score', 0):.3f}
                    </div>
                    """
                
                classification_html += "</div>"
            
            classification_html += "</div>"
            classifications_html += classification_html
        
        # Fill template
        return html_template.format(
            timestamp=datetime.utcnow().isoformat(),
            total_classifications=len(audit_data),
            classifications_html=classifications_html
        )
    
    async def get_audit_analytics(
        self,
        timeframe: str = "last_week",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit analytics and insights.
        
        Args:
            timeframe: Predefined timeframe for analytics
            start_time: Custom start time
            end_time: Custom end time
            
        Returns:
            Dictionary with analytics data
        """
        try:
            # Determine time range
            if timeframe == AuditAnalyticsTimeframe.CUSTOM:
                if not start_time or not end_time:
                    return {'error': 'Custom timeframe requires start_time and end_time'}
            else:
                end_time = datetime.utcnow()
                if timeframe == AuditAnalyticsTimeframe.LAST_HOUR:
                    start_time = end_time - timedelta(hours=1)
                elif timeframe == AuditAnalyticsTimeframe.LAST_DAY:
                    start_time = end_time - timedelta(days=1)
                elif timeframe == AuditAnalyticsTimeframe.LAST_WEEK:
                    start_time = end_time - timedelta(weeks=1)
                elif timeframe == AuditAnalyticsTimeframe.LAST_MONTH:
                    start_time = end_time - timedelta(days=30)
            
            # Get audit logs for the timeframe
            audit_logs = await self.get_audit_logs(
                start_time=start_time,
                end_time=end_time,
                limit=10000
            )
            
            # Analyze the data
            analytics = {
                'timeframe': {
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_hours': (end_time - start_time).total_seconds() / 3600
                },
                'event_statistics': await self._analyze_event_statistics(audit_logs['audit_logs']),
                'classification_trends': await self._analyze_classification_trends(audit_logs['audit_logs']),
                'performance_trends': await self._analyze_performance_trends(audit_logs['audit_logs']),
                'error_analysis': await self._analyze_error_patterns(audit_logs['audit_logs']),
                'system_health': await self._assess_system_health(audit_logs['audit_logs'])
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get audit analytics: {e}")
            return {'error': str(e)}
    
    async def _analyze_event_statistics(self, audit_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze event statistics from audit logs."""
        event_counts = {}
        severity_counts = {}
        hourly_distribution = {}
        
        for log in audit_logs:
            # Count event types
            event_type = log.get('event_type', 'unknown')
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            # Count severity levels
            severity = log.get('severity', 'unknown')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Hourly distribution
            timestamp = log.get('timestamp', '')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    hour = dt.hour
                    hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
                except:
                    pass
        
        return {
            'total_events': len(audit_logs),
            'event_type_distribution': event_counts,
            'severity_distribution': severity_counts,
            'hourly_distribution': hourly_distribution
        }
    
    async def _analyze_classification_trends(self, audit_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze classification trends from audit logs."""
        classification_events = [
            log for log in audit_logs 
            if log.get('event_type') == 'classification_completed'
        ]
        
        label_distribution = {}
        routing_distribution = {}
        confidence_scores = []
        
        for event in classification_events:
            details = event.get('event_details', {})
            classification_summary = details.get('classification_summary', {})
            
            # Label distribution
            label = classification_summary.get('label', 'unknown')
            label_distribution[label] = label_distribution.get(label, 0) + 1
            
            # Routing distribution
            routing = classification_summary.get('routing_decision', 'unknown')
            routing_distribution[routing] = routing_distribution.get(routing, 0) + 1
            
            # Confidence scores
            confidence = classification_summary.get('confidence')
            if confidence is not None:
                confidence_scores.append(confidence)
        
        # Calculate confidence statistics
        confidence_stats = {}
        if confidence_scores:
            confidence_stats = {
                'average': sum(confidence_scores) / len(confidence_scores),
                'min': min(confidence_scores),
                'max': max(confidence_scores),
                'count': len(confidence_scores)
            }
        
        return {
            'total_classifications': len(classification_events),
            'label_distribution': label_distribution,
            'routing_distribution': routing_distribution,
            'confidence_statistics': confidence_stats
        }
    
    async def _analyze_performance_trends(self, audit_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance trends from audit logs."""
        processing_times = []
        
        for log in audit_logs:
            performance_metrics = log.get('performance_metrics', {})
            if 'processing_time_ms' in performance_metrics:
                processing_times.append(performance_metrics['processing_time_ms'])
        
        performance_stats = {}
        if processing_times:
            performance_stats = {
                'average_ms': sum(processing_times) / len(processing_times),
                'min_ms': min(processing_times),
                'max_ms': max(processing_times),
                'total_samples': len(processing_times)
            }
        
        return {
            'processing_time_statistics': performance_stats,
            'performance_samples': len(processing_times)
        }
    
    async def _analyze_error_patterns(self, audit_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze error patterns from audit logs."""
        error_logs = [
            log for log in audit_logs 
            if log.get('severity') in ['error', 'critical']
        ]
        
        error_types = {}
        error_events = {}
        
        for error_log in error_logs:
            # Count error types
            error_details = error_log.get('error_details', {})
            error_type = error_details.get('error_type', 'unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1
            
            # Count error events
            event_type = error_log.get('event_type', 'unknown')
            error_events[event_type] = error_events.get(event_type, 0) + 1
        
        return {
            'total_errors': len(error_logs),
            'error_type_distribution': error_types,
            'error_event_distribution': error_events,
            'error_rate': len(error_logs) / len(audit_logs) if audit_logs else 0
        }
    
    async def _assess_system_health(self, audit_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess overall system health from audit logs."""
        total_events = len(audit_logs)
        error_events = len([log for log in audit_logs if log.get('severity') in ['error', 'critical']])
        warning_events = len([log for log in audit_logs if log.get('severity') == 'warning'])
        
        success_rate = (total_events - error_events) / total_events if total_events > 0 else 0
        
        # Determine health status
        if success_rate >= 0.95:
            health_status = "healthy"
        elif success_rate >= 0.90:
            health_status = "warning"
        else:
            health_status = "critical"
        
        return {
            'health_status': health_status,
            'success_rate': success_rate,
            'error_rate': error_events / total_events if total_events > 0 else 0,
            'warning_rate': warning_events / total_events if total_events > 0 else 0,
            'total_events_analyzed': total_events,
            'recommendations': await self._generate_health_recommendations(success_rate, error_events, warning_events)
        }
    
    async def _generate_health_recommendations(
        self, 
        success_rate: float, 
        error_count: int, 
        warning_count: int
    ) -> List[str]:
        """Generate health recommendations based on metrics."""
        recommendations = []
        
        if success_rate < 0.90:
            recommendations.append("System success rate is below 90%. Investigate error patterns and system stability.")
        
        if error_count > 10:
            recommendations.append(f"High error count ({error_count}). Review error logs and implement fixes.")
        
        if warning_count > 20:
            recommendations.append(f"High warning count ({warning_count}). Monitor system performance and resource usage.")
        
        if success_rate >= 0.95 and error_count <= 5:
            recommendations.append("System is operating within normal parameters.")
        
        return recommendations


# Export main classes
__all__ = [
    'AuditInterfaceService',
    'EvidenceBucketGroup',
    'ReportFormat',
    'AuditAnalyticsTimeframe'
]