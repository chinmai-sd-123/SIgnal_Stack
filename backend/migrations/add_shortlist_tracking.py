"""
Migration: Add shortlist tracking and candidate status
"""
import sys
import os

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.config.database import engine


def upgrade():
    """Add shortlist fields and JobCandidate table"""
    with engine.connect() as conn:
        print("Starting migration...")
        
        # Update jobs table
        print("Adding applications_open column...")
        conn.execute(text("""
            ALTER TABLE jobs 
            ADD COLUMN applications_open INTEGER DEFAULT 1 NOT NULL
        """))
        
        print("Adding total_positions column...")
        conn.execute(text("""
            ALTER TABLE jobs 
            ADD COLUMN total_positions INTEGER DEFAULT 1 NOT NULL
        """))
        
        print("Adding shortlist_multiplier column...")
        conn.execute(text("""
            ALTER TABLE jobs 
            ADD COLUMN shortlist_multiplier REAL DEFAULT 3.0 NOT NULL
        """))
        
        print("Adding updated_at column...")
        conn.execute(text("""
            ALTER TABLE jobs 
            ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """))
        
        # Create job_candidates table
        print("Creating job_candidates table...")
        conn.execute(text("""
            CREATE TABLE job_candidates (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                status TEXT DEFAULT 'applied' NOT NULL,
                evaluation_score REAL,
                outcome_coverage REAL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                evaluated_at TIMESTAMP,
                shortlisted_at TIMESTAMP,
                evaluation_data TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
                UNIQUE (job_id, candidate_id)
            )
        """))
        
        print("Creating indexes...")
        conn.execute(text("""
            CREATE INDEX idx_job_candidates_job_id ON job_candidates(job_id)
        """))
        
        conn.execute(text("""
            CREATE INDEX idx_job_candidates_status ON job_candidates(status)
        """))
        
        conn.commit()
        print("✅ Migration complete: shortlist tracking added")


def downgrade():
    """Remove shortlist tracking"""
    with engine.connect() as conn:
        print("Rolling back migration...")
        
        # Drop job_candidates table
        conn.execute(text("DROP TABLE IF EXISTS job_candidates"))
        
        # Remove columns from jobs (SQLite doesn't support DROP COLUMN easily)
        print("⚠️  Note: SQLite doesn't support DROP COLUMN. Manual intervention needed.")
        print("   Or create new jobs table and migrate data.")
        
        conn.commit()
        print("✅ Rollback complete")


if __name__ == "__main__":
    print("=" * 60)
    print("SHORTLIST TRACKING MIGRATION")
    print("=" * 60)
    upgrade()
