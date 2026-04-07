"""Auth router — register, login, profile, change password"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator, EmailStr
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.user import User, UserRole
from backend.models.station import Station
from backend.auth.jwt_handler import get_password_hash, verify_password, create_access_token
from backend.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ── Schemas ──────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username:   str
    full_name:  str
    password:   str
    role:       UserRole = UserRole.citizen
    badge_id:   str | None = None
    station_id: int | None = None
    phone:      str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

    @field_validator("username")
    @classmethod
    def username_clean(cls, v):
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        return v.lower().strip()


class LoginRequest(BaseModel):
    username: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class UserResponse(BaseModel):
    id:         int
    username:   str
    full_name:  str
    role:       str
    badge_id:   str | None
    station_id: int | None
    station_name: str | None = None
    phone:      str | None
    is_active:  bool

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/register", response_model=UserResponse, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if req.badge_id and db.query(User).filter(User.badge_id == req.badge_id).first():
        raise HTTPException(status_code=400, detail="Badge ID already registered")

    # Only citizens can self-register. Officer accounts created by admin (seeded).
    # For prototype, allow all roles via this endpoint.
    user = User(
        username      = req.username,
        full_name     = req.full_name,
        password_hash = get_password_hash(req.password),
        role          = req.role,
        badge_id      = req.badge_id,
        station_id    = req.station_id,
        phone         = req.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    station = db.query(Station).filter(Station.id == user.station_id).first() if user.station_id else None
    result = UserResponse.model_validate(user)
    result.station_name = station.name if station else None
    return result


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username.lower().strip()).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated. Contact administrator.")

    token = create_access_token(user.id, user.username, user.role.value)
    station = db.query(Station).filter(Station.id == user.station_id).first() if user.station_id else None

    return {
        "access_token": token,
        "token_type":   "bearer",
        "user": {
            "id":           user.id,
            "username":     user.username,
            "full_name":    user.full_name,
            "role":         user.role.value,
            "badge_id":     user.badge_id,
            "station_id":   user.station_id,
            "station_name": station.name if station else None,
            "photo_url":    user.photo_url,
        }
    }


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    station = db.query(Station).filter(Station.id == current_user.station_id).first() if current_user.station_id else None
    result = UserResponse.model_validate(current_user)
    result.station_name = station.name if station else None
    return result


@router.put("/change-password")
def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password too short (min 6 chars)")
    current_user.password_hash = get_password_hash(req.new_password)
    db.commit()
    return {"message": "Password changed successfully"}
