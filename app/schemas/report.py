from pydantic import BaseModel, field_validator
from typing import Optional
import bleach


class ReportJobRequest(BaseModel):
    job_post_id: int
    reason: str
    description: Optional[str]

    @field_validator("description")
    @classmethod
    def clean_description(cls, v):
        if v:
            # Sanitize the description to prevent XSS
            return bleach.clean(v, strip=True)
        return v


class ReportJobResponse(BaseModel):
    message: str
