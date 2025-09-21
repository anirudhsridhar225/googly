"""
Performance reporting system for generating and exporting performance analysis reports.

This module implements performance report generation, metrics storage in Firestore,
and dashboard/export functionality for the legal document classification system.
"""

import json
import csv
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
import logging

from firestore_wrapper import FirestoreWrapper
from performance.performance_tracker import (
    PerformanceTracker,
    ClassificationMetrics,
    BucketUsageMetrics,
    ConfidenceCalibrationMetrics
)

logger = logging.getLogger(__name__)


@dataclass
class PerformanceReport:
    """Comprehensive performance report containing all metrics and analysis."""
    report_id: str
    report_type: str  # "daily", "weekly", "monthly", "custom"
    period_start: datetime
    period_end: datetime
    generated_at: datetime
    
    # Summary statistics
    total_classifications: int
    average_confidence: float
    classification_distribution: Dict[str, int]
    
    # Detailed metrics
    classification_metrics: List[ClassificationMetrics]
    bucket_usage_metrics: List[BucketUsageMetrics]
    confidence_calibration_metrics: List[ConfidenceCalibrationMetrics]
    
    # Analysis insights
    top_performing_buckets: List[Dict[str, Any]]
    confidence_trends: Dict[str, Any]
    performance_insights: List[str]
    
    # Metadata
    total_buckets: int
    active_buckets: int
    rule_override_rate: float


@dataclass
class DashboardMetrics:
    """Real-time dashboard metrics for monitoring system performance."""
    timestamp: datetime
    
    # Current period metrics (last 24 hours)
    classifications_today: int
    average_confidence_today: float
    low_confidence_alerts: int
    
    # Trending metrics (last 7 days)
    classification_trend: List[Dict[str, Any]]  # Daily counts
    confidence_trend: List[Dict[str, Any]]  # Daily averages
    bucket_usage_trend: List[Dict[str, Any]]  # Most used buckets
    
    # System health indicators
    error_rate: float
    processing_latency_avg: float
    bucket_effectiveness: float
    
    # Alerts and warnings
    active_alerts: List[Dict[str, Any]]


