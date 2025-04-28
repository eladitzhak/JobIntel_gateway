from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class AppliedJobOut(BaseModel):
    job_id: int
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    applied_at: datetime

    class Config:
        from_attributes = True


class AppliedJobsResponse(BaseModel):
    applied_jobs: List[AppliedJobOut]
    total: int
    page: int
    page_size: int
