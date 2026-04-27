"""Utility for extracting text from uploaded document files."""
import io
import logging

logger = logging.getLogger(__name__)


async def extract_text_from_upload(content: bytes, extension: str) -> str:
    """Extract text from document bytes based on file extension."""
    ext = extension.lower().lstrip(".")

    if ext == "txt":
        return _decode_text(content)

    if ext == "pdf":
        return _extract_pdf(content)

    if ext in ("doc", "docx"):
        return _extract_docx(content)

    if ext == "csv":
        return _extract_csv(content)

    if ext == "json":
        return _decode_text(content)

    return _decode_text(content)


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _extract_pdf(content: bytes) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
        return "\n\n".join(pages)
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}")

    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        return "\n\n".join(
            page.extract_text() or "" for page in reader.pages
        )
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return ""


def _extract_docx(content: bytes) -> str:
    try:
        from docx import Document
        doc = Document(io.BytesIO(content))
        return "\n".join(para.text for para in doc.paragraphs if para.text.strip())
    except Exception as e:
        logger.error(f"DOCX extraction failed: {e}")
        return ""


def _extract_csv(content: bytes) -> str:
    try:
        import pandas as pd
        df = pd.read_csv(io.BytesIO(content))
        return df.to_string(index=False)
    except Exception as e:
        logger.error(f"CSV extraction failed: {e}")
        return _decode_text(content)
