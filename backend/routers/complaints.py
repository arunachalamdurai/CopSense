"""Complaints router with AI priority classification"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.complaint import Complaint, ComplaintStatus, ComplaintPriority
from backend.models.user import User, UserRole
from backend.auth.dependencies import get_current_user
from backend.ai.priority_engine import classify_complaint

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])


class ComplaintCreate(BaseModel):
    citizen_name:   str
    phone:          str
    complaint_type: str
    description:    str
    location:       str
    station_id:     int
    lat:            float | None = None
    lng:            float | None = None

    @field_validator("citizen_name", "phone", "complaint_type", "description", "location")
    @classmethod
    def required(cls, v, info):
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} is required")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def phone_length(cls, v):
        digits = ''.join(c for c in v if c.isdigit())
        if len(digits) < 10:
            raise ValueError("Phone number must be at least 10 digits")
        return v

    @field_validator("description")
    @classmethod
    def desc_length(cls, v):
        if len(v.strip()) < 10:
            raise ValueError("Description must be at least 10 characters")
        return v


class ComplaintStatusUpdate(BaseModel):
    status:     ComplaintStatus
    officer_id: int | None = None


def comp_to_dict(c: Complaint, db) -> dict:
    from backend.models.station import Station
    station = db.query(Station).filter(Station.id == c.station_id).first()
    return {
        **{col.name: getattr(c, col.name) for col in c.__table__.columns},
        "station_name": station.name if station else None,
    }


@router.get("")
def list_complaints(
    page:       int = Query(1, ge=1),
    per_page:   int = Query(20, le=100),
    status:     Optional[str] = None,
    priority:   Optional[str] = None,
    station_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Complaint)
    if current_user.role == UserRole.station_officer:
        q = q.filter(Complaint.station_id == current_user.station_id)
    elif current_user.role == UserRole.citizen:
        q = q.filter(Complaint.created_by_id == current_user.id)
    elif station_id:
        q = q.filter(Complaint.station_id == station_id)

    if status:   q = q.filter(Complaint.status == status)
    if priority: q = q.filter(Complaint.priority == priority)

    total       = q.count()
    complaints  = q.order_by(Complaint.date.desc()).offset((page-1)*per_page).limit(per_page).all()
    return {"total": total, "data": [comp_to_dict(c, db) for c in complaints]}


@router.post("", status_code=201)
def create_complaint(
    req: ComplaintCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # AI priority classification
    priority_str, ai_score = classify_complaint(req.description, req.complaint_type)
    priority = ComplaintPriority(priority_str)

    complaint = Complaint(
        **req.model_dump(),
        priority       = priority,
        ai_score       = ai_score,
        created_by_id  = current_user.id,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    result = comp_to_dict(complaint, db)
    result["ai_priority"] = priority_str
    result["ai_score"]    = ai_score
    return result


@router.put("/{complaint_id}/status")
def update_status(
    complaint_id: int,
    req: ComplaintStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in [UserRole.district_head, UserRole.station_officer]:
        raise HTTPException(status_code=403, detail="Not authorized to update complaint status")
    c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    c.status = req.status
    if req.officer_id:
        c.officer_id = req.officer_id
    db.commit()
    return comp_to_dict(c, db)


@router.get("/stats")
def complaint_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Complaint)
    if current_user.role == UserRole.station_officer:
        q = q.filter(Complaint.station_id == current_user.station_id)
    return {
        "total":    q.count(),
        "open":     q.filter(Complaint.status == ComplaintStatus.open).count(),
        "resolved": q.filter(Complaint.status == ComplaintStatus.resolved).count(),
        "critical": q.filter(Complaint.priority == ComplaintPriority.critical).count(),
        "high":     q.filter(Complaint.priority == ComplaintPriority.high).count(),
    }
