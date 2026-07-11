import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.models import IngestionMailbox, User
from app.services.ingestion_service import sync_mailbox
from app.services.notification_service import check_all

logger = logging.getLogger(__name__)


def sync_all_active_mailboxes() -> None:
    db = SessionLocal()
    try:
        mailboxes = db.execute(select(IngestionMailbox).where(IngestionMailbox.is_active)).scalars().all()
        for mailbox in mailboxes:
            try:
                sync_mailbox(db, mailbox)
            except Exception:
                logger.exception("Scheduled sync failed for mailbox %s", mailbox.id)
    finally:
        db.close()


def run_notification_checks() -> None:
    db = SessionLocal()
    try:
        user_ids = db.execute(select(User.id).where(User.is_active)).scalars().all()
        for user_id in user_ids:
            check_all(db, user_id)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Temporary bootstrapping for local development.
    Base.metadata.create_all(bind=engine)

    settings = get_settings()
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        sync_all_active_mailboxes,
        "interval",
        minutes=settings.sync_interval_minutes,
        id="sync_active_mailboxes",
    )
    scheduler.add_job(
        run_notification_checks,
        "interval",
        minutes=settings.notification_check_interval_minutes,
        id="run_notification_checks",
    )
    scheduler.start()

    yield

    scheduler.shutdown()


def create_application() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, version=settings.app_version, debug=settings.debug, lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix=settings.api_v1_prefix)

    return application


app = create_application()
