from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from backend.api.routes import forecast
from backend.api.routes import retrieval
from backend.api.routes import copilot
from backend.api.routes import vendors
from backend.api.routes import history
from backend.api.routes import forecast_week
from backend.api.routes import scheduler as scheduler_routes
from backend.database.db import init_db
from backend.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Starting Hawker Copilot API...")
    init_db()
    start_scheduler()
    logger.info("Database and scheduler initialized.")
    yield
    # Shutdown
    stop_scheduler()
    logger.info("Scheduler stopped. Goodbye.")


app = FastAPI(
    title="Hawker Copilot API",
    description="AI Operational Copilot for Singapore Hawkers",
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(forecast.router,         prefix="/api/v1")
app.include_router(retrieval.router,        prefix="/api/v1")
app.include_router(copilot.router,          prefix="/api/v1")
app.include_router(vendors.router,          prefix="/api/v1")
app.include_router(history.router,          prefix="/api/v1")
app.include_router(forecast_week.router,    prefix="/api/v1")
app.include_router(scheduler_routes.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "project": "Hawker Copilot",
        "version": "0.4.0",
        "layers": {
            "layer_1": "core-forecast-engine [ACTIVE]",
            "layer_2": "intelligence-retrieval [ACTIVE]",
            "layer_3": "ai-copilot [ACTIVE]",
        },
        "features": {
            "vendors": "5 preloaded + self-registration [ACTIVE]",
            "persistence": "SQLite recommendations history [ACTIVE]",
            "week_forecast": "7-day forecast chart data [ACTIVE]",
            "confidence": "weighted scoring system [ACTIVE]",
            "scheduler": "nightly alerts 19:00 SGT [ACTIVE]",
            "telegram": "vendor prep alerts [ACTIVE]",
        }
    }