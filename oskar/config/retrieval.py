from dataclasses import dataclass


@dataclass
class RetrievalConfig:
    DOCUMENT_MATCH_BOOST: float = 2.5
    BM25_DOCUMENT_BOOST: float = 4.0
    AS9100_QUERY_BOOST: float = 1.5
    AS9100_BM25_BOOST: float = 2.0
    RERANK_DOCUMENT_BOOST: float = 2.0
    RERANK_AS9100_BOOST: float = 1.5

    DEFAULT_TOP_K_SEMANTIC: int = 8
    DEFAULT_TOP_K_KEYWORD: int = 8
    DEFAULT_FINAL_TOP_K: int = 3
    AS9100_TOP_K: int = 10

    EMBEDDING_MAX_TOKENS: int = 256


RETRIEVAL_CONFIG = RetrievalConfig()
