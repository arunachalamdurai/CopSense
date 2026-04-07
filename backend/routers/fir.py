"""FIR router — CRUD with validation, duplicate prevention, RBAC"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend.models.fir import FIR, FIRStatus
from backend.models.user import User, UserRole
from backend.auth.dependencies import get_current_user, require_station_or_above

router = APIRouter(prefix="/api/fir", tags=["FIR Management"])


class FIRCreate(BaseModel):
    fir_number:        str
    crime_type:        str
    ipc_section:       str = ""
    location:          str
    lat:               float | None = None
    lng:               float | None = None
    complainant_name:  str
    complainant_phone: str = ""
    description:       str = ""
    officer_assigned_id: int | None = None
    station_id:        int
    evidence_attached: bool = False

    @field_validator("fir_number")
    @classmethod
    def fir_number_format(cls, v):
        if not v or len(v) < 3:
            raise ValueError("FIR number must be at least 3 characters")
        return v.strip().upper()

    @field_validator("crime_type", "location", "complainant_name")
    @classmethod
    def not_empty(cls, v, info):
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} is required")
        return v.strip()


class FIRUpdate(BaseModel):
    status:            FIRStatus | None = None
    officer_assigned_id: int | None = None
    ipc_section:       str | None = None
    description:       str | None = None
    evidence_attached: bool | None = None


class FIRResponse(BaseModel):
    id:                int
    fir_number:        str
    crime_type:        str
    ipc_section:       str
    location:          str
    lat:               float | None
    lng:               float | None
    complainant_name:  str
    complainant_phone: str
    description:       str
    station_id:        int
    officer_assigned_id: int | None
    status:            str
    evidence_attached: bool
    date_filed:        datetime
    updated_at:        datetime
    days_pending:      int = 0
    officer_name:      str | None = None
    station_name:      str | None = None

    model_config = {"from_attributes": True}


def fir_to_response(fir: FIR, db) -> dict:
    from backend.models.station import Station
    from backend.models.user import User as UserM
    now = datetime.utcnow()
    station = db.query(Station).filter(Station.id == fir.station_id).first()
    officer = db.query(UserM).filter(UserM.id == fir.officer_assigned_id).first() if fir.officer_assigned_id else None
    return {
        **{c.name: getattr(fir, c.name) for c in fir.__table__.columns},
        "days_pending": (now - fir.date_filed).days,
        "officer_name": officer.full_name if officer else None,
        "station_name": station.name if station else None,
    }


@router.get("")
def list_firs(
    page:     int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status:   Optional[str] = None,
    search:   Optional[str] = None,
    station_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db:       Session = Depends(get_db),
):
    q = db.query(FIR)
    # RBAC filter
    if current_user.role == UserRole.station_officer:
        q = q.filter(FIR.station_id == current_user.station_id)
    elif current_user.role == UserRole.field_officer:
        q = q.filter(FIR.officer_assigned_id == current_user.id)
    elif station_id:
        q = q.filter(FIR.station_id == station_id)

    if status:
        q = q.filter(FIR.status == status)
    if search:
        term = f"%{search}%"
        q = q.filter(
            FIR.fir_number.ilike(term)
            | FIR.crime_type.ilike(term)
            | FIR.complainant_name.ilike(term)
        )

    total = q.count()
    firs  = q.order_by(FIR.date_filed.desc()).offset((page-1)*per_page).limit(per_page).all()
    return {
        "total": total,
        "page":  page,
        "per_page": per_page,
        "data": [fir_to_response(f, db) for f in firs],
    }


@router.post("", status_code=201)
def create_fir(
    req: FIRCreate,
    current_user: User = Depends(require_station_or_above),
    db:  Session = Depends(get_db),
):
    # Duplicate prevention
    if db.query(FIR).filter(FIR.fir_number == req.fir_number).first():
        raise HTTPException(status_code=409, detail=f"FIR number {req.fir_number} already exists")

    fir = FIR(**req.model_dump(), created_by_id=current_user.id)
    db.add(fir)
    db.commit()
    db.refresh(fir)
    return fir_to_response(fir, db)


@router.get("/stats")
def fir_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(FIR)
    if current_user.role == UserRole.station_officer:
        q = q.filter(FIR.station_id == current_user.station_id)
    elif current_user.role == UserRole.field_officer:
        q = q.filter(FIR.officer_assigned_id == current_user.id)

    total   = q.count()
    pending = q.filter(FIR.status == FIRStatus.under_investigation).count()
    closed  = q.filter(FIR.status == FIRStatus.closed).count()
    charge  = q.filter(FIR.status == FIRStatus.charge_sheet_filed).count()
    return {
        "total": total,
        "registered": q.filter(FIR.status == FIRStatus.registered).count(),
        "under_investigation": pending,
        "charge_sheet_filed": charge,
        "closed": closed,
    }


@router.get("/{fir_id}")
def get_fir(
    fir_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fir = db.query(FIR).filter(FIR.id == fir_id).first()
    if not fir:
        raise HTTPException(status_code=404, detail="FIR not found")
    return fir_to_response(fir, db)


@router.put("/{fir_id}")
def update_fir(
    fir_id: int,
    req:   FIRUpdate,
    current_user: User = Depends(require_station_or_above),
    db:    Session = Depends(get_db),
):
    fir = db.query(FIR).filter(FIR.id == fir_id).first()
    if not fir:
        raise HTTPException(status_code=404, detail="FIR not found")
    for k, v in req.model_dump(exclude_none=True).items():
        setattr(fir, k, v)
    fir.updated_at = datetime.utcnow()
    db.commit()
    return fir_to_response(fir, db)


@router.delete("/{fir_id}", status_code=204)
def delete_fir(
    fir_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.district_head:
        raise HTTPException(status_code=403, detail="Only District Head can delete FIRs")
    fir = db.query(FIR).filter(FIR.id == fir_id).first()
    if not fir:
        raise HTTPException(status_code=404, detail="FIR not found")
    db.delete(fir)
    db.commit()
