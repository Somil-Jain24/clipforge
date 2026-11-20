# ClipForge AI — Automated Distributed Video Clipping Platform

ClipForge AI is an automated, distributed video clipping platform designed to transform long-form YouTube videos or direct video uploads into vertical (9:16) viral shorts, reels, and clips with blurred background framing and styled captions.

Engineered with a **strict ₹0 budget architecture**, ClipForge AI runs completely on free-tier services and open-source infrastructure without requiring paid APIs, credit cards, or trial subscriptions.

---

## 🌟 Key Features

- **Distributed, Resumable Architecture:** Decoupled web dashboard, centralized job queue, and on-demand GPU/CPU workers.
- **₹0 Operating Cost:** Uses Supabase Free Tier, Google Colab Free T4 GPU, Google Drive free storage, and Telegram Bot API.
- **Atomic Job Claiming:** Robust transactional job queue prevents duplicate chunk processing across multiple workers.
- **Worker Heartbeats & Lease Recovery:** Dead or disconnected workers automatically surrender expired leases for recovery without losing progress.
- **Chunk-Based Checkpointing:** Long videos are split into configurable chunks (default: 120s); progress and generated clips persist after every chunk.
- **Vertical 9:16 FFmpeg Pipeline:** Automatically centers foreground content over a blurred 1080×1920 background canvas with bold ASS subtitle rendering.
- **Heuristic Transcript Analysis:** Evaluates speech patterns, question density, superlatives, and pace to extract candidate highlights (12–35 seconds).
- **Instant Telegram Notifications:** Dispatches real-time alerts on job submission, processing stages, completion with download links, or worker disconnects.
- **Zero-Friction UI:** Responsive React + Vite + Tailwind CSS dashboard with preview player, chunk progress bars, and batch ZIP download.

---

## 🏗️ Architecture Overview

```
                      +---------------------------------------+
                      |           Frontend Dashboard          |
                      |   (React / TypeScript / Tailwind)     |
                      |   Hosted on Cloudflare / GH Pages     |
                      +-------------------+-------------------+
                                          |
                                    REST API / Poll
                                          v
                      +---------------------------------------+
                      |            FastAPI Backend            |
                      |  - Job submission & management        |
                      |  - Atomic leasing & heartbeats        |
                      |  - Telegram notification dispatcher   |
                      +-------------------+-------------------+
                                          |
                        +-----------------+-----------------+
                        |                                   |
                        v                                   v
          +---------------------------+       +---------------------------+
          |   Supabase PostgreSQL     |       |   Telegram Bot API        |
          |  (Free 500MB Database)    |       |  (Free alerts & links)    |
          +---------------------------+       +---------------------------+
                        ^
                        | REST / Poll & Heartbeat
                        v
          +---------------------------------------------------------------+
          |                     Processing Worker                         |
          |       (Google Colab Free GPU or Local Background Worker)      |
          |                                                               |
          |  1. Atomic Claim -> Lease Heartbeat Thread                   |
          |  2. Download Video (yt-dlp or upload stream)                  |
          |  3. Chunking (120s segments) & Faster-Whisper Transcription   |
          |  4. Transcript Heuristic Highlight Detection                  |
          |  5. 9:16 1080x1920 FFmpeg Render + Styled Captions            |
          |  6. Checkpoint Persistence -> Next Chunk / Complete           |
          +-------------------------------+-------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |           Persistent Media            |
                      |   (Google Drive in Colab / Local FS)  |
                      +---------------------------------------+
```

---

## 💰 Strict ₹0 Budget Service Matrix

| Component | Service | Free Tier Allowance | Purpose |
|---|---|---|---|
| **Database & Metadata** | **Supabase** | 500 MB PostgreSQL, 2 free projects, 50,000 monthly active users | Relational schema, atomic job locking, heartbeats |
| **Frontend Hosting** | **Cloudflare Pages** or **GitHub Pages** | Unlimited free bandwidth, custom domains, automated CI/CD | Production static hosting for React single-page app |
| **Compute / GPU Worker** | **Google Colab Free** | NVIDIA T4 GPU (~15 GB VRAM) on demand | Faster-Whisper FP16 inference, FFmpeg encoding |
| **Media & Checkpoints** | **Google Drive** | 15 GB free storage per Google Account | Persistent storage for raw videos, chunks, and rendered clips |
| **Alerts & Links** | **Telegram Bot API** | 100% free, unlimited messages | Instant job progress, failure alerts, and direct download links |

