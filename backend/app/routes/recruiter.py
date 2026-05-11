from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.recruiter import Recruiter
from app.schemas.recruiter import RecruiterCreate, RecruiterResponse, RecruiterLogin

router = APIRouter(prefix="/recruiter", tags=["Recruiter"])

@router.post("/login", response_model=RecruiterResponse)
def login_recruiter(login_data: RecruiterLogin, db: Session = Depends(get_db)):
    # Check if recruiter exists
    recruiter = db.query(Recruiter).filter(Recruiter.email == login_data.email).first()
    
    if not recruiter:
        # Create new recruiter handling
        # For this flow, since we removed Name from login, we create with just email
        # Ideally we should have a separate signup, but to keep flow simple:
        recruiter = Recruiter(
            email=login_data.email,
            password=login_data.password, # In production, HASH THIS
            name="" # Default empty name
        )
        db.add(recruiter)
        db.commit()
        db.refresh(recruiter)
    else:
        # Verify password
        if recruiter.password != login_data.password:
             raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return recruiter
