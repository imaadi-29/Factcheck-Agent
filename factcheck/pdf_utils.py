"""Step 1 - READ: turn an uploaded PDF into plain text, page by page.

We keep the page number for every piece of text so the final report can
say exactly where in the document each claim came from.
"""

import pymupdf as fitz  # PyMuPDF (reads PDFs)

MAX_PAGES = 40          # keeps API usage (and cost) predictable
MAX_CHARS_PER_PAGE = 6000


class PDFError(Exception):
    """Raised when the PDF cannot be used (corrupt, encrypted, scanned, ...)."""


def extract_pages(pdf_bytes: bytes) -> tuple[list[dict], int]:
    """Return ([{"page": 1, "text": "..."}, ...], total_page_count) for pages that have text."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:  # corrupt or not a PDF
        raise PDFError("This file could not be opened as a PDF.") from exc

    if doc.needs_pass:
        raise PDFError("This PDF is password-protected. Please upload an unlocked copy.")

    pages = []
    for index, page in enumerate(doc):
        if index >= MAX_PAGES:
            break
        text = " ".join(page.get_text("text").split())  # collapse whitespace
        if text:
            pages.append({"page": index + 1, "text": text[:MAX_CHARS_PER_PAGE]})
    total_pages = doc.page_count
    doc.close()

    if not pages:
        raise PDFError(
            "No selectable text was found. The PDF may be a scanned image; "
            "please upload a PDF with real text."
        )
    return pages, total_pages
