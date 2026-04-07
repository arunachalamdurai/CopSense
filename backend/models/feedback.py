"""Feedback model with NLP sensitivity classification"""
import enum
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Enum, ForeignKey, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class FeedbackSensitivity(str, enum.Enum):
    low      = "low"
    medium   = "medium"
    high     = "high"
    critical = "critical"


class Feedback(Base):
    __tablename__ = "feedback"

    id:                   Mapped[int]                 = mapped_column(Integer, primary_key=True, index=True)
    citizen_id:           Mapped[int|None]            = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    station_id:           Mapped[int]                 = mapped_column(Integer, ForeignKey("stations.id"), nullable=False)
    officer_id:           Mapped[int|None]            = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    feedback_text:        Mapped[str]                 = mapped_column(Text, nullable=False)
    feedback_type:        Mapped[str]                 = mapped_column(String(32), default="officer")  # officer|station|multiple
    rating:               Mapped[int]                 = mapped_column(Integer, default=3)            # 1-5
    sensitivity:          Mapped[FeedbackSensitivity] = mapped_column(Enum(FeedbackSensitivity), default=FeedbackSensitivity.low)
    ai_score:             Mapped[int]                 = mapped_column(Integer, default=0)
    submitted_at:         Mapped[datetime]            = mapped_column(DateTime, default=datetime.utcnow)
    duplicate_check_hash: Mapped[str]                 = mapped_column(String(64), index=True, default="")
    is_anonymous:         Mapped[bool]                = mapped_column(Boolean, default=False)
    alert_sent:           Mapped[bool]                = mapped_column(Boolean, default=False)

    citizen = relationship("User", foreign_keys=[citizen_id])
    officer = relationship("User", foreign_keys=[officer_id])
    station = relationship("Station", back_populates="feedback")
