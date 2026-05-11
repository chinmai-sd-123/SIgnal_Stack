from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config.database import engine
import app.models as models

# Create tables
models.Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events."""
    # Startup
    print("[*] Starting SignalStack API...")
    
    # Initialize secrets
    from app.services.secrets import init_secrets
    init_secrets(".env")
    
    # Start worker queue
    from app.services.worker_queue import init_workers
    init_workers()
    
    # Initialize cache
    from app.services.cache import cache
    print(f"Cache initialized: {'Redis' if cache.redis_client else 'In-memory'}")

    # Start durable Redis-backed job evaluation worker when Redis is available.
    from app.services.bulk_evaluation_service import init_redis_job_evaluation_worker
    if init_redis_job_evaluation_worker():
        print("Job evaluation queue initialized: Redis")
    else:
        print("Job evaluation queue initialized: in-memory")
    
    print("[+] SignalStack API ready!")
    
    yield  # App runs here
    
    # Shutdown
    print("[-] Shutting down SignalStack API...")
    from app.services.bulk_evaluation_service import stop_redis_job_evaluation_worker
    stop_redis_job_evaluation_worker(timeout=5)
    from app.services.worker_queue import worker_queue
    worker_queue.stop(wait=True, timeout=5)
    print("[!] Goodbye!")

app = FastAPI(title="SignalStack API", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def debug_exception_handler(request, exc):
    import traceback
    print(f"Global Exception: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"message": str(exc)},
    )

from app.routes import outcome, task_decomposer, signal_extractor, evaluator, feedback, public_jobs, job

# Pipeline Routers
app.include_router(outcome.router)
app.include_router(task_decomposer.router)
app.include_router(signal_extractor.router)
app.include_router(evaluator.router)
app.include_router(feedback.router)
app.include_router(public_jobs.router)
app.include_router(job.router)
from app.routes import analytics
app.include_router(analytics.router, prefix="/analytics")

from app.routes import repo
app.include_router(repo.router)

# Outcome Templates
from app.routes import outcome_templates
app.include_router(outcome_templates.router)

# Snapshot routes
from app.routes import snapshot
app.include_router(snapshot.router)

# Invite routes
from app.routes import invite
app.include_router(invite.router)

# Metrics endpoint
from app.monitoring import get_all_metrics, get_prometheus_format
from fastapi.responses import PlainTextResponse

@app.get("/metrics")
def metrics():
    """Prometheus-compatible metrics endpoint."""
    return get_all_metrics()

@app.get("/metrics/prometheus", response_class=PlainTextResponse)
def prometheus_metrics():
    """Prometheus text format metrics."""
    return get_prometheus_format()

# Admin LLM Logs endpoint
@app.get("/admin/evaluations/{evaluation_id}/llm_logs")
def get_evaluation_llm_logs(evaluation_id: int):
    """Get LLM logs for a specific evaluation."""
    from app.services.llm_summarizer import get_llm_logs_for_evaluation
    from app.config.database import SessionLocal
    db = SessionLocal()
    try:
        logs = get_llm_logs_for_evaluation(db, evaluation_id)
        return {"evaluation_id": evaluation_id, "logs": logs}
    finally:
        db.close()

# Weight History endpoint
@app.get("/admin/weight-history")
def get_weight_history(signal_name: str = None, limit: int = 50):
    """Get weight change history for audit."""
    from app.services.weight_updater import get_weight_history as get_history
    from app.config.database import SessionLocal
    db = SessionLocal()
    try:
        history = get_history(db, signal_name, limit)
        return {"history": history}
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
