-- ClipForge AI Initial Schema
-- Compatible with Supabase Free Tier (PostgreSQL 14+)

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Projects Table
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('youtube', 'upload')),
    source_url TEXT,
    source_file TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Jobs Table
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'QUEUED' CHECK (
        status IN ('QUEUED', 'DOWNLOADING', 'TRANSCRIBING', 'ANALYZING', 'RENDERING', 'COMPLETED', 'FAILED', 'CANCELLED', 'PAUSED')
    ),
    current_stage TEXT NOT NULL DEFAULT 'QUEUED',
    progress REAL NOT NULL DEFAULT 0.0,
    total_chunks INT NOT NULL DEFAULT 0,
    completed_chunks INT NOT NULL DEFAULT 0,
    worker_id TEXT,
    lease_expires_at TIMESTAMPTZ,
    retry_count INT NOT NULL DEFAULT 0,
    max_retries INT NOT NULL DEFAULT 3,
    error_details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient queue polling and worker lease checks
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_lease ON jobs(lease_expires_at);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);

-- 4. Job Chunks Table (for persistent checkpoints and granular recovery)
CREATE TABLE IF NOT EXISTS job_chunks (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (
        status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')
    ),
    checkpoint_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_job_chunk_index UNIQUE (job_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_job_chunks_status ON job_chunks(job_id, status);

-- 5. Clips Table (generated vertical shorts)
CREATE TABLE IF NOT EXISTS clips (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    chunk_id TEXT REFERENCES job_chunks(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    duration REAL NOT NULL,
    score REAL NOT NULL DEFAULT 0.0,
    transcript_snippet TEXT,
    file_path TEXT NOT NULL,
    file_size BIGINT NOT NULL DEFAULT 0,
    aspect_ratio TEXT NOT NULL DEFAULT '9:16',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clips_job ON clips(job_id);

-- 6. Processing Logs Table
CREATE TABLE IF NOT EXISTS processing_logs (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    worker_id TEXT,
    level TEXT NOT NULL DEFAULT 'INFO' CHECK (level IN ('INFO', 'WARNING', 'ERROR')),
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_logs_job ON processing_logs(job_id, created_at);

-- 7. Worker Heartbeats Table
CREATE TABLE IF NOT EXISTS worker_heartbeats (
    worker_id TEXT PRIMARY KEY,
    hostname TEXT,
    device_type TEXT NOT NULL DEFAULT 'cpu',
    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    current_job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'ONLINE' CHECK (status IN ('ONLINE', 'BUSY', 'OFFLINE'))
);

CREATE INDEX IF NOT EXISTS idx_worker_heartbeats ON worker_heartbeats(last_heartbeat);
