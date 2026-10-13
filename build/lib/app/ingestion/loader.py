from pathlib import Path

from pypdf import PdfReader


def load_pdf(path: str) -> str:
    """Operator-only local loader; no API accepts filesystem paths or arbitrary URLs."""
    with Path(path).open("rb") as source:
        return "\n".join(page.extract_text() or "" for page in PdfReader(source).pages)
