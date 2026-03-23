"""Text chunking and tokenization utilities."""

import logging
from typing import List

import nltk

from oskar.config import NLTK_DATA_PATH

logger = logging.getLogger(__name__)


def setup_nltk() -> bool:
    nltk.data.path.clear()
    nltk.data.path.append(NLTK_DATA_PATH)

    try:
        nltk.word_tokenize("test sentence")
        logger.info("NLTK tokenizer available")
        return True
    except LookupError:
        logger.warning("NLTK punkt_tab not found. Attempting download...")
        try:
            nltk.download('punkt_tab', download_dir=NLTK_DATA_PATH, quiet=True)
            nltk.download('punkt', download_dir=NLTK_DATA_PATH, quiet=True)
            nltk.word_tokenize("test sentence")
            logger.info("NLTK downloaded successfully")
            return True
        except Exception as e:
            logger.warning(f"NLTK download failed: {e}")
            logger.info("Using simple tokenization (split on whitespace)")
            return False


NLTK_AVAILABLE = setup_nltk()


def tokenize_text(text: str) -> List[str]:
    if NLTK_AVAILABLE:
        try:
            return nltk.word_tokenize(text)
        except Exception:
            pass
    return text.split()


def create_chunks(text: str, chunk_size: int = 512, chunk_overlap: int = 64) -> List[str]:
    words = tokenize_text(text)
    chunks = []
    step = max(chunk_size - chunk_overlap, 1)

    i = 0
    while i < len(words):
        chunk = words[i:i + chunk_size]
        chunks.append(' '.join(chunk))
        i += step

    return chunks
