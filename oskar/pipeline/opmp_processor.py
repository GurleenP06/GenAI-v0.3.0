"""OPMP document processor."""

import re
import logging
from pathlib import Path
from typing import List, Dict, Optional

from oskar.pipeline.base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class OPMPProcessor(BaseProcessor):
    def __init__(self):
        pass

    def extract_page1_metadata(self, page_text: str) -> Dict[str, str]:
        metadata = {"procedure_title": "", "opmp_number": "", "revision_number": ""}

        opmp_match = re.search(r'OPMP:?\s*(\d+\.\d+)', page_text, re.IGNORECASE)
        if opmp_match:
            metadata["opmp_number"] = opmp_match.group(1)

        rev_match = re.search(r'Rev\.?:?\s*(\w+(?:\.\d+)?)', page_text, re.IGNORECASE)
        if rev_match:
            metadata["revision_number"] = rev_match.group(1)

        title_match = re.search(
            r'Procedure\s+Title\s+(.+?)(?=Page\s*\d|WARNING|OPMP:|$)',
            page_text,
            re.IGNORECASE | re.DOTALL
        )
        if title_match:
            title_text = title_match.group(1).strip()
            title_text = re.sub(r'\s+', ' ', title_text)
            title_text = re.split(r'WARNING|PROPRIETARY|Page\s*\d', title_text, flags=re.IGNORECASE)[0]
            metadata["procedure_title"] = title_text.strip()

        return metadata

    def remove_header_footer(self, text: str, procedure_title: str) -> str:
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            skip = False

            if re.match(r'^operations\s+programs?\s+management', line_lower):
                skip = True
            elif re.match(r'^procedure$', line_lower):
                skip = True
            elif re.match(r'^opmp:', line_lower):
                skip = True
            elif re.match(r'^rev\.?:', line_lower):
                skip = True
            elif re.match(r'^date:', line_lower):
                skip = True
            elif re.match(r'^page\s*\d', line_lower):
                skip = True
            elif re.match(r'^procedure\s+title', line_lower):
                skip = True
            elif 'electronically controlled' in line_lower:
                skip = True
            elif 'copies may not be the latest' in line_lower:
                skip = True
            elif 'information contained on this page' in line_lower:
                skip = True
            elif 'does not contain data subject' in line_lower:
                skip = True
            elif 'subject to the notice' in line_lower:
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

    def find_scope_section_start(self, text: str) -> int:
        patterns = [
            r'\n3\.0\s+Scope\s+and\s+Purpose',
            r'\n3\.0\s+Purpose\s+and\s+Scope',
            r'\n3\.0\s+Scope\b',
            r'\n2\.0\s+Scope\s+and\s+Purpose',
            r'\n2\.0\s+Purpose\s+and\s+Scope',
            r'\n2\.0\s+Scope\b',
        ]

        for pattern in patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if len(matches) >= 2:
                return matches[1].start()
            elif len(matches) == 1:
                toc_match = re.search(r'TABLE\s+OF\s+CONTENTS', text, re.IGNORECASE)
                if toc_match and matches[0].start() > toc_match.end():
                    return matches[0].start()
                elif not toc_match:
                    return matches[0].start()

        return -1

    def find_acronyms_section(self, text: str) -> Optional[str]:
        patterns = [
            r'(\d+\.0)\s*Acronyms?\s+and\s+Definitions?\s*\n(.+?)(?=\n\s*\d+\.0\s+[A-Z]|\Z)',
            r'(\d+\.0)\s*Definitions?\s+and\s+Acronyms?\s*\n(.+?)(?=\n\s*\d+\.0\s+[A-Z]|\Z)',
            r'(\d+\.0)\s*Acronyms?\s*\n(.+?)(?=\n\s*\d+\.0\s+[A-Z]|\Z)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(2).strip()

        return None

    def parse_acronyms(self, text: str) -> List[Dict[str, str]]:
        acronyms = []

        section_text = self.find_acronyms_section(text)
        if not section_text:
            return acronyms

        for line in section_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            if re.match(r'^\d+\.\d', line):
                continue
            if line.lower().startswith('definition'):
                continue

            dash_match = re.match(r'^(.+?)\s*[-–—]\s*([A-Z].+)$', line)
            if dash_match:
                abbreviation = dash_match.group(1).strip()
                full_form = dash_match.group(2).strip()
                if len(abbreviation) <= 20:
                    if full_form.endswith('.'):
                        full_form = full_form[:-1]
                    acronyms.append({"abbreviation": abbreviation, "full_form": full_form})
                continue

            colon_match = re.match(r'^(.+?)\s*:\s*([A-Z].+)$', line)
            if colon_match:
                abbreviation = colon_match.group(1).strip()
                full_form = colon_match.group(2).strip()
                if len(abbreviation) <= 20:
                    if full_form.endswith('.'):
                        full_form = full_form[:-1]
                    acronyms.append({"abbreviation": abbreviation, "full_form": full_form})
                continue

            space_match = re.match(r'^(.+?)\s{2,}([A-Z].+)$', line)
            if space_match:
                abbreviation = space_match.group(1).strip()
                full_form = space_match.group(2).strip()
                if len(abbreviation) <= 20:
                    if full_form.endswith('.'):
                        full_form = full_form[:-1]
                    acronyms.append({"abbreviation": abbreviation, "full_form": full_form})
                continue

            space_match2 = re.match(r'^(.+?)\s+([A-Z][a-z].+)$', line)
            if space_match2:
                abbreviation = space_match2.group(1).strip()
                full_form = space_match2.group(2).strip()
                if len(abbreviation) <= 20 and re.match(r'^[\(\)A-Za-z0-9]', abbreviation):
                    if full_form.endswith('.'):
                        full_form = full_form[:-1]
                    acronyms.append({"abbreviation": abbreviation, "full_form": full_form})
                continue

        return acronyms

    def find_references_section(self, text: str) -> Optional[str]:
        patterns = [
            r'(\d+\.0)\s*References?\s*\n(.+?)(?=\n\s*\d+\.0\s+[A-Z]|\Z)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(2).strip()

        return None

    def parse_references(self, text: str) -> List[Dict[str, str]]:
        references = []

        section_text = self.find_references_section(text)
        if not section_text:
            return references

        for line in section_text.split('\n'):
            line = line.strip()
            if not line or re.match(r'^\d+\.\d', line):
                continue

            ref_match = re.match(r'^([A-Z][A-Za-z0-9&.\s-]{1,25}?\d+(?:[.-]\d+)*[A-Za-z]?)\s*[:]\s*(.+?)$', line)
            if ref_match:
                doc_number = ref_match.group(1).strip()
                doc_title = ref_match.group(2).strip()
                if len(doc_number) <= 30 and len(doc_title) > 3:
                    references.append({"document_number": doc_number, "document_title": doc_title})

        return references

    def remove_sections_from_text(self, text: str) -> str:
        acronym_patterns = [
            r'\d+\.0\s*Acronyms?\s+and\s+Definitions?\s*\n.+?(?=\n\s*\d+\.0\s+[A-Z])',
            r'\d+\.0\s*Definitions?\s+and\s+Acronyms?\s*\n.+?(?=\n\s*\d+\.0\s+[A-Z])',
            r'\d+\.0\s*Acronyms?\s*\n.+?(?=\n\s*\d+\.0\s+[A-Z])',
        ]

        for pattern in acronym_patterns:
            text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)

        text = re.sub(
            r'\d+\.0\s*References?\s*\n.+?(?=\n\s*\d+\.0\s+[A-Z])',
            '',
            text,
            flags=re.DOTALL | re.IGNORECASE
        )

        return text

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

        acronyms = self.parse_acronyms(combined_text)
        references = self.parse_references(combined_text)

        scope_start = self.find_scope_section_start(combined_text)
        if scope_start > 0:
            combined_text = combined_text[scope_start:]

        combined_text = self.remove_sections_from_text(combined_text)
        clean_text = self.normalize_lines(combined_text)

        return {
            "filename": pdf_path.stem + ".txt",
            "metadata": metadata,
            "acronyms": acronyms,
            "references": references,
            "clean_text": clean_text,
            "source_url": source_url
        }
