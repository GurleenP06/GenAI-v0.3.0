"""Project management routes."""

import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException

from oskar.api.schemas import Project
from oskar.repositories.chat_repository import get_repository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/create_project/")
async def create_project(project: Project):
    repo = get_repository()
    project_id = str(uuid.uuid4())
    repo.projects[project_id] = {
        "id": project_id,
        "name": project.name,
        "description": project.description,
        "created_at": datetime.now().isoformat(),
    }
    repo.save_projects()
    return {"project_id": project_id, "project": repo.projects[project_id]}


@router.get("/list_projects/")
async def list_projects():
    repo = get_repository()
    return list(repo.projects.values())


@router.delete("/delete_project/{project_id}")
async def delete_project(project_id: str):
    repo = get_repository()
    if project_id in repo.projects:
        for chat_id, chat in repo.chat_metadata.items():
            if chat.get("project_id") == project_id:
                chat["project_id"] = None
        del repo.projects[project_id]
        repo.save_projects()
        repo.save_chats()
        return {"message": "Project deleted"}
    raise HTTPException(status_code=404, detail="Project not found")
