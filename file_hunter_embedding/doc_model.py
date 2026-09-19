"""Nomic text embedding model for document search."""

import logging
import os

import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

logger = logging.getLogger(__name__)

_model = None
_tokenizer = None
_device = None

DEFAULT_MODEL = "nomic-ai/nomic-embed-text-v1"


def _detect_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def load(model_path: str | None = None, offline: bool = False):
    global _model, _tokenizer, _device
    if offline:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
    model_path = model_path or DEFAULT_MODEL
    _device = _detect_device()
    logger.info("Loading document model: %s on %s", model_path, _device)
    _tokenizer = AutoTokenizer.from_pretrained(model_path, model_max_length=8192)
    _model = AutoModel.from_pretrained(model_path, trust_remote_code=True).to(_device).eval()
    logger.info("Document model loaded")


def _mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
        input_mask_expanded.sum(1), min=1e-9
    )


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Caller must add the task prefix."""
    inputs = _tokenizer(
        texts, return_tensors="pt", padding=True, truncation=True, max_length=8192,
    ).to(_device)
    with torch.no_grad():
        output = _model(**inputs)
    embeddings = _mean_pooling(output, inputs["attention_mask"])
    embeddings = F.normalize(embeddings.to(torch.float32), p=2, dim=-1)
    return embeddings.cpu().tolist()


def embed_document_chunks(chunks: list[str]) -> list[list[float]]:
    """Embed document chunks with the search_document prefix."""
    prefixed = [f"search_document: {c}" for c in chunks]
    return embed_texts(prefixed)


def embed_query(query: str) -> list[float]:
    """Embed a search query with the search_query prefix."""
    result = embed_texts([f"search_query: {query}"])
    return result[0]
