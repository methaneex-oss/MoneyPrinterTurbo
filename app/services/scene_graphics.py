"""Narration-led, local vector graphics for editorial video scenes.

Graphics are intentionally conservative: charts use only numeric values present
in the scene heading; other scene types use abstract, non-factual visual motifs.
No network calls, paid APIs, downloaded models, or fabricated statistics.
"""
from __future__ import annotations

import math
import re

import numpy as np
from loguru import logger
from moviepy import CompositeVideoClip, ImageClip
from PIL import Image, ImageDraw, ImageFont

from app.services.scene_animation import infer_scene_type, normalize_scene_label

_PANEL = (470, 190)
_ACCENTS = {
    "comparison": (255, 190, 92, 255),
    "timeline": (154, 139, 255, 255),
    "data": (112, 222, 157, 255),
    "explainer": (255, 137, 163, 255),
    "narrative": (70, 211, 231, 255),
}
_NUMBER = re.compile(
    r"(?<![\\w.-])(?P<prefix>[$€£₦])?\\s*(?P<value>\\d+(?:\\.\\d+)?)"
    r"(?P<unit>\\s*(?:%|percent|per cent|million|billion|trillion|thousand|"
    r"years?|months?|days?|hours?|minutes?|seconds?|weeks?|degrees?|kg|km|miles?|"
    r"cm|mm|meters?|metres?|°[CF]|[CF]elsius|[CF]ahrenheit|ms|MB|GB|TB|Hz|"
    r"kHz|MHz|GHz|watts?|kilowatts?))?(?=$|[^\\w])",
    re.IGNORECASE,
)


def _comparable_numeric_values(label: str) -> list[tuple[float, str]]:
    """Return values only when at least two explicit quantities share one unit."""
    matches = list(_NUMBER.finditer(label))
    if len(matches) < 2:
        return []

    def unit_key(match):
        prefix = (match.group("prefix") or "").casefold()
        unit = (match.group("unit") or "").strip().casefold()
        if unit in {"percent", "per cent"}:
            unit = "%"
        return prefix, unit

    if len({unit_key(match) for match in matches}) != 1:
        return []
    return [
        (float(match.group("value")), match.group(0).strip())
        for match in matches
    ]


def _scene_indicator_position(kind: str, time_seconds: float) -> tuple[float, float]:
    """Return a restrained, looping motion path inside the scene's vector panel."""
    phase = (max(0.0, float(time_seconds)) % 2.4) / 2.4
    if kind == "comparison":
        return 74 + 36 * phase, 87
    if kind == "timeline":
        return 30 + 130 * phase, 91
    if kind == "data":
        return 30 + 130 * phase, 120 - 55 * phase
    if kind == "explainer":
        nodes = ((31, 88), (94, 55), (157, 88))
        segment = phase * (len(nodes) - 1)
        index = min(len(nodes) - 2, int(segment))
        progress = segment - index
        start, finish = nodes[index], nodes[index + 1]
        return (
            start[0] + (finish[0] - start[0]) * progress,
            start[1] + (finish[1] - start[1]) * progress,
        )
    angle = phase * 2 * math.pi
    return 94 + 42 * math.cos(angle), 94 + 30 * math.sin(angle)


def _font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except (OSError, ValueError):
        return ImageFont.load_default()


