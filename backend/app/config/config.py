import os
from dotenv import load_dotenv

# Explicitly load .env from backend root
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(base_dir, ".env"))

class Config:
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

config = Config()
if config.OPENAI_API_KEY:
    print(f"[OK] Loaded OPENAI_API_KEY: {config.OPENAI_API_KEY[:5]}...")
else:
    print("[ERROR] OPENAI_API_KEY is missing!")
