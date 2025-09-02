from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List
import PyPDF2 as pypdf
import docx
import io

import models

router = APIRouter()

VALID_FORMATS = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
]


@router.get("")
async def get_ocr():
    return {"message": "you've reached the ocr router"}


@router.get("/categorise")
async def get_hex():
    # TODO: handled the get endpoint to get the tags from the ai and assign hex accordingly
    return {"message": "hex_code"}


@router.post("/categorise", response_model=models.HighlighterOutput, responses={
    415:
        {
            "description": "Unsupported Media Type",
            "model": models.ErrorResponse
        },

    400:
        {
            "description": "Bad Request",
            "model": models.ErrorResponse
        },
})
async def categorise_data(files: List[UploadFile] = File(...)):
    # TODO: handle the post endpoint to post the pdf to the ai
    file_names = []
    data = []

    for file in files:
        if file.content_type not in VALID_FORMATS:
            raise HTTPException(status_code=415, detail="Only PDF allowed")

        file_names.append(str(file.filename))
        file_bytes = await file.read()
        text = ""

        try:
            if file.content_type == "application/pdf":
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                text = "".join(page.extract_text()
                               or "" for page in reader.pages)

            elif file.content_type == "application/msword":
                raise HTTPException(
                    status_code=415, detail="Legacy doc, not supported yet, please convert to docx and try again.")

            elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                doc = docx.Document(io.BytesIO(file_bytes))
                text = "\n".join(p.text for p in doc.paragraphs)

        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading {
                                file.filename}: {e}")

        data.append(text)

    # TODO: pass the data to the ocr model and process
    return models.HighlighterOutput(
        documentName=file_names,
        documentId=data,
        severityReport=[],
        tags=[],
        severity=[]
    )
