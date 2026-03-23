import json
import logging
import time
import numpy as np
import pandas as pd
import faiss
from pathlib import Path
from typing import List, Tuple

from sentence_transformers import SentenceTransformer

from oskar.config import (
    RLPM_FAISS_INDEX_PATH,
    RLPM_METADATA_PATH,
    RLPM_FEWSHOT_PATH,
    RLPM_COMPARISON_DIR,
    EMBEDDING_MODEL_PATH,
    DEVICE,
)
from oskar.utils.logging import log_progress as _log_progress

logger = logging.getLogger(__name__)

_PREFIX = "RLPM_PIPELINE"


def log_progress(msg: str):
    _log_progress(_PREFIX, msg)


class RLPMIndexManager:
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
            log_progress("RLPM already initialized - skipping")
            return cls._instance

        instance = cls()

        log_progress("=" * 60)
        log_progress("INITIALIZING RLPM INDEX MANAGER")
        log_progress("=" * 60)

        start_time = time.time()

        if not Path(RLPM_FAISS_INDEX_PATH).exists():
            log_progress("RLPM index not found - building from scratch...")
            from oskar.rlpm.knowledge_builder import RLPMKnowledgeBuilder
            builder = RLPMKnowledgeBuilder()
            builder.build_all()

        if Path(RLPM_FAISS_INDEX_PATH).exists():
            instance.faiss_index = faiss.read_index(RLPM_FAISS_INDEX_PATH)
            log_progress(f"  Loaded RLPM FAISS index: {instance.faiss_index.ntotal} vectors")
        else:
            instance.faiss_index = None
            log_progress("  WARNING: No RLPM FAISS index available")

        if Path(RLPM_METADATA_PATH).exists():
            instance.metadata_df = pd.read_csv(RLPM_METADATA_PATH)
            instance.corpus = instance.metadata_df['chunk_text'].tolist()
            log_progress(f"  Loaded RLPM metadata: {len(instance.corpus)} chunks")
        else:
            instance.metadata_df = pd.DataFrame()
            instance.corpus = []

        instance.embedding_model = SentenceTransformer(
            EMBEDDING_MODEL_PATH,
            device=DEVICE
        )

        if Path(RLPM_FEWSHOT_PATH).exists():
            with open(RLPM_FEWSHOT_PATH, 'r') as f:
                instance.fewshot_examples = json.load(f)
            log_progress(f"  Loaded {len(instance.fewshot_examples)} few-shot examples")
        else:
            instance.fewshot_examples = []
            log_progress("  WARNING: No few-shot examples found")

        instance.comparisons = {}
        comp_dir = Path(RLPM_COMPARISON_DIR)
        if comp_dir.exists():
            for comp_file in comp_dir.glob("comparison_*.json"):
                with open(comp_file, 'r') as f:
                    comp_data = json.load(f)
                instance.comparisons[comp_data["document"]] = comp_data
            log_progress(f"  Loaded {len(instance.comparisons)} comparison results")

        cls._initialized = True
        log_progress(f"RLPM initialized in {time.time() - start_time:.1f}s")
        log_progress("=" * 60)

        return instance

    @classmethod
    def is_initialized(cls) -> bool:
        return cls._initialized

    def search_rlpm_references(self, query: str, top_k: int = 10) -> List[Tuple[str, dict]]:
        if self.faiss_index is None or len(self.corpus) == 0:
            return []

        query_embedding = self.embedding_model.encode(
            [query], convert_to_numpy=True, show_progress_bar=False
        )[0]

        fetch_k = min(top_k * 2, self.faiss_index.ntotal)
        distances, indices = self.faiss_index.search(
            np.array([query_embedding], dtype=np.float32),
            fetch_k
        )

        results = []
        for i, idx_val in enumerate(indices[0]):
            if 0 <= idx_val < len(self.metadata_df):
                row = self.metadata_df.iloc[idx_val]
                results.append((
                    row['chunk_text'],
                    {
                        'filename': row['filename'],
                        'source_url': '',
                        'source_type': 'rlpm_reference'
                    }
                ))

        return results[:top_k]

    def get_fewshot_prompt_text(self) -> str:
        if not self.fewshot_examples:
            return ""

        lines = ["EXAMPLES OF RLPM CHANGES (from actual Old vs New document comparisons):\n"]

        for i, ex in enumerate(self.fewshot_examples, 1):
            lines.append(f"Example {i} ({ex['type']}):")
            lines.append(f"  {ex['description']}")
            lines.append("")

        return '\n'.join(lines)

    def get_comparison_summary(self) -> str:
        if not self.comparisons:
            return ""

        lines = ["SUMMARY OF KNOWN RLPM CHANGES (from Old vs New procedure comparisons):\n"]

        for doc_name, comp in self.comparisons.items():
            stats = comp.get("statistics", {})
            lines.append(f"Document: {doc_name}")
            lines.append(f"  Matched sections: {stats.get('total_matched', 0)}")
            lines.append(f"  Added sections: {stats.get('total_added', 0)}")
            lines.append(f"  Removed sections: {stats.get('total_removed', 0)}")
            lines.append(f"  Split sections: {stats.get('total_split', 0)}")
            lines.append(f"  Merged sections: {stats.get('total_merged', 0)}")

            for sc in comp.get("structural_changes", [])[:3]:
                if sc["type"] == "added":
                    lines.append(f"  + NEW: Section {sc['section']} - {sc['title']}")
                elif sc["type"] == "removed":
                    lines.append(f"  - REMOVED: Section {sc['section']} - {sc['title']}")

            for cc in comp.get("content_changes", [])[:3]:
                if cc.get("terminology_changes"):
                    tc = cc["terminology_changes"][0]
                    lines.append(f"  ~ TERMINOLOGY: '{tc['old_text']}' -> '{tc['new_text']}' (Section {cc['old_section']})")

            lines.append("")

        return '\n'.join(lines)


def get_rlpm_manager() -> RLPMIndexManager:
    if not RLPMIndexManager.is_initialized():
        return RLPMIndexManager.initialize()
    return RLPMIndexManager._instance


def ensure_rlpm_initialized():
    if not RLPMIndexManager.is_initialized():
        RLPMIndexManager.initialize()
