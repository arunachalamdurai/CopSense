"""Crowd Event / AI Planning model"""
import enum
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Enum, ForeignKey, Integer, Float, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class EventRiskLevel(str, enum.Enum):
    low      = "low"
    medium   = "medium"
    high     = "high"
    critical = "critical"


class CrowdEvent(Base):
    __tablename__ = "crowd_events"

    id:             Mapped[int]            = mapped_column(Integer, primary_key=True, index=True)
    name:           Mapped[str]            = mapped_column(String(256), nullable=False)
    location:       Mapped[str]            = mapped_column(String(256), nullable=False)
    lat:            Mapped[float|None]     = mapped_column(Float, nullable=True)
    lng:            Mapped[float|None]     = mapped_column(Float, nullable=True)
    event_date:     Mapped[datetime]       = mapped_column(DateTime, nullable=False)
    crowd_size:     Mapped[int]            = mapped_column(Integer, nullable=False)
    duration_hrs:   Mapped[int]            = mapped_column(Integer, default=4)
    risk_level:     Mapped[EventRiskLevel] = mapped_column(Enum(EventRiskLevel), default=EventRiskLevel.medium)
    risk_score:     Mapped[int]            = mapped_column(Integer, default=50)
    ai_blueprint:   Mapped[dict]           = mapped_column(JSON, default=dict)   # full AI deployment plan
    station_id:     Mapped[int|None]       = mapped_column(Integer, ForeignKey("stations.id"), nullable=True)
    created_by_id:  Mapped[int|None]       = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    status:         Mapped[str]            = mapped_column(String(32), default="planned")  # planned|active|completed
    deployed:       Mapped[bool]           = mapped_column(Boolean, default=False) if True else mapped_column(Integer, default=0)
    created_at:     Mapped[datetime]       = mapped_column(DateTime, default=datetime.utcnow)

    created_by = relationship("User")
