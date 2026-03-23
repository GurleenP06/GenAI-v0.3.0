"""Vector database creation utilities."""

import numpy as np
import pandas as pd
import faiss
from typing import List, Dict
from sentence_transformers import SentenceTransformer


def batch_encode(texts: List[str], embedding_model: SentenceTransformer, batch_size: int = 32) -> np.ndarray:
    embeddings = []
    total_batches = (len(texts) + batch_size - 1) // batch_size

    print(f"Generating embeddings for {len(texts)} chunks...")

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = embedding_model.encode(
            batch,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        embeddings.append(batch_embeddings)

        batch_num = (i // batch_size) + 1
        if batch_num % 10 == 0 or batch_num == total_batches:
            print(f"  Batch {batch_num}/{total_batches}")

    return np.vstack(embeddings)


def create_vector_database(
    chunks_metadata: List[Dict],
    faiss_index_path: str,
    metadata_path: str,
    embedding_model: SentenceTransformer,
    batch_size: int = 32
):
    print("\nCreating vector database...")

    chunk_texts = [m["chunk_text"] for m in chunks_metadata]
    embeddings = batch_encode(chunk_texts, embedding_model, batch_size)

    dimension = embeddings.shape[1]
    n_neighbors = min(32, len(chunk_texts))

    index = faiss.IndexHNSWFlat(dimension, n_neighbors)
    index.add(np.array(embeddings, dtype=np.float32))

    faiss.write_index(index, str(faiss_index_path))
    print(f"FAISS index saved: {faiss_index_path}")

    metadata_df = pd.DataFrame(chunks_metadata)
    metadata_df.to_csv(metadata_path, index=False)
    print(f"Metadata saved: {metadata_path}")
