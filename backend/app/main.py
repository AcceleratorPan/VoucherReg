from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

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

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    storage_path = settings.local_storage_path
    storage_path.mkdir(parents=True, exist_ok=True)
    app.mount("/files", StaticFiles(directory=storage_path), name="files")

    return app


app = create_app()
