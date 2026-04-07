"""FastAPI dependency for JWT auth + RBAC"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.auth.jwt_handler import decode_token
from backend.models.user import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload  = decode_token(credentials.credentials)
        user_id  = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user

def require_roles(*roles: UserRole):
    """Returns a dependency that restricts access to given roles."""
    def _check(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in roles]}"
            )
        return current_user
    return _check

# Pre-built role guards
require_district_head   = require_roles(UserRole.district_head)
require_station_or_above = require_roles(UserRole.district_head, UserRole.station_officer)
require_field_or_above   = require_roles(UserRole.district_head, UserRole.station_officer, UserRole.field_officer)
require_citizen          = require_roles(UserRole.citizen)
