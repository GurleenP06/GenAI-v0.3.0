"""Response generation service - orchestrates query -> retrieval -> generation -> citation."""

import logging
from typing import List, Dict, Tuple, Any, Optional

import pandas as pd

from oskar.config import GENERATION_CONFIG, RLPM_CONFIG
from oskar.core.assistant_types import AssistantType
from oskar.core.query_classifier import detect_query_type, classify_query
from oskar.core.prompts import SYSTEM_PROMPTS, build_prompt
from oskar.services.model_service import get_ollama_client
from oskar.utils.text import get_original_extension, extract_citations
from oskar.utils.sanitize import clean_response_text, sanitize_for_json

logger = logging.getLogger(__name__)


def build_context_section(
    retrieved_docs: List[str],
    retrieved_metadata: List[Dict],
    max_chars: int = None
) -> Tuple[str, Dict[int, Dict]]:

    if max_chars is None:
        max_chars = GENERATION_CONFIG.MAX_CONTEXT_CHARS

    docs_by_file = {}
    meta_by_file = {}

    for doc, meta in zip(retrieved_docs, retrieved_metadata):
        filename = meta['filename']
        if filename not in docs_by_file:
            docs_by_file[filename] = []
            meta_by_file[filename] = meta
        docs_by_file[filename].append(doc.strip())

    context_parts = []
    doc_mapping = {}
    current_chars = 0

    doc_idx = 1
    for filename, chunks in docs_by_file.items():
        meta = meta_by_file[filename]

        combined_text = "\n\n".join(chunks)

        base_name = filename.replace('.txt', '')
        doc_header = f"[{doc_idx}] {base_name}:\n"
        full_doc = doc_header + combined_text

        if current_chars + len(full_doc) > max_chars:
            remaining = max_chars - current_chars - len(doc_header) - 100
            if remaining > 200:
                full_doc = doc_header + combined_text[:remaining] + "..."
            else:
                break

        context_parts.append(full_doc)
        current_chars += len(full_doc)

        doc_mapping[doc_idx] = {
            'filename': filename,
            'display_filename': base_name,
            'original_extension': get_original_extension(filename),
            'source_url': meta.get('source_url', ''),
            'content': combined_text,
            'chunk_count': len(chunks)
        }

        doc_idx += 1

    if not context_parts:
        return "", {}

    context_section = "SOURCES:\n\n" + "\n\n---\n\n".join(context_parts)

    logger.info(f"Context: {len(doc_mapping)} sources, ~{current_chars} chars")

    return context_section, doc_mapping


