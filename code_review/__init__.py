"""SendraAI: Multi-Agent Autonomous Code Review & PR Risk Guardrail.

Public API:
    run_review(code_diff, file_paths) -> str
"""

from src.main import run_review

__version__ = "0.1.0"
__all__ = ["run_review"]
