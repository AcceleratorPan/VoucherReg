from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request

from app.api.error_handlers import register_exception_handlers
from app.api.router import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        Path("./data").mkdir(parents=True, exist_ok=True)
        yield

    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

    # Add debug middleware
    @app.middleware("http")
    async def debug_middleware(request: Request, call_next):
        print(f"DEBUG: {request.method} {request.url.path}")
        response = await call_next(request)
        print(f"DEBUG: Response status {response.status_code}")
        return response

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    return app


app = create_app()
