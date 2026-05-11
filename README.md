<p align="center">
  <strong>🚀</strong>
</p>

<h1 align="center">SignalStack</h1>

<p align="center">
  <strong>AI-Powered Hiring Platform That Evaluates Talent by Proof of Work, Not Resumes</strong>
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#key-features">Features</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#getting-started">Getting Started</a> •
  <a href="#api-reference">API</a> •
  <a href="#project-structure">Structure</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/node-20+-339933?logo=node.js&logoColor=white" alt="Node 20+">
  <img src="https://img.shields.io/badge/FastAPI-0.128-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black" alt="React 18">
  <img src="https://img.shields.io/badge/OpenAI-gpt--5--mini-412991?logo=openai&logoColor=white" alt="OpenAI">
  <img src="https://img.shields.io/badge/license-proprietary-red" alt="License">
</p>

---

## Overview

SignalStack is an **AI-native recruiter platform** that transforms how companies evaluate engineering talent. Instead of parsing résumés and relying on keyword matching, SignalStack analyzes candidates' **actual code** from GitHub repositories, extracting measurable signals like language proficiency, framework usage, test coverage, CI/CD adoption, and commit authorship — then ranks candidates with AI-driven confidence scores.

### The Problem

Traditional hiring pipelines are fundamentally broken:

- **Résumé Inflation** — No way to verify if a candidate *actually* wrote the code they claim.
- **ATS Keyword Filtering** — Great engineers get rejected because their résumé doesn't match arbitrary keyword patterns.
- **Manual Signal Extraction** — Recruiters spend hours reviewing GitHub profiles with no structured methodology.
- **Gut-Feel Decisions** — Hiring decisions lack data backing, leading to inconsistent outcomes.

### How SignalStack Solves It

```
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │                          SIGNALSTACK PIPELINE                               │
 │                                                                             │
 │   Define         Decompose        Extract          Evaluate       Decide    │
 │   Outcome   ───► Tasks       ───► Signals     ───► Candidates ──► Shortlist │
 │                                                                             │
 │   "Build a       • Auth module    • Languages      • Fit score    • Ranked  │
 │    REST API       • DB layer       • Frameworks     • Evidence     • Accept/ │
 │    with auth"     • Testing        • Test coverage  • Authorship   • Reject  │
 │                   • Deployment     • CI/CD usage    • Confidence            │
 │                                                                             │
 │                  AI-Powered                    Feedback Loop                 │
 │                  (OpenAI gpt-4o-mini)          (Learns from decisions)       │
 └──────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Features

### 🎯 Outcome-Based Hiring

| Feature | Description |
|---------|-------------|
| **Outcome Definitions** | Define what you need accomplished — not just a job title |
| **AI Task Decomposition** | Automatically breaks outcomes into measurable, evaluable sub-tasks |
| **Template Library** | Pre-built outcome templates for common engineering roles |
| **Multi-Outcome Jobs** | Attach multiple outcome definitions to a single job posting |

### 🔬 Signal Extraction Pipeline

| Feature | Description |
|---------|-------------|
| **GitHub Repo Analysis** | Deep analysis of repository structure, languages, and patterns |
| **Deterministic Signals** | Rule-based extraction of languages, frameworks, test coverage, CI/CD indicators |
| **AI-Enhanced Signals** | LLM-powered assessment of code quality, architecture patterns, and complexity |
| **Authorship Forensics** | Git commit analysis and identity verification to confirm who wrote the code |
| **Cost Guard** | Budget-aware pipeline that controls LLM token spend per evaluation |
| **Noise Filtering** | Automatically excludes config files, lock files, and non-signal artifacts |

### 📊 Evaluation & Scoring

| Feature | Description |
|---------|-------------|
| **Multi-Dimensional Scoring** | Scores across capability, experience, and production-readiness dimensions |
| **Evidence-Based Assessment** | Every score backed by specific code evidence from repositories |
| **Confidence Scoring** | Statistical confidence level for each evaluation |
| **Shortlist Generation** | AI-ranked candidate shortlist with accept/reject/maybe recommendations |
| **Visualization Charts** | Radar and bar charts for dimension-level score comparison |

### 🔄 Continuous Learning

| Feature | Description |
|---------|-------------|
| **Feedback Loop** | Record hiring outcomes (hired/rejected/performed well) to improve future matching |
| **Adaptive Weights** | Signal weights automatically adjust based on historical hiring success |
| **Weight History Audit** | Full audit trail of how signal weights change over time |
| **LLM Log Inspection** | Admin access to review raw LLM inputs/outputs for any evaluation |

### 🌟 Candidate Experience & Invites

| Feature | Description |
|---------|-------------|
| **Reusable Invite Links** | Generate permanent, job-level invitation links for multiple candidates |
| **Unified Application Portal** | A stunning, branded (teal/brass) application portal for candidates |
| **Duplicate Prevention** | Prevents candidate double-submissions via email validation |
| **Automated Proof Injection** | Automatically creates Proof records for every outcome in the job |
| **State Sync & Cascading** | Real-time syncing of AI hiring decisions (Hired/Rejected) back to the recruiter dashboard |

### 🛠️ Operational Features

| Feature | Description |
|---------|-------------|
| **Prometheus Metrics** | Built-in `/metrics` endpoint for monitoring (evaluations, LLM latency, errors) |
| **Background Worker Queue** | Async processing for expensive operations (signal extraction, evaluation) |
| **Redis Caching** | Optional Redis for caching GitHub API responses (falls back to in-memory) |
| **Admin Dashboard** | System health, audit logs, and configuration management |
| **SPA Routing** | Seamless client-side routing configured for edge deployments (e.g., Vercel) |

---

## Architecture

### System Overview

```
 ┌───────────────────────────┐         ┌───────────────────────────┐
 │     FRONTEND (React)      │         │    BACKEND (FastAPI)      │
 │       Port 5173           │  HTTP   │       Port 8000           │
 │                           │◄───────►│                           │
 │  • React 18 + Vite        │  REST   │  • FastAPI + Uvicorn      │
 │  • TailwindCSS            │   API   │  • SQLAlchemy ORM         │
 │  • React Router v6        │         │  • PostgreSQL Database    │
 │  • Recharts               │         │  • OpenAI Integration     │
 │  • Lucide Icons           │         │  • GitHub API Client      │
 └───────────────────────────┘         │  • Worker Queue           │
                                       │  • Redis Cache (optional) │
                                       └───────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, Vite 5, TailwindCSS 3, React Router 6, Recharts, Lucide React |
