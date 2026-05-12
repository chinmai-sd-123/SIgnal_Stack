import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config.config import config
from app.config.database import Base, SessionLocal, engine
import app.models as models
from app.models.job import Job
from app.models.outcome import Outcome
from app.models.recruiter import Recruiter
from app.models.task import Task
from app.services.auth import hash_password
from app.services.schema_guard import ensure_runtime_schema
from app.utils.slug_utils import slugify
from app.utils.time_utils import utc_now


DEMO_JOB_ID = "demo-clickpost-ai-engineer"


def ensure_columns(db):
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema(engine)
    db.commit()


def upsert_recruiter(db, email, password, role, name):
    email = email.strip().lower()
    recruiter = db.query(Recruiter).filter(Recruiter.email == email).first()
    if not recruiter:
        recruiter = Recruiter(
            id=str(uuid.uuid4()),
            email=email,
            password=hash_password(password),
            role=role,
            name=name,
        )
        db.add(recruiter)
    else:
        recruiter.password = hash_password(password)
        recruiter.role = role
        recruiter.name = recruiter.name or name
    db.flush()
    return recruiter


def seed_clickpost_job(db, recruiter):
    existing = db.query(Job).filter(Job.id == DEMO_JOB_ID).first()
    if existing:
        existing.recruiter_id = recruiter.id
        return existing

    job = Job(
        id=DEMO_JOB_ID,
        recruiter_id=recruiter.id,
        title="AI Engineer - Intern",
        description=(
            "Build applied AI systems for logistics operations: productionize AI prototypes, "
            "build copilots and internal search, create agents and automation workflows, "
            "and add prompt evaluation, feedback loops, queues, monitoring, and observability."
        ),
        company="ClickPost",
        location="Bangalore [In-Office]",
        category="Software Engineering",
        job_type="Internship",
        currency="INR",
        slug=f"ai-engineer-intern-clickpost-{DEMO_JOB_ID[-8:]}",
        company_slug=slugify("ClickPost"),
        location_slug=slugify("Bangalore"),
        category_slug=slugify("Software Engineering"),
        status="active",
        created_at=utc_now(),
        last_refreshed_at=utc_now(),
        required_languages=["Python", "JavaScript"],
    )
    db.add(job)

    outcomes = [
        (
            "Productionize AI Backend Services",
            "Candidate can turn an AI prototype, script, or notebook into a working backend service.",
            [
                "FastAPI or Flask API exposing AI functionality",
                "OpenAI/Claude/Gemini client integration with configurable credentials",
                "Background jobs, retries, or queue-safe processing",
            ],
        ),
        (
            "Build RAG or Internal Search Systems",
            "Candidate can build retrieval/search workflows over documents, logs, configs, or operational data.",
            [
                "Document ingestion, chunking, or indexing pipeline",
                "Embedding/vector search or retrieval integration",
                "Grounded answer generation with source/context handling",
            ],
        ),
        (
            "Create AI Agents and Workflow Automations",
            "Candidate can build useful automations or agentic workflows for operations/support/debugging.",
            [
                "Tool/API calling or multi-step agent workflow",
                "Error handling and safe execution boundaries",
                "Useful output for operations, support, analytics, or RCA",
            ],
        ),
        (
            "Build Evaluation, Feedback, and Observability Loops",
            "Candidate can measure, monitor, and improve AI behavior in production-like systems.",
            [
                "Prompt or output evaluation logic",
                "Feedback capture or learning loop",
                "Latency, token, cost, cache, or failure metrics",
            ],
        ),
    ]

    for outcome_index, (title, description, tasks) in enumerate(outcomes, start=1):
        outcome = Outcome(
            id=f"{DEMO_JOB_ID}-outcome-{outcome_index}",
            job_id=job.id,
            title=title,
            description=description,
            version=1,
            status="active",
            company=job.company,
            location=job.location,
            category=job.category,
            job_type=job.job_type,
        )
        db.add(outcome)
        for task_index, task_name in enumerate(tasks, start=1):
            db.add(Task(
                id=f"{outcome.id}-task-{task_index}",
                outcome_id=outcome.id,
                name=task_name,
                priority="High" if task_index <= 2 else "Medium",
                weight=0.4 if task_index == 1 else 0.3,
                version=1,
            ))

    return job


def main():
    db = SessionLocal()
    try:
        ensure_columns(db)
        admin_email = config.ADMIN_EMAIL or "admin@signalstack.dev"
        admin = upsert_recruiter(db, admin_email, "Admin@12345", "admin", "SignalStack Admin")
        demo = upsert_recruiter(
            db,
            config.DEMO_RECRUITER_EMAIL,
            config.DEMO_RECRUITER_PASSWORD,
            "recruiter",
            "Demo Recruiter",
        )
        job = seed_clickpost_job(db, demo)
        db.commit()
        print({
            "admin_email": admin.email,
            "admin_password": "Admin@12345",
            "demo_email": demo.email,
            "demo_password": config.DEMO_RECRUITER_PASSWORD,
            "demo_job_id": job.id,
        })
    finally:
        db.close()


if __name__ == "__main__":
    main()
