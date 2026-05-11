from app.config.database import engine, Base
from app.models.task import TaskWeightHistory
from app.models.outcome import Outcome
# Import other models to ensure they are registered
import app.models

print("Creating all tables...")
try:
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")
except Exception as e:
    print(f"Error creating tables: {e}")
