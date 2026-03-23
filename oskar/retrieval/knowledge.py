"""High-level knowledge retrieval functions."""

import logging
import pandas as pd
from typing import List, Dict, Tuple, Any, Optional

from oskar.config import DEVICE
from oskar.retrieval.index_manager import get_index_manager
from oskar.retrieval.search import hybrid_search
from oskar.retrieval.document_matcher import get_target_documents, find_matching_filenames

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


SMALL_DOCUMENT_THRESHOLD = 20


def retrieve_knowledge(query: str, top_k: int = 6, prioritize_examples: bool = False) -> List[Tuple[str, Dict]]:
    idx = get_index_manager()

    target_filenames = get_target_documents(query, idx.unique_filenames)

    if target_filenames:
        logger.info(f"Document reference detected!")
        logger.info(f"Target files: {target_filenames}")

    if target_filenames:
        all_results = []

        for target_file in target_filenames:
            chunk_count = idx.get_chunk_count_for_file(target_file)
            logger.info(f"{target_file} has {chunk_count} chunks")

            if chunk_count <= SMALL_DOCUMENT_THRESHOLD:
                logger.info(f"Small document - retrieving ALL {chunk_count} chunks")
                chunks = idx.get_all_chunks_from_file(target_file)

                for chunk in chunks:
                    all_results.append((
                        chunk['chunk_text'],
                        {
                            'filename': chunk['filename'],
                            'source_url': chunk['source_url'] if pd.notna(chunk.get('source_url')) else ''
                        }
                    ))
            else:
                logger.info(f"Large document - using hybrid search")
                target_results = hybrid_search(query, top_k=top_k, filter_filenames=[target_file])
                all_results.extend(target_results)

        seen = set()
        unique_results = []
        for text, meta in all_results:
            key = text[:100]
            if key not in seen:
                seen.add(key)
                unique_results.append((text, meta))

        logger.info(f"Total chunks from target document(s): {len(unique_results)}")

        if len(unique_results) < top_k:
            other_results = hybrid_search(query, top_k=3)
            for text, meta in other_results:
                if meta['filename'] not in target_filenames and text[:100] not in seen:
                    unique_results.append((text, meta))
                    seen.add(text[:100])

        return unique_results

    else:
        return hybrid_search(query, top_k=top_k)


def retrieve_specific_documents(query: str, document_names: List[str], top_k: int = 10) -> List[Tuple[str, Dict]]:
    idx = get_index_manager()

    matched = []
    for name in document_names:
        matches = find_matching_filenames([name], idx.unique_filenames, threshold=0.4)
        matched.extend([fn for fn, _ in matches])

    matched = list(set(matched))

    if matched:
        return hybrid_search(query, top_k=top_k, filter_filenames=matched)

    return hybrid_search(query, top_k=top_k)


def retrieve_for_comparison(query: str, doc1_name: str, doc2_name: str, top_k: int = 20) -> List[Tuple[str, Dict]]:
    idx = get_index_manager()

    doc1_matches = find_matching_filenames([doc1_name], idx.unique_filenames, threshold=0.4)
    doc2_matches = find_matching_filenames([doc2_name], idx.unique_filenames, threshold=0.4)

    doc1_files = [fn for fn, _ in doc1_matches[:2]]
    doc2_files = [fn for fn, _ in doc2_matches[:2]]

    half_k = top_k // 2

    doc1_results = hybrid_search(query, top_k=half_k, filter_filenames=doc1_files) if doc1_files else []
    doc2_results = hybrid_search(query, top_k=half_k, filter_filenames=doc2_files) if doc2_files else []

    results = []
    seen = set()
    max_len = max(len(doc1_results), len(doc2_results))

    for i in range(max_len):
        if i < len(doc1_results):
            text, meta = doc1_results[i]
            if text[:100] not in seen:
                results.append((text, meta))
                seen.add(text[:100])
        if i < len(doc2_results):
            text, meta = doc2_results[i]
            if text[:100] not in seen:
                results.append((text, meta))
                seen.add(text[:100])

    return results[:top_k]


def get_document_chunks(document_name: str, max_chunks: int = 50) -> List[Dict]:
    idx = get_index_manager()

    matches = find_matching_filenames([document_name], idx.unique_filenames, threshold=0.4)
    matched_files = [fn for fn, _ in matches[:3]]

    if not matched_files:
        return []

    df = idx.metadata_df[idx.metadata_df['filename'].isin(matched_files)].head(max_chunks)
    return df.to_dict(orient='records')


def get_retrieval_stats() -> Dict[str, Any]:
    idx = get_index_manager()
    return {
        "total_chunks": idx.chunk_count,
        "faiss_vectors": idx.faiss_index.ntotal,
        "unique_documents": len(idx.unique_filenames),
        "device": DEVICE,
    }
