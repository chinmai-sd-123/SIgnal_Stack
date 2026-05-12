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
| Repository analysis | Reads source files, folders, manifests, commits, README files, and selected snippets. |
| Repo selection | Selects likely relevant repositories from a GitHub profile using job context. |
| Evidence grounding | Grounds AI assessments in concrete code snippets and deterministic facts. |
| Scoring | Separates capability, evidence confidence, verification, and production readiness. |
| Queueing | Supports Redis-backed background evaluation for high-volume candidate batches. |
| Review UX | Shows ranked candidates, evidence cards, skill dimensions, and decision actions. |
| Learning loop | Captures feedback and adjusts future signal weights. |

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

The frontend is job-centric: recruiters manage jobs, outcomes, invite links, candidates, evaluation progress, and final decisions from one workflow.

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

---

## Evidence Grounding

The evaluator is designed to avoid hallucinated assessments:

- AI assessment receives outcome title, outcome description, and signal text.
- Evidence is selected from actual repository files, code snippets, manifests, README files, commits, and deterministic facts.
- Resume links are treated as candidate context, not proof of code implementation.
- Evidence snippets are scoped to the candidate and submission so one candidate's repository does not leak into another report.
- The UI exposes key evidence and full snippets so reviewers can inspect the basis for each score.
- If no relevant code or artifact evidence exists, score strength is capped.

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

The frontend shows job-scoped queue progress, not global queue noise from another job.

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
| Deterministic signals | Computes tests, CI, manifests, authorship, frameworks, and repo facts without LLM calls. |
| Top-candidate deep evaluation | Screens all candidates first, then deep-evaluates the strongest candidates. |
| Redis queue | Prevents duplicate queued work and keeps processing durable. |

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

Small but important source files are preserved as evidence instead of being drowned out by generic config files.

---

## Key Features

### Recruiter Workflow

- Create a job.
- Add one or more outcomes.
- Generate concise evaluation signals.
- Invite candidates with reusable public links.
- Review live application and evaluation progress.
- Compare ranked candidates.
- Inspect evidence.
- Proceed to interview or reject.
- Capture feedback for future weighting.

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
      services/            GitHub, Redis, LLM, queue, shortlist, LeetCode
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
JWT_SECRET=change-this-in-production
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
| `JWT_SECRET` | Production | Token signing secret. |
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
- Redis queue tested if changing evaluation processing.
- Evidence grounding tests updated if changing scoring or LLM prompts.
- Browser check completed for candidate application and job evaluation pages.

---

## Important API Surfaces

| Endpoint | Purpose |
| --- | --- |
| `POST /jobs` | Create a job. |
| `GET /jobs` | List jobs. |
| `GET /jobs/{job_id}` | Get job details. |
| `GET /jobs/{job_id}/outcomes` | List outcomes under a job. |
| `POST /jobs/{job_id}/invites` | Create an invite link. |
| `GET /jobs/{job_id}/invites` | List invites and submissions. |
| `POST /jobs/{job_id}/evaluations/queue` | Queue background evaluation. |
| `GET /jobs/{job_id}/evaluations/progress` | Read job-scoped evaluation progress. |
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
- Multi-recruiter authentication and role-based access.
- Evaluation replay and comparison snapshots.
- Organization-level analytics and hiring quality metrics.
- Pluggable evidence sources beyond GitHub and LeetCode.

---

## License

Proprietary. All rights reserved.

---

**SignalStack helps hiring teams replace resume guessing with inspectable proof-of-work evaluation.**