def build_rlpm_context_section(
    rlpm_refs: List[Tuple[str, Dict]],
    target_chunks: List[Tuple[str, Dict]],
    fewshot_text: str,
    comparison_summary: str,
    max_chars: int = None
) -> Tuple[str, Dict[int, Dict]]:

    if max_chars is None:
        max_chars = RLPM_CONFIG.RLPM_MAX_CONTEXT_CHARS

    doc_mapping = {}
    current_chars = 0
    parts = []
    doc_idx = 1

    if fewshot_text:
        parts.append(fewshot_text)
        current_chars += len(fewshot_text)

    if comparison_summary:
        parts.append(comparison_summary)
        current_chars += len(comparison_summary)

    rlpm_by_file = {}
    rlpm_meta_by_file = {}
    for text, meta in rlpm_refs:
        fn = meta['filename']
        if fn not in rlpm_by_file:
            rlpm_by_file[fn] = []
            rlpm_meta_by_file[fn] = meta
        rlpm_by_file[fn].append(text.strip())

    parts.append("\nRLPM REQUIREMENTS (from GCP-59 and stage documents):\n")

    for filename, chunks in rlpm_by_file.items():
        combined = "\n\n".join(chunks)
        base_name = filename.replace('.txt', '').replace('.pdf', '').replace('.docx', '')
        header = f"[{doc_idx}] {base_name} (RLPM Reference):\n"
        full_text = header + combined

        if current_chars + len(full_text) > max_chars * 0.5:
            remaining = int(max_chars * 0.5) - current_chars - len(header) - 50
            if remaining > 200:
                full_text = header + combined[:remaining] + "..."
            else:
                break

        parts.append(full_text)
        current_chars += len(full_text)

        doc_mapping[doc_idx] = {
            'filename': filename,
            'display_filename': base_name,
            'original_extension': '',
            'source_url': '',
            'content': combined,
            'chunk_count': len(chunks),
            'source_type': 'rlpm_reference'
        }
        doc_idx += 1

    target_by_file = {}
    target_meta_by_file = {}
    for text, meta in target_chunks:
        fn = meta['filename']
        if fn not in target_by_file:
            target_by_file[fn] = []
            target_meta_by_file[fn] = meta
        target_by_file[fn].append(text.strip())

    parts.append("\n\nTARGET DOCUMENT TO ANALYZE:\n")

    for filename, chunks in target_by_file.items():
        meta = target_meta_by_file[filename]
        combined = "\n\n".join(chunks)
        base_name = filename.replace('.txt', '')
        header = f"[{doc_idx}] {base_name} (Target Document):\n"
        full_text = header + combined

        remaining_budget = max_chars - current_chars - len(header) - 100
        if remaining_budget > 200:
            if len(full_text) > remaining_budget:
                full_text = header + combined[:remaining_budget] + "..."
        else:
            break

        parts.append(full_text)
        current_chars += len(full_text)

        doc_mapping[doc_idx] = {
            'filename': filename,
            'display_filename': base_name,
            'original_extension': get_original_extension(filename),
            'source_url': meta.get('source_url', ''),
            'content': combined,
            'chunk_count': len(chunks),
            'source_type': 'target_document'
        }
        doc_idx += 1

    context_section = '\n'.join(parts)
    logger.info(f"RLPM Context: {len(doc_mapping)} sources, ~{current_chars} chars")

    return context_section, doc_mapping


def _process_citations(response_text: str, doc_mapping: Dict) -> Tuple[Dict, Dict]:
    citations_found = extract_citations(response_text)
    citation_info = {}
    highlighted_passages = {}

    for citation in citations_found:
        try:
            doc_idx = int(citation)
            if doc_idx in doc_mapping:
                doc_info = doc_mapping[doc_idx]
                citation_info[citation] = {
                    'filename': str(doc_info['filename']),
                    'display_filename': str(doc_info['display_filename']),
                    'original_extension': str(doc_info.get('original_extension', '')),
                    'source_url': str(doc_info['source_url']) if doc_info['source_url'] else '',
                    'chunk_count': doc_info.get('chunk_count', 1)
                }

                content = doc_info['content']
                excerpt = content[:500]
                if '\n\n' in excerpt:
                    excerpt = excerpt.split('\n\n')[0]
                if len(content) > 500:
                    excerpt += "..."

                highlighted_passages[citation] = [{
                    'filename': doc_info['filename'],
                    'display_filename': doc_info['display_filename'],
                    'passage': excerpt
                }]

        except (ValueError, KeyError) as e:
            logger.warning(f"Citation error [{citation}]: {e}")

    return citation_info, highlighted_passages


