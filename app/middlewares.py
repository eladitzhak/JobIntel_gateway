from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from datetime import datetime
import pytz

from app.core.database import get_db
from app.models.user import User
from app.core.logger import logger
from sqlalchemy.ext.asyncio import AsyncSession


class LoginTrackingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if "session" in request.scope:
            session_user = request.session.get("user")
            IST = pytz.timezone("Israel")
            if session_user:
                try:
                    user_id = session_user.get("id")
                    if user_id:
                        current_time_israel = datetime.now(IST)
                        db: AsyncSession = await anext(get_db())
                        db_user = await db.get(User, user_id)
                        if db_user and db_user.last_login is None:
                            db_user.last_login = current_time_israel
                        db_user.last_seen = current_time_israel
                        await db.commit()
                except Exception as e:
                    logger.info("⚠️ Login tracking middleware error:", e)
        else:
            logger.error("⚠️ Session not available on this request.")
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"➡️ {request.method} {request.url.path}")
        try:
            response: Response = await call_next(request)
            logger.info(
                f"✅ {request.method} {request.url.path} - {response.status_code}"
            )
            return response
        except Exception as e:
            logger.error(
                f"❌ Error during request: {request.method} {request.url.path} - {e}"
            )
            raise
