"""Original Solo Stack presenter and reusable visual identity assets.

The character is drawn from vector primitives at render time. This avoids
inconsistent per-scene image generation and requires no external model/API.
"""
from __future__ import annotations

import math
from PIL import Image, ImageDraw


BRAND = {
    "name": "Solo Stack",
    "palette": {
        "ink": "#101827",
        "panel": "#17243A",
        "cyan": "#46D3E7",
        "coral": "#FF8963",
        "cream": "#F6F4EE",
        "muted": "#A8B4C7",
    },
    "character": "Stack",
    "character_description": (
        "An original compact, warm-toned cartoon technology analyst with a "
        "teal jacket, cream shirt, expressive eyebrows and a small cyan stack "
        "emblem. Not based on any existing TV, film or game character."
    ),
}


def _rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def build_presenter_frame(
    time_seconds: float = 0.0,
    size: tuple[int, int] = (480, 560),
    expression: str = "talk",
) -> Image.Image:
    """Render a deterministic transparent presenter frame at the requested time."""
    width, height = (max(160, int(v)) for v in size)
    scale = min(width / 480, height / 560)
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    def p(x, y):
        return (int((width - 480 * scale) / 2 + x * scale),
                int((height - 560 * scale) / 2 + y * scale))
    def ellipse(box, fill, outline=None, stroke=1):
        draw.ellipse((*p(box[0], box[1]), *p(box[2], box[3])),
                     fill=fill, outline=outline, width=max(1, int(stroke * scale)))
    def polygon(points, fill, outline=None):
        draw.polygon([p(x, y) for x, y in points], fill=fill)
        if outline:
            draw.line([p(x, y) for x, y in points + [points[0]]],
                      fill=outline, width=max(1, int(4 * scale)), joint="curve")
    ink = _rgb(BRAND["palette"]["ink"])
    teal = _rgb(BRAND["palette"]["cyan"])
    coral = _rgb(BRAND["palette"]["coral"])
    cream = _rgb(BRAND["palette"]["cream"])
    bob = math.sin(max(0.0, time_seconds) * 4.2) * 3
    # Legs and shoes.
    polygon([(188, 430), (235, 430), (230, 510), (188, 510)], ink)
    polygon([(255, 430), (300, 430), (308, 510), (264, 510)], ink)
    draw.rounded_rectangle((*p(166, 496), *p(235, 530)), radius=int(18*scale), fill=ink)
    draw.rounded_rectangle((*p(258, 496), *p(332, 530)), radius=int(18*scale), fill=ink)
    # Jacket and shirt.
    polygon([(160, 255+bob), (320, 255+bob), (355, 440), (125, 440)], teal, ink)
    polygon([(220, 258+bob), (260, 258+bob), (278, 390), (240, 414), (202, 390)], cream)
    polygon([(216, 260+bob), (264, 260+bob), (240, 310), (216, 260+bob)], coral)
    # Arms, with an animated small gesture.
    gesture = math.sin(max(0.0, time_seconds) * 2.5) * 10
    polygon([(155, 278+bob), (188, 290+bob), (150-gesture, 390), (118-gesture, 380)], teal, ink)
    ellipse((100-gesture, 365, 143-gesture, 408), cream, ink, 4)
    polygon([(310, 280+bob), (340, 295+bob), (360+gesture, 355), (330+gesture, 370)], teal, ink)
    ellipse((338+gesture, 344, 378+gesture, 385), cream, ink, 4)
    # Head, ears, hair and face.
    ellipse((139, 66+bob, 341, 285+bob), cream, ink, 6)
    ellipse((119, 157+bob, 155, 205+bob), cream, ink, 5)
    ellipse((325, 157+bob, 361, 205+bob), cream, ink, 5)
    polygon([(145, 150+bob), (150, 91+bob), (191, 58+bob),
             (275, 55+bob), (329, 105+bob), (328, 144+bob),
             (295, 116+bob), (240, 128+bob), (183, 115+bob)], ink)
    # Eyes and brows vary with expression.
    brow = 4 if expression == "surprised" else 0
    ellipse((184, 158+bob-brow, 210, 190+bob), ink)
    ellipse((267, 158+bob-brow, 293, 190+bob), ink)
    draw.line([p(178, 148+bob-brow), p(214, 143+bob-brow)], fill=ink, width=max(2,int(7*scale)))
    draw.line([p(263, 143+bob-brow), p(299, 148+bob-brow)], fill=ink, width=max(2,int(7*scale)))
    draw.arc((*p(210, 180+bob), *p(270, 235+bob)), 10, 165, fill=ink, width=max(2,int(5*scale)))
    if expression == "surprised":
        ellipse((224, 207+bob, 258, 248+bob), coral, ink, 3)
    else:
        draw.arc((*p(218, 204+bob), *p(264, 244+bob)), 0, 180, fill=coral, width=max(2,int(6*scale)))
    # Distinctive brand badge.
    draw.rounded_rectangle((*p(185, 330+bob), *p(295, 374+bob)),
                           radius=int(12*scale), fill=ink)
    for index in range(3):
        draw.rounded_rectangle((*p(199, 340+bob+index*9), *p(279, 345+bob+index*9)),
                               radius=int(3*scale), fill=teal if index != 1 else coral)
    return image


def add_presenter_overlay(clip, *, expression: str = "talk", corner: str = "right"):
    """Add the branded presenter to a clip using low-cost local frame rendering."""
    import numpy as np
    from moviepy import CompositeVideoClip, VideoClip

    width, height = (int(value) for value in clip.size)
    if width < 360 or height < 360 or float(clip.duration or 0) < 0.6:
        return clip
    target_h = min(int(height * 0.38), 420)
    target_w = int(target_h * 480 / 560)
    x = max(12, width - target_w - int(width * 0.035)) if corner == "right" else int(width * 0.035)
    y = max(12, height - target_h - int(height * 0.035))
    duration = min(float(clip.duration), 12.0)
    def frame(t):
        return np.asarray(build_presenter_frame(t, (target_w, target_h), expression).convert("RGB"))
    overlay = VideoClip(frame, duration=duration).with_position((x, y))
    return CompositeVideoClip([clip, overlay], size=(width, height)).with_duration(float(clip.duration))
