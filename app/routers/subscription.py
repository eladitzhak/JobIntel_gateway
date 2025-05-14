from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from app.schemas.subscribe import SubscribeRequest
from app.core.database import commit_or_rollback, get_db
from app.models.user import User

router = APIRouter()


@router.post("/subscribe")
async def subscribe(
    subscribe_data: SubscribeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    session_user = request.session.get("user")
    if not session_user:
        raise HTTPException(status_code=401, detail="Not logged in")

    user_id = session_user["id"]

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Merge existing and new keywords
    existing_keywords = user.subscribed_keywords or []
    new_keywords = subscribe_data.keywords

    merged_keywords = list(set(existing_keywords + new_keywords))

    user.subscribed_keywords = merged_keywords
    async with commit_or_rollback(db, context=f"subscribe user_id={user_id}"):
        pass
    await db.refresh(user)

    return {
        "message": "Subscription updated successfully",
        "keywords": user.subscribed_keywords,
    }
