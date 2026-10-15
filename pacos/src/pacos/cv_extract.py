"""Turn an uploaded CV file (PDF, DOCX, or plain text) into plain text.

Like the extractors, this only proposes: the operator reviews the text in the
CV editor and saves it explicitly. No model call — layout is flattened to
paragraphs, which is all the generation prompts need.
"""
from __future__ import annotations

import io
import re
import zipfile
from xml.etree import ElementTree

MAX_BYTES = 5 * 1024 * 1024  # a CV is a few hundred KB; refuse anything silly

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class CvExtractError(ValueError):
    """The file couldn't be read as a CV (wrong type, corrupt, or image-only)."""


def extract_cv_text(filename: str, data: bytes) -> str:
    if not data:
        raise CvExtractError("The file is empty.")
    if len(data) > MAX_BYTES:
        raise CvExtractError("File is larger than 5 MB. Upload the CV itself, not a portfolio.")

    name = (filename or "").lower()
    if name.endswith(".pdf") or data[:5] == b"%PDF-":
        text = _from_pdf(data)
    elif name.endswith(".docx") or (data[:2] == b"PK" and not name.endswith(".txt")):
        text = _from_docx(data)
    elif name.endswith(".doc"):
        raise CvExtractError("Old .doc files aren't supported. Save it as .docx or PDF and retry.")
    elif name.endswith((".txt", ".md")) or not name:
        text = data.decode("utf-8", errors="replace")
    else:
        raise CvExtractError("Unsupported file type. Upload a PDF, DOCX, or TXT.")

    text = _tidy(text)
    if len(text) < 40:
        raise CvExtractError(
            "Couldn't find readable text in that file. If it's a scanned PDF, "
            "export a text-based PDF or paste the text instead."
        )
    return text


def _from_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:  # optional dependency missing in this install
        raise CvExtractError("PDF support isn't installed (pip install pypdf).") from e
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        raise CvExtractError(f"Couldn't read that PDF ({type(e).__name__}).") from e


def _from_docx(data: bytes) -> str:
    """Paragraph text from word/document.xml; tables come out one cell per line."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            root = ElementTree.fromstring(z.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as e:
        raise CvExtractError("Couldn't read that DOCX. Is it a Word document?") from e
    lines = []
    for p in root.iter(f"{_W}p"):
        parts = []
        for node in p.iter():
            if node.tag == f"{_W}t" and node.text:
                parts.append(node.text)
            elif node.tag == f"{_W}tab":
                parts.append("\t")
            elif node.tag in (f"{_W}br", f"{_W}cr"):
                parts.append("\n")
        lines.append("".join(parts))
    return "\n".join(lines)


def _tidy(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = re.sub(r"[ \t ]+\n", "\n", text)   # trailing spaces
    text = re.sub(r"\n{3,}", "\n\n", text)          # collapse blank runs
    return text.strip()
