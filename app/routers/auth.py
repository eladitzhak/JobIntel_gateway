from fastapi import APIRouter, Request, Depends
from starlette.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User  # Make sure lowercase if needed
from sqlalchemy import select


router = APIRouter()

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/login", include_in_schema=True)
async def login(request: Request):
    print("Login route called")
    if request.session.get("user"):
        return RedirectResponse(url="/me")
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/login/callback", name="auth_callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    print("Auth callback route called")
    token = await oauth.google.authorize_access_token(request)
    user_info = await oauth.google.userinfo(token=token)

    email = user_info["email"]

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if not user:
        print("Creating new user")
        user = User(
            email=email,
            google_id=user_info.get("sub"),
            picture=user_info.get("picture"),
            name=user_info.get("name"),  # ✅ Add this
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    request.session["user"] = {
        "id": user.id,
        "email": user.email,
        "name": user_info.get("name"),
        # "picture": user_info.get("picture")
    }

    return RedirectResponse(url="/me")


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")


@router.get("/me", include_in_schema=True)
async def get_current_user(request: Request):
    print("Get current user route called /me")
    user = request.session.get("user")
    if user:
        return JSONResponse(content={"user": user})
    return RedirectResponse(url="/login")
