import pytest
from backend.telegram import TelegramNotifier

def test_telegram_notifications_mocked(monkeypatch):
    sent_messages = []
    def mock_send(self, text, parse_mode="HTML"):
        sent_messages.append(text)
        return True

    monkeypatch.setattr(TelegramNotifier, "send_message", mock_send)
    notifier = TelegramNotifier(token="fake-token", chat_id="123456")

    # 1. Job Submitted
    notifier.notify_job_submitted("job-123", "Startup Interview", "https://youtube.com/...")
    assert len(sent_messages) == 1
    assert "New Job Queued" in sent_messages[-1]
    assert "Startup Interview" in sent_messages[-1]

    # 2. Processing Started
    notifier.notify_processing_started("job-123", "Startup Interview", "colab-worker", "cuda")
    assert len(sent_messages) == 2
    assert "Processing Started" in sent_messages[-1]
    assert "CUDA" in sent_messages[-1]

    # 3. Processing Resumed
    notifier.notify_processing_resumed("job-123", "Startup Interview", 2, 5)
    assert len(sent_messages) == 3
    assert "Processing Resumed" in sent_messages[-1]

    # 4. Processing Completed
    notifier.notify_processing_completed("job-123", "Startup Interview", 4, 185.0)
    assert len(sent_messages) == 4
    assert "Clips Ready for Download" in sent_messages[-1]
    assert "4 vertical (9:16) shorts" in sent_messages[-1]
    assert "3m 5s" in sent_messages[-1]

def test_telegram_unconfigured_graceful():
    notifier = TelegramNotifier(token=None, chat_id=None)
    assert not notifier.is_configured
    result = notifier.send_message("Test")
    assert result is False
