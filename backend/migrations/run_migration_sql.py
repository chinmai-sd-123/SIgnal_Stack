"""
Simple migration: Add shortlist tracking via SQL
Run this directly with: python migrations/run_migration_sql.py
"""
import sqlite3
import os

# Get database path (same as in app/config/database.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(BASE_DIR, "data", "sql_app_v6.db")

print(f"Connecting to database: {db_path}")

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Starting migration...")

try:
    # Add columns to jobs table (SQLite doesn't support non-constant defaults in ALTER TABLE)
    print("Adding applications_open column...")
    cursor.execute("ALTER TABLE jobs ADD COLUMN applications_open INTEGER DEFAULT 1 NOT NULL")
    
    print("Adding total_positions column...")
    cursor.execute("ALTER TABLE jobs ADD COLUMN total_positions INTEGER DEFAULT 1 NOT NULL")
    
    print("Adding shortlist_multiplier column...")
    cursor.execute("ALTER TABLE jobs ADD COLUMN shortlist_multiplier REAL DEFAULT 3.0 NOT NULL")
    
    print("Adding updated_at column (nullable to avoid SQLite limitation)...")
    cursor.execute("ALTER TABLE jobs ADD COLUMN updated_at TIMESTAMP")
    
    # Update existing rows to have current timestamp
    cursor.execute("UPDATE jobs SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
    
    # Create job_candidates table
    print("Creating job_candidates table...")
    cursor.execute("""
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
    """)
    
    print("Creating indexes...")
    cursor.execute("CREATE INDEX idx_job_candidates_job_id ON job_candidates(job_id)")
    cursor.execute("CREATE INDEX idx_job_candidates_status ON job_candidates(status)")
    
    # Commit changes
    conn.commit()
    print("✅ Migration complete: shortlist tracking added")
    
except sqlite3.OperationalError as e:
    error_msg = str(e).lower()
    if "duplicate column name" in error_msg or "already exists" in error_msg:
        print(f"⚠️  Already exists (skipping): {e}")
        # Still try to create the table if it doesn't exist
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_candidates (
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
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_candidates_job_id ON job_candidates(job_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_candidates_status ON job_candidates(status)")
            conn.commit()
            print("✅ Migration tables verified/created")
        except Exception as e2:
            print(f"Table creation also skipped: {e2}")
            conn.commit()
    else:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
    raise
finally:
    conn.close()
    print("Database connection closed")
