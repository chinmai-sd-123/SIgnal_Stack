from typing import List, Optional

from sqlalchemy.orm import Session
import app.models as models
import app.schemas as schemas
from app.config.config import config
from app.services import crud

class OutcomePipeline:
    def __init__(self, db: Session):
        self.db = db

    def create_outcome(self, outcome: schemas.OutcomeCreate) -> models.Outcome:
        from app.utils.slug_utils import slugify, generate_seo_slug, parse_location, generate_location_slug
        
        # 1. Generate SEO Slugs
        final_slug = generate_seo_slug(outcome.title, outcome.company)
        category_slug = slugify(outcome.category)
        subcategory_slug = slugify(outcome.subcategory) if outcome.subcategory else None
        company_slug = slugify(outcome.company)
        
        # 2. Parse Location
        city, state = parse_location(outcome.location)
        location_slug = generate_location_slug(city, state)
        
        # 3. Construct Public URL (using a configurable domain in real prod, here localhost)
        # We can also store this as relative or absolute.
        # For SEO, absolute is safer for meta tags.
        base_url = (config.PUBLIC_BASE_URL or "http://localhost:3000").rstrip("/")
        public_url = f"{base_url}/jobs/view/{final_slug}"
        
        # 0. Check for "Save as Template" Flag (Recursive Creation)
        if outcome.save_as_template and not outcome.is_template:
            # 1. Create the Master Template first
            template_create = outcome.copy()
            template_create.save_as_template = False
            template_create.is_template = 1
            template_create.source_template_id = None
            
            # Recursively create the template
            # We don't link it to a job_id (it's a master)
            master_template = crud.create_outcome(self.db, template_create, job_id="template_master")
            
            # 2. Now Create the Instance linked to this new template
            # We use the instantiation logic to ensure consistency
            from app.services import crud as service_crud
            db_outcome = service_crud.instantiate_outcome_from_template(
                self.db, 
                template_id=master_template.id, 
                target_job_id=outcome.job_id
            )
            
            # Update SEO fields for the instance since instantiation doesn't do it
            db_outcome.slug = final_slug
            db_outcome.category_slug = category_slug
            db_outcome.subcategory_slug = subcategory_slug
            db_outcome.company_slug = company_slug
            db_outcome.location_slug = location_slug
            db_outcome.public_url = public_url
            self.db.add(db_outcome)
            self.db.commit()
            
            return db_outcome

        # 4. Create in DB via CRUD (Standard path)
        db_outcome = crud.create_outcome(
            self.db, 
            outcome,
            job_id=outcome.job_id,
            slug=final_slug,
            category_slug=category_slug,
            subcategory_slug=subcategory_slug,
            company_slug=company_slug,
            location_slug=location_slug,
            city=city,
            state=state,
            public_url=public_url
        )
        
        return db_outcome

    def get_outcome(self, outcome_id: str) -> Optional[models.Outcome]:
        return crud.get_outcome(self.db, outcome_id)

    def get_outcome_by_slug(self, slug: str) -> Optional[models.Outcome]:
        return crud.get_outcome_by_slug(self.db, slug)
