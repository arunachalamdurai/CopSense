"""Feedback router with NLP sensitivity + duplicate prevention"""
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from typing import Optional
from backend.database import get_db
from backend.models.feedback import Feedback, FeedbackSensitivity
from backend.models.user import User, UserRole
from backend.auth.dependencies import get_current_user
from backend.ai.priority_engine import classify_feedback

router = APIRouter(prefix="/api/feedback", tags=["Citizen Feedback"])


class FeedbackCreate(BaseModel):
    station_id:    int
    officer_id:    int | None = None
    feedback_text: str
    feedback_type: str = "officer"   # officer | station | multiple
    rating:        int = 3
    is_anonymous:  bool = False

    @field_validator("feedback_text")
    @classmethod
    def text_required(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("Feedback text must be at least 10 characters")
        return v.strip()

    @field_validator("rating")
    @classmethod
    def rating_range(cls, v):
        if v < 1 or v > 5:
            raise ValueError("Rating must be between 1 and 5")
        return v

    @field_validator("feedback_type")
    @classmethod
    def valid_type(cls, v):
        if v not in ["officer", "station", "multiple"]:
            raise ValueError("feedback_type must be: officer | station | multiple")
        return v


def fb_dict(fb: Feedback, db) -> dict:
    from backend.models.station import Station
    from backend.models.user import User as UserM
    station = db.query(Station).filter(Station.id == fb.station_id).first()
    officer = db.query(UserM).filter(UserM.id == fb.officer_id).first() if fb.officer_id else None
    return {
        **{c.name: getattr(fb, c.name) for c in fb.__table__.columns},
        "station_name": station.name if station else None,
        "officer_name": officer.full_name if officer else None,
    }


@router.post("", status_code=201)
def submit_feedback(
    req:          FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    # Duplicate check: same citizen + officer + station within last 7 days
    dup_hash = hashlib.md5(
        f"{current_user.id}:{req.station_id}:{req.officer_id}:{req.feedback_text[:50]}".encode()
    ).hexdigest()
    if db.query(Feedback).filter(Feedback.duplicate_check_hash == dup_hash).first():
        raise HTTPException(status_code=409, detail="Duplicate feedback detected — you already submitted similar feedback recently")

    # NLP classification
    sensitivity_str, ai_score = classify_feedback(req.feedback_text, req.rating)
    sensitivity = FeedbackSensitivity(sensitivity_str)

    fb = Feedback(
        citizen_id          = current_user.id,
        station_id          = req.station_id,
        officer_id          = req.officer_id,
        feedback_text       = req.feedback_text,
        feedback_type       = req.feedback_type,
        rating              = req.rating,
        is_anonymous        = req.is_anonymous,
        sensitivity         = sensitivity,
        ai_score            = ai_score,
        duplicate_check_hash= dup_hash,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return {
        **fb_dict(fb, db),
        "ai_sensitivity": sensitivity_str,
        "ai_score":       ai_score,
        "alert_required": sensitivity_str in ["high", "critical"],
    }


@router.get("")
def list_feedback(
    page:       int = Query(1, ge=1),
    per_page:   int = Query(20, le=100),
    station_id: Optional[int] = None,
    sensitivity:Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db:         Session = Depends(get_db),
):
    q = db.query(Feedback)

    # Role-based visibility
    if current_user.role == UserRole.citizen:
        # Citizens see only their own
        q = q.filter(Feedback.citizen_id == current_user.id)
    elif current_user.role == UserRole.field_officer:
        raise HTTPException(status_code=403, detail="Field officers cannot view feedback")
    elif current_user.role == UserRole.station_officer:
        q = q.filter(Feedback.station_id == current_user.station_id)
    # district_head sees all
    elif station_id:
        q = q.filter(Feedback.station_id == station_id)

    if sensitivity:
        q = q.filter(Feedback.sensitivity == sensitivity)

    total = q.count()
    fbs   = q.order_by(Feedback.submitted_at.desc()).offset((page-1)*per_page).limit(per_page).all()
    return {"total": total, "data": [fb_dict(fb, db) for fb in fbs]}


@router.get("/stats")
def feedback_stats(
    current_user: User = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    from sqlalchemy import func
    q = db.query(Feedback)
    if current_user.role == UserRole.station_officer:
        q = q.filter(Feedback.station_id == current_user.station_id)
    elif current_user.role == UserRole.citizen:
        q = q.filter(Feedback.citizen_id == current_user.id)
    avg_rating = db.query(func.avg(Feedback.rating)).scalar() or 0
    return {
        "total":    q.count(),
        "critical": q.filter(Feedback.sensitivity == FeedbackSensitivity.critical).count(),
        "high":     q.filter(Feedback.sensitivity == FeedbackSensitivity.high).count(),
        "medium":   q.filter(Feedback.sensitivity == FeedbackSensitivity.medium).count(),
        "low":      q.filter(Feedback.sensitivity == FeedbackSensitivity.low).count(),
        "avg_rating": round(float(avg_rating), 2),
    }
