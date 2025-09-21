#!/usr/bin/env python3
"""
Standalone script to create semantic buckets from existing reference documents.

This script:
1. Retrieves all reference documents from the database
2. Uses clustering to create semantic buckets
3. Stores the buckets back to the database

Usage:
    python create_semantic_buckets.py [--n-clusters N] [--dry-run]
"""

import argparse
import asyncio
import logging
from typing import List, Optional

from bucket_manager import BucketManager
from bucket_store import BucketStore
from document_store import DocumentStore
from firestore_client import get_firestore_client
from legal_models import Document, DocumentType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_semantic_buckets(
    n_clusters: Optional[int] = None,
    dry_run: bool = False
) -> None:
    """
    Create semantic buckets from existing reference documents.
    
    Args:
        n_clusters: Number of clusters to create (auto-determined if None)
        dry_run: If True, only show what would be done without making changes
    """
    try:
        # Initialize services
        logger.info("Initializing services...")
        firestore_client = get_firestore_client()
        document_store = DocumentStore(firestore_client)
        bucket_manager = BucketManager()
        bucket_store = BucketStore(firestore_client)
        
        # Get all reference documents
        logger.info("Retrieving reference documents...")
        reference_docs = await document_store.list_reference_documents()
        
        if not reference_docs:
            logger.warning("No reference documents found. Upload some reference documents first.")
            return
        
        logger.info(f"Found {len(reference_docs)} reference documents")
        
        # Log document info
        for doc in reference_docs:
            logger.info(f"  - {doc.metadata.filename} ({doc.severity_label.value if doc.severity_label else 'No severity'})")
        
        if dry_run:
            logger.info("DRY RUN: Would create semantic buckets from these documents")
            return
        
        # Create semantic buckets
        logger.info(f"Creating semantic buckets (n_clusters={n_clusters or 'auto'})...")
        buckets = await bucket_manager.create_buckets_from_documents(
            documents=reference_docs,
            n_clusters=n_clusters
        )
        
        logger.info(f"Created {len(buckets)} semantic buckets")
        
        # Store buckets in database
        logger.info("Storing buckets in database...")
        for bucket in buckets:
            try:
                bucket_id = await bucket_store.create_bucket(bucket)
                logger.info(f"  - Stored bucket {bucket_id}: {bucket.bucket_name} ({bucket.document_count} docs)")
            except Exception as e:
                logger.error(f"  - Failed to store bucket {bucket.bucket_name}: {e}")
        
        logger.info("✅ Semantic bucket creation completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error creating semantic buckets: {e}")
        raise


async def list_existing_buckets() -> None:
    """List existing buckets in the database."""
    try:
        logger.info("Listing existing buckets...")
        firestore_client = get_firestore_client()
        bucket_store = BucketStore(firestore_client)
        
        buckets = await bucket_store.list_buckets()
        
        if not buckets:
            logger.info("No existing buckets found")
        else:
            logger.info(f"Found {len(buckets)} existing buckets:")
            for bucket in buckets:
                logger.info(f"  - {bucket.bucket_name}: {bucket.document_count} documents")
                
    except Exception as e:
        logger.error(f"Error listing buckets: {e}")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Create semantic buckets from reference documents")
    parser.add_argument(
        "--n-clusters", 
        type=int, 
        help="Number of clusters to create (auto-determined if not specified)"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--list", 
        action="store_true", 
        help="List existing buckets and exit"
    )
    
    args = parser.parse_args()
    
    if args.list:
        await list_existing_buckets()
        return
    
    await create_semantic_buckets(
        n_clusters=args.n_clusters,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    asyncio.run(main())