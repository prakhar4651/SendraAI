"""SendraAI (backwards compatibility alias for code_review).

Prefer:
    from sendra_ai import run_review
"""

from sendra_ai import run_review, __version__

__all__ = ["run_review", "__version__"]
