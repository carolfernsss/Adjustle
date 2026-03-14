
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import logging
from pathlib import Path

# making the logs less messy
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.CRITICAL)


from Backend.authentication import auth_router as auth_router
from Backend.scheduling import scheduling_router as scheduling_router
from Backend.ai_module import ai_router as ai_router
from Backend.notification import router as notification_router
from Backend.database import init_db, close_db, db, users_table, timetable_table, _seed_timetable_grid, _seed_schedule_alerts


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
    # printing startup messages
    print("Database is initializing...")
    await init_db()
    
    # adding default login accounts
    default_users = [
        {"username": "BCATeacher", "password": "Teacher123@", "branch": "BCA", "role": "teacher"},
        {"username": "BCADATeacher", "password": "Teacher123@", "branch": "BCADA", "role": "teacher"},
        {"username": "Carol", "password": "Carol18@", "branch": "BCA", "role": "student"},
        {"username": "Jerusha", "password": "Jerusha02@", "branch": "BCADA", "role": "student"},
    ]
    for u in default_users:
        query = users_table.select().where(users_table.c.username == u["username"])
        existing_user = await db.fetch_one(query)
        if not existing_user:
            await db.execute(users_table.insert().values(**u))
            print(f"Seeded user: {u['username']}")

    # Seeding timetable if empty
    tt_count = await db.fetch_val("SELECT COUNT(*) FROM timetable")
    if tt_count == 0:
        print("Timetable is empty. Seeding initial data...")
        await _seed_timetable_grid()
        await _seed_schedule_alerts()
        print("Timetable seeded successfully.")

    print("ADJUSTLE BACKEND IS READY")

@app.on_event("shutdown")
async def shutdown_event():
    await close_db()

# making folders for image results
os.makedirs("backend_static/results", exist_ok=True)
app.mount("/backend_static", StaticFiles(directory="backend_static"), name="backend_static")

# connecting all the different api parts
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

# showing the react pages from the build folder
frontend_path = Path(__file__).resolve().parent.parent / "Frontend" / "build"
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
