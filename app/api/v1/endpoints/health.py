from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthRead

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthRead)
def health() -> HealthRead:
    settings = get_settings()
    return HealthRead(status="ok", app=settings.app_name, version=settings.app_version)
