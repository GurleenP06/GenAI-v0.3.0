import json
import logging
import time
import numpy as np
import pandas as pd
import faiss
from pathlib import Path
from typing import List, Dict, Any

from sentence_transformers import SentenceTransformer

from oskar.config import (
    RLPM_DATA_DIR,
    RLPM_OUTPUT_DIR,
    RLPM_COMPARISON_DIR,
    RLPM_REFERENCE_DOCS,
    RLPM_COMPARISON_PAIRS,
    RLPM_FAISS_INDEX_PATH,
    RLPM_METADATA_PATH,
    RLPM_FEWSHOT_PATH,
    EMBEDDING_MODEL_PATH,
    DEVICE,
)
from oskar.extraction import extract_text
from oskar.utils.logging import log_progress as _log_progress
from oskar.rlpm.section_parser import parse_sections, align_sections
from oskar.rlpm.comparison import summarize_comparison_with_ollama, generate_fewshot_examples

logger = logging.getLogger(__name__)

_PREFIX = "RLPM_PIPELINE"


def log_progress(msg: str):
    _log_progress(_PREFIX, msg)


class RLPMKnowledgeBuilder:
    def __init__(self):
        self.rlpm_dir = Path(RLPM_DATA_DIR)
        self.output_dir = Path(RLPM_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.comparison_dir = Path(RLPM_COMPARISON_DIR)
        self.comparison_dir.mkdir(parents=True, exist_ok=True)

        log_progress(f"Loading embedding model: {EMBEDDING_MODEL_PATH}")
        self.embedding_model = SentenceTransformer(
            EMBEDDING_MODEL_PATH,
            device=DEVICE
        )

    def find_rlpm_reference_docs(self) -> List[Path]:
        if not self.rlpm_dir.exists():
            logger.error(f"RLPM directory not found: {self.rlpm_dir}")
            return []

        reference_docs = []
        all_files = list(self.rlpm_dir.glob("*"))

        for pattern_key, pattern_value in RLPM_REFERENCE_DOCS.items():
            for f in all_files:
                if f.is_file() and f.suffix.lower() in ('.pdf', '.docx', '.txt'):
                    fname_upper = f.name.upper()
                    if 'OLD' in fname_upper or 'NEW' in fname_upper:
                        continue
                    if pattern_value.upper() in fname_upper:
                        reference_docs.append(f)
                        log_progress(f"  Found reference doc [{pattern_key}]: {f.name}")
                        break

        return reference_docs

    def find_comparison_pairs(self) -> List[Dict[str, Path]]:
        pairs = []
        all_files = list(self.rlpm_dir.glob("*"))

        for pair_config in RLPM_COMPARISON_PAIRS:
            old_file = None
            new_file = None

            for f in all_files:
                if not f.is_file():
                    continue
                fname_upper = f.name.upper()
                doc_pattern = pair_config["doc_pattern"].upper()

                if doc_pattern in fname_upper:
                    if pair_config["old_pattern"].upper() in fname_upper:
                        old_file = f
                    elif pair_config["new_pattern"].upper() in fname_upper:
                        new_file = f

            if old_file and new_file:
                pairs.append({
                    "name": pair_config["name"],
                    "old_file": old_file,
                    "new_file": new_file
                })
                log_progress(f"  Found comparison pair [{pair_config['name']}]:")
                log_progress(f"    Old: {old_file.name}")
                log_progress(f"    New: {new_file.name}")
            else:
                log_progress(f"  WARNING: Missing pair for {pair_config['name']}")
                if not old_file:
                    log_progress(f"    Missing OLD file matching: {pair_config['old_pattern']} + {pair_config['doc_pattern']}")
                if not new_file:
                    log_progress(f"    Missing NEW file matching: {pair_config['new_pattern']} + {pair_config['doc_pattern']}")

        return pairs

    def build_reference_index(self, reference_docs: List[Path]) -> bool:
        log_progress("Building RLPM reference document index...")

        all_chunks = []
        chunk_size = 512
        chunk_overlap = 64

        for doc_path in reference_docs:
            text = extract_text(doc_path)
            if not text:
                continue

            words = text.split()
            step = max(chunk_size - chunk_overlap, 1)
            i = 0
            while i < len(words):
                chunk = ' '.join(words[i:i + chunk_size])
                all_chunks.append({
                    "chunk_text": chunk,
                    "filename": doc_path.name,
                    "source_type": "rlpm_reference"
                })
                i += step

        if not all_chunks:
            log_progress("  No chunks generated from reference docs")
            return False

        log_progress(f"  Generated {len(all_chunks)} chunks from {len(reference_docs)} reference docs")

        texts = [c["chunk_text"] for c in all_chunks]
        embeddings = self.embedding_model.encode(
            texts, convert_to_numpy=True, show_progress_bar=False,
            batch_size=32
        )

        dimension = embeddings.shape[1]
        n_neighbors = min(32, len(texts))
        index = faiss.IndexHNSWFlat(dimension, n_neighbors)
        index.add(np.array(embeddings, dtype=np.float32))

        faiss.write_index(index, RLPM_FAISS_INDEX_PATH)
        log_progress(f"  RLPM FAISS index saved: {RLPM_FAISS_INDEX_PATH}")

        df = pd.DataFrame(all_chunks)
        df.to_csv(RLPM_METADATA_PATH, index=False)
        log_progress(f"  RLPM metadata saved: {RLPM_METADATA_PATH}")

        return True

    def run_comparisons(self, pairs: List[Dict[str, Path]]) -> List[Dict[str, Any]]:
        log_progress("Running Old vs New document comparisons...")

        all_comparisons = []

        for pair in pairs:
            log_progress(f"  Comparing: {pair['name']}")

            old_text = extract_text(pair["old_file"])
            new_text = extract_text(pair["new_file"])

            if not old_text or not new_text:
                log_progress(f"    Skipping - could not extract text")
                continue

            old_sections = parse_sections(old_text)
            new_sections = parse_sections(new_text)

            log_progress(f"    Old doc: {len(old_sections)} sections")
            log_progress(f"    New doc: {len(new_sections)} sections")

            alignment = align_sections(old_sections, new_sections, self.embedding_model)

            log_progress(f"    Matched: {len(alignment['matched'])}")
            log_progress(f"    Added: {len(alignment['added'])}")
            log_progress(f"    Removed: {len(alignment['removed'])}")
            log_progress(f"    Split: {len(alignment['split'])}")
            log_progress(f"    Merged: {len(alignment['merged'])}")

            comparison = summarize_comparison_with_ollama(alignment, pair["name"])
            all_comparisons.append(comparison)

            comp_path = self.comparison_dir / f"comparison_{pair['name'].replace(' ', '_')}.json"
            with open(comp_path, 'w', encoding='utf-8') as f:
                json.dump(comparison, f, indent=2, default=str)
            log_progress(f"    Saved comparison: {comp_path}")

        return all_comparisons

    def build_all(self):
        log_progress("=" * 60)
        log_progress("RLPM KNOWLEDGE BASE BUILD")
        log_progress("=" * 60)

        start_time = time.time()

        log_progress("\nStep 1: Finding RLPM reference documents...")
        reference_docs = self.find_rlpm_reference_docs()

        if reference_docs:
            self.build_reference_index(reference_docs)
        else:
            log_progress("  WARNING: No reference docs found - RLPM retrieval will be limited")

        log_progress("\nStep 2: Finding comparison pairs...")
        pairs = self.find_comparison_pairs()

        comparisons = []
        if pairs:
            comparisons = self.run_comparisons(pairs)
        else:
            log_progress("  WARNING: No comparison pairs found")

        log_progress("\nStep 3: Generating few-shot examples...")
        fewshot = generate_fewshot_examples(comparisons)

        with open(RLPM_FEWSHOT_PATH, 'w', encoding='utf-8') as f:
            json.dump(fewshot, f, indent=2)
        log_progress(f"  Saved {len(fewshot)} few-shot examples: {RLPM_FEWSHOT_PATH}")

        elapsed = time.time() - start_time
        log_progress(f"\nRLPM build complete in {elapsed:.1f}s")
        log_progress("=" * 60)

        return {
            "reference_docs": len(reference_docs),
            "comparison_pairs": len(pairs),
            "comparisons": len(comparisons),
            "fewshot_examples": len(fewshot)
        }
