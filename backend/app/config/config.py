import logging
import os

from dotenv import load_dotenv

# Explicitly load .env from backend root
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(base_dir, ".env"))

class Config:
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:3000")
    ENABLE_LLM_SUMMARIZATION = os.getenv("ENABLE_LLM_SUMMARIZATION", "true").lower() in ("true", "1", "yes")

config = Config()
logger = logging.getLogger(__name__)
if not config.OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY is missing; LLM features may be disabled.")
