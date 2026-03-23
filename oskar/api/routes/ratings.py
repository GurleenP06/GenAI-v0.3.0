"""Rating submission routes."""

import logging

from fastapi import APIRouter

from oskar.api.schemas import RatingRequest
from oskar.repositories.chat_repository import get_repository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/save_rating/")
async def save_rating(request: RatingRequest):
    try:
        repo = get_repository()
        repo.save_rating(request.question, request.response, request.rating)
        return {"message": "Rating saved successfully"}
    except Exception as e:
        return {"error": str(e)}
