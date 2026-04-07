"""Officer Duty & GPS tracking router — with my-assignments, violation-report"""
import math
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.duty import DutyAssignment, DutyStatus, GPSLog
from backend.models.user import User, UserRole
from backend.models.crowd_event import CrowdEvent
from backend.auth.dependencies import get_current_user, require_station_or_above

router = APIRouter(prefix="/api/duty", tags=["Officer Duty"])


class DutyCreate(BaseModel):
    officer_id:   int
    station_id:   int
    zone:         str
    lat_assigned: float
    lng_assigned: float
    radius_km:    float = 1.0
    start_time:   datetime
    end_time:     datetime
    crowd_event_id: int | None = None


class GPSUpdate(BaseModel):
    lat:              float
    lng:              float
    violation_reason: str = ""


def duty_dict(d: DutyAssignment, db) -> dict:
    from backend.models.user import User as UserM
    officer = db.query(UserM).filter(UserM.id == d.officer_id).first()
    return {
        **{c.name: getattr(d, c.name) for c in d.__table__.columns},
        "officer_name": officer.full_name if officer else None,
        "officer_badge": officer.badge_id if officer else None,
    }


def haversine(lat1, lng1, lat2, lng2) -> float:
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (math.sin(d_lat/2)**2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(d_lng/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


@router.get("")
def list_duties(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(DutyAssignment)
    if current_user.role == UserRole.field_officer:
        q = q.filter(DutyAssignment.officer_id == current_user.id)
    elif current_user.role == UserRole.station_officer:
        q = q.filter(DutyAssignment.station_id == current_user.station_id)
    duties = q.order_by(DutyAssignment.start_time.desc()).all()
    return {"data": [duty_dict(d, db) for d in duties]}


@router.post("", status_code=201)
def assign_duty(
    req: DutyCreate,
    current_user: User = Depends(require_station_or_above),
    db: Session = Depends(get_db),
):
    duty = DutyAssignment(**req.model_dump())
    db.add(duty)
    db.commit()
    db.refresh(duty)
    return duty_dict(duty, db)


@router.post("/{duty_id}/gps")
def submit_gps(
    duty_id: int,
    req:     GPSUpdate,
    current_user: User = Depends(get_current_user),
    db:      Session = Depends(get_db),
):
    if current_user.role == UserRole.citizen:
        raise HTTPException(status_code=403)

    duty = db.query(DutyAssignment).filter(DutyAssignment.id == duty_id).first()
    if not duty:
        raise HTTPException(status_code=404, detail="Duty assignment not found")

    # Geofence check (Haversine)
    dist    = haversine(req.lat, req.lng, duty.lat_assigned, duty.lng_assigned)
    in_zone = dist <= duty.radius_km

    log = GPSLog(
        officer_id       = current_user.id,
        duty_id          = duty_id,
        lat              = req.lat,
        lng              = req.lng,
        in_zone          = in_zone,
        violation_reason = req.violation_reason if not in_zone else "",
    )
    db.add(log)

    if not in_zone:
        duty.status = DutyStatus.off_zone

    db.commit()
    return {
        "in_zone":            in_zone,
        "geofence_violation": not in_zone,
        "distance_km":        round(dist, 3),
        "allowed_radius":     duty.radius_km,
        "violation":          not in_zone,
        "message":            "GPS logged" if in_zone else "OUT OF ZONE ALERT — Station officer notified",
    }


@router.get("/violations")
def gps_violations(
    current_user: User = Depends(require_station_or_above),
    db: Session = Depends(get_db),
):
    logs = (
        db.query(GPSLog)
        .filter(GPSLog.in_zone == False)
        .order_by(GPSLog.timestamp.desc())
        .limit(100)
        .all()
    )
    results = []
    for l in logs:
        officer = db.query(User).filter(User.id == l.officer_id).first()
        results.append({
            **{c.name: getattr(l, c.name) for c in l.__table__.columns},
            "officer_name": officer.full_name if officer else None,
            "officer_badge": officer.badge_id if officer else None,
        })
    return {"data": results}


@router.get("/my-assignments")
def my_duty_assignments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the logged-in officer's own duty assignments (for duty board personal view)."""
    if current_user.role == UserRole.citizen:
        raise HTTPException(status_code=403, detail="Citizens do not have duty assignments")

    duties = db.query(DutyAssignment).filter(
        DutyAssignment.officer_id == current_user.id
    ).order_by(DutyAssignment.start_time.desc()).limit(20).all()

    results = []
    for d in duties:
        event = None
        if d.crowd_event_id:
            ev = db.query(CrowdEvent).filter(CrowdEvent.id == d.crowd_event_id).first()
            if ev:
                event = {"id": ev.id, "name": ev.name, "location": ev.location}
        results.append({
            **duty_dict(d, db),
            "crowd_event": event,
        })
    return {"data": results}

