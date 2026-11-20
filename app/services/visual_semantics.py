"""Optional local image-text semantic checks for downloaded video materials.

The feature is opt-in and requires a user-supplied, locally cached MobileCLIP2-S0
checkpoint. It never downloads model weights automatically and never blocks video
generation. Similarity is a retrieval signal, not a calibrated probability.
"""
from __future__ import annotations

from functools import lru_cache
import math
import os
from typing import Any

from loguru import logger

from app.config import config


DEFAULT_MODEL_NAME = "MobileCLIP2-S0"


def is_enabled() -> bool:
    """Return true only when explicitly enabled with an existing checkpoint."""
    if not config.app.get("local_visual_semantics_enabled", False):
        return False
    checkpoint = str(config.app.get("local_visual_semantics_checkpoint", "") or "").strip()
    return bool(checkpoint and os.path.isfile(os.path.expanduser(checkpoint)))


def cosine_similarity(first: list[float], second: list[float]) -> float:
    """Compute cosine similarity for finite, non-empty feature vectors."""
    if not first or len(first) != len(second):
        raise ValueError("feature vectors must be non-empty and have equal lengths")
    if not all(math.isfinite(float(value)) for value in (*first, *second)):
        raise ValueError("feature vectors must contain finite values")
    dot = sum(float(a) * float(b) for a, b in zip(first, second))
    first_norm = math.sqrt(sum(float(value) ** 2 for value in first))
    second_norm = math.sqrt(sum(float(value) ** 2 for value in second))
    if first_norm == 0 or second_norm == 0:
        raise ValueError("feature vectors must have non-zero norms")
    return dot / (first_norm * second_norm)


@lru_cache(maxsize=1)
def _load_model(checkpoint_path: str, model_name: str):
    """Load an explicitly supplied local checkpoint; no model hub lookup occurs."""
    import open_clip
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, _, preprocess = open_clip.create_model_and_transforms(
        model_name,
        pretrained=checkpoint_path,
        device=device,
    )
    model.eval()
    tokenizer = open_clip.get_tokenizer(model_name)
    return torch, model, preprocess, tokenizer, device


def score_video_text(
    video_path: str,
    scene_text: str,
    *,
    sample_count: int = 3,
) -> dict[str, Any] | None:
    """Compare sampled video frames with a scene description using MobileCLIP.

    Returns mean and best-frame cosine similarities. Returns None when disabled;
    model/runtime errors are isolated by the caller so rendering can continue.
    """
    if not is_enabled() or not scene_text or not scene_text.strip():
        return None

    checkpoint = os.path.abspath(
        os.path.expanduser(str(config.app["local_visual_semantics_checkpoint"]))
    )
    model_name = str(
        config.app.get("local_visual_semantics_model", DEFAULT_MODEL_NAME)
        or DEFAULT_MODEL_NAME
    )
    torch, model, preprocess, tokenizer, device = _load_model(checkpoint, model_name)

    from moviepy.video.io.VideoFileClip import VideoFileClip

    sample_count = max(1, min(int(sample_count), 5))
    clip = VideoFileClip(video_path, audio=False)
    try:
        duration = float(clip.duration or 0)
        if duration <= 0:
            raise ValueError("video has no positive duration")
        # Avoid codec-sensitive endpoints and distribute samples across the clip.
        margin = min(0.05, duration / 20)
        timestamps = [
            margin + (duration - 2 * margin) * (index + 1) / (sample_count + 1)
            for index in range(sample_count)
        ]
        from PIL import Image

        images = [
            preprocess(Image.fromarray(clip.get_frame(timestamp)).convert("RGB"))
            for timestamp in timestamps
        ]
    finally:
        clip.close()

    image_batch = torch.stack(images).to(device)
    text_batch = tokenizer([f"A video frame showing {scene_text.strip()}."]).to(device)
    with torch.inference_mode():
        image_features = model.encode_image(image_batch)
        text_features = model.encode_text(text_batch)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        scores = (image_features @ text_features.T).squeeze(-1).detach().cpu().tolist()

    if isinstance(scores, (int, float)):
        scores = [float(scores)]
    scores = [float(score) for score in scores]
    if not scores or not all(math.isfinite(score) for score in scores):
        raise ValueError("vision model returned invalid similarity scores")

    return {
        "model": model_name,
        "sample_count": len(scores),
        "mean_similarity": round(sum(scores) / len(scores), 4),
        "best_frame_similarity": round(max(scores), 4),
        "similarity_type": "cosine",
    }


def clear_model_cache() -> None:
    """Release the cached model reference, useful for tests and constrained runtimes."""
    _load_model.cache_clear()
