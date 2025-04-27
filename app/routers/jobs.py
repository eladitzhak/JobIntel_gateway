from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.schemas.job import JobsResponse, JobOut
from app.models.job_post import JobPost  # adjust import path if needed

router = APIRouter()


@router.get("/jobs", response_model=JobsResponse)
async def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
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
        base_query.offset(offset).limit(page_size).order_by(JobPost.posted_time.desc())
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
