from fastapi import APIRouter

from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.dashboard import router as dashboard_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.portal import router as portal_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.ssi import router as ssi_router
from app.api.v1.endpoints.units import router as units_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(dashboard_router)
api_router.include_router(ssi_router)
api_router.include_router(units_router)
api_router.include_router(analytics_router)
api_router.include_router(reports_router)
api_router.include_router(portal_router)
