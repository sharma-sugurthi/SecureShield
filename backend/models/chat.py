from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str
    method: str
    duration_ms: float