def _draw_motif(draw: ImageDraw.ImageDraw, kind: str, accent, label: str):
    """Draw a data-safe visual grammar; no implied measurements or dates."""
    white = (235, 241, 250, 235)
    muted = (130, 148, 172, 220)
    if kind == "comparison":
        draw.rounded_rectangle((20, 48, 82, 126), 10, fill=(31, 45, 65, 255), outline=accent, width=3)
        draw.rounded_rectangle((104, 48, 166, 126), 10, fill=(31, 45, 65, 255), outline=muted, width=3)
        draw.text((40, 77), "A", font=_font(25), fill=white)
        draw.text((124, 77), "B", font=_font(25), fill=white)
        draw.line((85, 87, 101, 87), fill=accent, width=4)
    elif kind == "timeline":
        years = re.findall(r"\b(?:18|19|20)\d{2}\b", label)[:3]
        positions = (30, 95, 160) if len(years) != 2 else (48, 142)
        draw.line((22, 91, 168, 91), fill=muted, width=4)
        for index, x in enumerate(positions):
            draw.ellipse((x - 9, 82, x + 9, 100), fill=accent if index == 0 else white)
            marker = years[index] if len(years) == len(positions) else f"{index + 1:02d}"
            marker_width = draw.textbbox((0, 0), marker, font=_font(11))[2]
            draw.text((x - marker_width // 2, 111), marker, font=_font(11), fill=muted)
    elif kind == "data":
        comparable_values = _comparable_numeric_values(label)[:4]
        if comparable_values:
            values = [value for value, _ in comparable_values]
            maximum = max(values) or 1.0
            for index, (value, value_label) in enumerate(comparable_values):
                x = 22 + index * 39
                bar_height = max(8, int(76 * value / maximum))
                draw.rounded_rectangle((x, 128 - bar_height, x + 23, 128), 5, fill=accent)
                label_width = draw.textbbox((0, 0), value_label, font=_font(9))[2]
                draw.text((x + 11 - label_width // 2, max(42, 124 - bar_height - 14)),
                          value_label, font=_font(9), fill=white)
        else:
            # No numeric values were supplied: show a neutral data-grid motif.
            for x in (28, 66, 104, 142):
                draw.line((x, 53, x, 130), fill=muted, width=2)
            for y in (62, 96, 130):
                draw.line((20, y, 158, y), fill=muted, width=2)
    elif kind == "explainer":
        centers = ((31, 88), (94, 55), (157, 88))
        draw.line((centers[0], centers[1], centers[2]), fill=muted, width=4)
        for index, (x, y) in enumerate(centers):
            radius = 14 if index == 1 else 11
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=accent if index == 1 else white)
    else:
        draw.arc((28, 43, 160, 145), 205, 335, fill=accent, width=5)
        draw.ellipse((82, 79, 106, 103), outline=white, width=3)
        draw.line((94, 42, 94, 62), fill=muted, width=3)


def build_scene_graphic(label: str) -> Image.Image:
    """Create a transparent editorial panel with a type-specific vector motif."""
    clean = normalize_scene_label(label)
    if not clean:
        raise ValueError("scene label cannot be empty")
    kind = infer_scene_type(clean)
    accent = _ACCENTS[kind]
    image = Image.new("RGBA", _PANEL, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((1, 1, _PANEL[0]-2, _PANEL[1]-2), 20,
                           fill=(7, 13, 25, 222), outline=(255, 255, 255, 48), width=2)
    draw.rounded_rectangle((1, 1, 8, _PANEL[1]-2), 4, fill=accent)
    _draw_motif(draw, kind, accent, clean)
    draw.line((190, 34, 190, 156), fill=(255, 255, 255, 45), width=2)
    draw.text((214, 43), kind.upper(), font=_font(15), fill=accent)
    # The heading is the only textual claim shown in this panel.
    words = clean.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=_font(21))[2] > 228 and current:
            lines.append(current)
            current = word
        else:
            current = candidate
        if len(lines) == 3:
            break
    if current and len(lines) < 3:
        lines.append(current)
    for index, line in enumerate(lines):
        draw.text((214, 76 + index * 27), line, font=_font(21), fill=(246, 248, 252, 255))
    return image


def _add_scene_graphic(clip, label: str):
    """Add a compact, animated vector explainer panel to a rendered clip."""
    clean = normalize_scene_label(label)
    duration = min(3.2, float(getattr(clip, "duration", 0) or 0))
    width, height = (int(value) for value in clip.size)
    if not clean or duration < 0.8 or width < 640 or height < 360:
        return clip
    kind = infer_scene_type(clean)
    panel = build_scene_graphic(clean)
    # Keep the panel inside the frame on both landscape and portrait canvases.
    scale = min(1.0, (width * 0.58) / panel.width, (height * 0.36) / panel.height)
    if scale < 1.0:
        panel = panel.resize((int(panel.width * scale), int(panel.height * scale)), Image.Resampling.LANCZOS)
    panel_clip = ImageClip(np.asarray(panel)).with_duration(duration)
    x = max(18, width - panel.width - int(width * 0.035))
    target_y = max(18, height - panel.height - int(height * 0.055))
    travel = min(28, max(10, int(height * 0.025)))
    panel_clip = panel_clip.with_position(
        lambda t: (x, int(target_y + travel * (1.0 - min(1.0, max(0.0, t / 0.45)))))
    )

    # A small luminous marker moves through the diagram according to its
    # visual grammar, creating in-panel motion beyond the card's entrance.
    accent = _ACCENTS[kind]
    indicator_size = max(12, int(22 * scale))
    indicator_image = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
    indicator_draw = ImageDraw.Draw(indicator_image)
    indicator_draw.ellipse((1, 1, 23, 23), fill=(*accent[:3], 72))
    indicator_draw.ellipse((6, 6, 18, 18), fill=accent)
    indicator_draw.ellipse((10, 10, 14, 14), fill=(255, 255, 255, 245))
    if indicator_size != 24:
        indicator_image = indicator_image.resize(
            (indicator_size, indicator_size), Image.Resampling.LANCZOS
        )
    indicator = ImageClip(np.asarray(indicator_image)).with_duration(duration)
    indicator = indicator.with_position(
        lambda t: (
            x + (_scene_indicator_position(kind, t)[0] * scale) - indicator_size / 2,
            int(target_y + travel * (1.0 - min(1.0, max(0.0, t / 0.45))))
            + (_scene_indicator_position(kind, t)[1] * scale) - indicator_size / 2,
        )
    )
    return CompositeVideoClip(
        [clip, panel_clip, indicator], size=(width, height)
    ).with_duration(float(clip.duration))



def add_scene_graphic(clip, label: str):
    """Fail open: visual enhancement failures must never abort video rendering."""
    try:
        return _add_scene_graphic(clip, label)
    except Exception as exc:
        logger.warning(
            "scene graphic overlay skipped; preserving source clip: "
            f"{type(exc).__name__}: {exc}"
        )
        return clip
