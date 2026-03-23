from dataclasses import dataclass
from typing import Dict


OLLAMA_BASE_URL = "http://localhost:11434"


@dataclass
class ModelConfig:
    name: str
    display_name: str
    context_length: int
    description: str
    recommended_for: str


AVAILABLE_MODELS: Dict[str, ModelConfig] = {
    "mistral": ModelConfig(
        name="mistral",
        display_name="Mistral 7B",
        context_length=8192,
        description="Fast, efficient 7B model with good instruction following",
        recommended_for="General queries, fast responses"
    ),
    "llama3.1": ModelConfig(
        name="llama3.1",
        display_name="Llama 3.1 8B",
        context_length=8192,
        description="Meta's latest 8B model with strong reasoning",
        recommended_for="Complex reasoning, detailed analysis"
    ),
    "mistral-nemo": ModelConfig(
        name="mistral-nemo",
        display_name="Mistral Nemo 12B",
        context_length=8192,
        description="Larger Mistral model with improved capabilities",
        recommended_for="Detailed document analysis"
    ),
    "llama3-chatqa": ModelConfig(
        name="llama3-chatqa",
        display_name="Llama3 ChatQA 8B",
        context_length=8192,
        description="Optimized for conversational Q&A and RAG",
        recommended_for="Question answering, RAG applications"
    ),
}

DEFAULT_MODEL = "mistral"


def get_model_config(model_name: str) -> ModelConfig:
    if model_name in AVAILABLE_MODELS:
        return AVAILABLE_MODELS[model_name]
    return AVAILABLE_MODELS[DEFAULT_MODEL]


def list_available_models() -> list:
    return [
        {
            "name": cfg.name,
            "display_name": cfg.display_name,
            "description": cfg.description,
            "recommended_for": cfg.recommended_for
        }
        for cfg in AVAILABLE_MODELS.values()
    ]
