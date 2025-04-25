# Track when a user views or applies to a job:
from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from app.core.database import Base


class JobView(Base):
    __tablename__ = "job_views"
    __table_args__ = (UniqueConstraint("user_id", "job_post_id", name="uq_job_view"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    job_post_id = Column(Integer, ForeignKey("job_posts.id", ondelete="CASCADE"))
    viewed_at = Column(DateTime(timezone=True), server_default=func.now())
