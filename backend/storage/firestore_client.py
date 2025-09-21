"""
Firestore client initialization and connection management.
Provides centralized Firestore client setup with connection testing.
"""

import logging
from typing import Optional
from google.cloud import firestore
from google.cloud.firestore import Client
from google.api_core import exceptions as gcp_exceptions
from core.config import get_firestore_config, settings

logger = logging.getLogger(__name__)

# Global Firestore client instance
_firestore_client: Optional[Client] = None


def get_firestore_client() -> Client:
    """
    Get or create the Firestore client instance.
    
    Returns:
        Client: Firestore client instance
        
    Raises:
        Exception: If client initialization fails
    """
    global _firestore_client
    
    if _firestore_client is None:
        _firestore_client = initialize_firestore_client()
    
    return _firestore_client


def initialize_firestore_client() -> Client:
    """
    Initialize the Firestore client with configuration.
    
    Returns:
        Client: Initialized Firestore client
        
    Raises:
        Exception: If initialization fails
    """
    try:
        config = get_firestore_config()
        
        # Initialize client with project and database
        if config.get("credentials_path"):
            # Use service account key file if provided
            import os
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config["credentials_path"]
        
        client = firestore.Client(
            project=config["project"],
            database=config["database"]
        )
        
        logger.info(f"Firestore client initialized for project: {config['project']}, database: {config['database']}")
        return client
        
    except Exception as e:
        logger.error(f"Failed to initialize Firestore client: {e}")
        raise


async def test_firestore_connection() -> bool:
    """
    Test the Firestore connection by performing a simple operation.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        client = get_firestore_client()
        
        # Test connection by creating a test document and then deleting it
        test_collection = "connection_test"
        test_doc_id = "test_connection"
        
        # Write a test document
        test_doc_ref = client.collection(test_collection).document(test_doc_id)
        test_doc_ref.set({
            "test": True,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        
        # Read the test document to verify write/read operations
        doc = test_doc_ref.get()
        if not doc.exists:
            logger.error("Test document was not created successfully")
            return False
        
        # Clean up test document
        test_doc_ref.delete()
        
        logger.info("Firestore connection test successful")
        return True
        
    except gcp_exceptions.PermissionDenied as e:
        logger.error(f"Firestore connection test failed - Permission denied: {e}")
        return False
    except gcp_exceptions.NotFound as e:
        logger.error(f"Firestore connection test failed - Resource not found: {e}")
        return False
    except Exception as e:
        logger.error(f"Firestore connection test failed: {e}")
        return False


def initialize_collections() -> bool:
    """
    Initialize required Firestore collections with proper indexes.
    
    Returns:
        bool: True if initialization is successful, False otherwise
    """
    try:
        client = get_firestore_client()
        
        # Define required collections
        collections = [
            "legal_documents",
            "semantic_buckets", 
            "document_classifications",
            "classification_rules",
            "review_queue"
        ]
        
        # Create collections by adding a dummy document and then deleting it
        # This ensures the collections exist for index creation
        for collection_name in collections:
            try:
                # Check if collection exists by trying to get a document
                dummy_ref = client.collection(collection_name).document("_init_check")
                dummy_ref.set({"initialized": True})
                dummy_ref.delete()
                
                logger.info(f"Collection '{collection_name}' initialized")
                
            except Exception as e:
                logger.error(f"Failed to initialize collection '{collection_name}': {e}")
                return False
        
        logger.info("All Firestore collections initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Firestore collections: {e}")
        return False


def get_collection_reference(collection_name: str):
    """
    Get a reference to a Firestore collection.
    
    Args:
        collection_name (str): Name of the collection
        
    Returns:
        CollectionReference: Firestore collection reference
    """
    client = get_firestore_client()
    return client.collection(collection_name)


def close_firestore_client():
    """
    Close the Firestore client connection.
    """
    global _firestore_client
    
    if _firestore_client is not None:
        # Firestore client doesn't have an explicit close method
        # Setting to None will allow garbage collection
        _firestore_client = None
        logger.info("Firestore client connection closed")


# Collection name constants for easy reference
class Collections:
    """Constants for Firestore collection names."""
    DOCUMENTS = "legal_documents"
    BUCKETS = "semantic_buckets"
    CLASSIFICATIONS = "document_classifications"
    RULES = "classification_rules"
    REVIEW_QUEUE = "review_queue"