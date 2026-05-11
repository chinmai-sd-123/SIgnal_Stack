import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Ensure we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config.database import Base
import app.models  # Ensure models are loaded

load_dotenv()

def port_data():
    sqlite_url = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'data', 'sql_app_v6.db')}"
    pg_url = os.getenv("DATABASE_URL")
    
    if not pg_url or not pg_url.startswith("postgresql"):
        print("Error: DATABASE_URL not found or not a PostgreSQL URL.")
        return
        
    print(f"Connecting to SQLite: {sqlite_url}")
    sqlite_engine = create_engine(sqlite_url)
    
    print(f"Connecting to PostgreSQL: {pg_url.split('@')[-1]}")
    pg_engine = create_engine(pg_url)
    
    with sqlite_engine.connect() as sqlite_conn:
        with pg_engine.connect() as pg_conn:
            for table in Base.metadata.sorted_tables:
                print(f"Porting table: {table.name}")
                
                if table.name == "outcomes":
                    # Ensure template_master job exists to satisfy foreign key constraints
                    try:
                        with pg_conn.begin():
                            pg_conn.execute(
                                text("INSERT INTO jobs (id, title, status) VALUES ('template_master', 'Template Master', 'active') ON CONFLICT DO NOTHING")
                            )
                    except Exception as e:
                        pass
                        
                rows = sqlite_conn.execute(table.select()).fetchall()
                if not rows:
                    print(f"  No data in {table.name}")
                    continue
                
                print(f"  Inserting {len(rows)} rows into {table.name}...")
                
                dicts = [dict(row._mapping) for row in rows]
                
                try:
                    with pg_conn.begin():
                        pg_conn.execute(table.insert().values(dicts))
                    print(f"  Successfully ported {table.name}")
                except Exception as e:
                    print(f"  Warning batch inserting into {table.name}. Falling back to individual inserts...")
                    success = 0
                    for d in dicts:
                        try:
                            with pg_conn.begin():
                                pg_conn.execute(table.insert().values(d))
                            success += 1
                        except Exception as e2:
                            pass
                    print(f"  Successfully ported {success}/{len(dicts)} rows individually into {table.name}")
                    
    print("\n✅ Data porting complete!")

if __name__ == "__main__":
    port_data()

