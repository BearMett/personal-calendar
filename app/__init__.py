from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from pathlib import Path

from ..config import settings

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Personal Calendar Agent API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
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

# Initialize database
from .models import Base, engine
Base.metadata.create_all(bind=engine)