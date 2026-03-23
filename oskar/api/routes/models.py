"""Model management routes - list, change, pull models via Ollama."""

import logging

from fastapi import APIRouter, HTTPException

from oskar.api.schemas import ModelChangeRequest
from oskar.services import model_service
from oskar.config import list_available_models

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/models/")
async def list_models():
    status = model_service.check_ollama_status()

    configured = list_available_models()
    available = status.get("available_models", [])

    return {
        "current_model": model_service.get_current_model(),
        "configured_models": configured,
        "locally_available": available,
        "ollama_status": status.get("status", "unknown"),
    }


@router.post("/models/change/")
async def change_model(request: ModelChangeRequest):
    try:
        model_service.set_model(request.model)
        return {
            "message": f"Model changed to {request.model}",
            "current_model": model_service.get_current_model(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/models/pull/{model_name}")
async def pull_model(model_name: str):
    client = model_service.get_ollama_client()
    success = client.pull_model(model_name)

    if success:
        return {"message": f"Model {model_name} pulled successfully"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to pull model {model_name}")
