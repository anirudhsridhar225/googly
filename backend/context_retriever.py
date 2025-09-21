"""
Context Retrieval System for Legal Document Severity Classification.

This module implements bucket-based context extraction for classification,
including bucket selection using embedding similarity and document chunk retrieval.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

from legal_models import Document, Bucket, ContextBlock, SeverityLevel
from bucket_manager import BucketManager
from document_store import DocumentStore
from embedding_service import EmbeddingGenerator

logger = logging.getLogger(__name__)


class ContextRetriever:
    """
    Retrieves relevant context for document classification using bucket-based approach.
    
    Selects relevant buckets based on embedding similarity to centroids,
    then retrieves and scores document chunks from those buckets.
    """
    
    def __init__(
        self,
        bucket_manager: Optional[BucketManager] = None,
        document_store: Optional[DocumentStore] = None,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        max_context_chunks: int = 10,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        """
        Initialize the context retriever.
        
        Args:
            bucket_manager: Bucket manager instance
            document_store: Document store instance
            embedding_generator: Embedding generator instance
            max_context_chunks: Maximum number of chunks to retrieve
            chunk_size: Size of text chunks in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.bucket_manager = bucket_manager or BucketManager()
        self.document_store = document_store or DocumentStore()
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.max_context_chunks = max_context_chunks
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def _create_text_chunks(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            
            # Try to break at word boundaries
            if end < len(text):
                last_space = chunk.rfind(' ')
                if last_space > start + self.chunk_size // 2:
                    chunk = chunk[:last_space]
                    end = start + last_space
            
            chunks.append(chunk.strip())
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks
    
    async def _calculate_chunk_relevance_scores(
        self,
        query_embedding: List[float],
        document_chunks: List[Tuple[str, str, str]]  # (doc_id, chunk_text, bucket_id)
    ) -> List[Tuple[str, str, str, float]]:
        """
        Calculate relevance scores for document chunks using PRE-COMPUTED embeddings.
        
        Args:
            query_embedding: Query document embedding
            document_chunks: List of (doc_id, chunk_text, bucket_id) tuples
            
        Returns:
            List of (doc_id, chunk_text, bucket_id, score) tuples sorted by score
        """
        if not document_chunks:
            return []
        
        scored_chunks = []
        
        try:
            # Get unique document IDs to retrieve stored chunk embeddings
            unique_doc_ids = list(set(chunk[0] for chunk in document_chunks))
            logger.info(f"Using pre-computed embeddings for {len(unique_doc_ids)} documents, {len(document_chunks)} chunks")
            
            # Retrieve all stored chunk embeddings for these documents
            from firestore_client import get_firestore_client
            db = get_firestore_client()
            
            # Get stored chunk embeddings
            doc_chunk_embeddings = {}
            for doc_id in unique_doc_ids:
                chunks_ref = db.collection('embedding_chunks').where('document_id', '==', doc_id)
                chunk_docs = chunks_ref.stream()
                
                doc_chunks_data = []
                for chunk_doc in chunk_docs:
                    chunk_data = chunk_doc.to_dict()
                    doc_chunks_data.append({
                        'text': chunk_data.get('text', ''),
                        'embedding': chunk_data.get('embedding', []),
                        'start_char': chunk_data.get('start_char', 0),
                        'end_char': chunk_data.get('end_char', 0)
                    })
                
                doc_chunk_embeddings[doc_id] = doc_chunks_data
            
            # Calculate similarity scores using stored embeddings
            for doc_id, chunk_text, bucket_id in document_chunks:
                best_similarity = 0.0
                
                # Find matching stored chunk by text similarity
                if doc_id in doc_chunk_embeddings:
                    stored_chunks = doc_chunk_embeddings[doc_id]
                    
                    # Find the best matching stored chunk for this text chunk
                    for stored_chunk in stored_chunks:
                        stored_text = stored_chunk['text']
                        stored_embedding = stored_chunk['embedding']
                        
                        # Check if this is the same or similar chunk (simple text matching)
                        if len(stored_embedding) > 0 and (
                            chunk_text.strip() in stored_text or 
                            stored_text.strip() in chunk_text or
                            abs(len(chunk_text) - len(stored_text)) < 50
                        ):
                            similarity = self.embedding_generator.calculate_similarity(
                                query_embedding, stored_embedding
                            )
                            best_similarity = max(best_similarity, similarity)
                
                scored_chunks.append((doc_id, chunk_text, bucket_id, best_similarity))
            
            # Sort by relevance score (descending)
            scored_chunks.sort(key=lambda x: x[3], reverse=True)
            logger.info(f"Calculated similarity scores for {len(scored_chunks)} chunks using stored embeddings")
            
        except Exception as e:
            logger.warning(f"Failed to use stored embeddings, falling back to simple scoring: {e}")
            # Fallback: Use bucket centroids or simple text matching
            scored_chunks = [(doc_id, chunk_text, bucket_id, 0.5) 
                           for doc_id, chunk_text, bucket_id in document_chunks]
        
        return scored_chunks
    
    async def _retrieve_chunks_from_bucket(
        self,
        bucket: Bucket,
        query_embedding: List[float],
        max_chunks_per_bucket: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks from a specific bucket.
        
        Args:
            bucket: Bucket to retrieve chunks from
            query_embedding: Query document embedding
            max_chunks_per_bucket: Maximum chunks to retrieve from this bucket
            
        Returns:
            List of chunk dictionaries with metadata
        """
        if not bucket.document_ids:
            return []
        
        # Get documents from the bucket
        bucket_documents = await self.document_store.get_documents_by_ids(bucket.document_ids)
        
        if not bucket_documents:
            logger.warning(f"No documents found for bucket {bucket.bucket_id}")
            return []
        
        # Create chunks from all documents in the bucket
        all_chunks = []
        for doc in bucket_documents:
            doc_chunks = self._create_text_chunks(doc.text)
            for chunk_text in doc_chunks:
                all_chunks.append((doc.id, chunk_text, bucket.bucket_id))
        
        # Calculate relevance scores for chunks
        scored_chunks = await self._calculate_chunk_relevance_scores(
            query_embedding, all_chunks
        )
        
        # Return top chunks with metadata
        retrieved_chunks = []
        for doc_id, chunk_text, bucket_id, score in scored_chunks[:max_chunks_per_bucket]:
            # Find the source document for additional metadata
            source_doc = next((doc for doc in bucket_documents if doc.id == doc_id), None)
            
            chunk_info = {
                'document_id': doc_id,
                'chunk_text': chunk_text,
                'similarity_score': score,
                'bucket_id': bucket_id,
                'document_metadata': {
                    'filename': source_doc.metadata.filename if source_doc else 'unknown',
                    'severity_label': source_doc.severity_label.value if source_doc and source_doc.severity_label else None,
                    'upload_date': source_doc.metadata.upload_date.isoformat() if source_doc else None
                }
            }
            retrieved_chunks.append(chunk_info)
        
        return retrieved_chunks
    
    async def retrieve_context(
        self,
        query_document: Document,
        available_buckets: List[Bucket],
        top_k_buckets: int = 3
    ) -> ContextBlock:
        """
        Retrieve context for classification from relevant buckets.
        
        Args:
            query_document: Document to classify
            available_buckets: List of available semantic buckets
            top_k_buckets: Number of top buckets to use for context
            
        Returns:
            ContextBlock with retrieved context and metadata
        """
        if not available_buckets:
            logger.warning("No buckets available for context retrieval")
            return ContextBlock(
                bucket_info={'bucket_id': 'none', 'bucket_name': 'no_buckets'},
                retrieved_chunks=[],
                total_similarity_score=0.0
            )
        
        logger.info(f"Retrieving context for document {query_document.id} from {len(available_buckets)} buckets")
        
        # Find relevant buckets using bucket manager
        relevant_buckets = await self.bucket_manager.find_relevant_buckets(
            query_document.embedding,
            available_buckets,
            top_k=top_k_buckets
        )
        
        if not relevant_buckets:
            logger.warning(f"No relevant buckets found for document {query_document.id}")
            return ContextBlock(
                bucket_info={'bucket_id': 'none', 'bucket_name': 'no_relevant_buckets'},
                retrieved_chunks=[],
                total_similarity_score=0.0
            )
        
        # Retrieve chunks from relevant buckets
        all_retrieved_chunks = []
        total_similarity = 0.0
        primary_bucket = relevant_buckets[0][0]  # Most similar bucket
        
        chunks_per_bucket = max(1, self.max_context_chunks // len(relevant_buckets))
        
        for bucket, bucket_similarity in relevant_buckets:
            logger.debug(f"Retrieving chunks from bucket {bucket.bucket_name} (similarity: {bucket_similarity:.3f})")
            
            bucket_chunks = await self._retrieve_chunks_from_bucket(
                bucket, query_document.embedding, chunks_per_bucket
            )
            
            # Add bucket similarity to chunk metadata
            for chunk in bucket_chunks:
                chunk['bucket_similarity'] = bucket_similarity
            
            all_retrieved_chunks.extend(bucket_chunks)
            total_similarity += bucket_similarity
        
        # Sort all chunks by similarity score and limit to max_context_chunks
        all_retrieved_chunks.sort(key=lambda x: x['similarity_score'], reverse=True)
        final_chunks = all_retrieved_chunks[:self.max_context_chunks]
        
        # Create bucket info for the primary bucket
        bucket_info = {
            'bucket_id': primary_bucket.bucket_id,
            'bucket_name': primary_bucket.bucket_name,
            'bucket_description': primary_bucket.description,
            'document_count': primary_bucket.document_count,
            'selected_buckets': [
                {
                    'bucket_id': bucket.bucket_id,
                    'bucket_name': bucket.bucket_name,
                    'similarity_score': similarity
                }
                for bucket, similarity in relevant_buckets
            ]
        }
        
        context_block = ContextBlock(
            bucket_info=bucket_info,
            retrieved_chunks=final_chunks,
            total_similarity_score=total_similarity / len(relevant_buckets) if relevant_buckets else 0.0
        )
        
        logger.info(f"Retrieved {len(final_chunks)} chunks from {len(relevant_buckets)} buckets "
                   f"(avg similarity: {context_block.total_similarity_score:.3f})")
        
        return context_block
    
    async def format_context_for_classification(self, context_block: ContextBlock) -> str:
        """
        Format context block into a structured template for classification.
        
        Args:
            context_block: Context block with retrieved chunks
            
        Returns:
            Formatted context string for classification prompt
        """
        if not context_block.retrieved_chunks:
            return "No relevant context found for classification."
        
        # Group chunks by severity level for better organization
        chunks_by_severity = {}
        for chunk in context_block.retrieved_chunks:
            severity = chunk['document_metadata'].get('severity_label', 'UNKNOWN')
            if severity not in chunks_by_severity:
                chunks_by_severity[severity] = []
            chunks_by_severity[severity].append(chunk)
        
        # Build formatted context
        context_parts = []
        
        # Add bucket information
        bucket_info = context_block.bucket_info
        context_parts.append("=== CONTEXT INFORMATION ===")
        context_parts.append(f"Primary Bucket: {bucket_info.get('bucket_name', 'unknown')}")
        context_parts.append(f"Total Buckets Used: {len(bucket_info.get('selected_buckets', []))}")
        context_parts.append(f"Overall Similarity Score: {context_block.total_similarity_score:.3f}")
        context_parts.append("")
        
        # Add chunks organized by severity
        context_parts.append("=== REFERENCE EXAMPLES ===")
        
        for severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH, SeverityLevel.MEDIUM, SeverityLevel.LOW]:
            severity_chunks = chunks_by_severity.get(severity.value, [])
            if severity_chunks:
                context_parts.append(f"\n--- {severity.value} SEVERITY EXAMPLES ---")
                
                for i, chunk in enumerate(severity_chunks[:3], 1):  # Limit to 3 per severity
                    context_parts.append(f"\nExample {i} (Similarity: {chunk['similarity_score']:.3f}):")
                    context_parts.append(f"Source: {chunk['document_metadata']['filename']}")
                    context_parts.append(f"Content: {chunk['chunk_text'][:300]}...")
                    if len(chunk['chunk_text']) > 300:
                        context_parts.append("[Content truncated]")
        
        # Add any unknown severity chunks
        unknown_chunks = chunks_by_severity.get('UNKNOWN', [])
        if unknown_chunks:
            context_parts.append(f"\n--- ADDITIONAL REFERENCES ---")
            for i, chunk in enumerate(unknown_chunks[:2], 1):  # Limit to 2
                context_parts.append(f"\nReference {i} (Similarity: {chunk['similarity_score']:.3f}):")
                context_parts.append(f"Source: {chunk['document_metadata']['filename']}")
                context_parts.append(f"Content: {chunk['chunk_text'][:300]}...")
        
        context_parts.append("\n=== END CONTEXT ===")
        
        return "\n".join(context_parts)
    
    async def get_context_statistics(self, context_block: ContextBlock) -> Dict[str, Any]:
        """
        Get statistics about the retrieved context.
        
        Args:
            context_block: Context block to analyze
            
        Returns:
            Dictionary with context statistics
        """
        if not context_block.retrieved_chunks:
            return {
                'total_chunks': 0,
                'avg_similarity': 0.0,
                'severity_distribution': {},
                'source_documents': 0,
                'buckets_used': 0
            }
        
        chunks = context_block.retrieved_chunks
        
        # Calculate statistics
        similarities = [chunk['similarity_score'] for chunk in chunks]
        avg_similarity = sum(similarities) / len(similarities)
        
        # Count severity distribution
        severity_counts = {}
        source_docs = set()
        
        for chunk in chunks:
            severity = chunk['document_metadata'].get('severity_label', 'UNKNOWN')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            source_docs.add(chunk['document_id'])
        
        # Count buckets used
        buckets_used = len(context_block.bucket_info.get('selected_buckets', []))
        
        return {
            'total_chunks': len(chunks),
            'avg_similarity': avg_similarity,
            'max_similarity': max(similarities),
            'min_similarity': min(similarities),
            'severity_distribution': severity_counts,
            'source_documents': len(source_docs),
            'buckets_used': buckets_used,
            'total_similarity_score': context_block.total_similarity_score
        }


# Export the main class
__all__ = ['ContextRetriever']