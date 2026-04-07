"""FIR model with validation fields"""
import enum
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Enum, ForeignKey, Integer, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class FIRStatus(str, enum.Enum):
    registered           = "registered"
    under_investigation  = "under_investigation"
    charge_sheet_filed   = "charge_sheet_filed"
    closed               = "closed"


class FIR(Base):
    __tablename__ = "firs"

    id:                Mapped[int]       = mapped_column(Integer, primary_key=True, index=True)
    fir_number:        Mapped[str]       = mapped_column(String(32), unique=True, index=True, nullable=False)
    crime_type:        Mapped[str]       = mapped_column(String(64), nullable=False)
    ipc_section:       Mapped[str]       = mapped_column(String(32), default="")
    location:          Mapped[str]       = mapped_column(String(256), nullable=False)
    lat:               Mapped[float|None]= mapped_column(Float, nullable=True)
    lng:               Mapped[float|None]= mapped_column(Float, nullable=True)
    complainant_name:  Mapped[str]       = mapped_column(String(128), nullable=False)
    complainant_phone: Mapped[str]       = mapped_column(String(16), default="")
    description:       Mapped[str]       = mapped_column(Text, default="")
    officer_assigned_id: Mapped[int|None]= mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    station_id:        Mapped[int]       = mapped_column(Integer, ForeignKey("stations.id"), nullable=False)
    status:            Mapped[FIRStatus] = mapped_column(Enum(FIRStatus), default=FIRStatus.registered)
    evidence_attached: Mapped[bool]      = mapped_column(Boolean, default=False)
    evidence_path:     Mapped[str|None]  = mapped_column(String(256), nullable=True)
    date_filed:        Mapped[datetime]  = mapped_column(DateTime, default=datetime.utcnow)
    updated_at:        Mapped[datetime]  = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id:     Mapped[int|None]  = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    station          = relationship("Station", back_populates="firs")
    officer_assigned = relationship("User", foreign_keys=[officer_assigned_id])
    created_by       = relationship("User", foreign_keys=[created_by_id])