def _generate_rlpm_response(
    query: str,
    client,
    max_new_tokens: int = None,
    temperature: float = None
) -> Dict[str, Any]:

    from oskar.retrieval import retrieve_knowledge, get_index_manager, get_target_documents, hybrid_search
    from oskar.rlpm import get_rlpm_manager, ensure_rlpm_initialized, retrieve_for_rlpm_analysis

    ensure_rlpm_initialized()
    rlpm_mgr = get_rlpm_manager()
    main_idx = get_index_manager()

    rlpm_cfg = RLPM_CONFIG
    effective_max_tokens = max_new_tokens or rlpm_cfg.RLPM_MAX_TOKENS
    effective_temperature = temperature or rlpm_cfg.RLPM_TEMPERATURE

    logger.info(f"RLPM Analysis: {query[:80]}...")
    logger.info(f"Model: {client.model}")

    target_filenames = get_target_documents(query, main_idx.unique_filenames)

    if not target_filenames:
        logger.info("No specific document referenced - using general RLPM search")
        target_chunks = retrieve_knowledge(query, top_k=rlpm_cfg.TARGET_DOC_TOP_K)
    else:
        logger.info(f"Target documents: {target_filenames}")
        target_chunks = []
        for tf in target_filenames:
            chunk_count = main_idx.get_chunk_count_for_file(tf)
            if chunk_count <= 30:
                chunks = main_idx.get_all_chunks_from_file(tf)
                for c in chunks:
                    target_chunks.append((
                        c['chunk_text'],
                        {
                            'filename': c['filename'],
                            'source_url': c['source_url'] if pd.notna(c.get('source_url')) else ''
                        }
                    ))
            else:
                results = hybrid_search(query, top_k=rlpm_cfg.TARGET_DOC_TOP_K, filter_filenames=[tf])
                target_chunks.extend(results)

    retrieval_result = retrieve_for_rlpm_analysis(query, target_chunks)
    rlpm_refs = retrieval_result["rlpm_references"]

    logger.info(f"RLPM refs: {len(rlpm_refs)} chunks, Target: {len(target_chunks)} chunks")

    fewshot_text = rlpm_mgr.get_fewshot_prompt_text()
    comparison_summary = rlpm_mgr.get_comparison_summary()

    context_section, doc_mapping = build_rlpm_context_section(
        rlpm_refs=rlpm_refs,
        target_chunks=target_chunks,
        fewshot_text=fewshot_text,
        comparison_summary=comparison_summary,
        max_chars=rlpm_cfg.RLPM_MAX_CONTEXT_CHARS
    )

    system_prompt = SYSTEM_PROMPTS[AssistantType.RLPM_ANALYST]

    prompt = build_prompt(
        query=query,
        context=context_section,
        system_prompt=system_prompt,
        model_name=client.model,
        query_type='rlpm'
    )

    logger.info("Generating RLPM analysis...")

    response_text = client.generate(
        prompt=prompt,
        temperature=effective_temperature,
        max_tokens=effective_max_tokens
    )

    response_text = clean_response_text(response_text)

    citation_info, highlighted_passages = _process_citations(response_text, doc_mapping)

    return sanitize_for_json({
        'response': response_text,
        'citations': citation_info,
        'highlighted_passages': highlighted_passages,
        'source_documents': {
            str(k): {
                'filename': v['filename'],
                'display_filename': v['display_filename'],
                'source_url': v['source_url']
            } for k, v in doc_mapping.items()
        },
        'assistant_type': 'rlpm_analyst',
        'query_type': 'rlpm',
        'model_used': client.model
    })


