from pydantic import BaseModel, Field
from uuid import uuid4, UUID
from typing import List, Optional


class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    email: str
    contact_number: int
    verified: bool = False
    wants_history: Optional[bool] = False
    history: List[UUID]
    # recent_chats: List["Chat"] = []  this is for caching recent chats


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    contact_number: Optional[int] = None
    wants_history: Optional[bool] = None


class Chat(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    title: str


class HighlighterOutput(BaseModel):
    documentName: List[str]
    documentId: List[str]
    severityReport: List[str]
    tags: List[str]
    severity: List[str]


class ErrorResponse(BaseModel):
    detail: str
