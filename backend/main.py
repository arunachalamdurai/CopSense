"""
CopSense — FastAPI Application Entry Point
Run: uvicorn backend.main:app --reload --port 8000
"""
import os
import threading
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database import engine, Base, SessionLocal
from backend.services.seed import seed

# Import all models so SQLAlchemy creates their tables
import backend.models

# Import routers
from backend.routers.auth         import router as auth_router
from backend.routers.fir          import router as fir_router
from backend.routers.complaints   import router as complaints_router
from backend.routers.custody      import router as custody_router
from backend.routers.feedback     import router as feedback_router
from backend.routers.duty         import router as duty_router
from backend.routers.alerts       import router as alerts_router
from backend.routers.dashboard    import router as dashboard_router
from backend.routers.heatmap      import router as heatmap_router
from backend.routers.crowd_emergency import crowd_router, emergency_router
from backend.routers.stations      import router as stations_router


def background_alert_scanner():
    """Run AI alert scan every 60 seconds in background."""
    while True:
        time.sleep(60)
        try:
            from backend.ai.alert_engine import run_alert_scan
            db = SessionLocal()
            new_alerts = run_alert_scan(db)
            if new_alerts:
                print(f"[AlertEngine] Generated {len(new_alerts)} new alert(s)")
            db.close()
        except Exception as e:
            print(f"[AlertEngine] Error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    seed()  # only seeds if DB is empty
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "custody"), exist_ok=True)

    # Start background alert scanner in daemon thread
    scanner_thread = threading.Thread(target=background_alert_scanner, daemon=True)
    scanner_thread.start()
    print("[CopSense] API server started. Background alert scanner active.")
    yield
    # Shutdown
    print("[CopSense] Shutting down.")


app = FastAPI(
    title     = "CopSense MIS — Bihar Police",
    version   = "2.0.0",
    description="Intelligent Police Monitoring & Decision Support System",
    lifespan  = lifespan,
)

# CORS — allow frontend at any local port
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# Static file serving for uploads
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Mount all routers
app.include_router(auth_router)
app.include_router(fir_router)
app.include_router(complaints_router)
app.include_router(custody_router)
app.include_router(feedback_router)
app.include_router(duty_router)
app.include_router(alerts_router)
app.include_router(dashboard_router)
app.include_router(heatmap_router)
app.include_router(crowd_router)
app.include_router(emergency_router)
app.include_router(stations_router)


@app.get("/")
def root():
    return {
        "system":  "CopSense MIS",
        "version": "2.0.0",
        "status":  "operational",
        "docs":    "/docs",
        "district":"Patna, Bihar",
    }


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}
