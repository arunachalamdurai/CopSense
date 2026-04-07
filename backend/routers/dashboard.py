"""Dashboard stats router — real-time counts from DB"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend.models.fir import FIR, FIRStatus
from backend.models.complaint import Complaint, ComplaintStatus, ComplaintPriority
from backend.models.custody import CustodyRecord
from backend.models.alert import Alert, AlertPriority
from backend.models.feedback import Feedback
from backend.models.user import User, UserRole
from backend.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats")
def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    def station_filter(q, model):
        if current_user.role == UserRole.station_officer:
            return q.filter(getattr(model, "station_id") == current_user.station_id)
        return q

    fir_q      = station_filter(db.query(FIR), FIR)
    comp_q     = station_filter(db.query(Complaint), Complaint)
    custody_q  = db.query(CustodyRecord).filter(CustodyRecord.is_released == False)
    alert_q    = db.query(Alert).filter(Alert.resolved == False)
    feedback_q = db.query(Feedback)

    total_officers = db.query(User).filter(
        User.role.in_([UserRole.station_officer, UserRole.field_officer]),
        User.is_active == True,
    ).count()

    avg_rating = db.query(func.avg(Feedback.rating)).scalar() or 0

    return {
        "total_firs":         fir_q.count(),
        "pending_cases":      fir_q.filter(FIR.status == FIRStatus.under_investigation).count(),
        "closed_cases":       fir_q.filter(FIR.status == FIRStatus.closed).count(),
        "open_complaints":    comp_q.filter(Complaint.status == ComplaintStatus.open).count(),
        "resolved_complaints":comp_q.filter(Complaint.status == ComplaintStatus.resolved).count(),
        "total_complaints":   comp_q.count(),
        "custody_persons":    custody_q.count(),
        "custody_alerts":     custody_q.filter(CustodyRecord.last_update_time <= func.datetime("now", "-4 hours")).count(),
        "critical_alerts":    alert_q.filter(Alert.priority == AlertPriority.critical).count(),
        "active_alerts":      alert_q.count(),
        "total_officers":     total_officers,
        "feedback_count":     feedback_q.count(),
        "avg_rating":         round(float(avg_rating), 2),
        "satisfaction_pct":   round(float(avg_rating) / 5 * 100, 1),
    }


@router.get("/recent-firs")
def recent_firs(
    limit: int = 8,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(FIR)
    if current_user.role == UserRole.station_officer:
        q = q.filter(FIR.station_id == current_user.station_id)
    firs = q.order_by(FIR.date_filed.desc()).limit(limit).all()

    results = []
    for f in firs:
        from backend.models.station import Station
        station = db.query(Station).filter(Station.id == f.station_id).first()
        results.append({
            "id":         f.id,
            "fir_number": f.fir_number,
            "crime_type": f.crime_type,
            "status":     f.status.value,
            "date_filed": f.date_filed.isoformat(),
            "station":    station.name if station else "—",
        })
    return {"data": results}
