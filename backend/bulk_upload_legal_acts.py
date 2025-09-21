#!/usr/bin/env python3
"""
Batch upload Tamil Nadu Legal Acts as reference documents and create semantic buckets.

This script:
1. Scans the TamilNadu_Legal_Acts directory for PDF files
2. Uploads each as a reference document to Firestore
3. Creates semantic buckets from all reference documents
4. Optionally runs clause classification on a test document

Usage:
    python bulk_upload_legal_acts.py [--dry-run] [--test-classify document.pdf]
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import hashlib

# Add the backend directory to the Python path
sys.path.append('/home/anirudh/code/projects/googly/backend')

from processing.document_processing import DocumentProcessor
from storage.document_store import DocumentStore
from storage.bucket_manager import BucketManager
from storage.bucket_store import BucketStore
from services.embedding_service import EmbeddingGenerator
from storage.firestore_client import get_firestore_client
from models.legal_models import Document, DocumentType, SeverityLevel, DocumentMetadata
from processing.utils import extract_text_auto
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LegalActsBulkUploader:
    """Handles bulk upload of Tamil Nadu Legal Acts."""
    
    def __init__(self):
        self.firestore_client = get_firestore_client()
        self.document_store = DocumentStore()
        self.document_processor = DocumentProcessor()
        self.embedding_generator = EmbeddingGenerator()
        self.bucket_manager = BucketManager()
        self.bucket_store = BucketStore(self.firestore_client)
        
        # Tamil Nadu Legal Acts directory
        self.legal_acts_dir = Path("/home/anirudh/TamilNadu_Legal_Acts/TamilNadu_Legal_Acts")
        
    def scan_legal_acts_directory(self) -> List[Path]:
        """Scan the directory for PDF files."""
        if not self.legal_acts_dir.exists():
            raise ValueError(f"Directory not found: {self.legal_acts_dir}")
        
        pdf_files = list(self.legal_acts_dir.glob("**/*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files in {self.legal_acts_dir}")
        
        return pdf_files
    
    def classify_legal_act_severity(self, filename: str, content: str) -> SeverityLevel:
        """
        Basic severity classification based on document content and filename.
        This is a simple heuristic - you can make it more sophisticated.
        """
        filename_lower = filename.lower()
        content_lower = content.lower()
        
        # Critical - Constitutional, fundamental rights, criminal procedure
        critical_keywords = [
            'constitution', 'fundamental', 'criminal procedure', 'prevention of corruption',
            'essential services', 'public safety', 'emergency', 'detention'
        ]
        
        # High - Major legislation, taxation, land rights, labor laws
        high_keywords = [
            'taxation', 'land acquisition', 'labor', 'employment', 'revenue',
            'registration', 'stamp', 'court', 'judicial', 'police'
        ]
        
        # Medium - Administrative, regulatory
        medium_keywords = [
            'regulation', 'rules', 'administrative', 'municipal', 'local',
            'licensing', 'registration', 'procedure'
        ]
        
        # Check for critical keywords
        if any(keyword in filename_lower or keyword in content_lower[:2000] 
               for keyword in critical_keywords):
            return SeverityLevel.CRITICAL
        
        # Check for high keywords
        if any(keyword in filename_lower or keyword in content_lower[:2000] 
               for keyword in high_keywords):
            return SeverityLevel.HIGH
        
        # Check for medium keywords
        if any(keyword in filename_lower or keyword in content_lower[:2000] 
               for keyword in medium_keywords):
            return SeverityLevel.MEDIUM
        
        # Default to LOW for informational acts
        return SeverityLevel.LOW
    
    def extract_tags_from_content(self, filename: str, content: str) -> List[str]:
        """Extract relevant tags from the legal act."""
        tags = []
        
        filename_lower = filename.lower()
        content_lower = content.lower()
        
        # Add category tags based on content
        tag_keywords = {
            'taxation': ['tax', 'revenue', 'duty', 'levy'],
            'land': ['land', 'acquisition', 'property', 'real estate'],
            'labor': ['labor', 'employment', 'worker', 'wages'],
            'criminal': ['criminal', 'penal', 'offence', 'punishment'],
            'civil': ['civil', 'contract', 'tort', 'damages'],
            'administrative': ['administrative', 'procedure', 'rules'],
            'municipal': ['municipal', 'local', 'corporation', 'council'],
            'judicial': ['court', 'judicial', 'procedure', 'evidence'],
            'commercial': ['commercial', 'business', 'trade', 'company'],
            'constitutional': ['constitution', 'fundamental', 'rights']
        }
        
        for tag, keywords in tag_keywords.items():
            if any(keyword in filename_lower or keyword in content_lower[:2000] 
                   for keyword in keywords):
                tags.append(tag)
        
        # Add 'legal_act' and 'tamil_nadu' as standard tags
        tags.extend(['legal_act', 'tamil_nadu'])
        
        return list(set(tags))  # Remove duplicates
    
    async def process_single_legal_act(
        self, 
        pdf_path: Path, 
        dry_run: bool = False
    ) -> Optional[Document]:
        """Process a single legal act PDF file."""
        try:
            logger.info(f"Processing: {pdf_path.name}")
            
            # Read file content
            with open(pdf_path, 'rb') as f:
                file_bytes = f.read()
            
            # Extract text using existing OCR utilities
            text_content = extract_text_auto(
                file_bytes, 
                "application/pdf", 
                pdf_path.name
            )
            
            if not text_content or len(text_content.strip()) < 100:
                logger.warning(f"Insufficient text extracted from {pdf_path.name}")
                return None
            
            # Classify severity and extract tags
            severity = self.classify_legal_act_severity(pdf_path.name, text_content)
            tags = self.extract_tags_from_content(pdf_path.name, text_content)
            
            logger.info(f"  - Severity: {severity.value}")
            logger.info(f"  - Tags: {', '.join(tags)}")
            logger.info(f"  - Text length: {len(text_content)} chars")
            
            if dry_run:
                logger.info(f"  - DRY RUN: Would upload {pdf_path.name}")
                return None
            
            # Generate embedding
            embedding = await self.embedding_generator.generate_embedding(text_content)
            
            # Create content hash for duplicate detection
            content_hash = hashlib.sha256(text_content.encode()).hexdigest()
            
            # Create document metadata
            metadata = DocumentMetadata(
                filename=pdf_path.name,
                file_size=len(file_bytes),
                content_hash=content_hash,
                upload_date=datetime.utcnow(),
                tags=tags,
                uploader_id="bulk_upload_script",
                original_format="pdf"
            )
            
            # Create document
            document = Document(
                id=f"legal_act_{content_hash[:12]}",
                document_type=DocumentType.REFERENCE,
                content=text_content,
                embedding=embedding,
                metadata=metadata,
                severity_label=severity,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Store in Firestore
            try:
                await self.document_store.store_document(document)
                logger.info(f"  ✅ Successfully uploaded: {pdf_path.name}")
                return document
            except ValueError as e:
                if "already exists" in str(e):
                    logger.info(f"  ⚠️ Skipping duplicate: {pdf_path.name}")
                    return None
                else:
                    raise
            
        except Exception as e:
            logger.error(f"  ❌ Failed to process {pdf_path.name}: {e}")
            return None
    
    async def bulk_upload_legal_acts(self, dry_run: bool = False) -> List[Document]:
        """Upload all legal acts as reference documents."""
        pdf_files = self.scan_legal_acts_directory()
        
        if not pdf_files:
            logger.warning("No PDF files found to upload")
            return []
        
        logger.info(f"Starting bulk upload of {len(pdf_files)} legal acts...")
        
        uploaded_documents = []
        
        for i, pdf_path in enumerate(pdf_files):
            logger.info(f"Progress: {i+1}/{len(pdf_files)}")
            
            document = await self.process_single_legal_act(pdf_path, dry_run)
            if document:
                uploaded_documents.append(document)
            
            # Small delay to be respectful to the API
            await asyncio.sleep(0.5)
        
        logger.info(f"✅ Bulk upload completed: {len(uploaded_documents)} documents uploaded")
        return uploaded_documents
    
    async def create_semantic_buckets(self, dry_run: bool = False) -> None:
        """Create semantic buckets from all reference documents."""
        logger.info("Creating semantic buckets from reference documents...")
        
        # Get all reference documents
        reference_docs = await self.document_store.list_reference_documents()
        
        if not reference_docs:
            logger.warning("No reference documents found for bucketing")
            return
        
        logger.info(f"Found {len(reference_docs)} reference documents for bucketing")
        
        if dry_run:
            logger.info("DRY RUN: Would create semantic buckets")
            return
        
        # Create buckets
        buckets = await self.bucket_manager.create_buckets_from_documents(
            documents=reference_docs,
            bucket_name_prefix="tamil_legal"
        )
        
        logger.info(f"Created {len(buckets)} semantic buckets")
        
        # Store buckets in database
        for bucket in buckets:
            try:
                bucket_id = await self.bucket_store.create_bucket(bucket)
                logger.info(f"  ✅ Stored bucket: {bucket.bucket_name} ({bucket.document_count} docs)")
            except Exception as e:
                logger.error(f"  ❌ Failed to store bucket {bucket.bucket_name}: {e}")
    
    async def test_clause_classification(self, test_document_path: str) -> None:
        """Test clause classification on a document."""
        logger.info(f"Testing clause classification on: {test_document_path}")
        
        if not os.path.exists(test_document_path):
            logger.error(f"Test document not found: {test_document_path}")
            return
        
        # Use the document analysis endpoint
        url = "http://localhost:8000/api/classification/analyze/document"
        
        try:
            with open(test_document_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(url, files=files, timeout=300)
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Clause classification completed successfully!")
                logger.info(f"  - Found {len(result.get('clauses', []))} problematic clauses")
                
                for i, clause in enumerate(result.get('clauses', [])[:3]):  # Show first 3
                    logger.info(f"  - Clause {i+1}: {clause.get('severity')} - {clause.get('category')}")
            else:
                logger.error(f"Clause classification failed: {response.status_code} - {response.text}")
        
        except Exception as e:
            logger.error(f"Error during clause classification: {e}")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Bulk upload Tamil Nadu Legal Acts")
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--test-classify", 
        type=str,
        help="Path to a document to test clause classification after upload"
    )
    parser.add_argument(
        "--skip-upload", 
        action="store_true",
        help="Skip upload and only create buckets from existing documents"
    )
    parser.add_argument(
        "--skip-buckets", 
        action="store_true",
        help="Skip bucket creation"
    )
    
    args = parser.parse_args()
    
    uploader = LegalActsBulkUploader()
    
    try:
        # Step 1: Bulk upload legal acts
        if not args.skip_upload:
            logger.info("🚀 Starting bulk upload of Tamil Nadu Legal Acts...")
            uploaded_docs = await uploader.bulk_upload_legal_acts(dry_run=args.dry_run)
            
            if not args.dry_run:
                logger.info(f"📊 Upload Summary:")
                logger.info(f"  - Total documents uploaded: {len(uploaded_docs)}")
                
                # Show severity distribution
                severity_counts = {}
                for doc in uploaded_docs:
                    severity = doc.severity_label.value if doc.severity_label else 'None'
                    severity_counts[severity] = severity_counts.get(severity, 0) + 1
                
                for severity, count in severity_counts.items():
                    logger.info(f"  - {severity}: {count} documents")
        
        # Step 2: Create semantic buckets
        if not args.skip_buckets:
            logger.info("🗂️ Creating semantic buckets...")
            await uploader.create_semantic_buckets(dry_run=args.dry_run)
        
        # Step 3: Test clause classification if requested
        if args.test_classify and not args.dry_run:
            logger.info("🔍 Testing clause classification...")
            await uploader.test_clause_classification(args.test_classify)
        
        logger.info("🎉 All operations completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error during bulk upload: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())