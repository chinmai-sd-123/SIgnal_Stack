# SignalStack

**Proof-of-work hiring infrastructure for technical teams.**

SignalStack turns a job description into measurable outcomes, collects candidate proof of work, analyzes repositories and artifacts, and produces evidence-backed hiring reports. It is built for teams that want to evaluate what candidates have actually built instead of relying on resume keywords.

---

## Why This Exists

Most early hiring funnels are noisy:

- Resumes are hard to verify.
- Personal projects are evaluated inconsistently.
- Recruiters do not have time to inspect every repository deeply.
- Traditional ATS scoring rewards keyword stuffing instead of demonstrated work.
- Great early-career candidates may not have CI/CD, production deployments, or polished portfolios.

SignalStack solves this with an outcome-first evaluation pipeline:

1. Define the job.
2. Decompose the job into outcomes.
3. Generate evidence-checkable signals for each outcome.
4. Collect candidate repositories, resumes, LeetCode profiles, and context.
5. Parse repositories deeply across code, config, manifests, README files, commits, and folders.
6. Score candidates with grounded evidence, confidence, authorship verification, and production-readiness signals.
7. Let recruiters review, shortlist, reject, or proceed to interview.

The system is intentionally strict about evidence and intentionally fair about personal projects: tests, CI, Docker, and deployment are treated as quality bonuses unless the role explicitly requires them.

---

## Product Snapshot

| Area | What SignalStack Does |
| --- | --- |
| Job modeling | Creates job postings with multiple role-specific outcomes. |
| Outcome decomposition | Uses AI to generate short, verifiable evaluation signals. |
| Candidate intake | Provides public invite links and a candidate application portal. |
| Recruiter access | Supports email/password login, invite-only recruiter signup, admin role controls, and recruiter-scoped data isolation. |
| Repository analysis | Reads source files, folders, manifests, commits, README files, and selected snippets. |
| Repo selection | Selects likely relevant repositories from a GitHub profile using job context. |
| Evidence grounding | Grounds AI assessments in concrete code snippets and deterministic facts. |
| Scoring | Separates capability, evidence confidence, verification, and production readiness. |
| Queueing | Supports Redis-backed background evaluation for high-volume candidate batches. |
| Review UX | Shows ranked candidates, evidence cards, skill dimensions, and decision actions. |
| Learning loop | Captures feedback and adjusts future signal weights. |
| Admin operations | Exposes admin-only signal weights, task learning, audit logs, LLM logs, recruiter invites, and metrics. |

---

## Architecture

```text
Candidate Invite
      |
      v
Candidate Application Portal
      |
      v
Proof Records: GitHub repo, resume, LinkedIn, LeetCode, notes
      |
      v
Background Evaluation Queue
      |
      +--> GitHub repository parser
      +--> Repository selector
      +--> Deterministic signal extractor
      +--> Authorship verifier
      +--> Evidence selector
      +--> LLM grounded assessment
      +--> Scoring engine
      |
      v
Recruiter Report: score, confidence, verification, evidence, decision
```

### Backend

- **FastAPI** API server
- **SQLAlchemy** persistence layer
- **PostgreSQL** for production data
- **Redis** for durable evaluation queue and cache when configured
- **JWT-style bearer authentication** for recruiters and admins
- **OpenAI** for grounded assessment and signal generation
- **GitHub API** for repository tree, file, commit, and metadata analysis
- **LeetCode GraphQL** lookup for real profile stats, with no fake fallback
- **Prometheus-compatible metrics** for operational monitoring

### Frontend

- **React 18**
- **Vite**
- **React Router**
- **Tailwind CSS**
- **Recharts**
- **Lucide icons**

The frontend is job-centric: recruiters manage jobs, outcomes, invite links, candidates, evaluation progress, and final decisions from one workflow. Public candidate invite links remain unauthenticated, while recruiter/admin pages require login.

---

## Authentication and Access Control

SignalStack now supports multi-recruiter usage with role-based access.

| Role | Access |
| --- | --- |
| Admin | Can access all jobs, admin panels, recruiter invites, signal weights, task learning, audit logs, LLM logs, analytics, and metrics. |
| Recruiter | Can create and manage only their own jobs, outcomes, invites, submissions, evaluations, reports, and decisions. |
| Candidate | Can access only public invite/application links and submit proof for that invite. |

Authentication behavior:

