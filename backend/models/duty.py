"""Officer Duty & GPS Tracking models"""
import enum
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Enum, ForeignKey, Integer, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class DutyStatus(str, enum.Enum):
    active    = "active"
    completed = "completed"
    absent    = "absent"
    off_zone  = "off_zone"


class DutyAssignment(Base):
    __tablename__ = "duty_assignments"

    id:             Mapped[int]         = mapped_column(Integer, primary_key=True, index=True)
    officer_id:     Mapped[int]         = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    station_id:     Mapped[int]         = mapped_column(Integer, ForeignKey("stations.id"), nullable=False)
    zone:           Mapped[str]         = mapped_column(String(8), nullable=False)
    lat_assigned:   Mapped[float]       = mapped_column(Float, default=25.603)
    lng_assigned:   Mapped[float]       = mapped_column(Float, default=85.133)
    radius_km:      Mapped[float]       = mapped_column(Float, default=1.0)   # allowed radius
    start_time:     Mapped[datetime]    = mapped_column(DateTime, nullable=False)
    end_time:       Mapped[datetime]    = mapped_column(DateTime, nullable=False)
    status:         Mapped[DutyStatus]  = mapped_column(Enum(DutyStatus), default=DutyStatus.active)
    patrol_notes:   Mapped[str]         = mapped_column(Text, default="")
    crowd_event_id: Mapped[int|None]    = mapped_column(Integer, ForeignKey("crowd_events.id"), nullable=True)
    created_at:     Mapped[datetime]    = mapped_column(DateTime, default=datetime.utcnow)

    officer = relationship("User")


class GPSLog(Base):
    __tablename__ = "gps_logs"

    id:               Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    officer_id:       Mapped[int]      = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    duty_id:          Mapped[int|None] = mapped_column(Integer, ForeignKey("duty_assignments.id"), nullable=True)
    lat:              Mapped[float]    = mapped_column(Float, nullable=False)
    lng:              Mapped[float]    = mapped_column(Float, nullable=False)
    timestamp:        Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    in_zone:          Mapped[bool]     = mapped_column(Boolean, default=True)
    violation_reason: Mapped[str]      = mapped_column(String(256), default="")

    officer = relationship("User")
