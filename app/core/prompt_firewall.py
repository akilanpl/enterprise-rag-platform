INJECTION_PATTERNS = [
    "ignore previous instructions",
    "system prompt",
    "act as",
    "override",
    "you are now",
    "disregard above"
]

def sanitize_context(text: str) -> str:
    lowered = text.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in lowered:
            return "[REMOVED: POTENTIAL PROMPT INJECTION]"
    return text
