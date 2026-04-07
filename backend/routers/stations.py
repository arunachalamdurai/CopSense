"""Stations router — public station list + officers per station"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.station import Station
from backend.models.user import User, UserRole

router = APIRouter(prefix="/api/stations", tags=["Stations"])


@router.get("")
def list_stations(db: Session = Depends(get_db)):
    """Public endpoint — no auth required. Returns all stations."""
    stations = db.query(Station).all()
    result = []
    for s in stations:
        result.append({
            "id":            s.id,
            "name":          s.name,
            "zone":          s.zone,
            "lat":           s.lat,
            "lng":           s.lng,
            "address":       s.address,
            "officer_count": s.officer_count,
        })
    return {"data": result}


@router.get("/{station_id}")
def get_station(station_id: int, db: Session = Depends(get_db)):
    """Public — get a single station by ID."""
    s = db.query(Station).filter(Station.id == station_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Station not found")
    return {
        "id":            s.id,
        "name":          s.name,
        "zone":          s.zone,
        "lat":           s.lat,
        "lng":           s.lng,
        "address":       s.address,
        "officer_count": s.officer_count,
    }


@router.get("/{station_id}/officers")
def station_officers(station_id: int, db: Session = Depends(get_db)):
    """
    Returns officers at a station for citizen feedback.
    Includes name, badge_id, role, photo_url (avatar initials-based).
    """
    station = db.query(Station).filter(Station.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    officers = db.query(User).filter(
        User.station_id == station_id,
        User.role.in_([UserRole.station_officer, UserRole.field_officer]),
        User.is_active == True,
    ).all()

    result = []
    for o in officers:
        # Generate initials for avatar
        initials = "".join(p[0] for p in o.full_name.split() if p)[:2].upper()
        result.append({
            "id":         o.id,
            "full_name":  o.full_name,
            "badge_id":   o.badge_id,
            "role":       o.role.value,
            "phone":      o.phone,
            "photo_url":  o.photo_url,
            "initials":   initials,
        })
    return {
        "station_id":   station_id,
        "station_name": station.name,
        "data":         result,
    }
