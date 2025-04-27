from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class JobOut(BaseModel):
    id: int
    title: Optional[str]
    company: Optional[str]
    location: Optional[str]
    description: Optional[str]
    requirements: Optional[str]
    posted_time: Optional[datetime]
    link: Optional[str]
    source: Optional[str]

    class Config:
        from_attributes = True  # <-- THIS IS THE NEW Pydantic v2 equivalent of orm_mode


class JobsResponse(BaseModel):
    jobs: List[JobOut]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
