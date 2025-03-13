import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import timedelta

from ..models import get_db
from ..models.user import User
from ..schemas.auth import UserCreate, User as UserSchema
from ..utils.auth import get_password_hash, create_access_token
from ..utils.auth import get_current_active_user, get_current_user
from config import settings
from ..services.google_calendar_service import GoogleCalendarService

# Define the OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter(tags=["authentication"], prefix="/auth")


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
    client_secrets_file = settings.GOOGLE_CLIENT_SECRETS_FILE
    scopes = settings.GOOGLE_OAUTH_SCOPES
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    auth_url = GoogleCalendarService.get_auth_url(
        client_secrets_file, scopes, redirect_uri
    )
    return {"auth_url": auth_url}


@router.get("/google-auth-callback")
async def google_auth_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        code = request.query_params.get("code")
        client_secrets_file = settings.GOOGLE_CLIENT_SECRETS_FILE
        # Calendar 스코프와 이메일/프로필 정보를 위한 스코프 추가
        scopes = settings.GOOGLE_OAUTH_SCOPES
        redirect_uri = settings.GOOGLE_REDIRECT_URI

        # InstalledAppFlow를 사용하여 코드로부터 직접 Credentials 가져오기
        from google_auth_oauthlib.flow import InstalledAppFlow

        flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
        flow.redirect_uri = redirect_uri
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # 이제 userinfo API를 사용하여 사용자 정보 가져오기
        from googleapiclient.discovery import build

        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()
        email = user_info.get("email")
        full_name = user_info.get("name", "")

        logging.info(f"Email from userinfo: {email}")
        logging.info(f"Full name from userinfo: {full_name}")

        db_user = db.query(User).filter(User.email == email).first()
        if not db_user:
            # Create new user
            db_user = User(
                username=email.split("@")[0],
                email=email,
                hashed_password="",  # No password for OAuth users
                full_name=full_name,
                is_active=True,
                is_superuser=False,
                calendar_preference="google",  # Default to Google Calendar
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)

        current_user = db_user

        # Store credentials in user-specific field in the database
        current_user.google_credentials = credentials.to_json()
        db.commit()

        # Generate JWT access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": current_user.username}, expires_delta=access_token_expires
        )

        # Return token and user info
        return {
            "message": "Google Calendar linked successfully",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "full_name": current_user.full_name,
            },
        }

    except Exception as e:
        logging.error(f"Error in google_auth_callback: {str(e)}")
        logging.exception(e)
        return JSONResponse(
            status_code=500, content={"message": f"Authentication error: {str(e)}"}
        )


@router.get("/oauth2-redirect")
async def oauth2_redirect(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Swagger UI의 OAuth2 리다이렉션을 처리하고 JWT 토큰을 자동으로 설정합니다.
    """
    try:
        # 인증 코드를 추출
        code = request.query_params.get("code")
        if not code:
            return HTMLResponse(
                content="<h1>인증 코드가 없습니다.</h1>", status_code=400
            )

        # 코드를 사용하여 Google OAuth 토큰 획득
        client_secrets_file = settings.GOOGLE_CLIENT_SECRETS_FILE
        scopes = settings.GOOGLE_OAUTH_SCOPES
        redirect_uri = "http://localhost:8000/api/docs/oauth2-redirect"  # 수정된 Swagger 리다이렉트 URI

        from google_auth_oauthlib.flow import InstalledAppFlow

        flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
        flow.redirect_uri = redirect_uri
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Google API를 사용하여 사용자 정보 가져오기
        from googleapiclient.discovery import build

        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()
        email = user_info.get("email")

        if not email:
            return HTMLResponse(
                content="<h1>사용자 이메일을 가져올 수 없습니다.</h1>", status_code=400
            )

        # 사용자 정보로 JWT 토큰 생성
        db_user = db.query(User).filter(User.email == email).first()
        if not db_user:
            # 새 사용자 생성
            db_user = User(
                username=email.split("@")[0],
                email=email,
                hashed_password="",
                full_name=user_info.get("name", ""),
                is_active=True,
                is_superuser=False,
                calendar_preference="google",
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)

        # 자격 증명 저장
        db_user.google_credentials = credentials.to_json()
        db.commit()

        # JWT 토큰 생성
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        jwt_token = create_access_token(
            data={"sub": db_user.username}, expires_delta=access_token_expires
        )

        # Swagger UI에 토큰을 전달하는 JavaScript 함수
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>인증 성공</title>
            <script>
                // OAuth 인증 성공 후 JWT 토큰을 Swagger UI에 자동으로 전달
                window.onload = function() {{
                    const token = "{jwt_token}";
                    
                    // 부모 창으로 토큰 전달
                    if (window.opener) {{
                        // Swagger UI에 토큰 설정
                        window.opener.authorizeWithJWT(token);
                        
                        // 창 닫기
                        setTimeout(function() {{
                            window.close();
                        }}, 1000);
                    }} else {{
                        document.getElementById('token-value').textContent = token;
                    }}
                }};
            </script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                h1 {{ color: #4CAF50; }}
                code {{ background-color: #f4f4f4; padding: 2px 5px; border-radius: 3px; font-family: monospace; }}
                .token {{ background-color: #f8f8f8; padding: 10px; border-radius: 4px; word-break: break-all; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>인증 성공!</h1>
                <p>
                    Google OAuth 인증이 성공적으로 완료되었습니다.
                    이제 이 창은 자동으로 닫히고 Swagger UI에서 토큰이 설정됩니다.
                </p>
                <p>토큰을 복사하여 Swagger UI에 입력하세요:</p>
                <p class="token" id="token-value">{jwt_token}</p>
                <p>이 토큰을 "Bearer {jwt_token}" 형식으로 "Authorize" 대화 상자에 입력하세요.</p>
                <button onclick="copyToken()">토큰 복사</button>
                <script>
                function copyToken() {{
                    const tokenElement = document.getElementById('token-value');
                    const range = document.createRange();
                    range.selectNode(tokenElement);
                    window.getSelection().removeAllRanges();
                    window.getSelection().addRange(range);
                    document.execCommand('copy');
                    window.getSelection().removeAllRanges();
                    alert('토큰이 클립보드에 복사되었습니다.');
                }}
                </script>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    except Exception as e:
        import logging

        logging.error(f"OAuth2 리다이렉션 처리 오류: {str(e)}")
        logging.exception(e)
        return HTMLResponse(content=f"<h1>오류 발생: {str(e)}</h1>", status_code=500)


@router.post("/token")
async def login_for_access_token(
    username: str, password: str, db: Session = Depends(get_db)
):
    from ..utils.auth import authenticate_user

    user = authenticate_user(db, username, password)
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

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
        },
    }


# 유틸리티 함수 추가 - OAuth2 토큰으로 인증하기
async def authenticate_with_oauth2_token(token: str, db: Session):
    """OAuth2 토큰으로 사용자 인증을 수행합니다."""
    try:
        # 토큰 검증 및 사용자 정보 확인
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        import json

        # JSON 문자열에서 OAuth2 자격 증명 객체 생성
        credentials = Credentials.from_authorized_user_info(json.loads(token))

        # 사용자 정보 가져오기
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()
        email = user_info.get("email")

        if not email:
            return None

        # 이메일로 사용자 찾기
        user = db.query(User).filter(User.email == email).first()
        return user
    except Exception as e:
        logging.error(f"OAuth2 인증 중 오류: {str(e)}")
        return None
