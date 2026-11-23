"""Original, reusable Solo Stack character renderer.

Stack's visual identity remains stable while scene-specific acting controls
change expression, gaze, pose, gesture, intensity and occasional wardrobe.
All frames are rendered locally with Pillow; no image API is required.
"""
from __future__ import annotations

import math
from PIL import Image, ImageDraw

BRAND = {
    "name": "Solo Stack",
    "palette": {
        "ink": "#101827", "panel": "#17243A", "cyan": "#46D3E7",
        "coral": "#FF8963", "cream": "#F6F4EE", "muted": "#A8B4C7",
        "skin": "#EFC6A7", "hair": "#202637", "teal_dark": "#168C9B",
    },
    "character": "Stack",
    "character_description": (
        "An original friendly cartoon technology analyst with a distinctive "
        "swept dark hairstyle, expressive eyes, teal jacket and three-bar emblem."
    ),
}

_OUTFITS = {
    "base": ("#46D3E7", "#FF8963", "#F6F4EE"),
    "smart": ("#2E718D", "#FF8963", "#F6F4EE"),
    "creative": ("#8069C8", "#FF8963", "#F6F4EE"),
    "studio": ("#1C8F83", "#F2B84B", "#F6F4EE"),
}
_VALID_ACTIONS = {"talk", "present", "question", "react", "lean", "think", "celebrate", "warn"}
_VALID_EXPRESSIONS = {"talk", "curious", "surprised", "skeptical", "thoughtful", "pleased", "concerned"}
_VALID_GAZES = {"camera", "evidence", "up"}


