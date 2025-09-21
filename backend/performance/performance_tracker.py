"""
Performance tracking system for monitoring classification metrics and system performance.

This module implements comprehensive metrics collection for:
- Classification distribution and confidence analysis per severity class
- Bucket selection pattern monitoring and usage statistics
- Confidence calibration metrics and distribution analysis
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import statistics
import json
import logging

from storage.firestore_client import get_firestore_client
from google.cloud.firestore import Client
from models.legal_models import ClassificationResult, Bucket

logger = logging.getLogger(__name__)


@dataclass
class ClassificationMetrics:
    """Metrics for classification distribution and confidence analysis."""
    severity_class: str
    total_classifications: int
    confidence_mean: float
    confidence_median: float
    confidence_std: float
    confidence_min: float
    confidence_max: float
    low_confidence_count: int  # Below 0.7
    medium_confidence_count: int  # 0.7-0.85
    high_confidence_count: int  # Above 0.85
    rule_override_count: int
    timestamp: datetime


@dataclass
class BucketUsageMetrics:
    """Metrics for bucket selection patterns and usage statistics."""
    bucket_id: str
    bucket_name: str
    selection_count: int
    avg_similarity_score: float
    documents_contributed: int
    last_used: datetime
    usage_frequency: float  # selections per day
    effectiveness_score: float  # based on classification confidence when used


@dataclass
class ConfidenceCalibrationMetrics:
    """Metrics for confidence calibration and distribution analysis."""
    confidence_bin: str  # e.g., "0.8-0.9"
    predicted_confidence_avg: float
    actual_accuracy: Optional[float]  # When ground truth is available
    sample_count: int
    calibration_error: Optional[float]  # |predicted - actual|
    timestamp: datetime


@dataclass
class SystemPerformanceMetrics:
    """Overall system performance metrics."""
    total_classifications: int
    avg_processing_time: float
    error_rate: float
    gemini_api_latency: float
    firestore_query_latency: float
    bucket_selection_latency: float
    timestamp: datetime


class PerformanceTracker:
    """
    Tracks and analyzes system performance metrics for monitoring and evaluation.
    
    Implements requirements 7.1, 7.2, 7.3 for performance monitoring.
    """
    
    def __init__(self, firestore_client: Client = None):
        if firestore_client is None:
            self.firestore_client = get_firestore_client()
        else:
            self.firestore_client = firestore_client
        self.metrics_collection = "performance_metrics"
        self.classification_metrics_collection = "classification_metrics"
        self.bucket_metrics_collection = "bucket_usage_metrics"
        self.calibration_metrics_collection = "confidence_calibration_metrics"
        self.system_metrics_collection = "system_performance_metrics"
    
    async def track_classification(
        self,
        result: ClassificationResult,
        processing_time: float,
        bucket_id: str,
        bucket_similarity: float,
        rule_overrides: List[str] = None
    ) -> None:
        """
        Track a single classification for metrics collection.
        
        Args:
            result: Classification result
            processing_time: Time taken to process in seconds
            bucket_id: ID of the bucket used for context
            bucket_similarity: Similarity score to selected bucket
            rule_overrides: List of rule IDs that were applied
        """
        try:
            # Store individual classification record
            classification_record = {
                "classification_id": result.classification_id,
                "severity_label": result.label.value if hasattr(result.label, 'value') else str(result.label),
                "confidence": result.confidence,
                "processing_time": processing_time,
                "bucket_id": bucket_id,
                "bucket_similarity": bucket_similarity,
                "rule_overrides": rule_overrides or [],
                "confidence_warning": result.confidence_warning,
                "timestamp": datetime.utcnow(),
                "evidence_count": len(result.evidence) if result.evidence else 0
            }
            
            await self.firestore_client.add_document(
                self.classification_metrics_collection,
                classification_record
            )
            
            # Update bucket usage metrics
            await self._update_bucket_usage(bucket_id, bucket_similarity, result.confidence)
            
            logger.info(f"Tracked classification: {result.label} with confidence {result.confidence}")
            
        except Exception as e:
            logger.error(f"Error tracking classification: {e}")
    
    async def _update_bucket_usage(
        self,
        bucket_id: str,
        similarity_score: float,
        classification_confidence: float
    ) -> None:
        """Update bucket usage statistics."""
        try:
            # Get or create bucket usage record
            bucket_usage_doc = await self.firestore_client.get_document(
                self.bucket_metrics_collection,
                bucket_id
            )
            
            if bucket_usage_doc:
                # Update existing record
                usage_data = bucket_usage_doc
                usage_data["selection_count"] += 1
                usage_data["avg_similarity_score"] = (
                    (usage_data["avg_similarity_score"] * (usage_data["selection_count"] - 1) + similarity_score) /
                    usage_data["selection_count"]
                )
                usage_data["last_used"] = datetime.utcnow()
                
                # Update effectiveness score (weighted average of classification confidence)
                prev_effectiveness = usage_data.get("effectiveness_score", 0.0)
                usage_data["effectiveness_score"] = (
                    (prev_effectiveness * (usage_data["selection_count"] - 1) + classification_confidence) /
                    usage_data["selection_count"]
                )
                
                await self.firestore_client.update_document(
                    self.bucket_metrics_collection,
                    bucket_id,
                    usage_data
                )
            else:
                # Create new record
                bucket_info = await self.firestore_client.get_document("semantic_buckets", bucket_id)
                bucket_name = bucket_info.get("bucket_name", "Unknown") if bucket_info else "Unknown"
                
                usage_data = {
                    "bucket_id": bucket_id,
                    "bucket_name": bucket_name,
                    "selection_count": 1,
                    "avg_similarity_score": similarity_score,
                    "documents_contributed": bucket_info.get("document_count", 0) if bucket_info else 0,
                    "last_used": datetime.utcnow(),
                    "usage_frequency": 0.0,  # Will be calculated in aggregation
                    "effectiveness_score": classification_confidence
                }
                
                await self.firestore_client.set_document(
                    self.bucket_metrics_collection,
                    bucket_id,
                    usage_data
                )
                
        except Exception as e:
            logger.error(f"Error updating bucket usage for {bucket_id}: {e}")
    
    async def generate_classification_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[ClassificationMetrics]:
        """
        Generate classification distribution and confidence metrics per severity class.
        
        Args:
            start_date: Start date for metrics calculation
            end_date: End date for metrics calculation
            
        Returns:
            List of ClassificationMetrics for each severity class
        """
        try:
            # Query classification records in date range
            query_conditions = [
                ("timestamp", ">=", start_date),
                ("timestamp", "<=", end_date)
            ]
            
            classifications = await self.firestore_client.query_documents(
                self.classification_metrics_collection,
                query_conditions
            )
            
            # Group by severity class
            severity_groups = defaultdict(list)
            for classification in classifications:
                severity_groups[classification["severity_label"]].append(classification)
            
            metrics_list = []
            for severity_class, records in severity_groups.items():
                confidences = [r["confidence"] for r in records]
                rule_overrides = sum(1 for r in records if r.get("rule_overrides"))
                
                # Confidence distribution
                low_conf = sum(1 for c in confidences if c < 0.7)
                medium_conf = sum(1 for c in confidences if 0.7 <= c <= 0.85)
                high_conf = sum(1 for c in confidences if c > 0.85)
                
                metrics = ClassificationMetrics(
                    severity_class=severity_class,
                    total_classifications=len(records),
                    confidence_mean=statistics.mean(confidences),
                    confidence_median=statistics.median(confidences),
                    confidence_std=statistics.stdev(confidences) if len(confidences) > 1 else 0.0,
                    confidence_min=min(confidences),
                    confidence_max=max(confidences),
                    low_confidence_count=low_conf,
                    medium_confidence_count=medium_conf,
                    high_confidence_count=high_conf,
                    rule_override_count=rule_overrides,
                    timestamp=datetime.utcnow()
                )
                
                metrics_list.append(metrics)
            
            return metrics_list
            
        except Exception as e:
            logger.error(f"Error generating classification metrics: {e}")
            return []
    
    async def generate_bucket_usage_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[BucketUsageMetrics]:
        """
        Generate bucket selection pattern and usage statistics.
        
        Args:
            start_date: Start date for metrics calculation
            end_date: End date for metrics calculation
            
        Returns:
            List of BucketUsageMetrics for each bucket
        """
        try:
            # Get all bucket usage records
            bucket_usage_records = await self.firestore_client.get_all_documents(
                self.bucket_metrics_collection
            )
            
            # Calculate usage frequency based on date range
            date_range_days = (end_date - start_date).days
            if date_range_days == 0:
                date_range_days = 1
            
            metrics_list = []
            for record in bucket_usage_records:
                # Calculate usage frequency
                usage_frequency = record["selection_count"] / date_range_days
                
                metrics = BucketUsageMetrics(
                    bucket_id=record["bucket_id"],
                    bucket_name=record["bucket_name"],
                    selection_count=record["selection_count"],
                    avg_similarity_score=record["avg_similarity_score"],
                    documents_contributed=record["documents_contributed"],
                    last_used=record["last_used"],
                    usage_frequency=usage_frequency,
                    effectiveness_score=record["effectiveness_score"]
                )
                
                metrics_list.append(metrics)
            
            # Sort by selection count (most used first)
            metrics_list.sort(key=lambda x: x.selection_count, reverse=True)
            
            return metrics_list
            
        except Exception as e:
            logger.error(f"Error generating bucket usage metrics: {e}")
            return []
    
    async def generate_confidence_calibration_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
        bin_size: float = 0.1
    ) -> List[ConfidenceCalibrationMetrics]:
        """
        Generate confidence calibration metrics and distribution analysis.
        
        Args:
            start_date: Start date for metrics calculation
            end_date: End date for metrics calculation
            bin_size: Size of confidence bins (default 0.1 for 10% bins)
            
        Returns:
            List of ConfidenceCalibrationMetrics for each confidence bin
        """
        try:
            # Query classification records in date range
            query_conditions = [
                ("timestamp", ">=", start_date),
                ("timestamp", "<=", end_date)
            ]
            
            classifications = await self.firestore_client.query_documents(
                self.classification_metrics_collection,
                query_conditions
            )
            
            # Create confidence bins
            bins = {}
            for i in range(int(1.0 / bin_size)):
                bin_start = i * bin_size
                bin_end = (i + 1) * bin_size
                bin_key = f"{bin_start:.1f}-{bin_end:.1f}"
                bins[bin_key] = []
            
            # Assign classifications to bins
            for classification in classifications:
                confidence = classification["confidence"]
                bin_index = min(int(confidence / bin_size), len(bins) - 1)
                bin_key = list(bins.keys())[bin_index]
                bins[bin_key].append(classification)
            
            metrics_list = []
            for bin_key, records in bins.items():
                if not records:
                    continue
                
                confidences = [r["confidence"] for r in records]
                avg_confidence = statistics.mean(confidences)
                
                # Note: actual_accuracy would require ground truth labels
                # For now, we'll set it to None and calculate when available
                metrics = ConfidenceCalibrationMetrics(
                    confidence_bin=bin_key,
                    predicted_confidence_avg=avg_confidence,
                    actual_accuracy=None,  # Would need ground truth
                    sample_count=len(records),
                    calibration_error=None,  # Would need ground truth
                    timestamp=datetime.utcnow()
                )
                
                metrics_list.append(metrics)
            
            return metrics_list
            
        except Exception as e:
            logger.error(f"Error generating confidence calibration metrics: {e}")
            return []
    
    async def get_system_performance_summary(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get overall system performance summary.
        
        Args:
            start_date: Start date for metrics calculation
            end_date: End date for metrics calculation
            
        Returns:
            Dictionary containing system performance summary
        """
        try:
            # Get classification metrics
            classification_metrics = await self.generate_classification_metrics(start_date, end_date)
            
            # Get bucket usage metrics
            bucket_metrics = await self.generate_bucket_usage_metrics(start_date, end_date)
            
            # Get confidence calibration metrics
            calibration_metrics = await self.generate_confidence_calibration_metrics(start_date, end_date)
            
            # Calculate summary statistics
            total_classifications = sum(m.total_classifications for m in classification_metrics)
            avg_confidence = statistics.mean([m.confidence_mean for m in classification_metrics]) if classification_metrics else 0.0
            
            # Bucket usage summary
            total_buckets = len(bucket_metrics)
            active_buckets = sum(1 for b in bucket_metrics if b.selection_count > 0)
            avg_bucket_effectiveness = statistics.mean([b.effectiveness_score for b in bucket_metrics]) if bucket_metrics else 0.0
            
            # Confidence distribution summary
            total_samples = sum(m.sample_count for m in calibration_metrics)
            
            summary = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "classification_summary": {
                    "total_classifications": total_classifications,
                    "average_confidence": avg_confidence,
                    "severity_distribution": {m.severity_class: m.total_classifications for m in classification_metrics}
                },
                "bucket_usage_summary": {
                    "total_buckets": total_buckets,
                    "active_buckets": active_buckets,
                    "average_effectiveness": avg_bucket_effectiveness,
                    "most_used_bucket": bucket_metrics[0].bucket_name if bucket_metrics else None
                },
                "confidence_calibration_summary": {
                    "total_samples": total_samples,
                    "confidence_bins": len(calibration_metrics)
                },
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating system performance summary: {e}")
            return {}