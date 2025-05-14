from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from datetime import datetime
from pytz import timezone


from app.core.config import settings
from app.core.logger import logger

ISRAEL_TZ = timezone("Israel")

DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=settings.debug)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


# Dependency to use in routers/services
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def commit_or_rollback(session: AsyncSession, *, context: str = "unspecified"):
    try:
        yield
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.exception(f"❌ DB commit failed in {context}: {e}")
