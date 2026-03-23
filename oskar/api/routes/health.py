"""Health check and root info routes."""

import logging

from fastapi import APIRouter

from oskar.services import model_service
import oskar.config as config

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check():
    try:
        ollama_status = model_service.check_ollama_status()

        rlpm_status = "unknown"
        try:
            from oskar.rlpm import RLPMIndexManager
            rlpm_status = "initialized" if RLPMIndexManager.is_initialized() else "not_initialized"
        except Exception:
            rlpm_status = "unavailable"

        return {
            "status": "healthy",
            "ollama": ollama_status,
            "device": config.DEVICE,
            "rlpm": rlpm_status,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


@router.get("/")
async def root():
    return {
        "name": "OSKAR API",
        "version": "2.1.0-ollama",
        "description": "Operations Support Knowledge Assistant with RAG + RLPM",
        "current_model": model_service.get_current_model(),
        "endpoints": {
            "generate": "/generate/",
            "models": "/models/",
            "health": "/health",
            "rlpm_status": "/rlpm/status",
            "rlpm_rebuild": "/rlpm/rebuild",
            "rlpm_comparisons": "/rlpm/comparisons",
        },
    }
