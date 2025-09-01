from pydantic import BaseModel
from uuid import uuid4


class User(BaseModel):
    id: str = uuid4()
    name: str
    email: str


class PDF(BaseModel):
    url: str
