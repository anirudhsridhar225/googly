"""
Document Storage Service for Legal Document Severity Classification System.

This module provides Firestore-based document storage with CRUD operations,
duplicate detection, metadata management, and indexing capabilities.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from uuid import uuid4

from google.cloud import firestore
from google.api_core import exceptions as gcp_exceptions

from storage.firestore_client import get_firestore_client, Collections
from models.legal_models import Document, DocumentType, SeverityLevel, DocumentMetadata

logger = logging.getLogger(__name__)


class DocumentStore:
    """Firestore-based document storage service."""
    
    def __init__(self):
        self.client = get_firestore_client()
        self.collection_name = Collections.DOCUMENTS
        
    async def store_document(self, document: Document) -> str:
        """
        Store a document in Firestore.
        
        Args:
            document: Document instance to store
            
        Returns:
            Document ID of the stored document
            
        Raises:
            Exception: If storage operation fails
        """
        try:
            # Check for duplicates using content hash
            existing_doc = await self.find_duplicate_by_hash(document.metadata.content_hash)
            if existing_doc:
                logger.warning(f"Duplicate document detected: {document.metadata.filename}")
                raise ValueError(f"Document with same content already exists: {existing_doc['id']}")
            
            # Convert document to Firestore format
            doc_data = document.to_firestore_dict()
            
            # Store in Firestore
            doc_ref = self.client.collection(self.collection_name).document(document.id)
            doc_ref.set(doc_data)
            
            logger.info(f"Stored document {document.id} ({document.metadata.filename})")
            return document.id
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error storing document {document.id}: {e}")
            raise Exception(f"Failed to store document: {str(e)}")
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """
        Retrieve a document by ID.
        
        Args:
            document_id: ID of the document to retrieve
            
        Returns:
            Document instance or None if not found
        """
        try:
            doc_ref = self.client.collection(self.collection_name).document(document_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            doc_data = doc.to_dict()
            return Document.from_firestore_dict(doc_data)
            
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}")
            return None
    
    async def get_documents_by_ids(self, document_ids: List[str]) -> List[Document]:
        """
        Retrieve multiple documents by their IDs.
        
        Args:
            document_ids: List of document IDs to retrieve
            
        Returns:
            List of Document instances (may be fewer than requested if some not found)
        """
        if not document_ids:
            return []
        
        documents = []
        
        try:
            # Firestore batch get (up to 500 documents)
            batch_size = 500
            for i in range(0, len(document_ids), batch_size):
                batch_ids = document_ids[i:i + batch_size]
                doc_refs = [
                    self.client.collection(self.collection_name).document(doc_id) 
                    for doc_id in batch_ids
                ]
                
                docs = self.client.get_all(doc_refs)
                
                for doc in docs:
                    if doc.exists:
                        doc_data = doc.to_dict()
                        document = Document.from_firestore_dict(doc_data)
                        documents.append(document)
            
            logger.debug(f"Retrieved {len(documents)} documents out of {len(document_ids)} requested")
            return documents
            
        except Exception as e:
            logger.error(f"Error retrieving documents by IDs: {e}")
            return []
    
    async def update_document(self, document_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update specific fields of a document.
        
        Args:
            document_id: ID of the document to update
            updates: Dictionary of fields to update
            
        Returns:
            True if update succeeded, False otherwise
        """
        try:
            doc_ref = self.client.collection(self.collection_name).document(document_id)
            
            # Add update timestamp
            updates['updated_at'] = datetime.utcnow().isoformat()
            
            doc_ref.update(updates)
            
            logger.info(f"Updated document {document_id}")
            return True
            
        except gcp_exceptions.NotFound:
            logger.warning(f"Document {document_id} not found for update")
            return False
        except Exception as e:
            logger.error(f"Error updating document {document_id}: {e}")
            return False
    
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from Firestore.
        
        Args:
            document_id: ID of the document to delete
            
        Returns:
            True if deletion succeeded, False otherwise
        """
        try:
            doc_ref = self.client.collection(self.collection_name).document(document_id)
            doc_ref.delete()
            
            logger.info(f"Deleted document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False
    
    async def find_duplicate_by_hash(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """
        Find a document with the same content hash.
        
        Args:
            content_hash: SHA-256 hash of document content
            
        Returns:
            Dictionary with document data if found, None otherwise
        """
        try:
            query = self.client.collection(self.collection_name).where(
                'metadata.content_hash', '==', content_hash
            ).limit(1)
            
            docs = query.stream()
            
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['id'] = doc.id
                return doc_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking for duplicate document: {e}")
            return None
    
    async def get_documents_by_type(
        self, 
        document_type: DocumentType, 
        limit: Optional[int] = None,
        severity_label: Optional[SeverityLevel] = None
    ) -> List[Document]:
        """
        Retrieve documents by type and optionally by severity label.
        
        Args:
            document_type: Type of documents to retrieve
            limit: Maximum number of documents to return
            severity_label: Optional severity label filter
            
        Returns:
            List of Document instances
        """
        try:
            query = self.client.collection(self.collection_name).where(
                'document_type', '==', document_type.value
            )
            
            if severity_label:
                query = query.where('severity_label', '==', severity_label.value)
            
            if limit:
                query = query.limit(limit)
            
            # Order by creation date (newest first)
            query = query.order_by('created_at', direction=firestore.Query.DESCENDING)
            
            docs = query.stream()
            documents = []
            
            for doc in docs:
                doc_data = doc.to_dict()
                document = Document.from_firestore_dict(doc_data)
                documents.append(document)
            
            logger.debug(f"Retrieved {len(documents)} documents of type {document_type}")
            return documents
            
        except Exception as e:
            logger.error(f"Error retrieving documents by type: {e}")
            return []
    
    async def search_documents_by_tags(self, tags: List[str], match_all: bool = False) -> List[Document]:
        """
        Search documents by tags.
        
        Args:
            tags: List of tags to search for
            match_all: If True, document must have all tags; if False, any tag matches
            
        Returns:
            List of Document instances matching the tag criteria
        """
        if not tags:
            return []
        
        try:
            if match_all:
                # Document must contain all tags
                query = self.client.collection(self.collection_name)
                for tag in tags:
                    query = query.where('metadata.tags', 'array_contains', tag)
            else:
                # Document must contain at least one tag
                query = self.client.collection(self.collection_name).where(
                    'metadata.tags', 'array_contains_any', tags
                )
            
            docs = query.stream()
            documents = []
            
            for doc in docs:
                doc_data = doc.to_dict()
                document = Document.from_firestore_dict(doc_data)
                documents.append(document)
            
            logger.debug(f"Found {len(documents)} documents matching tags: {tags}")
            return documents
            
        except Exception as e:
            logger.error(f"Error searching documents by tags: {e}")
            return []
    
    async def get_document_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored documents.
        
        Returns:
            Dictionary with document statistics
        """
        try:
            stats = {
                'total_documents': 0,
                'by_type': {},
                'by_severity': {},
                'recent_uploads': 0
            }
            
            # Get all documents
            docs = self.client.collection(self.collection_name).stream()
            
            recent_cutoff = datetime.utcnow().timestamp() - (7 * 24 * 60 * 60)  # 7 days ago
            
            for doc in docs:
                doc_data = doc.to_dict()
                stats['total_documents'] += 1
                
                # Count by type
                doc_type = doc_data.get('document_type', 'unknown')
                stats['by_type'][doc_type] = stats['by_type'].get(doc_type, 0) + 1
                
                # Count by severity (for reference documents)
                severity = doc_data.get('severity_label')
                if severity:
                    stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1
                
                # Count recent uploads
                created_at = doc_data.get('created_at')
                if created_at:
                    if isinstance(created_at, str):
                        created_timestamp = datetime.fromisoformat(created_at).timestamp()
                    else:
                        created_timestamp = created_at.timestamp()
                    
                    if created_timestamp > recent_cutoff:
                        stats['recent_uploads'] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting document statistics: {e}")
            return {'error': str(e)}
    
    async def create_indexes(self) -> bool:
        """
        Create necessary Firestore indexes for efficient querying.
        Note: This is informational - actual indexes must be created via Firebase console or CLI.
        
        Returns:
            True (indexes need to be created manually)
        """
        required_indexes = [
            {
                'collection': self.collection_name,
                'fields': [
                    {'field': 'document_type', 'order': 'ASCENDING'},
                    {'field': 'created_at', 'order': 'DESCENDING'}
                ]
            },
            {
                'collection': self.collection_name,
                'fields': [
                    {'field': 'document_type', 'order': 'ASCENDING'},
                    {'field': 'severity_label', 'order': 'ASCENDING'},
                    {'field': 'created_at', 'order': 'DESCENDING'}
                ]
            },
            {
                'collection': self.collection_name,
                'fields': [
                    {'field': 'metadata.content_hash', 'order': 'ASCENDING'}
                ]
            },
            {
                'collection': self.collection_name,
                'fields': [
                    {'field': 'metadata.tags', 'order': 'ASCENDING'}
                ]
            }
        ]
        
        logger.info("Required Firestore indexes:")
        for idx in required_indexes:
            logger.info(f"  Collection: {idx['collection']}")
            for field in idx['fields']:
                logger.info(f"    Field: {field['field']} ({field['order']})")
        
        logger.info("Please create these indexes using the Firebase console or CLI")
        return True
    
    async def batch_store_documents(self, documents: List[Document]) -> Tuple[List[str], List[str]]:
        """
        Store multiple documents in a batch operation.
        
        Args:
            documents: List of Document instances to store
            
        Returns:
            Tuple of (successful_ids, failed_ids)
        """
        if not documents:
            return [], []
        
        successful_ids = []
        failed_ids = []
        
        try:
            # Firestore batch write (up to 500 operations)
            batch_size = 500
            
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i + batch_size]
                batch = self.client.batch()
                
                for document in batch_docs:
                    try:
                        # Check for duplicates
                        existing_doc = await self.find_duplicate_by_hash(document.metadata.content_hash)
                        if existing_doc:
                            logger.warning(f"Skipping duplicate document: {document.metadata.filename}")
                            failed_ids.append(document.id)
                            continue
                        
                        # Add to batch
                        doc_ref = self.client.collection(self.collection_name).document(document.id)
                        doc_data = document.to_firestore_dict()
                        batch.set(doc_ref, doc_data)
                        
                    except Exception as e:
                        logger.error(f"Error preparing document {document.id} for batch: {e}")
                        failed_ids.append(document.id)
                
                # Commit batch
                batch.commit()
                
                # Add successful IDs
                for document in batch_docs:
                    if document.id not in failed_ids:
                        successful_ids.append(document.id)
            
            logger.info(f"Batch stored {len(successful_ids)} documents, {len(failed_ids)} failed")
            return successful_ids, failed_ids
            
        except Exception as e:
            logger.error(f"Error in batch document storage: {e}")
            # Mark all as failed if batch operation fails
            failed_ids.extend([doc.id for doc in documents if doc.id not in failed_ids])
            return successful_ids, failed_ids


# Export the main class
__all__ = ['DocumentStore']