from sqlalchemy import Column, Integer, ForeignKey, DateTime, func
from sqlalchemy.schema import UniqueConstraint
from app.core.database import Base


class JobApplication(Base):
    __tablename__ = "job_applications"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_application"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    job_id = Column(Integer, ForeignKey("job_posts.id", ondelete="CASCADE"))
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
