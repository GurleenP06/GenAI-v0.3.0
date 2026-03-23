from dataclasses import dataclass

RLPM_REFERENCE_DOCS = {
    "gcp59": "GCP-59",
    "pursuit_to_startup": "Pursuit",
    "development": "Development",
    "production": "Production",
    "sustainment": "Sustainment",
}

RLPM_COMPARISON_PAIRS = [
    {
        "name": "IMP 07-01-01",
        "old_pattern": "Old",
        "new_pattern": "New",
        "doc_pattern": "IMP",
    },
    {
        "name": "OPMP 4.11",
        "old_pattern": "Old",
        "new_pattern": "New",
        "doc_pattern": "OPMP",
    },
]


@dataclass
class RLPMConfig:
    RLPM_RETRIEVAL_TOP_K: int = 10
    TARGET_DOC_TOP_K: int = 15

    SEMANTIC_MATCH_THRESHOLD: float = 0.85
    MODERATE_MATCH_THRESHOLD: float = 0.50
    SPLIT_MERGE_THRESHOLD: float = 0.45

    RLPM_TEMPERATURE: float = 0.05
    RLPM_MAX_TOKENS: int = 1200
    RLPM_MAX_CONTEXT_CHARS: int = 28000

    COMPARISON_CHUNK_SIZE: int = 3000
    MAX_SECTIONS_TO_SUMMARIZE: int = 15


RLPM_CONFIG = RLPMConfig()
