import logging
from pathlib import Path

from docx import Document

logger = logging.getLogger(__name__)


def extract_text_from_docx(docx_path: Path) -> str:
    try:
        doc = Document(str(docx_path))
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    except Exception as e:
        logger.error(f"Error extracting DOCX {docx_path}: {e}")
        return ""
