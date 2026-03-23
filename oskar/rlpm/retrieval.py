from typing import List, Dict, Tuple

from oskar.config import RLPM_CONFIG
from oskar.rlpm.index_manager import get_rlpm_manager


def retrieve_for_rlpm_analysis(
    query: str,
    target_doc_chunks: List[Tuple[str, Dict]],
    top_k_rlpm: int = None
) -> Dict[str, List[Tuple[str, Dict]]]:

    mgr = get_rlpm_manager()
    cfg = RLPM_CONFIG

    if top_k_rlpm is None:
        top_k_rlpm = cfg.RLPM_RETRIEVAL_TOP_K

    rlpm_context = mgr.search_rlpm_references(query, top_k=top_k_rlpm)

    if target_doc_chunks:
        sample_text = ' '.join([c[0][:200] for c in target_doc_chunks[:3]])
        additional_rlpm = mgr.search_rlpm_references(sample_text, top_k=5)

        seen = set()
        for text, meta in rlpm_context:
            seen.add(text[:100])

        for text, meta in additional_rlpm:
            if text[:100] not in seen:
                rlpm_context.append((text, meta))
                seen.add(text[:100])

    return {
        "rlpm_references": rlpm_context,
        "target_document": target_doc_chunks
    }
