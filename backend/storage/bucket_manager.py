"""
Legal Document Severity Classification System - Bucket Manager

This module implements the bucket management system for organizing documents into semantic buckets
and performing bucket operations like creation, similarity search, and maintenance.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
import asyncio
from uuid import uuid4

from services.clustering_engine import ClusteringEngine, ClusteringResult
from models.legal_models import Document, Bucket, DocumentType

logger = logging.getLogger(__name__)


class BucketManager:
    """
    Manages the lifecycle of semantic buckets for document organization.
    
    Handles bucket creation, document assignment, similarity search,
    and maintenance operations including centroid recomputation.
    """
    
    def __init__(
        self,
        clustering_engine: Optional[ClusteringEngine] = None,
        min_documents_per_bucket: int = 3,
        max_documents_per_bucket: int = 100,
        similarity_threshold: float = 0.7
    ):
        """
        Initialize the bucket manager.
        
        Args:
            clustering_engine: Clustering engine instance (creates default if None)
            min_documents_per_bucket: Minimum documents required per bucket
            max_documents_per_bucket: Maximum documents allowed per bucket
            similarity_threshold: Threshold for bucket similarity matching
        """
        self.clustering_engine = clustering_engine or ClusteringEngine()
        self.min_documents_per_bucket = min_documents_per_bucket
        self.max_documents_per_bucket = max_documents_per_bucket
        self.similarity_threshold = similarity_threshold
    
    async def create_buckets_from_documents(
        self,
        documents: List[Document],
        n_clusters: Optional[int] = None,
        bucket_name_prefix: str = "bucket"
    ) -> List[Bucket]:
        """
        Create semantic buckets from a list of reference documents.
        
        Args:
            documents: List of reference documents to cluster
            n_clusters: Number of clusters (auto-determined if None)
            bucket_name_prefix: Prefix for generated bucket names
            
        Returns:
            List of created Bucket objects
            
        Raises:
            ValueError: If insufficient documents or invalid input
        """
        if not documents:
            raise ValueError("Cannot create buckets from empty document list")
        
        # Filter only reference documents
        reference_docs = [doc for doc in documents if doc.document_type == DocumentType.REFERENCE]
        
        if len(reference_docs) < self.min_documents_per_bucket:
            raise ValueError(f"Need at least {self.min_documents_per_bucket} reference documents")
        
        logger.info(f"Creating buckets from {len(reference_docs)} reference documents")
        
        # Extract embeddings and document IDs
        embeddings = [doc.embedding for doc in reference_docs]
        document_ids = [doc.id for doc in reference_docs]
        
        # Perform clustering
        clustering_result = self.clustering_engine.cluster_documents(
            embeddings, n_clusters=n_clusters
        )
        
        logger.info(f"Clustering completed: {clustering_result.n_clusters} clusters, "
                   f"silhouette score: {clustering_result.silhouette_score:.3f}")
        
        # Create buckets from clustering results
        buckets = []
        current_time = datetime.utcnow()
        
        for cluster_id in range(clustering_result.n_clusters):
            # Get documents assigned to this cluster
            cluster_doc_ids = [
                document_ids[i] for i, label in enumerate(clustering_result.cluster_labels)
                if label == cluster_id
            ]
            
            # Skip clusters with too few documents
            if len(cluster_doc_ids) < self.min_documents_per_bucket:
                logger.warning(f"Skipping cluster {cluster_id} with only {len(cluster_doc_ids)} documents")
                continue
            
            # Create bucket
            bucket = Bucket(
                bucket_id=str(uuid4()),
                bucket_name=f"{bucket_name_prefix}_{cluster_id}",
                centroid_embedding=clustering_result.centroids[cluster_id],
                document_ids=cluster_doc_ids,
                created_at=current_time,
                updated_at=current_time,
                document_count=len(cluster_doc_ids),
                description=f"Semantic cluster {cluster_id} with {len(cluster_doc_ids)} documents"
            )
            
            buckets.append(bucket)
        
        logger.info(f"Created {len(buckets)} buckets successfully")
        return buckets
    
    async def find_relevant_buckets(
        self,
        query_embedding: List[float],
        buckets: List[Bucket],
        top_k: int = 3,
        min_similarity: Optional[float] = None
    ) -> List[Tuple[Bucket, float]]:
        """
        Find the most relevant buckets for a query embedding.
        
        Args:
            query_embedding: Query document embedding
            buckets: List of available buckets
            top_k: Number of top buckets to return
            min_similarity: Minimum similarity threshold (uses default if None)
            
        Returns:
            List of (bucket, similarity_score) tuples, sorted by similarity
        """
        if not buckets:
            return []
        
        if min_similarity is None:
            min_similarity = self.similarity_threshold
        
        # Calculate similarities to all bucket centroids
        bucket_similarities = []
        all_similarities = []  # Track all similarities for debugging
        
        for bucket in buckets:
            similarity = self.clustering_engine.calculate_cosine_similarity(
                query_embedding, bucket.centroid_embedding
            )
            all_similarities.append((bucket.bucket_name, similarity))
            
            if similarity >= min_similarity:
                bucket_similarities.append((bucket, similarity))
        
        # Sort by similarity (descending) and return top_k
        bucket_similarities.sort(key=lambda x: x[1], reverse=True)
        
        result = bucket_similarities[:top_k]
        
        # Log similarities for debugging
        logger.info(f"Bucket similarities (threshold={min_similarity:.2f}): " + 
                   ", ".join([f"{name}:{sim:.3f}" for name, sim in all_similarities[:5]]))
        logger.info(f"Found {len(result)} relevant buckets out of {len(buckets)} total")
        
        return result
    
    async def assign_document_to_bucket(
        self,
        document: Document,
        buckets: List[Bucket],
        auto_update_centroid: bool = True
    ) -> Optional[Bucket]:
        """
        Assign a document to the most similar bucket.
        
        Args:
            document: Document to assign
            buckets: Available buckets
            auto_update_centroid: Whether to update bucket centroid after assignment
            
        Returns:
            The bucket the document was assigned to, or None if no suitable bucket
        """
        if not buckets:
            return None
        
        # Find the most similar bucket
        relevant_buckets = await self.find_relevant_buckets(
            document.embedding, buckets, top_k=1
        )
        
        if not relevant_buckets:
            logger.info(f"No suitable bucket found for document {document.id}")
            return None
        
        target_bucket, similarity = relevant_buckets[0]
        
        # Check if bucket has space
        if target_bucket.document_count >= self.max_documents_per_bucket:
            logger.warning(f"Bucket {target_bucket.bucket_id} is at capacity")
            return None
        
        # Add document to bucket
        if document.id not in target_bucket.document_ids:
            target_bucket.document_ids.append(document.id)
            target_bucket.document_count += 1
            target_bucket.updated_at = datetime.utcnow()
            
            logger.info(f"Assigned document {document.id} to bucket {target_bucket.bucket_id} "
                       f"(similarity: {similarity:.3f})")
            
            # Update centroid if requested
            if auto_update_centroid:
                # Note: This would require fetching all documents in the bucket
                # For now, we'll mark that centroid needs updating
                logger.debug(f"Bucket {target_bucket.bucket_id} centroid needs updating")
        
        return target_bucket
    
    async def update_bucket_centroid(
        self,
        bucket: Bucket,
        documents: List[Document]
    ) -> Bucket:
        """
        Update a bucket's centroid based on its current documents.
        
        Args:
            bucket: Bucket to update
            documents: All documents (to find bucket's documents)
            
        Returns:
            Updated bucket with new centroid
            
        Raises:
            ValueError: If bucket has no documents or documents not found
        """
        if not bucket.document_ids:
            raise ValueError(f"Bucket {bucket.bucket_id} has no documents")
        
        # Find documents that belong to this bucket
        bucket_documents = [
            doc for doc in documents 
            if doc.id in bucket.document_ids
        ]
        
        if not bucket_documents:
            raise ValueError(f"No documents found for bucket {bucket.bucket_id}")
        
        if len(bucket_documents) != len(bucket.document_ids):
            logger.warning(f"Found {len(bucket_documents)} documents but bucket claims "
                          f"{len(bucket.document_ids)} documents")
        
        # Extract embeddings and calculate new centroid
        embeddings = [doc.embedding for doc in bucket_documents]
        new_centroid = self.clustering_engine.update_centroid(embeddings)
        
        # Update bucket
        bucket.centroid_embedding = new_centroid
        bucket.document_count = len(bucket_documents)
        bucket.document_ids = [doc.id for doc in bucket_documents]  # Ensure consistency
        bucket.updated_at = datetime.utcnow()
        
        logger.info(f"Updated centroid for bucket {bucket.bucket_id} with {len(bucket_documents)} documents")
        
        return bucket
    
    async def update_multiple_bucket_centroids(
        self,
        buckets: List[Bucket],
        documents: List[Document]
    ) -> List[Bucket]:
        """
        Update centroids for multiple buckets.
        
        Args:
            buckets: List of buckets to update
            documents: All available documents
            
        Returns:
            List of updated buckets
        """
        updated_buckets = []
        
        for bucket in buckets:
            try:
                updated_bucket = await self.update_bucket_centroid(bucket, documents)
                updated_buckets.append(updated_bucket)
            except ValueError as e:
                logger.error(f"Failed to update bucket {bucket.bucket_id}: {e}")
                # Keep original bucket if update fails
                updated_buckets.append(bucket)
        
        return updated_buckets
    
    async def merge_buckets(
        self,
        bucket1: Bucket,
        bucket2: Bucket,
        documents: List[Document],
        new_name: Optional[str] = None
    ) -> Bucket:
        """
        Merge two buckets into one.
        
        Args:
            bucket1: First bucket to merge
            bucket2: Second bucket to merge
            documents: All documents (to recalculate centroid)
            new_name: Name for merged bucket (auto-generated if None)
            
        Returns:
            New merged bucket
        """
        # Combine document IDs
        combined_doc_ids = list(set(bucket1.document_ids + bucket2.document_ids))
        
        # Create new bucket
        merged_bucket = Bucket(
            bucket_id=str(uuid4()),
            bucket_name=new_name or f"merged_{bucket1.bucket_name}_{bucket2.bucket_name}",
            centroid_embedding=[0.0],  # Will be updated below
            document_ids=combined_doc_ids,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            document_count=len(combined_doc_ids),
            description=f"Merged bucket from {bucket1.bucket_name} and {bucket2.bucket_name}"
        )
        
        # Update centroid with combined documents
        merged_bucket = await self.update_bucket_centroid(merged_bucket, documents)
        
        logger.info(f"Merged buckets {bucket1.bucket_id} and {bucket2.bucket_id} "
                   f"into {merged_bucket.bucket_id} with {merged_bucket.document_count} documents")
        
        return merged_bucket
    
    async def split_bucket(
        self,
        bucket: Bucket,
        documents: List[Document],
        n_splits: int = 2
    ) -> List[Bucket]:
        """
        Split a bucket into multiple smaller buckets.
        
        Args:
            bucket: Bucket to split
            documents: All documents (to get bucket's documents)
            n_splits: Number of buckets to split into
            
        Returns:
            List of new buckets from the split
            
        Raises:
            ValueError: If bucket cannot be split or insufficient documents
        """
        if n_splits < 2:
            raise ValueError("Must split into at least 2 buckets")
        
        # Get documents for this bucket
        bucket_documents = [
            doc for doc in documents 
            if doc.id in bucket.document_ids
        ]
        
        if len(bucket_documents) < n_splits * self.min_documents_per_bucket:
            raise ValueError(f"Insufficient documents to split into {n_splits} buckets")
        
        # Create new buckets from clustering
        new_buckets = await self.create_buckets_from_documents(
            bucket_documents,
            n_clusters=n_splits,
            bucket_name_prefix=f"split_{bucket.bucket_name}"
        )
        
        logger.info(f"Split bucket {bucket.bucket_id} into {len(new_buckets)} new buckets")
        
        return new_buckets
    
    async def get_bucket_statistics(self, buckets: List[Bucket]) -> Dict[str, Any]:
        """
        Get statistics about the bucket collection.
        
        Args:
            buckets: List of buckets to analyze
            
        Returns:
            Dictionary with bucket statistics
        """
        if not buckets:
            return {
                "total_buckets": 0,
                "total_documents": 0,
                "avg_documents_per_bucket": 0,
                "min_documents_per_bucket": 0,
                "max_documents_per_bucket": 0,
                "empty_buckets": 0
            }
        
        document_counts = [bucket.document_count for bucket in buckets]
        total_documents = sum(document_counts)
        
        stats = {
            "total_buckets": len(buckets),
            "total_documents": total_documents,
            "avg_documents_per_bucket": total_documents / len(buckets),
            "min_documents_per_bucket": min(document_counts),
            "max_documents_per_bucket": max(document_counts),
            "empty_buckets": sum(1 for count in document_counts if count == 0),
            "bucket_names": [bucket.bucket_name for bucket in buckets],
            "creation_dates": [bucket.created_at.isoformat() for bucket in buckets]
        }
        
        return stats
    
    async def validate_bucket_integrity(
        self,
        buckets: List[Bucket],
        documents: List[Document]
    ) -> Dict[str, List[str]]:
        """
        Validate the integrity of buckets and their document assignments.
        
        Args:
            buckets: List of buckets to validate
            documents: All available documents
            
        Returns:
            Dictionary with validation issues found
        """
        issues = {
            "missing_documents": [],
            "orphaned_documents": [],
            "inconsistent_counts": [],
            "duplicate_assignments": [],
            "empty_buckets": []
        }
        
        document_id_set = {doc.id for doc in documents}
        assigned_doc_ids = set()
        
        for bucket in buckets:
            # Check for missing documents
            for doc_id in bucket.document_ids:
                if doc_id not in document_id_set:
                    issues["missing_documents"].append(
                        f"Bucket {bucket.bucket_id} references missing document {doc_id}"
                    )
                
                # Check for duplicate assignments
                if doc_id in assigned_doc_ids:
                    issues["duplicate_assignments"].append(
                        f"Document {doc_id} assigned to multiple buckets"
                    )
                assigned_doc_ids.add(doc_id)
            
            # Check count consistency
            if len(bucket.document_ids) != bucket.document_count:
                issues["inconsistent_counts"].append(
                    f"Bucket {bucket.bucket_id} count mismatch: "
                    f"claimed {bucket.document_count}, actual {len(bucket.document_ids)}"
                )
            
            # Check for empty buckets
            if bucket.document_count == 0:
                issues["empty_buckets"].append(f"Bucket {bucket.bucket_id} is empty")
        
        # Check for orphaned documents (reference docs not in any bucket)
        reference_docs = [doc for doc in documents if doc.document_type == DocumentType.REFERENCE]
        for doc in reference_docs:
            if doc.id not in assigned_doc_ids:
                issues["orphaned_documents"].append(
                    f"Reference document {doc.id} not assigned to any bucket"
                )
        
        return issues