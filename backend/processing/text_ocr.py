from typing import List

import requests
from fastapi import APIRouter, File, HTTPException, UploadFile

import models
from .utils import VALID_FORMATS, extract_files

router = APIRouter()


@router.get("/health")
async def get_ocr():
    return {"message": "you've reached the ocr router"}


@router.post(
    "/categorise",
    response_model=models.HighlighterOutput,
    responses={
        415: {"description": "Unsupported Media Type", "model": models.ErrorResponse},
        400: {"description": "Bad Request", "model": models.ErrorResponse},
    },
)
async def categorise_text(files: List[UploadFile] = File(...)):
    result = await extract_files(files)
    # TODO: post-process the text using the categorization model
    return result
