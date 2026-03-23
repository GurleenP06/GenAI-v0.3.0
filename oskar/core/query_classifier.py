import re
from oskar.core.assistant_types import AssistantType


def detect_query_type(query: str) -> str:
    query_lower = query.lower()

    list_patterns = [
        r'\blist\b', r'\blist all\b', r'\bwhat are the\b', r'\bwhat types\b',
        r'\bhow many\b', r'\ball the\b', r'\bevery\b', r'\bwhat kinds\b',
        r'\beach\b', r'\bdifferent kinds\b', r'\bcategories\b', r'\btypes of\b',
        r'\bwhat .+ are there\b', r'\bname the\b', r'\bidentify all\b'
    ]
    for pattern in list_patterns:
        if re.search(pattern, query_lower):
            return 'list'

    procedure_patterns = [
        r'\bhow to\b', r'\bsteps to\b', r'\bsteps for\b', r'\bprocedure for\b',
        r'\bprocess for\b', r'\bwhat is the process\b', r'\bhow do i\b',
        r'\bhow do you\b', r'\bwalk me through\b', r'\bguide me\b'
    ]
    for pattern in procedure_patterns:
        if re.search(pattern, query_lower):
            return 'procedure'

    compare_patterns = [r'\bcompare\b', r'\bversus\b', r'\bvs\.?\b', r'\bdifference between\b', r'\bdifferences\b']
    for pattern in compare_patterns:
        if re.search(pattern, query_lower):
            return 'compare'

    explain_patterns = [
        r'\bwhat is\b', r'\bwhat are\b', r'\bdefine\b', r'\bexplain\b',
        r'\bdescribe\b', r'\bwhat does .+ mean\b', r'\bmeaning of\b'
    ]
    for pattern in explain_patterns:
        if re.search(pattern, query_lower):
            return 'explain'

    return 'general'


def classify_query(query: str) -> AssistantType:
    query_lower = query.lower()
    query_type = detect_query_type(query)

    if query_type == 'list':
        return AssistantType.LIST_EXTRACTION

    if query_type == 'procedure':
        return AssistantType.PROCEDURE

    writing_keywords = {'write', 'draft', 'compose', 'email', 'letter', 'template',
                       'format', 'rewrite', 'edit', 'proofread', 'create a', 'prepare a',
                       'memo', 'report', 'document', 'proposal'}
    for keyword in writing_keywords:
        if re.search(rf'\b{re.escape(keyword)}\b', query_lower):
            return AssistantType.WRITING

    comparison_keywords = {'compare', 'difference', 'versus', 'vs', 'between', 'contrast'}
    for keyword in comparison_keywords:
        if re.search(rf'\b{re.escape(keyword)}\b', query_lower):
            return AssistantType.DOCUMENT_SPECIFIC

    doc_patterns = [
        r'\b(opmp|opmwi|imp|mmp|qmsp|iso|as9100)\s*[\d._-]+',
        r'\bfrom\s+\w+\s*[\d._-]+',
        r'\bin\s+\w+\s*[\d._-]+',
    ]
    for pattern in doc_patterns:
        if re.search(pattern, query_lower):
            return AssistantType.DOCUMENT_SPECIFIC

    opo_keywords = {
        'opo', 'operations', 'program', 'management', 'opmp', 'imp', 'procedure',
        'as9100', 'iso', 'standard', 'quality', 'compliance', 'audit', 'inventory',
        'cycle count', 'sap', 'mrp', 'erp', 'supplier', 'procurement',
        'non-conformance', 'corrective action', 'capa', 'qms', 'change order', 'co'
    }
    for keyword in opo_keywords:
        if re.search(rf'\b{re.escape(keyword)}\b', query_lower):
            return AssistantType.OPO_SEARCH

    return AssistantType.GENERAL
