
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
import os

# Define the React build path:
frontend_path = os.path.join(os.path.dirname(__file__), "..", "Frontend", "build")

if os.path.exists(frontend_path):
    # Serve React static assets:
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_path, "static")), name="react_static")

    # Add a root route so the React UI loads:
    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))

    # Wildcard catch-all for SPA routing (like /login or /count) and static files at root
    @app.get("/{file_name:path}")
    async def serve_react_app(file_name: str):
        file_path = os.path.join(frontend_path, file_name)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
            
        index_path = os.path.join(frontend_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"error": "Frontend build index.html not found"}
else:
    print(f"Warning: Frontend build folder not found at {frontend_path}. Ensure you run 'npm run build' first.")
