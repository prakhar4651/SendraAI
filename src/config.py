"""Configuration settings for the multi-agent code review pipeline."""

import os
import pathlib
from dotenv import load_dotenv

# Ensure .env is loaded from project root and current working directory
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")
load_dotenv()

# Standard Windows SSL / certificate inspection workaround
os.environ["PYTHONHTTPSVERIFY"] = "0"
try:
    import certifi
    os.environ["SSL_CERT_FILE"] = certifi.where()
except Exception:
    pass

# LLM Provider Configuration (Groq)
MODEL = os.getenv("MODEL", "openai/gpt-oss-120b")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "qwen/qwen3.8-27b")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))

# Logging
LOG_FILE = "logs/review.log"

# Diff chunking — diffs larger than this are truncated per-file before being
# sent to agents, keeping each LLM call within a safe token budget.
MAX_DIFF_CHARS = 40_000


def get_llm(
    model: str = MODEL,
    fallback_model: str | None = FALLBACK_MODEL,
    temperature: float = TEMPERATURE,
    max_tokens: int | None = None,
):
    """Instantiate a ChatGroq LLM instance with fallback support."""
    from langchain_groq import ChatGroq

    primary_kwargs = {"model": model, "temperature": temperature}
    if max_tokens:
        primary_kwargs["max_tokens"] = max_tokens
    primary = ChatGroq(**primary_kwargs)

    if fallback_model and fallback_model != model:
        fallback_kwargs = {"model": fallback_model, "temperature": temperature}
        # qwen models on Groq on-demand tier require max_tokens <= 1000 due to OTPM limits
        if "qwen" in fallback_model.lower():
            fallback_kwargs["max_tokens"] = min(max_tokens or 800, 800)
        elif max_tokens:
            fallback_kwargs["max_tokens"] = max_tokens
        fallback = ChatGroq(**fallback_kwargs)
        return primary.with_fallbacks([fallback])
    return primary


