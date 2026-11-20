import os
import shutil
import logging
from typing import Dict, Any, Optional
import yt_dlp
from worker.ffmpeg_utils import probe_video, get_ffmpeg_path

logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self, download_dir: str):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    def download_youtube(self, url: str, job_id: str) -> Dict[str, Any]:
        """
        Downloads a YouTube video using yt-dlp with format fallback and error handling.
        Returns dict with file path, title, duration.
        """
        output_template = os.path.join(self.download_dir, f"{job_id}_source.%(ext)s")
        
        ffmpeg_bin = get_ffmpeg_path()
        ydl_opts = {
            # Prefer 1080p/720p H264 with AAC audio
            'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_template,
            'merge_output_format': 'mp4',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'ffmpeg_location': os.path.dirname(ffmpeg_bin) if os.path.exists(ffmpeg_bin) else None,
        }

        try:
            logger.info(f"Starting yt-dlp download for URL: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info)
                # Ensure .mp4 extension
                base, _ = os.path.splitext(downloaded_file)
                final_path = f"{base}.mp4"
                if not os.path.exists(final_path) and os.path.exists(downloaded_file):
                    final_path = downloaded_file

                probe = probe_video(final_path)
                return {
                    "path": final_path,
                    "title": info.get("title", "YouTube Video"),
                    "duration": probe["duration"],
                    "uploader": info.get("uploader", "Unknown"),
                    "file_size": os.path.getsize(final_path)
                }
        except Exception as e:
            logger.error(f"Failed to download YouTube video: {e}")
            raise RuntimeError(f"YouTube download failed: {str(e)}")

    def prepare_uploaded_video(self, source_path: str, job_id: str) -> Dict[str, Any]:
        """
        Validates and prepares a directly uploaded video file.
        """
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source video file not found at: {source_path}")

        probe = probe_video(source_path)
        if not probe["has_video"]:
            raise ValueError("Uploaded file does not contain a valid video stream.")

        return {
            "path": source_path,
            "title": os.path.basename(source_path),
            "duration": probe["duration"],
            "file_size": os.path.getsize(source_path)
        }
