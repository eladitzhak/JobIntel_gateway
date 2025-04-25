from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime

class JobPostBase(BaseModel):
    title: str
    company: Optional[str]
    description: Optional[str]
    requirements: Optional[str]
    responsibilities: Optional[str]
    link: HttpUrl
    keywords: List[str]
    source: str
    location: Optional[str]

class JobPostOut(JobPostBase):
    id: int
    posted_time: Optional[datetime]
    scraped_time: datetime
    validated: bool
    validated_date: Optional[datetime]
    status: str
    error_reason: Optional[str]
    hidden: bool

    class Config:
        from_attributes = True
