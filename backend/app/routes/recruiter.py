from datetime import timedelta
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from app.config.database import get_db
from app.config.config import config
from app.models.recruiter import Recruiter
from app.models.recruiter_invite import RecruiterInvite
from app.schemas.recruiter import (
    RecruiterAuthResponse,
    RecruiterInviteCreate,
    RecruiterInviteResponse,
    RecruiterLogin,
    RecruiterResponse,
    RecruiterSignup,
)
from app.services.auth import create_access_token, get_current_recruiter, hash_password, require_admin, verify_password
from app.utils.time_utils import utc_now

router = APIRouter(prefix="/recruiter", tags=["Recruiter"])


def _ensure_recruiter_columns(db: Session):
    columns = {column["name"] for column in inspect(db.bind).get_columns("recruiters")}
    if "role" not in columns:
        db.execute(text("ALTER TABLE recruiters ADD COLUMN role VARCHAR NOT NULL DEFAULT 'recruiter'"))
        db.commit()


def _auth_response(recruiter: Recruiter):
    return {
        "access_token": create_access_token(recruiter),
        "token_type": "bearer",
        "recruiter": recruiter,
    }


@router.post("/login", response_model=RecruiterAuthResponse)
def login_recruiter(login_data: RecruiterLogin, db: Session = Depends(get_db)):
    _ensure_recruiter_columns(db)
    email = str(login_data.email).strip().lower()
    recruiter = db.query(Recruiter).filter(Recruiter.email == email).first()
    
    if not recruiter:
        if not config.ADMIN_EMAIL or email != config.ADMIN_EMAIL:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account not found. Ask an admin for a recruiter invite.",
            )
        recruiter = Recruiter(
            email=email,
            password=hash_password(login_data.password),
            name="",
            role="admin",
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
    
    return _auth_response(recruiter)


@router.post("/signup", response_model=RecruiterAuthResponse)
def signup_recruiter(signup_data: RecruiterSignup, db: Session = Depends(get_db)):
    _ensure_recruiter_columns(db)
    email = str(signup_data.email).strip().lower()
    token = (signup_data.invite_token or "").strip()

    invite = db.query(RecruiterInvite).filter(RecruiterInvite.token == token).first()
    if not invite or invite.status != "active":
        raise HTTPException(status_code=400, detail="Invalid or expired invite")
    if invite.expires_at and invite.expires_at < utc_now():
        invite.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="Invite expired")
    if invite.email.lower() != email:
        raise HTTPException(status_code=400, detail="Invite email does not match")

    existing = db.query(Recruiter).filter(Recruiter.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Account already exists. Please log in.")

    recruiter = Recruiter(
        email=email,
        password=hash_password(signup_data.password),
        name=signup_data.name or invite.name or "",
        role="recruiter",
    )
    db.add(recruiter)
    db.flush()

    invite.status = "used"
    invite.used_at = utc_now()
    db.commit()
    db.refresh(recruiter)
    return _auth_response(recruiter)


@router.get("/me", response_model=RecruiterResponse)
def get_me(current: Recruiter = Depends(get_current_recruiter)):
    return current


@router.post("/invites", response_model=RecruiterInviteResponse)
def create_recruiter_invite(
    invite_data: RecruiterInviteCreate,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(require_admin),
):
    email = str(invite_data.email).strip().lower()
    existing_recruiter = db.query(Recruiter).filter(Recruiter.email == email).first()
    if existing_recruiter:
        raise HTTPException(status_code=409, detail="Recruiter account already exists")

    existing_invites = db.query(RecruiterInvite).filter(
        RecruiterInvite.email == email,
        RecruiterInvite.status == "active",
    ).all()
    for existing in existing_invites:
        existing.status = "revoked"

    invite = RecruiterInvite(
        email=email,
        name=invite_data.name,
        token=secrets.token_urlsafe(24),
        status="active",
        invited_by=current.id,
        expires_at=utc_now() + timedelta(days=14),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


@router.get("/invites", response_model=list[RecruiterInviteResponse])
def list_recruiter_invites(
    db: Session = Depends(get_db),
    current: Recruiter = Depends(require_admin),
):
    return db.query(RecruiterInvite).order_by(RecruiterInvite.created_at.desc()).limit(100).all()


@router.get("/invites/{token}", response_model=RecruiterInviteResponse)
def get_recruiter_invite(token: str, db: Session = Depends(get_db)):
    invite = db.query(RecruiterInvite).filter(RecruiterInvite.token == token).first()
    if not invite or invite.status != "active":
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite.expires_at and invite.expires_at < utc_now():
        invite.status = "expired"
        db.commit()
        raise HTTPException(status_code=404, detail="Invite expired")
    return invite