- Recruiters log in with email and password.
- New recruiter signup is invite-only.
- Admin creates recruiter invites from the admin/recruiter management flow.
- The first login for `ADMIN_EMAIL` can bootstrap the admin account.
- Jobs are owned by `recruiter_id`; non-admin users only see and mutate their own jobs.
- Admin pages are guarded by role checks, not only hidden in the frontend.
- Public candidate application links stay public so candidates can apply without an account.

Security-sensitive operations include backend access checks:

- Job create/list/detail/update/archive/delete
- Outcome create/edit/delete
- Invite create/list/delete
- Submission list/delete
- Evaluation queue/progress/report fetch
- Feedback and decision history
- Admin-only weight learning, audit logs, LLM logs, metrics, and recruiter invites

---

## Core Evaluation Philosophy

SignalStack does not produce a single opaque AI number. It separates the report into dimensions that are useful for hiring decisions:

| Dimension | Purpose |
| --- | --- |
| Capability | Does the work show the skill required by the outcome? |
| Evidence confidence | How much concrete evidence supports the claim? |
| Verification | Is there authorship evidence that the candidate contributed? |
| Production readiness | Are there quality signals such as tests, docs, deployment, CI, or Docker? |
| Risk flags | Are there signs of copied forks, missing proof, unrelated artifacts, or weak grounding? |

Authorship is not used as a blunt punishment. The system reports whether authorship is verified, unverified, or conflicting, while still evaluating the work itself. This makes the output fairer for early applicants and more useful for recruiters.

The headline candidate score is the final fit score. Capability remains visible as a separate sub-score, so recruiters can distinguish "this candidate built the core thing" from "this project also has strong verification and production hygiene." The report-level top fit score and the top candidate card use the same scoring definition.

---

## Evidence Grounding

The evaluator is designed to avoid hallucinated assessments:

- AI assessment receives outcome title, outcome description, and signal text.
- Evidence is selected from actual repository files, code snippets, manifests, README files, commits, and deterministic facts.
- Resume links are treated as candidate context, not proof of code implementation.
- Evidence snippets are scoped to the candidate and submission so one candidate's repository does not leak into another report.
- The UI presents evidence as a clean audit trail: AI assessment, key evidence, short code snippets with GitHub links, repository structure, authorship verification, and project health scan.
- Stored evidence is compacted to protect database reliability, while preserving the important evidence categories reviewers need to audit a decision.
- Full code inspection redirects to GitHub source links instead of storing huge file blobs in the evaluation row.
- If no relevant code or artifact evidence exists, score strength is capped.
- GitHub fetches retry transient disconnects, timeouts, rate limits, and server errors with exponential backoff before falling back.

---

## Queue and Scale Behavior

SignalStack supports high-volume candidate evaluation through a background queue.

| Scenario | Behavior |
| --- | --- |
| 2 candidates | Evaluations run in the background and progress is visible on the job page. |
| 1,000 candidates | Submissions are queued, processed asynchronously, and tracked with job-specific progress. |
| User navigates away | Backend processing continues; returning to the job page refreshes live progress. |
| Redis configured | Redis-backed queue survives process restarts better than memory-only queue. |
| Redis unavailable | System falls back to in-memory queue and cache for local development. |
| New candidate after an earlier evaluation | Only missing/stale report candidates are refreshed and merged into the latest outcome report. Existing evaluated candidates remain visible while the full report catches up. |
| Existing report while refresh is running | Recruiters can open the partial/current report while missing candidates are evaluated in the background. |
| Re-clicking evaluate | Already evaluated candidates are not unnecessarily re-run unless the outcome/report is stale. |

The frontend shows job-scoped queue progress, not global queue noise from another job.
For small and medium batches, the job progress card lists every evaluated candidate returned by the backend instead of hiding candidates behind a fixed five-person preview.

---

## Metrics, Latency, and Observability

SignalStack exposes runtime metrics from the backend at:

- `GET /metrics` for JSON metrics
- `GET /metrics/prometheus` for Prometheus text format

Current metric families:

