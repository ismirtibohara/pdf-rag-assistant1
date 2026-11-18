from typing import List
from pydantic import BaseModel


class Source(BaseModel):
    page: int
    quote: str


class RAGAnswer(BaseModel):
    answer: str
    sources: List[Source]
    confidence: float
    found_in_document: bool