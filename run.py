import uvicorn
import os
from app import app
from config import settings

if __name__ == "__main__":
    # Run the application with uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=settings.APP_ENV != "production",
        workers=1 if settings.APP_ENV != "production" else 4
    )