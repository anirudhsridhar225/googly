"""
Gemini Embedding Generation Service for Legal Document Severity Classification System.

This module provides embedding generation capabilities using Google's Gemini API
with rate limiting, retry logic, caching, and error handling.
"""

import asyncio
import logging
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import hashlib

import google.generativeai as genai
from google.api_core import exceptions as gcp_exceptions
from google.api_core import retry

from config import get_gemini_config
from firestore_client import get_firestore_client, Collections
from retry_mechanisms import (
    RetryMechanism, CircuitBreaker, gemini_retry_config, gemini_circuit_breaker
)
from exceptions import (
    GeminiAPIException, GeminiRateLimitException, GeminiServiceUnavailableException
)
from error_logger import error_logger

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """Firestore-based caching for embeddings to reduce API calls."""
    
    def __init__(self):
        self.collection_name = "embedding_cache"
        self.cache_ttl_days = 30  # Cache embeddings for 30 days
    
    def _generate_cache_key(self, text: str, model_name: str) -> str:
        """Generate a cache key for the given text and model."""
        content = f"{model_name}:{text}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    async def get_cached_embedding(self, text: str, model_name: str) -> Optional[List[float]]:
        """
        Retrieve cached embedding if available and not expired.
        
        Args:
            text: Input text for embedding
            model_name: Name of the embedding model
            
        Returns:
            Cached embedding vector or None if not found/expired
        """
        try:
            cache_key = self._generate_cache_key(text, model_name)
            client = get_firestore_client()
            
            doc_ref = client.collection(self.collection_name).document(cache_key)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            data = doc.to_dict()
            
            # Check if cache entry is expired
            cached_at = data.get('cached_at')
            if cached_at:
                if isinstance(cached_at, str):
                    cached_at = datetime.fromisoformat(cached_at)
                
                expiry_date = cached_at + timedelta(days=self.cache_ttl_days)
                if datetime.utcnow() > expiry_date:
                    # Cache expired, delete the entry
                    doc_ref.delete()
                    return None
            
            embedding = data.get('embedding')
            if embedding and isinstance(embedding, list):
                logger.debug(f"Cache hit for embedding (key: {cache_key[:8]}...)")
                return embedding
            
            return None
            
        except Exception as e:
            logger.warning(f"Error retrieving cached embedding: {e}")
            return None
    
    async def cache_embedding(self, text: str, model_name: str, embedding: List[float]) -> bool:
        """
        Cache an embedding in Firestore.
        
        Args:
            text: Input text for embedding
            model_name: Name of the embedding model
            embedding: Embedding vector to cache
            
        Returns:
            True if caching succeeded, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(text, model_name)
            client = get_firestore_client()
            
            cache_data = {
                'text_hash': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                'model_name': model_name,
                'embedding': embedding,
                'cached_at': datetime.utcnow().isoformat(),
                'text_length': len(text)
            }
            
            doc_ref = client.collection(self.collection_name).document(cache_key)
            doc_ref.set(cache_data)
            
            logger.debug(f"Cached embedding (key: {cache_key[:8]}...)")
            return True
            
        except Exception as e:
            logger.warning(f"Error caching embedding: {e}")
            return False


class RateLimiter:
    """Rate limiter for Gemini API calls."""
    
    def __init__(self, max_requests_per_minute: int = 60):
        self.max_requests_per_minute = max_requests_per_minute
        self.requests = []
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make an API request."""
        async with self.lock:
            now = time.time()
            
            # Remove requests older than 1 minute
            self.requests = [req_time for req_time in self.requests if now - req_time < 60]
            
            # If we're at the limit, wait
            if len(self.requests) >= self.max_requests_per_minute:
                sleep_time = 60 - (now - self.requests[0]) + 1  # Add 1 second buffer
                logger.info(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
                
                # Clean up old requests after sleeping
                now = time.time()
                self.requests = [req_time for req_time in self.requests if now - req_time < 60]
            
            # Record this request
            self.requests.append(now)


class EmbeddingGenerator:
    """Gemini-based embedding generator with caching and rate limiting."""
    
    def __init__(self):
        self.model_name = "models/embedding-001"  # Gemini embedding model
        self.cache = EmbeddingCache()
        self.rate_limiter = RateLimiter(max_requests_per_minute=50)  # Conservative limit
        self.max_retries = 3  # Keep for backward compatibility
        self.base_delay = 1.0  # Keep for backward compatibility
        
        # Initialize retry mechanism
        self.retry_mechanism = RetryMechanism(gemini_retry_config)
        
        # Initialize Gemini client
        try:
            config = get_gemini_config()
            genai.configure(api_key=config["api_key"])
            
            logger.info(f"Initialized EmbeddingGenerator with model: {self.model_name}")
            
        except Exception as e:
            error_logger.log_exception(
                e,
                context={"operation": "embedding_generator_init", "model_name": self.model_name}
            )
            raise GeminiAPIException(f"Failed to initialize embedding generator: {str(e)}", cause=e)
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector
            
        Raises:
            Exception: If embedding generation fails after retries
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Check cache first
        cached_embedding = await self.cache.get_cached_embedding(text, self.model_name)
        if cached_embedding:
            return cached_embedding
        
        # Generate new embedding with retry and circuit breaker
        async def _generate_embedding_api_call():
            await self.rate_limiter.acquire()
            
            try:
                # Use Gemini API to generate embedding
                result = genai.embed_content(
                    model=self.model_name,
                    content=text,
                    task_type="retrieval_document"
                )
                
                embedding = result['embedding']
                
                if not embedding or len(embedding) == 0:
                    raise GeminiAPIException("Received empty embedding from Gemini API")
                
                return embedding
                
            except gcp_exceptions.ResourceExhausted as e:
                # Convert to our custom exception with retry-after info
                retry_after = getattr(e, 'retry_after', None)
                raise GeminiRateLimitException(retry_after=retry_after, cause=e)
                
            except gcp_exceptions.ServiceUnavailable as e:
                raise GeminiServiceUnavailableException(cause=e)
                
            except gcp_exceptions.GoogleAPIError as e:
                raise GeminiAPIException(f"Gemini API error: {str(e)}", cause=e)
                
            except Exception as e:
                raise GeminiAPIException(f"Unexpected error generating embedding: {str(e)}", cause=e)
        
        # Execute with circuit breaker and retry
        embedding = await gemini_circuit_breaker.execute(
            self.retry_mechanism.execute_with_retry,
            _generate_embedding_api_call,
            context={"operation": "embedding_generation", "text_length": len(text)}
        )
        
        # Cache the embedding
        await self.cache.cache_embedding(text, self.model_name, embedding)
        
        logger.debug(f"Generated embedding for text ({len(text)} chars)")
        return embedding
    
    async def batch_generate_embeddings(
        self, 
        texts: List[str], 
        batch_size: int = 10,
        progress_callback: Optional[callable] = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in each batch
            progress_callback: Optional callback function for progress updates
            
        Returns:
            List of embedding vectors in the same order as input texts
            
        Raises:
            Exception: If any embedding generation fails
        """
        if not texts:
            return []
        
        embeddings = []
        total_texts = len(texts)
        
        logger.info(f"Starting batch embedding generation for {total_texts} texts")
        
        for i in range(0, total_texts, batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = []
            
            # Process each text in the batch
            for j, text in enumerate(batch_texts):
                try:
                    embedding = await self.generate_embedding(text)
                    batch_embeddings.append(embedding)
                    
                    # Call progress callback if provided
                    if progress_callback:
                        progress = (i + j + 1) / total_texts
                        progress_callback(progress, i + j + 1, total_texts)
                        
                except Exception as e:
                    logger.error(f"Failed to generate embedding for text {i + j}: {e}")
                    raise
            
            embeddings.extend(batch_embeddings)
            
            # Small delay between batches to be respectful to the API
            if i + batch_size < total_texts:
                await asyncio.sleep(0.1)
        
        logger.info(f"Completed batch embedding generation for {total_texts} texts")
        return embeddings
    
    async def chunk_text(self, text: str, chunk_size: int = 3000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks.

        Args:
            text: The full cleaned text to chunk
            chunk_size: Approximate max characters per chunk
            overlap: Number of characters to overlap between consecutive chunks

        Returns:
            List of text chunks (strings)
        """
        if not text:
            return []

        chunks = []
        start = 0
        text_len = len(text)
        while start < text_len:
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            if end >= text_len:
                break
            start = max(0, end - overlap)

        logger.debug(f"Split text into {len(chunks)} chunks (chunk_size={chunk_size}, overlap={overlap})")
        return chunks

    async def generate_chunk_embeddings(
        self,
        text: str,
        chunk_size: int = 3000,
        overlap: int = 200,
        batch_size: int = 8,
    ) -> List[Dict[str, Any]]:
        """
        Split text into chunks, generate embeddings for each chunk, and return a list
        of chunk metadata including embeddings.

        Returns list items:
            { 'chunk_index': int, 'text': str, 'embedding': List[float], 'text_length': int }
        """
        chunks = await self.chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        if not chunks:
            return []

        # Use batch embedding to leverage caching and rate limiting
        embeddings = await self.batch_generate_embeddings(chunks, batch_size=batch_size)

        if len(embeddings) != len(chunks):
            raise GeminiAPIException("Mismatch between chunks and embeddings generated")

        result = []
        for i, (chunk_text, emb) in enumerate(zip(chunks, embeddings)):
            result.append({
                'chunk_index': i,
                'text': chunk_text,
                'embedding': emb,
                'text_length': len(chunk_text)
            })

        return result

    async def store_chunk_embeddings(self, document_id: str, chunk_infos: List[Dict[str, Any]]) -> None:
        """
        Persist chunk embeddings to Firestore under collection 'embedding_chunks'.

        Each chunk document will contain: document_id, chunk_index, chunk_hash, embedding,
        text_excerpt (truncated), text_length, created_at.
        """
        try:
            client = get_firestore_client()
            collection = client.collection('embedding_chunks')

            for info in chunk_infos:
                chunk_text = info.get('text', '')
                chunk_hash = hashlib.sha256(chunk_text.encode('utf-8')).hexdigest()
                doc_data = {
                    'document_id': document_id,
                    'chunk_index': info.get('chunk_index'),
                    'chunk_hash': chunk_hash,
                    'embedding': info.get('embedding'),
                    'text_excerpt': (chunk_text[:500] + '...') if len(chunk_text) > 500 else chunk_text,
                    'text_length': info.get('text_length'),
                    'created_at': datetime.utcnow().isoformat()
                }

                # Use a deterministic id to allow idempotent writes (document_id + chunk_index)
                doc_id = f"{document_id}_{info.get('chunk_index')}"
                collection.document(doc_id).set(doc_data)

            logger.info(f"Stored {len(chunk_infos)} chunk embeddings for document {document_id}")

        except Exception as e:
            error_logger.log_exception(e, context={"operation": "store_chunk_embeddings", "document_id": document_id})
            logger.warning(f"Failed to store chunk embeddings for {document_id}: {e}")

    async def generate_query_embedding(self, query_text: str) -> List[float]:
        """
        Generate embedding for a query text (used for similarity search).
        
        Args:
            query_text: Query text to embed
            
        Returns:
            Query embedding vector
        """
        if not query_text or not query_text.strip():
            raise ValueError("Query text cannot be empty")
        
        try:
            await self.rate_limiter.acquire()
            
            # Use query-specific task type for better retrieval performance
            result = genai.embed_content(
                model=self.model_name,
                content=query_text,
                task_type="retrieval_query"
            )
            
            embedding = result['embedding']
            
            if not embedding or len(embedding) == 0:
                raise ValueError("Received empty embedding from Gemini API")
            
            logger.debug(f"Generated query embedding for text ({len(query_text)} chars)")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between -1 and 1
        """
        if len(embedding1) != len(embedding2):
            raise ValueError("Embeddings must have the same dimension")
        
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        
        # Calculate magnitudes
        magnitude1 = sum(a * a for a in embedding1) ** 0.5
        magnitude2 = sum(b * b for b in embedding2) ** 0.5
        
        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        # Calculate cosine similarity
        similarity = dot_product / (magnitude1 * magnitude2)
        return similarity
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the embedding cache.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            client = get_firestore_client()
            collection_ref = client.collection(self.cache.collection_name)
            
            # Get total count
            docs = collection_ref.stream()
            total_count = sum(1 for _ in docs)
            
            # Get recent count (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_docs = collection_ref.where('cached_at', '>=', week_ago.isoformat()).stream()
            recent_count = sum(1 for _ in recent_docs)
            
            return {
                'total_cached_embeddings': total_count,
                'recent_cached_embeddings': recent_count,
                'cache_ttl_days': self.cache.cache_ttl_days,
                'model_name': self.model_name
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                'error': str(e)
            }


# Export the main class
__all__ = ['EmbeddingGenerator', 'EmbeddingCache', 'RateLimiter']