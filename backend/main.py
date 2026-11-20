import os
import shutil
import zipfile
import io
import re
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, Header, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session, joinedload

from backend.config import settings
from backend.database import get_db, init_db
from backend.models import User, Project, Job, JobChunk, Clip, ProcessingLog, WorkerHeartbeat
from backend.schemas import (
    ProjectCreate, ProjectResponse,
    JobResponse, JobProgressUpdate,
    JobChunkResponse, ChunkCheckpointRequest,
    ClipCreate, ClipResponse,
    LogEntryCreate, LogEntryResponse,
    WorkerClaimRequest, WorkerHeartbeatRequest,
    WorkerStatusResponse, SystemStatusResponse
)
from backend.telegram import telegram_notifier

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="ClipForge AI — Automated Distributed Video Clipping Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    os.makedirs(os.path.join(settings.STORAGE_DIR, "videos"), exist_ok=True)
    os.makedirs(os.path.join(settings.STORAGE_DIR, "clips"), exist_ok=True)
    os.makedirs(os.path.join(settings.STORAGE_DIR, "checkpoints"), exist_ok=True)
    init_db()

# Ensure directories and schema exist on import
os.makedirs(os.path.join(settings.STORAGE_DIR, "videos"), exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_DIR, "clips"), exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_DIR, "checkpoints"), exist_ok=True)
init_db()

# --- Helper Utilities ---

def validate_youtube_url(url: str) -> bool:
    if not url:
        return False
    pattern = r"(?:https?://)?(?:www\.|m\.)?(?:youtube\.com/(?:watch\?.*?\bv=|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})"
    return bool(re.search(pattern, url))

def sanitize_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", name)