| **Backend** | Python 3.11+, FastAPI 0.128, Uvicorn, SQLAlchemy 2.0 |
| **Database** | PostgreSQL (Neon serverless DB via psycopg2) |
| **AI/LLM** | OpenAI API (gpt-4o-mini) |
| **External APIs** | GitHub REST API |
| **Caching** | Redis (optional — in-memory fallback) |
| **Monitoring** | Prometheus-compatible metrics endpoint |
| **Async Processing** | Custom thread-pool worker queue |

### Database Schema

```
signalstack.db
├── outcomes              # What companies need accomplished
├── outcome_templates     # Reusable outcome definitions
├── tasks                 # Decomposed measurable sub-tasks
├── jobs                  # Job postings with metadata & SEO fields
├── invites               # Reusable, permanent job invitation links
├── invite_submissions    # Candidate applications via invite links
├── job_candidates        # Candidate-job associations & status
├── proofs                # Candidate submissions (GitHub repos)
├── snapshots             # Point-in-time repo analysis snapshots
├── evaluations           # AI assessment results & scores
├── feedback              # Hiring outcome feedback for learning
├── recruiters            # Recruiter accounts
└── audit_logs            # System audit trail
```

### Pipeline Architecture

```
                          ┌─────────────────┐
                          │   GitHub API     │
                          └────────┬────────┘
                                   │
                                   ▼
┌─────────┐   ┌──────────┐   ┌─────────────────┐   ┌──────────────┐   ┌────────────┐
│ Outcome  │──►│  Task     │──►│    Signal        │──►│  Scoring     │──►│  Shortlist  │
│ Creation │   │ Decompose │   │    Extraction    │   │  Engine      │   │  Generator  │
│          │   │  (LLM)    │   │                  │   │              │   │             │
│ Define   │   │ Break into│   │ • Deterministic  │   │ • Dimension  │   │ • Rank      │
│ what you │   │ measurable│   │   (rule-based)   │   │   scoring    │   │ • Accept/   │
│ need     │   │ tasks     │   │ • LLM-enhanced   │   │ • Evidence   │   │   Reject    │
│          │   │           │   │   (AI analysis)  │   │   matching   │   │ • Confidence│
└─────────┘   └──────────┘   │ • Identity        │   │ • Confidence │   │   scores    │
                              │   verification    │   │   calc       │   │             │
                              └─────────────────┘   └──────────────┘   └────────────┘
                                                                              │
                                                           ┌──────────────────┘
                                                           ▼
                                                    ┌────────────┐
                                                    │  Feedback   │
                                                    │  Loop       │
                                                    │             │
                                                    │ Adjust      │
                                                    │ weights     │
                                                    │ from hiring │
                                                    │ outcomes    │
                                                    └────────────┘
```

