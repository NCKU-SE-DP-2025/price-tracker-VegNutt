from datetime import timedelta
from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import TokenResponse, UserCreate, UserResponse
from app.api.security import create_access_token, get_current_user
from app.core.config import settings
from app.db.database import get_db_session
from app.models import User
from app.services import AuthService


router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db_session)):
    """Register a new user."""
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    return AuthService.create_user(db, user.username, user.password)


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: dict = Depends(lambda: {"username": "", "password": ""}),
    db: Session = Depends(get_db_session),
):
    """Login and get access token."""
    # Note: In production, use OAuth2PasswordRequestForm
    from fastapi.security import OAuth2PasswordRequestForm
    
    # Placeholder - should receive form_data from OAuth2PasswordRequestForm
    username = form_data.get("username", "")
    password = form_data.get("password", "")
    
    user = AuthService.authenticate_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_user_me(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user
