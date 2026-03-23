"""Unified file text extraction - eliminates duplication across app.py, document_pipeline.py, rlpm_pipeline.py."""

import logging
from pathlib import Path

from oskar.extraction.pdf import extract_text_from_pdf
from oskar.extraction.docx import extract_text_from_docx
from oskar.extraction.pptx import extract_text_from_pptx
from oskar.extraction.xlsx import extract_text_from_xlsx, extract_text_from_xls

logger = logging.getLogger(__name__)

EXTRACTORS = {
    '.pdf': extract_text_from_pdf,
    '.docx': extract_text_from_docx,
    '.pptx': extract_text_from_pptx,
    '.xlsx': extract_text_from_xlsx,
    '.xlsm': extract_text_from_xlsx,
    '.xls': extract_text_from_xls,
}


def extract_text(file_path: Path) -> str:
    """Extract text from a file based on its extension."""
    suffix = file_path.suffix.lower()

    if suffix in ('.txt', '.md'):
        return file_path.read_text(encoding='utf-8', errors='ignore')

    extractor = EXTRACTORS.get(suffix)
    if extractor is None:
        logger.warning(f"Unsupported file type: {suffix} for {file_path}")
        return ""

    return extractor(file_path)
