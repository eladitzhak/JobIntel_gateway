from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base
from sqlalchemy.orm import relationship


class ReportedJob(Base):
    __tablename__ = "reported_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_post_id = Column(
        Integer, ForeignKey("job_posts.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    reason = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job_post = relationship("JobPost", back_populates="reports")
