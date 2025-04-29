from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func, update
from app.core.database import get_db
from app.schemas.job import JobsResponse, JobOut
from app.models.job_post import JobPost  # adjust import path if needed
from app.models.job_view import JobView  # Import JobView
from sqlalchemy.exc import SQLAlchemyError
from fastapi import status
from datetime import datetime


router = APIRouter()


@router.get("/jobs", response_model=JobsResponse)
async def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    try:
        offset = (page - 1) * page_size

        base_query = select(JobPost)

        if keyword:
            # Filter by keyword (case-insensitive)
            keyword_pattern = f"%{keyword.lower()}%"
            base_query = base_query.where(
                JobPost.title.ilike(keyword_pattern)
                | JobPost.description.ilike(keyword_pattern)
                | func.array_to_string(JobPost.keywords, " ").ilike(keyword_pattern)
            )

        # 1. Get total count AFTER filtering
        total_query = await db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = total_query.scalar_one()

        # 2. Get paginated jobs AFTER filtering
        jobs_query = await db.execute(
            base_query.offset(offset)
            .limit(page_size)
            .order_by(JobPost.posted_time.desc())
        )
        jobs = jobs_query.scalars().all()

        # Pagination calculation
        total_pages = (total + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1

        return JobsResponse(
            jobs=jobs,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
        )
    except SQLAlchemyError as e:
        # Connection issues, DB issues, etc
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. Please try again later.",
        )
    except Exception as e:
        # Catch-all for any other exceptions
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later.",
        )


@router.get(
    "/job/{job_id}",
    response_model=JobOut,
    responses={404: {"description": "Job not found"}},
)
async def get_job_details(
    job_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JobOut:
    result = await db.execute(select(JobPost).where(JobPost.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # ✅ Update or insert the JobView with latest viewed_at timestamp
    session_user = request.session.get("user")
    if session_user:
        user_id = session_user["id"]
        view_check = await db.execute(
            select(JobView).where(
                JobView.user_id == user_id, JobView.job_post_id == job_id
            )
        )
        existing_view = view_check.scalar_one_or_none()
        if existing_view:
            await db.execute(
                update(JobView)
                .where(
                    JobView.user_id == user_id,
                    JobView.job_post_id == job_id,
                )
                .values(viewed_at=datetime.utcnow())
            )
        else:
            # If no existing view, create a new one
            db.add(JobView(user_id=user_id, job_post_id=job_id))
        try:
            await db.commit()
        except Exception as e:
            # Handle commit failure (e.g., rollback, log error, etc.)
            import logging
            logging.error(f"Failed to commit transaction for job view update: {e}")
            await db.rollback()  # for safety

    return job
