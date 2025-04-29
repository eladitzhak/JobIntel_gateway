from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class JobOut(BaseModel):
    id: int
    title: Optional[str]
    company: Optional[str]
    location: Optional[str]
    posted_time: Optional[datetime]
    description: Optional[str]

    class Config:
        from_attributes = True


class JobsResponse(BaseModel):
    jobs: List[JobOut]
    total: int
    page: int
    page_size: int
