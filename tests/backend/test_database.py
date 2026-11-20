import pytest
from backend.models import User, Project, Job, JobChunk, Clip, ProcessingLog, WorkerHeartbeat

def test_database_schema_and_models(db_session):
    # 1. Create Project and Job
    project = Project(
        name="Test Podcast",
        source_type="youtube",
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )
    db_session.add(project)
    db_session.flush()

    job = Job(
        project_id=project.id,
        status="QUEUED",
        current_stage="QUEUED",
        total_chunks=3
    )
    db_session.add(job)
    db_session.flush()

    # 2. Add Chunks
    chunk1 = JobChunk(
        job_id=job.id,
        chunk_index=0,
        start_time=0.0,
        end_time=120.0,
        status="COMPLETED",
        checkpoint_data={"clips_count": 2}
    )
    db_session.add(chunk1)
    db_session.flush()

    # 3. Add Clip
    clip = Clip(
        job_id=job.id,
        chunk_id=chunk1.id,
        title="Viral Insight Moment",
        start_time=15.0,
        end_time=38.0,
        duration=23.0,
        score=88.5,
        transcript_snippet="This is the greatest secret",
        file_path="/storage/clips/test_clip.mp4"
    )
    db_session.add(clip)
    db_session.commit()

    # Query back
    retrieved_job = db_session.query(Job).filter(Job.id == job.id).first()
    assert retrieved_job is not None
    assert retrieved_job.project_id == project.id
    assert retrieved_job.status == "QUEUED"
    assert len(retrieved_job.chunks) == 1
    assert retrieved_job.chunks[0].chunk_index == 0
    assert len(retrieved_job.clips) == 1
    assert retrieved_job.clips[0].title == "Viral Insight Moment"
