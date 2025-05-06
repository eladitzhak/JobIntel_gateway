from typing import List
from collections import Counter

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import Depends
from fastapi import APIRouter, Request, Depends, Query

from app.core.database import get_db
from app.models.job_post import JobPost


router = APIRouter()


# In routes/api_keywords.py or wherever you want
@router.get("/keywords", response_model=List[str])
async def get_popular_keywords(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(func.unnest(JobPost.keywords)))
    all_keywords = [row[0] for row in result.all() if row[0]]
    # Count and get most common

    top = [kw for kw, _ in Counter(all_keywords).most_common(20)]
    return top
