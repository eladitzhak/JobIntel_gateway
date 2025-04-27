from fastapi import FastAPI
from app.core.config import settings
from sqlalchemy import text
from fastapi import Depends
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.sessions import SessionMiddleware
from app.routers import auth, jobs
from app.routers import subscription


app = FastAPI(title="JobIntel Gateway API")

app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(subscription.router)


@app.get("/")
def read_root():
    return {
        "message": "🚀 JobIntel Gateway is live!",
        "debug": settings.debug,
        "environment": "local",
        "version": "v1.0.0",
    }


@app.get("/db-test")
async def test_db(session: AsyncSession = Depends(get_db)):
    result = await session.execute(text("SELECT 1"))
    return {"db_connected": result.scalar() == 1}
