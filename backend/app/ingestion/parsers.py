import io

from docx import Document as DocxDocument
from pypdf import PdfReader

TEXT_MIME_TYPES = {"text/plain", "text/markdown", "text/csv"}
PDF_MIME_TYPE = "application/pdf"
DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def extract_text(mime_type: str, raw: bytes) -> str:
    if mime_type in TEXT_MIME_TYPES:
        return raw.decode("utf-8", errors="replace")

    if mime_type == PDF_MIME_TYPE:
        reader = PdfReader(io.BytesIO(raw))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)

    if mime_type == DOCX_MIME_TYPE:
        doc = DocxDocument(io.BytesIO(raw))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)

    raise ValueError(f"Unsupported mime type for text extraction: {mime_type}")
