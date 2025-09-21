#!/usr/bin/env python3
"""
Cluster embedding chunks from Firestore and create semantic buckets.
This works with the chunk-level embeddings stored during document import.
"""
import asyncio
import logging
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from pathlib import Path
from typing import List, Dict, Any
import statistics

from firestore_client import get_firestore_client
from bucket_manager import BucketManager
from bucket_store import BucketStore
from models.legal_models import Bucket

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

async def get_all_embedding_chunks():
    """
    Retrieve all embedding chunks from Firestore.
    Returns list of chunk data with embeddings, document info, and text.
    """
    db = get_firestore_client()
    
    # Get all chunks from the embedding_chunks collection
    chunks_ref = db.collection('embedding_chunks')
    chunks = chunks_ref.stream()
    
    chunk_data = []
    doc_names = {}  # Cache document names
    
    logger.info("Retrieving embedding chunks from Firestore...")
    
    for chunk in chunks:
        chunk_dict = chunk.to_dict()
        
        # Get document name if not cached
        doc_id = chunk_dict.get('document_id')
        if doc_id and doc_id not in doc_names:
            doc_ref = db.collection('legal_documents').document(doc_id)
            doc_data = doc_ref.get().to_dict()
            if doc_data and 'metadata' in doc_data:
                doc_names[doc_id] = doc_data['metadata'].get('filename', f'doc_{doc_id}')
            else:
                doc_names[doc_id] = f'doc_{doc_id}'
        
        chunk_info = {
            'chunk_id': chunk.id,
            'document_id': doc_id,
            'document_name': doc_names.get(doc_id, 'unknown'),
            'embedding': chunk_dict.get('embedding', []),
            'text': chunk_dict.get('text', ''),
            'start_char': chunk_dict.get('start_char', 0),
            'end_char': chunk_dict.get('end_char', 0)
        }
        
        if chunk_info['embedding']:  # Only include chunks with embeddings
            chunk_data.append(chunk_info)
    
    logger.info(f"Retrieved {len(chunk_data)} embedding chunks")
    return chunk_data

async def cluster_embedding_chunks(chunk_data: List[Dict], n_clusters: int = 8):
    """
    Cluster embedding chunks using K-means and create buckets.
    """
    if len(chunk_data) < n_clusters:
        n_clusters = max(2, len(chunk_data) // 2)
        logger.warning(f"Reduced clusters to {n_clusters} due to limited data")
    
    # Extract embeddings and prepare data
    embeddings = np.array([chunk['embedding'] for chunk in chunk_data])
    logger.info(f"Clustering {len(embeddings)} chunks with {embeddings.shape[1]} dimensions")
    
    # Perform K-means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(embeddings)
    
    # Calculate silhouette score
    if len(set(cluster_labels)) > 1:
        sil_score = silhouette_score(embeddings, cluster_labels)
        logger.info(f"Clustering completed: {n_clusters} clusters, silhouette score: {sil_score:.3f}")
    else:
        logger.warning("All chunks assigned to single cluster")
    
    # Group chunks by cluster
    clusters = {}
    for i, chunk in enumerate(chunk_data):
        cluster_id = int(cluster_labels[i])
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(chunk)
    
    # Create buckets from clusters
    buckets = []
    min_chunks_per_bucket = 3  # Minimum chunks per bucket
    
    for cluster_id, chunks in clusters.items():
        if len(chunks) < min_chunks_per_bucket:
            logger.warning(f"Skipping cluster {cluster_id} with only {len(chunks)} chunks")
            continue
        
        # Calculate centroid embedding
        cluster_embeddings = np.array([chunk['embedding'] for chunk in chunks])
        centroid = np.mean(cluster_embeddings, axis=0).tolist()
        
        # Generate bucket name based on common document names
        doc_names = [chunk['document_name'] for chunk in chunks]
        doc_counts = {}
        for name in doc_names:
            doc_counts[name] = doc_counts.get(name, 0) + 1
        
        # Most common documents in this cluster
        top_docs = sorted(doc_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        bucket_name = f"chunk_cluster_{cluster_id}"
        
        # Create description based on content
        sample_texts = [chunk['text'][:100] + "..." for chunk in chunks[:3]]
        description = f"Cluster {cluster_id}: {len(chunks)} chunks from {len(set(doc_names))} documents. Top docs: {', '.join([f'{doc}({count})' for doc, count in top_docs[:2]])}. Sample: {' | '.join(sample_texts)}"
        
        # Extract document IDs (unique ones)
        document_ids = list(set(chunk['document_id'] for chunk in chunks if chunk['document_id']))
        
        bucket = Bucket(
            bucket_name=bucket_name,
            centroid_embedding=centroid,
            document_ids=document_ids,
            document_count=len(document_ids),
            description=description[:500]  # Limit description length
        )
        
        buckets.append((bucket, chunks))
        logger.info(f"Created bucket '{bucket_name}' with {len(chunks)} chunks from {len(document_ids)} documents")
    
    return buckets

async def store_chunk_buckets(buckets_and_chunks):
    """Store the chunk-based buckets to Firestore."""
    bucket_store = BucketStore()
    stored_bucket_ids = []
    
    for bucket, chunks in buckets_and_chunks:
        try:
            bucket_id = await bucket_store.create_bucket(bucket)
            stored_bucket_ids.append(bucket_id)
            
            # Log bucket details
            logger.info(f"Stored bucket {bucket_id} ({bucket.bucket_name})")
            logger.info(f"  Chunks: {len(chunks)}")
            logger.info(f"  Documents: {len(bucket.document_ids)}")
            
            # Show sample chunk texts
            sample_chunks = chunks[:2]
            for i, chunk in enumerate(sample_chunks):
                text_preview = chunk['text'][:150] + "..." if len(chunk['text']) > 150 else chunk['text']
                logger.info(f"  Sample chunk {i+1}: {text_preview}")
            
        except Exception as e:
            logger.error(f"Failed to store bucket {bucket.bucket_name}: {e}")
    
    return stored_bucket_ids

async def main():
    """Main function to cluster embedding chunks."""
    print("=== Clustering Embedding Chunks ===")
    
    # Get all embedding chunks
    chunk_data = await get_all_embedding_chunks()
    
    if not chunk_data:
        print("No embedding chunks found in the database")
        return
    
    print(f"Found {len(chunk_data)} embedding chunks")
    
    # Show distribution by document
    doc_counts = {}
    for chunk in chunk_data:
        doc_name = chunk['document_name']
        doc_counts[doc_name] = doc_counts.get(doc_name, 0) + 1
    
    print("\nChunks per document:")
    for doc_name, count in sorted(doc_counts.items()):
        print(f"  {doc_name}: {count} chunks")
    
    # Try clustering with different numbers of clusters
    for n_clusters in [10, 8, 6]:
        print(f"\n--- Trying with {n_clusters} clusters ---")
        
        buckets_and_chunks = await cluster_embedding_chunks(chunk_data, n_clusters)
        
        if buckets_and_chunks:
            print(f"Successfully created {len(buckets_and_chunks)} buckets")
            
            # Store buckets
            stored_ids = await store_chunk_buckets(buckets_and_chunks)
            print(f"Stored {len(stored_ids)} buckets to Firestore")
            
            return stored_ids
        else:
            print(f"No valid buckets created with {n_clusters} clusters")
    
    print("Failed to create any buckets")

if __name__ == "__main__":
    asyncio.run(main())