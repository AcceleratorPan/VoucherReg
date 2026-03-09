from fastapi import APIRouter

from app.api.routes.downloads import router as downloads_router
from app.api.routes.files import router as files_router
from app.api.routes.health import router as health_router
from app.api.routes.voucher_tasks import router as voucher_tasks_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(files_router, tags=["files"])
api_router.include_router(downloads_router, tags=["downloads"])
api_router.include_router(voucher_tasks_router, tags=["voucher-tasks"])
