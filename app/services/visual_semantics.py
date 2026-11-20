"""Optional local image-text semantic checks for downloaded video materials.

The feature is opt-in and uses the MIT-licensed TinyCLIP checkpoint from a local
directory. Model files are never downloaded automatically and inspection never
blocks video generation. Similarity is a retrieval signal, not a probability.
"""
from __future__ import annotations

from functools import lru_cache
import math
import os
from typing import Any

from app.config import config


DEFAULT_MODEL_NAME = "TinyCLIP-ViT-8M-16-Text-3M-YFCC15M"


def _checkpoint_directory() -> str:
    value = str(config.app.get("local_visual_semantics_checkpoint", "") or "").strip()
    return os.path.abspath(os.path.expanduser(value)) if value else ""


def is_enabled() -> bool:
    """Require explicit opt-in and a complete local Transformers checkpoint."""
    if not config.app.get("local_visual_semantics_enabled", False):
        return False
    checkpoint_dir = _checkpoint_directory()
    has_weights = checkpoint_dir and any(
        os.path.isfile(os.path.join(checkpoint_dir, filename))
        for filename in ("model.safetensors", "pytorch_model.bin")
    )
    return bool(
        checkpoint_dir
        and os.path.isdir(checkpoint_dir)
        and os.path.isfile(os.path.join(checkpoint_dir, "config.json"))
        and has_weights
    )


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
def _load_model(checkpoint_dir: str, model_name: str):
    """Load only local checkpoint files; local_files_only prevents hub downloads."""
    import torch
    from transformers import CLIPModel, CLIPProcessor

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = CLIPModel.from_pretrained(
        checkpoint_dir,
        local_files_only=True,
    ).to(device)
    processor = CLIPProcessor.from_pretrained(
        checkpoint_dir,
        local_files_only=True,
    )
    model.eval()
    return torch, model, processor, device


def score_video_text(
    video_path: str,
    scene_text: str,
    *,
    sample_count: int = 3,
) -> dict[str, Any] | None:
    """Compare sampled video frames with a scene description using TinyCLIP.

    Returns mean and best-frame cosine similarities. Returns None when disabled;
    model/runtime errors are isolated by the caller so rendering can continue.
    """
    if not is_enabled() or not scene_text or not scene_text.strip():
        return None

    checkpoint_dir = _checkpoint_directory()
    model_name = str(
        config.app.get("local_visual_semantics_model", DEFAULT_MODEL_NAME)
        or DEFAULT_MODEL_NAME
    )
    torch, model, processor, device = _load_model(checkpoint_dir, model_name)

    from moviepy.video.io.VideoFileClip import VideoFileClip
    from PIL import Image

    sample_count = max(1, min(int(sample_count), 5))
    clip = VideoFileClip(video_path, audio=False)
    try:
        duration = float(clip.duration or 0)
        if duration <= 0:
            raise ValueError("video has no positive duration")
        margin = min(0.05, duration / 20)
        timestamps = [
            margin + (duration - 2 * margin) * (index + 1) / (sample_count + 1)
            for index in range(sample_count)
        ]
        images = [
            Image.fromarray(clip.get_frame(timestamp)).convert("RGB")
            for timestamp in timestamps
        ]
    finally:
        clip.close()

    inputs = processor(
        text=[f"A video frame showing {scene_text.strip()}."],
        images=images,
        return_tensors="pt",
        padding=True,
    )
    inputs = {name: value.to(device) for name, value in inputs.items()}
    with torch.inference_mode():
        outputs = model(**inputs)
        image_features = torch.nn.functional.normalize(
            outputs.image_embeds, dim=-1
        )
        text_features = torch.nn.functional.normalize(
            outputs.text_embeds, dim=-1
        )
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