---

## Getting Started

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.11+ | Backend runtime |
| **Node.js** | 20+ | Frontend build tooling |
| **OpenAI API Key** | — | For AI task decomposition, signal analysis, and evaluation |
| **GitHub Token** | — | For repository analysis (read access scope) |
| **Redis** | 7+ *(optional)* | Caching layer — falls back to in-memory if unavailable |

### 1. Clone the Repository

```bash
git clone https://github.com/chinmai-sd-123/SIgnal_Stack.git
cd SIgnal_Stack
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your keys:

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

```env
# ─── REQUIRED ───────────────────────────────────────
GITHUB_TOKEN=ghp_your_github_token_here
OPENAI_API_KEY=sk-your_openai_api_key_here

# ─── OPTIONAL ───────────────────────────────────────
OPENAI_MODEL=gpt-4o-mini                   # Default model
DATABASE_URL=postgresql://user:password@host/dbname # Default: PostgreSQL
DATABASE_URL_TEST=postgresql://user:password@host/dbname_test # Test DB for pytest
REDIS_URL=redis://localhost:6379/0          # Falls back to in-memory
JWT_SECRET=change-this-in-production
WORKER_THREADS=3
ENABLE_LLM_SUMMARIZATION=true
PUBLIC_BASE_URL=http://localhost:3000       # Public job page base URL
DEBUG=false
```

> **Note:** See [`backend/.env.example`](backend/.env.example) for the full list of configuration options with inline documentation.

### 3. Install Dependencies

**Backend:**

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

**Frontend:**

```bash
cd frontend
npm install
```

### 4. Initialize the Database

```bash
cd backend
python create_tables.py
```

This creates the SQLite database with all required tables. Optionally seed with templates:

```bash
python seed_outcome_templates.py
```

### 5. Start the Application

**Terminal 1 — Backend (Port 8000):**

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend (Port 5173):**

```bash
cd frontend
npm run dev
```

### 6. Verify

| Service | URL |
|---------|-----|
| **Frontend UI** | http://localhost:5173 |
| **Backend API** | http://localhost:8000 |
| **API Docs (Swagger)** | http://localhost:8000/docs |
| **Prometheus Metrics** | http://localhost:8000/metrics |

---

## API Reference

### Core Pipeline

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/outcomes/` | Create a new outcome definition |
| `GET` | `/outcomes/` | List all outcomes |
| `POST` | `/decompose/{outcome_id}` | AI-decompose outcome into tasks |
| `POST` | `/submit-proof/` | Submit a GitHub repo as proof of work |
| `POST` | `/extract-signals/{proof_id}` | Extract signals from submitted proof |
| `POST` | `/evaluate/{outcome_id}` | Run AI evaluation for an outcome |
| `GET` | `/evaluation/{evaluation_id}` | Get evaluation results |

### Jobs & Invites

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/jobs/` | Create a new job posting |
| `GET` | `/jobs/` | List all jobs |
| `GET` | `/jobs/{job_id}` | Get job details |
| `PUT` | `/jobs/{job_id}` | Update a job |
| `DELETE` | `/jobs/{job_id}` | Delete a job |
| `POST` | `/jobs/{job_id}/invites` | Generate a new invite link |
| `GET` | `/invites/{token}` | Validate candidate invite link |
| `POST` | `/invites/{token}/submit`| Submit candidate application |

### Feedback & Learning

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/feedback/` | Submit hiring outcome feedback |
| `GET` | `/feedback/` | Get feedback history |

### Admin & Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/metrics` | Prometheus-compatible JSON metrics |
| `GET` | `/metrics/prometheus` | Prometheus text format |
| `GET` | `/admin/evaluations/{id}/llm_logs` | LLM call logs for an evaluation |
| `GET` | `/admin/weight-history` | Signal weight change audit trail |
| `GET` | `/analytics/` | Pipeline analytics dashboard data |

> **Full interactive API docs:** Visit http://localhost:8000/docs when the backend is running.

---

## Project Structure

