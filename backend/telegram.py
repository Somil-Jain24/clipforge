import logging
import requests
from typing import Optional
from backend.config import settings

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else None

    @property
    def is_configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Sends a message via Telegram Bot API synchronously.
        Silently returns False if unconfigured or on network failure, ensuring zero interruption.
        """
        if not self.is_configured:
            logger.debug("Telegram notifications skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured.")
            return False

        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": False
            }
            res = requests.post(url, json=payload, timeout=5.0)
            if res.status_code == 200:
                logger.info("Telegram notification sent successfully.")
                return True
            else:
                logger.warning(f"Telegram API returned status {res.status_code}: {res.text}")
                return False
        except Exception as e:
            logger.warning(f"Failed to send Telegram notification: {e}")
            return False

    def notify_job_submitted(self, job_id: str, project_name: str, source: str) -> bool:
        msg = (
            f"🎬 <b>ClipForge AI — New Job Queued</b>\n\n"
            f"<b>Project:</b> {project_name}\n"
            f"<b>Job ID:</b> <code>{job_id}</code>\n"
            f"<b>Source:</b> {source}\n"
            f"<b>Status:</b> ⏳ Waiting for available GPU/CPU worker\n\n"
            f"👉 <a href='{settings.DASHBOARD_URL}/jobs/{job_id}'>View Job Dashboard</a>"
        )
        return self.send_message(msg)

    def notify_processing_started(self, job_id: str, project_name: str, worker_id: str, device: str) -> bool:
        msg = (
            f"⚡ <b>ClipForge AI — Processing Started</b>\n\n"
            f"<b>Project:</b> {project_name}\n"
            f"<b>Job ID:</b> <code>{job_id}</code>\n"
            f"<b>Worker:</b> <code>{worker_id}</code> ({device.upper()})\n"
            f"<b>Current Stage:</b> 📥 Downloading & Transcribing\n\n"
            f"👉 <a href='{settings.DASHBOARD_URL}/jobs/{job_id}'>Monitor Progress</a>"
        )
        return self.send_message(msg)

    def notify_processing_resumed(self, job_id: str, project_name: str, chunk_index: int, total_chunks: int) -> bool:
        msg = (
            f"🔄 <b>ClipForge AI — Processing Resumed</b>\n\n"
            f"<b>Project:</b> {project_name}\n"
            f"<b>Job ID:</b> <code>{job_id}</code>\n"
            f"<b>Resumed at Chunk:</b> {chunk_index + 1} / {total_chunks}\n"
            f"<b>Note:</b> Checkpoints preserved. Skipping already generated clips.\n\n"
            f"👉 <a href='{settings.DASHBOARD_URL}/jobs/{job_id}'>Monitor Progress</a>"
        )
        return self.send_message(msg)

    def notify_worker_disconnected(self, job_id: str, project_name: str, last_chunk: int, total_chunks: int) -> bool:
        msg = (
            f"⚠️ <b>ClipForge AI — Worker Disconnected</b>\n\n"
            f"<b>Project:</b> {project_name}\n"
            f"<b>Job ID:</b> <code>{job_id}</code>\n"
            f"<b>Progress:</b> Chunk {last_chunk} / {total_chunks} completed.\n"
            f"<b>State:</b> Paused & preserved safely in database.\n"
            f"<b>Action:</b> Reconnect or restart your Colab worker to resume without lost data.\n\n"
            f"👉 <a href='{settings.DASHBOARD_URL}/jobs/{job_id}'>Job Status</a>"
        )
        return self.send_message(msg)

    def notify_processing_failed(self, job_id: str, project_name: str, error: str) -> bool:
        msg = (
            f"❌ <b>ClipForge AI — Processing Failed</b>\n\n"
            f"<b>Project:</b> {project_name}\n"
            f"<b>Job ID:</b> <code>{job_id}</code>\n"
            f"<b>Error Details:</b> <code>{error[:300]}</code>\n\n"
            f"👉 <a href='{settings.DASHBOARD_URL}/jobs/{job_id}'>Inspect & Retry</a>"
        )
        return self.send_message(msg)

    def notify_processing_completed(
        self,
        job_id: str,
        project_name: str,
        clips_count: int,
        duration_sec: Optional[float] = None
    ) -> bool:
        duration_str = f"{int(duration_sec // 60)}m {int(duration_sec % 60)}s" if duration_sec else "N/A"
        msg = (
            f"🎉 <b>ClipForge AI — Clips Ready for Download!</b>\n\n"
            f"<b>Project:</b> {project_name}\n"
            f"<b>Job ID:</b> <code>{job_id}</code>\n"
            f"<b>Generated Clips:</b> {clips_count} vertical (9:16) shorts\n"
            f"<b>Processing Time:</b> {duration_str}\n\n"
            f"📥 <a href='{settings.DASHBOARD_URL}/jobs/{job_id}'>Download Finished Clips Now</a>"
        )
        return self.send_message(msg)

telegram_notifier = TelegramNotifier()
