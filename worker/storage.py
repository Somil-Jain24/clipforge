import os
import shutil
import hashlib
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class StorageManager:
    """
    Unified storage manager supporting both local filesystem and Google Drive paths.
    In Google Colab, when Google Drive is mounted, it points to /content/drive/MyDrive/ClipForge.
    """
    def __init__(self, base_dir: Optional[str] = None):
        colab_drive_path = "/content/drive/MyDrive/ClipForge"
        if os.path.exists("/content/drive/MyDrive") or os.path.exists(colab_drive_path):
            self.base_dir = colab_drive_path
            self.storage_type = "google_drive"
            logger.info(f"Using Google Drive persistent storage at: {self.base_dir}")
        else:
            self.base_dir = base_dir or os.path.abspath("./storage")
            self.storage_type = "local"
            logger.info(f"Using local filesystem storage at: {self.base_dir}")

        self.videos_dir = os.path.join(self.base_dir, "videos")
        self.clips_dir = os.path.join(self.base_dir, "clips")
        self.checkpoints_dir = os.path.join(self.base_dir, "checkpoints")
        self.models_dir = os.path.join(self.base_dir, "models")
        self.logs_dir = os.path.join(self.base_dir, "logs")

        for d in [self.videos_dir, self.clips_dir, self.checkpoints_dir, self.models_dir, self.logs_dir]:
            os.makedirs(d, exist_ok=True)

    def get_clip_path(self, job_id: str, clip_index: int, title: str) -> str:
        safe_title = "".join(c for c in title if c.isalnum() or c in ("-", "_")).rstrip()
        job_clip_dir = os.path.join(self.clips_dir, job_id)
        os.makedirs(job_clip_dir, exist_ok=True)
        return os.path.join(job_clip_dir, f"clip_{clip_index:02d}_{safe_title}.mp4")

    def get_chunk_dir(self, job_id: str) -> str:
        chunk_dir = os.path.join(self.checkpoints_dir, job_id)
        os.makedirs(chunk_dir, exist_ok=True)
        return chunk_dir

    def calculate_sha256(self, file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

    def verify_file(self, file_path: str, min_bytes: int = 1024) -> bool:
        if not os.path.exists(file_path):
            return False
        return os.path.getsize(file_path) >= min_bytes
