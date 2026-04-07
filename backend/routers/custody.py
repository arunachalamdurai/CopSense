"""Custody Safety router with 4-hr monitoring, video upload"""
import os
import shutil
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.custody import CustodyRecord, HealthStatus
from backend.models.user import User, UserRole
from backend.auth.dependencies import get_current_user, require_station_or_above
from backend.ai.alert_engine import mock_whatsapp_notify
from backend.config import settings

router = APIRouter(prefix="/api/custody", tags=["Custody Safety"])


class CustodyCreate(BaseModel):
    arrest_id:        str
    accused_name:     str
    accused_age:      int | None = None
    accused_address:  str = ""
    arrest_date:      datetime
    custody_location: str
    relative_name:    str = ""
    relative_phone:   str          # REQUIRED
    crime_type:       str = ""
    ipc_section:      str = ""
    station_id:       int
    notes:            str = ""

    @field_validator("relative_phone")
    @classmethod
    def phone_required(cls, v):
        if not v or not v.strip():
            raise ValueError("Relative phone number is required")
        digits = ''.join(c for c in v if c.isdigit())
        if len(digits) < 10:
            raise ValueError("Relative phone must be at least 10 digits")
        return v.strip()

    @field_validator("arrest_id", "accused_name", "custody_location")
    @classmethod
    def not_empty(cls, v, info):
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} is required")
        return v.strip()


class HealthUpdateRequest(BaseModel):
    health_status: HealthStatus
    notes:         str = ""


def custody_dict(rec: CustodyRecord, db) -> dict:
    from datetime import timezone
    now    = datetime.utcnow()
    hours_since = round((now - rec.last_update_time).total_seconds() / 3600, 1)
    overdue = hours_since >= 4.0
    from backend.models.station import Station
    from backend.models.user import User as UserM
    station = db.query(Station).filter(Station.id == rec.station_id).first()
    officer = db.query(UserM).filter(UserM.id == rec.officer_id).first()
    return {
        **{c.name: getattr(rec, c.name) for c in rec.__table__.columns},
        "hours_since_update": hours_since,
        "overdue": overdue,
        # Frontend-compatible aliases
        "custody_id":         rec.arrest_id,
        "person_name":        rec.accused_name,
        "age":                rec.accused_age,
        "arrest_reason":      rec.crime_type,
        "arresting_officer":  officer.full_name if officer else "—",
        "station_name":       station.name if station else "—",
        "last_health_check":  rec.last_update_time.isoformat(),
        "injury_status":      "None",
        "medical_status":     rec.health_status.value.capitalize() if rec.health_status else "Stable",
        "meal_provided":      True,
    }


@router.get("")
def list_custody(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == UserRole.citizen:
        raise HTTPException(status_code=403, detail="Citizens cannot view custody records")
    q = db.query(CustodyRecord).filter(CustodyRecord.is_released == False)
    if current_user.role in [UserRole.station_officer, UserRole.field_officer]:
        q = q.filter(CustodyRecord.station_id == current_user.station_id)
    records = q.order_by(CustodyRecord.arrest_date.desc()).all()
    data = [custody_dict(r, db) for r in records]
    return {"total": len(data), "data": data, "custody_records": data}



@router.post("", status_code=201)
def create_custody(
    req: CustodyCreate,
    current_user: User = Depends(require_station_or_above),
    db: Session = Depends(get_db),
):
    if db.query(CustodyRecord).filter(CustodyRecord.arrest_id == req.arrest_id.upper()).first():
        raise HTTPException(status_code=409, detail=f"Arrest ID {req.arrest_id} already registered")

    rec = CustodyRecord(
        **req.model_dump(),
        arrest_id  = req.arrest_id.upper(),
        officer_id = current_user.id,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    # Mock notify relative
    mock_whatsapp_notify(
        rec.relative_phone,
        f"Dear {rec.relative_name or 'Family'}, {rec.accused_name} has been taken into custody at "
        f"{rec.custody_location}. Arrest ID: {rec.arrest_id}. For queries, contact the police station.",
    )
    return custody_dict(rec, db)


@router.put("/{custody_id}/update")
def health_update(
    custody_id: int,
    req: HealthUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rec = db.query(CustodyRecord).filter(CustodyRecord.id == custody_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Custody record not found")
    rec.health_status    = req.health_status
    rec.last_update_time = datetime.utcnow()
    if req.notes:
        rec.notes = rec.notes + f"\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] {req.notes}"
    db.commit()
    return custody_dict(rec, db)


@router.post("/{custody_id}/video")
async def upload_video(
    custody_id: int,
    note: str = Form(""),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rec = db.query(CustodyRecord).filter(CustodyRecord.id == custody_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Custody record not found")

    # Validate file type
    if not file.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv", ".webm")):
        raise HTTPException(status_code=400, detail="Only video files allowed (.mp4, .avi, .mov)")

    # Save locally
    upload_dir = os.path.join(settings.UPLOAD_DIR, "custody", str(custody_id))
    os.makedirs(upload_dir, exist_ok=True)
    timestamp   = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename    = f"{timestamp}_{file.filename}"
    file_path   = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Log upload in JSON field
    uploads = rec.video_uploads or []
    uploads.append({
        "url":       f"/uploads/custody/{custody_id}/{filename}",
        "timestamp": datetime.utcnow().isoformat(),
        "note":      note,
        "officer":   current_user.full_name,
    })
    rec.video_uploads    = uploads
    rec.last_update_time = datetime.utcnow()
    db.commit()

    # Mock WhatsApp notification to relative
    mock_whatsapp_notify(
        rec.relative_phone,
        f"CopSense Update: Custody video for {rec.accused_name} (ID: {rec.arrest_id}) "
        f"uploaded at {datetime.utcnow().strftime('%H:%M %d/%m/%Y')}. "
        f"Note: {note or 'Routine check'}"
    )
    return {"message": "Video uploaded successfully", "url": f"/uploads/custody/{custody_id}/{filename}"}


@router.get("/alerts")
def custody_alerts(
    current_user: User = Depends(require_station_or_above),
    db: Session = Depends(get_db),
):
    """Return all custody records that are overdue (>4 hrs without update)."""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(hours=4)
    q = db.query(CustodyRecord).filter(
        CustodyRecord.last_update_time <= cutoff,
        CustodyRecord.is_released == False,
    )
    if current_user.role == UserRole.station_officer:
        q = q.filter(CustodyRecord.station_id == current_user.station_id)
    overdue = q.all()
    return {"total": len(overdue), "data": [custody_dict(r, db) for r in overdue]}
