"""CLI entry point for the embedding service."""

import argparse
import logging
import os

import uvicorn

from file_hunter_embedding import config, model


def main():
    parser = argparse.ArgumentParser(
        description="File Hunter Embedding Service — CLIP image and text embeddings"
    )
    parser.add_argument("--host", default=None, help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=None, help="Port (default: 8002)")
    parser.add_argument("--model", default=None, help="Model path or HuggingFace ID")
    parser.add_argument("--config", default=None, help="Path to config file (default: ./config.json)")
    args = parser.parse_args()

    config.load_config(args.config)

    host = args.host or config.get("host")
    port = args.port or config.get("port")
    model_path = args.model or config.get("model")

    log_level = logging.DEBUG if os.environ.get("FH_DEBUG") else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    logger = logging.getLogger("file_hunter_embedding")
    logger.info("File Hunter Embedding Service starting")
    logger.info("Model: %s", model_path)
    logger.info("HTTP: %s:%d", host, port)

    model.load(model_path, offline=config.get("offline", False))

    from file_hunter_embedding.app import create_app

    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="warning", log_config=None)


if __name__ == "__main__":
    main()
