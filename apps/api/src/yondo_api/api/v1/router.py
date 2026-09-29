from fastapi import APIRouter

from yondo_api.api.health import versioned_router as health_router

router = APIRouter()
router.include_router(health_router)

