"""OSKAR API - FastAPI application."""

import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from oskar.repositories.chat_repository import get_repository

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("OSKAR STARTUP (Ollama Edition)")
    logger.info("=" * 60)

    try:
        from oskar.services.model_service import initialize
        initialize()
        logger.info("OSKAR initialized successfully!")
    except Exception as e:
        logger.error(f"Initialization warning: {e}")
        logger.info("OSKAR will start, but some features may not work.")

    repo = get_repository()
    data_dir = Path("./chat_data")
    for file in data_dir.glob("export_*.*"):
        if file.is_file():
            try:
                file.unlink()
            except:
                pass

    logger.info("=" * 60)
    logger.info("OSKAR READY - Accepting requests")
    logger.info("=" * 60)

    yield

    logger.info("OSKAR SHUTDOWN")


def create_app() -> FastAPI:
    app = FastAPI(
        title="OSKAR API",
        description="Operations Support Knowledge Assistant with RAG + RLPM",
        version="2.1.0-ollama",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    from oskar.api.routes import chat, projects, models, documents, rlpm, health, ratings, sessions
    app.include_router(chat.router)
    app.include_router(projects.router)
    app.include_router(models.router)
    app.include_router(documents.router)
    app.include_router(rlpm.router)
    app.include_router(health.router)
    app.include_router(ratings.router)
    app.include_router(sessions.router)

    # Serve static files
    static_dir = Path(__file__).parent.parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app


app = create_app()
