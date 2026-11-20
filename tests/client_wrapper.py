import os
import json
from typing import Optional, Dict, Any
from fastapi import BackgroundTasks, HTTPException
from backend.main import (
    create_project_with_job, upload_video_file, list_jobs,
    get_job_details, retry_job, cancel_job, pause_job,
    resume_job, delete_job, claim_job, worker_heartbeat,
    update_job_progress, save_chunk_checkpoint, register_clip,
    add_job_log, get_job_logs, complete_job, fail_job,
    get_system_status, download_clip, download_all_clips
)
from backend.schemas import (
    ProjectCreate, WorkerClaimRequest, WorkerHeartbeatRequest,
    JobProgressUpdate, ChunkCheckpointRequest, ClipCreate, LogEntryCreate
)

class MockResponse:
    def __init__(self, status_code: int, data: Any = None, content: bytes = b"", headers: Optional[Dict[str, str]] = None):
        self.status_code = status_code
        self._data = data
        self.content = content
        self.headers = headers or {}

    def json(self):
        if isinstance(self._data, dict) or isinstance(self._data, list):
            return self._data
        if hasattr(self._data, "model_dump"):
            return self._data.model_dump()
        return self._data

class DirectTestClient:
    def __init__(self, db):
        self.db = db

    def post(self, url: str, json: Optional[Dict[str, Any]] = None, files: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> MockResponse:
        bg = BackgroundTasks()
        params = params or {}
        try:
            # 1. /api/projects
            if url == "/api/projects":
                p_in = ProjectCreate(**(json or {}))
                res = create_project_with_job(p_in, bg, self.db)
                return MockResponse(201, res.model_dump())

            # 2. /api/upload
            elif url == "/api/upload":
                # Mock upload file
                class MockUploadFile:
                    def __init__(self, filename, file_obj, content_type):
                        self.filename = filename
                        self.file = file_obj
                        self.content_type = content_type

                file_tuple = (files or {}).get("file", ("video.mp4", None, "video/mp4"))
                upload_obj = MockUploadFile(file_tuple[0], file_tuple[1], file_tuple[2])
                name = (data or {}).get("name")
                res = upload_video_file(bg, upload_obj, name, self.db)
                return MockResponse(200, res)

            # 3. /api/jobs/{id}/retry
            elif "/retry" in url:
                job_id = url.split("/api/jobs/")[1].split("/retry")[0]
                res = retry_job(job_id, self.db)
                return MockResponse(200, res)

            # 4. /api/jobs/{id}/cancel
            elif "/cancel" in url:
                job_id = url.split("/api/jobs/")[1].split("/cancel")[0]
                res = cancel_job(job_id, self.db)
                return MockResponse(200, res)

            # 5. /api/jobs/{id}/pause
            elif "/pause" in url:
                job_id = url.split("/api/jobs/")[1].split("/pause")[0]
                res = pause_job(job_id, self.db)
                return MockResponse(200, res)

            # 6. /api/jobs/{id}/resume
            elif "/resume" in url:
                job_id = url.split("/api/jobs/")[1].split("/resume")[0]
                res = resume_job(job_id, self.db)
                return MockResponse(200, res)

            # 7. /api/worker/claim
            elif url == "/api/worker/claim":
                req = WorkerClaimRequest(**(json or {}))
                res = claim_job(req, bg, self.db)
                return MockResponse(200, res)

            # 8. /api/worker/heartbeat
            elif url == "/api/worker/heartbeat":
                req = WorkerHeartbeatRequest(**(json or {}))
                res = worker_heartbeat(req, self.db)
                return MockResponse(200, res)

            # 9. /api/worker/jobs/{id}/progress
            elif "/progress" in url:
                job_id = url.split("/api/worker/jobs/")[1].split("/progress")[0]
                up = JobProgressUpdate(**(json or {}))
                res = update_job_progress(job_id, up, self.db)
                return MockResponse(200, res)

            # 10. /api/worker/jobs/{id}/chunks/{idx}/checkpoint
            elif "/checkpoint" in url:
                parts = url.split("/api/worker/jobs/")[1].split("/chunks/")
                job_id = parts[0]
                chunk_index = int(parts[1].split("/checkpoint")[0])
                req = ChunkCheckpointRequest(**(json or {}))
                res = save_chunk_checkpoint(job_id, chunk_index, req, self.db)
                return MockResponse(200, res)

            # 11. /api/worker/jobs/{id}/clips
            elif "/clips" in url:
                job_id = url.split("/api/worker/jobs/")[1].split("/clips")[0]
                clip_in = ClipCreate(**(json or {}))
                res = register_clip(job_id, clip_in, self.db)
                return MockResponse(200, res.model_dump())

            # 12. /api/worker/jobs/{id}/complete
            elif "/complete" in url:
                job_id = url.split("/api/worker/jobs/")[1].split("/complete")[0]
                worker_id = params.get("worker_id", "")
                res = complete_job(job_id, bg, worker_id, self.db)
                return MockResponse(200, res)

            # 13. /api/worker/jobs/{id}/fail
            elif "/fail" in url:
                job_id = url.split("/api/worker/jobs/")[1].split("/fail")[0]
                error = params.get("error", "Error")
                worker_id = params.get("worker_id")
                res = fail_job(job_id, bg, error, worker_id, self.db)
                return MockResponse(200, res)

            return MockResponse(404, {"detail": "Endpoint not found"})

        except HTTPException as he:
            return MockResponse(he.status_code, {"detail": he.detail})
        except Exception as e:
            return MockResponse(500, {"detail": str(e)})

    def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> MockResponse:
        params = params or {}
        try:
            if url == "/api/jobs":
                status = params.get("status")
                limit = int(params.get("limit", 50))
                offset = int(params.get("offset", 0))
                res = list_jobs(status=status, limit=limit, offset=offset, db=self.db)
                return MockResponse(200, [r.model_dump() for r in res])

            elif url.startswith("/api/jobs/") and "/logs" in url:
                job_id = url.split("/api/jobs/")[1].split("/logs")[0]
                res = get_job_logs(job_id, self.db)
                return MockResponse(200, [r.model_dump() for r in res])

            elif url.startswith("/api/jobs/") and "/download-all" in url:
                job_id = url.split("/api/jobs/")[1].split("/download-all")[0]
                resp = download_all_clips(job_id, self.db)
                return MockResponse(200, content=resp.body, headers={"content-type": "application/zip"})

            elif url.startswith("/api/jobs/"):
                job_id = url.split("/api/jobs/")[1]
                res = get_job_details(job_id, self.db)
                return MockResponse(200, res.model_dump())

            elif url == "/api/status":
                res = get_system_status(self.db)
                return MockResponse(200, res.model_dump())

            elif url.startswith("/api/clips/") and "/download" in url:
                clip_id = url.split("/api/clips/")[1].split("/download")[0]
                resp = download_clip(clip_id, self.db)
                # FileResponse
                with open(resp.path, "rb") as f:
                    content = f.read()
                return MockResponse(200, content=content, headers={"content-type": "video/mp4"})

            return MockResponse(404, {"detail": "Not found"})
        except HTTPException as he:
            return MockResponse(he.status_code, {"detail": he.detail})
        except Exception as e:
            return MockResponse(500, {"detail": str(e)})

    def delete(self, url: str) -> MockResponse:
        try:
            if url.startswith("/api/jobs/"):
                job_id = url.split("/api/jobs/")[1]
                res = delete_job(job_id, self.db)
                return MockResponse(200, res)
            return MockResponse(404, {"detail": "Not found"})
        except HTTPException as he:
            return MockResponse(he.status_code, {"detail": he.detail})
        except Exception as e:
            return MockResponse(500, {"detail": str(e)})
