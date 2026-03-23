import json
import logging
import time
import requests
from typing import List, Dict, Any, Optional

from oskar.config import (
    DEFAULT_MODEL,
    OLLAMA_BASE_URL,
    GENERATION_CONFIG,
    DEVICE,
    AVAILABLE_MODELS,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def log_progress(msg: str):
    print(f"[RAG_MODEL] {msg}", flush=True)


class OllamaClient:
    def __init__(self, model: str = None, base_url: str = None):
        self.model = model or DEFAULT_MODEL
        self.base_url = base_url or OLLAMA_BASE_URL
        self._verified = False
        self._available_models = []

    def verify_connection(self) -> bool:
        if self._verified:
            return True

        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()

            models_data = response.json().get("models", [])
            self._available_models = [m.get("name", "") for m in models_data]

            model_found = False
            for available in self._available_models:
                if self.model in available or available.startswith(self.model):
                    model_found = True
                    break

            if not model_found:
                available_str = ", ".join(self._available_models) if self._available_models else "none"
                log_progress(f"WARNING: Model '{self.model}' not found locally.")
                log_progress(f"Available models: {available_str}")
                log_progress(f"Run: ollama pull {self.model}")
                return False

            self._verified = True
            return True

        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                "Cannot connect to Ollama. Make sure Ollama is running:\n"
                "  - Windows: Start the Ollama app from Start Menu\n"
                "  - Or run in terminal: ollama serve\n"
                f"  - Expected URL: {self.base_url}"
            )
        except Exception as e:
            raise RuntimeError(f"Ollama connection error: {e}")

    def list_models(self) -> List[str]:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            models = response.json().get("models", [])
            return [m.get("name", "") for m in models]
        except:
            return []

    def pull_model(self, model_name: str) -> bool:
        log_progress(f"Pulling model: {model_name}...")
        try:
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                stream=True,
                timeout=600
            )
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    status = data.get("status", "")
                    if "pulling" in status or "downloading" in status:
                        log_progress(f"  {status}")
            log_progress(f"Model {model_name} pulled successfully!")
            return True
        except Exception as e:
            log_progress(f"Failed to pull model: {e}")
            return False

    def set_model(self, model_name: str):
        self.model = model_name
        self._verified = False
        log_progress(f"Switched to model: {model_name}")

    def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 400,
        system: str = None
    ) -> str:
        self.verify_connection()

        request_body = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": GENERATION_CONFIG.TOP_P,
                "num_predict": max_tokens,
                "repeat_penalty": GENERATION_CONFIG.REPEAT_PENALTY,
            }
        }

        if system:
            request_body["system"] = system

        try:
            start_time = time.time()

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=request_body,
                timeout=300
            )
            response.raise_for_status()

            result = response.json()
            generation_time = time.time() - start_time

            eval_count = result.get("eval_count", 0)
            if eval_count > 0:
                tokens_per_sec = eval_count / generation_time
                logger.info(f"Generated {eval_count} tokens in {generation_time:.1f}s ({tokens_per_sec:.1f} tok/s)")

            return result.get("response", "")

        except requests.exceptions.Timeout:
            raise RuntimeError(
                "Ollama request timed out. The model may be overloaded or "
                "the prompt is too long. Try a shorter query."
            )
        except requests.exceptions.HTTPError as e:
            error_msg = str(e)
            if "model" in error_msg.lower():
                raise RuntimeError(f"Model error: {e}. Try running: ollama pull {self.model}")
            raise RuntimeError(f"Ollama HTTP error: {e}")
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise


# Module-level singleton
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client


def set_model(model_name: str):
    client = get_ollama_client()
    client.set_model(model_name)


def get_current_model() -> str:
    client = get_ollama_client()
    return client.model


def check_ollama_status() -> Dict[str, Any]:
    client = get_ollama_client()

    try:
        client.verify_connection()
        models = client.list_models()

        return {
            "status": "connected",
            "base_url": client.base_url,
            "current_model": client.model,
            "available_models": models,
            "configured_models": list(AVAILABLE_MODELS.keys())
        }
    except Exception as e:
        return {
            "status": "disconnected",
            "error": str(e),
            "base_url": client.base_url
        }


def check_gpu_memory() -> Dict[str, Any]:
    return {
        "status": "managed_by_ollama",
        "note": "Run 'ollama ps' to see model memory usage",
        "device": DEVICE
    }


def initialize():
    log_progress("=" * 60)
    log_progress("INITIALIZING OSKAR RAG SYSTEM (Ollama Edition)")
    log_progress("=" * 60)

    log_progress("Checking Ollama connection...")
    client = get_ollama_client()

    try:
        client.verify_connection()
        log_progress(f"Ollama connected - using model: {client.model}")
    except RuntimeError as e:
        log_progress(f"WARNING: {e}")
        log_progress("OSKAR will start, but LLM generation won't work until Ollama is running.")

    models = client.list_models()
    if models:
        log_progress(f"Available models: {', '.join(models)}")

    log_progress("Initializing retriever...")
    from oskar.retrieval import ensure_initialized as ensure_retriever_initialized
    ensure_retriever_initialized()

    log_progress("Initializing RLPM pipeline...")
    try:
        from oskar.rlpm import ensure_rlpm_initialized
        ensure_rlpm_initialized()
        log_progress("RLPM pipeline initialized!")
    except Exception as e:
        log_progress(f"RLPM initialization warning: {e}")
        log_progress("RLPM features may be limited.")

    log_progress("=" * 60)
    log_progress("OSKAR RAG SYSTEM READY!")
    log_progress("=" * 60)
