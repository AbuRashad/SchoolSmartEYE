import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.services import seed_data
from app.services.camera_ingestion import ingestion_service


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Populate demo seed data and start live camera ingestion on startup."""
    logger.info("Application startup initiated", extra={"app_env": settings.app_env})
    seed_data.populate()
    logger.info("Seed data population complete")

    # Live camera ingestion — only activates if cameras_sources_file exists.
    loaded = ingestion_service.load_from_file(settings.camera_sources_file)
    if loaded:
        logger.info("Live camera ingestion active: %d camera(s)", loaded)
    else:
        logger.info(
            "No live cameras configured (looked for %s). Running in demo mode.",
            settings.camera_sources_file,
        )

    try:
        yield
    finally:
        ingestion_service.stop_all()
        logger.info("Application shutdown complete")


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_str)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": settings.app_name}
