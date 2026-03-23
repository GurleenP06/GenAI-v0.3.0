import os
from pathlib import Path

# Base directory is the parent of the v0.2.0 folder (same as original config.py)
BASE_DIR = Path(__file__).parent.parent.parent.parent.absolute()

# NLTK data path
NLTK_DATA_PATH = str(BASE_DIR / "Shared_Files" / "models" / "nltk_data")

# ML model paths
EMBEDDING_MODEL_PATH = str(BASE_DIR / "Shared_Files" / "models" / "all-MiniLM-L6-v2")
ENTROPY_MODEL_PATH = str(BASE_DIR / "Shared_Files" / "models" / "ms-marco-MiniLM-L6-en")

# Data directories
TXT_DIRECTORY = str(BASE_DIR / "Shared_Files" / "data")
SOURCE_LINK_FILE = str(BASE_DIR / "Shared_Files" / "data" / "SourceLinks.xlsx")

# v0.2.0-level paths (relative to the project root, not the package)
_PROJECT_DIR = Path(__file__).parent.parent.parent

METADATA_PATH = str(_PROJECT_DIR / "metadata.csv")
FAISS_INDEX_PATH = str(_PROJECT_DIR / "faiss_index")
TEXT_FILES_DIR = str(_PROJECT_DIR / "Text")

# RLPM paths
RLPM_DATA_DIR = str(BASE_DIR / "Shared_Files" / "data" / "RLPM")

RLPM_OUTPUT_DIR = str(_PROJECT_DIR / "rlpm_data")
RLPM_METADATA_PATH = str(_PROJECT_DIR / "rlpm_data" / "rlpm_metadata.csv")
RLPM_FAISS_INDEX_PATH = str(_PROJECT_DIR / "rlpm_data" / "rlpm_faiss_index")
RLPM_COMPARISON_DIR = str(_PROJECT_DIR / "rlpm_data" / "comparisons")
RLPM_FEWSHOT_PATH = str(_PROJECT_DIR / "rlpm_data" / "rlpm_fewshot_examples.json")
