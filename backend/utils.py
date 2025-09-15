import io
from typing import Optional

import docx
import PyPDF2 as pypdf
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

# Supported MIME types for the OCR endpoint
VALID_FORMATS = [
    # Documents
    "application/pdf",
    "application/msword",  # legacy .doc (unsupported for now)
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    # Images
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/tiff",
    "image/bmp",
]


def _extract_text_from_pdf_text_layer(file_bytes: bytes) -> str:
    """Extract text from the PDF's embedded text layer using PyPDF2.

    Returns an empty string if no text is found (common for scanned PDFs).
    """
    text = []
    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        # Attempt decryption with empty password if encrypted
        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt("")
            except Exception:
                # If we can't decrypt, return empty string so OCR fallback can try
                return ""
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text:
                text.append(page_text)
    except Exception:
        # Parsing failed; allow OCR fallback
        return ""
    return "\n".join(text).strip()


def _ocr_images(images) -> str:
    """Run Tesseract OCR on a sequence of PIL Images and return concatenated text."""
    ocr_text_parts = []
    for idx, image in enumerate(images):
        try:
            if not isinstance(image, Image.Image):
                image = Image.fromarray(image)
            # Convert to RGB to avoid mode issues
            img_rgb = image.convert("RGB")
            ocr_text = pytesseract.image_to_string(img_rgb)
            ocr_text_parts.append(ocr_text)
        except Exception:
            # Skip problematic page and continue
            continue
    return "\n".join(ocr_text_parts).strip()


def extract_text_from_pdf_bytes(file_bytes: bytes, dpi: int = 300) -> str:
    """Extract text from a PDF file.

    Strategy:
    1) Try extracting the text layer via PyPDF2.
    2) If empty (likely scanned), convert pages to images (via pdf2image) and OCR.
    """
    # Step 1: text layer
    text = _extract_text_from_pdf_text_layer(file_bytes)
    if text:
        return text

    # Step 2: OCR fallback for scanned PDFs
    try:
        images = convert_from_bytes(file_bytes, dpi=dpi, fmt="png")
        return _ocr_images(images)
    except Exception:
        # As a last resort, return empty string to signal failure upstream
        return ""


def extract_text_from_docx_bytes(file_bytes: bytes) -> str:
    """Extract text from a DOCX file by concatenating paragraph texts."""
    try:
        document = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in document.paragraphs).strip()
    except Exception:
        return ""


def extract_text_from_image_bytes(file_bytes: bytes) -> str:
    """OCR an image and return detected text."""
    try:
        image = Image.open(io.BytesIO(file_bytes))
        image = image.convert("RGB")
        return pytesseract.image_to_string(image).strip()
    except Exception:
        return ""


def extract_text_auto(
    file_bytes: bytes, content_type: str, filename: Optional[str] = None
) -> str:
    """Auto-detect the file type by content-type and route to appropriate extractor.

    - For PDFs: extract embedded text first, then OCR fallback if needed.
    - For DOCX: read paragraphs.
    - For images: OCR directly.
    - For legacy DOC (.doc): unsupported; caller should handle 415.
    """
    if content_type == "application/pdf":
        return extract_text_from_pdf_bytes(file_bytes)

    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_text_from_docx_bytes(file_bytes)

    if content_type == "application/msword":
        # Unsupported legacy DOC
        return ""

    if content_type.startswith("image/"):
        return extract_text_from_image_bytes(file_bytes)

    # Unknown type: try best-effort fallbacks using filename extension if available
    if filename:
        lower = filename.lower()
        if lower.endswith(".pdf"):
            return extract_text_from_pdf_bytes(file_bytes)
        if lower.endswith(".docx"):
            return extract_text_from_docx_bytes(file_bytes)
        if lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp")):
            return extract_text_from_image_bytes(file_bytes)

    # Give up
    return ""

