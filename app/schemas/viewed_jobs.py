from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ViewedJobOut(BaseModel):
    job_id: int
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    viewed_at: datetime

    class Config:
        from_attributes = True


class ViewedJobsResponse(BaseModel):
    viewed_jobs: List[ViewedJobOut]
    total: int
    page: int
    page_size: int