| Metric | Type | What It Tells You |
| --- | --- | --- |
| `signalstack_evaluations_total` | Counter | Total completed evaluation runs. |
| `signalstack_snapshot_fetch_total` | Counter | GitHub snapshot/repository fetch attempts. |
| `signalstack_snapshot_fetch_errors` | Counter | Failed repository snapshot fetches. |
| `signalstack_llm_calls_total` | Counter | Total LLM calls made by the system. |
| `signalstack_llm_failures_total` | Counter | Failed LLM calls. |
| `signalstack_llm_input_tokens_total` | Counter | Provider-reported input tokens. |
| `signalstack_llm_output_tokens_total` | Counter | Provider-reported output tokens. |
| `signalstack_llm_estimated_cost_total` | Counter | Estimated LLM spend using configured or model-inferred token prices. |
| `signalstack_llm_cache_hits_total` | Counter | LLM prompt/schema cache hits. |
| `signalstack_llm_cache_misses_total` | Counter | LLM prompt/schema cache misses. |
| `signalstack_llm_usage_missing_total` | Counter | LLM calls where provider usage data was not returned. |
| `signalstack_feedback_events_total` | Counter | Recruiter feedback events captured. |
| `signalstack_active_evaluations` | Gauge | Evaluations currently running. |
| `signalstack_cost_per_candidate{candidate_id}` | Gauge | Accumulated estimated LLM cost for a candidate. |
| `signalstack_cost_per_job{job_id}` | Gauge | Accumulated estimated LLM cost for a job. |
| `signalstack_evaluation_duration_seconds` | Histogram | End-to-end evaluation duration. |
| `signalstack_llm_latency_seconds` | Histogram | LLM call latency. |

The JSON endpoint returns `avg`, `min`, `max`, `p50`, `p95`, and `p99` for histogram metrics. This lets the team reason about real latency instead of relying on one-off local timings.

Example response shape:

```json
{
  "uptime_seconds": 1234.5,
  "counters": {
    "evaluations_total": 42,
    "llm_calls_total": 120,
    "llm_failures_total": 1
  },
  "gauges": {
    "active_evaluations": 2
  },
  "histograms": {
    "evaluation_duration_seconds": {
      "count": 42,
      "avg": 18.4,
      "p50": 12.1,
      "p95": 44.8,
      "p99": 61.2
    },
    "llm_latency_seconds": {
      "count": 120,
      "avg": 2.7,
      "p50": 1.9,
      "p95": 6.4,
      "p99": 9.2
    }
  }
}
```

### Recommended Production SLOs

These are operating targets, not hardcoded claims:

| Workflow | Target |
| --- | --- |
| Job detail page progress fetch | p95 under 500 ms |
| Invite page load | p95 under 1 s |
| Repository preview | p95 under 3 s with cache warm |
| Single LLM call | p95 under 8 s |
| Candidate screening | p95 under 60 s per candidate, depending on repo size |
| 1,000-candidate job evaluation | Background queue completes progressively without blocking recruiter navigation |
| LLM failure rate | Under 2 percent |
| Evaluation stuck states | 0 unresolved `evaluating` rows after worker recovery |

### Monitoring Dashboard Ideas

For production, track:

- Evaluation throughput per hour
- Queue depth and processing age
- Active evaluations
- LLM calls per candidate
- LLM failure rate
- Average and p95 LLM latency
- GitHub API error rate
- Cache hit rate for GitHub and LLM responses
- Cost per evaluated candidate
- Candidates evaluated per job
- Evidence-missing rate
- Authorship verified/unverified/conflict distribution

---

## LLM Cost Optimization

SignalStack is designed to avoid calling the LLM when deterministic evidence is enough or when prerequisites are missing.

Existing controls:

| Control | How It Reduces Cost |
| --- | --- |
| Cost guard | Skips full LLM evaluation when no repo or evidence is available. |
| GitHub cache | Avoids repeatedly fetching repository trees, files, and commits. |
| LLM response cache | Reuses model responses for identical prompts and schemas. |
| Evidence selector | Sends only high-signal snippets instead of entire repositories. |
| Evidence compaction | Stores a compact audit trail instead of huge report payloads. |
| Deterministic signals | Computes tests, CI, manifests, authorship, frameworks, and repo facts without LLM calls. |
| Top-candidate deep evaluation | Screens all candidates first, then deep-evaluates the strongest candidates. |
| Redis queue | Prevents duplicate queued work and keeps processing durable. |
| Incremental report merge | Evaluates only missing/stale candidates when new submissions arrive. |

Recommended cost strategy:

1. **Use a two-stage pipeline.**
   - Stage 1: deterministic screening for every candidate.
   - Stage 2: LLM deep evaluation only for top candidates or borderline cases.

2. **Set a deep-evaluation limit.**
   - For high-volume roles, evaluate all submissions cheaply, then run deep LLM assessment on the top 50-100 candidates.

