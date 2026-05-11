from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.config.database import get_db
from app.models.job import Job
import app.schemas.job as job_schemas

router = APIRouter(prefix="/api/public", tags=["Public SEO Jobs"])

@router.get("/jobs", response_model=List[job_schemas.JobResponse])
def get_all_public_jobs(db: Session = Depends(get_db)):
    """Fetch all open jobs for the public board."""
    return db.query(Job).filter(Job.status == "active").order_by(Job.created_at.desc()).all()

@router.get("/jobs/view/{slug}", response_model=job_schemas.JobResponse)
def get_job_by_seo_slug(slug: str, db: Session = Depends(get_db)):
    """Fetch a single job by its unique SEO slug."""
    job = db.query(Job).filter(Job.slug == slug).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.get("/jobs/{slug}")
def smart_job_search(slug: str, db: Session = Depends(get_db)):
    """
    Detects if slug is a category or a location and returns filtered jobs.
    Location slugs start with 'in-'.
    """
    if slug.startswith("in-"):
        # Search by Location Slug
        jobs = db.query(Job).filter(
            Job.location_slug == slug,
            Job.status == "active"
        ).all()
        return {"type": "location", "slug": slug, "jobs": jobs}
    else:
        # Alias mapping for better UX/SEO
        aliases = {
            "product-manager": "product-management",
            "pm": "product-management",
            "software-engineer": "software-engineering",
            "swe": "software-engineering",
            "data-science": "data-science-analytics"
        }
        search_slug = aliases.get(slug, slug)

        # Search by Subcategory Slug (more specific)
        jobs = db.query(Job).filter(
            Job.subcategory_slug == search_slug,
            Job.status == "active"
        ).all()
        
        if not jobs:
            # Search by Category Slug
            jobs = db.query(Job).filter(
                Job.category_slug == search_slug,
                Job.status == "active"
            ).all()
            if jobs:
                return {"type": "category", "slug": search_slug, "jobs": jobs}
            
            # Search by Company Slug
            jobs = db.query(Job).filter(
                Job.company_slug == search_slug,
                Job.status == "active"
            ).all()
            if jobs:
                return {"type": "company", "slug": search_slug, "jobs": jobs}

        return {"type": "subcategory", "slug": search_slug, "jobs": jobs}

@router.get("/job-counts")
def get_job_counts(db: Session = Depends(get_db)):
    """Return counts for SEO logic (thresholds)."""
    from sqlalchemy import func
    counts = db.query(
        Job.category_slug, 
        func.count(Job.id)
    ).group_by(Job.category_slug).all()
    return {c[0]: c[1] for c in counts if c[0]}

@router.get("/sitemap-data")
def get_sitemap_data(db: Session = Depends(get_db)):
    """Return data needed for dynamic sitemap generation."""
    jobs = db.query(Job).filter(Job.status == "active").all()
    # Unique categories and subcategories
    categories = db.query(Job.category_slug).filter(Job.status == "active").distinct().all()
    locations = db.query(Job.location_slug).filter(Job.status == "active").distinct().all()
    
    return {
        "jobs": [{"slug": j.slug, "lastmod": j.last_refreshed_at} for j in jobs],
        "categories": [c[0] for c in categories if c[0]],
        "locations": [l[0] for l in locations if l[0]]
    }
