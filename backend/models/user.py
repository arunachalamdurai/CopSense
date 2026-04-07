"""User model with RBAC roles"""
import enum
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class UserRole(str, enum.Enum):
    district_head   = "district_head"
    station_officer = "station_officer"
    field_officer   = "field_officer"
    citizen         = "citizen"


class User(Base):
    __tablename__ = "users"

    id:            Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    username:      Mapped[str]      = mapped_column(String(64), unique=True, index=True, nullable=False)
    full_name:     Mapped[str]      = mapped_column(String(128), nullable=False)
    badge_id:      Mapped[str|None] = mapped_column(String(32), unique=True, nullable=True)
    password_hash: Mapped[str]      = mapped_column(String(256), nullable=False)
    role:          Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    station_id:    Mapped[int|None] = mapped_column(Integer, ForeignKey("stations.id"), nullable=True)
    is_active:     Mapped[bool]     = mapped_column(Boolean, default=True)
    created_at:    Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    phone:         Mapped[str|None] = mapped_column(String(16), nullable=True)
    photo_url:     Mapped[str|None] = mapped_column(String(256), nullable=True)

    station = relationship("Station", back_populates="users")

    def __repr__(self):
        return f"<User {self.username} [{self.role}]>"
