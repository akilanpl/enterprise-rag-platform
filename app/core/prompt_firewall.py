import re

PATTERN = re.compile(
    r"ignore previous instructions|system prompt|disregard above|override instructions", re.I
)


def sanitize_context(text: str) -> str:
    # Heuristic only. Authorization is enforced before retrieval, never by a model.
    return "[Content withheld: potential instruction injection]" if PATTERN.search(text) else text
