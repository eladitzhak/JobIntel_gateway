from pydantic import BaseModel
from typing import Optional

class ReportJobRequest(BaseModel):
    job_post_id: int
    reason: str
    description: Optional[str]
