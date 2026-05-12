from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from app.config.database import get_db
from app.config.config import config
from app.models.recruiter import Recruiter
from app.schemas.recruiter import RecruiterAuthResponse, RecruiterLogin, RecruiterResponse
from app.services.auth import create_access_token, get_current_recruiter, hash_password, verify_password

router = APIRouter(prefix="/recruiter", tags=["Recruiter"])


def _ensure_recruiter_columns(db: Session):
    columns = {column["name"] for column in inspect(db.bind).get_columns("recruiters")}
    if "role" not in columns:
        db.execute(text("ALTER TABLE recruiters ADD COLUMN role VARCHAR NOT NULL DEFAULT 'recruiter'"))
        db.commit()


@router.post("/login", response_model=RecruiterAuthResponse)
def login_recruiter(login_data: RecruiterLogin, db: Session = Depends(get_db)):
    _ensure_recruiter_columns(db)
    email = str(login_data.email).strip().lower()
    recruiter = db.query(Recruiter).filter(Recruiter.email == email).first()
    
    if not recruiter:
        role = "admin" if config.ADMIN_EMAIL and email == config.ADMIN_EMAIL else "recruiter"
        recruiter = Recruiter(
            email=email,
            password=hash_password(login_data.password),
            name="",
            role=role,
        )
        db.add(recruiter)
        db.commit()
        db.refresh(recruiter)
    else:
        if not verify_password(login_data.password, recruiter.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not recruiter.password.startswith("pbkdf2_sha256$"):
            recruiter.password = hash_password(login_data.password)
        if config.ADMIN_EMAIL and recruiter.email.lower() == config.ADMIN_EMAIL:
            recruiter.role = "admin"
        db.commit()
        db.refresh(recruiter)
    
    return {
        "access_token": create_access_token(recruiter),
        "token_type": "bearer",
        "recruiter": recruiter,
    }


@router.get("/me", response_model=RecruiterResponse)
def get_me(current: Recruiter = Depends(get_current_recruiter)):
    return current