def _rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def build_presenter_frame(
    time_seconds: float = 0.0,
    size: tuple[int, int] = (480, 560),
    expression: str = "talk",
    *,
    action: str = "talk",
    gaze: str = "camera",
    wardrobe: str = "base",
    intensity: float = 0.85,
) -> Image.Image:
    """Render one transparent, deterministic character frame."""
    width, height = (max(160, int(v)) for v in size)
    scale = min(width / 480, height / 560)
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def p(x, y):
        return (
            int((width - 480 * scale) / 2 + x * scale),
            int((height - 560 * scale) / 2 + y * scale),
        )

    def ellipse(box, fill, outline=None, stroke=1):
        draw.ellipse((*p(box[0], box[1]), *p(box[2], box[3])),
                     fill=fill, outline=outline, width=max(1, int(stroke * scale)))

    def poly(points, fill, outline=None, stroke=5):
        pts = [p(x, y) for x, y in points]
        draw.polygon(pts, fill=fill)
        if outline:
            draw.line(pts + [pts[0]], fill=outline,
                      width=max(1, int(stroke * scale)), joint="curve")

    ink = _rgb(BRAND["palette"]["ink"])
    skin = _rgb(BRAND["palette"]["skin"])
    cream = _rgb(BRAND["palette"]["cream"])
    teal_hex, coral_hex, shirt_hex = _OUTFITS.get(wardrobe, _OUTFITS["base"])
    teal, coral, shirt = _rgb(teal_hex), _rgb(coral_hex), _rgb(shirt_hex)
    t = max(0.0, float(time_seconds))
    power = _clamp(intensity, 0.35, 1.0)
    bob = math.sin(t * 3.8) * 2.8 * power
    sway = math.sin(t * 2.1) * 3.0 * power
    lean = 0.0
    if action == "lean":
        lean = -8 * power * (0.65 + 0.35 * math.sin(t * 2.0))
    elif action == "think":
        lean = 4 * power
    elif action == "celebrate":
        bob += abs(math.sin(t * 5.2)) * 5 * power

    # Legs and shoes: the silhouette remains stable across costumes.
    poly([(185+sway, 425+bob), (231+sway, 425+bob), (226+sway, 510), (185+sway, 510)], ink)
    poly([(253+sway, 425+bob), (299+sway, 425+bob), (307+sway, 510), (264+sway, 510)], ink)
    draw.rounded_rectangle((*p(164+sway, 495), *p(235+sway, 532)),
                           radius=max(5, int(17*scale)), fill=ink)
    draw.rounded_rectangle((*p(258+sway, 495), *p(334+sway, 532)),
                           radius=max(5, int(17*scale)), fill=ink)
    # Jacket with lapels and soft shadow panels.
    body = [(157+lean, 255+bob), (323+lean, 255+bob), (356+lean, 440), (124+lean, 440)]
    poly(body, teal, ink, 7)
    poly([(157+lean, 258+bob), (190+lean, 275+bob), (171+lean, 420), (133+lean, 420)], _rgb("#168C9B"))
    poly([(323+lean, 258+bob), (291+lean, 275+bob), (309+lean, 420), (347+lean, 420)], _rgb("#168C9B"))
    poly([(215+lean, 257+bob), (265+lean, 257+bob), (281+lean, 390), (240+lean, 417), (199+lean, 390)], shirt, ink, 3)
    poly([(212+lean, 258+bob), (268+lean, 258+bob), (240+lean, 313)], coral, ink, 2)
    # Lapels add a tailored, recognizable silhouette.
    poly([(190+lean, 270+bob), (221+lean, 292+bob), (207+lean, 344+bob), (181+lean, 302+bob)], cream, ink, 3)
    poly([(290+lean, 270+bob), (259+lean, 292+bob), (273+lean, 344+bob), (299+lean, 302+bob)], cream, ink, 3)

    # Arms are posed from scene intent rather than one repeated waving loop.
    arm_wave = math.sin(t * 3.0) * 7 * power
    left_hand = (125.0, 385.0)
    right_hand = (355.0, 385.0)
    if action in {"present", "question"}:
        right_hand = (372 + arm_wave, 292 - 12 * power)
    elif action == "react":
        right_hand = (356 + arm_wave, 326 - 18 * power)
        left_hand = (124 - arm_wave, 326 - 18 * power)
    elif action == "think":
        right_hand = (292, 220 + arm_wave)
    elif action == "celebrate":
        left_hand, right_hand = (135, 250 + arm_wave), (345, 250 - arm_wave)
    elif action == "warn":
        right_hand = (365, 278)
    elif action == "lean":
        right_hand = (337, 385)
    # Arms and hands.
    poly([(157+lean, 278+bob), (190+lean, 294+bob), (left_hand[0]+8, left_hand[1]), (left_hand[0]-23, left_hand[1]-7)], teal, ink, 6)
    poly([(310+lean, 278+bob), (340+lean, 294+bob), (right_hand[0]+16, right_hand[1]+10), (right_hand[0]-14, right_hand[1]+23)], teal, ink, 6)
    ellipse((left_hand[0]-19, left_hand[1]-18, left_hand[0]+20, left_hand[1]+20), skin, ink, 4)
    ellipse((right_hand[0]-18, right_hand[1]-18, right_hand[0]+21, right_hand[1]+21), skin, ink, 4)
    if action == "warn":
        draw.line([p(right_hand[0]+1, right_hand[1]-8), p(right_hand[0]+1, right_hand[1]-42)],
                  fill=skin, width=max(3, int(10*scale)))
    if action == "think":
        ellipse((right_hand[0]-7, right_hand[1]-7, right_hand[0]+7, right_hand[1]+7), skin, ink, 2)

    # Head, ears, hair and face.
    head_x = lean * 0.35
    ellipse((139+head_x, 66+bob, 341+head_x, 286+bob), skin, ink, 7)
    ellipse((119+head_x, 157+bob, 155+head_x, 205+bob), skin, ink, 5)
    ellipse((325+head_x, 157+bob, 361+head_x, 205+bob), skin, ink, 5)
    # Distinctive swept hair with a single curl and layered highlights.
    poly([(143+head_x, 157+bob), (146+head_x, 108+bob), (172+head_x, 72+bob),
          (210+head_x, 54+bob), (254+head_x, 58+bob), (279+head_x, 38+bob),
          (300+head_x, 68+bob), (332+head_x, 104+bob), (333+head_x, 151+bob),
          (300+head_x, 122+bob), (270+head_x, 113+bob), (236+head_x, 127+bob),
          (193+head_x, 113+bob), (166+head_x, 132+bob)], ink, ink, 3)
    draw.arc((*p(171+head_x, 67+bob), *p(251+head_x, 125+bob)), 185, 285,
             fill=_rgb("#46516A"), width=max(2, int(5*scale)))

    # Expression and gaze are independently controllable.
    eye_shift = 0
    if gaze == "evidence":
        eye_shift = 5
    elif gaze == "up":
        eye_shift = -4
    brow_left, brow_right = 0, 0
    mouth = expression if expression in _VALID_EXPRESSIONS else "talk"
    if mouth == "surprised":
        brow_left = brow_right = -8
    elif mouth == "skeptical":
        brow_left, brow_right = -7, 5
    elif mouth == "thoughtful":
        brow_left = brow_right = 3
    elif mouth == "concerned":
        brow_left, brow_right = 5, -4
    elif mouth == "pleased":
        brow_left, brow_right = -2, -2
    # Eye whites and irises.
    for cx in (198, 280):
        ellipse((cx-18+head_x, 153+bob, cx+18+head_x, 194+bob), cream, ink, 3)
        ellipse((cx-5+eye_shift+head_x, 166+bob, cx+7+eye_shift+head_x, 183+bob), ink)
        ellipse((cx-2+eye_shift+head_x, 168+bob, cx+2+eye_shift+head_x, 172+bob), cream)
    draw.line([p(174+head_x, 144+bob+brow_left), p(216+head_x, 139+bob+brow_left)],
              fill=ink, width=max(3, int(8*scale)))
    draw.line([p(262+head_x, 139+bob+brow_right), p(304+head_x, 144+bob+brow_right)],
              fill=ink, width=max(3, int(8*scale)))
    # Nose and expressive mouth.
    draw.arc((*p(218+head_x, 184+bob), *p(261+head_x, 224+bob)), 285, 75,
             fill=_rgb("#B77F68"), width=max(2, int(3*scale)))
    if mouth == "surprised":
        ellipse((222+head_x, 213+bob, 258+head_x, 254+bob), coral, ink, 3)
    elif mouth == "concerned":
        draw.arc((*p(215+head_x, 226+bob), *p(266+head_x, 255+bob)), 185, 350,
                 fill=ink, width=max(3, int(5*scale)))
    elif mouth == "pleased":
        draw.arc((*p(210+head_x, 202+bob), *p(270+head_x, 254+bob)), 5, 175,
                 fill=ink, width=max(3, int(6*scale)))
    else:
        draw.arc((*p(211+head_x, 205+bob), *p(269+head_x, 247+bob)), 5, 175,
                 fill=ink, width=max(3, int(5*scale)))
    # Stack emblem is invariant even when a context-specific jacket is used.
    badge_box = (*p(184+lean, 332+bob), *p(296+lean, 377+bob))
    draw.rounded_rectangle(badge_box, radius=max(4, int(12*scale)), fill=ink)
    for index in range(3):
        stripe = (*p(199+lean, 341+bob+index*10), *p(281+lean, 346+bob+index*10))
        draw.rounded_rectangle(stripe, radius=max(2, int(3*scale)),
                               fill=_rgb(BRAND["palette"]["cyan"]) if index != 1 else coral)
    return image


