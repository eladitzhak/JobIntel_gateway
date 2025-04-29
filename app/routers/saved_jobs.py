from fastapi import APIRouter, Depends, Request, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.saved_job import SavedJob
from app.models.job_post import JobPost
from app.schemas.saved_jobs import SaveJobResponse, SavedJobsResponse, SavedJobOut


router = APIRouter()


@router.post(
    "/job/{job_id}/save",
    response_model=SaveJobResponse,
    responses={
        400: {"description": "Job already saved"},
        401: {"description": "Not logged in"},
        404: {"description": "Job not found"},
    },
)
async def save_job(
    job_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SaveJobResponse:
    session_user = request.session.get("user")
    if not session_user:
        raise HTTPException(status_code=401, detail="Not logged in")
    user_id = session_user["id"]

    # Validate job exists
    job_query = await db.execute(select(JobPost).where(JobPost.id == job_id))
    job = job_query.scalars().first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check if already saved
    saved_query = await db.execute(
        select(SavedJob).where(SavedJob.user_id == user_id, SavedJob.job_id == job_id)
    )
    already_saved = saved_query.scalars().first()

    if already_saved:
        raise HTTPException(status_code=400, detail="Job already saved")

    saved = SavedJob(user_id=user_id, job_id=job_id)
    db.add(saved)
    await db.commit()
    await db.refresh(saved)

    return {"message": "Job saved successfully"}


@router.delete(
    "/job/{job_id}/save",
    response_model=SaveJobResponse,
    responses={
        400: {"description": "Bad request"},
        401: {"description": "Not logged in"},
        404: {"description": "Saved job not found"},
    },
)
async def unsave_job(
    job_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SaveJobResponse:
    session_user = request.session.get("user")
    if not session_user:
        raise HTTPException(status_code=401, detail="Not logged in")

    user_id = session_user["id"]

    saved_query = await db.execute(
        select(SavedJob).where(SavedJob.user_id == user_id, SavedJob.job_id == job_id)
    )
    saved = saved_query.scalars().first()

    if not saved:
        raise HTTPException(status_code=404, detail="Saved job not found")

    await db.delete(saved)
    await db.commit()

    return {"message": "Job unsaved successfully"}


@router.get(
    "/saved-jobs",
    response_model=SavedJobsResponse,
    responses={
        401: {"description": "Not logged in"},
    },
)
async def list_saved_jobs(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> SavedJobsResponse:
    session_user = request.session.get("user")
    if not session_user:
        raise HTTPException(status_code=401, detail="Not logged in")

    user_id = session_user["id"]
    offset = (page - 1) * page_size

    # Query saved jobs
    saved_query = await db.execute(
        select(SavedJob)
        .where(SavedJob.user_id == user_id)
        .offset(offset)
        .limit(page_size)
        .order_by(SavedJob.saved_at.desc())
    )
    saved_jobs = saved_query.scalars().all()

    # Query total saved jobs
    total_query = await db.execute(
        select(func.count()).select_from(SavedJob).where(SavedJob.user_id == user_id)
    )
    total = total_query.scalar_one()

    return SavedJobsResponse(
        saved_jobs=[
            SavedJobOut(
                job_id=saved.job_id,
                saved_at=saved.saved_at,
                title=None,  # Improve later
                company=None,
                location=None,
            )
            for saved in saved_jobs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
