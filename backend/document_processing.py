"""
Document Processing Service for Legal Document Severity Classification System.

This module extends the existing text extraction functionality in text_ocr.py and utils.py
to support the legal document processing pipeline with enhanced preprocessing, chunking,
and document management capabilities.
"""

import hashlib
import logging
import re
from typing import List, Optional, Tuple
from datetime import datetime

from fastapi import UploadFile, HTTPException
from legal_models import Document, DocumentMetadata, DocumentType, SeverityLevel
from utils import extract_text_auto, VALID_FORMATS

logger = logging.getLogger(__name__)


class TextProcessor:
    """Enhanced text processing utilities for legal documents."""
    
    @staticmethod
    def clean_legal_text(text: str) -> str:
        """
        Clean and preprocess legal document text.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text suitable for embedding and classification
        """
        if not text:
            return ""
        
        # Remove excessive whitespace and normalize line breaks
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove common OCR artifacts
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\{\}\"\'\/\\\@\#\$\%\^\&\*\+\=\<\>\|]', '', text)
        
        # Normalize common legal document patterns
        text = re.sub(r'\b(WHEREAS|THEREFORE|WHEREFORE)\b', lambda m: m.group(1).capitalize(), text)
        text = re.sub(r'\b(Section|Article|Clause)\s+(\d+)', r'\1 \2', text)
        
        # Remove excessive punctuation
        text = re.sub(r'\.{3,}', '...', text)
        text = re.sub(r'-{2,}', '--', text)
        
        return text.strip()
    
    @staticmethod
    def chunk_document(text: str, max_chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """
        Split document into overlapping chunks for embedding processing.
        
        Args:
            text: Document text to chunk
            max_chunk_size: Maximum characters per chunk
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of text chunks
        """
        if not text or len(text) <= max_chunk_size:
            return [text] if text else []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + max_chunk_size
            
            # Try to break at sentence boundaries
            if end < len(text):
                # Look for sentence endings within the last 200 characters
                sentence_end = text.rfind('.', start + max_chunk_size - 200, end)
                if sentence_end > start:
                    end = sentence_end + 1
                else:
                    # Fall back to word boundaries
                    word_end = text.rfind(' ', start + max_chunk_size - 100, end)
                    if word_end > start:
                        end = word_end
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = max(start + 1, end - overlap)
            
            # Prevent infinite loops
            if start >= len(text):
                break
        
        return chunks
    
    @staticmethod
    def calculate_content_hash(text: str) -> str:
        """
        Calculate SHA-256 hash of document content for duplicate detection.
        
        Args:
            text: Document text content
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    @staticmethod
    def extract_legal_metadata(text: str, filename: str) -> dict:
        """
        Extract legal document metadata from text content.
        
        Args:
            text: Document text content
            filename: Original filename
            
        Returns:
            Dictionary of extracted metadata
        """
        metadata = {
            'word_count': len(text.split()),
            'char_count': len(text),
            'has_signatures': bool(re.search(r'\b(signature|signed|executed)\b', text, re.IGNORECASE)),
            'has_dates': bool(re.search(r'\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b', text)),
            'has_legal_terms': bool(re.search(r'\b(whereas|therefore|party|agreement|contract)\b', text, re.IGNORECASE)),
            'document_sections': len(re.findall(r'\b(section|article|clause)\s+\d+', text, re.IGNORECASE))
        }
        
        # Try to extract document type from filename or content
        filename_lower = filename.lower()
        if any(term in filename_lower for term in ['contract', 'agreement']):
            metadata['inferred_type'] = 'contract'
        elif any(term in filename_lower for term in ['policy', 'procedure']):
            metadata['inferred_type'] = 'policy'
        elif any(term in filename_lower for term in ['memo', 'memorandum']):
            metadata['inferred_type'] = 'memorandum'
        else:
            metadata['inferred_type'] = 'unknown'
        
        return metadata


class DocumentProcessor:
    """Main document processor for the legal classification system."""
    
    def __init__(self):
        self.text_processor = TextProcessor()
    
    async def process_uploaded_file(
        self, 
        file: UploadFile, 
        document_type: DocumentType,
        severity_label: Optional[SeverityLevel] = None,
        uploader_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Tuple[str, List[str], DocumentMetadata]:
        """
        Process an uploaded file and extract text with metadata.
        
        Args:
            file: Uploaded file object
            document_type: Type of document (reference or classification)
            severity_label: Severity label for reference documents
            uploader_id: ID of the user uploading the document
            tags: Optional tags for the document
            
        Returns:
            Tuple of (extracted_text, text_chunks, document_metadata)
            
        Raises:
            HTTPException: If file processing fails
        """
        # Validate file type
        if file.content_type not in VALID_FORMATS:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type: {file.content_type}. "
                       f"Supported types: {', '.join(VALID_FORMATS)}"
            )
        
        # Validate document type and severity label consistency
        if document_type == DocumentType.REFERENCE and severity_label is None:
            raise HTTPException(
                status_code=400,
                detail="Reference documents must have a severity label"
            )
        
        if document_type == DocumentType.CLASSIFICATION and severity_label is not None:
            raise HTTPException(
                status_code=400,
                detail="Classification documents should not have a severity label"
            )
        
        try:
            # Read file content
            file_bytes = await file.read()
            file_size = len(file_bytes)
            
            # Extract text using existing utilities
            raw_text = extract_text_auto(file_bytes, file.content_type, file.filename)
            
            if not raw_text or not raw_text.strip():
                raise HTTPException(
                    status_code=400,
                    detail=f"No text could be extracted from {file.filename}"
                )
            
            # Clean and preprocess text
            cleaned_text = self.text_processor.clean_legal_text(raw_text)
            
            if not cleaned_text:
                raise HTTPException(
                    status_code=400,
                    detail=f"Document {file.filename} contains no readable text after processing"
                )
            
            # Generate text chunks for embedding
            text_chunks = self.text_processor.chunk_document(cleaned_text)
            
            # Calculate content hash for duplicate detection
            content_hash = self.text_processor.calculate_content_hash(cleaned_text)
            
            # Extract legal metadata
            legal_metadata = self.text_processor.extract_legal_metadata(cleaned_text, file.filename)
            
            # Create document metadata
            metadata = DocumentMetadata(
                filename=file.filename,
                upload_date=datetime.utcnow(),
                file_size=file_size,
                content_hash=content_hash,
                uploader_id=uploader_id,
                tags=tags or []
            )
            
            # Add legal metadata to tags
            if legal_metadata.get('inferred_type') != 'unknown':
                metadata.tags.append(f"type:{legal_metadata['inferred_type']}")
            
            if legal_metadata.get('has_legal_terms'):
                metadata.tags.append("contains:legal_terms")
            
            if legal_metadata.get('has_signatures'):
                metadata.tags.append("contains:signatures")
            
            logger.info(
                f"Successfully processed document {file.filename}: "
                f"{len(cleaned_text)} chars, {len(text_chunks)} chunks"
            )
            
            return cleaned_text, text_chunks, metadata
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing document {file.filename}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Internal error processing document: {str(e)}"
            )
    
    def validate_document_text(self, text: str, min_length: int = 50) -> bool:
        """
        Validate that document text meets minimum requirements.
        
        Args:
            text: Document text to validate
            min_length: Minimum character length required
            
        Returns:
            True if text is valid, False otherwise
        """
        if not text or len(text.strip()) < min_length:
            return False
        
        # Check for reasonable text content (not just special characters)
        word_count = len(text.split())
        if word_count < 10:  # At least 10 words
            return False
        
        # Check for reasonable character distribution
        alpha_chars = sum(1 for c in text if c.isalpha())
        if alpha_chars / len(text) < 0.3:  # At least 30% alphabetic characters
            return False
        
        return True
    
    async def create_document_model(
        self,
        text: str,
        embedding: List[float],
        metadata: DocumentMetadata,
        document_type: DocumentType,
        severity_label: Optional[SeverityLevel] = None
    ) -> Document:
        """
        Create a Document model instance from processed data.
        
        Args:
            text: Processed document text
            embedding: Document embedding vector
            metadata: Document metadata
            document_type: Type of document
            severity_label: Severity label for reference documents
            
        Returns:
            Document model instance
            
        Raises:
            ValueError: If document data is invalid
        """
        # Validate inputs
        if not self.validate_document_text(text):
            raise ValueError("Document text does not meet minimum requirements")
        
        if not embedding or len(embedding) == 0:
            raise ValueError("Document embedding cannot be empty")
        
        # Create and validate document
        document = Document(
            text=text,
            embedding=embedding,
            metadata=metadata,
            document_type=document_type,
            severity_label=severity_label
        )
        
        return document
    
    async def process_text_for_classification(
        self,
        text: str,
        metadata: DocumentMetadata
    ) -> Document:
        """
        Process raw text for classification (without file upload).
        
        Args:
            text: Raw document text
            metadata: Document metadata
            
        Returns:
            Processed Document ready for classification
            
        Raises:
            ValueError: If text processing fails
        """
        try:
            # Clean and preprocess text
            cleaned_text = self.text_processor.clean_legal_text(text)
            
            if not cleaned_text:
                raise ValueError("Document contains no readable text after processing")
            
            # Validate text meets requirements
            if not self.validate_document_text(cleaned_text):
                raise ValueError("Document text does not meet minimum requirements")
            
            # Calculate content hash for duplicate detection
            content_hash = self.text_processor.calculate_content_hash(cleaned_text)
            metadata.content_hash = content_hash
            
            # Extract legal metadata and add to tags
            legal_metadata = self.text_processor.extract_legal_metadata(cleaned_text, metadata.filename)
            
            if legal_metadata.get('inferred_type') != 'unknown':
                metadata.tags.append(f"type:{legal_metadata['inferred_type']}")
            
            if legal_metadata.get('has_legal_terms'):
                metadata.tags.append("contains:legal_terms")
            
            if legal_metadata.get('has_signatures'):
                metadata.tags.append("contains:signatures")
            
            # For text-only processing, we need to generate embedding
            # This will be handled by the classification engine
            # For now, create document with empty embedding (will be filled later)
            document = Document(
                text=cleaned_text,
                embedding=[],  # Will be populated by classification engine
                metadata=metadata,
                document_type=DocumentType.CLASSIFICATION,
                severity_label=None
            )
            
            logger.info(
                f"Successfully processed text for classification: "
                f"{len(cleaned_text)} chars, filename: {metadata.filename}"
            )
            
            return document
            
        except Exception as e:
            logger.error(f"Error processing text for classification: {str(e)}")
            raise ValueError(f"Text processing failed: {str(e)}")


# Export the main classes
__all__ = ['DocumentProcessor', 'TextProcessor']