def add_presenter_overlay(
    clip,
    *,
    expression: str = "talk",
    corner: str = "right",
    acting_direction: dict | None = None,
):
    """Composite Stack with episode-specific acting over an opening clip."""
    import numpy as np
    from moviepy import CompositeVideoClip, VideoClip

    direction = acting_direction if isinstance(acting_direction, dict) else {}
    action = direction.get("action", "talk")
    if action not in _VALID_ACTIONS:
        action = "talk"
    expression = direction.get("expression", expression)
    if expression not in _VALID_EXPRESSIONS:
        expression = "talk"
    gaze = direction.get("gaze", "camera")
    if gaze not in _VALID_GAZES:
        gaze = "camera"
    wardrobe = direction.get("wardrobe", "base")
    if wardrobe not in _OUTFITS:
        wardrobe = "base"
    try:
        intensity = _clamp(float(direction.get("intensity", 0.85)), 0.35, 1.0)
    except (TypeError, ValueError):
        intensity = 0.85

    width, height = (int(value) for value in clip.size)
    if width < 360 or height < 360 or float(clip.duration or 0) < 0.6:
        return clip
    target_h = min(int(height * 0.38), 420)
    target_w = int(target_h * 480 / 560)
    x = max(12, width - target_w - int(width * 0.035)) if corner == "right" else int(width * 0.035)
    y = max(12, height - target_h - int(height * 0.035))
    duration = min(float(clip.duration), 12.0)

    def frame(t):
        return np.asarray(build_presenter_frame(
            t, (target_w, target_h), expression, action=action, gaze=gaze,
            wardrobe=wardrobe, intensity=intensity,
        ).convert("RGB"))

    overlay = VideoClip(frame, duration=duration).with_position((x, y))
    return CompositeVideoClip([clip, overlay], size=(width, height)).with_duration(float(clip.duration))
