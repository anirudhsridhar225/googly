"""
Firestore Schema Initialization and Management

This module provides functions to initialize Firestore collections with proper
indexes and security rules for the legal document classification system.
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from models.legal_models import FIRESTORE_COLLECTIONS
# from storage.firestore_client import get_firestore_client  # Import only when needed


logger = logging.getLogger(__name__)


class FirestoreSchemaManager:
    """Manages Firestore schema initialization and maintenance."""
    
    def __init__(self, db: Optional[firestore.Client] = None):
        """
        Initialize the schema manager.
        
        Args:
            db: Firestore client instance. If None, will create a new one.
        """
        if db is None:
            try:
                from storage.firestore_client import get_firestore_client
                self.db = get_firestore_client()
            except ImportError:
                self.db = None
        else:
            self.db = db
    
    async def initialize_collections(self) -> bool:
        """
        Initialize all required Firestore collections with sample documents
        to ensure proper indexing.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing Firestore collections...")
            
            # Initialize each collection
            for collection_key, collection_name in FIRESTORE_COLLECTIONS.items():
                await self._initialize_collection(collection_name, collection_key)
            
            logger.info("Firestore collections initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Firestore collections: {e}")
            return False
    
    async def _initialize_collection(self, collection_name: str, collection_type: str) -> None:
        """
        Initialize a specific collection with proper structure.
        
        Args:
            collection_name: Name of the Firestore collection
            collection_type: Type of collection (documents, buckets, etc.)
        """
        collection_ref = self.db.collection(collection_name)
        
        # Check if collection already has documents
        docs = collection_ref.limit(1).stream()
        if any(docs):
            logger.info(f"Collection {collection_name} already exists with documents")
            return
        
        # Create initial document based on collection type
        initial_doc = self._get_initial_document(collection_type)
        if initial_doc:
            doc_ref = collection_ref.document('_schema_init')
            doc_ref.set(initial_doc)
            logger.info(f"Initialized collection {collection_name}")
    
    def _get_initial_document(self, collection_type: str) -> Optional[Dict[str, Any]]:
        """
        Get initial document structure for a collection type.
        
        Args:
            collection_type: Type of collection
            
        Returns:
            Initial document structure or None
        """
        now = datetime.utcnow().isoformat()
        
        initial_docs = {
            'documents': {
                'id': '_schema_init',
                'text': 'Schema initialization document',
                'embedding': [0.0] * 768,  # Standard embedding size
                'metadata': {
                    'filename': '_schema_init.txt',
                    'upload_date': now,
                    'file_size': 0,
                    'content_hash': 'init',
                    'tags': ['schema', 'init']
                },
                'created_at': now,
                'document_type': 'reference',
                'severity_label': 'LOW',
                '_is_schema_init': True
            },
            'buckets': {
                'bucket_id': '_schema_init',
                'bucket_name': 'Schema Initialization Bucket',
                'centroid_embedding': [0.0] * 768,
                'document_ids': [],
                'created_at': now,
                'updated_at': now,
                'document_count': 0,
                'description': 'Initial bucket for schema setup',
                '_is_schema_init': True
            },
            'rules': {
                'rule_id': '_schema_init',
                'name': 'Schema Initialization Rule',
                'description': 'Initial rule for schema setup',
                'conditions': [{
                    'operator': 'contains',
                    'field': 'text',
                    'value': '_schema_init',
                    'case_sensitive': False
                }],
                'condition_logic': 'AND',
                'severity_override': 'LOW',
                'priority': 1,
                'active': False,
                'created_at': now,
                'updated_at': now,
                '_is_schema_init': True
            },
            'classifications': {
                'classification_id': '_schema_init',
                'document_id': '_schema_init',
                'label': 'LOW',
                'confidence': 1.0,
                'rationale': 'Schema initialization classification',
                'evidence': [],
                'bucket_id': '_schema_init',
                'rule_overrides': [],
                'routing_decision': 'auto_accept',
                'model_version': 'init-1.0',
                'created_at': now,
                'human_reviewed': False,
                '_is_schema_init': True
            },
            'review_queue': {
                'queue_id': '_schema_init',
                'document_id': '_schema_init',
                'classification_id': '_schema_init',
                'priority': 1,
                'assigned_reviewer': None,
                'status': 'pending',
                'created_at': now,
                'updated_at': now,
                '_is_schema_init': True
            },
            'audit_logs': {
                'log_id': '_schema_init',
                'event_type': 'schema_initialization',
                'document_id': '_schema_init',
                'classification_id': '_schema_init',
                'user_id': 'system',
                'action': 'initialize_schema',
                'details': {'message': 'Schema initialization log'},
                'timestamp': now,
                '_is_schema_init': True
            }
        }
        
        return initial_docs.get(collection_type)
    
    async def create_indexes(self) -> bool:
        """
        Create recommended indexes for efficient querying.
        Note: Firestore indexes are typically created through the Firebase console
        or gcloud CLI. This method documents the required indexes.
        
        Returns:
            bool: True if index creation guidance provided successfully
        """
        try:
            logger.info("Documenting required Firestore indexes...")
            
            required_indexes = self._get_required_indexes()
            
            # Log the required indexes for manual creation
            for collection, indexes in required_indexes.items():
                logger.info(f"Required indexes for {collection}:")
                for index in indexes:
                    logger.info(f"  - {index}")
            
            logger.info("Index documentation complete. Create these indexes in Firebase console.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to document indexes: {e}")
            return False
    
    def _get_required_indexes(self) -> Dict[str, List[str]]:
        """
        Get list of required composite indexes for each collection.
        
        Returns:
            Dictionary mapping collection names to required indexes
        """
        return {
            FIRESTORE_COLLECTIONS['documents']: [
                "document_type ASC, created_at DESC",
                "document_type ASC, severity_label ASC, created_at DESC",
                "metadata.tags ARRAY, document_type ASC",
                "metadata.content_hash ASC"
            ],
            FIRESTORE_COLLECTIONS['buckets']: [
                "document_count DESC, created_at DESC",
                "updated_at DESC",
                "bucket_name ASC"
            ],
            FIRESTORE_COLLECTIONS['rules']: [
                "active ASC, priority DESC",
                "active ASC, created_at DESC",
                "severity_override ASC, priority DESC"
            ],
            FIRESTORE_COLLECTIONS['classifications']: [
                "document_id ASC, created_at DESC",
                "routing_decision ASC, created_at DESC",
                "label ASC, confidence DESC",
                "human_reviewed ASC, created_at DESC",
                "bucket_id ASC, created_at DESC"
            ],
            FIRESTORE_COLLECTIONS['review_queue']: [
                "status ASC, priority DESC, created_at ASC",
                "assigned_reviewer ASC, status ASC",
                "status ASC, created_at ASC"
            ],
            FIRESTORE_COLLECTIONS['audit_logs']: [
                "event_type ASC, timestamp DESC",
                "document_id ASC, timestamp DESC",
                "user_id ASC, timestamp DESC"
            ]
        }
    
    async def validate_schema(self) -> Dict[str, bool]:
        """
        Validate that all required collections exist and have proper structure.
        
        Returns:
            Dictionary mapping collection names to validation status
        """
        validation_results = {}
        
        try:
            for collection_key, collection_name in FIRESTORE_COLLECTIONS.items():
                validation_results[collection_name] = await self._validate_collection(collection_name)
            
            logger.info(f"Schema validation complete: {validation_results}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return {name: False for name in FIRESTORE_COLLECTIONS.values()}
    
    async def _validate_collection(self, collection_name: str) -> bool:
        """
        Validate a specific collection exists and has documents.
        
        Args:
            collection_name: Name of the collection to validate
            
        Returns:
            bool: True if collection is valid, False otherwise
        """
        try:
            collection_ref = self.db.collection(collection_name)
            docs = list(collection_ref.limit(1).stream())
            return len(docs) > 0
            
        except Exception as e:
            logger.error(f"Failed to validate collection {collection_name}: {e}")
            return False
    
    async def cleanup_schema_init_docs(self) -> bool:
        """
        Remove schema initialization documents after proper setup.
        
        Returns:
            bool: True if cleanup successful, False otherwise
        """
        try:
            logger.info("Cleaning up schema initialization documents...")
            
            for collection_name in FIRESTORE_COLLECTIONS.values():
                collection_ref = self.db.collection(collection_name)
                
                # Query for schema init documents
                docs = collection_ref.where(
                    filter=FieldFilter('_is_schema_init', '==', True)
                ).stream()
                
                # Delete schema init documents
                for doc in docs:
                    doc.reference.delete()
                    logger.info(f"Deleted schema init doc from {collection_name}")
            
            logger.info("Schema initialization cleanup complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup schema init docs: {e}")
            return False


async def initialize_firestore_schema() -> bool:
    """
    Initialize the complete Firestore schema for the legal document classification system.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        schema_manager = FirestoreSchemaManager()
        
        # Initialize collections
        if not await schema_manager.initialize_collections():
            return False
        
        # Create index documentation
        if not await schema_manager.create_indexes():
            return False
        
        # Validate schema
        validation_results = await schema_manager.validate_schema()
        if not all(validation_results.values()):
            logger.error(f"Schema validation failed: {validation_results}")
            return False
        
        logger.info("Firestore schema initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Firestore schema initialization failed: {e}")
        return False


async def reset_firestore_schema() -> bool:
    """
    Reset the Firestore schema by cleaning up and reinitializing.
    WARNING: This will remove all schema initialization documents.
    
    Returns:
        bool: True if reset successful, False otherwise
    """
    try:
        schema_manager = FirestoreSchemaManager()
        
        # Cleanup existing schema init docs
        if not await schema_manager.cleanup_schema_init_docs():
            logger.warning("Failed to cleanup existing schema docs, continuing...")
        
        # Reinitialize
        return await initialize_firestore_schema()
        
    except Exception as e:
        logger.error(f"Firestore schema reset failed: {e}")
        return False


if __name__ == "__main__":
    import asyncio
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run schema initialization
    asyncio.run(initialize_firestore_schema())