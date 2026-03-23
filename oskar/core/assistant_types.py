from enum import Enum


class AssistantType(Enum):
    GENERAL = "general"
    WRITING = "writing"
    DOCUMENT_SPECIFIC = "document_specific"
    OPO_SEARCH = "opo_search"
    PROCEDURE = "procedure"
    LIST_EXTRACTION = "list_extraction"
    RLPM_ANALYST = "rlpm_analyst"
