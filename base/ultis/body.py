from pydantic import BaseModel, Field
from typing import Optional, List


class SplitRequest(BaseModel):
    chunk_size: Optional[int] = 512
    chunk_overlap: Optional[int] = 128
    separators: Optional[List[str]] = ["\n\n", "\n"]

class RerankRequest(BaseModel):
    top_k: Optional[int] = 5

class QueryRequest(BaseModel):
    question: Optional[str]
    engine: Optional[str] = "bing"
    split: SplitRequest = Field(default_factory=SplitRequest)
    rerank: RerankRequest = Field(default_factory=RerankRequest)