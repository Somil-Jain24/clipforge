# ClipForge AI — Architecture & System Design

## 1. System Overview

ClipForge AI is a distributed, resilient, zero-cost video clipping platform designed to transform long-form YouTube videos or uploaded video files into viral, high-quality 9:16 vertical short clips (for TikTok, YouTube Shorts, Instagram Reels) with styled captions, blurred background padding, and word-level highlighting.

The system is engineered specifically for a **strictly ₹0 budget**, using resilient decoupled architecture to bridge free-tier ephemeral compute (such as Google Colab Free GPU or home desktop) with persistent free cloud storage and databases.

```
┌─────────────────────────┐          ┌─────────────────────────────────────────┐
│     Client Browser      │          │       Google Colab / Local Worker       │
│  (React + Vite + TS)    │          │  (Faster-Whisper, yt-dlp, FFmpeg)       │
└────────────┬────────────┘          └────────────────────┬────────────────────┘
             │                                            │
             │ HTTPS / REST                               │ Heartbeat & Lease Claim
             ▼                                            ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       ClipForge Backend API (FastAPI)                        │
│               - Job Submission, Queue Manager, Lease Tracker                 │
│               - Checkpoint Validator & Telegram Notifier                     │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                      ┌────────────────┴────────────────┐
                      ▼                                 ▼
         ┌─────────────────────────┐       ┌─────────────────────────┐
         │  Supabase PostgreSQL    │       │  Storage (Google Drive  │
         │  Free Database Tier     │       │   or Local / S3 Free)   │
         │  (Queue, State, Logs)   │       │   (Videos, Checkpoints) │
         └─────────────────────────┘       └─────────────────────────┘
```

---

## 2. Free-Tier Service Matrix & Constraints

| Service | Role | Free Tier Quota / Limitations | Resilience Strategy |
| :--- | :--- | :--- | :--- |
| **Cloudflare Pages / GitHub Pages** | Frontend Dashboard | Unlimited bandwidth, 100% free static hosting | Pre-built static SPA bundle, client-side routing, environment variable injection at build |
| **Supabase Free Tier** | Job Metadata & Queue | 500 MB database, 50,000 monthly active users, direct Postgres access | Lean schema: only metadata and checkpoint references stored in Postgres. Heavy video data stored externally. |
| **Google Drive** | Media & Model Storage | 15 GB free storage per Google Account | Structured folder hierarchy (`MyDrive/ClipForge/...`), chunked streaming, cleanup routines |
| **Google Colab Free** | Compute / GPU Worker | ~12 hours runtime, idle timeouts, ephemeral disk, potential random preemption | **Resumable Chunks & Checkpointing**: Colab runtime loss never corrupts jobs. Resumes at the exact incomplete chunk. |
| **Telegram Bot API** | Real-Time Notifications | Completely free, 30 msgs/second | Asynchronous notification service for job submission, start, progress, disconnect, failure, completion. |

---

## 3. Persistent Job Queue & Atomic Concurrency Safety

### 3.1 Job States
```
           ┌──────────┐
           │  QUEUED  │◄─────────────────────┐
           └────┬─────┘                      │ (Lease Timeout Recovery / Retry)
                │ (Atomic Claim)             │
                ▼                            │
         ┌─────────────┐                     │
         │ DOWNLOADING │                     │
         └──────┬──────┘                     │
                ▼                            │
        ┌──────────────┐                     │
        │ TRANSCRIBING │─────────────────────┤
        └──────┬───────┘                     │
                ▼                            │
         ┌────────────┐                      │
         │ ANALYZING  │─────────────────────┤
         └─────┬──────┘                      │
                ▼                            │
         ┌───────────┐                       │
         │ RENDERING │───────────────────────┘
         └─────┬─────┘
               │
        ┌──────┴──────┐
        ▼             ▼
  ┌───────────┐ ┌───────────┐
  │ COMPLETED │ │  FAILED   │
  └───────────┘ └───────────┘
```

In addition to the forward pipeline, jobs can transition to:
- `PAUSED`: Temporarily paused by user or when worker disconnect is detected.
- `CANCELLED`: Aborted by user; remaining chunks and temporary files cleaned up.

### 3.2 Atomic Job Claiming Algorithm
To prevent two workers from racing or processing the same job:
1. Standard PostgreSQL: Uses `FOR UPDATE SKIP LOCKED`:
   ```sql
   UPDATE jobs
   SET status = 'DOWNLOADING',
       worker_id = :worker_id,
       lease_expires_at = :now + :lease_duration_sec,
       updated_at = :now
   WHERE id = (
       SELECT id FROM jobs
       WHERE status = 'QUEUED'
          OR (status IN ('DOWNLOADING', 'TRANSCRIBING', 'ANALYZING', 'RENDERING')
              AND lease_expires_at < :now
              AND retry_count < max_retries)
       ORDER BY created_at ASC
       LIMIT 1
       FOR UPDATE SKIP LOCKED
   )
   RETURNING *;
   ```
2. SQLite (Local / Offline Testing): Concurrency-safe atomic transaction using immediate lock and conditional state transition.

### 3.3 Worker Heartbeats & Lease Expiration
- Every active worker sends a heartbeat every **15 seconds**.
- The heartbeat updates `worker_heartbeats` table and extends `jobs.lease_expires_at = NOW() + 60s`.
- If a worker crashes or Colab disconnects, its lease expires after 60 seconds.
- The next available worker automatically claims the uncompleted job and resumes from the last completed chunk checkpoint.

---

## 4. Chunked Video Pipeline & Persistent Checkpoints

Long videos (e.g. 10m to 2h) are split into logical chunks (configurable, default: **120 seconds**).
Each chunk is processed through the following deterministic cycle:
1. **Audio Extraction & Transcription**: Faster-Whisper (FP16 on GPU, INT8 on CPU) produces word-level timestamps.
2. **Viral Candidate Detection**: Transcripts are scored using heuristic keyword analysis, pacing/density metrics, sentence completeness, and punchy hook detection.
3. **Clip Refinement**: Window boundaries are snapped to sentence and breath boundaries (target duration: 12-35s).
4. **9:16 Vertical Video Synthesis**:
   - Blurred background: Scaled and Gaussian-blurred 1080x1920 crop.
   - Foreground: Original aspect ratio video centered with subtle dropshadow.
   - Captions: High-contrast styled subtitles with karaoke-style active word highlighting and safe margin placement.
5. **Checkpoint Persistence**: The chunk status is recorded as `COMPLETED` in `job_chunks`, and rendered clips are written to persistent storage.
6. **Progress Update**: Progress percentage = `(completed_chunks / total_chunks) * 100`.

If a disconnection happens at chunk 4 of 10:
- Chunks 1, 2, and 3 are already saved and marked `COMPLETED`.
- On reconnect, Worker reads existing checkpoints, skips chunks 1-3, and resumes directly at chunk 4.

---

## 5. Security & Isolation

- **Zero Credentials in Git**: All tokens (`SUPABASE_KEY`, `TELEGRAM_BOT_TOKEN`, `WORKER_SECRET`) configured exclusively via environment variables or Colab secure user inputs.
- **Path Traversal Protection**: Uploaded files and storage keys sanitize all input filenames, restricting access strictly to designated project directories.
- **Signed/Controlled Downloads**: Downloads are served via authenticated or tokenized backend endpoints, avoiding public bucket indexing.
- **Input Validation**: Strict validation on YouTube URLs (regex check), uploaded file MIME types (`video/mp4`, `video/quicktime`, `video/x-matroska`, `video/webm`), and file size limits.
