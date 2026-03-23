"""Search functions: BM25, semantic, reranking, and hybrid search."""

import numpy as np
import pandas as pd
import bm25s
from typing import List, Dict, Tuple, Optional

from oskar.retrieval.index_manager import get_index_manager


def bm25_search(query: str, top_k: int = 10, filter_filenames: Optional[List[str]] = None) -> pd.DataFrame:
    idx = get_index_manager()

    tokenized_query = bm25s.tokenize(query, stopwords="en")
    fetch_k = top_k * 4 if filter_filenames else top_k * 2

    results, scores = idx.bm25_index.retrieve(
        tokenized_query,
        k=min(fetch_k, len(idx.corpus)),
        corpus=idx.corpus
    )

    result_docs = []
    for i in range(results.shape[1]):
        chunk_text = results[0, i]
        score = float(scores[0, i])

        mask = idx.metadata_df['chunk_text'] == chunk_text
        if mask.any():
            row = idx.metadata_df[mask].iloc[0]

            if filter_filenames and row['filename'] not in filter_filenames:
                continue

            result_docs.append({
                "chunk_text": chunk_text,
                "filename": row['filename'],
                "source_url": row['source_url'],
                "score": score
            })

    if not result_docs:
        return pd.DataFrame(columns=['chunk_text', 'filename', 'source_url', 'score'])

    return pd.DataFrame(result_docs).head(top_k)


def semantic_search(query: str, top_k: int = 10, filter_filenames: Optional[List[str]] = None) -> pd.DataFrame:
    idx = get_index_manager()

    query_embedding = idx.encode_query(query)
    fetch_k = top_k * 4 if filter_filenames else top_k * 2

    distances, indices = idx.faiss_index.search(
        np.array([query_embedding], dtype=np.float32),
        fetch_k
    )

    results = []
    for i, idx_val in enumerate(indices[0]):
        if 0 <= idx_val < len(idx.metadata_df):
            row = idx.metadata_df.iloc[idx_val]

            if filter_filenames and row['filename'] not in filter_filenames:
                continue

            results.append({
                'chunk_text': row['chunk_text'],
                'filename': row['filename'],
                'source_url': row['source_url'],
                'score': 1.0 / (1.0 + distances[0][i])
            })

    if not results:
        return pd.DataFrame(columns=['chunk_text', 'filename', 'source_url', 'score'])

    return pd.DataFrame(results).head(top_k)


def rerank_results(query: str, candidates: List[Dict]) -> List[Dict]:
    if not candidates:
        return []

    idx = get_index_manager()
    pairs = [(query, c['chunk_text']) for c in candidates]

    try:
        scores = idx.reranker.predict(pairs)
    except:
        scores = np.arange(len(candidates), 0, -1)

    for i, c in enumerate(candidates):
        c['rerank_score'] = float(scores[i])

    return sorted(candidates, key=lambda x: x['rerank_score'], reverse=True)


def hybrid_search(query: str, top_k: int = 5, filter_filenames: Optional[List[str]] = None) -> List[Tuple[str, Dict]]:

    semantic_df = semantic_search(query, top_k=top_k * 2, filter_filenames=filter_filenames)
    bm25_df = bm25_search(query, top_k=top_k * 2, filter_filenames=filter_filenames)

    all_results = {}

    for _, row in semantic_df.iterrows():
        key = row['chunk_text'][:100]
        if key not in all_results:
            all_results[key] = {
                'chunk_text': row['chunk_text'],
                'filename': row['filename'],
                'source_url': row['source_url']
            }

    for _, row in bm25_df.iterrows():
        key = row['chunk_text'][:100]
        if key not in all_results:
            all_results[key] = {
                'chunk_text': row['chunk_text'],
                'filename': row['filename'],
                'source_url': row['source_url']
            }

    candidates = list(all_results.values())

    if not candidates:
        return []

    reranked = rerank_results(query, candidates)

    results = []
    for c in reranked[:top_k]:
        results.append((
            c['chunk_text'],
            {
                'filename': c['filename'],
                'source_url': c['source_url'] if pd.notna(c['source_url']) else ''
            }
        ))

    return results
