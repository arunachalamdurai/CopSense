"""System Alert model"""
import enum
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Enum, ForeignKey, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class AlertPriority(str, enum.Enum):
    critical = "critical"
    high     = "high"
    warning  = "warning"
    info     = "info"


class AlertType(str, enum.Enum):
    murder        = "murder"
    missing       = "missing"
    custody       = "custody"
    delay         = "delay"
    absentee      = "absentee"
    complaint     = "complaint"
    violence      = "violence"
    gps_violation = "gps_violation"
    feedback      = "feedback"
    resolved      = "resolved"


class Alert(Base):
    __tablename__ = "alerts"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, index=True)
    type:        Mapped[AlertType]     = mapped_column(Enum(AlertType), nullable=False)
    priority:    Mapped[AlertPriority] = mapped_column(Enum(AlertPriority), nullable=False)
    title:       Mapped[str]           = mapped_column(String(256), nullable=False)
    description: Mapped[str]           = mapped_column(Text, default="")
    station_id:  Mapped[int|None]      = mapped_column(Integer, ForeignKey("stations.id"), nullable=True)
    officer_id:  Mapped[int|None]      = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    module:      Mapped[str]           = mapped_column(String(32), default="system")  # fir|custody|complaint|duty
    ref_id:      Mapped[int|None]      = mapped_column(Integer, nullable=True)        # reference to source record
    resolved:    Mapped[bool]          = mapped_column(Boolean, default=False)
    created_at:  Mapped[datetime]      = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime|None] = mapped_column(DateTime, nullable=True)

    station = relationship("Station")
    officer = relationship("User")
