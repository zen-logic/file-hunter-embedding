"""Text embedding model for document search."""

import logging
import os

logger = logging.getLogger(__name__)

_model = None
_device = None

DEFAULT_MODEL = "nomic-ai/nomic-embed-text-v1"


def load(model_path: str | None = None, offline: bool = False):
    global _model, _device
    if offline:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
    model_path = model_path or DEFAULT_MODEL
    from sentence_transformers import SentenceTransformer
    logger.info("Loading document model: %s", model_path)
    _model = SentenceTransformer(model_path)
    _device = str(_model.device)
    logger.info("Document model loaded on %s", _device)


def embed_document_chunks(chunks: list[str]) -> list[list[float]]:
    """Embed document chunks with the search_document prefix."""
    prefixed = [f"search_document: {c}" for c in chunks]
    embeddings = _model.encode(prefixed, normalize_embeddings=True)
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """Embed a search query with the search_query prefix."""
    embedding = _model.encode([f"search_query: {query}"], normalize_embeddings=True)
    return embedding[0].tolist()
