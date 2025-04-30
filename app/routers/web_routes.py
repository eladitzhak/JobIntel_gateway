from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.job_post import JobPost
from app.core.database import get_db
from fastapi.templating import Jinja2Templates

import os

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(
    directory=os.path.join(BASE_DIR, "../templates")
)  # <- Adjust path if needed


@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(JobPost).order_by(JobPost.posted_time.desc()).limit(10)
    )
    jobs = result.scalars().all()
    return templates.TemplateResponse(
        "homepage.html", {"request": request, "jobs": jobs}
    )


@router.get("/job/{job_id}", response_class=HTMLResponse)
async def job_detail(request: Request, job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(JobPost).where(JobPost.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        return HTMLResponse(content="Job not found", status_code=404)
    return templates.TemplateResponse(
        "job_detail.html", {"request": request, "job": job}
    )
