"""Retrieval package - re-exports the main public API."""

from oskar.retrieval.index_manager import get_index_manager, ensure_initialized, RetrievalIndexManager
from oskar.retrieval.knowledge import retrieve_knowledge, retrieve_specific_documents, retrieve_for_comparison, get_document_chunks, get_retrieval_stats
from oskar.retrieval.search import hybrid_search, semantic_search, bm25_search, rerank_results
from oskar.retrieval.document_matcher import get_target_documents, extract_potential_doc_refs
