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
from datetime import datetime, timedelta, timezone


import os

from app.models.saved_job import SavedJob
from app.models.user import User
from app.schemas.job import JobOut, JobsResponse

# TODO:ADD TO ENV
SCRAPER_SERVICE_URL = (
    "http://13.60.6.112:8000"  # TODO: Replace this with jobscraper URL
)

RECENT_MINUTES = 120


async def was_scraped_recently_check(keywords: list[str]) -> dict[str, bool]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SCRAPER_SERVICE_URL}/was-scraped-recently",
                params={"keywords": keywords},
                timeout=5,
            )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("❌ Scraper check failed:", e, e.request.url, str(e))
        return {}


router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(
    directory=os.path.join(BASE_DIR, "../templates")
)  # <- Adjust path if needed


async def trigger_scrape(keywords: list[str]) -> None:
    if not keywords:
        return
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


async def get_current_user(
    request: Request, db: AsyncSession
) -> tuple[Optional[User], Optional[int]]:
    """
    Extracts the logged-in user from the session and fetches the user object from the database.

    Returns:
        - user: The User object if authenticated, otherwise None.
        - user_id: The user's ID if authenticated, otherwise None.
    """
    session_user = request.session.get("user")
    if not session_user:
        return None, None
    user_id = session_user["id"]
    user = await db.get(User, user_id)
    return user, user_id


# TODO: need to move out the scraping
async def prepare_keywords(
    keywords: List[str], db: AsyncSession, user: Optional[User]
) -> tuple[List[str], List[str]]:
    """
    Checks which keywords have been recently scraped using Redis (via scraper API),
    If Redis or the scraper service is unreachable, it assumes all keywords need scraping.
    triggers background scraping,
    and identifies which keywords are new to the user's subscription.

    Args:
        keywords: A list of keywords passed by the user.
        db: Database session.
        user: The authenticated User object (or None for guest users).

    Returns:
        - keywords_to_scrape: Keywords that need to be scraped.
        - new_keywords: Keywords not in the user's subscription list (empty for unauthenticated users).
    """

    keywords_to_scrape = []
    new_keywords = []

    # Step 1: Redis freshness check (via microservice)
    keywords_scraped_status = await was_scraped_recently_check(keywords)
    if not keywords_scraped_status:
        print(
            "⚠️ Redis check failed or returned no data — so assuming all keywords are stale"
        )
        keywords_to_scrape = keywords
    else:
        keywords_to_scrape = [
            kw for kw in keywords if not keywords_scraped_status.get(kw, False)
        ]

    # Step 2: Trigger scrape (non-blocking)
    await trigger_scrape(keywords_to_scrape)

    # Step 3: Compare with user's subscriptions
    new_keywords = []
    if user:
        subscribed_keywords = set(user.subscribed_keywords or [])
        new_keywords = [kw for kw in keywords if kw not in subscribed_keywords]

    return keywords_to_scrape, new_keywords

    # if keywords:
    #     keywords_scraped_status = await was_scraped_recently_check(keywords)
    #     keywords_to_scrape = [
    #         kw for kw in keywords if not keywords_scraped_status.get(kw, False)
    #     ]
    #     await trigger_scrape(keywords_to_scrape)
    #     print(f"🔥 Triggered scrape for: {keywords_to_scrape}")

    #     if user:
    #         subscribed_keywords = set(user.subscribed_keywords or [])
    #         new_keywords = [kw for kw in keywords if kw not in subscribed_keywords]

    # return keywords_to_scrape, new_keywords


# TODO: improvement: If the ReportedJob table grows large, this query could become slow. Consider optimizing it with proper indexing on user_id and job_post_id.
async def get_reported_job_ids_for_user(
    user_id: Optional[int], db: AsyncSession
) -> set[int]:
    """
    Retrieves the set of job_post_ids that the authenticated user has reported.

    Args:
        user_id: The ID of the current user (None if unauthenticated).
        db: Database session.

    Returns:
        A set of reported job_post_ids (empty if user is not logged in).
    """
    if not user_id:
        return set()

    result = await db.execute(
        select(ReportedJob.job_post_id).where(ReportedJob.user_id == user_id)
    )

    return {row[0] for row in result.all()}


