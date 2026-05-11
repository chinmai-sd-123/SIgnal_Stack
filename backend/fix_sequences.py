import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.config.database import Base
import app.models

load_dotenv()
pg_url = os.getenv("DATABASE_URL")
engine = create_engine(pg_url)

with engine.connect() as conn:
    for table in Base.metadata.sorted_tables:
        if "id" in table.columns and str(table.columns["id"].type) == "INTEGER":
            try:
                query = text(f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), coalesce(max(id), 1), max(id) IS NOT null) FROM {table.name};")
                conn.execute(query)
                conn.commit()
                print(f"Reset sequence for {table.name}")
            except Exception as e:
                print(f"Skipping {table.name}: {e}")

