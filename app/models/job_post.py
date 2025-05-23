from sqlalchemy import Column, Integer, String, DateTime, Boolean, ARRAY, Text
from sqlalchemy.sql import func
from app.core.database import Base
from sqlalchemy.orm import relationship


class JobPost(Base):
    __tablename__ = "job_posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    responsibilities = Column(Text, nullable=True)
    link = Column(String, unique=True, nullable=False)
    keywords = Column(ARRAY(String), nullable=False)

    posted_time = Column(DateTime(timezone=True), nullable=True)
    scraped_time = Column(DateTime(timezone=True), server_default=func.now())

    source = Column(String, nullable=False)  # e.g., "GoogleSearch", "Comeet", etc.
    location = Column(String, nullable=True)

    validated = Column(Boolean, default=False)
    validated_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="pending")  # "pending", "ok", "error"
    error_reason = Column(String, nullable=True)

    hidden = Column(Boolean, default=False)  # if user-reported or admin-hidden

    ##USED BY OTHER MICROSERVICES
    snippet = Column(String, nullable=True)
    scraped_at = Column(DateTime(timezone=True), nullable=True)
    last_validated_by = Column(String, nullable=True)
    validation_notes = Column(String, nullable=True)
    fields_updated = Column(ARRAY(String), default=[])
    is_user_reported = Column(Boolean, default=False)

    reports = relationship(
        "ReportedJob", back_populates="job_post", cascade="all, delete"
    )
