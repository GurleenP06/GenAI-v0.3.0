import re
import numpy as np
from typing import List, Dict, Any
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer

from oskar.config import RLPM_CONFIG


@dataclass
class DocumentSection:
    section_number: str
    title: str
    content: str
    start_pos: int
    level: int


def parse_sections(text: str) -> List[DocumentSection]:
    section_pattern = re.compile(
        r'^(\d+(?:\.\d+)*\.?)\s+(.+?)$',
        re.MULTILINE
    )

    matches = list(section_pattern.finditer(text))

    if not matches:
        return [DocumentSection(
            section_number="1.0",
            title="Full Document",
            content=text.strip(),
            start_pos=0,
            level=1
        )]

    sections = []
    for i, match in enumerate(matches):
        sec_num = match.group(1).rstrip('.')
        sec_title = match.group(2).strip()
        start = match.start()

        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)

        content = text[start:end].strip()
        level = sec_num.count('.') + 1

        if len(content) < 20 and i < len(matches) - 1:
            continue

        sections.append(DocumentSection(
            section_number=sec_num,
            title=sec_title,
            content=content,
            start_pos=start,
            level=level
        ))

    return sections


def compute_section_embeddings(
    sections: List[DocumentSection],
    embedding_model: SentenceTransformer
) -> np.ndarray:
    texts = [s.content for s in sections]
    if not texts:
        return np.array([])
    return embedding_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)


def align_sections(
    old_sections: List[DocumentSection],
    new_sections: List[DocumentSection],
    embedding_model: SentenceTransformer
) -> Dict[str, Any]:
    if not old_sections or not new_sections:
        return {
            "matched": [],
            "added": [s.section_number for s in new_sections],
            "removed": [s.section_number for s in old_sections],
            "split": [],
            "merged": []
        }

    old_embeddings = compute_section_embeddings(old_sections, embedding_model)
    new_embeddings = compute_section_embeddings(new_sections, embedding_model)

    old_norm = old_embeddings / (np.linalg.norm(old_embeddings, axis=1, keepdims=True) + 1e-8)
    new_norm = new_embeddings / (np.linalg.norm(new_embeddings, axis=1, keepdims=True) + 1e-8)
    similarity_matrix = np.dot(old_norm, new_norm.T)

    cfg = RLPM_CONFIG

    old_matched = set()
    new_matched = set()
    matched_pairs = []

    # High-confidence matches
    for old_idx in range(len(old_sections)):
        best_new_idx = int(np.argmax(similarity_matrix[old_idx]))
        best_score = float(similarity_matrix[old_idx][best_new_idx])

        if best_score >= cfg.SEMANTIC_MATCH_THRESHOLD and best_new_idx not in new_matched:
            matched_pairs.append({
                "old_section": old_sections[old_idx].section_number,
                "old_title": old_sections[old_idx].title,
                "new_section": new_sections[best_new_idx].section_number,
                "new_title": new_sections[best_new_idx].title,
                "similarity": round(best_score, 3),
                "change_type": "renumbered" if old_sections[old_idx].section_number != new_sections[best_new_idx].section_number else "minor_edit",
                "old_content": old_sections[old_idx].content,
                "new_content": new_sections[best_new_idx].content
            })
            old_matched.add(old_idx)
            new_matched.add(best_new_idx)

    # Moderate matches
    for old_idx in range(len(old_sections)):
        if old_idx in old_matched:
            continue

        best_new_idx = -1
        best_score = 0.0

        for new_idx in range(len(new_sections)):
            if new_idx in new_matched:
                continue
            score = float(similarity_matrix[old_idx][new_idx])
            if score > best_score:
                best_score = score
                best_new_idx = new_idx

        if best_score >= cfg.MODERATE_MATCH_THRESHOLD and best_new_idx >= 0:
            matched_pairs.append({
                "old_section": old_sections[old_idx].section_number,
                "old_title": old_sections[old_idx].title,
                "new_section": new_sections[best_new_idx].section_number,
                "new_title": new_sections[best_new_idx].title,
                "similarity": round(best_score, 3),
                "change_type": "modified",
                "old_content": old_sections[old_idx].content,
                "new_content": new_sections[best_new_idx].content
            })
            old_matched.add(old_idx)
            new_matched.add(best_new_idx)

    # Detect splits
    splits = []
    for old_idx in range(len(old_sections)):
        if old_idx in old_matched:
            continue

        partial_matches = []
        for new_idx in range(len(new_sections)):
            if new_idx in new_matched:
                continue
            score = float(similarity_matrix[old_idx][new_idx])
            if score >= cfg.SPLIT_MERGE_THRESHOLD:
                partial_matches.append((new_idx, score))

        if len(partial_matches) >= 2:
            splits.append({
                "old_section": old_sections[old_idx].section_number,
                "old_title": old_sections[old_idx].title,
                "new_sections": [
                    {
                        "section": new_sections[ni].section_number,
                        "title": new_sections[ni].title,
                        "similarity": round(sc, 3)
                    }
                    for ni, sc in partial_matches
                ],
                "old_content": old_sections[old_idx].content
            })
            old_matched.add(old_idx)
            for ni, _ in partial_matches:
                new_matched.add(ni)

    # Detect merges
    merges = []
    for new_idx in range(len(new_sections)):
        if new_idx in new_matched:
            continue

        partial_matches = []
        for old_idx in range(len(old_sections)):
            if old_idx in old_matched:
                continue
            score = float(similarity_matrix[old_idx][new_idx])
            if score >= cfg.SPLIT_MERGE_THRESHOLD:
                partial_matches.append((old_idx, score))

        if len(partial_matches) >= 2:
            merges.append({
                "new_section": new_sections[new_idx].section_number,
                "new_title": new_sections[new_idx].title,
                "old_sections": [
                    {
                        "section": old_sections[oi].section_number,
                        "title": old_sections[oi].title,
                        "similarity": round(sc, 3)
                    }
                    for oi, sc in partial_matches
                ],
                "new_content": new_sections[new_idx].content
            })
            new_matched.add(new_idx)
            for oi, _ in partial_matches:
                old_matched.add(oi)

    removed = []
    for old_idx in range(len(old_sections)):
        if old_idx not in old_matched:
            removed.append({
                "section": old_sections[old_idx].section_number,
                "title": old_sections[old_idx].title,
                "content": old_sections[old_idx].content
            })

    added = []
    for new_idx in range(len(new_sections)):
        if new_idx not in new_matched:
            added.append({
                "section": new_sections[new_idx].section_number,
                "title": new_sections[new_idx].title,
                "content": new_sections[new_idx].content
            })

    return {
        "matched": matched_pairs,
        "added": added,
        "removed": removed,
        "split": splits,
        "merged": merges
    }
