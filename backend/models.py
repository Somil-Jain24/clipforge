import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Float, Integer, BigInteger,
    DateTime, ForeignKey, Enum, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # 'youtube' | 'upload'
    source_url = Column(String, nullable=True)
    source_file = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="projects")
    jobs = relationship("Job", back_populates="project", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # State: QUEUED, DOWNLOADING, TRANSCRIBING, ANALYZING, RENDERING, COMPLETED, FAILED, CANCELLED, PAUSED
    status = Column(String, nullable=False, default="QUEUED")
    current_stage = Column(String, nullable=False, default="QUEUED")
    progress = Column(Float, nullable=False, default=0.0)
    total_chunks = Column(Integer, nullable=False, default=0)
    completed_chunks = Column(Integer, nullable=False, default=0)
    
    # Worker Lease management
    worker_id = Column(String, nullable=True)
    lease_expires_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    error_details = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="jobs")
    chunks = relationship("JobChunk", back_populates="job", cascade="all, delete-orphan", order_by="JobChunk.chunk_index")
    clips = relationship("Clip", back_populates="job", cascade="all, delete-orphan")
    logs = relationship("ProcessingLog", back_populates="job", cascade="all, delete-orphan", order_by="ProcessingLog.created_at")

    __table_args__ = (
        Index("idx_jobs_status", "status"),
        Index("idx_jobs_lease", "lease_expires_at"),
        Index("idx_jobs_created", "created_at"),
    )


class JobChunk(Base):
    __tablename__ = "job_chunks"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    
    # PENDING, PROCESSING, COMPLETED, FAILED
    status = Column(String, nullable=False, default="PENDING")
    checkpoint_data = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    job = relationship("Job", back_populates="chunks")
    clips = relationship("Clip", back_populates="chunk")

    __table_args__ = (
        UniqueConstraint("job_id", "chunk_index", name="uq_job_chunk_index"),
        Index("idx_job_chunks_status", "job_id", "status"),
    )


class Clip(Base):
    __tablename__ = "clips"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    chunk_id = Column(String, ForeignKey("job_chunks.id", ondelete="SET NULL"), nullable=True)
    title = Column(String, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)
    score = Column(Float, nullable=False, default=0.0)
    transcript_snippet = Column(Text, nullable=True)
    file_path = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False, default=0)
    aspect_ratio = Column(String, nullable=False, default="9:16")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    job = relationship("Job", back_populates="clips")
    chunk = relationship("JobChunk", back_populates="clips")

    __table_args__ = (
        Index("idx_clips_job", "job_id"),
    )


class ProcessingLog(Base):
    __tablename__ = "processing_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    worker_id = Column(String, nullable=True)
    level = Column(String, nullable=False, default="INFO")  # 'INFO' | 'WARNING' | 'ERROR'
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    job = relationship("Job", back_populates="logs")

    __table_args__ = (
        Index("idx_logs_job", "job_id", "created_at"),
    )


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    worker_id = Column(String, primary_key=True)
    hostname = Column(String, nullable=True)
    device_type = Column(String, nullable=False, default="cpu")  # 'cuda' | 'cpu'
    last_heartbeat = Column(DateTime, default=datetime.utcnow, nullable=False)
    current_job_id = Column(String, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    status = Column(String, nullable=False, default="ONLINE")  # 'ONLINE' | 'BUSY' | 'OFFLINE'

    __table_args__ = (
        Index("idx_worker_heartbeats", "last_heartbeat"),
    )
