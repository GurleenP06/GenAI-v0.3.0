from pydantic import BaseModel
from typing import List, Optional, Dict


class Project(BaseModel):
    name: str
    description: Optional[str] = ""


class ChatMetadata(BaseModel):
    session_id: str
    name: str
    project_id: Optional[str] = None
    is_favorite: bool = False
    created_at: str
    updated_at: str


class RenameRequest(BaseModel):
    session_id: str
    new_name: str


class MoveToProjectRequest(BaseModel):
    session_id: str
    project_id: Optional[str]


class ToggleFavoriteRequest(BaseModel):
    session_id: str


class ExportRequest(BaseModel):
    session_id: str
    format: str


class QueryRequest(BaseModel):
    session_id: str
    query: str
    assistant_type: Optional[str] = None
    model: Optional[str] = None


class ChatHistoryRequest(BaseModel):
    session_id: str


class RatingRequest(BaseModel):
    session_id: str
    question: str
    response: str
    sentiment: str  # "positive" or "negative"
    star_rating: int  # 1-5 overall
    scoring_parameters: Optional[Dict[str, int]] = None  # accuracy, relevance, completeness, conciseness (1-5 each)
    reasons: List[str] = []
    feedback_text: str = ""
    citations: Optional[Dict] = None
    assistant_type: Optional[str] = None
    model: Optional[str] = None


class DocumentViewRequest(BaseModel):
    filename: str
    original_extension: str
    highlights: List[Dict]


class ModelChangeRequest(BaseModel):
    model: str


class RegisterSessionRequest(BaseModel):
    name: str
    role: str


class NewChatRequest(BaseModel):
    project_id: Optional[str] = None
    user_name: Optional[str] = None
    user_role: Optional[str] = None


class LogInteractionRequest(BaseModel):
    session_id: str
    question: str
    response: str
    response_time_ms: int
    assistant_type: Optional[str] = None
    model: Optional[str] = None
