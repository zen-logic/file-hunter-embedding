"""ASGI application — embedding endpoints."""

import io
import json
import logging

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
    try:
        image = Image.open(io.BytesIO(body)).convert("RGB")
    except Exception as e:
        return JSONResponse({"error": f"Invalid image: {e}"}, status_code=400)
    try:
        embedding = model.embed_image(image)
    except Exception as e:
        logger.exception("embed_image failed")
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
    try:
        embedding = model.embed_text(text)
    except Exception as e:
        logger.exception("embed_text failed")
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
    content_type = request.headers.get("content-type", "")
    filename = request.headers.get("x-filename", "document")
    body = await request.body()
    if not body:
        return JSONResponse({"error": "Empty request body"}, status_code=400)

    try:
        _ensure_doc_model()
        from file_hunter_embedding import extract, doc_model
        chunks = extract.extract_and_chunk(body, filename)
        if not chunks:
            return JSONResponse({"error": "No text content extracted"}, status_code=400)
        texts = [c["text"] for c in chunks]
        embeddings = doc_model.embed_document_chunks(texts)
        result = []
        for i, chunk in enumerate(chunks):
            result.append({
                "text": chunk["text"],
                "meta": chunk["meta"],
                "embedding": embeddings[i],
            })
        return JSONResponse({"chunks": result})
    except Exception as e:
        logger.exception("embed_document failed")
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
    try:
        _ensure_doc_model()
        from file_hunter_embedding import doc_model
        embedding = doc_model.embed_query(query)
        return JSONResponse({"embedding": embedding})
    except Exception as e:
        logger.exception("search_text failed")
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
