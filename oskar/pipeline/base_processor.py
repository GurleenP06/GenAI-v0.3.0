"""Base processor with shared methods for OPMP and IMP processors."""

import re
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Optional

import pdfplumber

logger = logging.getLogger(__name__)


class BaseProcessor:
    def extract_pages(self, pdf_path: Path) -> List[Tuple[int, str]]:
        pages = []
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    pages.append((i + 1, text))
        except Exception as e:
            logger.error(f"Error extracting pages from {pdf_path}: {e}")
        return pages

    def normalize_lines(self, text: str) -> str:
        lines = text.split('\n')
        normalized = []
        current_para = []

        for line in lines:
            stripped = line.strip()

            if not stripped:
                if current_para:
                    normalized.append(' '.join(current_para))
                    current_para = []
                normalized.append('')
                continue

            is_heading = bool(re.match(r'^\d+(?:\.\d+)*\.?\s+[A-Z]', stripped))
            is_bullet = stripped.startswith('•') or stripped.startswith('-') or re.match(r'^\d+\)', stripped)

            if is_heading or is_bullet:
                if current_para:
                    normalized.append(' '.join(current_para))
                    current_para = []
                if is_heading:
                    normalized.append('')
                normalized.append(stripped)
                continue

            if current_para:
                last_text = current_para[-1]
                continues_sentence = (
                    (last_text and not last_text.rstrip().endswith(('.', ':', '?', '!', ';'))) or
                    (stripped and stripped[0].islower()) or
                    last_text.rstrip().endswith(',')
                )
                if continues_sentence:
                    current_para.append(stripped)
                else:
                    normalized.append(' '.join(current_para))
                    current_para = [stripped]
            else:
                current_para = [stripped]

        if current_para:
            normalized.append(' '.join(current_para))

        result = '\n'.join(normalized)
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result.strip()