class PerformanceReporter:
    """
    Generates performance reports and provides dashboard metrics.
    
    Implements requirements 7.4, 7.5 for performance reporting and analytics.
    """
    
    def __init__(self, firestore_wrapper: FirestoreWrapper, performance_tracker: PerformanceTracker):
        self.firestore_wrapper = firestore_wrapper
        self.performance_tracker = performance_tracker
        self.reports_collection = "performance_reports"
        self.dashboard_metrics_collection = "dashboard_metrics"
    
    async def generate_performance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        report_type: str = "custom"
    ) -> PerformanceReport:
        """
        Generate a comprehensive performance report for the specified period.
        
        Args:
            start_date: Start date for the report period
            end_date: End date for the report period
            report_type: Type of report (daily, weekly, monthly, custom)
            
        Returns:
            PerformanceReport: Complete performance report
        """
        try:
            logger.info(f"Generating {report_type} performance report for {start_date} to {end_date}")
            
            # Generate all metrics
            classification_metrics = await self.performance_tracker.generate_classification_metrics(
                start_date, end_date
            )
            bucket_usage_metrics = await self.performance_tracker.generate_bucket_usage_metrics(
                start_date, end_date
            )
            confidence_calibration_metrics = await self.performance_tracker.generate_confidence_calibration_metrics(
                start_date, end_date
            )
            
            # Calculate summary statistics
            total_classifications = sum(m.total_classifications for m in classification_metrics)
            avg_confidence = (
                sum(m.confidence_mean * m.total_classifications for m in classification_metrics) / 
                total_classifications if total_classifications > 0 else 0.0
            )
            
            classification_distribution = {
                m.severity_class: m.total_classifications for m in classification_metrics
            }
            
            # Analyze top performing buckets
            top_performing_buckets = self._analyze_top_buckets(bucket_usage_metrics)
            
            # Generate confidence trends analysis
            confidence_trends = self._analyze_confidence_trends(confidence_calibration_metrics)
            
            # Generate performance insights
            performance_insights = self._generate_performance_insights(
                classification_metrics, bucket_usage_metrics, confidence_calibration_metrics
            )
            
            # Calculate additional metrics
            total_buckets = len(bucket_usage_metrics)
            active_buckets = sum(1 for b in bucket_usage_metrics if b.selection_count > 0)
            rule_override_rate = (
                sum(m.rule_override_count for m in classification_metrics) / 
                total_classifications if total_classifications > 0 else 0.0
            )
            
            # Create report
            report = PerformanceReport(
                report_id=f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                report_type=report_type,
                period_start=start_date,
                period_end=end_date,
                generated_at=datetime.utcnow(),
                total_classifications=total_classifications,
                average_confidence=avg_confidence,
                classification_distribution=classification_distribution,
                classification_metrics=classification_metrics,
                bucket_usage_metrics=bucket_usage_metrics,
                confidence_calibration_metrics=confidence_calibration_metrics,
                top_performing_buckets=top_performing_buckets,
                confidence_trends=confidence_trends,
                performance_insights=performance_insights,
                total_buckets=total_buckets,
                active_buckets=active_buckets,
                rule_override_rate=rule_override_rate
            )
            
            # Store report in Firestore
            await self._store_report(report)
            
            logger.info(f"Generated performance report {report.report_id}")
            return report
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            raise
    
    async def generate_dashboard_metrics(self) -> DashboardMetrics:
        """
        Generate real-time dashboard metrics for system monitoring.
        
        Returns:
            DashboardMetrics: Current dashboard metrics
        """
        try:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = now - timedelta(days=7)
            
            # Get today's metrics
            today_summary = await self.performance_tracker.get_system_performance_summary(
                today_start, now
            )
            
            # Get weekly trend data
            classification_trend = await self._get_classification_trend(week_start, now)
            confidence_trend = await self._get_confidence_trend(week_start, now)
            bucket_usage_trend = await self._get_bucket_usage_trend(week_start, now)
            
            # Calculate system health indicators
            error_rate = await self._calculate_error_rate(today_start, now)
            processing_latency = await self._calculate_processing_latency(today_start, now)
            bucket_effectiveness = await self._calculate_bucket_effectiveness(week_start, now)
            
            # Get active alerts
            active_alerts = await self._get_active_alerts()
            
            # Count low confidence classifications today
            low_confidence_alerts = await self._count_low_confidence_today(today_start, now)
            
            dashboard_metrics = DashboardMetrics(
                timestamp=now,
                classifications_today=today_summary.get("classification_summary", {}).get("total_classifications", 0),
                average_confidence_today=today_summary.get("classification_summary", {}).get("average_confidence", 0.0),
                low_confidence_alerts=low_confidence_alerts,
                classification_trend=classification_trend,
                confidence_trend=confidence_trend,
                bucket_usage_trend=bucket_usage_trend,
                error_rate=error_rate,
                processing_latency_avg=processing_latency,
                bucket_effectiveness=bucket_effectiveness,
                active_alerts=active_alerts
            )
            
            # Store dashboard metrics
            await self._store_dashboard_metrics(dashboard_metrics)
            
            return dashboard_metrics
            
        except Exception as e:
            logger.error(f"Error generating dashboard metrics: {e}")
            raise
    
    async def export_report_json(self, report: PerformanceReport) -> str:
        """
        Export performance report as JSON string.
        
        Args:
            report: Performance report to export
            
        Returns:
            str: JSON representation of the report
        """
        try:
            # Convert dataclasses to dictionaries
            report_dict = asdict(report)
            
            # Convert datetime objects to ISO strings
            def convert_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: convert_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_datetime(item) for item in obj]
                return obj
            
            report_dict = convert_datetime(report_dict)
            
            return json.dumps(report_dict, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Error exporting report to JSON: {e}")
            raise
    
    async def export_report_csv(self, report: PerformanceReport) -> str:
        """
        Export performance report as CSV string.
        
        Args:
            report: Performance report to export
            
        Returns:
            str: CSV representation of the report
        """
        try:
            output = io.StringIO()
            
            # Write report summary
            writer = csv.writer(output)
            writer.writerow(["Performance Report Summary"])
            writer.writerow(["Report ID", report.report_id])
            writer.writerow(["Report Type", report.report_type])
            writer.writerow(["Period Start", report.period_start.isoformat()])
            writer.writerow(["Period End", report.period_end.isoformat()])
            writer.writerow(["Generated At", report.generated_at.isoformat()])
            writer.writerow(["Total Classifications", report.total_classifications])
            writer.writerow(["Average Confidence", f"{report.average_confidence:.3f}"])
            writer.writerow([])
            
            # Write classification distribution
            writer.writerow(["Classification Distribution"])
            writer.writerow(["Severity Level", "Count"])
            for severity, count in report.classification_distribution.items():
                writer.writerow([severity, count])
            writer.writerow([])
            
            # Write classification metrics
            writer.writerow(["Classification Metrics by Severity"])
            writer.writerow([
                "Severity", "Total", "Confidence Mean", "Confidence Median", 
                "Confidence Std", "Low Conf Count", "Medium Conf Count", "High Conf Count"
            ])
            for metric in report.classification_metrics:
                writer.writerow([
                    metric.severity_class,
                    metric.total_classifications,
                    f"{metric.confidence_mean:.3f}",
                    f"{metric.confidence_median:.3f}",
                    f"{metric.confidence_std:.3f}",
                    metric.low_confidence_count,
                    metric.medium_confidence_count,
                    metric.high_confidence_count
                ])
            writer.writerow([])
            
            # Write bucket usage metrics
            writer.writerow(["Bucket Usage Metrics"])
            writer.writerow([
                "Bucket Name", "Selection Count", "Avg Similarity", 
                "Usage Frequency", "Effectiveness Score"
            ])
            for metric in report.bucket_usage_metrics[:10]:  # Top 10 buckets
                writer.writerow([
                    metric.bucket_name,
                    metric.selection_count,
                    f"{metric.avg_similarity_score:.3f}",
                    f"{metric.usage_frequency:.2f}",
                    f"{metric.effectiveness_score:.3f}"
                ])
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error exporting report to CSV: {e}")
            raise
    
    async def get_stored_reports(
        self,
        limit: int = 10,
        report_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve stored performance reports from Firestore.
        
        Args:
            limit: Maximum number of reports to retrieve
            report_type: Filter by report type (optional)
            
        Returns:
            List[Dict[str, Any]]: List of stored reports
        """
        try:
            conditions = []
            if report_type:
                conditions.append(("report_type", "==", report_type))
            
            # Add ordering by generated_at (most recent first)
            # Note: This would need to be implemented in the FirestoreWrapper
            reports = await self.firestore_wrapper.query_documents(
                self.reports_collection,
                conditions
            )
            
            # Sort by generated_at in Python (since Firestore ordering isn't implemented)
            reports.sort(key=lambda x: x.get("generated_at", ""), reverse=True)
            
            return reports[:limit]
            
        except Exception as e:
            logger.error(f"Error retrieving stored reports: {e}")
            return []
    
    def _analyze_top_buckets(self, bucket_metrics: List[BucketUsageMetrics]) -> List[Dict[str, Any]]:
        """Analyze and return top performing buckets."""
        top_buckets = []
        
        # Sort by effectiveness score
        sorted_buckets = sorted(bucket_metrics, key=lambda x: x.effectiveness_score, reverse=True)
        
        for bucket in sorted_buckets[:5]:  # Top 5 buckets
            top_buckets.append({
                "bucket_name": bucket.bucket_name,
                "effectiveness_score": bucket.effectiveness_score,
                "selection_count": bucket.selection_count,
                "usage_frequency": bucket.usage_frequency,
                "avg_similarity": bucket.avg_similarity_score
            })
        
        return top_buckets
    
    def _analyze_confidence_trends(
        self, 
        calibration_metrics: List[ConfidenceCalibrationMetrics]
    ) -> Dict[str, Any]:
        """Analyze confidence calibration trends."""
        if not calibration_metrics:
            return {"bins": [], "total_samples": 0, "avg_confidence": 0.0}
        
        total_samples = sum(m.sample_count for m in calibration_metrics)
        weighted_confidence = sum(
            m.predicted_confidence_avg * m.sample_count for m in calibration_metrics
        )
        avg_confidence = weighted_confidence / total_samples if total_samples > 0 else 0.0
        
        bins_data = []
        for metric in sorted(calibration_metrics, key=lambda x: x.confidence_bin):
            bins_data.append({
                "bin": metric.confidence_bin,
                "sample_count": metric.sample_count,
                "avg_confidence": metric.predicted_confidence_avg,
                "percentage": (metric.sample_count / total_samples * 100) if total_samples > 0 else 0
            })
        
        return {
            "bins": bins_data,
            "total_samples": total_samples,
            "avg_confidence": avg_confidence
        }
    
    def _generate_performance_insights(
        self,
        classification_metrics: List[ClassificationMetrics],
        bucket_metrics: List[BucketUsageMetrics],
        calibration_metrics: List[ConfidenceCalibrationMetrics]
    ) -> List[str]:
        """Generate actionable performance insights."""
        insights = []
        
        if classification_metrics:
            # Confidence insights
            total_classifications = sum(m.total_classifications for m in classification_metrics)
            low_confidence_total = sum(m.low_confidence_count for m in classification_metrics)
            low_confidence_rate = low_confidence_total / total_classifications if total_classifications > 0 else 0
            
            if low_confidence_rate > 0.2:
                insights.append(f"High low-confidence rate ({low_confidence_rate:.1%}). Consider reviewing bucket organization or adding more reference documents.")
            
            # Rule override insights
            rule_override_total = sum(m.rule_override_count for m in classification_metrics)
            rule_override_rate = rule_override_total / total_classifications if total_classifications > 0 else 0
            
            if rule_override_rate > 0.1:
                insights.append(f"High rule override rate ({rule_override_rate:.1%}). Review rule effectiveness and AI model performance.")
        
        if bucket_metrics:
            # Bucket usage insights
            active_buckets = sum(1 for b in bucket_metrics if b.selection_count > 0)
            total_buckets = len(bucket_metrics)
            
            if active_buckets / total_buckets < 0.5:
                insights.append(f"Only {active_buckets}/{total_buckets} buckets are being used. Consider bucket consolidation or rebalancing.")
            
            # Effectiveness insights
            avg_effectiveness = sum(b.effectiveness_score for b in bucket_metrics) / len(bucket_metrics)
            if avg_effectiveness < 0.8:
                insights.append(f"Average bucket effectiveness is {avg_effectiveness:.2f}. Consider improving reference document quality.")
        
        if not insights:
            insights.append("System performance is within normal parameters.")
        
        return insights
    
    async def _get_classification_trend(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get daily classification count trend."""
        # This would query daily aggregated data
        # For now, return mock data structure
        trend = []
        current_date = start_date
        while current_date <= end_date:
            trend.append({
                "date": current_date.isoformat(),
                "count": 0  # Would be populated from actual data
            })
            current_date += timedelta(days=1)
        return trend
    
    async def _get_confidence_trend(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get daily confidence average trend."""
        # Similar to classification trend but for confidence
        trend = []
        current_date = start_date
        while current_date <= end_date:
            trend.append({
                "date": current_date.isoformat(),
                "avg_confidence": 0.0  # Would be populated from actual data
            })
            current_date += timedelta(days=1)
        return trend
    
    async def _get_bucket_usage_trend(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get bucket usage trend over time."""
        # Would return trending bucket usage data
        return []
    
    async def _calculate_error_rate(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate system error rate for the period."""
        # Would calculate based on error logs
        return 0.0
    
    async def _calculate_processing_latency(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate average processing latency."""
        # Would calculate from performance metrics
        return 0.0
    
    async def _calculate_bucket_effectiveness(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate overall bucket effectiveness."""
        bucket_metrics = await self.performance_tracker.generate_bucket_usage_metrics(start_date, end_date)
        if not bucket_metrics:
            return 0.0
        
        return sum(b.effectiveness_score for b in bucket_metrics) / len(bucket_metrics)
    
    async def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get current active system alerts."""
        # Would query alert system
        return []
    
    async def _count_low_confidence_today(self, start_date: datetime, end_date: datetime) -> int:
        """Count low confidence classifications for today."""
        conditions = [
            ("timestamp", ">=", start_date),
            ("timestamp", "<=", end_date),
            ("confidence", "<", 0.7)
        ]
        
        try:
            low_conf_classifications = await self.firestore_wrapper.query_documents(
                "classification_metrics",
                conditions
            )
            return len(low_conf_classifications)
        except Exception:
            return 0
    
    async def _store_report(self, report: PerformanceReport) -> None:
        """Store performance report in Firestore."""
        try:
            report_dict = asdict(report)
            
            # Convert datetime objects to ISO strings for Firestore
            def convert_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: convert_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_datetime(item) for item in obj]
                return obj
            
            report_dict = convert_datetime(report_dict)
            
            await self.firestore_wrapper.set_document(
                self.reports_collection,
                report.report_id,
                report_dict
            )
            
        except Exception as e:
            logger.error(f"Error storing report {report.report_id}: {e}")
            raise
    
    async def _store_dashboard_metrics(self, metrics: DashboardMetrics) -> None:
        """Store dashboard metrics in Firestore."""
        try:
            metrics_dict = asdict(metrics)
            
            # Convert datetime objects
            def convert_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: convert_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_datetime(item) for item in obj]
                return obj
            
            metrics_dict = convert_datetime(metrics_dict)
            
            # Use timestamp as document ID
            doc_id = metrics.timestamp.strftime("%Y%m%d_%H%M%S")
            
            await self.firestore_wrapper.set_document(
                self.dashboard_metrics_collection,
                doc_id,
                metrics_dict
            )
            
        except Exception as e:
            logger.error(f"Error storing dashboard metrics: {e}")
            raise