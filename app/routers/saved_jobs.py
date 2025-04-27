from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.saved_job import SavedJob
from app.models.job_post import JobPost
from app.schemas.saved_jobs import SaveJobResponse


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
