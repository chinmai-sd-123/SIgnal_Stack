"""
Seed invite submissions for load-testing job evaluation.

Usage:
    python backend/seed_eval_candidates.py --job-id <job_id> --count 50
    python backend/seed_eval_candidates.py --job-id <job_id> --count 50 --queue

This creates InviteSubmission rows plus Proof rows for every existing outcome
under the job. It is intended for development/testing only.
"""

import argparse
import uuid

from app.config.database import SessionLocal
from app.models.invite import Invite, InviteSubmission
from app.models.job import Job
from app.services.bulk_evaluation_service import ensure_job_candidate, queue_job_evaluation
from app.services.submission_proof_service import create_proofs_for_submission, get_candidate_id
from app.utils.time_utils import utc_now


SAMPLE_REPOS = [
    "https://github.com/chinmai-sd-123/astronaut_space_health.git",
    "https://github.com/chinmai-sd-123/Intelligent-Customer-Support-Ticket-Classification.git",
    "https://github.com/chinmai-sd-123/titanic-survival-prediction.git",
    "https://github.com/chinmai-sd-123/Customer-Churn-Prediction.git",
    "https://github.com/chinmai-sd-123/Spam-message-detection.git",
]


def _get_or_create_seed_invite(db, job_id: str) -> Invite:
    invite = db.query(Invite).filter(
        Invite.job_id == job_id,
        Invite.token.like("seed-%"),
    ).first()
    if invite:
        return invite

    invite = Invite(
        id=str(uuid.uuid4()),
        token=f"seed-{uuid.uuid4()}",
        job_id=job_id,
        status="active",
        expires_at=utc_now().replace(year=utc_now().year + 1),
    )
    db.add(invite)
    db.flush()
    return invite


def seed_candidates(job_id: str, count: int, queue_after: bool = False) -> dict:
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        invite = _get_or_create_seed_invite(db, job_id)
        created_submissions = 0
        created_proofs = 0

        for index in range(1, count + 1):
            email = f"seed-candidate-{index:03d}@example.test"
            existing = db.query(InviteSubmission).filter(
                InviteSubmission.invite_id == invite.id,
                InviteSubmission.candidate_email == email,
            ).first()
            if existing:
                continue

            submission = InviteSubmission(
                id=str(uuid.uuid4()),
                invite_id=invite.id,
                job_id=job_id,
                candidate_name=f"Seed Candidate {index:03d}",
                candidate_email=email,
                github_username=f"seed-candidate-{index:03d}",
                repo_url=SAMPLE_REPOS[(index - 1) % len(SAMPLE_REPOS)],
                linkedin_url="",
                resume_url=f"https://example.test/resumes/seed-candidate-{index:03d}.pdf",
                leetcode_username="",
                context="Seeded load-test candidate for evaluation queue verification.",
                status="submitted",
            )
            db.add(submission)
            db.flush()

            created_submissions += 1
            created_proofs += create_proofs_for_submission(db, submission, job_id)
            ensure_job_candidate(db, job_id, get_candidate_id(submission), status="submitted")

        db.commit()

        task_id = None
        if queue_after and created_submissions:
            task_id = queue_job_evaluation(
                job_id,
                deep_limit=min(25, count),
                include_deep_evaluation=True,
            )

        return {
            "job_id": job_id,
            "invite_id": invite.id,
            "created_submissions": created_submissions,
            "created_proofs": created_proofs,
            "queue_task_id": task_id,
        }
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Seed candidates for evaluation testing.")
    parser.add_argument("--job-id", required=True, help="Existing job id")
    parser.add_argument("--count", type=int, default=50, help="Number of candidates to seed")
    parser.add_argument("--queue", action="store_true", help="Queue job evaluation after seeding")
    args = parser.parse_args()

    result = seed_candidates(args.job_id, args.count, queue_after=args.queue)
    print(result)


if __name__ == "__main__":
    main()
