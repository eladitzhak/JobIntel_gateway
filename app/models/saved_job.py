from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base

class SavedJob(Base):
    __tablename__ = "saved_jobs"
    ### Ensure a user can't save the same job multiple times
    __table_args__ = (UniqueConstraint("user_id", "job_post_id", name="uq_saved_job"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    job_post_id = Column(Integer, ForeignKey("job_posts.id", ondelete="CASCADE"))
    saved_at = Column(DateTime(timezone=True), server_default=func.now())
