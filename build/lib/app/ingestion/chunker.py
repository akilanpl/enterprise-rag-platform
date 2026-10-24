import re


def chunk_text(text: str, size=600, overlap=120) -> list[str]:
    if size <= overlap or overlap < 0:
        raise ValueError("Require size > overlap >= 0")
    text = re.sub(r"\s+", " ", text).strip()
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks
