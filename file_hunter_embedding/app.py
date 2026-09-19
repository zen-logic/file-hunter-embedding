"""ASGI application — embedding endpoints."""

import io
import json
import logging
import time

from PIL import Image
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from file_hunter_embedding import model

logger = logging.getLogger(__name__)

_doc_model_loaded = False


async def embed_image_route(request: Request):
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("image/"):
        return JSONResponse({"error": "Expected image content type"}, status_code=400)
    body = await request.body()
    logger.info("embed/image: %d bytes", len(body))
    try:
        image = Image.open(io.BytesIO(body)).convert("RGB")
    except Exception:
        logger.warning("embed/image: cannot identify image (%d bytes)", len(body))
        return JSONResponse({"error": f"Cannot identify image ({len(body)} bytes)"}, status_code=400)
    try:
        start = time.perf_counter()
        embedding = model.embed_image(image)
        elapsed = time.perf_counter() - start
        logger.info("embed/image: %dx%d embedded in %.2fs", image.width, image.height, elapsed)
    except Exception as e:
        logger.exception("embed/image: failed")
        return JSONResponse({"error": str(e)}, status_code=500)
    return JSONResponse({"embedding": embedding})


async def embed_text_route(request: Request):
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    text = body.get("text", "").strip()
    if not text:
        return JSONResponse({"error": "Missing 'text' field"}, status_code=400)
    logger.info("embed/text: '%s'", text[:100])
    try:
        start = time.perf_counter()
        embedding = model.embed_text(text)
        elapsed = time.perf_counter() - start
        logger.info("embed/text: embedded in %.2fs", elapsed)
    except Exception as e:
        logger.exception("embed/text: failed")
        return JSONResponse({"error": str(e)}, status_code=500)
    return JSONResponse({"embedding": embedding})


def _ensure_doc_model():
    """Lazy-load the document embedding model on first use."""
    global _doc_model_loaded
    if not _doc_model_loaded:
        from file_hunter_embedding import doc_model, config
        doc_model.load(
            config.get("doc_model"),
            offline=config.get("offline", False),
        )
        _doc_model_loaded = True


async def embed_document_route(request: Request):
    """POST /api/embed/document — extract, chunk, and embed a document."""
    filename = request.headers.get("x-filename", "document")
    body = await request.body()
    if not body:
        return JSONResponse({"error": "Empty request body"}, status_code=400)

    logger.info("embed/document: %s (%d bytes)", filename, len(body))
    try:
        _ensure_doc_model()
        from file_hunter_embedding import extract, doc_model

        start = time.perf_counter()
        chunks = extract.extract_and_chunk(body, filename)
        extract_time = time.perf_counter() - start

        if not chunks:
            logger.warning("embed/document: no content extracted from %s", filename)
            return JSONResponse({"error": "No text content extracted"}, status_code=400)

        logger.info("embed/document: %d chunks extracted in %.2fs", len(chunks), extract_time)

        start = time.perf_counter()
        texts = [c["text"] for c in chunks]
        embeddings = doc_model.embed_document_chunks(texts)
        embed_time = time.perf_counter() - start

        logger.info("embed/document: %d chunks embedded in %.2fs", len(chunks), embed_time)

        result = []
        for i, chunk in enumerate(chunks):
            result.append({
                "text": chunk["text"],
                "meta": chunk["meta"],
                "embedding": embeddings[i],
            })
        return JSONResponse({"chunks": result})
    except Exception as e:
        logger.exception("embed/document: failed for %s", filename)
        return JSONResponse({"error": str(e)}, status_code=500)


async def search_text_route(request: Request):
    """POST /api/embed/search — embed a text query for document search."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    query = body.get("query", "").strip()
    if not query:
        return JSONResponse({"error": "Missing 'query' field"}, status_code=400)
    logger.info("embed/search: '%s'", query[:100])
    try:
        _ensure_doc_model()
        from file_hunter_embedding import doc_model
        start = time.perf_counter()
        embedding = doc_model.embed_query(query)
        elapsed = time.perf_counter() - start
        logger.info("embed/search: embedded in %.2fs", elapsed)
        return JSONResponse({"embedding": embedding})
    except Exception as e:
        logger.exception("embed/search: failed")
        return JSONResponse({"error": str(e)}, status_code=500)


def create_app() -> Starlette:
    return Starlette(
        routes=[
            Route("/api/embed/image", embed_image_route, methods=["POST"]),
            Route("/api/embed/text", embed_text_route, methods=["POST"]),
            Route("/api/embed/document", embed_document_route, methods=["POST"]),
            Route("/api/embed/search", search_text_route, methods=["POST"]),
        ],
    )
