import pytest
from datetime import datetime, timedelta
from backend.models import Job, JobChunk

def test_atomic_claim_and_duplicate_prevention(test_client):
    # Enqueue job
    res = test_client.post(
        "/api/projects",
        json={
            "name": "Concurrency Project",
            "source_type": "youtube",
            "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }
    )
    job_id = res.json()["id"]

    # Worker 1 claims job
    claim1 = test_client.post(
        "/api/worker/claim",
        json={"worker_id": "colab-worker-1", "device_type": "cuda"}
    )
    assert claim1.status_code == 200
    claim1_data = claim1.json()
    assert claim1_data["status"] == "claimed"
    assert claim1_data["job_id"] == job_id

    # Worker 2 tries to claim at the same time: must receive empty!
    claim2 = test_client.post(
        "/api/worker/claim",
        json={"worker_id": "colab-worker-2", "device_type": "cpu"}
    )
    assert claim2.status_code == 200
    assert claim2.json()["status"] == "empty"

def test_worker_heartbeat_lease_extension(test_client, db_session):
    res = test_client.post(
        "/api/projects",
        json={"name": "HB Test", "source_type": "youtube", "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    )
    job_id = res.json()["id"]

    claim = test_client.post(
        "/api/worker/claim",
        json={"worker_id": "worker-hb", "device_type": "cuda"}
    )
    assert claim.json()["status"] == "claimed"

    hb_res = test_client.post(
        "/api/worker/heartbeat",
        json={
            "worker_id": "worker-hb",
            "current_job_id": job_id,
            "status": "BUSY"
        }
    )
    assert hb_res.status_code == 200
    extended_lease = hb_res.json()["lease_extended_to"]
    assert extended_lease is not None

def test_lease_expiration_and_recovery(test_client, db_session):
    res = test_client.post(
        "/api/projects",
        json={"name": "Crash Recovery", "source_type": "youtube", "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    )
    job_id = res.json()["id"]

    claim1 = test_client.post(
        "/api/worker/claim",
        json={"worker_id": "crashed-worker", "device_type": "cuda"}
    )
    assert claim1.json()["status"] == "claimed"

    chunk_res = test_client.post(
        f"/api/worker/jobs/{job_id}/chunks/0/checkpoint",
        json={"chunk_index": 0, "status": "COMPLETED", "checkpoint_data": {"test": "data"}}
    )
    assert chunk_res.status_code == 200

    # Simulate lease expiration in database (worker disappeared for > 60s)
    expired_time = datetime.utcnow() - timedelta(seconds=120)
    job = db_session.query(Job).filter(Job.id == job_id).first()
    job.lease_expires_at = expired_time
    db_session.commit()

    # Worker 2 comes online: should reclaim the abandoned job and resume with completed_chunks = [0]!
    claim2 = test_client.post(
        "/api/worker/claim",
        json={"worker_id": "resumed-worker", "device_type": "cuda"}
    )
    assert claim2.status_code == 200
    claim2_data = claim2.json()
    assert claim2_data["status"] == "claimed"
    assert claim2_data["job_id"] == job_id
    assert 0 in claim2_data["completed_chunks"]
