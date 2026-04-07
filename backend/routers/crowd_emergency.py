"""Crowd Planning + Emergency Response routers"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from backend.database import get_db
from backend.models.crowd_event import CrowdEvent, EventRiskLevel
from backend.models.duty import DutyAssignment
from backend.models.user import User, UserRole
from backend.auth.dependencies import get_current_user, require_station_or_above
from backend.ai.crowd_planner import calculate_risk_score, generate_blueprint
from backend.ai.emergency_optimizer import rank_officers, explain_recommendation

crowd_router = APIRouter(prefix="/api/crowd-planning", tags=["Crowd Planning"])
emergency_router = APIRouter(prefix="/api/emergency", tags=["Emergency Response"])


# ── CROWD PLANNING ────────────────────────────────────────────────────────────

class CrowdAnalyzeRequest(BaseModel):
    name:          str
    location:      str
    lat:           float | None = None
    lng:           float | None = None
    event_date:    datetime
    crowd_size:    int
    duration_hrs:  int = 4
    risk_level:    str = "medium"
    event_type:    str = ""
    vip_presence:  bool = False
    past_incidents:int = 0
    station_id:    int | None = None


@crowd_router.post("/analyze", status_code=201)
def analyze_event(
    req: CrowdAnalyzeRequest,
    current_user: User = Depends(require_station_or_above),
    db: Session = Depends(get_db),
):
    risk_score = calculate_risk_score(
        req.crowd_size, req.duration_hrs, req.risk_level,
        req.vip_presence, req.past_incidents, req.event_type,
    )
    blueprint = generate_blueprint(req.name, req.location, req.crowd_size, req.duration_hrs, risk_score, req.event_type)
    rl = EventRiskLevel(req.risk_level) if req.risk_level in [e.value for e in EventRiskLevel] else EventRiskLevel.medium
    event = CrowdEvent(
        name=req.name, location=req.location, lat=req.lat, lng=req.lng,
        event_date=req.event_date, crowd_size=req.crowd_size, duration_hrs=req.duration_hrs,
        risk_level=rl, risk_score=risk_score, ai_blueprint=blueprint,
        station_id=req.station_id, created_by_id=current_user.id,
    )
    db.add(event); db.commit(); db.refresh(event)
    return {"event_id": event.id, "risk_score": risk_score, "blueprint": blueprint}


@crowd_router.get("")
def list_events(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    events = db.query(CrowdEvent).order_by(CrowdEvent.created_at.desc()).limit(50).all()
    return {"data": [{c.name: getattr(e, c.name) for c in e.__table__.columns} for e in events]}


@crowd_router.post("/{event_id}/deploy")
def deploy_event(
    event_id: int,
    current_user: User = Depends(require_station_or_above),
    db: Session = Depends(get_db),
):
    event = db.query(CrowdEvent).filter(CrowdEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    blueprint = event.ai_blueprint
    n_officers = blueprint.get("personnel", {}).get("total_officers", 5)
    # Create duty assignments from blueprint zones
    duties_created = 0
    for zone_info in blueprint.get("patrol_zones", []):
        duty = DutyAssignment(
            officer_id=current_user.id, station_id=event.station_id or 1,
            zone=zone_info["zone"], lat_assigned=event.lat or 25.603,
            lng_assigned=event.lng or 85.133, radius_km=0.5,
            start_time=event.event_date,
            end_time=datetime.fromtimestamp(event.event_date.timestamp() + event.duration_hrs * 3600),
            crowd_event_id=event.id, patrol_notes=f"AI-deployed: {zone_info['description']}",
        )
        db.add(duty); duties_created += 1
    event.deployed = duties_created > 0
    db.commit()
    return {"message": f"Deployed {duties_created} patrol zone assignments to duty board"}


# ── EMERGENCY RESPONSE ────────────────────────────────────────────────────────

class IncidentRequest(BaseModel):
    lat:           float
    lng:           float
    incident_type: str = "assault"
    severity:      str = "high"


class DispatchRequest(BaseModel):
    officer_id:    int
    incident_lat:  float
    incident_lng:  float
    incident_type: str


MOCK_OFFICERS = [
    {"id":1,"name":"SI Ravi Kumar","badge":"SI-0024","station":"Patna City","lat":25.6128,"lng":85.1346,"status":"available","armed":True,"vehicle":"PCR Van","rank_level":2},
    {"id":2,"name":"ASI Deepak Singh","badge":"ASI-0047","station":"Kankarbagh","lat":25.5961,"lng":85.1533,"status":"patrolling","armed":True,"vehicle":"Motorcycle","rank_level":1},
    {"id":3,"name":"Const. Mohan Lal","badge":"CONST-0112","station":"Gardanibagh","lat":25.6050,"lng":85.1236,"status":"available","armed":False,"vehicle":"Foot","rank_level":0},
    {"id":4,"name":"SI Priya Verma","badge":"SI-0031","station":"Boring Road","lat":25.6218,"lng":85.1117,"status":"available","armed":True,"vehicle":"PCR Van","rank_level":2},
    {"id":5,"name":"ASI Ajay Pandey","badge":"ASI-0062","station":"Phulwari","lat":25.5729,"lng":85.1200,"status":"patrolling","armed":True,"vehicle":"Motorcycle","rank_level":1},
    {"id":6,"name":"SI Arun Tiwari","badge":"SI-0055","station":"Phulwari","lat":25.5750,"lng":85.1180,"status":"available","armed":True,"vehicle":"PCR Van","rank_level":2},
    {"id":7,"name":"ASI Meena Kumari","badge":"ASI-0078","station":"Patna City","lat":25.6100,"lng":85.1320,"status":"patrolling","armed":False,"vehicle":"Motorcycle","rank_level":1},
    {"id":8,"name":"Const. Shyam Yadav","badge":"CONST-0134","station":"Kankarbagh","lat":25.5970,"lng":85.1560,"status":"available","armed":False,"vehicle":"Foot","rank_level":0},
    {"id":9,"name":"SI Dinesh Pandey","badge":"SI-0041","station":"Boring Road","lat":25.6190,"lng":85.1090,"status":"available","armed":True,"vehicle":"PCR Van","rank_level":2},
    {"id":10,"name":"ASI Anita Singh","badge":"ASI-0091","station":"Boring Road","lat":25.6180,"lng":85.1095,"status":"available","armed":True,"vehicle":"Motorcycle","rank_level":1},
]


def _build_live_officers(db: Session) -> list:
    """Build officer list from active duty assignments + latest GPS logs."""
    from backend.models.duty import DutyAssignment, DutyStatus, GPSLog
    from backend.models.station import Station
    active_duties = db.query(DutyAssignment).filter(
        DutyAssignment.status == DutyStatus.active
    ).all()

    officers = []
    for d in active_duties:
        officer = db.query(User).filter(User.id == d.officer_id).first()
        if not officer:
            continue
        station = db.query(Station).filter(Station.id == d.station_id).first()
        # Get latest GPS log
        gps = db.query(GPSLog).filter(
            GPSLog.duty_id == d.id
        ).order_by(GPSLog.timestamp.desc()).first()

        lat = gps.lat if gps else d.lat_assigned
        lng = gps.lng if gps else d.lng_assigned
        available = (d.status == DutyStatus.active and (not gps or gps.in_zone))

        rank_map = {UserRole.district_head: 3, UserRole.station_officer: 2, UserRole.field_officer: 1}
        officers.append({
            "id":         officer.id,
            "name":       officer.full_name,
            "badge":      officer.badge_id,
            "station":    station.name if station else "Unknown",
            "lat":        lat,
            "lng":        lng,
            "status":     "available" if available else "engaged",
            "armed":      True,
            "vehicle":    "PCR Van" if officer.role == UserRole.station_officer else "Motorcycle",
            "rank_level": rank_map.get(officer.role, 0),
        })
    return officers if officers else MOCK_OFFICERS


@emergency_router.post("/nearest")
def nearest_unit(req: IncidentRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    officers = _build_live_officers(db)
    ranked = rank_officers(officers, req.lat, req.lng, req.incident_type, req.severity)
    if not ranked:
        raise HTTPException(status_code=404, detail="No available officers found")
    top = ranked[0]
    return {
        "ranked_units":   ranked,
        "recommendation": explain_recommendation(top),
        "top_pick":       top,
    }


@emergency_router.post("/dispatch")
def dispatch(req: DispatchRequest, current_user: User = Depends(require_station_or_above), db: Session = Depends(get_db)):
    now = datetime.utcnow().strftime("%H:%M")
    return {
        "dispatched": True,
        "officer_id": req.officer_id,
        "incident_type": req.incident_type,
        "dispatch_time": now,
        "message": f"Officer dispatched to incident at ({req.incident_lat:.4f},{req.incident_lng:.4f})",
    }

