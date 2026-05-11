"""
Seed script for outcome templates.

This creates initial templates for 3 common roles:
- Software Engineer
- Backend Developer  
- Frontend Developer

Each template contains 2-3 pre-written outcomes that recruiters can customize.

Usage:
    python seed_outcome_templates.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.config.database import SessionLocal, engine
from app.models import Base
from app.models.outcome_template import OutcomeTemplate
import uuid


def seed_templates():
    """Seed the database with initial outcome templates."""
    db = SessionLocal()
    
    try:
        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine)
        
        templates = [
            {
                "id": str(uuid.uuid4()),
                "role_name": "Software Engineer",
                "category_slug": "software-engineering",
                "outcomes": [
                    {
                        "title": "Feature Development & Delivery",
                        "description": "Design, build, and ship production-ready features that solve user problems. Demonstrate ability to translate requirements into working code, write tests, and deploy to production with minimal oversight.",
                        "default_weight": 0.35
                    },
                    {
                        "title": "Code Quality & Maintainability",
                        "description": "Write clean, well-documented, and maintainable code that follows best practices. Show evidence of code reviews, refactoring, and technical debt management.",
                        "default_weight": 0.35
                    },
                    {
                        "title": "Collaboration & Execution",
                        "description": "Work effectively with cross-functional teams (product, design, QA). Demonstrate ability to unblock others, communicate technical decisions, and ship on time.",
                        "default_weight": 0.30
                    }
                ]
            },
            {
                "id": str(uuid.uuid4()),
                "role_name": "Backend Developer",
                "category_slug": "software-engineering",
                "outcomes": [
                    {
                        "title": "API & System Design",
                        "description": "Design and implement scalable, well-documented APIs. Show evidence of RESTful/GraphQL design, API versioning, and service architecture decisions.",
                        "default_weight": 0.40
                    },
                    {
                        "title": "Data Handling & Performance",
                        "description": "Efficiently manage data storage, retrieval, and processing. Demonstrate database design, query optimization, caching strategies, and performance tuning.",
                        "default_weight": 0.35
                    },
                    {
                        "title": "Reliability & Operations",
                        "description": "Build reliable systems with monitoring, logging, and error handling. Show evidence of production incident resolution, uptime improvements, and operational excellence.",
                        "default_weight": 0.25
                    }
                ]
            },
            {
                "id": str(uuid.uuid4()),
                "role_name": "Frontend Developer",
                "category_slug": "software-engineering",
                "outcomes": [
                    {
                        "title": "UI Development & Interaction",
                        "description": "Build responsive, pixel-perfect user interfaces that match designs. Demonstrate component architecture, state management, and interactive user experiences.",
                        "default_weight": 0.40
                    },
                    {
                        "title": "Performance & Accessibility",
                        "description": "Optimize frontend performance (load times, bundle size, rendering). Ensure accessibility standards (WCAG) and cross-browser compatibility.",
                        "default_weight": 0.30
                    },
                    {
                        "title": "Product Collaboration",
                        "description": "Work closely with designers and product managers to ship user-facing features. Show evidence of UX improvements, A/B testing, and user feedback integration.",
                        "default_weight": 0.30
                    }
                ]
            }
        ]
        
        # Check if templates already exist
        existing_count = db.query(OutcomeTemplate).count()
        if existing_count > 0:
            print(f"[!] Templates already exist ({existing_count} found). Skipping seed.")
            return
        
        # Insert templates
        for template_data in templates:
            template = OutcomeTemplate(**template_data)
            db.add(template)
        
        db.commit()
        print(f"[+] Successfully seeded {len(templates)} outcome templates!")
        
        # Print summary
        for template_data in templates:
            print(f"\n  - {template_data['role_name']}")
            for outcome in template_data['outcomes']:
                print(f"    * {outcome['title']}")
        
    except Exception as e:
        print(f"[X] Error seeding templates: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("[*] Seeding outcome templates...")
    seed_templates()
