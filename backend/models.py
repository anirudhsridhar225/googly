from pydantic import BaseModel
from uuid import uuid4
from typing import List, Optional


class User(BaseModel):
    id: str = uuid4()
    name: str
    email: str


class HighlighterOutput(BaseModel):
    documentName: List[str]
    documentId: List[str]
    severityReport: List[str]
    tags: List[str]
    severity: List[str]


class ErrorResponse(BaseModel):
    detail: str
