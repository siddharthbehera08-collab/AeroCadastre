from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import (
    verify_password,
    create_access_token,
    require_authenticated_user,
)
from backend.app.models.entities import User
from backend.app.schemas.api_schemas import LoginRequest, TokenResponse, UserResponse

router = APIRouter(tags=["Authentication"])


@router.post("/api/auth/token", response_model=TokenResponse)
@router.post("/api/auth/login", response_model=TokenResponse)
def login_for_access_token(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    token = create_access_token(subject=user.email, role=user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
    }


@router.get("/api/auth/me", response_model=UserResponse)
def get_current_user_profile(
    claims: dict = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == claims["sub"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authenticated user record not found.",
        )
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "department": user.department,
        "is_active": user.is_active,
    }