def run_async_task(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(coro)
        else:
            loop.run_until_complete(coro)
    except Exception:
        pass

# --- 1. Project & Submission Endpoints ---

@app.post("/api/projects", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_project_with_job(
    project_in: ProjectCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    if project_in.source_type == "youtube":
        if not project_in.source_url or not validate_youtube_url(project_in.source_url):
            raise HTTPException(
                status_code=400,
                detail="Invalid YouTube URL. Please provide a standard watch or shorts link."
            )

    project = Project(
        name=project_in.name,
        source_type=project_in.source_type,
        source_url=project_in.source_url,
    )
    db.add(project)
    db.flush()

    job = Job(
        project_id=project.id,
        status="QUEUED",
        current_stage="QUEUED",
        progress=0.0,
        total_chunks=0,
        completed_chunks=0
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    source_info = project_in.source_url if project_in.source_type == "youtube" else "Direct Video Upload"
    background_tasks.add_task(telegram_notifier.notify_job_submitted, job.id, project.name, source_info)

    return JobResponse(
        id=job.id,
        project_id=project.id,
        project_name=project.name,
        source_type=project.source_type,
        source_url=project.source_url,
        status=job.status,
        current_stage=job.current_stage,
        progress=job.progress,
        total_chunks=job.total_chunks,
        completed_chunks=job.completed_chunks,
        worker_id=job.worker_id,
        lease_expires_at=job.lease_expires_at,
        retry_count=job.retry_count,
        max_retries=job.max_retries,
        error_details=job.error_details,
        created_at=job.created_at,
        updated_at=job.updated_at,
        clips=[]
    )

@app.post("/api/upload")
def upload_video_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    allowed_types = ["video/mp4", "video/quicktime", "video/x-matroska", "video/webm"]
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported media format '{file.content_type}'. Supported: MP4, MOV, MKV, WEBM."
        )

    clean_name = sanitize_filename(name or file.filename or "uploaded_video")
    file_id = f"upload_{int(datetime.utcnow().timestamp())}_{clean_name}"
    save_path = os.path.join(settings.STORAGE_DIR, "videos", f"{file_id}.mp4")

    bytes_written = 0
    with open(save_path, "wb") as out_file:
        while content := file.file.read(1024 * 1024):
            bytes_written += len(content)
            if bytes_written > settings.UPLOAD_MAX_BYTES:
                out_file.close()
                os.remove(save_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"Uploaded file exceeds maximum limit of {settings.UPLOAD_MAX_BYTES // (1024*1024)}MB."
                )
            out_file.write(content)

    project = Project(
        name=name or file.filename or "Uploaded Video",
        source_type="upload",
        source_file=save_path
    )
    db.add(project)
    db.flush()

    job = Job(
        project_id=project.id,
        status="QUEUED",
        current_stage="QUEUED",
        progress=0.0
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(telegram_notifier.notify_job_submitted, job.id, project.name, f"File ({bytes_written // (1024*1024)} MB)")

    return {
        "status": "success",
        "project_id": project.id,
        "job_id": job.id,
        "file_size": bytes_written,
        "saved_path": save_path
    }

# --- 2. Job Query & Management Endpoints ---

@app.get("/api/jobs", response_model=List[JobResponse])
def list_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(Job).options(joinedload(Job.project), joinedload(Job.clips)).order_by(Job.created_at.desc())
    if status:
        query = query.filter(Job.status == status)

    jobs = query.offset(offset).limit(limit).all()
    response = []
    for j in jobs:
        clips_data = [
            ClipResponse(
                id=c.id,
                job_id=c.job_id,
                chunk_id=c.chunk_id,
                title=c.title,
                start_time=c.start_time,
                end_time=c.end_time,
                duration=c.duration,
                score=c.score,
                transcript_snippet=c.transcript_snippet,
                file_path=c.file_path,
                file_size=c.file_size,
                aspect_ratio=c.aspect_ratio,
                download_url=f"/api/clips/{c.id}/download",
                created_at=c.created_at
            ) for c in j.clips
        ]
        response.append(JobResponse(
            id=j.id,
            project_id=j.project_id,
            project_name=j.project.name if j.project else "Untitled",
            source_type=j.project.source_type if j.project else "unknown",
            source_url=j.project.source_url if j.project else None,
            status=j.status,
            current_stage=j.current_stage,
            progress=j.progress,
            total_chunks=j.total_chunks,
            completed_chunks=j.completed_chunks,
            worker_id=j.worker_id,
            lease_expires_at=j.lease_expires_at,
            retry_count=j.retry_count,
            max_retries=j.max_retries,
            error_details=j.error_details,
            created_at=j.created_at,
            updated_at=j.updated_at,
            clips=clips_data
        ))
    return response

@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job_details(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).options(joinedload(Job.project), joinedload(Job.clips)).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    clips_data = [
        ClipResponse(
            id=c.id,
            job_id=c.job_id,
            chunk_id=c.chunk_id,
            title=c.title,
            start_time=c.start_time,
            end_time=c.end_time,
            duration=c.duration,
            score=c.score,
            transcript_snippet=c.transcript_snippet,
            file_path=c.file_path,
            file_size=c.file_size,
            aspect_ratio=c.aspect_ratio,
            download_url=f"/api/clips/{c.id}/download",
            created_at=c.created_at
        ) for c in job.clips
    ]

    return JobResponse(
        id=job.id,
        project_id=job.project_id,
        project_name=job.project.name if job.project else "Untitled",
        source_type=job.project.source_type if job.project else "unknown",
        source_url=job.project.source_url if job.project else None,
        status=job.status,
        current_stage=job.current_stage,
        progress=job.progress,
        total_chunks=job.total_chunks,
        completed_chunks=job.completed_chunks,
        worker_id=job.worker_id,
        lease_expires_at=job.lease_expires_at,
        retry_count=job.retry_count,
        max_retries=job.max_retries,
        error_details=job.error_details,
        created_at=job.created_at,
        updated_at=job.updated_at,
        clips=clips_data
    )

@app.post("/api/jobs/{job_id}/retry")
def retry_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = "QUEUED"
    job.current_stage = "QUEUED (Retrying)"
    job.worker_id = None
    job.lease_expires_at = None
    job.retry_count += 1
    job.error_details = None
    job.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "success", "message": "Job re-queued for processing"}

@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = "CANCELLED"
    job.current_stage = "CANCELLED"
    job.lease_expires_at = None
    job.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "success", "message": "Job cancelled"}

@app.post("/api/jobs/{job_id}/pause")
def pause_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = "PAUSED"
    job.current_stage = "PAUSED"
    job.lease_expires_at = None
    job.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "success", "message": "Job paused"}

@app.post("/api/jobs/{job_id}/resume")
def resume_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = "QUEUED"
    job.current_stage = "QUEUED (Resumed)"
    job.lease_expires_at = None
    job.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "success", "message": "Job resumed and queued"}

