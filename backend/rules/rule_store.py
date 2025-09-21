"""
Rule Store for Legal Document Severity Classification System - Indian Law Context

This module implements rule CRUD operations in Firestore with proper indexing,
rule versioning, activation/deactivation, and import/export capabilities.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from uuid import uuid4

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from models.legal_models import Rule, RuleCondition, FIRESTORE_COLLECTIONS
from storage.firestore_client import get_firestore_client


class RuleVersion:
    """Represents a version of a rule for version control."""
    
    def __init__(
        self,
        version_id: str,
        rule_id: str,
        version_number: int,
        rule_data: Dict[str, Any],
        created_at: datetime,
        created_by: Optional[str] = None,
        change_description: Optional[str] = None
    ):
        self.version_id = version_id
        self.rule_id = rule_id
        self.version_number = version_number
        self.rule_data = rule_data
        self.created_at = created_at
        self.created_by = created_by
        self.change_description = change_description
    
    def to_firestore_dict(self) -> Dict[str, Any]:
        """Convert to Firestore-compatible dictionary."""
        return {
            "version_id": self.version_id,
            "rule_id": self.rule_id,
            "version_number": self.version_number,
            "rule_data": self.rule_data,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "change_description": self.change_description
        }
    
    @classmethod
    def from_firestore_dict(cls, data: Dict[str, Any]) -> "RuleVersion":
        """Create from Firestore dictionary."""
        return cls(
            version_id=data["version_id"],
            rule_id=data["rule_id"],
            version_number=data["version_number"],
            rule_data=data["rule_data"],
            created_at=datetime.fromisoformat(data["created_at"]),
            created_by=data.get("created_by"),
            change_description=data.get("change_description")
        )


class RuleImportExportFormat:
    """Standard format for rule import/export operations."""
    
    def __init__(
        self,
        rules: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        export_timestamp: datetime,
        format_version: str = "1.0"
    ):
        self.rules = rules
        self.metadata = metadata
        self.export_timestamp = export_timestamp
        self.format_version = format_version
    
    def to_json(self) -> str:
        """Convert to JSON string for export."""
        export_data = {
            "format_version": self.format_version,
            "export_timestamp": self.export_timestamp.isoformat(),
            "metadata": self.metadata,
            "rules": self.rules
        }
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> "RuleImportExportFormat":
        """Create from JSON string for import."""
        data = json.loads(json_str)
        return cls(
            rules=data["rules"],
            metadata=data["metadata"],
            export_timestamp=datetime.fromisoformat(data["export_timestamp"]),
            format_version=data.get("format_version", "1.0")
        )


class RuleStore:
    """
    Main rule storage class for Firestore operations.
    
    Handles rule CRUD operations, versioning, indexing, and import/export
    functionality for Indian legal document classification rules.
    """
    
    def __init__(self):
        self.db = get_firestore_client()
        self.logger = logging.getLogger(__name__ + ".RuleStore")
        
        # Collection references
        self.rules_collection = self.db.collection(FIRESTORE_COLLECTIONS['rules'])
        self.rule_versions_collection = self.db.collection('rule_versions')
        
        # Initialize indexes (in production, these would be created via Firestore console)
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Ensure required Firestore indexes exist (logged for manual creation)."""
        required_indexes = [
            {
                "collection": FIRESTORE_COLLECTIONS['rules'],
                "fields": [
                    {"field": "active", "order": "ASCENDING"},
                    {"field": "priority", "order": "DESCENDING"}
                ]
            },
            {
                "collection": FIRESTORE_COLLECTIONS['rules'],
                "fields": [
                    {"field": "severity_override", "order": "ASCENDING"},
                    {"field": "created_at", "order": "DESCENDING"}
                ]
            },
            {
                "collection": "rule_versions",
                "fields": [
                    {"field": "rule_id", "order": "ASCENDING"},
                    {"field": "version_number", "order": "DESCENDING"}
                ]
            }
        ]
        
        self.logger.info(f"Required Firestore indexes: {required_indexes}")
        # In production, these indexes would be created via Firestore console or CLI
    
    async def create_rule(
        self, 
        rule: Rule, 
        created_by: Optional[str] = None,
        change_description: Optional[str] = None
    ) -> str:
        """
        Create a new rule in Firestore.
        
        Args:
            rule: Rule object to create
            created_by: User ID who created the rule
            change_description: Description of the rule creation
            
        Returns:
            Rule ID of the created rule
        """
        try:
            # Ensure rule has an ID
            if not rule.rule_id:
                rule.rule_id = str(uuid4())
            
            # Set creation metadata
            rule.created_by = created_by
            rule.created_at = datetime.utcnow()
            rule.updated_at = datetime.utcnow()
            
            # Convert to Firestore format
            rule_data = rule.to_firestore_dict()
            
            # Create rule document
            doc_ref = self.rules_collection.document(rule.rule_id)
            doc_ref.set(rule_data)
            
            # Create initial version
            await self._create_rule_version(
                rule.rule_id, 1, rule_data, created_by, change_description or "Initial rule creation"
            )
            
            self.logger.info(f"Created rule {rule.rule_id}: {rule.name}")
            return rule.rule_id
            
        except Exception as e:
            self.logger.error(f"Error creating rule: {str(e)}")
            raise
    
    async def get_rule(self, rule_id: str) -> Optional[Rule]:
        """
        Retrieve a rule by ID.
        
        Args:
            rule_id: Rule ID to retrieve
            
        Returns:
            Rule object or None if not found
        """
        try:
            doc_ref = self.rules_collection.document(rule_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            rule_data = doc.to_dict()
            return Rule.from_firestore_dict(rule_data)
            
        except Exception as e:
            self.logger.error(f"Error retrieving rule {rule_id}: {str(e)}")
            raise
    
    async def update_rule(
        self, 
        rule: Rule, 
        updated_by: Optional[str] = None,
        change_description: Optional[str] = None
    ) -> bool:
        """
        Update an existing rule.
        
        Args:
            rule: Updated rule object
            updated_by: User ID who updated the rule
            change_description: Description of the changes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current rule for versioning
            current_rule = await self.get_rule(rule.rule_id)
            if not current_rule:
                raise ValueError(f"Rule {rule.rule_id} not found")
            
            # Update metadata
            rule.updated_at = datetime.utcnow()
            if updated_by:
                rule.created_by = updated_by  # Track last updater
            
            # Convert to Firestore format
            rule_data = rule.to_firestore_dict()
            
            # Update rule document
            doc_ref = self.rules_collection.document(rule.rule_id)
            doc_ref.set(rule_data)
            
            # Create new version
            latest_version = await self._get_latest_version_number(rule.rule_id)
            await self._create_rule_version(
                rule.rule_id, 
                latest_version + 1, 
                rule_data, 
                updated_by, 
                change_description or "Rule updated"
            )
            
            self.logger.info(f"Updated rule {rule.rule_id}: {rule.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating rule {rule.rule_id}: {str(e)}")
            raise
    
    async def delete_rule(self, rule_id: str, deleted_by: Optional[str] = None) -> bool:
        """
        Delete a rule (soft delete by deactivating).
        
        Args:
            rule_id: Rule ID to delete
            deleted_by: User ID who deleted the rule
            
        Returns:
            True if successful, False otherwise
        """
        try:
            rule = await self.get_rule(rule_id)
            if not rule:
                return False
            
            # Soft delete by deactivating
            rule.active = False
            rule.updated_at = datetime.utcnow()
            
            success = await self.update_rule(
                rule, 
                deleted_by, 
                f"Rule deleted by {deleted_by or 'system'}"
            )
            
            self.logger.info(f"Deleted (deactivated) rule {rule_id}")
            return success
            
        except Exception as e:
            self.logger.error(f"Error deleting rule {rule_id}: {str(e)}")
            raise
    
    async def list_rules(
        self,
        active_only: bool = True,
        severity_filter: Optional[str] = None,
        priority_min: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Rule]:
        """
        List rules with filtering options.
        
        Args:
            active_only: Only return active rules
            severity_filter: Filter by severity override
            priority_min: Minimum priority level
            limit: Maximum number of rules to return
            offset: Number of rules to skip
            
        Returns:
            List of Rule objects
        """
        try:
            query = self.rules_collection
            
            # Apply filters
            if active_only:
                query = query.where(filter=FieldFilter("active", "==", True))
            
            if severity_filter:
                query = query.where(filter=FieldFilter("severity_override", "==", severity_filter))
            
            if priority_min is not None:
                query = query.where(filter=FieldFilter("priority", ">=", priority_min))
            
            # Order by priority (descending) and creation date
            query = query.order_by("priority", direction=firestore.Query.DESCENDING)
            query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
            
            # Apply pagination
            if offset > 0:
                query = query.offset(offset)
            query = query.limit(limit)
            
            # Execute query
            docs = query.stream()
            
            rules = []
            for doc in docs:
                rule_data = doc.to_dict()
                rule = Rule.from_firestore_dict(rule_data)
                rules.append(rule)
            
            self.logger.info(f"Retrieved {len(rules)} rules")
            return rules
            
        except Exception as e:
            self.logger.error(f"Error listing rules: {str(e)}")
            raise
    
    async def activate_rule(self, rule_id: str, activated_by: Optional[str] = None) -> bool:
        """
        Activate a rule.
        
        Args:
            rule_id: Rule ID to activate
            activated_by: User ID who activated the rule
            
        Returns:
            True if successful, False otherwise
        """
        try:
            rule = await self.get_rule(rule_id)
            if not rule:
                return False
            
            rule.active = True
            rule.updated_at = datetime.utcnow()
            
            success = await self.update_rule(
                rule, 
                activated_by, 
                f"Rule activated by {activated_by or 'system'}"
            )
            
            self.logger.info(f"Activated rule {rule_id}")
            return success
            
        except Exception as e:
            self.logger.error(f"Error activating rule {rule_id}: {str(e)}")
            raise
    
    async def deactivate_rule(self, rule_id: str, deactivated_by: Optional[str] = None) -> bool:
        """
        Deactivate a rule.
        
        Args:
            rule_id: Rule ID to deactivate
            deactivated_by: User ID who deactivated the rule
            
        Returns:
            True if successful, False otherwise
        """
        try:
            rule = await self.get_rule(rule_id)
            if not rule:
                return False
            
            rule.active = False
            rule.updated_at = datetime.utcnow()
            
            success = await self.update_rule(
                rule, 
                deactivated_by, 
                f"Rule deactivated by {deactivated_by or 'system'}"
            )
            
            self.logger.info(f"Deactivated rule {rule_id}")
            return success
            
        except Exception as e:
            self.logger.error(f"Error deactivating rule {rule_id}: {str(e)}")
            raise
    
    async def get_rule_versions(self, rule_id: str, limit: int = 10) -> List[RuleVersion]:
        """
        Get version history for a rule.
        
        Args:
            rule_id: Rule ID to get versions for
            limit: Maximum number of versions to return
            
        Returns:
            List of RuleVersion objects
        """
        try:
            query = (self.rule_versions_collection
                    .where(filter=FieldFilter("rule_id", "==", rule_id))
                    .order_by("version_number", direction=firestore.Query.DESCENDING)
                    .limit(limit))
            
            docs = query.stream()
            
            versions = []
            for doc in docs:
                version_data = doc.to_dict()
                version = RuleVersion.from_firestore_dict(version_data)
                versions.append(version)
            
            self.logger.info(f"Retrieved {len(versions)} versions for rule {rule_id}")
            return versions
            
        except Exception as e:
            self.logger.error(f"Error retrieving versions for rule {rule_id}: {str(e)}")
            raise
    
    async def restore_rule_version(
        self, 
        rule_id: str, 
        version_number: int,
        restored_by: Optional[str] = None
    ) -> bool:
        """
        Restore a rule to a previous version.
        
        Args:
            rule_id: Rule ID to restore
            version_number: Version number to restore to
            restored_by: User ID who restored the rule
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the version to restore
            query = (self.rule_versions_collection
                    .where(filter=FieldFilter("rule_id", "==", rule_id))
                    .where(filter=FieldFilter("version_number", "==", version_number))
                    .limit(1))
            
            docs = list(query.stream())
            if not docs:
                raise ValueError(f"Version {version_number} not found for rule {rule_id}")
            
            version_data = docs[0].to_dict()
            rule_data = version_data["rule_data"]
            
            # Create rule from version data
            rule = Rule.from_firestore_dict(rule_data)
            rule.updated_at = datetime.utcnow()
            
            # Update the rule
            success = await self.update_rule(
                rule, 
                restored_by, 
                f"Restored to version {version_number} by {restored_by or 'system'}"
            )
            
            self.logger.info(f"Restored rule {rule_id} to version {version_number}")
            return success
            
        except Exception as e:
            self.logger.error(f"Error restoring rule {rule_id} to version {version_number}: {str(e)}")
            raise
    
    async def export_rules(
        self,
        rule_ids: Optional[List[str]] = None,
        active_only: bool = True,
        include_metadata: bool = True
    ) -> RuleImportExportFormat:
        """
        Export rules to a standardized format.
        
        Args:
            rule_ids: Specific rule IDs to export (None for all)
            active_only: Only export active rules
            include_metadata: Include rule metadata in export
            
        Returns:
            RuleImportExportFormat object
        """
        try:
            if rule_ids:
                # Export specific rules
                rules = []
                for rule_id in rule_ids:
                    rule = await self.get_rule(rule_id)
                    if rule and (not active_only or rule.active):
                        rules.append(rule)
            else:
                # Export all rules
                rules = await self.list_rules(active_only=active_only, limit=1000)
            
            # Convert to export format
            export_rules = []
            for rule in rules:
                rule_dict = rule.to_firestore_dict()
                if not include_metadata:
                    # Remove internal metadata
                    for key in ['created_at', 'updated_at', 'created_by']:
                        rule_dict.pop(key, None)
                export_rules.append(rule_dict)
            
            metadata = {
                "total_rules": len(export_rules),
                "active_only": active_only,
                "include_metadata": include_metadata,
                "exported_by": "system"  # In production, get from context
            }
            
            export_format = RuleImportExportFormat(
                rules=export_rules,
                metadata=metadata,
                export_timestamp=datetime.utcnow()
            )
            
            self.logger.info(f"Exported {len(export_rules)} rules")
            return export_format
            
        except Exception as e:
            self.logger.error(f"Error exporting rules: {str(e)}")
            raise
    
    async def import_rules(
        self,
        import_format: RuleImportExportFormat,
        imported_by: Optional[str] = None,
        overwrite_existing: bool = False
    ) -> Tuple[int, int, List[str]]:
        """
        Import rules from a standardized format.
        
        Args:
            import_format: RuleImportExportFormat object to import
            imported_by: User ID who imported the rules
            overwrite_existing: Whether to overwrite existing rules
            
        Returns:
            Tuple of (created_count, updated_count, error_messages)
        """
        try:
            created_count = 0
            updated_count = 0
            error_messages = []
            
            for rule_data in import_format.rules:
                try:
                    # Create rule object
                    rule = Rule.from_firestore_dict(rule_data)
                    
                    # Check if rule exists
                    existing_rule = await self.get_rule(rule.rule_id)
                    
                    if existing_rule:
                        if overwrite_existing:
                            await self.update_rule(
                                rule, 
                                imported_by, 
                                f"Imported and updated by {imported_by or 'system'}"
                            )
                            updated_count += 1
                        else:
                            error_messages.append(f"Rule {rule.rule_id} already exists (skipped)")
                    else:
                        await self.create_rule(
                            rule, 
                            imported_by, 
                            f"Imported by {imported_by or 'system'}"
                        )
                        created_count += 1
                        
                except Exception as e:
                    error_messages.append(f"Error importing rule {rule_data.get('rule_id', 'unknown')}: {str(e)}")
            
            self.logger.info(
                f"Import completed: {created_count} created, {updated_count} updated, "
                f"{len(error_messages)} errors"
            )
            
            return created_count, updated_count, error_messages
            
        except Exception as e:
            self.logger.error(f"Error importing rules: {str(e)}")
            raise
    
    async def _create_rule_version(
        self,
        rule_id: str,
        version_number: int,
        rule_data: Dict[str, Any],
        created_by: Optional[str] = None,
        change_description: Optional[str] = None
    ) -> str:
        """Create a new rule version."""
        version = RuleVersion(
            version_id=str(uuid4()),
            rule_id=rule_id,
            version_number=version_number,
            rule_data=rule_data,
            created_at=datetime.utcnow(),
            created_by=created_by,
            change_description=change_description
        )
        
        doc_ref = self.rule_versions_collection.document(version.version_id)
        doc_ref.set(version.to_firestore_dict())
        
        return version.version_id
    
    async def _get_latest_version_number(self, rule_id: str) -> int:
        """Get the latest version number for a rule."""
        query = (self.rule_versions_collection
                .where(filter=FieldFilter("rule_id", "==", rule_id))
                .order_by("version_number", direction=firestore.Query.DESCENDING)
                .limit(1))
        
        docs = list(query.stream())
        if docs:
            return docs[0].to_dict()["version_number"]
        return 0


# Export main classes
__all__ = [
    'RuleVersion',
    'RuleImportExportFormat',
    'RuleStore'
]