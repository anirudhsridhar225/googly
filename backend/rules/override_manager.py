"""
Override Manager for Legal Document Severity Classification System - Indian Law Context

This module implements rule-based classification overrides, pattern matching,
audit logging, and rule effectiveness tracking for Indian legal documents.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from models.legal_models import (
    Rule, Document, ClassificationResult, SeverityLevel,
    RuleCondition, RuleConditionOperator
)
from rules.rule_engine import RuleEngine, RuleEvaluationResult


@dataclass
class OverrideAuditLog:
    """Audit log entry for rule overrides."""
    
    log_id: str
    document_id: str
    original_classification: SeverityLevel
    override_classification: SeverityLevel
    applied_rules: List[str]
    rule_evidence: List[str]
    confidence_before: float
    confidence_after: float
    timestamp: datetime
    reasoning: str
    pattern_matches: List[str] = field(default_factory=list)


@dataclass
class RuleEffectivenessMetrics:
    """Metrics for tracking rule effectiveness."""
    
    rule_id: str
    rule_name: str
    total_applications: int = 0
    successful_overrides: int = 0
    false_positives: int = 0
    accuracy_score: float = 0.0
    last_applied: Optional[datetime] = None
    avg_confidence_improvement: float = 0.0
    indian_legal_domain_hits: Dict[str, int] = field(default_factory=dict)


class PatternMatcher:
    """
    Advanced pattern matching for Indian legal documents.
    
    Handles complex pattern matching including legal citations, 
    statutory references, and domain-specific terminology.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".PatternMatcher")
        
        # Indian legal citation patterns
        self.citation_patterns = {
            "supreme_court": [
                r'\b(AIR|SCC|SCR)\s+\d{4}\s+(SC|SCR)\s+\d+\b',
                r'\b\d{4}\s+(SCC|SCR)\s+\d+\b',
                r'\bSupreme Court.*\d{4}\b'
            ],
            "high_court": [
                r'\b(AIR|All|Bom|Cal|Del|Ker|Mad|P&H)\s+\d{4}\s+\w+\s+\d+\b',
                r'\bHigh Court.*\d{4}\b'
            ],
            "statutory": [
                r'\b(Section|Sec\.?)\s+\d+[A-Z]?(\(\d+\))?\s+(of\s+.*Act|IPC|CrPC|CPC)\b',
                r'\b(Article|Art\.?)\s+\d+[A-Z]?\s+(of.*Constitution|Constitution)\b',
                r'\b(Rule|Order)\s+\d+[A-Z]?\s+of\s+.*Rules?\b'
            ]
        }
        
        # Indian legal domain patterns
        self.domain_patterns = {
            "criminal_critical": [
                r'\b(Section\s+302|murder|culpable homicide)\b',
                r'\b(Section\s+376|rape|sexual assault)\b',
                r'\b(Section\s+420|cheating|fraud)\b',
                r'\b(POCSO|dowry death|Section\s+304B)\b'
            ],
            "constitutional_high": [
                r'\b(fundamental rights|Article\s+1[4-9]|Article\s+2[0-9]|Article\s+3[0-2])\b',
                r'\b(writ petition|habeas corpus|mandamus|certiorari)\b',
                r'\b(judicial review|constitutional validity)\b'
            ],
            "corporate_medium": [
                r'\b(Companies Act|SEBI|ROC|corporate governance)\b',
                r'\b(board resolution|shareholders|directors)\b',
                r'\b(merger|acquisition|listing)\b'
            ],
            "tax_high": [
                r'\b(tax evasion|penalty|assessment)\b',
                r'\b(GST|income tax|customs|excise)\b',
                r'\b(advance ruling|tribunal)\b'
            ]
        }
    
    def find_pattern_matches(
        self, 
        text: str, 
        rule: Rule
    ) -> Tuple[List[str], Dict[str, List[str]]]:
        """
        Find pattern matches in document text based on rule conditions.
        
        Args:
            text: Document text to search
            rule: Rule containing pattern conditions
            
        Returns:
            Tuple of (matched_patterns, evidence_by_category)
        """
        matched_patterns = []
        evidence_by_category = {}
        text_lower = text.lower()
        
        # Check rule conditions for pattern matching
        for condition in rule.conditions:
            if condition.operator == RuleConditionOperator.REGEX_MATCH:
                try:
                    flags = 0 if condition.case_sensitive else re.IGNORECASE
                    pattern = re.compile(str(condition.value), flags)
                    matches = pattern.findall(text)
                    if matches:
                        matched_patterns.extend(matches)
                        evidence_by_category[f"regex_{condition.field}"] = matches
                except re.error as e:
                    self.logger.error(f"Invalid regex in rule {rule.rule_id}: {str(e)}")
        
        # Check Indian legal citation patterns
        for category, patterns in self.citation_patterns.items():
            category_matches = []
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    category_matches.extend(matches)
            
            if category_matches:
                evidence_by_category[f"citation_{category}"] = category_matches
                matched_patterns.extend(category_matches)
        
        # Check domain-specific patterns
        for domain, patterns in self.domain_patterns.items():
            domain_matches = []
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    domain_matches.extend(matches)
            
            if domain_matches:
                evidence_by_category[f"domain_{domain}"] = domain_matches
                matched_patterns.extend(domain_matches)
        
        return matched_patterns, evidence_by_category
    
    def calculate_pattern_confidence(
        self, 
        matched_patterns: List[str],
        evidence_by_category: Dict[str, List[str]],
        rule: Rule
    ) -> float:
        """
        Calculate confidence score based on pattern matches.
        
        Args:
            matched_patterns: List of matched patterns
            evidence_by_category: Evidence organized by category
            rule: Rule being evaluated
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not matched_patterns:
            return 0.0
        
        base_confidence = 0.8
        
        # Boost confidence for high-quality legal citations
        if any("citation_supreme_court" in key for key in evidence_by_category.keys()):
            base_confidence += 0.15
        elif any("citation_high_court" in key for key in evidence_by_category.keys()):
            base_confidence += 0.10
        
        # Boost confidence for statutory references
        if any("citation_statutory" in key for key in evidence_by_category.keys()):
            base_confidence += 0.05
        
        # Boost confidence for domain-specific critical patterns
        critical_domains = ["criminal_critical", "constitutional_high", "tax_high"]
        if any(f"domain_{domain}" in evidence_by_category for domain in critical_domains):
            base_confidence += 0.10
        
        # Adjust based on rule priority
        priority_factor = min(rule.priority / 100.0, 0.1)
        base_confidence += priority_factor
        
        return min(1.0, base_confidence)


class OverrideManager:
    """
    Main override manager for applying rule-based classification overrides.
    
    Handles rule matching, override application, audit logging, and 
    effectiveness tracking for Indian legal documents.
    """
    
    def __init__(self, rule_engine: RuleEngine):
        self.rule_engine = rule_engine
        self.pattern_matcher = PatternMatcher()
        self.logger = logging.getLogger(__name__ + ".OverrideManager")
        
        # In-memory storage for audit logs and metrics (in production, use Firestore)
        self.audit_logs: List[OverrideAuditLog] = []
        self.effectiveness_metrics: Dict[str, RuleEffectivenessMetrics] = {}
    
    async def apply_overrides(
        self,
        document: Document,
        original_classification: ClassificationResult,
        applicable_rules: List[Rule]
    ) -> Tuple[ClassificationResult, List[OverrideAuditLog]]:
        """
        Apply rule-based overrides to a classification result.
        
        Args:
            document: Document being classified
            original_classification: Original AI classification
            applicable_rules: List of rules to evaluate
            
        Returns:
            Tuple of (final_classification, audit_logs)
        """
        self.logger.info(
            f"Applying overrides for document {document.id} with {len(applicable_rules)} rules"
        )
        
        # Evaluate all rules against the document
        rule_evaluations = await self.rule_engine.evaluate_rules(
            document, applicable_rules, original_classification
        )
        
        # Filter matched rules
        matched_evaluations = [eval_result for eval_result in rule_evaluations if eval_result.matched]
        
        if not matched_evaluations:
            self.logger.info(f"No rule overrides applied for document {document.id}")
            return original_classification, []
        
        # Resolve conflicts and get final override
        final_severity, applied_rule_ids, override_confidence = self.rule_engine.resolve_rule_conflicts(
            matched_evaluations, applicable_rules
        )
        
        # Create override classification result
        override_classification = self._create_override_classification(
            original_classification,
            final_severity,
            applied_rule_ids,
            override_confidence,
            matched_evaluations
        )
        
        # Generate audit logs
        audit_logs = await self._generate_audit_logs(
            document,
            original_classification,
            override_classification,
            matched_evaluations,
            applicable_rules
        )
        
        # Update effectiveness metrics
        await self._update_effectiveness_metrics(
            applied_rule_ids,
            applicable_rules,
            original_classification,
            override_classification
        )
        
        self.logger.info(
            f"Applied {len(applied_rule_ids)} rule overrides for document {document.id}: "
            f"{original_classification.label} -> {override_classification.label}"
        )
        
        return override_classification, audit_logs
    
    def _create_override_classification(
        self,
        original: ClassificationResult,
        override_severity: SeverityLevel,
        applied_rule_ids: List[str],
        override_confidence: float,
        matched_evaluations: List[RuleEvaluationResult]
    ) -> ClassificationResult:
        """Create a new classification result with rule overrides applied."""
        
        # Combine original rationale with rule reasoning
        rule_reasoning = []
        for eval_result in matched_evaluations:
            if eval_result.rule_id in applied_rule_ids:
                rule_reasoning.append(
                    f"Rule override applied: {eval_result.matched_conditions}"
                )
        
        combined_rationale = f"{original.rationale}\n\nRule Overrides Applied:\n" + "\n".join(rule_reasoning)
        
        # Create new classification result
        override_result = ClassificationResult(
            classification_id=original.classification_id,
            document_id=original.document_id,
            label=override_severity,
            confidence=override_confidence,
            rationale=combined_rationale,
            evidence=original.evidence,
            bucket_id=original.bucket_id,
            rule_overrides=applied_rule_ids,
            routing_decision=original.routing_decision,
            model_version=original.model_version,
            created_at=original.created_at
        )
        
        return override_result
    
    async def _generate_audit_logs(
        self,
        document: Document,
        original: ClassificationResult,
        override: ClassificationResult,
        matched_evaluations: List[RuleEvaluationResult],
        applicable_rules: List[Rule]
    ) -> List[OverrideAuditLog]:
        """Generate comprehensive audit logs for rule overrides."""
        
        audit_logs = []
        rule_lookup = {rule.rule_id: rule for rule in applicable_rules}
        
        for eval_result in matched_evaluations:
            if eval_result.rule_id in override.rule_overrides:
                rule = rule_lookup[eval_result.rule_id]
                
                # Find pattern matches for this rule
                pattern_matches, evidence_by_category = self.pattern_matcher.find_pattern_matches(
                    document.text, rule
                )
                
                audit_log = OverrideAuditLog(
                    log_id=f"audit_{document.id}_{eval_result.rule_id}_{int(datetime.utcnow().timestamp())}",
                    document_id=document.id,
                    original_classification=original.label,
                    override_classification=override.label,
                    applied_rules=[eval_result.rule_id],
                    rule_evidence=eval_result.evidence,
                    confidence_before=original.confidence,
                    confidence_after=override.confidence,
                    timestamp=datetime.utcnow(),
                    reasoning=f"Rule '{rule.name}' matched with conditions: {eval_result.matched_conditions}",
                    pattern_matches=pattern_matches
                )
                
                audit_logs.append(audit_log)
                self.audit_logs.append(audit_log)
        
        return audit_logs
    
    async def _update_effectiveness_metrics(
        self,
        applied_rule_ids: List[str],
        applicable_rules: List[Rule],
        original: ClassificationResult,
        override: ClassificationResult
    ) -> None:
        """Update rule effectiveness metrics."""
        
        rule_lookup = {rule.rule_id: rule for rule in applicable_rules}
        
        for rule_id in applied_rule_ids:
            if rule_id not in self.effectiveness_metrics:
                rule = rule_lookup[rule_id]
                self.effectiveness_metrics[rule_id] = RuleEffectivenessMetrics(
                    rule_id=rule_id,
                    rule_name=rule.name
                )
            
            metrics = self.effectiveness_metrics[rule_id]
            metrics.total_applications += 1
            metrics.last_applied = datetime.utcnow()
            
            # Calculate confidence improvement
            confidence_improvement = override.confidence - original.confidence
            if metrics.total_applications == 1:
                metrics.avg_confidence_improvement = confidence_improvement
            else:
                # Running average
                metrics.avg_confidence_improvement = (
                    (metrics.avg_confidence_improvement * (metrics.total_applications - 1) + confidence_improvement)
                    / metrics.total_applications
                )
            
            # For now, assume all overrides are successful (in production, this would be validated)
            metrics.successful_overrides += 1
            metrics.accuracy_score = metrics.successful_overrides / metrics.total_applications
    
    def get_rule_effectiveness_report(self, rule_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate rule effectiveness report.
        
        Args:
            rule_id: Optional specific rule ID to report on
            
        Returns:
            Dictionary containing effectiveness metrics
        """
        if rule_id and rule_id in self.effectiveness_metrics:
            metrics = self.effectiveness_metrics[rule_id]
            return {
                "rule_id": metrics.rule_id,
                "rule_name": metrics.rule_name,
                "total_applications": metrics.total_applications,
                "successful_overrides": metrics.successful_overrides,
                "accuracy_score": metrics.accuracy_score,
                "avg_confidence_improvement": metrics.avg_confidence_improvement,
                "last_applied": metrics.last_applied.isoformat() if metrics.last_applied else None
            }
        
        # Return summary of all rules
        summary = {
            "total_rules_tracked": len(self.effectiveness_metrics),
            "total_applications": sum(m.total_applications for m in self.effectiveness_metrics.values()),
            "overall_accuracy": 0.0,
            "rules": []
        }
        
        if summary["total_applications"] > 0:
            total_successful = sum(m.successful_overrides for m in self.effectiveness_metrics.values())
            summary["overall_accuracy"] = total_successful / summary["total_applications"]
        
        for metrics in self.effectiveness_metrics.values():
            summary["rules"].append({
                "rule_id": metrics.rule_id,
                "rule_name": metrics.rule_name,
                "applications": metrics.total_applications,
                "accuracy": metrics.accuracy_score,
                "avg_confidence_improvement": metrics.avg_confidence_improvement
            })
        
        # Sort by applications (most used first)
        summary["rules"].sort(key=lambda x: x["applications"], reverse=True)
        
        return summary
    
    def get_audit_trail(
        self, 
        document_id: Optional[str] = None,
        rule_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit trail for rule overrides.
        
        Args:
            document_id: Optional filter by document ID
            rule_id: Optional filter by rule ID
            limit: Maximum number of records to return
            
        Returns:
            List of audit log entries
        """
        filtered_logs = self.audit_logs
        
        if document_id:
            filtered_logs = [log for log in filtered_logs if log.document_id == document_id]
        
        if rule_id:
            filtered_logs = [log for log in filtered_logs if rule_id in log.applied_rules]
        
        # Sort by timestamp (most recent first)
        filtered_logs.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Limit results
        filtered_logs = filtered_logs[:limit]
        
        # Convert to dictionaries for JSON serialization
        return [
            {
                "log_id": log.log_id,
                "document_id": log.document_id,
                "original_classification": log.original_classification.value,
                "override_classification": log.override_classification.value,
                "applied_rules": log.applied_rules,
                "rule_evidence": log.rule_evidence,
                "confidence_before": log.confidence_before,
                "confidence_after": log.confidence_after,
                "timestamp": log.timestamp.isoformat(),
                "reasoning": log.reasoning,
                "pattern_matches": log.pattern_matches
            }
            for log in filtered_logs
        ]


# Export main classes
__all__ = [
    'OverrideAuditLog',
    'RuleEffectivenessMetrics',
    'PatternMatcher',
    'OverrideManager'
]