import os
import sys
import time
import uuid
import socket
import logging
import threading
import signal
from typing import Optional, Dict, Any, List

import requests

from worker.ffmpeg_utils import (
    get_ffmpeg_path,
    probe_video,
    split_video_into_chunks,
    render_vertical_clip
)
from worker.downloader import VideoDownloader
from worker.transcriber import AudioTranscriber
from worker.analyzer import ViralMomentAnalyzer
from worker.storage import StorageManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("ClipForgeWorker")

class ClipForgeWorker:
    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        worker_id: Optional[str] = None,
        chunk_duration_sec: int = 120,
        whisper_model: str = "base"
    ):
        self.api_url = api_url.rstrip("/")
        self.worker_id = worker_id or f"worker_{socket.gethostname()}_{str(uuid.uuid4())[:8]}"
        self.chunk_duration_sec = chunk_duration_sec
        self.hostname = socket.gethostname()
        self.device_type = self._detect_device()
        
        self.storage = StorageManager()
        self.downloader = VideoDownloader(self.storage.videos_dir)
        self.transcriber = AudioTranscriber(model_size=whisper_model, device="auto")
        self.analyzer = ViralMomentAnalyzer(min_duration=12.0, max_duration=35.0)

        self.running = False
        self.current_job_id: Optional[str] = None
        self._heartbeat_thread: Optional[threading.Thread] = None

    def _detect_device(self) -> str:
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"

    def start(self, single_job_mode: bool = False):
        """
        Starts the worker processing loop.
        If single_job_mode is True, exits after processing one job (ideal for testing/one-shot).
        """
        self.running = True
        logger.info(f"Starting ClipForge Worker [{self.worker_id}] on device '{self.device_type}'")
        logger.info(f"Backend API URL: {self.api_url}")

        # Start background heartbeat daemon
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

        try:
            while self.running:
                claimed = self._claim_and_process_job()
                if single_job_mode:
                    break
                if not claimed:
                    time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Worker received interrupt signal. Shutting down gracefully...")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        logger.info("ClipForge Worker stopped.")

    def _heartbeat_loop(self):
        while self.running:
            try:
                payload = {
                    "worker_id": self.worker_id,
                    "hostname": self.hostname,
                    "device_type": self.device_type,
                    "current_job_id": self.current_job_id,
                    "status": "BUSY" if self.current_job_id else "ONLINE"
                }
                requests.post(f"{self.api_url}/api/worker/heartbeat", json=payload, timeout=5)
            except Exception as e:
                logger.debug(f"Heartbeat ping failed: {e}")
            time.sleep(15)

    def _claim_and_process_job(self) -> bool:
        """
        Attempts to claim a job from the queue and executes the full clipping pipeline.
        """
        try:
            claim_payload = {
                "worker_id": self.worker_id,
                "hostname": self.hostname,
                "device_type": self.device_type
            }
            res = requests.post(f"{self.api_url}/api/worker/claim", json=claim_payload, timeout=10)
            if res.status_code != 200:
                logger.warning(f"Worker claim request returned HTTP {res.status_code}")
                return False

            data = res.json()
            if data.get("status") != "claimed":
                return False

            job_id = data["job_id"]
            self.current_job_id = job_id
            logger.info(f"Successfully claimed job: {job_id} ({data.get('project_name')})")

            self._execute_job(data)
            return True

        except Exception as e:
            logger.error(f"Error in claim/process loop: {e}", exc_info=True)
            return False
        finally:
            self.current_job_id = None

    def _log_to_backend(self, job_id: str, message: str, level: str = "INFO"):
        try:
            requests.post(
                f"{self.api_url}/api/worker/jobs/{job_id}/logs",
                json={"job_id": job_id, "worker_id": self.worker_id, "level": level, "message": message},
                timeout=5
            )
        except Exception:
            pass

    def _execute_job(self, job_info: Dict[str, Any]):
        job_id = job_info["job_id"]
        source_type = job_info.get("source_type")
        source_url = job_info.get("source_url")
        source_file = job_info.get("source_file")
        completed_chunks = set(job_info.get("completed_chunks", []))

        try:
            # 1. Download or retrieve source video
            self._update_progress(job_id, stage="DOWNLOADING", progress=5.0)
            self._log_to_backend(job_id, f"Acquiring video source ({source_type})...")

            if source_type == "youtube":
                video_data = self.downloader.download_youtube(source_url, job_id)
            else:
                video_data = self.downloader.prepare_uploaded_video(source_file, job_id)

            local_video_path = video_data["path"]
            duration = video_data["duration"]
            self._log_to_backend(job_id, f"Source video ready: {duration:.1f}s duration.")

            # 2. Split video into manageable chunks (default 120s)
            chunk_dir = self.storage.get_chunk_dir(job_id)
            chunks = split_video_into_chunks(local_video_path, self.chunk_duration_sec, chunk_dir)
            total_chunks = len(chunks)
            self._update_progress(job_id, stage="TRANSCRIBING", progress=15.0, total_chunks=total_chunks)
            self._log_to_backend(job_id, f"Video split into {total_chunks} chunks for resilient processing.")

            # 3. Process each chunk sequentially with persistent checkpoints
            generated_clips = []
            for chunk in chunks:
                idx = chunk["chunk_index"]

                # Checkpoint recovery: Skip chunk if already completed in prior run!
                if idx in completed_chunks:
                    logger.info(f"Skipping already completed chunk {idx + 1}/{total_chunks}")
                    self._log_to_backend(job_id, f"Resuming: Chunk {idx + 1}/{total_chunks} already completed. Skipping.")
                    continue

                self._log_to_backend(job_id, f"Processing chunk {idx + 1}/{total_chunks} [{chunk['start_time']:.1f}s - {chunk['end_time']:.1f}s]")
                
                # Transcribe chunk
                self._update_progress(job_id, stage="TRANSCRIBING", progress=round(15.0 + (idx / total_chunks) * 35.0, 1))
                segments = self.transcriber.transcribe(chunk["path"], chunk_offset=chunk["start_time"])

                # Analyze viral candidate moments
                self._update_progress(job_id, stage="ANALYZING")
                candidates = self.analyzer.analyze_segments(segments)
                self._log_to_backend(job_id, f"Chunk {idx + 1}: Found {len(candidates)} high-potential moments.")

                # Render vertical 9:16 clips for each candidate
                self._update_progress(job_id, stage="RENDERING")
                for c_idx, cand in enumerate(candidates, 1):
                    clip_path = self.storage.get_clip_path(job_id, len(generated_clips) + 1, cand["title"])
                    
                    render_vertical_clip(
                        source_video_path=local_video_path,
                        start_time=cand["start_time"],
                        duration=cand["duration"],
                        output_path=clip_path,
                        title=cand["title"]
                    )

                    # Register clip with backend
                    clip_payload = {
                        "job_id": job_id,
                        "title": cand["title"],
                        "start_time": cand["start_time"],
                        "end_time": cand["end_time"],
                        "duration": cand["duration"],
                        "score": cand["score"],
                        "transcript_snippet": cand["transcript_snippet"],
                        "file_path": clip_path,
                        "file_size": os.path.getsize(clip_path),
                        "aspect_ratio": "9:16"
                    }
                    requests.post(f"{self.api_url}/api/worker/jobs/{job_id}/clips", json=clip_payload, timeout=10)
                    generated_clips.append(clip_path)

                # Save persistent chunk checkpoint
                checkpoint_data = {
                    "start_time": chunk["start_time"],
                    "end_time": chunk["end_time"],
                    "candidates_count": len(candidates),
                    "clips_count": len(generated_clips)
                }
                requests.post(
                    f"{self.api_url}/api/worker/jobs/{job_id}/chunks/{idx}/checkpoint",
                    json={"chunk_index": idx, "status": "COMPLETED", "checkpoint_data": checkpoint_data},
                    timeout=10
                )
                completed_chunks.add(idx)
                current_pct = round((len(completed_chunks) / total_chunks) * 100.0, 1)
                self._update_progress(job_id, completed_chunks=len(completed_chunks), progress=min(99.0, current_pct))

            # 4. Final verification and complete job
            self._log_to_backend(job_id, f"All chunks finished! Generated {len(generated_clips)} vertical clips.")
            requests.post(
                f"{self.api_url}/api/worker/jobs/{job_id}/complete",
                params={"worker_id": self.worker_id},
                timeout=10
            )
            logger.info(f"Job {job_id} successfully COMPLETED.")

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            self._log_to_backend(job_id, f"Fatal processing error: {str(e)}", level="ERROR")
            requests.post(
                f"{self.api_url}/api/worker/jobs/{job_id}/fail",
                params={"error": str(e), "worker_id": self.worker_id},
                timeout=10
            )

    def _update_progress(
        self,
        job_id: str,
        stage: Optional[str] = None,
        progress: Optional[float] = None,
        total_chunks: Optional[int] = None,
        completed_chunks: Optional[int] = None
    ):
        try:
            payload = {}
            if stage:
                payload["current_stage"] = stage
            if progress is not None:
                payload["progress"] = progress
            if total_chunks is not None:
                payload["total_chunks"] = total_chunks
            if completed_chunks is not None:
                payload["completed_chunks"] = completed_chunks

            requests.post(f"{self.api_url}/api/worker/jobs/{job_id}/progress", json=payload, timeout=5)
        except Exception:
            pass

if __name__ == "__main__":
    api_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    worker = ClipForgeWorker(api_url=api_url)
    worker.start()
