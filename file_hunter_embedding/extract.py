"""Document extraction and chunking via Docling."""

import io
import logging

logger = logging.getLogger(__name__)


def extract_and_chunk(file_bytes: bytes, filename: str) -> list[dict]:
    """Extract text from a document and return structured chunks.

    Each chunk is a dict with 'text' and 'meta' (heading/section context).
    """
    from docling.document_converter import DocumentConverter
    from docling.chunking import HybridChunker

    # Write to a temp file — Docling needs a path or file-like
    import tempfile
    import os

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
