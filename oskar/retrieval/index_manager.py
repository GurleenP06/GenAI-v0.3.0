"""Singleton index manager for retrieval resources (FAISS, BM25, models)."""

import time
import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer, CrossEncoder
import bm25s
from typing import List, Dict

from oskar.config import METADATA_PATH, FAISS_INDEX_PATH, EMBEDDING_MODEL_PATH, ENTROPY_MODEL_PATH, DEVICE
from oskar.utils.logging import log_progress


class RetrievalIndexManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        pass

    @classmethod
    def initialize(cls):
        if cls._initialized:
            log_progress("RETRIEVER", "Already initialized - skipping")
            return cls._instance

        instance = cls()

        log_progress("RETRIEVER", "=" * 60)
        log_progress("RETRIEVER", "INITIALIZING RETRIEVAL INDEX MANAGER")
        log_progress("RETRIEVER", "=" * 60)

        start_time = time.time()

        instance._load_metadata()
        instance._load_faiss_index()
        instance._build_bm25_index()
        instance._load_models()

        cls._initialized = True
        log_progress("RETRIEVER", f"Initialized in {time.time() - start_time:.1f}s")
        log_progress("RETRIEVER", "=" * 60)

        return instance

    @classmethod
    def is_initialized(cls) -> bool:
        return cls._initialized

    def _load_metadata(self):
        log_progress("RETRIEVER", "Step 1/4: Loading metadata...")
        self.metadata_df = pd.read_csv(METADATA_PATH)
        self.chunk_count = len(self.metadata_df)
        self.metadata_df['filename_lower'] = self.metadata_df['filename'].str.lower()
        self.corpus = self.metadata_df['chunk_text'].tolist()
        self.unique_filenames = self.metadata_df['filename'].unique().tolist()
        log_progress("RETRIEVER", f"  Loaded {self.chunk_count:,} chunks from {len(self.unique_filenames)} documents")

    def _load_faiss_index(self):
        log_progress("RETRIEVER", "Step 2/4: Loading FAISS index...")
        self.faiss_index = faiss.read_index(FAISS_INDEX_PATH)
        log_progress("RETRIEVER", f"  Loaded {self.faiss_index.ntotal:,} vectors")

    def _build_bm25_index(self):
        log_progress("RETRIEVER", "Step 3/4: Building BM25 index...")
        self.tokenized_corpus = bm25s.tokenize(self.corpus, stopwords="en")
        self.bm25_index = bm25s.BM25()
        self.bm25_index.index(self.tokenized_corpus)
        log_progress("RETRIEVER", "  BM25 index built")

    def _load_models(self):
        log_progress("RETRIEVER", "Step 4/4: Loading ML models...")
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_PATH, device=DEVICE)
        self.reranker = CrossEncoder(ENTROPY_MODEL_PATH, device=DEVICE)
        self.embedding_tokenizer = self.embedding_model.tokenizer
        log_progress("RETRIEVER", "  Models loaded")

    def encode_query(self, query: str) -> np.ndarray:
        return self.embedding_model.encode([query], convert_to_numpy=True, show_progress_bar=False)[0]

    def get_all_chunks_from_file(self, filename: str) -> List[Dict]:
        """Get ALL chunks from a specific file."""
        chunks = self.metadata_df[self.metadata_df['filename'] == filename]
        return chunks.to_dict('records')

    def get_chunk_count_for_file(self, filename: str) -> int:
        """Get number of chunks in a file."""
        return len(self.metadata_df[self.metadata_df['filename'] == filename])


def get_index_manager() -> RetrievalIndexManager:
    if not RetrievalIndexManager.is_initialized():
        return RetrievalIndexManager.initialize()
    return RetrievalIndexManager._instance


def ensure_initialized():
    if not RetrievalIndexManager.is_initialized():
        RetrievalIndexManager.initialize()
