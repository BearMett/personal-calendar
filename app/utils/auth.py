from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from config import settings
from ..models import get_db
from ..models.user import User

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 setup with token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate a user by username and password."""
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


async def get_user_from_token(token: str, db: Session) -> Optional[User]:
    """JWT 토큰에서 사용자 가져오기"""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            return None
        user = db.query(User).filter(User.username == username).first()
        return user
    except JWTError:
        return None


async def get_user_from_oauth2(authorization: str, db: Session) -> Optional[User]:
    """OAuth2 토큰에서 사용자 가져오기 (Google 인증 정보 사용)"""
    if not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "")

    # DB에서 이 토큰을 사용하는 사용자 찾기
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        import json

        # 모든 사용자 조회
        users = db.query(User).filter(User.google_credentials.isnot(None)).all()

        # 각 사용자의 토큰으로 인증 시도
        for user in users:
            try:
                credentials_json = json.loads(user.google_credentials)
                if credentials_json.get("token") == token:
                    return user
            except:
                continue

        return None
    except Exception as e:
        import logging

        logging.error(f"OAuth2 인증 중 오류: {str(e)}")
        return None


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """현재 인증된 사용자 가져오기 - JWT 또는 OAuth2 인증 지원"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Authorization 헤더에서 토큰 추출
    authorization = request.headers.get("Authorization", "")
    if not authorization:
        # 토큰이 없으면 Swagger에서 제공하는 OAuth2 토큰을 확인
        raise credentials_exception

    # JWT 토큰으로 인증 시도
    user = await get_user_from_token(authorization.replace("Bearer ", ""), db)

    # JWT 인증 실패 시 OAuth2 인증 시도
    if user is None:
        user = await get_user_from_oauth2(authorization, db)

    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Check if current user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user
