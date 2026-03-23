"""Session routes - user registration and interaction logging."""

import uuid
import logging
from datetime import datetime

from fastapi import APIRouter

from oskar.api.schemas import RegisterSessionRequest, LogInteractionRequest
from oskar.repositories.chat_repository import get_repository
from oskar.config import DEFAULT_MODEL

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register_session/")
async def register_session(request: RegisterSessionRequest):
    session_id = str(uuid.uuid4())
    repo = get_repository()

    # Create chat session (same as new_chat)
    repo.chat_sessions[session_id] = {
        "summary": "",
        "messages": [],
        "assistant_type": "general",
        "model": DEFAULT_MODEL,
    }

    repo.chat_metadata[session_id] = {
        "session_id": session_id,
        "name": "New Chat",
        "project_id": None,
        "is_favorite": False,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "assistant_type": "general",
        "model": DEFAULT_MODEL,
        "user_name": request.name,
        "user_role": request.role,
    }
    repo.save_chats()

    # Create session log
    repo.create_session_log(session_id, request.name, request.role)

    logger.info(f"Session registered: {session_id} for {request.name} ({request.role})")

    return {"session_id": session_id, "name": request.name, "role": request.role}


@router.post("/log_interaction/")
async def log_interaction(request: LogInteractionRequest):
    repo = get_repository()

    repo.append_interaction(
        session_id=request.session_id,
        question=request.question,
        response_preview=request.response,
        response_time_ms=request.response_time_ms,
        assistant_type=request.assistant_type,
        model=request.model,
    )

    return {"status": "logged"}
