"""
AICTE OneView — FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import atexit

from .config import get_settings
from .database import engine, Base

# Import all models so they are registered with SQLAlchemy metadata
from .models import *  # noqa: F401, F403

from .api.auth import router as auth_router
from .api.institutions import router as inst_router
from .api.complaints import router as complaint_router
from .api.graph import router as graph_router
from .api.misc import (
    dashboard_router, priority_router, overlap_router,
    deadlines_router, notifications_router, users_router,
    audit_router, reports_router, bureaus_router, inactivity_router
)

settings = get_settings()

# Create tables (checkfirst=True prevents errors on existing indexes/tables)
Base.metadata.create_all(bind=engine, checkfirst=True)

# Create upload dir
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="AICTE OneView API",
    description=(
        "Integrated Dashboard for Monitoring and Tracking Institution-Related "
        "Complaint Cases Across AICTE Bureaus/Cells.\n\n"
        "**Data notice**: All complaint records in this demonstration are "
        "synthetic. No real AICTE complaint data is used."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS
origins_env = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
origins = [o.strip() for o in origins_env if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
for router in [
    auth_router, inst_router, complaint_router, graph_router,
    dashboard_router, priority_router, overlap_router,
    deadlines_router, notifications_router, users_router,
    audit_router, reports_router, bureaus_router, inactivity_router,
]:
    app.include_router(router)


from .ml.model_registry import get_model_status
from .services.scheduler_service import start_scheduler, stop_scheduler, get_scheduler_status

# Start scheduler on application startup
@app.on_event("startup")
def startup_event():
    start_scheduler()

# Stop scheduler on application shutdown
@app.on_event("shutdown")
def shutdown_event():
    stop_scheduler()

# Register cleanup for atexit (for development server scenarios)
atexit.register(stop_scheduler)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": "AICTE OneView",
        "version": "1.0.0",
        "detector_type": "rules_baseline",
        "algorithm_version": "rules-v1",
        "ml_status": "Rules-based baseline active. No ML model trained.",
        "data_notice": "All complaint records are Synthetic Demonstration Data.",
    }


@app.get("/api/ml/status")
def ml_status():
    return get_model_status()


@app.get("/api/scheduler/status")
def scheduler_status():
    """Get scheduler status for monitoring."""
    return get_scheduler_status()

