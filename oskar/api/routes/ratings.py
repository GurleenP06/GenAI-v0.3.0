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
        repo.save_detailed_rating(
            session_id=request.session_id,
            question=request.question,
            response=request.response,
            sentiment=request.sentiment,
            star_rating=request.star_rating,
            scoring_parameters=request.scoring_parameters,
            reasons=request.reasons,
            feedback_text=request.feedback_text,
            citations=request.citations,
            assistant_type=request.assistant_type,
            model=request.model,
        )
        return {"message": "Rating saved successfully"}
    except Exception as e:
        logger.error(f"Error saving rating: {e}")
        return {"error": str(e)}