3. **Cache aggressively.**
   - Cache GitHub trees, file contents, commit history, repo selection, and LLM outputs.
   - Use Redis in production so cache survives process restarts.

4. **Keep prompts evidence-only.**
   - Send selected snippets, deterministic facts, and outcome signals.
   - Do not send whole repositories, full resumes, or repeated boilerplate.

5. **Use smaller models for routing and summaries.**
   - Use a low-cost model for task/signal generation and summarization.
   - Reserve stronger models for final grounded assessment only when needed.

6. **Skip low-evidence candidates.**
   - If there is no valid repo, no artifact, or no relevant code evidence, return a deterministic low-confidence report instead of paying for an LLM call.

7. **Track cost per candidate.**
   - Add counters for `input_tokens`, `output_tokens`, `model`, `cached`, and `estimated_cost`.
   - Compute `cost_per_candidate = total_llm_cost / candidates_evaluated`.

8. **Batch where safe.**
   - Batch simple summarization or signal-generation tasks.
   - Do not batch unrelated candidate evidence into one prompt if it risks evidence leakage.

9. **Cap evidence size.**
   - Keep only the best snippets per outcome signal.
   - Prefer exact code excerpts over long README text.

10. **Review prompt drift.**
   - Regression-test prompts so generated signals stay short, verifiable, and role-specific.

Implemented cost metrics:

| Metric | Why It Matters |
| --- | --- |
| `signalstack_llm_input_tokens_total` | Tracks prompt growth. |
| `signalstack_llm_output_tokens_total` | Tracks generated output volume. |
| `signalstack_llm_estimated_cost_total` | Tracks spend directly. |
| `signalstack_llm_cache_hits_total` | Shows savings from prompt caching. |
| `signalstack_cost_per_candidate{candidate_id}` | Shows accumulated LLM cost for each candidate. |
| `signalstack_cost_per_job{job_id}` | Shows accumulated LLM cost for each job. |

Recommended cost metrics to add next:

| Metric | Why It Matters |
| --- | --- |
| `signalstack_llm_calls_per_candidate` | Detects expensive evaluation paths. |
| `signalstack_llm_cache_hit_rate` | Shows cache effectiveness as a ratio. |
| `signalstack_cost_per_hire` | Connects AI spend to hiring outcomes. |

---

## Repository Analysis

SignalStack is built to inspect code, not just README files.

It analyzes:

- Source files
- Folder structure
- README and docs
- Package manifests
- Requirements files
- Config files
- Tests when present
- CI/CD files when present
- Docker/deployment files when present
- Commit authorship and activity
- Framework and library usage
- Domain-specific code evidence for each outcome signal

Small but important source files are preserved as evidence instead of being drowned out by generic config files. GitHub requests are cached and retried with backoff for transient `RemoteDisconnected`, timeout, `429`, and `5xx` failures, which reduces false "no evidence found" outcomes caused by network instability.

Report evidence is intentionally compact:

- Keep the key AI-selected evidence.
- Keep the strongest source snippets for the signal.
- Keep repository structure context.
- Keep authorship verification.
- Keep project health scan.
- Link reviewers to GitHub for full source inspection.

---

## Key Features

### Recruiter Workflow

- Log in with email/password.
- Admins invite new recruiter accounts.
- Create a job.
- Add one or more outcomes.
- Generate concise evaluation signals.
- Invite candidates with reusable public links.
- Review live application and evaluation progress.
- Compare ranked candidates.
- Inspect evidence.
- Proceed to interview or reject.
- Capture feedback for future weighting.
- Delete jobs, outcomes, invites, or submissions with guarded destructive actions where supported.

### Candidate Workflow

- Open invite link.
- Submit profile details.
- Add GitHub username and repository.
- Optionally add resume, LinkedIn, LeetCode, and notes.
- Receive submission confirmation.

### Evaluation Workflow

- Parse proof payload.
- Select relevant repository.
- Extract deterministic signals.
- Verify authorship where possible.
- Build evidence snippets.
- Run grounded AI assessment.
- Score candidate per outcome.
- Aggregate results across the job.
- Surface report to recruiter.
- Merge newly evaluated candidates into existing reports without hiding previous candidates.

### Admin Workflow

- Invite recruiters and review invite status.
- View all jobs across recruiters.
- Monitor analytics, decision history, and active roles.
- Inspect signal weights and feedback-driven learning history.
- Review task-level learning changes.
- Inspect audit logs and LLM interaction logs.
- Check LLM usage, latency, tokens, cache hits, and estimated cost metrics.