```
signalstack/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry point, lifespan, CORS
│   │   ├── monitoring.py           # Prometheus metrics & structured logging
│   │   ├── config/
│   │   │   ├── config.py           # Environment variable loading
│   │   │   └── database.py         # SQLAlchemy engine & session factory
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── outcome.py          # Outcome definitions
│   │   │   ├── task.py             # Decomposed tasks
│   │   │   ├── job.py              # Job postings
│   │   │   ├── job_candidate.py    # Candidate-job tracking
│   │   │   ├── proof.py            # Submitted proofs
│   │   │   ├── snapshot.py         # Repo analysis snapshots
│   │   │   ├── evaluation.py       # AI evaluation results
│   │   │   ├── feedback.py         # Hiring feedback records
│   │   │   ├── recruiter.py        # Recruiter accounts
│   │   │   ├── outcome_template.py # Reusable templates
│   │   │   └── audit.py            # Audit log entries
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── routes/                 # API route handlers
│   │   │   ├── outcome.py          # Outcome CRUD
│   │   │   ├── task_decomposer.py  # AI task decomposition
│   │   │   ├── signal_extractor.py # Signal extraction trigger
│   │   │   ├── evaluator.py        # Evaluation pipeline
│   │   │   ├── feedback.py         # Feedback submission
│   │   │   ├── job.py              # Job management
│   │   │   ├── invite.py           # Candidate invites & submissions
│   │   │   ├── public_jobs.py      # Public job listing API
│   │   │   ├── repo.py             # GitHub repo operations
│   │   │   ├── snapshot.py         # Snapshot management
│   │   │   ├── analytics.py        # Analytics endpoints
│   │   │   └── outcome_templates.py# Template management
│   │   ├── services/               # Business logic layer
│   │   │   ├── llm.py              # OpenAI API client & prompt engineering
│   │   │   ├── llm_summarizer.py   # LLM output summarization & logging
│   │   │   ├── github.py           # GitHub API client
│   │   │   ├── crud.py             # Database CRUD operations
│   │   │   ├── cache.py            # Redis / in-memory cache
│   │   │   ├── worker_queue.py     # Background task queue
│   │   │   ├── repo_selector.py    # Intelligent repo selection
│   │   │   ├── shortlist_service.py# Candidate shortlisting logic
│   │   │   ├── weight_updater.py   # Adaptive signal weight learning
│   │   │   ├── secrets.py          # Secret management & key rotation
│   │   │   └── leetcode.py         # LeetCode profile analysis
│   │   ├── pipeline/               # Signal extraction & evaluation pipeline
│   │   │   ├── signal_extractor.py # Core signal extraction engine
│   │   │   ├── deterministic_signals.py # Rule-based signal detection
│   │   │   ├── evaluator.py        # AI evaluation orchestrator
│   │   │   ├── evidence_selector.py# Evidence matching & selection
│   │   │   ├── scoring_engine.py   # Multi-dimensional scoring
│   │   │   ├── identity_verifier.py# Git authorship forensics
│   │   │   ├── cost_guard.py       # LLM token budget management
│   │   │   ├── feedback.py         # Feedback processing pipeline
│   │   │   ├── matcher.py          # Signal-to-task matching
│   │   │   ├── snapshotter.py      # Repo snapshot creation
│   │   │   ├── outcome.py          # Outcome processing
│   │   │   ├── task_decomposer.py  # Task decomposition logic
│   │   │   ├── signal_normalizer.py# Signal normalization
│   │   │   ├── allocator.py        # Resource allocation
│   │   │   └── extractor.py        # Base extraction utilities
│   │   ├── constants/
│   │   │   └── categories.py       # Job categories & classifications
│   │   └── utils/
│   │       └── slug_utils.py       # URL slug generation
│   ├── data/                       # SQLite database files
│   ├── migrations/                 # Database migration scripts
│   ├── .env.example                # Environment variable template
│   ├── create_tables.py            # Database initialization script
│   ├── seed_outcome_templates.py   # Template seeding script
│   └── requirements.txt            # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── main.jsx                # React entry point
│   │   ├── App.jsx                 # Router & route definitions
│   │   ├── api.js                  # Backend API client
│   │   ├── index.css               # Global styles & design tokens
│   │   ├── App.css                 # App-level styles
│   │   ├── pages/                  # Page-level components
│   │   │   ├── JobDashboard.jsx    # Main dashboard — job listings
│   │   │   ├── JobCreateWizard.jsx # Job creation wizard
│   │   │   ├── JobDetail.jsx       # Job detail view with invite links
│   │   │   ├── CandidateApply.jsx  # Public candidate application portal
│   │   │   ├── OutcomeCreate.jsx   # Single outcome creation
│   │   │   ├── OutcomeCreateMultiple.jsx # Batch outcome creation
│   │   │   ├── OutcomeDashboard.jsx# Outcome detail & progress
│   │   │   ├── ProofSubmit.jsx     # GitHub proof submission
│   │   │   ├── EvaluationView.jsx  # Evaluation results & charts
│   │   │   ├── HiringDecisions.jsx # Hiring decision management
│   │   │   ├── ReviewerQueue.jsx   # Evaluation review queue
│   │   │   ├── FeedbackView.jsx    # Feedback & learning insights
│   │   │   ├── Dashboard.jsx       # Legacy outcomes dashboard
│   │   │   ├── Admin.jsx           # Admin panel
│   │   │   └── AdminAudit.jsx      # Audit log viewer
│   │   └── components/             # Reusable UI components
│   │       ├── Layout.jsx          # App shell & navigation
│   │       ├── DimensionChart.jsx  # Radar/bar score charts
│   │       ├── EvidenceItem.jsx    # Evidence display component
│   │       ├── EvidenceModal.jsx   # Evidence detail modal
│   │       ├── FeedbackModal.jsx   # Feedback submission modal
│   │       ├── TemplateSelector.jsx# Template picker
│   │       └── TemplateSelectionModal.jsx # Template selection modal
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── eslint.config.js
│
├── .gitignore
└── README.md
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | **Yes** | — | GitHub PAT with `repo` read scope |
| `OPENAI_API_KEY` | **Yes** | — | OpenAI API key for LLM features |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | OpenAI model identifier |
| `DATABASE_URL` | No | `sqlite:///./signalstack.db` | SQLAlchemy database URL |
| `DATABASE_URL_TEST` | No | — | Postgres test database URL for integration tests |
| `REDIS_URL` | No | — | Redis connection URL for caching |
| `JWT_SECRET` | No | `dev-secret-...` | JWT signing secret (**change in production**) |
| `SIGNALSTACK_API_KEY` | No | — | API key for external integrations |
| `WORKER_THREADS` | No | `3` | Number of background worker threads |
| `ENABLE_LLM_SUMMARIZATION` | No | `true` | Toggle LLM-enhanced analysis |
| `PUBLIC_BASE_URL` | No | `http://localhost:3000` | Base URL for public job links |
| `DEBUG` | No | `false` | Enable verbose debug logging |

