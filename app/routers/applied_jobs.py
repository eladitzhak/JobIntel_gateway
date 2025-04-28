from fastapi import APIRouter, Depends, Request, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.job_application import JobApplication
from app.schemas.applied_jobs import AppliedJobsResponse, AppliedJobOut

router = APIRouter()


@router.get(
    "/applied-jobs",
    response_model=AppliedJobsResponse,
    responses={401: {"description": "Not logged in"}},
)
async def list_applied_jobs(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> AppliedJobsResponse:
    session_user = request.session.get("user")
    if not session_user:
        raise HTTPException(status_code=401, detail="Not logged in")

    user_id = session_user["id"]
    offset = (page - 1) * page_size

    # Query applied jobs
    applied_query = await db.execute(
        select(JobApplication)
        .where(JobApplication.user_id == user_id)
        .offset(offset)
        .limit(page_size)
        .order_by(JobApplication.applied_at.desc())
    )
    applied_jobs = applied_query.scalars().all()

    # Query total count
    total_query = await db.execute(
        select(func.count())
        .select_from(JobApplication)
        .where(JobApplication.user_id == user_id)
    )
    total = total_query.scalar_one()

    return AppliedJobsResponse(
        applied_jobs=[
            AppliedJobOut(
                job_id=application.job_id,
                applied_at=application.applied_at,
                title=None,  # (optional: JOIN later if needed)
                company=None,
                location=None,
            )
            for application in applied_jobs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
