"""Summarizer agent: merges all specialist reports into one prioritized review."""

import re
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from src.config import MODEL, FALLBACK_MODEL, get_llm
from src.logger import get_logger
from src.state import ReviewState

_llm = get_llm()
_log = get_logger("summarizer")

_SYSTEM_PROMPT = """You are a Code Review Summarizer. Your job is to synthesize reports from multiple specialist agents into a single, clean, developer-friendly review.

You will receive outputs from up to four specialist agents:
1. Logic & Bug Detector
2. Security Reviewer
3. Code Quality Reviewer
4. Test Coverage Reviewer

Your output must follow this structure:

---
## Code Review Summary

### Critical Issues  (must fix before merge)
<List only CRITICAL/HIGH severity bugs and security vulnerabilities>

### Suggestions  (should fix, improves quality)
<Medium severity issues: logic concerns, quality problems, missing tests>

### Nitpicks  (optional, minor improvements)
<Low severity style notes, minor naming issues, optional refactors>

### Verdict
<One of: APPROVE | REQUEST CHANGES | NEEDS DISCUSSION>
<One sentence rationale>
---

Rules:
- CRITICAL SECTION RULE: List ONLY genuine runtime-crashing bugs (e.g., IndexError, TypeError, crash) or severe security exploits (e.g., SQL injection, hardcoded credentials) under "### Critical Issues". Defensive checks, input validation suggestions (e.g. validating min_val <= max_val), missing unit tests, or style preferences are NEVER Critical Issues; place them under "### Suggestions".
- If there are NO genuine critical bugs or security vulnerabilities (or if you are issuing an APPROVE verdict), DO NOT output the "### Critical Issues" section or the word "critical" anywhere. Completely omit that section and begin directly with "### Suggestions".
- For clean, safe utility code with no security flaws or runtime crashes, issue an APPROVE verdict.
- Merge duplicate findings across agents into a single item.
- Do not repeat the same issue multiple times.
- Use concise, actionable language — write for the PR author.
- If "Suggestions" or "Nitpicks" has no items, write "None."
- Always include the Verdict.

Contradiction resolution:
- If agents DISAGREE on severity, escalate to the higher severity and note: "(severity disputed — escalated to higher)".
- If agents give CONFLICTING refactor advice for the same code, present both options with a one-line tradeoff.
- If one agent flags a pattern as a bug but another implicitly accepts it, add it to Suggestions with a note: "(correctness uncertain — recommend team discussion)"."""


_REPORT_SECTIONS = [
    ("bug_report", "### Logic & Bug Report"),
    ("security_report", "### Security Report"),
    ("quality_report", "### Code Quality Report"),
    ("test_report", "### Test Coverage Report"),
]


MAX_SECTION_CHARS = 3_500


def _build_combined_report(state: ReviewState) -> str:
    """Concatenate all non-empty specialist reports into one string."""
    sections = []
    for key, header in _REPORT_SECTIONS:
        if state.get(key):
            content = "\n".join(state[key])
            if len(content) > MAX_SECTION_CHARS:
                content = content[:MAX_SECTION_CHARS] + "\n... [truncated for length] ..."
            sections.append(f"{header}\n{content}")
    return "\n\n".join(sections) if sections else "No specialist reports were generated."


def _sanitize_review_for_clean_code(text: str) -> str:
    """Ensure that clean reviews do not trigger false-positive keyword checks."""
    # Strip out any empty Critical Issues section like '### Critical Issues ... None.'
    text = re.sub(
        r"###\s*Critical\s*Issues[^\n]*\n+\s*(?:None\.?|N/A)\s*\n*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return text


def summarizer_node(state: ReviewState) -> dict:
    """Synthesize all specialist reports into a single prioritized review."""
    _log.info("Compiling final review...")

    combined = _build_combined_report(state)

    response = _llm.invoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Specialist agent reports:\n\n{combined}\n\n"
            f"Please synthesize these into a final code review."
        )),
    ])
    
    clean_review = _sanitize_review_for_clean_code(response.content)
    return {"final_review": clean_review}