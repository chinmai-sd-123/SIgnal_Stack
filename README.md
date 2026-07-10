# SignalStack

**Proof-of-work hiring infrastructure.** SignalStack turns a job description into measurable outcomes, collects candidate repositories and artifacts, parses real code, and produces evidence-backed hiring reports — every score traceable to inspectable proof.

> Resumes claim. Code proves. SignalStack evaluates what candidates actually built.

---

## How It Works

```text
Recruiter                      Candidate                     Evaluation Engine
─────────                      ─────────                     ─────────────────
Create job                                                   
  └─ Define outcomes                                         
      └─ AI generates                                        
         verifiable signals                                  
             │                                               
             ▼                                               
      Share invite link ────►  Apply (no login)              
                                └─ Submit up to 3 repos,     
                                   resume, LeetCode, notes   
                                        │                    
                                        ▼                    
                               Proof records created ──────► Background queue (Redis)
                                                                │
                                                                ├─ 1. Screen: deterministic
                                                                │     signals per repo, best
                                                                │     repo picked per candidate
                                                                ├─ 2. Deep eval (top N):
                                                                │     per signal, route evidence
                                                                │     from the BEST-matching repo
                                                                ├─ 3. Grounded LLM assessment
                                                                │     (strict JSON, evidence-only)
                                                                └─ 4. Score + verify authorship
                                                                        │
             ◄──────────────────────────────────────────────────────────┘
Review report: fit score, evidence cards, code snippets,
GitHub links, risk flags → interview / reject → feedback
updates signal weights for future evaluations
```

### Evaluation pipeline

1. **Outcome decomposition** — each role becomes outcomes; each outcome gets 3–5 short, evidence-checkable signals (AI-generated, recruiter-editable).
2. **Multi-repo intake** — candidates submit up to **3 repositories**. A RAG signal is judged against their RAG project, an API signal against their API project: each signal is routed to the repo with the strongest evidence for it.
3. **Deterministic screening** — tests, CI, Docker, migrations, framework usage, commit activity, fork detection, README quality. No LLM cost; every candidate gets screened.
4. **Evidence selection** — priority-ranked file selection (task-specific implementation files above manifests/README), content-relevance boosting, keyword-anchored snippets with GitHub source links.
5. **Grounded LLM assessment** — the model sees only selected evidence, must return strict JSON, may cite only supplied snippets (ungrounded citations are replaced with real ones), and scores are capped when no implementation code exists.
6. **Scoring** — separates **capability** (did they build it) from **evidence confidence**, **production readiness**, and **verification** (commit authorship). Learned signal weights from recruiter feedback are applied at every scoring stage.
7. **Learning loop** — interview/reject decisions and task boosts adjust signal/task weights (bounded, audited, revertible) for this job and its master template.

### Why it's fair for early-career candidates

Tests, CI, Docker, and deployment are treated as **bonuses**, not baseline requirements — unless the outcome explicitly demands them. Authorship uncertainty is surfaced as a trust note, never a hidden penalty. Unmodified forks and near-zero authorship are hard-capped.

---

## Architecture

```text
frontend/  React 18 + Vite + Tailwind (Vercel)
backend/   FastAPI + SQLAlchemy (Render)
           ├─ routes/     REST API (recruiter auth, jobs, outcomes, invites, evaluation)
           ├─ pipeline/   evaluator, evidence selector, signal extractor, scoring engine,
           │              identity verifier, feedback learning
           ├─ services/   LLM (OpenAI), GitHub, LeetCode, Redis queue/cache, auth, CRUD
           ├─ models/     SQLAlchemy models (PostgreSQL / Neon)
           └─ alembic/    schema migrations
```

| Concern | Implementation |
| --- | --- |
| API | FastAPI, Pydantic schemas, role-based access (admin / recruiter / public candidate) |
| Data | PostgreSQL (Neon) via SQLAlchemy; Alembic migrations; SQLite fallback for local dev |
| Queue & cache | Redis-backed evaluation queue with worker recovery; in-memory fallback |
| AI | OpenAI Responses API, strict JSON schema outputs, model routing (eval vs fast model), retries with jittered backoff, response caching, cost tracking |
| GitHub | Recursive tree + file + commit fetching, caching, retry/backoff on transient failures |
| Auth | PBKDF2-hashed passwords, signed bearer tokens, invite-only recruiter signup, admin bootstrap via `ADMIN_EMAIL` |
| Observability | `/metrics` (JSON) and `/metrics/prometheus`: LLM latency/tokens/cost, cache hits, evaluation durations, per-candidate/job cost |

### Reliability behaviors

