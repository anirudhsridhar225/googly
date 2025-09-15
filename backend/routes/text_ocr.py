from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile

import models
from utils import VALID_FORMATS, extract_text_auto

router = APIRouter()

# VALID_FORMATS imported from utils


@router.get("/health")
async def get_ocr():
    return {"message": "you've reached the ocr router"}


@router.get("/categorise")
async def get_hex():
    # TODO: handled the get endpoint to get the tags from the ai and assign hex accordingly
    return {"message": "hex_code"}


@router.post(
    "/extract",
    response_model=models.HighlighterOutput,
    responses={
        415: {"description": "Unsupported Media Type", "model": models.ErrorResponse},
        400: {"description": "Bad Request", "model": models.ErrorResponse},
    },
)
@router.post(
    "/categorise",
    include_in_schema=False,  # Backward-compatible alias
)
async def extract_text(files: List[UploadFile] = File(...)):
    """Extract text from PDFs (text or scanned) and images using centralized utils.

    Returns a HighlighterOutput where documentId holds the raw extracted text for each file.
    """
    file_names: List[str] = []
    extracted_texts: List[str] = []

    for file in files:
        if file.content_type not in VALID_FORMATS:
            raise HTTPException(
                status_code=415,
                detail=(
                    "Unsupported content type. "
                    "Supported: application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, and common image types."
                ),
            )

        file_names.append(str(file.filename))
        file_bytes = await file.read()

        # Legacy .doc is explicitly not supported
        if file.content_type == "application/msword":
            raise HTTPException(
                status_code=415,
                detail=(
                    "Legacy .doc not supported. Please convert to .docx and try again."
                ),
            )

        try:
            text = extract_text_auto(file_bytes, file.content_type, file.filename)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading {file.filename}: {e}")

        extracted_texts.append(text or "")

    return models.HighlighterOutput(
        documentName=file_names,
        documentId=extracted_texts,
        severityReport=[],
        tags=[],
        severity=[],
    )
