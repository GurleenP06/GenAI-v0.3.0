"""IMP document processor."""

import re
import logging
from pathlib import Path
from typing import List, Dict, Optional

from oskar.pipeline.base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class IMPProcessor(BaseProcessor):
    def __init__(self):
        pass

    def extract_page1_metadata(self, page_text: str) -> Dict[str, str]:
        metadata = {"procedure_title": "", "imp_number": "", "revision_number": ""}

        imp_match = re.search(r'IMP\s*No\.?:?\s*(\d+(?:[.-]\d+)*)', page_text, re.IGNORECASE)
        if imp_match:
            metadata["imp_number"] = imp_match.group(1)

        rev_match = re.search(r'REV:?\s*(\w+(?:\.\d+)?)', page_text, re.IGNORECASE)
        if rev_match:
            metadata["revision_number"] = rev_match.group(1)

        title_match = re.search(
            r'Procedure\s+Title:?\s*(.+?)(?=WARNING|IMP\s*No|REV:|$)',
            page_text,
            re.IGNORECASE | re.DOTALL
        )
        if title_match:
            title_text = title_match.group(1).strip()
            title_text = re.sub(r'\s+', ' ', title_text)
            title_text = re.split(r'WARNING|PROPRIETARY|PAGE:', title_text, flags=re.IGNORECASE)[0]
            metadata["procedure_title"] = title_text.strip()

        return metadata

    def remove_header_footer(self, text: str, procedure_title: str) -> str:
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            skip = False

            if re.match(r'^pratt\s*&\s*whitney\s+canada', line_lower):
                skip = True
            elif re.match(r'^industrial\s+management', line_lower):
                skip = True
            elif re.match(r'^procedure$', line_lower):
                skip = True
            elif re.match(r'^imp\s*no\.?:', line_lower):
                skip = True
            elif re.match(r'^rev:', line_lower):
                skip = True
            elif re.match(r'^date:', line_lower):
                skip = True
            elif re.match(r'^page:', line_lower):
                skip = True
            elif re.match(r'^procedure\s+title', line_lower):
                skip = True
            elif 'electronically controlled' in line_lower:
                skip = True
            elif 'copies may not be the latest' in line_lower:
                skip = True
            elif re.match(r'^\d+\s+of\s+\d+$', line_stripped):
                skip = True

            if procedure_title:
                title_normalized = re.sub(r'\s+', ' ', procedure_title.lower().strip())
                line_normalized = re.sub(r'\s+', ' ', line_lower.strip())
                if title_normalized == line_normalized:
                    skip = True

            if not skip:
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def process(self, pdf_path: Path, source_url: str = "") -> Optional[Dict]:
        pages = self.extract_pages(pdf_path)
        if not pages:
            return None

        page1_text = pages[0][1] if pages else ""
        metadata = self.extract_page1_metadata(page1_text)

        all_text_parts = []
        for page_num, page_text in pages:
            cleaned = self.remove_header_footer(page_text, metadata["procedure_title"])
            all_text_parts.append(cleaned)

        combined_text = '\n\n'.join(all_text_parts)
        clean_text = self.normalize_lines(combined_text)

        return {
            "filename": pdf_path.stem + ".txt",
            "metadata": metadata,
            "acronyms": [],
            "references": [],
            "clean_text": clean_text,
            "source_url": source_url
        }
