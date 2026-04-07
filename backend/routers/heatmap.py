"""Crime Heatmap router — lat/lng/intensity points from FIR + complaint data"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
import random
from datetime import datetime, timedelta
from backend.database import get_db
from backend.models.fir import FIR
from backend.models.complaint import Complaint
from backend.models.user import User
from backend.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/heatmap", tags=["Crime Heatmap"])

STATION_COORDS = {
    1: (25.6128, 85.1346, "Patna City"),
    2: (25.5961, 85.1533, "Kankarbagh"),
    3: (25.6050, 85.1236, "Gardanibagh"),
    4: (25.6218, 85.1117, "Boring Road"),
    5: (25.5729, 85.1200, "Phulwari"),
    6: (25.6312, 85.1253, "Sachivalaya"),
}
SEVERITY_WEIGHT = {"murder":1.0,"rape":1.0,"kidnap":1.0,"robbery":0.8,"assault":0.7,"missing":0.8,"theft":0.5,"fraud":0.5}


@router.get("")
def heatmap_points(days:int=Query(30),current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=days)
    firs   = db.query(FIR).filter(FIR.date_filed >= cutoff).all()
    comps  = db.query(Complaint).filter(Complaint.date >= cutoff).all()

    station_intensity: dict[int, float] = {}
    for fir in firs:
        w = 0.6
        for k, wt in SEVERITY_WEIGHT.items():
            if k in fir.crime_type.lower(): w = wt; break
        station_intensity[fir.station_id] = station_intensity.get(fir.station_id, 0) + w
    for comp in comps:
        station_intensity[comp.station_id] = station_intensity.get(comp.station_id, 0) + 0.3

    max_val = max(station_intensity.values()) if station_intensity else 1
    points = []
    for sid, intensity in station_intensity.items():
        coords = STATION_COORDS.get(sid)
        if not coords: continue
        lat, lng, name = coords
        norm = min(intensity / max_val, 1.0)
        for _ in range(max(int(norm * 15), 3)):
            points.append({"lat":round(lat+(random.random()-.5)*.012,6),"lng":round(lng+(random.random()-.5)*.012,6),"intensity":round(norm*(0.7+random.random()*.3),3),"station":name})
    return {"total_points":len(points),"days":days,"data":points}


@router.get("/zones")
def zone_summary(days:int=Query(30),current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=days)
    results = []
    for sid,(lat,lng,name) in STATION_COORDS.items():
        fc = db.query(FIR).filter(FIR.station_id==sid,FIR.date_filed>=cutoff).count()
        cc = db.query(Complaint).filter(Complaint.station_id==sid,Complaint.date>=cutoff).count()
        total = fc + cc*0.5
        results.append({"station_id":sid,"station_name":name,"fir_count":fc,"complaint_count":cc,"total_incidents":int(total),"risk_level":"high" if total>=30 else("medium" if total>=15 else "low"),"lat":lat,"lng":lng})
    results.sort(key=lambda x:x["total_incidents"],reverse=True)
    return {"data":results}


@router.get("/alert-colors")
def alert_colors(days:int=Query(30),current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    """Returns per-station color alert: red (high crime), orange (medium), green (low)."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = []
    for sid,(lat,lng,name) in STATION_COORDS.items():
        fc = db.query(FIR).filter(FIR.station_id==sid,FIR.date_filed>=cutoff).count()
        cc = db.query(Complaint).filter(Complaint.station_id==sid,Complaint.date>=cutoff).count()
        total = fc + cc * 0.5
        if total >= 30:
            color, risk = "#C62828", "high"
        elif total >= 15:
            color, risk = "#F9A825", "medium"
        else:
            color, risk = "#2E7D32", "low"
        result.append({
            "station_id":   sid,
            "station_name": name,
            "lat": lat, "lng": lng,
            "fir_count": fc,
            "complaint_count": cc,
            "total_incidents": int(total),
            "risk_level": risk,
            "color": color,
            "radius": 700 if risk == "high" else (550 if risk == "medium" else 400),
        })
    result.sort(key=lambda x: x["total_incidents"], reverse=True)
    return {"data": result, "days": days}
