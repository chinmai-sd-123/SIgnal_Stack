from app.config.database import engine, Base
import app.models

def clean_database():
    print("  Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print(" All tables dropped.")
    
    print(" Recreating tables...")
    Base.metadata.create_all(bind=engine)
    print(" Database cleaned and initialized!")

if __name__ == "__main__":
    clean_database()
