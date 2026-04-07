"""
Seed the database with demo users, stations, and sample data.
Run: python -m backend.services.seed
"""
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.database import SessionLocal, engine, Base
from backend.auth.jwt_handler import get_password_hash
from backend.models.user import User, UserRole
from backend.models.station import Station
from backend.models.fir import FIR, FIRStatus
from backend.models.complaint import Complaint, ComplaintPriority, ComplaintStatus
from backend.models.custody import CustodyRecord, HealthStatus
from backend.models.feedback import Feedback, FeedbackSensitivity
from backend.models.alert import Alert, AlertPriority, AlertType
import backend.models  # ensure all models registered

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            print("[Seed] Database already seeded. Skipping.")
            return

        # ── Stations ──────────────────────────────────────────────────────────
        stations_data = [
            ("Patna City PS", "A", 25.6128, 85.1346, "Patna City, Bihar", 28),
            ("Kankarbagh PS", "B", 25.5961, 85.1533, "Kankarbagh, Patna", 24),
            ("Gardanibagh PS","C", 25.6050, 85.1236, "Gardanibagh, Patna", 20),
            ("Boring Road PS","D", 25.6218, 85.1117, "Boring Road, Patna", 22),
            ("Phulwari PS",   "E", 25.5729, 85.1200, "Phulwari Sharif, Patna", 18),
            ("Sachivalaya PS","F", 25.6312, 85.1253, "Sachivalaya, Patna", 12),
        ]
        stations = []
        for name, zone, lat, lng, addr, cnt in stations_data:
            s = Station(name=name, zone=zone, lat=lat, lng=lng, address=addr, officer_count=cnt)
            db.add(s); stations.append(s)
        db.flush()

        # ── Users ─────────────────────────────────────────────────────────────
        users_data = [
            ("ssp.patna",     "SSP Amit Kumar Singh",  "Admin@123", UserRole.district_head,   "ADM-001",   None,          "9801234567"),
            ("so.patna",      "Insp. R.K. Sharma",     "Officer@123", UserRole.station_officer,"SI-0024",   stations[0].id,"9801234568"),
            ("so.kankarbagh", "Insp. Priya Verma",     "Officer@123", UserRole.station_officer,"SI-0031",   stations[1].id,"9801234569"),
            ("fo.deepak",     "ASI Deepak Singh",      "Field@123",  UserRole.field_officer,  "ASI-0047",  stations[1].id,"9801234570"),
            ("fo.ajay",       "ASI Ajay Pandey",       "Field@123",  UserRole.field_officer,  "ASI-0062",  stations[4].id,"9801234571"),
            ("fo.mohan",      "Const. Mohan Lal",      "Field@123",  UserRole.field_officer,  "CONST-0112",stations[2].id,"9801234572"),
            ("citizen.ravi",  "Ravi Kumar Sharma",     "Citizen@123",UserRole.citizen,         None,        None,          "9801234573"),
            ("citizen.meena", "Meena Devi",            "Citizen@123",UserRole.citizen,         None,        None,          "9801234574"),
        ]
        users = []
        for uname, fname, pwd, role, badge, sid, phone in users_data:
            u = User(username=uname, full_name=fname, password_hash=get_password_hash(pwd),
                     role=role, badge_id=badge, station_id=sid, phone=phone)
            db.add(u); users.append(u)
        db.flush()

        so_patna = users[1]; fo_deepak = users[3]

        # ── FIRs ──────────────────────────────────────────────────────────────
        firs_data = [
            ("FIR-2024-842","Murder","IPC 302","Patna City Market",25.613,85.135,"Ramesh Tiwari","9811111111",FIRStatus.under_investigation,stations[0].id,fo_deepak.id,datetime.utcnow()-timedelta(days=12)),
            ("FIR-2024-855","Missing Person","IPC 363","Boring Road",25.622,85.112,"Aarav Kumar","9822222222",FIRStatus.registered,stations[3].id,None,datetime.utcnow()-timedelta(days=2)),
            ("FIR-2024-790","Robbery","IPC 392","Kankarbagh Area",25.596,85.153,"Vijay Singh","9833333333",FIRStatus.under_investigation,stations[1].id,fo_deepak.id,datetime.utcnow()-timedelta(days=38)),
            ("FIR-2024-778","Fraud","IPC 420","Boring Road Chowk",25.621,85.111,"Anita Devi","9844444444",FIRStatus.under_investigation,stations[3].id,None,datetime.utcnow()-timedelta(days=37)),
            ("FIR-2024-801","Theft","IPC 379","Gandhi Maidan",25.620,85.140,"Suresh Kumar","9855555555",FIRStatus.closed,stations[0].id,so_patna.id,datetime.utcnow()-timedelta(days=14)),
            ("FIR-2024-812","Assault","IPC 308","Gardanibagh",25.605,85.124,"Kavita Devi","9866666666",FIRStatus.under_investigation,stations[2].id,None,datetime.utcnow()-timedelta(days=7)),
            ("FIR-2024-820","Cybercrime","IT Act 66","Sachivalaya",25.631,85.125,"Rohit Gupta","9877777777",FIRStatus.registered,stations[5].id,None,datetime.utcnow()-timedelta(days=3)),
            ("FIR-2024-835","Domestic Violence","IPC 498A","Phulwari",25.573,85.120,"Priya Singh","9888888888",FIRStatus.charge_sheet_filed,stations[4].id,users[4].id,datetime.utcnow()-timedelta(days=20)),
        ]
        for fn,ct,ipc,loc,lat,lng,cname,cphone,status,sid,oid,date in firs_data:
            db.add(FIR(fir_number=fn,crime_type=ct,ipc_section=ipc,location=loc,lat=lat,lng=lng,complainant_name=cname,complainant_phone=cphone,status=status,station_id=sid,officer_assigned_id=oid,date_filed=date,created_by_id=so_patna.id))

        # ── Complaints ────────────────────────────────────────────────────────
        complaints_data = [
            ("Kaveri Devi","9800000001","Domestic Violence","Husband assaulted me and threatened to kill me. Violence and weapons involved.",25.605,85.124,stations[2].id,ComplaintPriority.critical,85),
            ("Raju Prasad","9800000002","Bribery","Traffic officer demanded bribe of Rs 500 to clear challan. Corruption case.",25.612,85.135,stations[0].id,ComplaintPriority.high,60),
            ("Sunita Kumari","9800000003","Theft","Laptop stolen from office. CCTV footage available.",25.596,85.153,stations[1].id,ComplaintPriority.medium,35),
            ("Manoj Singh","9800000004","Noise Nuisance","Neighbor playing loud music every night.",25.621,85.112,stations[3].id,ComplaintPriority.low,8),
            ("Anjali Sinha","9800000005","Missing Person","My sister went missing from Patna Junction area.",25.620,85.140,stations[0].id,ComplaintPriority.critical,90),
        ]
        for cname,phone,ctype,desc,lat,lng,sid,priority,score in complaints_data:
            db.add(Complaint(citizen_name=cname,phone=phone,complaint_type=ctype,description=desc,lat=lat,lng=lng,location="Patna",station_id=sid,priority=priority,ai_score=score,created_by_id=users[6].id))

        # ── Custody Records ───────────────────────────────────────────────────
        custody_data = [
            ("ARR-001","Rajesh Kumar",35,"Kankarbagh","9700000001","Theft",stations[1].id,HealthStatus.stable,datetime.utcnow()-timedelta(hours=5)),
            ("ARR-002","Suresh Yadav",28,"Patna City","9700000002","Assault",stations[0].id,HealthStatus.moderate,datetime.utcnow()-timedelta(hours=2)),
            ("ARR-003","Mohammad Ali",42,"Boring Road","9700000003","Robbery",stations[3].id,HealthStatus.stable,datetime.utcnow()-timedelta(minutes=90)),
        ]
        for aid,aname,age,loc,rphone,ct,sid,hs,last_upd in custody_data:
            db.add(CustodyRecord(arrest_id=aid,accused_name=aname,accused_age=age,custody_location=loc,relative_phone=rphone,crime_type=ct,station_id=sid,officer_id=fo_deepak.id,health_status=hs,last_update_time=last_upd,arrest_date=datetime.utcnow()-timedelta(days=1)))

        # ── Feedback ──────────────────────────────────────────────────────────
        fb_data = [
            (users[6].id,stations[0].id,fo_deepak.id,"The officer was very helpful and responded quickly to my complaint.",5,FeedbackSensitivity.low,5),
            (users[7].id,stations[1].id,None,"Officer demanded bribe and was rude. Serious corruption and misconduct observed.",1,FeedbackSensitivity.critical,88),
            (users[6].id,stations[2].id,None,"Response was slow but behavior was acceptable.",3,FeedbackSensitivity.low,10),
        ]
        import hashlib
        for cid,sid,oid,text,rating,sens,score in fb_data:
            h = hashlib.md5(f"{cid}:{sid}:{oid}:{text[:50]}".encode()).hexdigest()
            db.add(Feedback(citizen_id=cid,station_id=sid,officer_id=oid,feedback_text=text,rating=rating,sensitivity=sens,ai_score=score,duplicate_check_hash=h))

        # ── Alerts ────────────────────────────────────────────────────────────
        alerts_data = [
            (AlertType.murder,   AlertPriority.critical,"Murder Case — FIR Registered","FIR-2024-842 (IPC 302). Immediate investigation team required.",stations[0].id,"fir"),
            (AlertType.missing,  AlertPriority.critical,"Missing Child Report — Urgent","Aarav Kumar (9yr) missing near Boring Road market.",stations[3].id,"fir"),
            (AlertType.custody,  AlertPriority.critical,"Custody Health Alert — No Update","ARR-001: Rajesh Kumar in custody 5.2 hrs with NO health update.",stations[1].id,"custody"),
            (AlertType.delay,    AlertPriority.high,    "FIR Delay — Charge Sheet Overdue","FIR-2024-790 (Robbery) — 38 days elapsed. Charge sheet due.",stations[1].id,"fir"),
            (AlertType.absentee, AlertPriority.high,    "Officer Off-Post Alert","Const. Ram Prasad not at assigned zone for 47 minutes.",stations[3].id,"duty"),
        ]
        for atype,priority,title,desc,sid,module in alerts_data:
            db.add(Alert(type=atype,priority=priority,title=title,description=desc,station_id=sid,module=module))

        db.commit()
        print("[Seed] ✅ Database seeded successfully!")
        print("\nDemo credentials:")
        creds = [
            ("ssp.patna",     "Admin@123",   "District Head (SSP)"),
            ("so.patna",      "Officer@123", "Station Officer — Patna City"),
            ("so.kankarbagh", "Officer@123", "Station Officer — Kankarbagh"),
            ("fo.deepak",     "Field@123",   "Field Officer"),
            ("citizen.ravi",  "Citizen@123", "Citizen"),
        ]
        for u, p, role in creds:
            print(f"  {role:35s}  username={u:20s}  password={p}")

    except Exception as e:
        db.rollback()
        print(f"[Seed] ❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
