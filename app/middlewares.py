from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from datetime import datetime
import pytz

from app.core.database import get_db
from app.models.user import User

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
                    print("⚠️ Login tracking middleware error:", e)
        else:
            print("⚠️ Session not available on this request.")
        return await call_next(request)
