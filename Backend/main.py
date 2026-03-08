
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
os.makedirs("backend_static/results", exist_ok=True)
app.mount("/backend_static", StaticFiles(directory="backend_static"), name="backend_static")

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

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import os

# Define the path to the React build folder:
frontend_path = Path(__file__).resolve().parent.parent / "Frontend" / "build"

if frontend_path.exists():
    # Serve React static assets (JS, CSS, media) so it doesn't result in a blank screen
    app.mount("/static", StaticFiles(directory=frontend_path / "static"), name="react_static")

    # Add a catch-all route at the bottom of the file to serve the React app:
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        # Allow hitting exact files at the root (like manifest.json, logo.png)
        exact_file = frontend_path / full_path
        if exact_file.exists() and exact_file.is_file():
            return FileResponse(exact_file)
            
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Frontend build not found"}
else:
    print("Warning: Frontend build folder not found at", frontend_path)
