"""
Rule Engine for Legal Document Severity Classification System - Indian Law Context

This module implements deterministic rule processing for Indian legal documents,
including rule condition parsing, evaluation, and conflict resolution.
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum

from models.legal_models import (
    Rule, RuleCondition, RuleConditionOperator, Document, 
    ClassificationResult, SeverityLevel
)

logger = logging.getLogger(__name__)


class IndianLegalDomain(str, Enum):
    """Indian legal domains for specialized rule processing."""
    CONSTITUTIONAL_LAW = "constitutional_law"
    CRIMINAL_LAW = "criminal_law"
    CIVIL_LAW = "civil_law"
    CORPORATE_LAW = "corporate_law"
    LABOUR_LAW = "labour_law"
    TAX_LAW = "tax_law"
    PROPERTY_LAW = "property_law"
    FAMILY_LAW = "family_law"
    ENVIRONMENTAL_LAW = "environmental_law"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    BANKING_LAW = "banking_law"
    CONSUMER_LAW = "consumer_law"


class RuleEvaluationResult:
    """Result of rule evaluation against a document."""
    
    def __init__(
        self,
        rule_id: str,
        matched: bool,
        confidence: float = 1.0,
        matched_conditions: List[str] = None,
        evidence: List[str] = None
    ):
        self.rule_id = rule_id
        self.matched = matched
        self.confidence = confidence
        self.matched_conditions = matched_conditions or []
        self.evidence = evidence or []
        self.evaluation_timestamp = datetime.utcnow()


class RuleEngine:
    """
    Main rule engine for deterministic rule processing in Indian legal context.
    
    Handles rule condition parsing, evaluation, priority resolution, and conflict
    management for Indian legal documents.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".RuleEngine")
        
        # Indian legal keywords for enhanced rule matching
        self.indian_legal_keywords = {
            "constitutional": [
                "fundamental rights", "directive principles", "constitution", 
                "article", "amendment", "supreme court", "high court",
                "judicial review", "writ petition", "habeas corpus"
            ],
            "criminal": [
                "ipc", "indian penal code", "crpc", "criminal procedure",
                "fir", "chargesheet", "bail", "custody", "arrest",
                "murder", "theft", "fraud", "cheating", "dowry"
            ],
            "civil": [
                "cpc", "civil procedure code", "suit", "decree", "injunction",
                "damages", "specific performance", "contract", "tort",
                "negligence", "defamation"
            ],
            "corporate": [
                "companies act", "sebi", "roc", "board resolution",
                "shareholders", "directors", "compliance", "listing",
                "merger", "acquisition", "corporate governance"
            ],
            "labour": [
                "industrial disputes", "trade union", "workmen compensation",
                "factories act", "minimum wages", "provident fund",
                "gratuity", "bonus", "retrenchment", "strike"
            ],
            "tax": [
                "income tax", "gst", "customs", "excise", "service tax",
                "assessment", "penalty", "notice", "refund",
                "tax evasion", "advance ruling"
            ]
        }
    
    async def evaluate_rules(
        self, 
        document: Document, 
        rules: List[Rule],
        classification_result: Optional[ClassificationResult] = None
    ) -> List[RuleEvaluationResult]:
        """
        Evaluate all applicable rules against a document.
        
        Args:
            document: Document to evaluate
            rules: List of rules to evaluate
            classification_result: Optional existing classification result
            
        Returns:
            List of rule evaluation results
        """
        self.logger.info(f"Evaluating {len(rules)} rules against document {document.id}")
        
        evaluation_results = []
        
        # Filter active rules and sort by priority (highest first)
        active_rules = [rule for rule in rules if rule.active]
        active_rules.sort(key=lambda r: r.priority, reverse=True)
        
        for rule in active_rules:
            try:
                result = await self._evaluate_single_rule(document, rule, classification_result)
                evaluation_results.append(result)
                
                if result.matched:
                    self.logger.info(
                        f"Rule {rule.rule_id} ({rule.name}) matched document {document.id}"
                    )
                
            except Exception as e:
                self.logger.error(f"Error evaluating rule {rule.rule_id}: {str(e)}")
                # Continue with other rules even if one fails
                continue
        
        return evaluation_results
    
    async def _evaluate_single_rule(
        self,
        document: Document,
        rule: Rule,
        classification_result: Optional[ClassificationResult] = None
    ) -> RuleEvaluationResult:
        """
        Evaluate a single rule against a document.
        
        Args:
            document: Document to evaluate
            rule: Rule to evaluate
            classification_result: Optional existing classification result
            
        Returns:
            Rule evaluation result
        """
        matched_conditions = []
        evidence = []
        
        # Evaluate each condition
        condition_results = []
        for condition in rule.conditions:
            condition_matched, condition_evidence = await self._evaluate_condition(
                document, condition, classification_result
            )
            condition_results.append(condition_matched)
            
            if condition_matched:
                matched_conditions.append(f"{condition.field} {condition.operator.value} {condition.value}")
                if condition_evidence:
                    evidence.extend(condition_evidence)
        
        # Apply condition logic (AND/OR)
        if rule.condition_logic == RuleConditionOperator.AND:
            rule_matched = all(condition_results)
        elif rule.condition_logic == RuleConditionOperator.OR:
            rule_matched = any(condition_results)
        else:
            rule_matched = False
        
        # Calculate confidence based on Indian legal context
        confidence = self._calculate_rule_confidence(rule, document, rule_matched)
        
        return RuleEvaluationResult(
            rule_id=rule.rule_id,
            matched=rule_matched,
            confidence=confidence,
            matched_conditions=matched_conditions,
            evidence=evidence
        )
    
    async def _evaluate_condition(
        self,
        document: Document,
        condition: RuleCondition,
        classification_result: Optional[ClassificationResult] = None
    ) -> Tuple[bool, List[str]]:
        """
        Evaluate a single rule condition.
        
        Args:
            document: Document to evaluate
            condition: Condition to evaluate
            classification_result: Optional existing classification result
            
        Returns:
            Tuple of (condition_matched, evidence_list)
        """
        evidence = []
        
        # Get the field value from document
        field_value = self._get_field_value(document, condition.field, classification_result)
        
        if field_value is None:
            return False, evidence
        
        # Convert to string for text operations
        field_str = str(field_value)
        condition_value = str(condition.value)
        
        # Apply case sensitivity
        if not condition.case_sensitive and isinstance(field_value, str):
            field_str = field_str.lower()
            condition_value = condition_value.lower()
        
        matched = False
        
        if condition.operator == RuleConditionOperator.CONTAINS:
            matched = condition_value in field_str
            if matched:
                evidence.append(f"Found '{condition.value}' in {condition.field}")
        
        elif condition.operator == RuleConditionOperator.REGEX_MATCH:
            try:
                flags = 0 if condition.case_sensitive else re.IGNORECASE
                pattern = re.compile(condition_value, flags)
                match = pattern.search(field_str)
                matched = match is not None
                if matched:
                    evidence.append(f"Regex '{condition.value}' matched in {condition.field}: '{match.group()}'")
            except re.error as e:
                self.logger.error(f"Invalid regex pattern '{condition_value}': {str(e)}")
                matched = False
        
        elif condition.operator == RuleConditionOperator.WORD_COUNT_GT:
            word_count = len(field_str.split())
            matched = word_count > int(condition.value)
            if matched:
                evidence.append(f"Word count {word_count} > {condition.value}")
        
        elif condition.operator == RuleConditionOperator.WORD_COUNT_LT:
            word_count = len(field_str.split())
            matched = word_count < int(condition.value)
            if matched:
                evidence.append(f"Word count {word_count} < {condition.value}")
        
        # Enhanced matching for Indian legal context (only for CONTAINS operator)
        if not matched and condition.field == "text" and condition.operator == RuleConditionOperator.CONTAINS:
            matched, context_evidence = self._evaluate_indian_legal_context(
                field_str, condition_value, condition.operator
            )
            if matched:
                evidence.extend(context_evidence)
        
        return matched, evidence
    
    def _evaluate_indian_legal_context(
        self, 
        text: str, 
        condition_value: str, 
        operator: RuleConditionOperator
    ) -> Tuple[bool, List[str]]:
        """
        Enhanced evaluation for Indian legal context.
        
        Args:
            text: Document text
            condition_value: Condition value to match
            operator: Condition operator
            
        Returns:
            Tuple of (matched, evidence_list)
        """
        evidence = []
        text_lower = text.lower()
        condition_lower = condition_value.lower()
        
        # Only enhance matching if the condition value is related to Indian legal terms
        # Check for Indian legal domain keywords
        for domain, keywords in self.indian_legal_keywords.items():
            for keyword in keywords:
                # Only match if the condition value is actually looking for this keyword
                if keyword == condition_lower and keyword in text_lower:
                    evidence.append(f"Indian legal keyword '{keyword}' found in {domain} context")
                    return True, evidence
        
        # Check for Indian legal citations only if looking for citation-related terms
        citation_terms = ["citation", "air", "scc", "scr", "section", "article"]
        if any(term in condition_lower for term in citation_terms):
            citation_patterns = [
                r'\b(AIR|SCC|SCR|All|Bom|Cal|Del|Ker|Mad|P&H)\s+\d{4}\s+\w+\s+\d+\b',
                r'\b\d{4}\s+(SCC|SCR|All|Bom|Cal|Del|Ker|Mad|P&H)\s+\d+\b',
                r'\b(Section|Sec\.?|Article|Art\.?)\s+\d+[A-Z]?\b',
                r'\b(Chapter|Ch\.?)\s+[IVX]+\b'
            ]
            
            for pattern in citation_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches and operator == RuleConditionOperator.CONTAINS:
                    evidence.append(f"Indian legal citation found: {matches[0]}")
                    return True, evidence
        
        return False, evidence
    
    def _get_field_value(
        self, 
        document: Document, 
        field_path: str,
        classification_result: Optional[ClassificationResult] = None
    ) -> Any:
        """
        Get field value from document using dot notation.
        
        Args:
            document: Document object
            field_path: Field path (e.g., 'text', 'metadata.filename')
            classification_result: Optional classification result
            
        Returns:
            Field value or None if not found
        """
        try:
            # Handle special fields
            if field_path == "text":
                return document.text
            elif field_path == "document_type":
                return document.document_type.value
            elif field_path.startswith("metadata."):
                metadata_field = field_path.split(".", 1)[1]
                if hasattr(document.metadata, metadata_field):
                    return getattr(document.metadata, metadata_field)
            elif field_path.startswith("classification.") and classification_result:
                classification_field = field_path.split(".", 1)[1]
                if hasattr(classification_result, classification_field):
                    return getattr(classification_result, classification_field)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting field value for {field_path}: {str(e)}")
            return None
    
    def _calculate_rule_confidence(
        self, 
        rule: Rule, 
        document: Document, 
        matched: bool
    ) -> float:
        """
        Calculate confidence score for rule evaluation in Indian legal context.
        
        Args:
            rule: Rule that was evaluated
            document: Document that was evaluated
            matched: Whether the rule matched
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not matched:
            return 0.0
        
        base_confidence = 0.9  # High confidence for rule-based matches
        
        # Adjust confidence based on rule complexity
        condition_count = len(rule.conditions)
        if condition_count > 3:
            base_confidence *= 0.95  # Slightly lower for complex rules
        
        # Adjust confidence based on Indian legal context
        text_lower = document.text.lower()
        
        # Higher confidence for documents with Indian legal citations
        citation_indicators = [
            "air", "scc", "scr", "supreme court", "high court",
            "section", "article", "act", "code", "rules"
        ]
        
        citation_count = sum(1 for indicator in citation_indicators if indicator in text_lower)
        if citation_count > 2:
            base_confidence = min(1.0, base_confidence * 1.05)
        
        # Adjust based on rule priority
        if rule.priority > 50:
            base_confidence = min(1.0, base_confidence * 1.02)
        
        return round(base_confidence, 3)
    
    def resolve_rule_conflicts(
        self, 
        evaluation_results: List[RuleEvaluationResult],
        rules: List[Rule]
    ) -> Tuple[Optional[SeverityLevel], List[str], float]:
        """
        Resolve conflicts between multiple matching rules.
        
        Args:
            evaluation_results: List of rule evaluation results
            rules: List of original rules
            
        Returns:
            Tuple of (final_severity, applied_rule_ids, confidence)
        """
        # Filter matched rules
        matched_results = [result for result in evaluation_results if result.matched]
        
        if not matched_results:
            return None, [], 0.0
        
        # Create rule lookup
        rule_lookup = {rule.rule_id: rule for rule in rules}
        
        # Sort by priority (highest first), then by confidence
        matched_results.sort(
            key=lambda r: (
                rule_lookup[r.rule_id].priority,
                r.confidence
            ),
            reverse=True
        )
        
        # Apply highest priority rule
        highest_priority_result = matched_results[0]
        highest_priority_rule = rule_lookup[highest_priority_result.rule_id]
        
        applied_rule_ids = [highest_priority_result.rule_id]
        final_confidence = highest_priority_result.confidence
        
        # Check for conflicts with same priority
        same_priority_results = [
            result for result in matched_results
            if rule_lookup[result.rule_id].priority == highest_priority_rule.priority
        ]
        
        if len(same_priority_results) > 1:
            # Apply most restrictive severity for Indian legal context
            severity_order = {
                SeverityLevel.LOW: 1,
                SeverityLevel.MEDIUM: 2,
                SeverityLevel.HIGH: 3,
                SeverityLevel.CRITICAL: 4
            }
            
            most_restrictive_severity = max(
                [rule_lookup[result.rule_id].severity_override for result in same_priority_results],
                key=lambda s: severity_order[s]
            )
            
            # Update applied rules to include all same-priority rules
            applied_rule_ids = [
                result.rule_id for result in same_priority_results
                if rule_lookup[result.rule_id].severity_override == most_restrictive_severity
            ]
            
            # Average confidence for multiple rules
            final_confidence = sum(result.confidence for result in same_priority_results) / len(same_priority_results)
            
            return most_restrictive_severity, applied_rule_ids, final_confidence
        
        return highest_priority_rule.severity_override, applied_rule_ids, final_confidence


# Export main classes
__all__ = [
    'IndianLegalDomain',
    'RuleEvaluationResult', 
    'RuleEngine'
]