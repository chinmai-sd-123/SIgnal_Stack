import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.config.database import engine, Base
import app.models

load_dotenv()

print("WARNING: This will drop all tables in your Postgres database and recreate them!")
print(f"Target DB: {engine.url}")
response = input("Are you sure? Type 'YES' to continue: ")

if response.strip() == "YES":
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Recreating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Database cleared successfully!")
else:
    print("Aborted.")

