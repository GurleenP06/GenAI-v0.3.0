"""Text processing utilities."""

import re
from pathlib import Path
from typing import List

from oskar.config.paths import TXT_DIRECTORY


def get_original_extension(txt_filename: str) -> str:
    """Given a .txt filename, find the original file extension."""
    if not txt_filename.endswith('.txt'):
        return ''

    base_name = txt_filename[:-4]
    data_dir = Path(TXT_DIRECTORY)
    extensions = ['.pdf', '.docx', '.pptx', '.xlsx', '.xls', '.xlsm']

    for ext in extensions:
        if (data_dir / f"{base_name}{ext}").exists():
            return ext

    return ''


def extract_citations(response_text: str) -> List[str]:
    """Extract citation numbers like [1], [2] from response text."""
    citation_pattern = r'\[(\d+)\]'
    return list(set(re.findall(citation_pattern, response_text)))
