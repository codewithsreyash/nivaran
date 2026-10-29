"""FastAPI dependency injection helpers."""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .database import get_db
from .models import User, UserRole
from .auth import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_roles(*roles: UserRole):
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in roles]}"
            )
        return current_user
    return checker


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_not_readonly(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role == UserRole.READ_ONLY:
        raise HTTPException(status_code=403, detail="Read-only users cannot perform this action")
    return current_user


GLOBAL_BUREAU_ROLES = {UserRole.ADMIN, UserRole.SUPERVISORY_REVIEWER}
SCOPED_BUREAU_ROLES = {UserRole.BUREAU_OFFICER, UserRole.READ_ONLY}


def get_bureau_scope(current_user: User) -> Optional[int]:
    """Return None for explicitly global roles, otherwise require a bureau."""
    if current_user.role in GLOBAL_BUREAU_ROLES:
        return None
    if current_user.role in SCOPED_BUREAU_ROLES and current_user.bureau_id is not None:
        return current_user.bureau_id
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="A bureau assignment is required for access",
    )


def ensure_bureau_access(current_user: User, bureau_id: Optional[int]) -> None:
    """Deny access outside a user's bureau; null ownership is not a bypass."""
    scope = get_bureau_scope(current_user)
    if scope is not None and bureau_id != scope:
        if current_user.role == UserRole.BUREAU_OFFICER:
            detail = f"Complaint is assigned to Bureau {bureau_id}, but officer belongs to Bureau {scope}"
        else:
            detail = "Access denied outside assigned bureau"
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def scope_query_to_bureau(query, bureau_column, current_user: User):
    """Apply mandatory row scope to a query; global roles retain existing visibility."""
    scope = get_bureau_scope(current_user)
    return query if scope is None else query.filter(bureau_column == scope)