- **Incremental reports** — new candidates merge into existing outcome reports; earlier candidates stay visible while refresh runs.
- **Worker recovery** — interrupted `evaluating` rows are re-queued; progress polling can revive the Redis worker after a process restart (Render-style deploys).
- **Evidence isolation** — proofs are scoped by job + outcome + candidate + submission, so evidence never leaks across reports.
- **Hallucination controls** — evidence-only prompting, grounded-citation checks, score caps, deterministic scoring layer.

---

## Getting Started

**Prerequisites:** Python 3.11+, Node 20+, PostgreSQL (or SQLite fallback), Redis (optional), GitHub token, OpenAI API key.

```bash
# Backend
cd backend
python -m venv .venv && .venv\Scripts\Activate.ps1   # or: source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
cp .env.example .env                                  # fill in your values
alembic upgrade head                                  # fresh DB (or: alembic stamp head for an existing DB)
uvicorn app.main:app --port 8000 --reload

# Frontend
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` (app), `http://localhost:8000/docs` (API), `http://localhost:8000/metrics` (metrics).

**Demo access:** run `python seed_demo_auth.py` to seed the demo recruiter (`demo@signalstack.dev` / `Demo@12345`, shown on the login page) plus an admin account and a sample job.

### Environment variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | Yes | Signal generation and grounded assessment. |
| `GITHUB_TOKEN` | Yes | Repository and commit analysis. |
| `DATABASE_URL` | Recommended | PostgreSQL connection (SQLite fallback if unset). |
| `REDIS_URL` | Recommended | Durable queue + cache (in-memory fallback if unset). |
| `AUTH_SECRET` | Production | Token-signing secret. |
| `ADMIN_EMAIL` | Production | First login with this email bootstraps the admin account. |
| `OPENAI_MODEL` | No | Primary model (default `gpt-5-mini`). |
| `OPENAI_EVAL_MODEL` / `OPENAI_FAST_MODEL` | No | Route grounded assessment vs cheap high-volume calls to different models. |
| `OPENAI_REASONING_EFFORT` / `OPENAI_MAX_OUTPUT_TOKENS` | No | Optional tuning for reasoning-capable models. |
| `LLM_INPUT_COST_PER_1M` / `LLM_OUTPUT_COST_PER_1M` | No | Price overrides for cost metrics (inferred per model by default). |
| `DEMO_RECRUITER_EMAIL` / `DEMO_RECRUITER_PASSWORD` | No | Demo seed credentials. |
| `WORKER_THREADS`, `PUBLIC_BASE_URL`, `DEBUG` | No | Worker concurrency, invite-link base URL, verbose logging. |

### Migrations

Alembic owns schema evolution (`backend/alembic/`). The baseline is idempotent.

```bash
cd backend
alembic upgrade head                                # fresh database
alembic stamp head                                  # adopt on an existing/deployed database
alembic revision --autogenerate -m "describe change"  # future changes
```

A narrow runtime `schema_guard` also self-heals recently added columns at startup, so deploys stay safe before migrations run.

---

## Quality Gates

```bash
python -m pytest backend/tests -q      # backend tests
cd frontend && npm run lint && npm run build
```

Pre-merge: tests green, lint clean, build passes, no secrets committed, auth-isolation tests run when touching access control.

---

## Key API Surfaces

| Endpoint | Purpose |
| --- | --- |
| `POST /recruiter/login` · `POST /recruiter/signup` | Auth (signup is invite-only). |
| `POST /jobs` · `GET /jobs/{id}` · `PATCH` · `DELETE` | Job lifecycle. |
| `POST /outcomes` · `PATCH /outcomes/{id}` | Outcome + signal management. |
| `POST /jobs/{id}/invites` · `POST /invites/{token}/submit` | Invite links and public candidate submission (supports `repo_urls`, max 3). |
| `POST /jobs/{id}/evaluations/queue` · `GET /jobs/{id}/evaluations/progress` | Background evaluation + job-scoped progress. |
| `GET /plugin/status/{outcome_id}` | Outcome evaluation report. |
| `POST /plugin/feedback` · `POST /feedback/task-weight` | Learning loop. |
| `GET /admin/*` | Signal weights, learning history, audit logs, LLM logs (admin only). |
| `GET /metrics` · `GET /metrics/prometheus` | Observability. |

---

## Design Principles

1. **Proof beats promises** — evaluate real work.
2. **Evidence beats vibes** — every score points to inspectable artifacts.
3. **Uncertainty is visible** — confidence, verification, and risk flags are first-class.
4. **Early candidates deserve fairness** — personal projects aren't judged like enterprise systems.
5. **Recruiters need decisions, not dashboards** — job → candidates → evidence → decision, fast.

## Roadmap

Separate worker service (Celery/RQ) · OpenTelemetry traces · embedding-based evidence retrieval for large repos · evaluation regression/calibration sets · organization & team permissions · exportable reports · realtime progress via SSE.

---

**License:** Proprietary. All rights reserved.
