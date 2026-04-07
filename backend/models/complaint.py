"""Complaint model with AI priority"""
import enum
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Enum, ForeignKey, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class ComplaintStatus(str, enum.Enum):
    open        = "open"
    in_progress = "in_progress"
    resolved    = "resolved"
    dismissed   = "dismissed"


class ComplaintPriority(str, enum.Enum):
    low      = "low"
    medium   = "medium"
    high     = "high"
    critical = "critical"


class Complaint(Base):
    __tablename__ = "complaints"

    id:             Mapped[int]               = mapped_column(Integer, primary_key=True, index=True)
    citizen_name:   Mapped[str]               = mapped_column(String(128), nullable=False)
    phone:          Mapped[str]               = mapped_column(String(16), nullable=False)
    complaint_type: Mapped[str]               = mapped_column(String(64), nullable=False)
    description:    Mapped[str]               = mapped_column(Text, nullable=False)
    location:       Mapped[str]               = mapped_column(String(256), nullable=False)
    lat:            Mapped[float|None]        = mapped_column(Float, nullable=True)
    lng:            Mapped[float|None]        = mapped_column(Float, nullable=True)
    date:           Mapped[datetime]          = mapped_column(DateTime, default=datetime.utcnow)
    station_id:     Mapped[int]               = mapped_column(Integer, ForeignKey("stations.id"), nullable=False)
    officer_id:     Mapped[int|None]          = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    status:         Mapped[ComplaintStatus]   = mapped_column(Enum(ComplaintStatus), default=ComplaintStatus.open)
    priority:       Mapped[ComplaintPriority] = mapped_column(Enum(ComplaintPriority), default=ComplaintPriority.low)
    ai_score:       Mapped[int]               = mapped_column(Integer, default=0)
    created_by_id:  Mapped[int|None]          = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    station    = relationship("Station", back_populates="complaints")
    officer    = relationship("User", foreign_keys=[officer_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
