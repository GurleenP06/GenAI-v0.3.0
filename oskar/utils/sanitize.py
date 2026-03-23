"""Response text sanitization utilities."""

import math
from typing import Any

import pandas as pd


def clean_response_text(text: str) -> str:
    """Remove model artifacts from generated text."""
    text = text.replace('\x00', '').replace('\ufffd', '')

    artifacts = [
        "[/INST]", "[INST]", "<s>", "</s>", "<<SYS>>", "<</SYS>>",
        "SOURCES:", "User Question:", "Based ONLY on"
    ]

    for artifact in artifacts:
        if artifact in text:
            parts = text.split(artifact)
            if artifact in ["[/INST]", "<<SYS>>"]:
                text = parts[-1] if len(parts) > 1 else text
            else:
                text = parts[0]

    return text.strip()


def sanitize_for_json(obj: Any) -> Any:
    """Replace NaN/Inf values to make objects JSON-serializable."""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return 0.0
        return obj
    elif pd.isna(obj):
        return ""
    else:
        return obj
