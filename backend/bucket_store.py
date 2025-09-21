"""
Legal Document Severity Classification System - Bucket Store

This module implements the Firestore storage operations for semantic buckets,
including CRUD operations, indexing for similarity search, and metadata management.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
from uuid import uuid4

from google.cloud import firestore
from google.cloud.firestore import Client, Query
from google.api_core import exceptions as gcp_exceptions

from firestore_client import get_firestore_client, Collections
from legal_models import Bucket, FIRESTORE_COLLECTIONS

logger = logging.getLogger(__name__)


class BucketStoreError(Exception):
    """Base exception for bucket store operations."""
    pass


class BucketNotFoundError(BucketStoreError):
    """Exception raised when a bucket is not found."""
    pass


class BucketStore:
    """
    Manages Firestore operations for semantic buckets.
    
    Handles bucket CRUD operations, similarity search indexing,
    and metadata management with proper error handling and transactions.
    """
    
    def __init__(self, client: Optional[Client] = None):
        """
        Initialize the bucket store.
        
        Args:
            client: Firestore client instance (creates default if None)
        """
        self.client = client or get_firestore_client()
        self.collection_name = FIRESTORE_COLLECTIONS['buckets']
        self.collection_ref = self.client.collection(self.collection_name)
    
    async def create_bucket(self, bucket: Bucket) -> str:
        """
        Create a new bucket in Firestore.
        
        Args:
            bucket: Bucket object to create
            
        Returns:
            str: The created bucket ID
            
        Raises:
            BucketStoreError: If creation fails
        """
        try:
            # Convert bucket to Firestore-compatible format
            bucket_data = bucket.to_firestore_dict()
            
            # Use the bucket's ID as the document ID
            doc_ref = self.collection_ref.document(bucket.bucket_id)
            
            # Create the document
            doc_ref.set(bucket_data)
            
            logger.info(f"Created bucket {bucket.bucket_id} with {bucket.document_count} documents")
            return bucket.bucket_id
            
        except Exception as e:
            logger.error(f"Failed to create bucket {bucket.bucket_id}: {e}")
            raise BucketStoreError(f"Failed to create bucket: {e}")
    
    async def get_bucket(self, bucket_id: str) -> Bucket:
        """
        Retrieve a bucket by ID.
        
        Args:
            bucket_id: ID of the bucket to retrieve
            
        Returns:
            Bucket: The retrieved bucket
            
        Raises:
            BucketNotFoundError: If bucket is not found
            BucketStoreError: If retrieval fails
        """
        try:
            doc_ref = self.collection_ref.document(bucket_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                raise BucketNotFoundError(f"Bucket {bucket_id} not found")
            
            # Convert Firestore document to Bucket object
            bucket_data = doc.to_dict()
            bucket = Bucket.from_firestore_dict(bucket_data)
            
            logger.debug(f"Retrieved bucket {bucket_id}")
            return bucket
            
        except BucketNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve bucket {bucket_id}: {e}")
            raise BucketStoreError(f"Failed to retrieve bucket: {e}")
    
    async def update_bucket(self, bucket: Bucket) -> None:
        """
        Update an existing bucket.
        
        Args:
            bucket: Updated bucket object
            
        Raises:
            BucketNotFoundError: If bucket is not found
            BucketStoreError: If update fails
        """
        try:
            # Check if bucket exists
            doc_ref = self.collection_ref.document(bucket.bucket_id)
            if not doc_ref.get().exists:
                raise BucketNotFoundError(f"Bucket {bucket.bucket_id} not found")
            
            # Update the bucket
            bucket_data = bucket.to_firestore_dict()
            doc_ref.set(bucket_data)
            
            logger.info(f"Updated bucket {bucket.bucket_id}")
            
        except BucketNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update bucket {bucket.bucket_id}: {e}")
            raise BucketStoreError(f"Failed to update bucket: {e}")
    
    async def delete_bucket(self, bucket_id: str) -> None:
        """
        Delete a bucket by ID.
        
        Args:
            bucket_id: ID of the bucket to delete
            
        Raises:
            BucketNotFoundError: If bucket is not found
            BucketStoreError: If deletion fails
        """
        try:
            doc_ref = self.collection_ref.document(bucket_id)
            
            # Check if bucket exists
            if not doc_ref.get().exists:
                raise BucketNotFoundError(f"Bucket {bucket_id} not found")
            
            # Delete the bucket
            doc_ref.delete()
            
            logger.info(f"Deleted bucket {bucket_id}")
            
        except BucketNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete bucket {bucket_id}: {e}")
            raise BucketStoreError(f"Failed to delete bucket: {e}")
    
    async def list_buckets(
        self,
        limit: Optional[int] = None,
        order_by: str = "created_at",
        descending: bool = False
    ) -> List[Bucket]:
        """
        List all buckets with optional filtering and ordering.
        
        Args:
            limit: Maximum number of buckets to return
            order_by: Field to order by
            descending: Whether to order in descending order
            
        Returns:
            List[Bucket]: List of buckets
            
        Raises:
            BucketStoreError: If listing fails
        """
        try:
            query = self.collection_ref
            
            # Add ordering
            direction = Query.DESCENDING if descending else Query.ASCENDING
            query = query.order_by(order_by, direction=direction)
            
            # Add limit if specified
            if limit:
                query = query.limit(limit)
            
            # Execute query
            docs = query.stream()
            
            buckets = []
            for doc in docs:
                bucket_data = doc.to_dict()
                bucket = Bucket.from_firestore_dict(bucket_data)
                buckets.append(bucket)
            
            logger.debug(f"Listed {len(buckets)} buckets")
            return buckets
            
        except Exception as e:
            logger.error(f"Failed to list buckets: {e}")
            raise BucketStoreError(f"Failed to list buckets: {e}")
    
    async def find_buckets_by_document(self, document_id: str) -> List[Bucket]:
        """
        Find all buckets that contain a specific document.
        
        Args:
            document_id: ID of the document to search for
            
        Returns:
            List[Bucket]: List of buckets containing the document
            
        Raises:
            BucketStoreError: If search fails
        """
        try:
            # Query buckets where document_ids array contains the document_id
            query = self.collection_ref.where("document_ids", "array_contains", document_id)
            docs = query.stream()
            
            buckets = []
            for doc in docs:
                bucket_data = doc.to_dict()
                bucket = Bucket.from_firestore_dict(bucket_data)
                buckets.append(bucket)
            
            logger.debug(f"Found {len(buckets)} buckets containing document {document_id}")
            return buckets
            
        except Exception as e:
            logger.error(f"Failed to find buckets for document {document_id}: {e}")
            raise BucketStoreError(f"Failed to find buckets for document: {e}")
    
    async def get_buckets_by_ids(self, bucket_ids: List[str]) -> List[Bucket]:
        """
        Retrieve multiple buckets by their IDs.
        
        Args:
            bucket_ids: List of bucket IDs to retrieve
            
        Returns:
            List[Bucket]: List of retrieved buckets (may be fewer than requested if some not found)
            
        Raises:
            BucketStoreError: If retrieval fails
        """
        try:
            if not bucket_ids:
                return []
            
            buckets = []
            
            # Firestore has a limit of 10 documents per batch get
            batch_size = 10
            for i in range(0, len(bucket_ids), batch_size):
                batch_ids = bucket_ids[i:i + batch_size]
                
                # Create document references
                doc_refs = [self.collection_ref.document(bucket_id) for bucket_id in batch_ids]
                
                # Get documents in batch
                docs = self.client.get_all(doc_refs)
                
                for doc in docs:
                    if doc.exists:
                        bucket_data = doc.to_dict()
                        bucket = Bucket.from_firestore_dict(bucket_data)
                        buckets.append(bucket)
                    else:
                        logger.warning(f"Bucket {doc.id} not found")
            
            logger.debug(f"Retrieved {len(buckets)} out of {len(bucket_ids)} requested buckets")
            return buckets
            
        except Exception as e:
            logger.error(f"Failed to retrieve buckets by IDs: {e}")
            raise BucketStoreError(f"Failed to retrieve buckets by IDs: {e}")
    
    async def update_bucket_metadata(
        self,
        bucket_id: str,
        metadata_updates: Dict[str, Any]
    ) -> None:
        """
        Update specific metadata fields of a bucket.
        
        Args:
            bucket_id: ID of the bucket to update
            metadata_updates: Dictionary of fields to update
            
        Raises:
            BucketNotFoundError: If bucket is not found
            BucketStoreError: If update fails
        """
        try:
            doc_ref = self.collection_ref.document(bucket_id)
            
            # Check if bucket exists
            if not doc_ref.get().exists:
                raise BucketNotFoundError(f"Bucket {bucket_id} not found")
            
            # Add updated timestamp
            metadata_updates["updated_at"] = datetime.utcnow().isoformat()
            
            # Update only specified fields
            doc_ref.update(metadata_updates)
            
            logger.info(f"Updated metadata for bucket {bucket_id}: {list(metadata_updates.keys())}")
            
        except BucketNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update bucket metadata {bucket_id}: {e}")
            raise BucketStoreError(f"Failed to update bucket metadata: {e}")
    
    async def get_bucket_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about all buckets in the store.
        
        Returns:
            Dict[str, Any]: Statistics including count, total documents, etc.
            
        Raises:
            BucketStoreError: If statistics retrieval fails
        """
        try:
            # Get all buckets
            docs = self.collection_ref.stream()
            
            total_buckets = 0
            total_documents = 0
            document_counts = []
            bucket_names = []
            
            for doc in docs:
                bucket_data = doc.to_dict()
                total_buckets += 1
                doc_count = bucket_data.get("document_count", 0)
                total_documents += doc_count
                document_counts.append(doc_count)
                bucket_names.append(bucket_data.get("bucket_name", "unknown"))
            
            stats = {
                "total_buckets": total_buckets,
                "total_documents": total_documents,
                "avg_documents_per_bucket": total_documents / total_buckets if total_buckets > 0 else 0,
                "min_documents_per_bucket": min(document_counts) if document_counts else 0,
                "max_documents_per_bucket": max(document_counts) if document_counts else 0,
                "empty_buckets": sum(1 for count in document_counts if count == 0),
                "bucket_names": bucket_names
            }
            
            logger.debug(f"Retrieved bucket statistics: {total_buckets} buckets, {total_documents} documents")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get bucket statistics: {e}")
            raise BucketStoreError(f"Failed to get bucket statistics: {e}")
    
    async def create_buckets_batch(self, buckets: List[Bucket]) -> List[str]:
        """
        Create multiple buckets in a batch operation.
        
        Args:
            buckets: List of buckets to create
            
        Returns:
            List[str]: List of created bucket IDs
            
        Raises:
            BucketStoreError: If batch creation fails
        """
        try:
            if not buckets:
                return []
            
            # Firestore batch has a limit of 500 operations
            batch_size = 500
            created_ids = []
            
            for i in range(0, len(buckets), batch_size):
                batch_buckets = buckets[i:i + batch_size]
                
                # Create batch
                batch = self.client.batch()
                
                for bucket in batch_buckets:
                    doc_ref = self.collection_ref.document(bucket.bucket_id)
                    bucket_data = bucket.to_firestore_dict()
                    batch.set(doc_ref, bucket_data)
                    created_ids.append(bucket.bucket_id)
                
                # Commit batch
                batch.commit()
            
            logger.info(f"Created {len(created_ids)} buckets in batch operation")
            return created_ids
            
        except Exception as e:
            logger.error(f"Failed to create buckets in batch: {e}")
            raise BucketStoreError(f"Failed to create buckets in batch: {e}")
    
    async def delete_buckets_batch(self, bucket_ids: List[str]) -> int:
        """
        Delete multiple buckets in a batch operation.
        
        Args:
            bucket_ids: List of bucket IDs to delete
            
        Returns:
            int: Number of buckets successfully deleted
            
        Raises:
            BucketStoreError: If batch deletion fails
        """
        try:
            if not bucket_ids:
                return 0
            
            # Firestore batch has a limit of 500 operations
            batch_size = 500
            deleted_count = 0
            
            for i in range(0, len(bucket_ids), batch_size):
                batch_ids = bucket_ids[i:i + batch_size]
                
                # Create batch
                batch = self.client.batch()
                
                for bucket_id in batch_ids:
                    doc_ref = self.collection_ref.document(bucket_id)
                    batch.delete(doc_ref)
                
                # Commit batch
                batch.commit()
                deleted_count += len(batch_ids)
            
            logger.info(f"Deleted {deleted_count} buckets in batch operation")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete buckets in batch: {e}")
            raise BucketStoreError(f"Failed to delete buckets in batch: {e}")
    
    async def search_buckets_by_name(
        self,
        name_pattern: str,
        limit: Optional[int] = None
    ) -> List[Bucket]:
        """
        Search buckets by name pattern.
        
        Args:
            name_pattern: Pattern to search for in bucket names
            limit: Maximum number of results to return
            
        Returns:
            List[Bucket]: List of matching buckets
            
        Raises:
            BucketStoreError: If search fails
        """
        try:
            # Firestore doesn't support full-text search, so we use prefix matching
            # For more advanced search, consider using Algolia or Elasticsearch
            query = self.collection_ref.where(
                "bucket_name", ">=", name_pattern
            ).where(
                "bucket_name", "<", name_pattern + "\uf8ff"  # Unicode high character for range end
            )
            
            if limit:
                query = query.limit(limit)
            
            docs = query.stream()
            
            buckets = []
            for doc in docs:
                bucket_data = doc.to_dict()
                bucket = Bucket.from_firestore_dict(bucket_data)
                buckets.append(bucket)
            
            logger.debug(f"Found {len(buckets)} buckets matching pattern '{name_pattern}'")
            return buckets
            
        except Exception as e:
            logger.error(f"Failed to search buckets by name pattern '{name_pattern}': {e}")
            raise BucketStoreError(f"Failed to search buckets by name: {e}")
    
    async def get_buckets_created_after(
        self,
        timestamp: datetime,
        limit: Optional[int] = None
    ) -> List[Bucket]:
        """
        Get buckets created after a specific timestamp.
        
        Args:
            timestamp: Timestamp to filter by
            limit: Maximum number of results to return
            
        Returns:
            List[Bucket]: List of buckets created after the timestamp
            
        Raises:
            BucketStoreError: If query fails
        """
        try:
            query = self.collection_ref.where(
                "created_at", ">", timestamp.isoformat()
            ).order_by("created_at")
            
            if limit:
                query = query.limit(limit)
            
            docs = query.stream()
            
            buckets = []
            for doc in docs:
                bucket_data = doc.to_dict()
                bucket = Bucket.from_firestore_dict(bucket_data)
                buckets.append(bucket)
            
            logger.debug(f"Found {len(buckets)} buckets created after {timestamp}")
            return buckets
            
        except Exception as e:
            logger.error(f"Failed to get buckets created after {timestamp}: {e}")
            raise BucketStoreError(f"Failed to get buckets created after timestamp: {e}")
    
    async def backup_buckets(self) -> Dict[str, Any]:
        """
        Create a backup of all bucket data.
        
        Returns:
            Dict[str, Any]: Backup data containing all buckets
            
        Raises:
            BucketStoreError: If backup fails
        """
        try:
            buckets = await self.list_buckets()
            
            backup_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "total_buckets": len(buckets),
                "buckets": [bucket.to_firestore_dict() for bucket in buckets]
            }
            
            logger.info(f"Created backup of {len(buckets)} buckets")
            return backup_data
            
        except Exception as e:
            logger.error(f"Failed to create bucket backup: {e}")
            raise BucketStoreError(f"Failed to create bucket backup: {e}")
    
    async def restore_buckets(self, backup_data: Dict[str, Any]) -> int:
        """
        Restore buckets from backup data.
        
        Args:
            backup_data: Backup data containing bucket information
            
        Returns:
            int: Number of buckets restored
            
        Raises:
            BucketStoreError: If restore fails
        """
        try:
            if "buckets" not in backup_data:
                raise BucketStoreError("Invalid backup data: missing 'buckets' field")
            
            buckets = []
            for bucket_data in backup_data["buckets"]:
                bucket = Bucket.from_firestore_dict(bucket_data)
                buckets.append(bucket)
            
            created_ids = await self.create_buckets_batch(buckets)
            
            logger.info(f"Restored {len(created_ids)} buckets from backup")
            return len(created_ids)
            
        except Exception as e:
            logger.error(f"Failed to restore buckets from backup: {e}")
            raise BucketStoreError(f"Failed to restore buckets from backup: {e}")