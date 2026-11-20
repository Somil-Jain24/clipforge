import pytest
import io

def test_create_youtube_project(test_client):
    res = test_client.post(
        "/api/projects",
        json={
            "name": "Finance Masterclass",
            "source_type": "youtube",
            "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "QUEUED"
    assert data["project_name"] == "Finance Masterclass"
    assert "id" in data

def test_invalid_youtube_url_rejected(test_client):
    res = test_client.post(
        "/api/projects",
        json={
            "name": "Invalid Project",
            "source_type": "youtube",
            "source_url": "https://random-phishing-site.com/video"
        }
    )
    assert res.status_code == 400
    assert "Invalid YouTube URL" in res.json()["detail"]

def test_upload_video_file_lifecycle(test_client):
    fake_video_bytes = b"RIFF....AVI..FAKEVIDEO"
    files = {
        "file": ("podcast.mp4", io.BytesIO(fake_video_bytes), "video/mp4")
    }
    data = {"name": "Local Interview"}

    res = test_client.post("/api/upload", files=files, data=data)
    assert res.status_code == 200
    res_data = res.json()
    assert "job_id" in res_data
    job_id = res_data["job_id"]

    list_res = test_client.get(f"/api/jobs/{job_id}")
    assert list_res.status_code == 200
    assert list_res.json()["project_name"] == "Local Interview"

def test_upload_invalid_mime_type(test_client):
    files = {
        "file": ("malicious.exe", io.BytesIO(b"binary"), "application/x-msdownload")
    }
    res = test_client.post("/api/upload", files=files)
    assert res.status_code == 400
    assert "Unsupported media format" in res.json()["detail"]

def test_job_retry_cancel_pause_resume(test_client):
    create_res = test_client.post(
        "/api/projects",
        json={
            "name": "Lifecycle Test",
            "source_type": "youtube",
            "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }
    )
    job_id = create_res.json()["id"]

    # Pause
    pause_res = test_client.post(f"/api/jobs/{job_id}/pause")
    assert pause_res.status_code == 200
    detail = test_client.get(f"/api/jobs/{job_id}").json()
    assert detail["status"] == "PAUSED"

    # Resume
    resume_res = test_client.post(f"/api/jobs/{job_id}/resume")
    assert resume_res.status_code == 200
    detail = test_client.get(f"/api/jobs/{job_id}").json()
    assert detail["status"] == "QUEUED"

    # Cancel
    cancel_res = test_client.post(f"/api/jobs/{job_id}/cancel")
    assert cancel_res.status_code == 200
    detail = test_client.get(f"/api/jobs/{job_id}").json()
    assert detail["status"] == "CANCELLED"

    # Retry
    retry_res = test_client.post(f"/api/jobs/{job_id}/retry")
    assert retry_res.status_code == 200
    detail = test_client.get(f"/api/jobs/{job_id}").json()
    assert detail["status"] == "QUEUED"
    assert detail["retry_count"] == 1
