"""Chat routes - session management, messaging, and response generation."""

import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException

from oskar.api.schemas import (
    QueryRequest,
    RenameRequest,
    MoveToProjectRequest,
    ToggleFavoriteRequest,
    ChatHistoryRequest,
)
from oskar.repositories.chat_repository import get_repository
from oskar.config import DEFAULT_MODEL
from oskar.services.generation_service import generate_response_with_citations

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/new_chat/")
async def new_chat(project_id: Optional[str] = None):
    session_id = str(uuid.uuid4())
    repo = get_repository()

    repo.chat_sessions[session_id] = {
        "summary": "",
        "messages": [],
        "assistant_type": "general",
        "model": DEFAULT_MODEL,
    }

    repo.chat_metadata[session_id] = {
        "session_id": session_id,
        "name": "New Chat",
        "project_id": project_id,
        "is_favorite": False,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "assistant_type": "general",
        "model": DEFAULT_MODEL,
    }
    repo.save_chats()
    return {"session_id": session_id, "metadata": repo.chat_metadata[session_id]}


@router.post("/rename_chat/")
async def rename_chat(request: RenameRequest):
    repo = get_repository()
    if request.session_id in repo.chat_metadata:
        repo.chat_metadata[request.session_id]["name"] = request.new_name
        repo.chat_metadata[request.session_id]["updated_at"] = datetime.now().isoformat()
        repo.save_chats()
        return {"message": "Chat renamed successfully"}
    raise HTTPException(status_code=404, detail="Chat not found")


@router.post("/move_to_project/")
async def move_to_project(request: MoveToProjectRequest):
    repo = get_repository()
    if request.session_id in repo.chat_metadata:
        repo.chat_metadata[request.session_id]["project_id"] = request.project_id
        repo.chat_metadata[request.session_id]["updated_at"] = datetime.now().isoformat()
        repo.save_chats()
        return {"message": "Chat moved successfully"}
    raise HTTPException(status_code=404, detail="Chat not found")


@router.post("/toggle_favorite/")
async def toggle_favorite(request: ToggleFavoriteRequest):
    repo = get_repository()
    if request.session_id in repo.chat_metadata:
        repo.chat_metadata[request.session_id]["is_favorite"] = not repo.chat_metadata[request.session_id]["is_favorite"]
        repo.chat_metadata[request.session_id]["updated_at"] = datetime.now().isoformat()
        repo.save_chats()
        return {"is_favorite": repo.chat_metadata[request.session_id]["is_favorite"]}
    raise HTTPException(status_code=404, detail="Chat not found")


@router.get("/list_chats/")
async def list_chats():
    repo = get_repository()
    organized_chats = {
        "favorites": [],
        "projects": {},
        "no_project": [],
    }

    for session_id, metadata in repo.chat_metadata.items():
        chat_info = {
            **metadata,
            "summary": repo.chat_sessions.get(session_id, {}).get("summary", "New Chat"),
        }

        if metadata["is_favorite"]:
            organized_chats["favorites"].append(chat_info)

        if metadata.get("project_id"):
            project_id = metadata["project_id"]
            if project_id not in organized_chats["projects"]:
                organized_chats["projects"][project_id] = {
                    "project": repo.projects.get(project_id, {"name": "Unknown Project"}),
                    "chats": [],
                }
            organized_chats["projects"][project_id]["chats"].append(chat_info)
        else:
            organized_chats["no_project"].append(chat_info)

    return organized_chats


@router.post("/get_chat_history/")
async def get_chat_history(request: ChatHistoryRequest):
    repo = get_repository()
    session_id = request.session_id
    history = repo.chat_sessions.get(session_id, {"messages": []})["messages"]
    return {"session_id": session_id, "history": history}


@router.post("/generate/")
async def generate_response(request: QueryRequest):
    session_id = request.session_id
    repo = get_repository()

    if session_id not in repo.chat_sessions:
        repo.chat_sessions[session_id] = {
            "summary": "",
            "messages": [],
            "assistant_type": "general",
            "model": DEFAULT_MODEL,
        }

    repo.chat_sessions[session_id]["messages"].append({
        "role": "user",
        "message": request.query,
    })

    if not repo.chat_sessions[session_id]["summary"]:
        repo.chat_sessions[session_id]["summary"] = request.query[:30] + ("..." if len(request.query) > 30 else "")
        if session_id in repo.chat_metadata and repo.chat_metadata[session_id]["name"] == "New Chat":
            repo.chat_metadata[session_id]["name"] = repo.chat_sessions[session_id]["summary"]
            repo.save_chats()

    assistant_type = request.assistant_type or repo.chat_sessions[session_id].get("assistant_type", "general")
    model = request.model or repo.chat_sessions[session_id].get("model", DEFAULT_MODEL)

    response_data = generate_response_with_citations(
        request.query,
        history=repo.chat_sessions[session_id]["messages"],
        assistant_type=assistant_type,
        model=model,
    )

    repo.chat_sessions[session_id]["assistant_type"] = response_data.get('assistant_type', assistant_type)
    repo.chat_sessions[session_id]["model"] = response_data.get('model_used', model)

    repo.chat_sessions[session_id]["messages"].append({
        "role": "assistant",
        "message": response_data['response'],
        "citations": response_data.get('citations', {}),
        "highlighted_passages": response_data.get('highlighted_passages', {}),
        "assistant_type": response_data.get('assistant_type', assistant_type),
        "model_used": response_data.get('model_used', model),
    })

    if session_id in repo.chat_metadata:
        repo.chat_metadata[session_id]["updated_at"] = datetime.now().isoformat()
        repo.chat_metadata[session_id]["assistant_type"] = response_data.get('assistant_type', assistant_type)
        repo.chat_metadata[session_id]["model"] = response_data.get('model_used', model)
        repo.save_chats()

    return {
        "session_id": session_id,
        "answer": response_data['response'],
        "citations": response_data.get('citations', {}),
        "highlighted_passages": response_data.get('highlighted_passages', {}),
        "assistant_type": response_data.get('assistant_type', assistant_type),
        "model_used": response_data.get('model_used', model),
    }
