"""Application configuration — loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM Provider ─────────────────────────────────────────────────────────────
# "groq" | "huggingface" | "auto"  (auto = try Groq first, fallback to HF)
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto")

# ── Groq ─────────────────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── HuggingFace Inference API ────────────────────────────────────────────────
HF_TOKEN: str = os.getenv("HF_TOKEN", "")
HF_MODEL: str = os.getenv("HF_MODEL", "meta-llama/Llama-3.3-70B-Instruct")

# ── Shared LLM settings ─────────────────────────────────────────────────────
TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.3"))

# ── Search ───────────────────────────────────────────────────────────────────
MAX_SEARCH_QUERIES: int = int(os.getenv("MAX_SEARCH_QUERIES", "3"))
MAX_RESULTS_PER_QUERY: int = int(os.getenv("MAX_RESULTS_PER_QUERY", "5"))
MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_CONTENT_LENGTH", "3000"))

# ── API ──────────────────────────────────────────────────────────────────────
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))
WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")
WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID: str = os.getenv("WHATSAPP_PHONE_ID", "")
WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "")

# ── CORS ─────────────────────────────────────────────────────────────────────
CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
