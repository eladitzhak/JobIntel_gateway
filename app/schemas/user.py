from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    google_id: str
    picture: Optional[str] = None
    subscribed_keywords: List[str] = []

class UserCreate(UserBase):
    pass

class UserOut(UserBase):
    id: int
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True  # for pydantic v2
