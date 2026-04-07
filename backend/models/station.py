"""Police Station model"""
from sqlalchemy import String, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class Station(Base):
    __tablename__ = "stations"

    id:            Mapped[int]   = mapped_column(Integer, primary_key=True, index=True)
    name:          Mapped[str]   = mapped_column(String(128), nullable=False)
    zone:          Mapped[str]   = mapped_column(String(8),  nullable=False)  # A-F
    lat:           Mapped[float] = mapped_column(Float, default=25.603)
    lng:           Mapped[float] = mapped_column(Float, default=85.133)
    address:       Mapped[str]   = mapped_column(String(256), default="")
    officer_count: Mapped[int]   = mapped_column(Integer, default=0)

    users       = relationship("User",      back_populates="station")
    firs        = relationship("FIR",       back_populates="station")
    complaints  = relationship("Complaint", back_populates="station")
    feedback    = relationship("Feedback",  back_populates="station")
