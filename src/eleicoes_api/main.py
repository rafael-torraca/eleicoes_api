from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from eleicoes_api.api.exception_handlers import (
    register_exception_handlers,
)
from eleicoes_api.api.middleware import RequestLoggingMiddleware
from eleicoes_api.api.routes.elections import router as elections_router
from eleicoes_api.api.routes.health import router as health_router
from eleicoes_api.core.config import get_settings
from eleicoes_api.core.logging_config import configure_logging
from eleicoes_api.infrastructure.tse.client import TSEClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    app.state.tse_client = TSEClient(
        timeout=settings.tse_http_timeout,
        cache_ttl=settings.tse_cache_ttl,
        max_cache_entries=settings.tse_cache_max_entries,
    )

    try:
        yield
    finally:
        await app.state.tse_client.close()


def create_app() -> FastAPI:
    settings = get_settings()

    configure_logging(settings.environment)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=settings.app_description,
        lifespan=lifespan,
    )

    register_exception_handlers(app)

    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(health_router)
    app.include_router(elections_router)

    return app


app = create_app()
