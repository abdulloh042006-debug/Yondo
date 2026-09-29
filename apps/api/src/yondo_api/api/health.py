from typing import Protocol

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


class HealthCheck(Protocol):
    async def __call__(self) -> bool: ...


class DatabaseHealthCheck:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def __call__(self) -> bool:
        async with self.engine.connect() as connection:
            await connection.execute(text('SELECT 1'))
        return True


class RedisHealthCheck:
    def __init__(self, client: object) -> None:
        self.client = client

    async def __call__(self) -> bool:
        return bool(await self.client.ping())  # type: ignore[attr-defined]


class LivenessResponse(BaseModel):
    status: str
    service: str
    version: str


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str]


public_router = APIRouter()
versioned_router = APIRouter(prefix='/health', tags=['health'])


@public_router.get('/health', response_model=LivenessResponse)
async def liveness(request: Request) -> LivenessResponse:
    settings = request.app.state.settings
    return LivenessResponse(status='ok', service=settings.app_name, version=settings.app_version)


@versioned_router.get('/ready', response_model=ReadinessResponse)
async def readiness(request: Request):
    results: dict[str, str] = {}
    healthy = True
    for name, check in request.app.state.readiness_checks.items():
        try:
            results[name] = 'ok' if await check() else 'unavailable'
        except Exception:
            results[name] = 'unavailable'
        healthy = healthy and results[name] == 'ok'

    response = ReadinessResponse(status='ok' if healthy else 'unavailable', checks=results)
    if healthy:
        return response
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response.model_dump(),
    )
