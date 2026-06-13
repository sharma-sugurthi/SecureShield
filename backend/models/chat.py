from pydantic import BaseModel, Field
from typing import List, Optional

class ChatRequest(BaseModel):
    query: str = Field(..., max_length=2000)
    thread_id: Optional[int] = None

class ChatResponse(BaseModel):
    answer: str
    method: str
    duration_ms: float
    thread_id: Optional[int] = None
