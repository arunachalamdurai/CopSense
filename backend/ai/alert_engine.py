"""
CopSense AI — Alert Engine
Background scanner that auto-generates alerts from module data.
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models.fir import FIR, FIRStatus
from backend.models.custody import CustodyRecord
from backend.models.duty import GPSLog
from backend.models.alert import Alert, AlertPriority, AlertType
from backend.models.complaint import Complaint, ComplaintPriority


def run_alert_scan(db: Session) -> list[Alert]:
    """
    Scan all modules and create new alerts where conditions are met.
    Returns list of newly created alerts.
    """
    new_alerts = []
    now = datetime.utcnow()

    # ── 1. FIR delays (>30 days without charge sheet) ─────────────────────────
    cutoff_fir = now - timedelta(days=30)
    overdue_firs = (
        db.query(FIR)
        .filter(FIR.date_filed <= cutoff_fir)
        .filter(FIR.status == FIRStatus.under_investigation)
        .all()
    )
    for fir in overdue_firs:
        existing = db.query(Alert).filter(
            Alert.module == "fir",
            Alert.ref_id == fir.id,
            Alert.type == AlertType.delay,
            Alert.resolved == False,
        ).first()
        if not existing:
            alert = Alert(
                type=AlertType.delay,
                priority=AlertPriority.high,
                title=f"FIR Delay — Charge Sheet Overdue: {fir.fir_number}",
                description=(
                    f"FIR {fir.fir_number} ({fir.crime_type}) has been under investigation "
                    f"for {(now - fir.date_filed).days} days without a charge sheet. "
                    "IO must initiate prosecution documents immediately."
                ),
                station_id=fir.station_id,
                officer_id=fir.officer_assigned_id,
                module="fir",
                ref_id=fir.id,
            )
            db.add(alert)
            new_alerts.append(alert)

    # ── 2. Custody no-update alert (>4 hours) ─────────────────────────────────
    cutoff_custody = now - timedelta(hours=4)
    overdue_custody = (
        db.query(CustodyRecord)
        .filter(CustodyRecord.last_update_time <= cutoff_custody)
        .filter(CustodyRecord.is_released == False)
        .all()
    )
    for rec in overdue_custody:
        existing = db.query(Alert).filter(
            Alert.module == "custody",
            Alert.ref_id == rec.id,
            Alert.type == AlertType.custody,
            Alert.resolved == False,
        ).first()
        if not existing:
            hours_since = round((now - rec.last_update_time).total_seconds() / 3600, 1)
            alert = Alert(
                type=AlertType.custody,
                priority=AlertPriority.critical,
                title=f"Custody Health Alert — No Update: {rec.accused_name}",
                description=(
                    f"Arrest {rec.arrest_id}: {rec.accused_name} in custody for {hours_since} hrs "
                    "with NO health update logged. 4-hour protocol violated. "
                    "Immediate SHO inspection required."
                ),
                station_id=rec.station_id,
                officer_id=rec.officer_id,
                module="custody",
                ref_id=rec.id,
            )
            db.add(alert)
            new_alerts.append(alert)

    # ── 3. Critical / High complaints unattended >2 hours ─────────────────────
    cutoff_complaint = now - timedelta(hours=2)
    urgent_complaints = (
        db.query(Complaint)
        .filter(Complaint.date <= cutoff_complaint)
        .filter(Complaint.priority.in_([ComplaintPriority.critical, ComplaintPriority.high]))
        .filter(Complaint.status == "open")
        .all()
    )
    for comp in urgent_complaints:
        existing = db.query(Alert).filter(
            Alert.module == "complaint",
            Alert.ref_id == comp.id,
            Alert.resolved == False,
        ).first()
        if not existing:
            alert = Alert(
                type=AlertType.complaint,
                priority=AlertPriority.high if comp.priority == "high" else AlertPriority.critical,
                title=f"Unattended {comp.priority.upper()} Complaint: {comp.complaint_type}",
                description=(
                    f"Complaint from {comp.citizen_name} ({comp.phone}) — "
                    f"{comp.complaint_type} at {comp.location}. "
                    f"AI Score: {comp.ai_score}. Pending for over 2 hours without response."
                ),
                station_id=comp.station_id,
                officer_id=comp.officer_id,
                module="complaint",
                ref_id=comp.id,
            )
            db.add(alert)
            new_alerts.append(alert)

    # ── 4. GPS out-of-zone violations ─────────────────────────────────────────
    recent_violations = (
        db.query(GPSLog)
        .filter(GPSLog.in_zone == False)
        .filter(GPSLog.timestamp >= now - timedelta(hours=1))
        .all()
    )
    for log in recent_violations:
        existing = db.query(Alert).filter(
            Alert.module == "duty",
            Alert.ref_id == log.id,
            Alert.resolved == False,
        ).first()
        if not existing:
            alert = Alert(
                type=AlertType.gps_violation,
                priority=AlertPriority.warning,
                title=f"GPS Out-of-Zone Alert — Officer ID {log.officer_id}",
                description=(
                    f"Officer has been detected outside assigned zone. "
                    f"Location: ({log.lat:.4f}, {log.lng:.4f}). "
                    f"Reason logged: {log.violation_reason or 'None'}. "
                    "Station officer notified."
                ),
                officer_id=log.officer_id,
                module="duty",
                ref_id=log.id,
            )
            db.add(alert)
            new_alerts.append(alert)

    if new_alerts:
        db.commit()

    return new_alerts


def mock_whatsapp_notify(phone: str, message: str, media_url: str | None = None) -> dict:
    """
    Mock WhatsApp notification (logs only — no real API call).
    In production: replace with Twilio/Meta WhatsApp Cloud API.
    """
    print(f"[MOCK WhatsApp] To: {phone}")
    print(f"  Message: {message}")
    if media_url:
        print(f"  Media: {media_url}")
    return {"status": "mocked", "to": phone, "message": message}
