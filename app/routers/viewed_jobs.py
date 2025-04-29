from fastapi import APIRouter, Depends, Request, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.job_view import JobView
from app.schemas.viewed_jobs import ViewedJobsResponse, ViewedJobOut

router = APIRouter()


@router.post("/job/{job_id}/viewed", responses={401: {"description": "Not logged in"}})
async def mark_job_as_viewed(
    job_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    session_user = request.session.get("user")
    if not session_user:
        raise HTTPException(status_code=401, detail="Not logged in")

    user_id = session_user["id"]

    view = JobView(user_id=user_id, job_post_id=job_id)
    db.add(view)
    await db.commit()
    await db.refresh(view)

    return {"message": "Job marked as viewed successfully"}


@router.get(
    "/viewed-jobs",
    response_model=ViewedJobsResponse,
    responses={401: {"description": "Not logged in"}},
)
async def list_viewed_jobs(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ViewedJobsResponse:
    session_user = request.session.get("user")
    if not session_user:
        raise HTTPException(status_code=401, detail="Not logged in")

    user_id = session_user["id"]
    offset = (page - 1) * page_size

    viewed_query = await db.execute(
        select(JobView)
        .where(JobView.user_id == user_id)
        .offset(offset)
        .limit(page_size)
        .order_by(JobView.viewed_at.desc())
    )
    views = viewed_query.scalars().all()

    total_query = await db.execute(
        select(func.count()).select_from(JobView).where(JobView.user_id == user_id)
    )
    total = total_query.scalar_one()

    return ViewedJobsResponse(
        viewed_jobs=[
            ViewedJobOut(
                job_id=view.job_id,
                viewed_at=view.viewed_at,
                title=None,  # Future: can join with JobPost if needed
                company=None,
                location=None,
            )
            for view in views
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
