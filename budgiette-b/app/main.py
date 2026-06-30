from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Temporary bootstrapping for local development.
    Base.metadata.create_all(bind=engine)
    yield


def create_application() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, version=settings.app_version, debug=settings.debug, lifespan=lifespan)
    application.include_router(api_router, prefix=settings.api_v1_prefix)

    return application


app = create_application()
