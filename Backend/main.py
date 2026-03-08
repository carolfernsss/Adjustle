
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import logging

# Silence uvicorn access logs but keep essential startup information
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.CRITICAL)


from Backend.authentication import auth_router as auth_router
from Backend.scheduling import scheduling_router as scheduling_router
from Backend.ai_module import ai_router as ai_router
from Backend.notification import router as notification_router
from Backend.database import init_db, close_db


app = FastAPI(
    title="Adjustle API",
    description="AI-driven timetable application with attendance tracking",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Only keep critical messages as requested
    print("Database is initializing...")
    await init_db()
    print("ADJUSTLE BACKEND IS READY")

@app.on_event("shutdown")
async def shutdown_event():
    await close_db()

# // Ensure the static directory exists for storing uploaded images and results
os.makedirs("static/results", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# // Include all the sub-routers for different modules of the application
app.include_router(auth_router, tags=["Authentication"])
app.include_router(scheduling_router, tags=["Scheduling"])
app.include_router(ai_router, tags=["AI Module"])
app.include_router(notification_router, tags=["Notifications"])

@app.get("/api")
def root():
    return {
        "name": "Adjustle API",
        "version": "1.0.0",
        "description": "AI-driven timetable application",
        "modules": [
            "Authentication",
            "AI Module (YOLO)",
            "Scheduling",
            "Notifications"
        ]
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

from pathlib import Path

# Serve the React Frontend Build Directory
frontend_build_path = Path(__file__).resolve().parent.parent / "Frontend" / "build"

if frontend_build_path.exists():
    # Mount the React 'static' folder (JS/CSS)
    react_static = frontend_build_path / "static"
    if react_static.exists():
        app.mount("/static/js", StaticFiles(directory=react_static / "js"), name="react_js")
        app.mount("/static/css", StaticFiles(directory=react_static / "css"), name="react_css")
        app.mount("/static/media", StaticFiles(directory=react_static / "media"), name="react_media")

    # Serve files directly from the build root (like manifest.json, favicon.ico)
    @app.get("/{file_name:path}")
    async def serve_react_app(file_name: str):
        file_path = frontend_build_path / file_name
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
            
        # Fallback to index.html for React Router (Single Page Application)
        index_path = frontend_build_path / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"error": "Frontend build index.html not found"}
else:
    print(f"Warning: Frontend build folder not found at {frontend_build_path}. Ensure you run 'npm run build' first.")