---

## Testing

Backend tests are split into fast unit tests and Postgres-backed integration tests. The repository-level
`pytest.ini` sets `backend/` on `PYTHONPATH`, disables pytest cache writes, and points pytest at
`backend/tests`.

```bash
# Install test dependencies
python -m pip install -r backend/requirements.txt -r backend/requirements-test.txt

# Run the full backend suite
python -m pytest -v

# Run only unit tests
python -m pytest -m unit -v

# Run only integration tests
DATABASE_URL_TEST=postgresql://user:password@host/dbname_test python -m pytest -m integration -v
```

Current verification status:

| Check | Command | Status |
|-------|---------|--------|
| Backend tests | `python -m pytest -v` | 13 passing |
| Frontend lint | `npm run lint` | Passing |
| Frontend build | `npm run build` | Passing |

On Windows PowerShell, if `npm run ...` is blocked by the script execution policy, run the same command
through `npm.cmd`, for example `npm.cmd run build`.

### Frontend Quality Checks

```bash
cd frontend
npm install
npm run lint
npm run build
```

---

## Monitoring

SignalStack exposes Prometheus-compatible metrics at `/metrics`:

| Metric | Type | Description |
|--------|------|-------------|
| `signalstack_evaluations_total` | Counter | Total evaluations executed |
| `signalstack_llm_calls_total` | Counter | Total LLM API calls |
| `signalstack_llm_failures_total` | Counter | Failed LLM calls |
| `signalstack_snapshot_fetch_total` | Counter | GitHub snapshot fetches |
| `signalstack_feedback_events_total` | Counter | Feedback events recorded |
| `signalstack_evaluation_duration_seconds` | Histogram | Evaluation processing time |
| `signalstack_llm_latency_seconds` | Histogram | LLM API response latency |
| `signalstack_active_evaluations` | Gauge | Currently running evaluations |

---

## License

This project is proprietary software. All rights reserved.

---

<p align="center">
  <strong>Built for the future of hiring — where proof beats promises.</strong>
</p>
