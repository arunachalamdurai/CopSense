"""Alerts router — Smart Alert Center"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from backend.database import get_db
from backend.models.alert import Alert, AlertPriority, AlertType
from backend.models.user import User, UserRole
from backend.auth.dependencies import get_current_user
from backend.ai.alert_engine import run_alert_scan

router = APIRouter(prefix="/api/alerts", tags=["Smart Alerts"])


@router.get("")
def list_alerts(
    page:       int = Query(1, ge=1),
    per_page:   int = Query(50, le=200),
    resolved:   Optional[bool] = False,
    priority:   Optional[str] = None,
    module:     Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db:         Session = Depends(get_db),
):
    q = db.query(Alert)
    if current_user.role not in [UserRole.district_head]:
        q = q.filter(Alert.station_id == current_user.station_id)
    if resolved is not None:
        q = q.filter(Alert.resolved == resolved)
    if priority:
        q = q.filter(Alert.priority == priority)
    if module:
        q = q.filter(Alert.module == module)

    total  = q.count()
    alerts = q.order_by(Alert.created_at.desc()).offset((page-1)*per_page).limit(per_page).all()
    return {
        "total": total,
        "data":  [{c.name: getattr(a, c.name) for c in a.__table__.columns} for a in alerts],
    }


@router.post("/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db:       Session = Depends(get_db),
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.resolved    = True
    alert.resolved_at = datetime.utcnow()
    db.commit()
    return {"message": f"Alert {alert_id} resolved"}


@router.post("/scan")
def trigger_scan(
    current_user: User = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    """Manually trigger AI alert scan — runs automatically in background every 60s."""
    new_alerts = run_alert_scan(db)
    return {"message": f"Scan complete. {len(new_alerts)} new alert(s) generated."}


@router.get("/stats")
def alert_stats(
    current_user: User = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    q = db.query(Alert).filter(Alert.resolved == False)
    if current_user.role != UserRole.district_head:
        q = q.filter(Alert.station_id == current_user.station_id)
    return {
        "critical": q.filter(Alert.priority == AlertPriority.critical).count(),
        "high":     q.filter(Alert.priority == AlertPriority.high).count(),
        "warning":  q.filter(Alert.priority == AlertPriority.warning).count(),
        "total_unresolved": q.count(),
    }
