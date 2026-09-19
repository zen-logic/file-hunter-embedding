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


def create_app() -> Starlette:
    return Starlette(
        routes=[
            Route("/api/embed/image", embed_image_route, methods=["POST"]),
            Route("/api/embed/text", embed_text_route, methods=["POST"]),
        ],
    )
