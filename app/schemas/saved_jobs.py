from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, func


class SaveJobResponse(BaseModel):
    message: str


class SavedJobOut(BaseModel):
    job_id: int
    title: Optional[str] = None  # Future: can add real title after join
    company: Optional[str] = None
    location: Optional[str] = None
    saved_at: datetime


class SavedJobsResponse(BaseModel):
    saved_jobs: List[SavedJobOut]
    total: int
    page: int
    page_size: int

    ##future use to join with jobid
    # class SavedJobOut(BaseModel):
    #     job_id: int
    #     title: Optional[str]
    #     company: Optional[str]
    #     location: Optional[str]
    #     description: Optional[str]
    #     requirements: Optional[str]
    #     posted_time: Optional[datetime]
    #     link: Optional[str]
    #     source: Optional[str]
    #     saved_at: Optional[datetime]
