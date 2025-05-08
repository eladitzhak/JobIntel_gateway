import httpx

from typing import List, Optional
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select
from app.core.config import settings
from app.models.job_post import JobPost
from app.core.database import get_db
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta, timezone
from app.models.reported_job import ReportedJob  # or your actual import path
from fastapi import Form


import os

from app.models.saved_job import SavedJob
from app.models.user import User
from app.schemas.job import JobOut, JobsResponse

# TODO:ADD TO ENV
SCRAPER_SERVICE_URL = "http://13.60.6.112:8000"  # TODO: Replace this


async def was_scraped_recently_check(keywords: list[str]) -> dict[str, bool]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SCRAPER_SERVICE_URL}/was-scraped-recently",
                params={"keywords": keywords},
                timeout=10,
            )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("❌ Scraper check failed:", e)
        return {}


router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(
    directory=os.path.join(BASE_DIR, "../templates")
)  # <- Adjust path if needed


async def trigger_scrape(keywords: list[str]) -> None:
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{SCRAPER_SERVICE_URL}/scrape",
                json={"keywords": keywords},
                headers={"X-API-KEY": settings.SCRAPER_API_KEY},
                timeout=10,
            )
    except Exception as e:
        print("❌ Failed to trigger scraper:", e)


@router.get("/", response_class=HTMLResponse)
async def homepage(
    request: Request,
    # keyword: Optional[str] = Query(None),
    # keywords: List[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
):
    """
    Renders the homepage with the latest validated job posts.

    - If a user is authenticated, the response excludes jobs that the user has reported
      (i.e., jobs with entries in the ReportedJob table for that user).
    - Displays jobs in descending order of their scraped time (most recent first).
    - Only includes jobs that are validated (JobPost.validated == True).

    Template: `homepage.html`

    Behavior:
    - If user is not logged in → shows all validated jobs.
    - If user is logged in → excludes jobs reported by the user.
    - Includes support for session-based login via cookies.

    Outcome:
    - Returns a rendered HTML page with filtered job cards.
    - Also passes `user_id`, `jobs`, and `now` as template variables.

    Future Improvements:
    - Add pagination for large job lists.
    - Add filtering/sorting by keywords, tags, or date.
    - Highlight recently posted jobs differently (e.g., "New" badge).
    - Add logic to highlight saved or applied jobs per user.
    - Enable showing jobs based on user's subscribed keywords.
    - Consider performance optimization via Redis cache or indexed views.
    - Optionally hide jobs with a high number of reports globally.

    """
    user = request.session.get("user")
    user_id = user["id"] if user else None
    session_user = request.session.get("user")

    keywords = request.query_params.getlist("keyword")

    new_keywords = []
    keywords_to_scrape = []
    # TODO if user already connected why need to pull db again?
    if session_user:
        user = await db.get(User, user_id)
        if keywords:
            scraped_status = await was_scraped_recently_check(keywords)
            keywords_to_scrape = [
                kw for kw in keywords if not scraped_status.get(kw, False)
            ]
            if keywords_to_scrape:
                # try:
                #     async with httpx.AsyncClient() as client:
                #         respons e = await client.post(
                #             f"{SCRAPER_SERVICE_URL}/scrape",
                #             json={"keywords": keywords_to_scrape},
                #             headers={"x-api-key": settings.SCRAPER_API_KEY},
                #             timeout=200,
                #         )
                #     response.raise_for_status()
                # except Exception as e:
                #     print("❌ Failed to trigger scraper:", e)
                #     # Handle the error as needed, e.g., log it or notify the user
                await trigger_scrape(keywords_to_scrape)
                print(f"🔥 Triggered scrape for: {keywords_to_scrape}")

            scraped = [k for k in keywords if scraped_status.get(k, False) is True]
            subscribed_keywords = set(user.subscribed_keywords or [])
            new_keywords = [kw for kw in keywords if kw not in subscribed_keywords]

    # Build subquery of jobs this user reported
    reported_ids = set()
    if user_id:
        """
        #TODO: improvement: If the ReportedJob table grows large, this query could become slow. Consider optimizing it with proper indexing on user_id and job_post_id.
        """
        subq = await db.execute(
            select(ReportedJob.job_post_id).where(ReportedJob.user_id == user_id)
        )
        reported_ids = {row[0] for row in subq.all()}

    # Fetch only jobs NOT reported by this user
    # Step 2: Base query — validated jobs, not reported by user
    query = select(JobPost).where(
        JobPost.validated == True, ~JobPost.id.in_(reported_ids)
    )
    # query = await db.execute(
    #     select(JobPost)
    #     .where((JobPost.validated == True) & (~JobPost.id.in_(reported_ids)))
    #     .order_by(JobPost.scraped_at.desc())
    #     .limit(5)
    # )

    if keywords:
        query = query.where(or_(*(JobPost.keywords.any(kw) for kw in keywords)))
    # if keyword:
    #     query = query.where(JobPost.keywords.any(keyword))

    query = query.order_by(JobPost.scraped_at.desc())  # Most recent first

    result = await db.execute(query)

    jobs = result.scalars().all()

    # Before return statement
    all_keywords_query = await db.execute(select(JobPost.keywords))
    all_keywords = set()
    for row in all_keywords_query.scalars():
        if row:
            all_keywords.update(row)

    top_keywords = list(sorted(all_keywords))[:10]  # Just sort alphabetically for now

    # Fetch saved job IDs for display
    saved_ids = set()
    if user_id:
        saved_query = await db.execute(
            select(SavedJob.job_post_id).where(SavedJob.user_id == user_id)
        )
        saved_ids = {row[0] for row in saved_query.all()}

    return templates.TemplateResponse(
        "homepage.html",
        {
            "request": request,
            "jobs": jobs,
            "user": user,
            "now": datetime.now(timezone.utc),
            "timedelta": timedelta,
            "saved_job_ids": saved_ids,
            # "keyword": keyword,
            "top_keywords": top_keywords,
            "all_keywords": sorted(all_keywords),  # ← ADD THI
            "new_keywords": new_keywords,  # 👈
            "keywords": keywords,  # ✅ ensure it's always present
            "keywords_to_scrape": keywords_to_scrape,  # 👈
        },
    )

    result = await db.execute(
        select(JobPost).where(JobPost.validated == True)
        # .order_by(JobPost.posted_time.desc(), JobPost.scraped_at.desc())
        # .limit(5)
    )
    jobs = result.scalars().all()

    saved_ids = set()

    if user:
        user_id = user["id"]
        saved_query = await db.execute(
            select(SavedJob.id).where(SavedJob.user_id == user["id"])
        )
        saved_ids = {row[0] for row in saved_query.all()}

    return templates.TemplateResponse(
        "homepage.html",
        {
            "request": request,
            "jobs": jobs,
            "now": datetime.now(timezone.utc),
            "timedelta": timedelta,
            "saved_job_ids": saved_ids,
        },
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


@router.post("/subscribe-keywords")
async def subscribe_keywords(
    request: Request,
    keywords: List[str] = Form(...),
    db: AsyncSession = Depends(get_db),
):
    session_user = request.session.get("user")
    if not session_user:
        return RedirectResponse("/", status_code=303)

    user_id = session_user["id"]
    user = await db.get(User, user_id)

    user.subscribed_keywords = list(set(user.subscribed_keywords or []) | set(keywords))
    await db.commit()

    return RedirectResponse("/", status_code=303)


@router.get("/jobs/updates", response_model=JobsResponse)
async def get_job_updates(
    keywords: List[str] = Query(...),
    known_ids: List[int] = Query([]),
    db: AsyncSession = Depends(get_db),
):
    # query = select(JobPost).where(JobPost.validated == True)
    query = select(JobPost)

    if keywords:
        query = query.where(or_(*(JobPost.keywords.any(kw) for kw in keywords)))
    if known_ids:
        query = query.where(JobPost.id.not_in(known_ids))

    result = await db.execute(query)
    jobs = result.scalars().all()

    # TODO: ned tp fix pagiantions
    return JobsResponse(
        jobs=[JobOut.model_validate(job) for job in jobs],
        total=len(jobs),
        page=1,
        page_size=len(jobs),
        total_pages=1,
        has_next=False,
        has_prev=False,
    )


@router.post("/trigger-scrape-safe")
async def trigger_scrape_safe_route(
    request: Request,
    # keywords: List[str] = Form(...),  # or use JSON
    payload: dict,
):
    try:
        keywords = payload.get("keywords", [])
        if not keywords:
            return {"status": "error", "detail": "No keywords provided"}
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{SCRAPER_SERVICE_URL}/scrape-from-user",
                params={"keywords": keywords},
                headers={"X-API-KEY": settings.SCRAPER_API_KEY},
                timeout=15,
            )
        return {"status": "triggered", "keywords": keywords}
    except Exception as e:
        print("❌ Failed to proxy scrape:", e)
        return {"status": "error", "detail": str(e)}
