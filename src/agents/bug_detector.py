"""Bug & Logic Detector agent: finds correctness issues in a code diff."""

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from src.config import MODEL, FALLBACK_MODEL, get_llm
from src.logger import get_logger
from src.state import ReviewState

_llm = get_llm()
_log = get_logger("bug_detector")

_SYSTEM_PROMPT = """You are a Logic & Bug Detector agent specializing in code correctness.

Analyze the provided code diff for:
- Off-by-one errors (wrong loop bounds, fence-post mistakes)
- Null/None pointer dereferences (using a variable before checking it exists)
- Infinite loops or missing loop termination conditions
- Incorrect conditionals (wrong operator, inverted logic, unreachable branches)
- Integer overflow / underflow risks
- Incorrect variable mutation inside loops
- Wrong return values or missing returns

Focus ONLY on correctness bugs. Do not comment on style, security, or test coverage.

Format your output as a numbered list. If no bugs are found, respond with:
"No logic or correctness issues detected."

Be specific: reference line numbers or code snippets from the diff where possible."""


def bug_detector_node(state: ReviewState) -> dict:
    """Scan the diff for logic and correctness bugs."""
    _log.info("Analyzing for logic errors...")

    response = _llm.invoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=f"Code diff to review:\n```\n{state['code_diff']}\n```"),
    ])

    return {"bug_report": [response.content]}
