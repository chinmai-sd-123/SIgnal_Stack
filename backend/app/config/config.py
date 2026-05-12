import logging
import os

from dotenv import load_dotenv

# Explicitly load .env from backend root
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(base_dir, ".env"))


DEFAULT_MODEL_PRICING_PER_1M = {
    "gpt-5.5": {"input": 5.00, "output": 30.00},
    "gpt-5.4": {"input": 2.50, "output": 15.00},
    "gpt-5.4-mini": {"input": 0.75, "output": 4.50},
    "gpt-5-mini": {"input": 0.25, "output": 2.00},
    "gpt-5": {"input": 1.25, "output": 10.00},
    "gpt-5-nano": {"input": 0.05, "output": 0.40},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}


def _pricing_default(model: str, direction: str) -> float:
    model_key = (model or "").strip()
    return DEFAULT_MODEL_PRICING_PER_1M.get(model_key, {}).get(direction, 0.0)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return float(raw)


class Config:
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    LLM_INPUT_COST_PER_1M = _env_float("LLM_INPUT_COST_PER_1M", _pricing_default(OPENAI_MODEL, "input"))
    LLM_OUTPUT_COST_PER_1M = _env_float("LLM_OUTPUT_COST_PER_1M", _pricing_default(OPENAI_MODEL, "output"))
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:3000")
    ENABLE_LLM_SUMMARIZATION = os.getenv("ENABLE_LLM_SUMMARIZATION", "true").lower() in ("true", "1", "yes")

config = Config()
logger = logging.getLogger(__name__)
if not config.OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY is missing; LLM features may be disabled.")
