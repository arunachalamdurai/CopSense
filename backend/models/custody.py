"""Custody Safety model"""
import enum
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Enum, ForeignKey, Integer, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class HealthStatus(str, enum.Enum):
    stable   = "stable"
    moderate = "moderate"
    critical = "critical"
    released = "released"


class CustodyRecord(Base):
    __tablename__ = "custody_records"

    id:               Mapped[int]          = mapped_column(Integer, primary_key=True, index=True)
    arrest_id:        Mapped[str]          = mapped_column(String(32), unique=True, index=True, nullable=False)
    accused_name:     Mapped[str]          = mapped_column(String(128), nullable=False)
    accused_age:      Mapped[int|None]     = mapped_column(Integer, nullable=True)
    accused_address:  Mapped[str]          = mapped_column(String(256), default="")
    arrest_date:      Mapped[datetime]     = mapped_column(DateTime, nullable=False)
    custody_location: Mapped[str]          = mapped_column(String(256), nullable=False)
    relative_name:    Mapped[str]          = mapped_column(String(128), default="")
    relative_phone:   Mapped[str]          = mapped_column(String(16), nullable=False)  # REQUIRED
    crime_type:       Mapped[str]          = mapped_column(String(64), default="")
    ipc_section:      Mapped[str]          = mapped_column(String(32), default="")
    officer_id:       Mapped[int]          = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    station_id:       Mapped[int]          = mapped_column(Integer, ForeignKey("stations.id"), nullable=False)
    health_status:    Mapped[HealthStatus] = mapped_column(Enum(HealthStatus), default=HealthStatus.stable)
    last_update_time: Mapped[datetime]     = mapped_column(DateTime, default=datetime.utcnow)
    video_uploads:    Mapped[list]         = mapped_column(JSON, default=list)   # [{url, timestamp, note}]
    alert_sent:       Mapped[bool]         = mapped_column(Boolean, default=False)
    is_released:      Mapped[bool]         = mapped_column(Boolean, default=False)
    notes:            Mapped[str]          = mapped_column(Text, default="")
    created_at:       Mapped[datetime]     = mapped_column(DateTime, default=datetime.utcnow)

    officer = relationship("User")
