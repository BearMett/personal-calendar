from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..models import get_db
from ..models.user import User
from ..schemas.auth import Token, UserCreate, User as UserSchema, LoginRequest
from ..utils.auth import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_password_hash,
)
from config import settings
from ..services.google_calendar_service import GoogleCalendarService

router = APIRouter(tags=["authentication"], prefix="/auth")


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """Get JWT token for authentication."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login using JSON request."""
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post(
    "/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED
)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if username already exists
    db_user = db.query(User).filter(User.username == user_data.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Check if email already exists
    db_user_email = db.query(User).filter(User.email == user_data.email).first()
    if db_user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=True,
        is_superuser=False,
        calendar_preference=user_data.calendar_preference,  # Add calendar preference
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user


@router.get("/google-auth-url")
async def get_google_auth_url():
    """Get Google OAuth2 authorization URL."""
    client_secrets_file = "path/to/client_secrets.json"
    scopes = ["https://www.googleapis.com/auth/calendar"]
    auth_url = GoogleCalendarService.get_auth_url(client_secrets_file, scopes)
    return {"auth_url": auth_url}


@router.get("/google-auth-callback")
async def google_auth_callback(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Handle Google OAuth2 callback and exchange code for tokens."""
    code = request.query_params.get("code")
    client_secrets_file = "path/to/client_secrets.json"
    scopes = ["https://www.googleapis.com/auth/calendar"]
    credentials = GoogleCalendarService.get_credentials_from_code(
        client_secrets_file, scopes, code
    )
    # Store credentials in the database or user session
    # Example: current_user.google_credentials = credentials
    # db.commit()
    return {"message": "Google Calendar linked successfully"}