def generate_response_with_citations(
    query: str,
    history: Optional[List[Dict]] = None,
    max_new_tokens: int = None,
    temperature: float = None,
    assistant_type: Optional[AssistantType] = None,
    model: str = None
) -> Dict[str, Any]:

    try:
        from oskar.retrieval import retrieve_knowledge, ensure_initialized as ensure_retriever_initialized

        ensure_retriever_initialized()

        client = get_ollama_client()
        if model:
            client.set_model(model)

        if isinstance(assistant_type, str):
            type_map = {
                'general': AssistantType.GENERAL,
                'writing': AssistantType.WRITING,
                'document': AssistantType.DOCUMENT_SPECIFIC,
                'document_specific': AssistantType.DOCUMENT_SPECIFIC,
                'opo': AssistantType.OPO_SEARCH,
                'opo_search': AssistantType.OPO_SEARCH,
                'procedure': AssistantType.PROCEDURE,
                'list': AssistantType.LIST_EXTRACTION,
                'list_extraction': AssistantType.LIST_EXTRACTION,
                'rlpm': AssistantType.RLPM_ANALYST,
                'rlpm_analyst': AssistantType.RLPM_ANALYST,
            }
            assistant_type = type_map.get(assistant_type, AssistantType.GENERAL)

        query_type = detect_query_type(query)

        if assistant_type is None:
            assistant_type = classify_query(query)

        if assistant_type == AssistantType.RLPM_ANALYST:
            return _generate_rlpm_response(
                query=query,
                client=client,
                max_new_tokens=max_new_tokens,
                temperature=temperature
            )

        gen_config = GENERATION_CONFIG

        if assistant_type in [AssistantType.PROCEDURE, AssistantType.LIST_EXTRACTION]:
            effective_max_tokens = max_new_tokens or gen_config.MAX_NEW_TOKENS_OPO
            effective_temperature = temperature or gen_config.PROCEDURE_TEMPERATURE
            retrieval_top_k = 10
        elif assistant_type == AssistantType.OPO_SEARCH:
            effective_max_tokens = max_new_tokens or gen_config.MAX_NEW_TOKENS_OPO
            effective_temperature = temperature or gen_config.OPO_TEMPERATURE
            retrieval_top_k = gen_config.OPO_RETRIEVAL_TOP_K
        elif assistant_type == AssistantType.WRITING:
            effective_max_tokens = max_new_tokens or gen_config.MAX_NEW_TOKENS_WRITING
            effective_temperature = temperature or gen_config.WRITING_TEMPERATURE
            retrieval_top_k = gen_config.WRITING_RETRIEVAL_TOP_K
        elif assistant_type == AssistantType.DOCUMENT_SPECIFIC:
            effective_max_tokens = max_new_tokens or gen_config.MAX_NEW_TOKENS_OPO
            effective_temperature = temperature or gen_config.OPO_TEMPERATURE
            retrieval_top_k = 10
        else:
            effective_max_tokens = max_new_tokens or gen_config.MAX_NEW_TOKENS_DEFAULT
            effective_temperature = temperature or gen_config.DEFAULT_TEMPERATURE
            retrieval_top_k = gen_config.DEFAULT_RETRIEVAL_TOP_K

        logger.info(f"Query: {query[:50]}...")
        logger.info(f"Type: {assistant_type.value} | Query Type: {query_type} | Model: {client.model}")

        candidates = retrieve_knowledge(query, top_k=retrieval_top_k)

        retrieved_docs = [doc for doc, meta in candidates]
        retrieved_metadata = [meta for doc, meta in candidates]

        meaningful_docs = []
        meaningful_meta = []
        for doc, meta in zip(retrieved_docs, retrieved_metadata):
            if len(doc.strip()) > 50:
                meaningful_docs.append(doc)
                meaningful_meta.append(meta)

        logger.info(f"Retrieved: {len(meaningful_docs)} chunks")

        context_section, doc_mapping = build_context_section(
            meaningful_docs,
            meaningful_meta
        )

        system_prompt = SYSTEM_PROMPTS[assistant_type]

        prompt = build_prompt(
            query=query,
            context=context_section,
            system_prompt=system_prompt,
            model_name=client.model,
            query_type=query_type
        )

        logger.info(f"Generating response...")

        response_text = client.generate(
            prompt=prompt,
            temperature=effective_temperature,
            max_tokens=effective_max_tokens
        )

        response_text = clean_response_text(response_text)

        citation_info, highlighted_passages = _process_citations(response_text, doc_mapping)

        response_dict = {
            'response': response_text,
            'citations': citation_info,
            'highlighted_passages': highlighted_passages,
            'source_documents': {
                str(k): {
                    'filename': v['filename'],
                    'display_filename': v['display_filename'],
                    'source_url': v['source_url']
                } for k, v in doc_mapping.items()
            },
            'assistant_type': assistant_type.value,
            'query_type': query_type,
            'model_used': client.model
        }

        return sanitize_for_json(response_dict)

    except Exception as e:
        logger.exception("Error generating response")
        from oskar.services.model_service import get_current_model
        return {
            'response': f"An error occurred: {str(e)}. Please try again.",
            'citations': {},
            'highlighted_passages': {},
            'source_documents': {},
            'assistant_type': 'general',
            'query_type': 'general',
            'model_used': get_current_model()
        }
