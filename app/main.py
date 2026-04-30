import asyncio
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

_HARVEST_INTERVAL_SECONDS = 24 * 60 * 60  # 24 hours


async def _nightly_harvesting_loop() -> None:
    """Background task: recompute per-student engagement baselines once per day."""
    while True:
        await asyncio.sleep(_HARVEST_INTERVAL_SECONDS)
        try:
            # Import lazily to avoid circular import at module level
            from app.services.pedagogical_agent import PedagogicalAgentService
            agent = PedagogicalAgentService(
                snapshots=seed_data.engagement_snapshots,
                feedback_log=seed_data.agent_feedback_log,
                video_log_dir=settings.video_log_dir,
            )
            baselines = agent.compute_daily_baselines()
            logger.info(
                "Daily knowledge harvesting complete: %d student baseline(s) updated",
                len(baselines),
            )
        except Exception:  # noqa: BLE001
            logger.exception("Daily knowledge harvesting failed")


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

    # Start nightly engagement baseline harvesting task (Unit 15)
    harvest_task = asyncio.create_task(_nightly_harvesting_loop())
    logger.info("Unit 15 nightly harvesting task scheduled (interval: 24h)")

    try:
        yield
    finally:
        harvest_task.cancel()
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
