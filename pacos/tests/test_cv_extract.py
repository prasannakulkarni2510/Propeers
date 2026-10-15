"""Tests for CV file -> text extraction (pacos.cv_extract). Files are built in
memory: a DOCX via a minimal word/document.xml, a PDF via pypdf. No network."""
import io
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pacos.cv_extract import CvExtractError, extract_cv_text  # noqa: E402

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _docx(*paras: str) -> bytes:
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paras)
    xml = f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", xml)
    return buf.getvalue()


def test_docx_paragraphs_become_lines():
    text = extract_cv_text("cv.docx", _docx(
        "Jane Doe, Data Scientist", "Cut churn 12% with a gradient-boosted model at Acme."))
    assert text == "Jane Doe, Data Scientist\nCut churn 12% with a gradient-boosted model at Acme."


def test_plain_text_is_tidied():
    raw = b"Jane Doe   \r\n\r\n\r\n\r\nPython, SQL, and ten years of shipping ML systems."
    assert extract_cv_text("cv.txt", raw) == "Jane Doe\n\nPython, SQL, and ten years of shipping ML systems."


def test_image_only_pdf_is_rejected_with_guidance():
    pypdf = pytest.importorskip("pypdf")
    w = pypdf.PdfWriter()
    w.add_blank_page(200, 200)
    buf = io.BytesIO()
    w.write(buf)
    with pytest.raises(CvExtractError, match="scanned PDF"):
        extract_cv_text("scan.pdf", buf.getvalue())


@pytest.mark.parametrize("name,data,msg", [
    ("cv.doc", b"legacy", ".docx or PDF"),
    ("cv.png", b"\x89PNG....", "Unsupported"),
    ("cv.docx", b"PKnot-a-zip", "Word document"),
    ("cv.txt", b"", "empty"),
])
def test_bad_inputs_raise_readable_errors(name, data, msg):
    with pytest.raises(CvExtractError, match=msg):
        extract_cv_text(name, data)
