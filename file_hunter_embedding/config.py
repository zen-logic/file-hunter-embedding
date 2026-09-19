"""Configuration from config.json.

Config format:
{
  "host": "0.0.0.0",
  "port": 8002,
  "model": "facebook/metaclip-h14-fullcc2.5b",
  "doc_model": "nomic-ai/nomic-embed-text-v1"
}
"""

import json
from pathlib import Path

_CONFIG_FILE = Path("config.json")
_config: dict = {}

DEFAULTS = {
    "host": "0.0.0.0",
    "port": 8002,
    "model": "facebook/metaclip-h14-fullcc2.5b",
    "doc_model": "nomic-ai/nomic-embed-text-v1",
}


def load_config(path: str | None = None) -> dict:
    global _config, _CONFIG_FILE
    if path:
        _CONFIG_FILE = Path(path)
    if _CONFIG_FILE.exists():
        _config = json.loads(_CONFIG_FILE.read_text())
    else:
        _config = {}
    return _config


def get(key: str, default=None):
    return _config.get(key, DEFAULTS.get(key, default))
