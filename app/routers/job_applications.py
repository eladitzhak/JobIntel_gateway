from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.job_post import JobPost
from app.models.job_application import JobApplication

router = APIRouter()


@router.post("/job/{job_id}/applied")
async def mark_job_as_applied(
    job_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    session_user = request.session.get("user")
    if not session_user:
        raise HTTPException(status_code=401, detail="Not logged in")

    user_id = session_user["id"]

    # Validate job exists
    job_query = await db.execute(select(JobPost).where(JobPost.id == job_id))
    job = job_query.scalars().first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check if already applied
    existing_application_query = await db.execute(
        select(JobApplication).where(
            JobApplication.user_id == user_id, JobApplication.job_id == job_id
        )
    )
    existing_application = existing_application_query.scalars().first()

    if existing_application:
        raise HTTPException(status_code=400, detail="Already applied to this job")

    # Save new application
    application = JobApplication(user_id=user_id, job_id=job_id)
    db.add(application)
    await db.commit()
    await db.refresh(application)

    return {"message": "Marked job as applied successfully"}
