"""
Confidence Calculator for Legal Document Severity Classification.

This module implements multi-factor confidence scoring that combines model confidence,
chunk similarity scores, and rule override scores to provide calibrated confidence
estimates for classification decisions.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import statistics
import math

from models.legal_models import (
    ClassificationResult, ClassificationEvidence, Rule, SeverityLevel,
    FIRESTORE_COLLECTIONS
)
from storage.firestore_client import get_firestore_client

logger = logging.getLogger(__name__)


class ConfidenceFactors:
    """Container for different confidence factors."""
    
    def __init__(
        self,
        model_confidence: float,
        chunk_similarity_score: float,
        rule_override_score: float,
        evidence_quality_score: float,
        historical_calibration_score: float = 1.0
    ):
        self.model_confidence = model_confidence
        self.chunk_similarity_score = chunk_similarity_score
        self.rule_override_score = rule_override_score
        self.evidence_quality_score = evidence_quality_score
        self.historical_calibration_score = historical_calibration_score


class ConfidenceWeights:
    """Weights for combining different confidence factors."""
    
    def __init__(
        self,
        model_weight: float = 0.4,
        chunk_similarity_weight: float = 0.25,
        rule_override_weight: float = 0.2,
        evidence_quality_weight: float = 0.1,
        historical_calibration_weight: float = 0.05
    ):
        self.model_weight = model_weight
        self.chunk_similarity_weight = chunk_similarity_weight
        self.rule_override_weight = rule_override_weight
        self.evidence_quality_weight = evidence_quality_weight
        self.historical_calibration_weight = historical_calibration_weight
        
        # Ensure weights sum to 1.0
        total_weight = (
            model_weight + chunk_similarity_weight + rule_override_weight +
            evidence_quality_weight + historical_calibration_weight
        )
        
        if abs(total_weight - 1.0) > 0.001:
            logger.warning(f"Confidence weights sum to {total_weight}, normalizing to 1.0")
            self.model_weight /= total_weight
            self.chunk_similarity_weight /= total_weight
            self.rule_override_weight /= total_weight
            self.evidence_quality_weight /= total_weight
            self.historical_calibration_weight /= total_weight


class HistoricalCalibrationData:
    """Historical data for confidence calibration."""
    
    def __init__(self):
        self.confidence_bins: Dict[str, List[float]] = {}  # severity -> [confidence_scores]
        self.accuracy_by_confidence: Dict[float, float] = {}  # confidence_bin -> accuracy
        self.total_classifications: int = 0
        self.last_updated: Optional[datetime] = None


class ConfidenceCalculator:
    """
    Multi-factor confidence calculator for classification results.
    
    Combines model confidence, chunk similarity, rule overrides, and historical
    calibration data to provide accurate confidence estimates.
    """
    
    def __init__(
        self,
        weights: Optional[ConfidenceWeights] = None,
        enable_historical_calibration: bool = True,
        calibration_window_days: int = 30
    ):
        """
        Initialize the confidence calculator.
        
        Args:
            weights: Weights for combining confidence factors
            enable_historical_calibration: Whether to use historical calibration
            calibration_window_days: Days of historical data to use for calibration
        """
        self.weights = weights or ConfidenceWeights()
        self.enable_historical_calibration = enable_historical_calibration
        self.calibration_window_days = calibration_window_days
        
        # Firestore client for historical data
        self.firestore_client = get_firestore_client()
        
        # Cache for historical calibration data
        self._calibration_cache: Optional[HistoricalCalibrationData] = None
        self._cache_expiry: Optional[datetime] = None
        
        logger.info("Initialized ConfidenceCalculator")
    
    def _calculate_chunk_similarity_score(self, evidence: List[ClassificationEvidence]) -> float:
        """
        Calculate aggregate similarity score from evidence chunks.
        
        Args:
            evidence: List of classification evidence
            
        Returns:
            Aggregate similarity score (0.0 to 1.0)
        """
        if not evidence:
            return 0.0
        
        # Use weighted average of similarity scores
        # Higher similarity scores get more weight
        similarity_scores = [e.similarity_score for e in evidence]
        
        if not similarity_scores:
            return 0.0
        
        # Calculate weighted average where higher scores get exponentially more weight
        weights = [math.exp(score * 2) for score in similarity_scores]
        weighted_sum = sum(score * weight for score, weight in zip(similarity_scores, weights))
        weight_sum = sum(weights)
        
        return weighted_sum / weight_sum if weight_sum > 0 else 0.0
    
    def _calculate_rule_override_score(
        self,
        rule_overrides: List[str],
        applied_rules: List[Rule]
    ) -> float:
        """
        Calculate confidence score based on rule overrides.
        
        Args:
            rule_overrides: List of rule IDs that were applied
            applied_rules: List of Rule objects that were applied
            
        Returns:
            Rule override confidence score (0.0 to 1.0)
        """
        if not rule_overrides or not applied_rules:
            return 0.5  # Neutral score when no rules applied
        
        # Higher priority rules and more specific rules increase confidence
        total_priority = sum(rule.priority for rule in applied_rules)
        max_possible_priority = len(applied_rules) * 100  # Max priority is 100
        
        # Calculate rule specificity based on number of conditions
        total_conditions = sum(len(rule.conditions) for rule in applied_rules)
        avg_conditions = total_conditions / len(applied_rules) if applied_rules else 1
        
        # Normalize priority score
        priority_score = min(total_priority / max_possible_priority, 1.0) if max_possible_priority > 0 else 0.5
        
        # Normalize specificity score (more conditions = higher confidence)
        specificity_score = min(avg_conditions / 5.0, 1.0)  # Assume 5 conditions is very specific
        
        # Combine priority and specificity
        rule_score = (priority_score * 0.6) + (specificity_score * 0.4)
        
        # Rule overrides generally increase confidence
        return min(0.5 + (rule_score * 0.5), 1.0)
    
    def _calculate_evidence_quality_score(self, evidence: List[ClassificationEvidence]) -> float:
        """
        Calculate evidence quality score based on evidence characteristics.
        
        Args:
            evidence: List of classification evidence
            
        Returns:
            Evidence quality score (0.0 to 1.0)
        """
        if not evidence:
            return 0.0
        
        # Factors that contribute to evidence quality:
        # 1. Number of evidence pieces (more is better, up to a point)
        # 2. Diversity of evidence sources (different buckets/documents)
        # 3. Length and quality of chunk text
        # 4. Consistency of similarity scores
        
        num_evidence = len(evidence)
        
        # Score based on number of evidence pieces (optimal around 3-5)
        if num_evidence == 0:
            quantity_score = 0.0
        elif num_evidence <= 3:
            quantity_score = num_evidence / 3.0
        elif num_evidence <= 5:
            quantity_score = 1.0
        else:
            quantity_score = max(0.7, 1.0 - (num_evidence - 5) * 0.1)
        
        # Score based on diversity of sources
        unique_documents = len(set(e.document_id for e in evidence))
        unique_buckets = len(set(e.bucket_id for e in evidence))
        diversity_score = min((unique_documents + unique_buckets) / (num_evidence + 2), 1.0)
        
        # Score based on chunk text quality (length and content)
        chunk_lengths = [len(e.chunk_text.split()) for e in evidence]
        avg_chunk_length = statistics.mean(chunk_lengths) if chunk_lengths else 0
        # Optimal chunk length is around 50-200 words
        if avg_chunk_length < 10:
            length_score = avg_chunk_length / 10.0
        elif avg_chunk_length <= 200:
            length_score = 1.0
        else:
            length_score = max(0.5, 1.0 - (avg_chunk_length - 200) / 300.0)
        
        # Score based on consistency of similarity scores
        similarity_scores = [e.similarity_score for e in evidence]
        if len(similarity_scores) > 1:
            similarity_std = statistics.stdev(similarity_scores)
            consistency_score = max(0.0, 1.0 - similarity_std * 2)  # Lower std = higher consistency
        else:
            consistency_score = 1.0
        
        # Combine all quality factors
        quality_score = (
            quantity_score * 0.3 +
            diversity_score * 0.25 +
            length_score * 0.25 +
            consistency_score * 0.2
        )
        
        return min(quality_score, 1.0)
    
    async def _get_historical_calibration_data(self) -> HistoricalCalibrationData:
        """
        Get historical calibration data from Firestore.
        
        Returns:
            HistoricalCalibrationData object
        """
        # Check cache first
        if (self._calibration_cache and self._cache_expiry and 
            datetime.utcnow() < self._cache_expiry):
            return self._calibration_cache
        
        calibration_data = HistoricalCalibrationData()
        
        try:
            # Get classifications from the last N days
            cutoff_date = datetime.utcnow() - timedelta(days=self.calibration_window_days)
            
            collection_name = FIRESTORE_COLLECTIONS['classifications']
            query = (self.firestore_client.collection(collection_name)
                    .where('created_at', '>=', cutoff_date.isoformat())
                    .where('human_reviewed', '==', True))  # Only use human-reviewed data
            
            docs = query.stream()
            
            for doc in docs:
                doc_data = doc.to_dict()
                
                # Extract relevant data
                original_label = doc_data.get('label')
                final_label = doc_data.get('final_label', original_label)
                confidence = doc_data.get('confidence', 0.0)
                
                if original_label and confidence > 0:
                    # Track confidence scores by severity level
                    if original_label not in calibration_data.confidence_bins:
                        calibration_data.confidence_bins[original_label] = []
                    calibration_data.confidence_bins[original_label].append(confidence)
                    
                    # Track accuracy by confidence bins
                    confidence_bin = round(confidence * 10) / 10  # Round to nearest 0.1
                    if confidence_bin not in calibration_data.accuracy_by_confidence:
                        calibration_data.accuracy_by_confidence[confidence_bin] = []
                    
                    # Record whether the classification was correct
                    was_correct = (original_label == final_label)
                    calibration_data.accuracy_by_confidence[confidence_bin].append(was_correct)
                    
                    calibration_data.total_classifications += 1
            
            # Calculate average accuracy for each confidence bin
            for confidence_bin, correct_flags in calibration_data.accuracy_by_confidence.items():
                accuracy = sum(correct_flags) / len(correct_flags) if correct_flags else 0.0
                calibration_data.accuracy_by_confidence[confidence_bin] = accuracy
            
            calibration_data.last_updated = datetime.utcnow()
            
            # Cache the results for 1 hour
            self._calibration_cache = calibration_data
            self._cache_expiry = datetime.utcnow() + timedelta(hours=1)
            
            logger.debug(f"Loaded calibration data: {calibration_data.total_classifications} classifications")
            
        except Exception as e:
            logger.error(f"Failed to load historical calibration data: {e}")
        
        return calibration_data
    
    def _calculate_historical_calibration_score(
        self,
        model_confidence: float,
        predicted_label: SeverityLevel,
        calibration_data: HistoricalCalibrationData
    ) -> float:
        """
        Calculate calibration score based on historical accuracy.
        
        Args:
            model_confidence: Original model confidence
            predicted_label: Predicted severity label
            calibration_data: Historical calibration data
            
        Returns:
            Calibration adjustment factor (0.5 to 1.5)
        """
        if not self.enable_historical_calibration or calibration_data.total_classifications < 10:
            return 1.0  # No adjustment if insufficient data
        
        # Get historical accuracy for this confidence level
        confidence_bin = round(model_confidence * 10) / 10
        historical_accuracy = calibration_data.accuracy_by_confidence.get(confidence_bin)
        
        if historical_accuracy is None:
            # No data for this confidence bin, use overall accuracy
            all_accuracies = list(calibration_data.accuracy_by_confidence.values())
            historical_accuracy = statistics.mean(all_accuracies) if all_accuracies else 0.5
        
        # Get historical confidence distribution for this label
        label_confidences = calibration_data.confidence_bins.get(predicted_label.value, [])
        
        if label_confidences:
            # Compare current confidence to historical distribution
            avg_historical_confidence = statistics.mean(label_confidences)
            confidence_deviation = abs(model_confidence - avg_historical_confidence)
            
            # Penalize large deviations from historical patterns
            deviation_penalty = min(confidence_deviation * 0.5, 0.3)
        else:
            deviation_penalty = 0.0
        
        # Calculate calibration factor
        # Higher historical accuracy increases confidence
        # Large deviations from historical patterns decrease confidence
        calibration_factor = (
            0.5 +  # Base factor
            (historical_accuracy - 0.5) * 0.8 -  # Accuracy adjustment
            deviation_penalty  # Deviation penalty
        )
        
        # Clamp to reasonable range
        return max(0.5, min(1.5, calibration_factor))
    
    async def calculate_confidence(
        self,
        model_confidence: float,
        evidence: List[ClassificationEvidence],
        rule_overrides: List[str],
        applied_rules: List[Rule],
        predicted_label: SeverityLevel
    ) -> Tuple[float, ConfidenceFactors]:
        """
        Calculate final confidence score combining multiple factors.
        
        Args:
            model_confidence: Original model confidence score
            evidence: List of classification evidence
            rule_overrides: List of rule IDs that were applied
            applied_rules: List of Rule objects that were applied
            predicted_label: Predicted severity label
            
        Returns:
            Tuple of (final_confidence_score, confidence_factors)
        """
        try:
            # Calculate individual confidence factors
            chunk_similarity_score = self._calculate_chunk_similarity_score(evidence)
            rule_override_score = self._calculate_rule_override_score(rule_overrides, applied_rules)
            evidence_quality_score = self._calculate_evidence_quality_score(evidence)
            
            # Get historical calibration data
            calibration_data = await self._get_historical_calibration_data()
            historical_calibration_score = self._calculate_historical_calibration_score(
                model_confidence, predicted_label, calibration_data
            )
            
            # Create confidence factors object
            factors = ConfidenceFactors(
                model_confidence=model_confidence,
                chunk_similarity_score=chunk_similarity_score,
                rule_override_score=rule_override_score,
                evidence_quality_score=evidence_quality_score,
                historical_calibration_score=historical_calibration_score
            )
            
            # Calculate weighted combination
            final_confidence = (
                factors.model_confidence * self.weights.model_weight +
                factors.chunk_similarity_score * self.weights.chunk_similarity_weight +
                factors.rule_override_score * self.weights.rule_override_weight +
                factors.evidence_quality_score * self.weights.evidence_quality_weight +
                factors.historical_calibration_score * self.weights.historical_calibration_weight
            )
            
            # Apply historical calibration adjustment
            final_confidence *= historical_calibration_score
            
            # Ensure confidence is in valid range
            final_confidence = max(0.0, min(1.0, final_confidence))
            
            logger.debug(f"Calculated confidence: {final_confidence:.3f} "
                        f"(model: {model_confidence:.3f}, "
                        f"similarity: {chunk_similarity_score:.3f}, "
                        f"rules: {rule_override_score:.3f}, "
                        f"evidence: {evidence_quality_score:.3f}, "
                        f"calibration: {historical_calibration_score:.3f})")
            
            return final_confidence, factors
            
        except Exception as e:
            logger.error(f"Failed to calculate confidence: {e}")
            # Return conservative confidence on error
            return 0.5, ConfidenceFactors(
                model_confidence=model_confidence,
                chunk_similarity_score=0.5,
                rule_override_score=0.5,
                evidence_quality_score=0.5,
                historical_calibration_score=1.0
            )
    
    async def get_confidence_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get confidence statistics for analysis.
        
        Args:
            start_date: Start date for statistics
            end_date: End date for statistics
            
        Returns:
            Dictionary with confidence statistics
        """
        try:
            collection_name = FIRESTORE_COLLECTIONS['classifications']
            query = self.firestore_client.collection(collection_name)
            
            # Apply date filters
            if start_date:
                query = query.where('created_at', '>=', start_date.isoformat())
            if end_date:
                query = query.where('created_at', '<=', end_date.isoformat())
            
            docs = query.stream()
            
            confidence_scores = []
            confidence_by_label = {}
            accuracy_by_confidence_bin = {}
            
            for doc in docs:
                doc_data = doc.to_dict()
                
                confidence = doc_data.get('confidence', 0.0)
                label = doc_data.get('label')
                final_label = doc_data.get('final_label', label)
                human_reviewed = doc_data.get('human_reviewed', False)
                
                confidence_scores.append(confidence)
                
                # Track confidence by label
                if label:
                    if label not in confidence_by_label:
                        confidence_by_label[label] = []
                    confidence_by_label[label].append(confidence)
                
                # Track accuracy by confidence bin (only for human-reviewed)
                if human_reviewed and label and final_label:
                    confidence_bin = round(confidence * 10) / 10
                    if confidence_bin not in accuracy_by_confidence_bin:
                        accuracy_by_confidence_bin[confidence_bin] = []
                    
                    was_correct = (label == final_label)
                    accuracy_by_confidence_bin[confidence_bin].append(was_correct)
            
            # Calculate statistics
            stats = {
                'total_classifications': len(confidence_scores),
                'avg_confidence': statistics.mean(confidence_scores) if confidence_scores else 0.0,
                'median_confidence': statistics.median(confidence_scores) if confidence_scores else 0.0,
                'confidence_std': statistics.stdev(confidence_scores) if len(confidence_scores) > 1 else 0.0,
                'min_confidence': min(confidence_scores) if confidence_scores else 0.0,
                'max_confidence': max(confidence_scores) if confidence_scores else 0.0,
                'confidence_by_label': {},
                'accuracy_by_confidence_bin': {},
                'confidence_distribution': {}
            }
            
            # Calculate confidence statistics by label
            for label, scores in confidence_by_label.items():
                stats['confidence_by_label'][label] = {
                    'avg': statistics.mean(scores),
                    'median': statistics.median(scores),
                    'std': statistics.stdev(scores) if len(scores) > 1 else 0.0,
                    'count': len(scores)
                }
            
            # Calculate accuracy by confidence bin
            for confidence_bin, correct_flags in accuracy_by_confidence_bin.items():
                accuracy = sum(correct_flags) / len(correct_flags) if correct_flags else 0.0
                stats['accuracy_by_confidence_bin'][confidence_bin] = {
                    'accuracy': accuracy,
                    'count': len(correct_flags)
                }
            
            # Calculate confidence distribution
            confidence_bins = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
            for i in range(len(confidence_bins) - 1):
                bin_start = confidence_bins[i]
                bin_end = confidence_bins[i + 1]
                bin_name = f"{bin_start:.1f}-{bin_end:.1f}"
                
                count = sum(1 for score in confidence_scores 
                           if bin_start <= score < bin_end or (bin_end == 1.0 and score == 1.0))
                stats['confidence_distribution'][bin_name] = count
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get confidence statistics: {e}")
            return {'error': str(e)}


# Export the main classes
__all__ = ['ConfidenceCalculator', 'ConfidenceFactors', 'ConfidenceWeights', 'HistoricalCalibrationData']