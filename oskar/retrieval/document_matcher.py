"""Document matching utilities for identifying referenced documents in queries."""

import re
from typing import List, Tuple
from difflib import SequenceMatcher


def normalize_for_matching(text: str) -> str:
    text = text.upper()
    text = re.sub(r'[_\-./\\]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_potential_doc_refs(query: str) -> List[str]:
    potential_refs = []
    query_upper = query.upper()

    pattern1 = r'\b([A-Z]{2,10})[\s_\-]*(\d+(?:[\s_\-./]\d+)*)\b'
    for match in re.finditer(pattern1, query_upper):
        prefix = match.group(1)
        numbers = match.group(2)
        potential_refs.append(f"{prefix} {numbers}")
        potential_refs.append(f"{prefix}_{numbers}")
        potential_refs.append(f"{prefix}{numbers}")
        norm_nums = re.sub(r'[\s_\-./]', '_', numbers)
        potential_refs.append(f"{prefix}_{norm_nums}")

    seen = set()
    unique_refs = []
    for ref in potential_refs:
        ref_norm = normalize_for_matching(ref)
        if ref_norm not in seen and len(ref_norm) > 2:
            seen.add(ref_norm)
            unique_refs.append(ref)

    return unique_refs


def fuzzy_match_score(ref: str, filename: str) -> float:
    ref_norm = normalize_for_matching(ref)
    file_norm = normalize_for_matching(filename)

    if ref_norm in file_norm:
        return 0.9 + (len(ref_norm) / len(file_norm)) * 0.1

    ref_parts = ref_norm.split()
    file_parts = file_norm.split()

    matches = 0
    for rp in ref_parts:
        for fp in file_parts:
            if rp in fp or fp in rp:
                matches += 1
                break

    if matches == len(ref_parts) and len(ref_parts) > 0:
        return 0.7 + (matches / len(file_parts)) * 0.2

    return SequenceMatcher(None, ref_norm, file_norm).ratio() * 0.6


def find_matching_filenames(potential_refs: List[str], all_filenames: List[str], threshold: float = 0.5) -> List[Tuple[str, float]]:
    matches = []

    for filename in all_filenames:
        best_score = 0.0
        for ref in potential_refs:
            score = fuzzy_match_score(ref, filename)
            best_score = max(best_score, score)

        if best_score >= threshold:
            matches.append((filename, best_score))

    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


def get_target_documents(query: str, all_filenames: List[str]) -> List[str]:
    potential_refs = extract_potential_doc_refs(query)

    if not potential_refs:
        return []

    matches = find_matching_filenames(potential_refs, all_filenames, threshold=0.5)

    if not matches:
        return []

    if matches[0][1] >= 0.85:
        return [matches[0][0]]

    return [fn for fn, score in matches[:2] if score >= 0.5]
