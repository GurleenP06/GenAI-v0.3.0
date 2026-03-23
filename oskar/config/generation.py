from dataclasses import dataclass


@dataclass
class GenerationConfig:
    MAX_NEW_TOKENS_DEFAULT: int = 400
    MAX_NEW_TOKENS_WRITING: int = 700
    MAX_NEW_TOKENS_OPO: int = 800

    DEFAULT_TEMPERATURE: float = 0.2
    WRITING_TEMPERATURE: float = 0.3
    OPO_TEMPERATURE: float = 0.1
    PROCEDURE_TEMPERATURE: float = 0.05

    TOP_P: float = 0.85
    REPEAT_PENALTY: float = 1.08

    DEFAULT_RETRIEVAL_TOP_K: int = 5
    WRITING_RETRIEVAL_TOP_K: int = 5
    OPO_RETRIEVAL_TOP_K: int = 8

    MAX_CONTEXT_CHARS: int = 24000


GENERATION_CONFIG = GenerationConfig()
