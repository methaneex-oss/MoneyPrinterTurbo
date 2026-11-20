"""Lightweight, local motion-design overlays for generated video scenes.

This module intentionally uses only Pillow, NumPy and MoviePy dependencies that
are already part of MoneyPrinterTurbo. It does not call paid APIs or download
models. The animated chapter tag gives each script-matched stock shot a clear,
moving editorial cue instead of leaving the result as a raw clip sequence.
"""

from __future__ import annotations

import re

import numpy as np
from moviepy import CompositeVideoClip, ImageClip
from PIL import Image, ImageDraw, ImageFont


_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]")
MAX_LABEL_LENGTH = 72


def normalize_scene_label(value: str) -> str:
    """Return a short, safe, single-line scene label."""
    if not isinstance(value, str):
        return ""
    value = _CONTROL_CHARS.sub(" ", value)
    value = " ".join(value.split()).strip()
    if len(value) > MAX_LABEL_LENGTH:
        value = value[: MAX_LABEL_LENGTH - 1].rstrip() + "…"
    return value


def first_scene_label_indices(
    source_paths: list[str],
    scene_labels: dict[str, str] | None,
) -> dict[int, str]:
    """Return one label at the first timeline occurrence of each scene query."""
    if not isinstance(scene_labels, dict):
        return {}
    selected: dict[int, str] = {}
    seen_queries: set[str] = set()
    for index, source_path in enumerate(source_paths):
        label = scene_labels.get(source_path)
        if isinstance(label, str) and label and label not in seen_queries:
            selected[index] = label
            seen_queries.add(label)
    return selected


def scene_label_x(
    time_seconds: float,
    card_width: int,
    target_x: int,
    duration: float,
) -> int:
    """Slide a chapter tag in, hold it, then slide it back out."""
    if duration <= 0:
        return -card_width
    entry = min(0.42, duration * 0.38)
    exit_start = max(entry, duration - min(0.32, duration * 0.24))
    exit_end = max(exit_start + 0.001, duration)
    if time_seconds < entry:
        progress = max(0.0, min(1.0, time_seconds / entry))
        eased = 1.0 - (1.0 - progress) ** 3
        return int(round(-card_width + (target_x + card_width) * eased))
    if time_seconds < exit_start:
        return target_x
    progress = max(
        0.0,
        min(1.0, (time_seconds - exit_start) / (exit_end - exit_start)),
    )
    eased = progress * progress * (3.0 - 2.0 * progress)
    return int(round(target_x - (target_x + card_width) * eased))


def _font(font_path: str | None, size: int):
    if font_path:
        try:
            return ImageFont.truetype(font_path, size=size)
        except (OSError, ValueError):
            pass
    return ImageFont.load_default()


def build_scene_label_card(
    label: str,
    scene_index: int,
    video_width: int,
    font_path: str | None = None,
) -> Image.Image:
    """Build a transparent, restrained lower-third card for one scene."""
    label = normalize_scene_label(label)
    if not label:
        raise ValueError("scene label cannot be empty")

    width = max(360, min(max(360, video_width - 80), int(video_width * 0.72)))
    height = 124
    card = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    draw.rounded_rectangle(
        (1, 1, width - 2, height - 2),
        radius=22,
        fill=(8, 13, 26, 218),
        outline=(255, 255, 255, 58),
        width=2,
    )
    draw.rounded_rectangle(
        (1, 1, 12, height - 2),
        radius=6,
        fill=(70, 211, 231, 255),
    )

    small_font = _font(font_path, 17)
    title_font = _font(font_path, 34)
    scene_text = f"SCENE {max(1, int(scene_index)):02d}"
    draw.text((34, 19), scene_text, font=small_font, fill=(104, 222, 235, 255))

    max_text_width = width - 72
    fitted = label
    while fitted and draw.textbbox((0, 0), fitted, font=title_font)[2] > max_text_width:
        fitted = fitted[:-2].rstrip() + "…"
    draw.text((34, 52), fitted or label[:18], font=title_font, fill=(250, 252, 255, 255))
    return card


def add_scene_label(
    clip,
    label: str,
    *,
    scene_index: int,
    font_path: str | None = None,
):
    """Composite a short animated scene label over a MoviePy clip."""
    label = normalize_scene_label(label)
    if not label or not getattr(clip, "duration", None):
        return clip

    width, height = (int(value) for value in clip.size)
    if width < 360 or height < 240:
        return clip

    duration = min(2.25, float(clip.duration))
    if duration < 0.75:
        return clip

    card = build_scene_label_card(
        label, scene_index, width, font_path=font_path
    )
    card_width, card_height = card.size
    target_x = max(24, int(width * 0.045))
    target_y = max(24, int(height * 0.085))
    overlay = ImageClip(np.asarray(card)).with_duration(duration).with_position(
        lambda t: (
            scene_label_x(t, card_width, target_x, duration),
            target_y,
        )
    )
    return CompositeVideoClip(
        [clip, overlay],
        size=(width, height),
    ).with_duration(float(clip.duration))
