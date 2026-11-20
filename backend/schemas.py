from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Project Schemas ---
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    source_type: str = Field(..., pattern="^(youtube|upload)$")
    source_url: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    name: str
    source_type: str
    source_url: Optional[str] = None
    source_file: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Clip Schemas ---
class ClipCreate(BaseModel):
    job_id: str
    chunk_id: Optional[str] = None
    title: str
    start_time: float
    end_time: float
    duration: float
    score: float = 0.0
    transcript_snippet: Optional[str] = None
    file_path: str
    file_size: int = 0
    aspect_ratio: str = "9:16"

class ClipResponse(BaseModel):
    id: str
    job_id: str
    chunk_id: Optional[str] = None
    title: str
    start_time: float
    end_time: float
    duration: float
    score: float
    transcript_snippet: Optional[str] = None
    file_path: str
    file_size: int
    aspect_ratio: str
    download_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Chunk Schemas ---
class ChunkCheckpointRequest(BaseModel):
    chunk_index: int
    status: str = Field(..., pattern="^(PENDING|PROCESSING|COMPLETED|FAILED)$")
    checkpoint_data: Optional[Dict[str, Any]] = None

class JobChunkResponse(BaseModel):
    id: str
    job_id: str
    chunk_index: int
    start_time: float
    end_time: float
    status: str
    checkpoint_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Log Schemas ---
class LogEntryCreate(BaseModel):
    job_id: str
    worker_id: Optional[str] = None
    level: str = Field(default="INFO", pattern="^(INFO|WARNING|ERROR)$")
    message: str

class LogEntryResponse(BaseModel):
    id: str
    job_id: str
    worker_id: Optional[str] = None
    level: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Job Schemas ---
class JobResponse(BaseModel):
    id: str
    project_id: str
    project_name: Optional[str] = None
    source_type: Optional[str] = None
    source_url: Optional[str] = None
    status: str
    current_stage: str
    progress: float
    total_chunks: int
    completed_chunks: int
    worker_id: Optional[str] = None
    lease_expires_at: Optional[datetime] = None
    retry_count: int
    max_retries: int
    error_details: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    clips: List[ClipResponse] = []

    class Config:
        from_attributes = True

class JobProgressUpdate(BaseModel):
    current_stage: Optional[str] = None
    progress: Optional[float] = None
    total_chunks: Optional[int] = None
    completed_chunks: Optional[int] = None
    error_details: Optional[str] = None


# --- Worker Queue Schemas ---
class WorkerClaimRequest(BaseModel):
    worker_id: str
    hostname: Optional[str] = None
    device_type: str = "cpu"  # 'cuda' | 'cpu'

class WorkerHeartbeatRequest(BaseModel):
    worker_id: str
    hostname: Optional[str] = None
    device_type: str = "cpu"
    current_job_id: Optional[str] = None
    status: str = "ONLINE"

class WorkerStatusResponse(BaseModel):
    worker_id: str
    hostname: Optional[str] = None
    device_type: str
    last_heartbeat: datetime
    current_job_id: Optional[str] = None
    status: str
    is_active: bool

    class Config:
        from_attributes = True

class SystemStatusResponse(BaseModel):
    total_jobs: int
    active_jobs: int
    completed_jobs: int
    failed_jobs: int
    workers_online: int
    workers: List[WorkerStatusResponse] = []
