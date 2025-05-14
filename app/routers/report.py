from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.reported_job import ReportedJob
from app.models.user import User
from app.models.job_post import JobPost
from app.schemas.report import ReportJobRequest, ReportJobResponse

# router = APIRouter(prefix="/report-job", tags=["report-job"])
router = APIRouter()


@router.post("/report-job", response_model=ReportJobResponse)
async def report_job(
    report_data: ReportJobRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> ReportJobResponse:
    """
    Endpoint to report a job posting.
    Args:
        job_id (int): The ID of the job to report.
        reason (str): The reason for reporting the job.
    Returns:
        dict: A success message.
    """
    session_user = request.session.get("user")
    if not session_user:
        raise HTTPException(status_code=401, detail="Not logged in")
    if not report_data.job_post_id or not report_data.reason:
        raise HTTPException(status_code=400, detail="Job ID and reason are required.")
    user_id = session_user["id"]

    # Validate job exists
    job_query = await db.execute(
        select(JobPost).where(JobPost.id == report_data.job_post_id)
    )
    job = job_query.scalars().first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Save the report
    report = ReportedJob(
        user_id=user_id,
        job_post_id=report_data.job_post_id,
        reason=report_data.reason,
        free_text=html.escape(report_data.free_text) if report_data.free_text else None,  # Sanitize free_text to prevent XSS
    )

    db.add(report)
    await db.commit()
    await db.refresh(report)

    return ReportJobResponse(message="Job reported successfully")