async def fetch_filtered_jobs(
    db: AsyncSession, keywords: list[str], reported_ids: set[int]
) -> list[JobPost]:
    """
    Builds and executes the query to fetch validated jobs, excluding reported ones,
    and filtering by keywords if provided.

    Args:
        db: Database session.
        keywords: List of keyword filters (can be empty).
        reported_ids: Set of job IDs reported by the user to exclude.

    Returns:
        A list of JobPost objects sorted by most recently scraped.
    """

    filters = [JobPost.validated == True]
    if reported_ids:
        filters.append(~JobPost.id.in_(reported_ids))

    if keywords:
        filters.append(or_(*(JobPost.keywords.any(kw) for kw in keywords)))

    query = select(JobPost).where(*filters).order_by(JobPost.scraped_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


async def get_saved_job_ids_for_user(
    user_id: Optional[int], visible_job_ids: list[int], db: AsyncSession
) -> set[int]:
    """
    Retrieves the saved job_post_ids for the given user from the current visible jobs.

    Args:
        user_id: The authenticated user's ID, or None.
        visible_job_ids: List of JobPost IDs currently shown on the page.
        db: Database session.

    Returns:
        A set of saved job_post_ids matching the current visible jobs (empty if not logged in).
    """
    if not user_id or not visible_job_ids:
        return set()

    result = await db.execute(
        select(SavedJob.job_post_id).where(
            SavedJob.user_id == user_id,
            SavedJob.job_post_id.in_(visible_job_ids),
        )
    )
    return {row[0] for row in result.all()}


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
    # user = request.session.get("user")
    # user_id = user["id"] if user else None
    # TODO if user already connected cna skip this?
    user, user_id = await get_current_user(request, db)

    keywords = request.query_params.getlist("keyword")

    keywords_to_scrape, new_keywords_for_user = await prepare_keywords(
        keywords, db, user
    )

    # Build subquery of jobs this user reported
    user_reported_jobs_ids = await get_reported_job_ids_for_user(user_id, db)

    # Fetch only jobs NOT reported by this user
    filtered_jobs = await fetch_filtered_jobs(db, keywords, user_reported_jobs_ids)

    # Before return statement
    all_keywords_query = await db.execute(select(JobPost.keywords))
    all_keywords = set()
    for row in all_keywords_query.scalars():
        if row:
            all_keywords.update(row)

    # retturn top_keywords to show filter suggestions to the user
    top_keywords = list(sorted(all_keywords))[:10]  # Just sort alphabetically for now

    # Fetch saved job IDs for display
    job_ids = [job.id for job in filtered_jobs]
    saved_ids = await get_saved_job_ids_for_user(user_id, job_ids, db)

    return templates.TemplateResponse(
        "homepage.html",
        {
            "request": request,
            "jobs": filtered_jobs,
            "user": user,
            "now": datetime.now(timezone.utc),
            "timedelta": timedelta,
            "saved_job_ids": saved_ids,
            # "keyword": keyword,
            "top_keywords": top_keywords,
            "all_keywords": sorted(all_keywords),  # ← ADD THI
            "new_keywords": new_keywords_for_user,  # 👈
            "keywords": keywords,  # ✅ ensure it's always present
            "keywords_to_scrape": keywords_to_scrape,  # 👈
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
    """
    Retrieve recently scraped job posts that match the given keywords
    and are not already known to the frontend.

    This endpoint is used by the frontend to poll for new job posts after
    a background scraping task has been triggered (e.g., 8 seconds after page load).
    It ensures that only fresh, unseen jobs are returned to the user.

    Filtering logic:
    - Includes only jobs with `scraped_at` timestamps within the last `RECENT_MINUTES`
    - Matches any of the specified `keywords`
    - Excludes jobs with IDs listed in `known_ids` (already rendered in frontend)

    Args:
        keywords (List[str]): Keywords the client is interested in (required).
        known_ids (List[int]): JobPost IDs the client already has (optional).
        db (AsyncSession): Database session (FastAPI dependency).

    Returns:
        JobsResponse: A response object containing the filtered job posts,
                      pagination metadata (static for now), and total count.
    """
    recent_threshold = datetime.now(timezone.utc) - timedelta(minutes=RECENT_MINUTES)
    filters = [JobPost.scraped_at >= recent_threshold]

    # query jobs containing any of the keywords if provided
    if keywords:
        filters.append(or_(*(JobPost.keywords.any(kw) for kw in keywords)))

    if known_ids:
        filters.append(~JobPost.id.in_(known_ids))

    query = select(JobPost).where(*filters).order_by(JobPost.scraped_at.desc())

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
