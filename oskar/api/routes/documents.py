"""Document viewing and chat export routes."""

import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from oskar.api.schemas import DocumentViewRequest, ExportRequest
from oskar.repositories.chat_repository import get_repository
from oskar.services.export_service import export_as_txt, markdown_to_docx
from oskar.utils.media_types import get_media_type
import oskar.config as config

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/view_document/")
async def view_document(request: DocumentViewRequest):
    try:
        data_dir = Path(config.TXT_DIRECTORY)
        original_filename = request.filename

        if original_filename.endswith('.txt'):
            base_name = original_filename[:-4]
        else:
            base_name = original_filename

        found_file = None
        possible_extensions = ['.pdf', '.docx', '.pptx', '.xlsx', '.xls', '.xlsm', '.txt']

        for ext in possible_extensions:
            test_path = data_dir / f"{base_name}{ext}"
            if test_path.exists():
                found_file = test_path
                break

            for item in data_dir.iterdir():
                if item.is_dir():
                    test_path = item / f"{base_name}{ext}"
                    if test_path.exists():
                        found_file = test_path
                        break

            if found_file:
                break

        if not found_file:
            for file_path in data_dir.rglob("*"):
                if file_path.is_file() and base_name.lower() in file_path.stem.lower():
                    found_file = file_path
                    break

        if not found_file:
            raise HTTPException(status_code=404, detail=f"Document not found: {base_name}")

        return FileResponse(
            path=str(found_file),
            filename=found_file.name,
            media_type=get_media_type(found_file.suffix),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export_chat/")
async def export_chat(request: ExportRequest):
    repo = get_repository()

    if request.session_id not in repo.chat_sessions:
        raise HTTPException(status_code=404, detail="Chat not found")

    chat_history = repo.chat_sessions[request.session_id]["messages"]

    if request.format == "txt":
        temp_path = export_as_txt(chat_history)
        return FileResponse(
            path=str(temp_path),
            filename=f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            media_type="text/plain",
        )

    elif request.format == "docx":
        docx_path = markdown_to_docx(chat_history)
        return FileResponse(
            path=str(docx_path),
            filename=f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    else:
        raise HTTPException(status_code=400, detail="Invalid export format. Use 'txt' or 'docx'")
