from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException
import datetime
from app.models.job import Job
from app.models.job_candidate import JobCandidate
import uuid


class ShortlistService:
    """
    Manages candidate shortlisting and job closure based on finalized shortlist.
    """
    
    @staticmethod
    def apply_to_job(
        db: Session,
        job_id: str,
        candidate_id: str
    ) -> JobCandidate:
        """
        Candidate applies for a job.
        """
        # Get job
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check if accepting applications
        if not job.is_accepting_applications:
            raise HTTPException(
                status_code=400,
                detail=f"Job '{job.title}' is not accepting applications (status: {job.status}, applications_open: {job.applications_open})"
            )
        
        # Check if already applied
        existing = db.query(JobCandidate).filter(
            JobCandidate.job_id == job_id,
            JobCandidate.candidate_id == candidate_id
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Already applied to this job")
        
        # Create application
        application = JobCandidate(
            id=str(uuid.uuid4()),
            job_id=job_id,
            candidate_id=candidate_id,
            status="applied",
            applied_at=datetime.datetime.utcnow()
        )
        
        db.add(application)
        db.commit()
        db.refresh(application)
        
        return application
    
    @staticmethod
    def evaluate_candidate(
        db: Session,
        job_candidate_id: str,
        evaluation_score: float,
        outcome_coverage: float,
        evaluation_data: dict = None
    ) -> JobCandidate:
        """
        Store evaluation results for a candidate.
        Note: Evaluation happens regardless of job capacity.
        """
        candidate = db.query(JobCandidate).filter(JobCandidate.id == job_candidate_id).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Job candidate not found")
        
        # Update evaluation results
        candidate.status = "evaluated"
        candidate.evaluation_score = evaluation_score
        candidate.outcome_coverage = outcome_coverage
        candidate.evaluation_data = evaluation_data
        candidate.evaluated_at = datetime.datetime.utcnow()
        
        db.commit()
        db.refresh(candidate)
        
        return candidate
    
    @staticmethod
    def generate_shortlist(
        db: Session,
        job_id: str,
        auto_select: bool = True
    ) -> dict:
        """
        Generate recommended shortlist based on scores.
        Auto-selects top N candidates if auto_select=True.
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get all evaluated candidates, sorted by score
        candidates = db.query(JobCandidate).filter(
            JobCandidate.job_id == job_id,
            JobCandidate.status == "evaluated"
        ).order_by(desc(JobCandidate.evaluation_score)).all()
        
        shortlist_size = job.shortlist_size
        
        if auto_select:
            # Auto-select top N
            for i, candidate in enumerate(candidates):
                if i < shortlist_size:
                    candidate.status = "shortlisted"
                    candidate.shortlisted_at = datetime.datetime.utcnow()
            
            db.commit()
        
        # Return recommendation
        recommended = candidates[:shortlist_size]
        alternatives = candidates[shortlist_size:]
        
        return {
            "shortlist_size": shortlist_size,
            "total_positions": job.total_positions,
            "multiplier": job.shortlist_multiplier,
            "recommended_candidates": [
                {
                    "id": c.id,
                    "candidate_id": c.candidate_id,
                    "score": c.evaluation_score,
                    "status": c.status
                }
                for c in recommended
            ],
            "alternative_candidates": [
                {
                    "id": c.id,
                    "candidate_id": c.candidate_id,
                    "score": c.evaluation_score,
                    "status": c.status
                }
                for c in alternatives
            ]
        }
    
    @staticmethod
    def update_shortlist(
        db: Session,
        job_id: str,
        shortlisted_candidate_ids: list
    ) -> dict:
        """
        Manually update shortlist selection (recruiter edit).
        """
        # Get all evaluated candidates for this job
        candidates = db.query(JobCandidate).filter(
            JobCandidate.job_id == job_id,
            JobCandidate.status.in_(["evaluated", "shortlisted"])
        ).all()
        
        # Update statuses
        for candidate in candidates:
            if candidate.id in shortlisted_candidate_ids:
                candidate.status = "shortlisted"
                if not candidate.shortlisted_at:
                    candidate.shortlisted_at = datetime.datetime.utcnow()
            else:
                candidate.status = "evaluated"
                candidate.shortlisted_at = None
        
        db.commit()
        
        return {"success": True, "shortlisted_count": len(shortlisted_candidate_ids)}
    
    @staticmethod
    def finalize_shortlist(
        db: Session,
        job_id: str
    ) -> dict:
        """
        Finalize shortlist and close applications.
        This is the ONLY way a job status becomes "closed".
        """
        # Get job with lock
        job = db.query(Job).filter(Job.id == job_id).with_for_update().first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status != "active":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot finalize: Job status is '{job.status}' (must be 'active')"
            )
        
        # Get shortlisted candidates
        shortlisted = db.query(JobCandidate).filter(
            JobCandidate.job_id == job_id,
            JobCandidate.status == "shortlisted"
        ).all()
        
        if len(shortlisted) == 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot finalize: No candidates shortlisted"
            )
        
        # Close applications and update status
        job.applications_open = False
        job.status = "closed"
        job.updated_at = datetime.datetime.utcnow()
        
        db.commit()
        db.refresh(job)
        
        return {
            "success": True,
            "job_id": job.id,
            "job_title": job.title,
            "shortlisted_count": len(shortlisted),
            "message": f"Shortlist finalized. {len(shortlisted)} candidates ready for interviews."
        }