---

## Project Structure

```text
Signal_Stack/
  backend/
    app/
      config/              Database and runtime config
      constants/           Shared constants and category definitions
      models/              SQLAlchemy models
      pipeline/            Extraction, evidence, scoring, evaluation
      routes/              FastAPI route handlers
      schemas/             Pydantic request/response schemas
      services/            Auth, GitHub, Redis, LLM, queue, feedback, LeetCode
      utils/               Shared helpers
    tests/                 Unit and integration tests
    requirements.txt
    requirements-test.txt
  frontend/
    src/
      components/          Shared UI components
      pages/               App pages and workflows
      api.js               API client
      App.jsx              Router
    package.json
  README.md
  pytest.ini
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL for production-like runs
- Redis for durable queueing and cache
- GitHub token for repository analysis
- OpenAI API key for AI signal generation and assessment

### Backend Setup

```bash
cd backend
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate

python -m pip install -r requirements.txt -r requirements-test.txt
```

Create `backend/.env`:

```env
GITHUB_TOKEN=your_github_token
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5-mini
LLM_INPUT_COST_PER_1M=
LLM_OUTPUT_COST_PER_1M=

DATABASE_URL=postgresql://postgres:password@localhost:5432/signalstack
DATABASE_URL_TEST=postgresql://postgres:password@localhost:5432/signalstack_test

REDIS_URL=redis://localhost:6379/0

AUTH_SECRET=replace-with-a-long-random-secret
JWT_SECRET=
ADMIN_EMAIL=you@example.com
DEMO_RECRUITER_EMAIL=demo@signalstack.dev
DEMO_RECRUITER_PASSWORD=Demo@12345
SIGNALSTACK_API_KEY=

WORKER_THREADS=3
ENABLE_LLM_SUMMARIZATION=true
PUBLIC_BASE_URL=http://localhost:5173
DEBUG=false
```

Run the backend:

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open:

- Frontend: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`
- Metrics: `http://localhost:8000/metrics`

### First Admin Login

Set `AUTH_SECRET` and `ADMIN_EMAIL` before sharing the app with recruiters.

The first successful login using `ADMIN_EMAIL` bootstraps an admin account if one does not already exist. After that, the admin can create invite-only recruiter accounts from the recruiter invite/admin flow.

Optional demo seeding:

```bash
cd backend
python seed_demo_auth.py
```

The seed script uses `ADMIN_EMAIL`, `DEMO_RECRUITER_EMAIL`, and `DEMO_RECRUITER_PASSWORD`.

---

## Environment Variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `GITHUB_TOKEN` | Yes | GitHub repository and commit analysis. |
| `OPENAI_API_KEY` | Yes | AI signal generation and grounded assessment. |
| `OPENAI_MODEL` | No | Model name used by the OpenAI client. |
| `LLM_INPUT_COST_PER_1M` | Optional | Current input-token price per 1M tokens for estimated-cost metrics. Defaults are inferred for common OpenAI text models. |
| `LLM_OUTPUT_COST_PER_1M` | Optional | Current output-token price per 1M tokens for estimated-cost metrics. Defaults are inferred for common OpenAI text models. |
| `DATABASE_URL` | Recommended | Production database connection. |
| `DATABASE_URL_TEST` | Test only | Integration test database. |
| `REDIS_URL` | Recommended | Redis cache and job evaluation queue. |
| `AUTH_SECRET` | Production | Long random secret used for recruiter/admin auth token signing. |
| `JWT_SECRET` | Optional | Backward-compatible fallback if `AUTH_SECRET` is not set. |
| `ADMIN_EMAIL` | Production | Email address that receives admin role and can bootstrap the first admin login. |
| `DEMO_RECRUITER_EMAIL` | Optional | Demo recruiter email used by the auth seed script. |
| `DEMO_RECRUITER_PASSWORD` | Optional | Demo recruiter password used by the auth seed script. |
| `SIGNALSTACK_API_KEY` | Optional | External integration key. |
| `WORKER_THREADS` | Optional | In-memory worker concurrency. |
| `ENABLE_LLM_SUMMARIZATION` | Optional | Enables LLM-based summaries. |
| `PUBLIC_BASE_URL` | Optional | Base URL for public invite links. |
| `DEBUG` | Optional | Enables verbose debug behavior. |

---

## Quality Gates

Run backend tests:

```bash
python -m pytest backend/tests -q
```

Run frontend checks:

