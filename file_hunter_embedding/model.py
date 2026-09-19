"""CLIP model loading and embedding."""

import logging
import os

import torch
import torch.nn.functional as F
from PIL import Image
from transformers import AutoModel, AutoProcessor

logger = logging.getLogger(__name__)

_model = None
_processor = None
_device = None


def _detect_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def load(model_path: str, offline: bool = False):
    global _model, _processor, _device
    if offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
    _device = _detect_device()
    dtype = torch.float16 if _device.type != "cpu" else torch.float32
    logger.info("Loading model: %s on %s", model_path, _device)
    _model = (
        AutoModel.from_pretrained(model_path, dtype=dtype, use_safetensors=True)
        .to(_device)
        .eval()
    )
    _processor = AutoProcessor.from_pretrained(model_path, backend="torchvision")
    logger.info("Model loaded")


def _to_tensor(features) -> torch.Tensor:
    """Extract a tensor from model output — handles both plain tensors
    and BaseModelOutputWithPooling."""
    if isinstance(features, torch.Tensor):
        return features
    if hasattr(features, "pooler_output") and features.pooler_output is not None:
        return features.pooler_output
    if hasattr(features, "last_hidden_state"):
        return features.last_hidden_state[:, 0]
    raise TypeError(f"Unexpected model output type: {type(features)}")


def embed_image(image: Image.Image) -> list[float]:
    inputs = _processor(images=[image], return_tensors="pt", padding=True).to(_device)
    with torch.no_grad():
        features = _to_tensor(_model.get_image_features(**inputs))
        features = F.normalize(features.to(torch.float32), p=2, dim=-1)
    return features.squeeze(0).cpu().tolist()


def embed_text(text: str) -> list[float]:
    inputs = _processor(text=text, return_tensors="pt", padding=True, truncation=True).to(_device)
    with torch.no_grad():
        features = _to_tensor(_model.get_text_features(**inputs))
        features = F.normalize(features.to(torch.float32), p=2, dim=-1)
    return features.squeeze(0).cpu().tolist()