@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    db.delete(job)
    db.commit()
    return {"status": "success", "message": "Job and associated clips deleted"}

# --- 3. Worker Concurrency & Queue Execution Endpoints ---

@app.post("/api/worker/claim")
def claim_job(
    claim_req: WorkerClaimRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    now = datetime.utcnow()
    lease_expiration = now + timedelta(seconds=settings.LEASE_DURATION_SECONDS)

    worker_hb = db.query(WorkerHeartbeat).filter(WorkerHeartbeat.worker_id == claim_req.worker_id).first()
    if not worker_hb:
        worker_hb = WorkerHeartbeat(
            worker_id=claim_req.worker_id,
            hostname=claim_req.hostname,
            device_type=claim_req.device_type,
            last_heartbeat=now,
            status="ONLINE"
        )
        db.add(worker_hb)
    else:
        worker_hb.last_heartbeat = now
        worker_hb.hostname = claim_req.hostname or worker_hb.hostname
        worker_hb.device_type = claim_req.device_type
        worker_hb.status = "ONLINE"

    job = db.query(Job).options(joinedload(Job.project), joinedload(Job.chunks)).filter(
        or_(
            Job.status == "QUEUED",
            and_(
                Job.status.in_(["DOWNLOADING", "TRANSCRIBING", "ANALYZING", "RENDERING"]),
                Job.lease_expires_at < now,
                Job.retry_count < Job.max_retries
            )
        )
    ).order_by(Job.created_at.asc()).first()

    if not job:
        db.commit()
        return {"status": "empty", "message": "No jobs waiting in queue"}

    job.worker_id = claim_req.worker_id
    job.lease_expires_at = lease_expiration
    job.status = "DOWNLOADING"
    job.current_stage = "DOWNLOADING"
    job.updated_at = now
    worker_hb.current_job_id = job.id
    worker_hb.status = "BUSY"

    db.commit()
    db.refresh(job)

    completed_chunks = [c.chunk_index for c in job.chunks if c.status == "COMPLETED"]

    if completed_chunks:
        background_tasks.add_task(
            telegram_notifier.notify_processing_resumed,
            job.id, job.project.name, max(completed_chunks), job.total_chunks or len(completed_chunks)
        )
    else:
        background_tasks.add_task(
            telegram_notifier.notify_processing_started,
            job.id, job.project.name, claim_req.worker_id, claim_req.device_type
        )

    return {
        "status": "claimed",
        "job_id": job.id,
        "project_id": job.project_id,
        "project_name": job.project.name,
        "source_type": job.project.source_type,
        "source_url": job.project.source_url,
        "source_file": job.project.source_file,
        "total_chunks": job.total_chunks,
        "completed_chunks": completed_chunks,
        "lease_expires_at": lease_expiration.isoformat()
    }

@app.post("/api/worker/heartbeat")
def worker_heartbeat(
    req: WorkerHeartbeatRequest,
    db: Session = Depends(get_db)
):
    now = datetime.utcnow()
    new_lease = now + timedelta(seconds=settings.LEASE_DURATION_SECONDS)

    hb = db.query(WorkerHeartbeat).filter(WorkerHeartbeat.worker_id == req.worker_id).first()
    if not hb:
        hb = WorkerHeartbeat(
            worker_id=req.worker_id,
            hostname=req.hostname,
            device_type=req.device_type,
            last_heartbeat=now,
            current_job_id=req.current_job_id,
            status=req.status
        )
        db.add(hb)
    else:
        hb.last_heartbeat = now
        hb.current_job_id = req.current_job_id
        hb.status = req.status
        if req.hostname:
            hb.hostname = req.hostname

    if req.current_job_id:
        job = db.query(Job).filter(Job.id == req.current_job_id).first()
        if job and job.worker_id == req.worker_id and job.status not in ["COMPLETED", "FAILED", "CANCELLED"]:
            job.lease_expires_at = new_lease
            job.updated_at = now

    db.commit()
    return {"status": "ok", "lease_extended_to": new_lease.isoformat() if req.current_job_id else None}

@app.post("/api/worker/jobs/{job_id}/progress")
def update_job_progress(
    job_id: str,
    update_data: JobProgressUpdate,
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if update_data.current_stage:
        job.current_stage = update_data.current_stage
        if update_data.current_stage.upper() in ["DOWNLOADING", "TRANSCRIBING", "ANALYZING", "RENDERING"]:
            job.status = update_data.current_stage.upper()
    if update_data.progress is not None:
        job.progress = min(100.0, max(0.0, update_data.progress))
    if update_data.total_chunks is not None:
        job.total_chunks = update_data.total_chunks
    if update_data.completed_chunks is not None:
        job.completed_chunks = update_data.completed_chunks
    if update_data.error_details:
        job.error_details = update_data.error_details

    job.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "success"}

@app.post("/api/worker/jobs/{job_id}/chunks/{chunk_index}/checkpoint")
def save_chunk_checkpoint(
    job_id: str,
    chunk_index: int,
    req: ChunkCheckpointRequest,
    db: Session = Depends(get_db)
):
    chunk = db.query(JobChunk).filter(
        and_(JobChunk.job_id == job_id, JobChunk.chunk_index == chunk_index)
    ).first()

    now = datetime.utcnow()
    if not chunk:
        chunk = JobChunk(
            job_id=job_id,
            chunk_index=chunk_index,
            start_time=req.checkpoint_data.get("start_time", 0.0) if req.checkpoint_data else 0.0,
            end_time=req.checkpoint_data.get("end_time", 0.0) if req.checkpoint_data else 0.0,
            status=req.status,
            checkpoint_data=req.checkpoint_data,
            created_at=now,
            updated_at=now
        )
        db.add(chunk)
    else:
        chunk.status = req.status
        chunk.checkpoint_data = req.checkpoint_data
        chunk.updated_at = now

    db.flush()
    completed_count = db.query(func.count(JobChunk.id)).filter(
        and_(JobChunk.job_id == job_id, JobChunk.status == "COMPLETED")
    ).scalar() or 0

    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        job.completed_chunks = completed_count
        if job.total_chunks > 0:
            job.progress = round((completed_count / job.total_chunks) * 100.0, 1)

    db.commit()
    return {"status": "success", "chunk_index": chunk_index}

@app.post("/api/worker/jobs/{job_id}/clips", response_model=ClipResponse)
def register_clip(
    job_id: str,
    clip_in: ClipCreate,
    db: Session = Depends(get_db)
):
    clip = Clip(
        job_id=job_id,
        chunk_id=clip_in.chunk_id,
        title=clip_in.title,
        start_time=clip_in.start_time,
        end_time=clip_in.end_time,
        duration=clip_in.duration,
        score=clip_in.score,
        transcript_snippet=clip_in.transcript_snippet,
        file_path=clip_in.file_path,
        file_size=clip_in.file_size,
        aspect_ratio=clip_in.aspect_ratio
    )
    db.add(clip)
    db.commit()
    db.refresh(clip)

    return ClipResponse(
        id=clip.id,
        job_id=clip.job_id,
        chunk_id=clip.chunk_id,
        title=clip.title,
        start_time=clip.start_time,
        end_time=clip.end_time,
        duration=clip.duration,
        score=clip.score,
        transcript_snippet=clip.transcript_snippet,
        file_path=clip.file_path,
        file_size=clip.file_size,
        aspect_ratio=clip.aspect_ratio,
        download_url=f"/api/clips/{clip.id}/download",
        created_at=clip.created_at
    )

@app.post("/api/worker/jobs/{job_id}/logs")
def add_job_log(
    job_id: str,
    log_in: LogEntryCreate,
    db: Session = Depends(get_db)
):
    log_entry = ProcessingLog(
        job_id=job_id,
        worker_id=log_in.worker_id,
        level=log_in.level,
        message=log_in.message
    )
    db.add(log_entry)
    db.commit()
    return {"status": "success"}

@app.get("/api/jobs/{job_id}/logs", response_model=List[LogEntryResponse])
def get_job_logs(job_id: str, db: Session = Depends(get_db)):
    logs = db.query(ProcessingLog).filter(ProcessingLog.job_id == job_id).order_by(ProcessingLog.created_at.asc()).all()
    return logs

@app.post("/api/worker/jobs/{job_id}/complete")
def complete_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    worker_id: str = "",
    db: Session = Depends(get_db)
):
    job = db.query(Job).options(joinedload(Job.project), joinedload(Job.clips)).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = "COMPLETED"
    job.current_stage = "COMPLETED"
    job.progress = 100.0
    job.lease_expires_at = None
    job.updated_at = datetime.utcnow()

    hb = db.query(WorkerHeartbeat).filter(WorkerHeartbeat.worker_id == worker_id).first()
    if hb:
        hb.status = "ONLINE"
        hb.current_job_id = None

    db.commit()

    duration_sec = (job.updated_at - job.created_at).total_seconds()
    clips_count = len(job.clips)
    background_tasks.add_task(
        telegram_notifier.notify_processing_completed,
        job.id, job.project.name, clips_count, duration_sec
    )

    return {"status": "success", "message": f"Job {job_id} marked COMPLETED with {clips_count} clips"}