```bash
cd frontend
npm run lint
npm run build
```

On Windows PowerShell, use `npm.cmd` if script execution policy blocks `npm`:

```powershell
npm.cmd run lint
npm.cmd run build
```

Recommended pre-merge checklist:

- Backend tests pass.
- Frontend lint passes.
- Frontend production build passes.
- No secrets committed.
- Auth isolation tests pass when changing recruiter/admin access.
- Admin-only routes are checked from both admin and recruiter accounts.
- Redis queue tested if changing evaluation processing.
- Evidence grounding tests updated if changing scoring or LLM prompts.
- Browser check completed for candidate application and job evaluation pages.

---

## Important API Surfaces

| Endpoint | Purpose |
| --- | --- |
| `POST /recruiter/login` | Log in as recruiter or admin. |
| `POST /recruiter/signup` | Create recruiter account from an admin-generated invite token. |
| `GET /recruiter/me` | Fetch the current authenticated recruiter. |
| `POST /recruiter/invites` | Admin-only recruiter invite creation. |
| `GET /recruiter/invites` | Admin-only recruiter invite list. |
| `GET /recruiter/invites/{token}` | Public lookup for recruiter signup invite metadata. |
| `POST /jobs` | Create a job. |
| `GET /jobs` | List jobs. |
| `GET /jobs/{job_id}` | Get job details. |
| `PATCH /jobs/{job_id}` | Update/archive job metadata. |
| `DELETE /jobs/{job_id}` | Delete a job and associated job data after guarded confirmation. |
| `GET /jobs/{job_id}/outcomes` | List outcomes under a job. |
| `POST /outcomes` | Create an outcome under a job. |
| `PATCH /outcomes/{outcome_id}` | Edit outcome and regenerate its stale report state. |
| `DELETE /outcomes/{outcome_id}` | Delete an outcome and associated evaluations/proofs. |
| `POST /jobs/{job_id}/invites` | Create an invite link. |
| `GET /jobs/{job_id}/invites` | List invites and submissions. |
| `DELETE /invites/{invite_id}` | Revoke/delete an invite. |
| `DELETE /submissions/{submission_id}` | Delete a candidate submission. |
| `POST /jobs/{job_id}/evaluations/queue` | Queue background evaluation. |
| `GET /jobs/{job_id}/evaluations/progress` | Read job-scoped evaluation progress. |
| `GET /analytics/metrics` | Recruiter-scoped or admin-wide analytics dashboard metrics. |
| `GET /analytics/decisions` | Recruiter-scoped or admin-wide decision history. |
| `GET /admin/signal-weights` | Admin-only signal weight view. |
| `GET /admin/weight-history` | Admin-only signal weight learning history. |
| `GET /admin/task-weight-history` | Admin-only task learning history. |
| `GET /admin/audit-logs` | Admin-only audit logs. |
| `GET /admin/llm-logs` | Admin-only LLM interaction logs. |
| `POST /plugin/suggest-tasks` | Generate outcome signals. |
| `POST /plugin/github/repos/select` | Select relevant repositories. |
| `GET /plugin/leetcode/{username}` | Fetch real LeetCode stats. |
| `POST /plugin/evaluate` | Run outcome evaluation. |
| `GET /plugin/status/{job_id}` | Fetch evaluation status. |
| `GET /metrics` | JSON metrics. |
| `GET /metrics/prometheus` | Prometheus text metrics. |

---

## Design Principles

SignalStack is built around five product principles:

1. **Proof beats promises.** Evaluate real work.
2. **Evidence beats vibes.** Every score should point to inspectable artifacts.
3. **Uncertainty should be visible.** Confidence, verification, and risk flags are first-class.
4. **Early candidates deserve fairness.** Personal projects should not be judged like enterprise systems by default.
5. **Recruiters need decisions, not dashboards.** The UI should move from job to candidates to evidence to decision quickly.

---

## Roadmap

- Realtime evaluation updates via SSE or WebSockets.
- Richer repo diff and commit timeline views.
- Per-outcome calibration controls.
- Evaluation replay and comparison snapshots.
- Organization-level analytics and hiring quality metrics.
- Pluggable evidence sources beyond GitHub and LeetCode.
- Stronger organization/team permissions beyond the current admin/recruiter split.
- Evidence-quality regression suite for common false-positive repo patterns.

---

## License

Proprietary. All rights reserved.

---

**SignalStack helps hiring teams replace resume guessing with inspectable proof-of-work evaluation.**