---

## 🚀 Quickstart: Local Development

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- FFmpeg (automatically detected if installed system-wide, or bundled via `imageio-ffmpeg`)

### 1. Clone & Setup Environment
```bash
git clone https://github.com/Somil-Jain24/clipforge.git
cd clipforge
```

**Windows:**
```powershell
.\scripts\setup_dev.bat
```

**Linux / macOS:**
```bash
chmod +x scripts/setup_dev.sh
./scripts/setup_dev.sh
```

### 2. Configure Settings
Copy `.env.example` to `.env` and configure your credentials:
```env
DATABASE_URL=sqlite:///./clipforge.db
WORKER_SECRET=clipforge-local-dev-secret-key-replace-in-prod
STORAGE_DIR=./storage
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

### 3. Run Application
Run the three components in separate terminal windows:

- **Backend API:**
  ```bash
  # Windows
  .\.venv\Scripts\activate
  uvicorn backend.main:app --reload --port 8000
  
  # Linux/macOS
  source .venv/bin/activate
  uvicorn backend.main:app --reload --port 8000
  ```

- **Background Worker:**
  ```bash
  # Windows
  .\.venv\Scripts\activate
  python -m worker.runner --mode poll
  
  # Linux/macOS
  source .venv/bin/activate
  python -m worker.runner --mode poll
  ```

- **Frontend Dashboard:**
  ```bash
  cd frontend
  npm run dev
  ```
  Open `http://localhost:5173` in your browser.

---

## ☁️ Production Setup: Supabase & Colab Free

