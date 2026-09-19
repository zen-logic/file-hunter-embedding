"""Document extraction and chunking."""

import logging
import os

logger = logging.getLogger(__name__)

_TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log", ".xml", ".yaml", ".yml",
                    ".ini", ".cfg", ".conf", ".rst", ".htm", ".html", ".eml"}

_CHUNK_SIZE = 2000  # characters per chunk for plain text


def _chunk_plain_text(text: str, filename: str) -> list[dict]:
    """Split plain text into chunks by paragraphs, merging small ones."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return [{"text": text.strip(), "meta": ""}] if text.strip() else []

    chunks = []
    current = ""
    for para in paragraphs:
        if current and len(current) + len(para) + 2 > _CHUNK_SIZE:
            chunks.append({"text": current, "meta": ""})
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para

    if current:
        chunks.append({"text": current, "meta": ""})

    logger.info("Chunked %d paragraphs into %d chunks from %s", len(paragraphs), len(chunks), filename)
    return chunks


def _chunk_with_docling(file_bytes: bytes, filename: str) -> list[dict]:
    """Extract and chunk a document using Docling."""
    from docling.document_converter import DocumentConverter
    from docling.chunking import HybridChunker
    import tempfile

    suffix = os.path.splitext(filename)[1] if filename else ""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        converter = DocumentConverter()
        result = converter.convert(tmp_path)
        doc = result.document

        chunker = HybridChunker(merge_peers=True)
        chunks = []
        for chunk in chunker.chunk(doc):
            text = chunk.text.strip() if hasattr(chunk, "text") else str(chunk).strip()
            if not text:
                continue
            meta = ""
            if hasattr(chunk, "meta") and chunk.meta:
                headings = chunk.meta.headings if hasattr(chunk.meta, "headings") else []
                if headings:
                    meta = " > ".join(headings)
            chunks.append({"text": text, "meta": meta})

        logger.info("Extracted %d chunks from %s", len(chunks), filename)
        return chunks
    finally:
        os.unlink(tmp_path)


def extract_and_chunk(file_bytes: bytes, filename: str) -> list[dict]:
    """Extract text from a document and return structured chunks.

    Plain text formats are chunked directly by paragraph.
    Documents (PDF, DOCX, etc.) go through Docling.
    """
    ext = os.path.splitext(filename)[1].lower() if filename else ""

    if ext in _TEXT_EXTENSIONS:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1")
        return _chunk_plain_text(text, filename)

    return _chunk_with_docling(file_bytes, filename)
