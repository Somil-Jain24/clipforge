import os
import pytest
from worker.runner import ClipForgeWorker
from worker.ffmpeg_utils import generate_synthetic_test_video, probe_video, render_vertical_clip

def test_full_pipeline_with_simulated_disconnect_and_resume(test_client, tmp_path):
    # 1. Create a synthetic video (6s duration for fast test execution)
    video_path = str(tmp_path / "full_synth_video.mp4")
    generate_synthetic_test_video(video_path, duration_sec=6)

    # 2. Upload video and create job
    with open(video_path, "rb") as f:
        upload_res = test_client.post(
            "/api/upload",
            files={"file": ("synth_podcast.mp4", f, "video/mp4")},
            data={"name": "Synthetic 2-Min Podcast"}
        )
    assert upload_res.status_code == 200
    job_id = upload_res.json()["job_id"]

    # 3. Step A: Worker claims job
    claim_res = test_client.post(
        "/api/worker/claim",
        json={"worker_id": "test-worker-1", "device_type": "cpu"}
    )
    assert claim_res.status_code == 200
    claim_data = claim_res.json()
    assert claim_data["job_id"] == job_id
    assert claim_data["completed_chunks"] == []

    # Step B: Worker processes Chunk 0
    test_client.post(
        f"/api/worker/jobs/{job_id}/progress",
        json={"current_stage": "TRANSCRIBING", "progress": 25.0, "total_chunks": 2}
    )

    # Register Clip from Chunk 0
    clip0_path = str(tmp_path / "clip_chunk_0.mp4")
    render_vertical_clip(video_path, start_time=0.5, duration=2.0, output_path=clip0_path, title="Hook from Chunk 1")

    test_client.post(
        f"/api/worker/jobs/{job_id}/clips",
        json={
            "job_id": job_id,
            "title": "Hook from Chunk 1",
            "start_time": 0.5,
            "end_time": 2.5,
            "duration": 2.0,
            "score": 85.0,
            "transcript_snippet": "This is the greatest secret",
            "file_path": clip0_path,
            "file_size": os.path.getsize(clip0_path),
            "aspect_ratio": "9:16"
        }
    )

    # Save Chunk 0 Checkpoint
    test_client.post(
        f"/api/worker/jobs/{job_id}/chunks/0/checkpoint",
        json={"chunk_index": 0, "status": "COMPLETED", "checkpoint_data": {"done": True}}
    )

    # Step C: SIMULATED CRASH / DISCONNECT
    job_state_after_crash = test_client.get(f"/api/jobs/{job_id}").json()
    assert job_state_after_crash["completed_chunks"] == 1
    assert len(job_state_after_crash["clips"]) == 1

    # Step D: RECONNECT & RESUME
    test_client.post(f"/api/jobs/{job_id}/resume")
    resume_claim = test_client.post(
        "/api/worker/claim",
        json={"worker_id": "test-worker-2", "device_type": "cpu"}
    )
    assert resume_claim.json()["status"] == "claimed"
    assert 0 in resume_claim.json()["completed_chunks"]

    # Step E: Worker skips Chunk 0 (deduplication!) and processes Chunk 1
    clip1_path = str(tmp_path / "clip_chunk_1.mp4")
    render_vertical_clip(video_path, start_time=3.0, duration=2.0, output_path=clip1_path, title="Hook from Chunk 2")

    test_client.post(
        f"/api/worker/jobs/{job_id}/clips",
        json={
            "job_id": job_id,
            "title": "Hook from Chunk 2",
            "start_time": 3.0,
            "end_time": 5.0,
            "duration": 2.0,
            "score": 92.0,
            "transcript_snippet": "Never make this fatal mistake",
            "file_path": clip1_path,
            "file_size": os.path.getsize(clip1_path),
            "aspect_ratio": "9:16"
        }
    )

    test_client.post(
        f"/api/worker/jobs/{job_id}/chunks/1/checkpoint",
        json={"chunk_index": 1, "status": "COMPLETED", "checkpoint_data": {"done": True}}
    )

    # Step F: Finalize Job
    complete_res = test_client.post(
        f"/api/worker/jobs/{job_id}/complete",
        params={"worker_id": "test-worker-2"}
    )
    assert complete_res.status_code == 200

    # Step G: Validate Final State & Outputs
    final_job = test_client.get(f"/api/jobs/{job_id}").json()
    assert final_job["status"] == "COMPLETED"
    assert final_job["progress"] == 100.0
    assert final_job["completed_chunks"] == 2
    assert len(final_job["clips"]) == 2

    # Step H: Test Download Endpoints
    clip_id = final_job["clips"][0]["id"]
    dl_res = test_client.get(f"/api/clips/{clip_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "video/mp4"

    # Test Download All (ZIP)
    zip_res = test_client.get(f"/api/jobs/{job_id}/download-all")
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"
    assert len(zip_res.content) > 100
