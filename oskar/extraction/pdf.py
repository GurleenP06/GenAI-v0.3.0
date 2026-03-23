import logging
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: Path) -> str:
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            parts = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                parts.append(text)
            return '\n\n'.join(parts)
    except Exception as e:
        logger.error(f"Error extracting PDF {pdf_path}: {e}")
        return ""
