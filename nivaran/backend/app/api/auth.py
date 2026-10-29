"""Authentication API routes."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth import authenticate_user, create_access_token
from ..dependencies import get_current_user
from ..schemas import LoginRequest, Token, UserOut
from ..models import User
from ..services.audit_service import log_action

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db), request: Request = None):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token({"sub": str(user.id)})
    log_action(db, "user.login", user_id=user.id, resource_type="user",
               resource_id=user.id, ip_address=request.client.host if request else None)
    return Token(access_token=token, token_type="bearer", user=UserOut.model_validate(user))


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    log_action(db, "user.logout", user_id=current_user.id, resource_type="user",
               resource_id=current_user.id)
    return {"detail": "Logged out successfully"}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)