### 1. Supabase PostgreSQL Setup
1. Create a free account at [supabase.com](https://supabase.com).
2. Create a new free project.
3. In the Supabase Dashboard, open the **SQL Editor**.
4. Paste and execute the contents of `database/migrations/001_initial_schema.sql`.
5. Navigate to **Project Settings -> Database -> Connection string -> URI** (Transaction Pooler).
6. Copy the connection string into your backend `.env`:
   ```env
   DATABASE_URL=postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require
   ```

### 2. Telegram Notifications Setup
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot`, name your bot (e.g., `MyClipForgeBot`), and receive your `TELEGRAM_BOT_TOKEN`.
3. Start a conversation with your bot by clicking `/start`.
4. Message `@userinfobot` to get your numeric `TELEGRAM_CHAT_ID`.
5. Enter both values in `.env`.

### 3. Google Colab GPU Worker (`ClipForge_Worker.ipynb`)
1. Open [Google Colab](https://colab.research.google.com).
2. Open `notebooks/ClipForge_Worker.ipynb` directly from your GitHub repo under the **GitHub** tab (`Somil-Jain24/clipforge`) or upload it.
3. In the Colab menu, select **Runtime -> Change runtime type -> T4 GPU**.
4. In Cell 2 (Configuration), set:
   - `API_URL`: Public URL of your backend (e.g. deployed on Render or exposed via ngrok/localtunnel/cloudflared).
   - `GITHUB_REPO_URL`: `https://github.com/Somil-Jain24/clipforge.git` (pre-configured).
   - `WORKER_NAME`: `colab-gpu-worker-1`.
5. Execute **Cell 1: Environment Setup & Google Drive Mount**.
6. Execute **Cell 2: Start Resilient Worker Loop**.
   - Colab automatically clones `https://github.com/Somil-Jain24/clipforge.git` and runs the worker.
   - Colab will continuously poll your backend for queued jobs.
   - When finished or disconnected, all clips and chunk checkpoints remain saved in `MyDrive/ClipForge/`.

---

## 🔄 Automatic Recovery & Fault Tolerance

If a Google Colab session expires or disconnects during video processing:
1. **Heartbeat Expiration:** The worker sends heartbeats every 30 seconds. If a worker fails to send a heartbeat within `WORKER_LEASE_SECONDS` (default: 120s), its lease automatically expires.
2. **Safe Recovery:** The backend resets the job status from `PROCESSING` to `QUEUED` without deleting existing chunks.
3. **Resumed Execution:** When Colab or another worker reconnects and claims the job:
   - It reads `job_chunks` from the database.
   - It skips already completed chunks.
   - It picks up at the first uncompleted chunk and merges generated clips.
4. **Zero Duplicate Work:** Generated clips for completed chunks are permanently preserved in storage.

---

## 🧪 Automated Test Suite

The project includes an end-to-end automated test suite covering database transactions, concurrency, Telegram notifications, FFmpeg rendering, and worker recovery:

```bash
# Run entire test suite
.\.venv\Scripts\pytest.exe -v
```

### Verified Test Modules:
- `tests/backend/test_database.py`: Schema validation, foreign keys, cascade rules.
- `tests/backend/test_api_jobs.py`: YouTube URL submission, direct upload, lifecycle transitions.
- `tests/backend/test_queue_concurrency.py`: Atomic job claiming, double-claim prevention, lease expiration.
- `tests/backend/test_telegram.py`: Notification dispatch with mocked Telegram Bot API.
- `tests/worker/test_analyzer.py`: Transcript heuristic highlight scoring and boundary constraints.
- `tests/worker/test_ffmpeg_pipeline.py`: Synthetic video generation, 9:16 vertical render, blurred background, subtitle burning.
- `tests/worker/test_recovery_and_resume.py`: Simulated mid-processing disconnect, resume, checkpoint reuse, ZIP download.

---

## 📁 Repository Structure

```
clipping/
├── backend/                  # FastAPI Application
│   ├── config.py             # App settings & environment resolution
│   ├── database.py           # SQLAlchemy engine & session factory
│   ├── main.py               # REST API endpoints & lifecycle
│   ├── models.py             # PostgreSQL / SQLite relational models
│   ├── schemas.py            # Pydantic schemas & request validation
│   └── telegram.py           # Telegram Bot notification client
├── database/
│   └── migrations/
│       └── 001_initial_schema.sql # Supabase PostgreSQL migration DDL
├── docs/
│   └── ARCHITECTURE.md       # Deep architectural design & quota guide
├── frontend/                 # Vite + React + TypeScript Dashboard
│   ├── src/
│   │   ├── components/       # Modals, Cards, Header, Player, Status
│   │   ├── api.ts            # Typed Axios backend API client
│   │   ├── types.ts          # Frontend data contracts
│   │   └── App.tsx           # Dashboard view with live polling
│   └── package.json
├── notebooks/
│   └── ClipForge_Worker.ipynb # Google Colab GPU Worker notebook
├── scripts/
│   ├── setup_dev.bat         # Automated setup for Windows
│   └── setup_dev.sh          # Automated setup for Linux/macOS
├── tests/                    # Pytest test suite
│   ├── backend/
│   └── worker/
├── worker/                   # Processing Pipeline & Colab Worker
│   ├── analyzer.py           # Transcript heuristic scoring
│   ├── downloader.py         # yt-dlp downloader with fallback
│   ├── ffmpeg_utils.py       # 9:16 vertical renderer & subtitle burning
│   ├── runner.py             # Resilient job claiming & chunk runner
│   ├── storage.py            # File persistence & chunk checkpointing
│   └── transcriber.py        # Faster-Whisper GPU/CPU wrapper
├── .env.example              # Sample environment template
├── .gitignore
├── pytest.ini
├── requirements.txt          # Python dependencies
└── README.md
```

---

## ⚠️ Known Limitations & Mitigations

1. **Google Colab Session Limits:** Free Colab instances disconnect after ~12 hours or brief inactivity.
   - *Mitigation:* Chunk checkpoints guarantee that re-running Cell 2 in Colab resumes instantly from the last completed chunk without re-transcribing or re-rendering completed segments.
2. **YouTube Bot Detection (yt-dlp):** YouTube occasionally throttles or rate-limits automated requests.
   - *Mitigation:* The dashboard supports **Direct Video Upload** (MP4, MOV, MKV, WEBM) as a zero-dependency fallback.
3. **Supabase Inactivity Pausing:** Supabase pauses free databases after 7 days of inactivity.
   - *Mitigation:* Simply clicking "Resume" in the Supabase console reactivates the database with all tables and data intact.