@app.post("/api/worker/jobs/{job_id}/fail")
def fail_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    error: str = "Unknown error",
    worker_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    job = db.query(Job).options(joinedload(Job.project)).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = "FAILED"
    job.current_stage = "FAILED"
    job.error_details = error
    job.lease_expires_at = None
    job.updated_at = datetime.utcnow()

    if worker_id:
        hb = db.query(WorkerHeartbeat).filter(WorkerHeartbeat.worker_id == worker_id).first()
        if hb:
            hb.status = "ONLINE"
            hb.current_job_id = None

    db.commit()
    background_tasks.add_task(telegram_notifier.notify_processing_failed, job.id, job.project.name, error)
    return {"status": "success", "message": f"Job {job_id} marked FAILED"}

# --- 4. System Status & Observability ---

@app.get("/api/status", response_model=SystemStatusResponse)
def get_system_status(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    active_threshold = now - timedelta(seconds=45)

    all_workers = db.query(WorkerHeartbeat).all()
    online_count = 0
    worker_responses = []
    for w in all_workers:
        is_active = w.last_heartbeat >= active_threshold
        if is_active:
            online_count += 1
        worker_responses.append(
            WorkerStatusResponse(
                worker_id=w.worker_id,
                hostname=w.hostname,
                device_type=w.device_type,
                last_heartbeat=w.last_heartbeat,
                current_job_id=w.current_job_id,
                status=w.status if is_active else "OFFLINE",
                is_active=is_active
            )
        )

    total_jobs = db.query(func.count(Job.id)).scalar() or 0
    active_jobs = db.query(func.count(Job.id)).filter(
        Job.status.in_(["DOWNLOADING", "TRANSCRIBING", "ANALYZING", "RENDERING"])
    ).scalar() or 0
    completed_jobs = db.query(func.count(Job.id)).filter(Job.status == "COMPLETED").scalar() or 0
    failed_jobs = db.query(func.count(Job.id)).filter(Job.status == "FAILED").scalar() or 0

    return SystemStatusResponse(
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        workers_online=online_count,
        workers=worker_responses
    )

# --- 5. Download Endpoints ---

@app.get("/api/clips/{clip_id}/download")
def download_clip(clip_id: str, db: Session = Depends(get_db)):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip or not os.path.exists(clip.file_path):
        raise HTTPException(status_code=404, detail="Clip file not found")

    filename = f"{sanitize_filename(clip.title)}.mp4"
    return FileResponse(
        clip.file_path,
        media_type="video/mp4",
        filename=filename
    )

@app.get("/api/jobs/{job_id}/download-all")
def download_all_clips(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).options(joinedload(Job.clips), joinedload(Job.project)).filter(Job.id == job_id).first()
    if not job or not job.clips:
        raise HTTPException(status_code=404, detail="No clips available for this job")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for idx, clip in enumerate(job.clips, 1):
            if os.path.exists(clip.file_path):
                arcname = f"clip_{idx:02d}_{sanitize_filename(clip.title)}.mp4"
                zip_file.write(clip.file_path, arcname=arcname)

    zip_buffer.seek(0)
    project_slug = sanitize_filename(job.project.name if job.project else "clipforge")
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={project_slug}_clips.zip"}
    )
