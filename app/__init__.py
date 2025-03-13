from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel, OAuth2 as OAuth2Model
from fastapi.openapi.docs import get_swagger_ui_html
import os
from pathlib import Path
from config import settings

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Personal Calendar Agent API",
    version="0.1.0",
    docs_url=None,  # Disable default docs to use custom docs
    redoc_url=None,  # Disable ReDoc
    openapi_url="/api/openapi.json",
)

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up templates
templates = Jinja2Templates(directory="app/templates")

# Mount static files
static_path = Path("app/static")
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Import API routes
from .routes import auth, events, tasks, agent

# Include API routes
app.include_router(auth.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(agent.router, prefix="/api")

# Add OAuth2 authentication
oauth2_scheme = OAuth2Model(
    flows=OAuthFlowsModel(
        authorizationCode={
            "authorizationUrl": "https://accounts.google.com/o/oauth2/auth",
            "tokenUrl": "https://oauth2.googleapis.com/token",
            "scopes": {
                "openid": "OpenID Connect scope",
                "email": "Access to your email address",
                "profile": "Access to your profile information",
                "https://www.googleapis.com/auth/calendar": "Access to your Google Calendar",
            },
        }
    )
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version="0.1.0",
        description="Personal Calendar Agent API",
        routes=app.routes,
    )

    # 단일 OAuth2 보안 스키마 정의
    oauth2_scheme = {
        "type": "oauth2",
        "flows": {
            "authorizationCode": {
                "authorizationUrl": "https://accounts.google.com/o/oauth2/auth",
                "tokenUrl": "https://oauth2.googleapis.com/token",
                "scopes": {
                    "openid": "OpenID Connect scope",
                    "email": "Access to your email address",
                    "profile": "Access to your profile information",
                    "https://www.googleapis.com/auth/calendar": "Access to your Google Calendar",
                },
            }
        },
    }

    # OpenAPI 스키마에 보안 스키마 추가
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}

    openapi_schema["components"]["securitySchemes"] = {"OAuth2": oauth2_scheme}

    # 전역 보안 설정 추가 - 모든 API에 적용
    openapi_schema["security"] = [{"OAuth2": []}]

    # 각 경로별 보안 설정을 일관되게 적용
    for path in openapi_schema.get("paths", {}).values():
        for operation in path.values():
            operation["security"] = [{"OAuth2": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Custom Swagger UI with OAuth2 auto-token functionality
from fastapi.responses import HTMLResponse
from fastapi import Request


@app.get("/api/docs", include_in_schema=False)
async def custom_swagger_ui_html(request: Request):
    """
    커스텀 Swagger UI 제공
    - OAuth2 인증 후 토큰을 자동으로 설정하는 기능이 추가됨
    """
    openapi_url = app.openapi_url
    title = app.title + " - API Documentation"

    # authorizeWithJWT 함수를 추가하여 JWT 토큰으로 자동 인증
    custom_js = """
    <script>
    // OAuth2 인증 후 JWT 토큰을 설정하는 함수
    window.authorizeWithJWT = function(token) {
        try {
            // Swagger UI의 Auth 버튼을 찾아 토큰 설정
            const authBtn = document.querySelector('.btn.authorize');
            if (authBtn) {
                authBtn.click();
                
                // 모달이 열릴 때까지 약간 대기
                setTimeout(() => {
                    // Bearer 토큰 입력 필드 채우기
                    const tokenField = document.querySelector('.auth-container input[type="text"]');
                    if (tokenField) {
                        tokenField.value = 'Bearer ' + token;
                        
                        // Authorize 버튼 클릭
                        const authorizeBtn = document.querySelector('.auth-btn-wrapper button.btn.modal-btn.auth.authorize.button');
                        if (authorizeBtn) {
                            authorizeBtn.click();
                            
                            // 모달 닫기 버튼 클릭
                            setTimeout(() => {
                                const closeBtn = document.querySelector('.btn-done.btn.modal-btn.button');
                                if (closeBtn) {
                                    closeBtn.click();
                                    console.log('JWT 토큰 자동 설정 성공!');
                                }
                            }, 300);
                        }
                    }
                }, 300);
            }
        } catch (e) {
            console.error('JWT 토큰 자동 설정 실패:', e);
        }
    };
    </script>
    """

    # get_swagger_ui_html을 사용하여 기본 Swagger UI HTML 생성
    swagger_ui_html = get_swagger_ui_html(
        openapi_url=openapi_url,
        title=title,
        oauth2_redirect_url="/api/docs/oauth2-redirect",
        init_oauth={
            "clientId": "276361238447-j2m5lflm6l6dhrel13tmquj3adfhjf6t.apps.googleusercontent.com",
            "usePkceWithAuthorizationCodeGrant": True,
            "useBasicAuthenticationWithAccessCodeGrant": True,
        },
    )

    # 커스텀 JavaScript 코드 추가
    html_content = swagger_ui_html.body.decode("utf-8")
    html_content = html_content.replace("</head>", f"{custom_js}</head>")

    return HTMLResponse(content=html_content)


# Initialize database
from .models import Base, engine

Base.metadata.create_all(bind=engine)
