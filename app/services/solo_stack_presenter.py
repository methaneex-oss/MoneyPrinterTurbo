"""Original, reusable Solo Stack character renderer.

Stack's visual identity remains stable while scene-specific acting controls
change expression, gaze, pose, gesture, intensity and occasional wardrobe.
All frames are rendered locally with Pillow; no image API is required.
"""
from __future__ import annotations

import math
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFilter

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
_VALID_ACTIONS = {"talk", "present", "question", "react", "lean", "think", "celebrate", "warn", "shrug"}
_VALID_EXPRESSIONS = {"talk", "curious", "surprised", "skeptical", "thoughtful", "pleased", "concerned"}
_VALID_GAZES = {"camera", "evidence", "up"}


def _rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _build_presenter_frame_native(
    time_seconds: float = 0.0,
    size: tuple[int, int] = (480, 560),
    expression: str = "talk",
    *,
    action: str = "talk",
    gaze: str = "camera",
    wardrobe: str = "base",
    intensity: float = 0.85,
    mouth_open: float = 0.0,
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
    if action == "present":
        right_hand = (370 + arm_wave, 308 - 10 * power)
    elif action == "question":
        right_hand = (368 + arm_wave, 276 - 16 * power)
    elif action == "shrug":
        left_hand = (118 - arm_wave, 300 - 8 * power)
        right_hand = (362 + arm_wave, 300 - 8 * power)
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
    # Small palm/finger creases make the hands read as hands at phone size.
    # The marks stay inside the palm silhouette and remain understated.
    hand_detail = _rgb("#B77F68")
    for hand_x, hand_y in (left_hand, right_hand):
        for offset in (-7, 0, 7):
            draw.line(
                [p(hand_x + offset, hand_y - 3),
                 p(hand_x + offset + 2, hand_y + 5)],
                fill=hand_detail,
                width=max(1, int(1.5 * scale)),
            )
    if action == "present":
        # Open, slightly fanned fingers read as an invitation to inspect the
        # evidence rather than the pointed emphasis used for a question.
        for offset in (-10, 0, 10):
            finger_path = [
                p(right_hand[0] + offset, right_hand[1] - 10),
                p(right_hand[0] + offset + 1, right_hand[1] - 25),
            ]
            draw.line(
                finger_path, fill=ink, width=max(4, int(8 * scale)),
            )
            draw.line(
                finger_path, fill=skin, width=max(2, int(5 * scale)),
            )
    if action in {"question", "warn"}:
        # Questions use a diagonal emphasis; warnings use a clear vertical
        # stop/attention gesture. Both receive the same clean outer contour.
        if action == "warn":
            finger_path = [
                p(right_hand[0] + 1, right_hand[1] - 10),
                p(right_hand[0] + 1, right_hand[1] - 42),
            ]
        else:
            finger_path = [
                p(right_hand[0] + 4, right_hand[1] - 12),
                p(right_hand[0] + 13, right_hand[1] - 30),
                p(right_hand[0] + 18, right_hand[1] - 35),
            ]
        draw.line(
            finger_path, fill=ink, width=max(5, int(9 * scale)), joint="curve",
        )
        draw.line(
            finger_path, fill=skin, width=max(3, int(6 * scale)), joint="curve",
        )
    if action == "shrug":
        # The mirrored hands and short outward forearms make uncertainty or a
        # trade-off visibly different from a one-handed presentation.
        for hand_x, hand_y in (left_hand, right_hand):
            draw.arc(
                (*p(hand_x - 12, hand_y - 10), *p(hand_x + 12, hand_y + 10)),
                190, 350, fill=ink, width=max(2, int(3 * scale)),
            )
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
    eye_opening = 1.0
    if mouth == "surprised":
        brow_left = brow_right = -8
        eye_opening = 1.18
    elif mouth == "curious":
        brow_left, brow_right = -7, 1
        eye_opening = 1.10
    elif mouth == "skeptical":
        brow_left, brow_right = -7, 5
        eye_opening = 0.82
    elif mouth == "thoughtful":
        brow_left = brow_right = 3
        eye_opening = 0.94
    elif mouth == "concerned":
        brow_left, brow_right = 5, -4
        eye_opening = 0.96
    elif mouth == "pleased":
        brow_left, brow_right = -2, -2
        eye_opening = 0.94
    eye_top = 173.5 - 20.5 * eye_opening
    eye_bottom = 173.5 + 20.5 * eye_opening
    # Expression-specific eye openness makes curiosity and skepticism legible
    # even when the mouth is moving with narration audio.
    for cx in (198, 280):
        ellipse((cx-18+head_x, eye_top+bob, cx+18+head_x, eye_bottom+bob), cream, ink, 3)
        ellipse((cx-5+eye_shift+head_x, 166+bob, cx+7+eye_shift+head_x, 183+bob), ink)
        ellipse((cx-2+eye_shift+head_x, 168+bob, cx+2+eye_shift+head_x, 172+bob), cream)
    draw.line([p(174+head_x, 144+bob+brow_left), p(216+head_x, 139+bob+brow_left)],
              fill=ink, width=max(3, int(8*scale)))
    draw.line([p(262+head_x, 139+bob+brow_right), p(304+head_x, 144+bob+brow_right)],
              fill=ink, width=max(3, int(8*scale)))
    # Natural blinks are eased over the episode timeline. A short triangular
    # envelope gives the eyelids a visible close/open motion instead of a
    # one-frame switch that can look like flicker at 30 fps.
    blink_phase = t % 4.2
    blink_progress = max(0.0, 1.0 - abs(blink_phase - 0.225) / 0.065)
    blink_progress = blink_progress * blink_progress * (3.0 - 2.0 * blink_progress)
    if blink_progress > 0.015:
        lid_drop = (eye_bottom - eye_top) * blink_progress
        for left, right in ((178, 218), (260, 300)):
            lid_y = eye_top + lid_drop
            draw.rectangle(
                (*p(left+head_x, eye_top+bob),
                 *p(right+head_x, lid_y+bob)),
                fill=skin,
            )
            draw.line(
                [p(left+head_x, lid_y+bob), p(right+head_x, lid_y+bob)],
                fill=ink,
                width=max(2, int((3.0 + 1.5 * blink_progress)*scale)),
            )
    # Nose and expressive mouth.
    draw.arc((*p(218+head_x, 184+bob), *p(261+head_x, 224+bob)), 285, 75,
             fill=_rgb("#B77F68"), width=max(2, int(3*scale)))
    opening = _clamp(mouth_open, 0.0, 1.0)
    if opening > 0.12:
        mouth_height = 7 + 21 * opening
        ellipse((224+head_x, 220+bob, 256+head_x, 220+bob+mouth_height), ink)
        if opening > 0.55:
            ellipse((232+head_x, 220+bob+mouth_height*0.62,
                     248+head_x, 220+bob+mouth_height*0.88), coral)
    elif mouth == "surprised":
        ellipse((222+head_x, 213+bob, 258+head_x, 254+bob), coral, ink, 3)
    elif mouth == "concerned":
        draw.arc((*p(215+head_x, 226+bob), *p(266+head_x, 255+bob)), 185, 350,
                 fill=ink, width=max(3, int(5*scale)))
    elif mouth == "curious":
        ellipse((228+head_x, 222+bob, 252+head_x, 244+bob), ink)
    elif mouth == "skeptical":
        draw.arc((*p(215+head_x, 222+bob), *p(267+head_x, 252+bob)), 185, 340,
                 fill=ink, width=max(3, int(5*scale)))
    elif mouth == "thoughtful":
        draw.line([p(225+head_x, 238+bob), p(255+head_x, 238+bob)],
                  fill=ink, width=max(3, int(4*scale)))
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



def build_presenter_frame(
    time_seconds: float = 0.0,
    size: tuple[int, int] = (480, 560),
    expression: str = "talk",
    *,
    action: str = "talk",
    gaze: str = "camera",
    wardrobe: str = "base",
    intensity: float = 0.85,
    mouth_open: float = 0.0,
) -> Image.Image:
    """Render Stack with supersampling, soft studio depth and restrained detail.

    The character is drawn at 2x the requested resolution and downsampled with
    Lanczos. This materially improves curves, facial features and small brand
    details at Shorts-sized overlay dimensions without external assets or APIs.
    The transparent silhouette and public API remain unchanged.
    """
    width, height = (max(1, int(v)) for v in size)
    render_size = (max(160, width * 2), max(160, height * 2))
    frame = _build_presenter_frame_native(
        time_seconds,
        render_size,
        expression,
        action=action,
        gaze=gaze,
        wardrobe=wardrobe,
        intensity=intensity,
        mouth_open=mouth_open,
    )

    # A soft, offset contact shadow separates Stack from busy app footage while
    # retaining alpha transparency for MoviePy compositing.
    alpha = frame.getchannel("A")
    shadow_mask = Image.new("L", frame.size, 0)
    shadow_mask.paste(alpha, (0, max(1, int(height * 0.018))))
    shadow_mask = shadow_mask.filter(
        ImageFilter.GaussianBlur(max(1.0, min(width, height) * 0.018))
    )
    shadow = Image.new("RGBA", frame.size, (5, 12, 24, 0))
    shadow.putalpha(shadow_mask.point(lambda value: int(value * 0.34)))
    frame = Image.alpha_composite(shadow, frame)

    # Fine, low-contrast costume details make the jacket read as tailored
    # fabric rather than a flat polygon. Coordinates use the original 480x560
    # design grid, independent of output resolution.
    draw = ImageDraw.Draw(frame)
    scale = min(render_size[0] / 480, render_size[1] / 560)
    ox = (render_size[0] - 480 * scale) / 2
    oy = (render_size[1] - 560 * scale) / 2

    def point(x: float, y: float) -> tuple[int, int]:
        return int(ox + x * scale), int(oy + y * scale)

    line_width = max(1, int(2.0 * scale))
    seam = (205, 246, 244, 105)
    # Lapel seams and a narrow jacket edge highlight.
    draw.line(
        [point(190, 281), point(202, 330), point(188, 365)],
        fill=seam,
        width=line_width,
        joint="curve",
    )
    draw.line(
        [point(290, 281), point(278, 330), point(292, 365)],
        fill=seam,
        width=line_width,
        joint="curve",
    )
    # Three tiny fasteners give the torso a deliberate, finished construction.
    for y in (390, 408, 426):
        cx, cy = point(310, y)
        radius = max(1, int(2.2 * scale))
        draw.ellipse(
            (cx-radius, cy-radius, cx+radius, cy+radius),
            fill=(246, 244, 238, 190),
        )

    # A restrained hair highlight helps the swept silhouette stay readable
    # against dark footage; it never changes the character's identity.
    draw.arc(
        (*point(170, 64), *point(258, 126)),
        190,
        270,
        fill=(139, 166, 190, 115),
        width=max(1, int(2.5 * scale)),
    )

    # Preserve requested dimensions even for very small callers.
    return frame.resize((width, height), Image.Resampling.LANCZOS)



def _overlay_position_scores(
    frame, overlay_size: tuple[int, int]
) -> dict[tuple[int, int], float]:
    """Score safe presenter zones by sampled visual complexity in the source frame.

    The lower subtitle band is intentionally excluded. A stable candidate order
    makes uniform footage deterministic while visual evidence can move the host
    to a genuinely less obstructive region.
    """
    import numpy as np

    frame = np.asarray(frame)
    if frame.ndim != 3 or frame.shape[2] < 3:
        raise ValueError("presenter placement requires an RGB video frame")
    height, width = frame.shape[:2]
    overlay_w, overlay_h = (int(value) for value in overlay_size)
    if min(width, height, overlay_w, overlay_h) <= 0:
        raise ValueError("presenter placement dimensions must be positive")

    margin_x = max(12, int(width * 0.035))
    min_x = min(margin_x, max(0, width - overlay_w))
    max_x = max(min_x, width - overlay_w - margin_x)
    step_x = max(12, overlay_w // 4)
    x_values = list(range(min_x, max_x + 1, step_x))
    if not x_values or x_values[-1] != max_x:
        x_values.append(max_x)

    # Search the complete upper/middle safe area rather than a fixed corner
    # menu. The subtitle band is excluded from the candidate space entirely.
    min_y = max(12, int(height * 0.045))
    max_y = max(min_y, int(height * 0.66) - overlay_h)
    step_y = max(12, overlay_h // 4)
    y_values = list(range(min_y, max_y + 1, step_y))
    if not y_values or y_values[-1] != max_y:
        y_values.append(max_y)
    scores = {}
    for y in y_values:
        for x in x_values:
            right = min(width, x + overlay_w)
            bottom = min(int(height * 0.66), y + overlay_h)
            top = min(y, max(0, bottom - 1))
            left = min(x, max(0, right - 1))
            patch = frame[top:bottom, left:right, :3]
            if patch.size == 0:
                scores[(x, y)] = float("inf")
                continue
            # Downsample before scoring: this is a placement heuristic, not
            # object recognition, and should add negligible render overhead.
            ys = np.linspace(
                0, patch.shape[0] - 1, min(20, patch.shape[0])
            ).astype(int)
            xs = np.linspace(
                0, patch.shape[1] - 1, min(20, patch.shape[1])
            ).astype(int)
            small = patch[ys][:, xs].astype(np.float32)
            gray = (
                small[..., 0] * 0.299
                + small[..., 1] * 0.587
                + small[..., 2] * 0.114
            )
            texture = float(gray.std())
            edges = float(
                (np.abs(np.diff(gray, axis=0)).mean() if gray.shape[0] > 1 else 0)
                + (np.abs(np.diff(gray, axis=1)).mean() if gray.shape[1] > 1 else 0)
            )
            luminance = float(gray.mean())
            exposure_penalty = (
                max(0.0, 24.0 - luminance)
                + max(0.0, luminance - 232.0)
            )
            scores[(x, y)] = (
                texture * 0.55 + edges * 0.9 + exposure_penalty * 0.25
            )
    return scores


def _choose_overlay_position(
    clip, overlay_size: tuple[int, int]
) -> tuple[int, int]:
    """Choose a low-obstruction zone from several actual clip frames."""
    duration = max(0.0, float(getattr(clip, "duration", 0.0) or 0.0))
    sample_times = sorted({
        min(max(0.0, duration * fraction), max(0.0, duration - 0.04))
        for fraction in (0.18, 0.5, 0.82)
    })
    combined = {}
    for sample_time in sample_times:
        try:
            scores = _overlay_position_scores(clip.get_frame(sample_time), overlay_size)
        except Exception:
            continue
        for position, score in scores.items():
            combined[position] = combined.get(position, 0.0) + score
    if not combined:
        width, height = (int(value) for value in clip.size)
        overlay_w, overlay_h = overlay_size
        return (
            max(12, width - overlay_w - int(width * 0.035)),
            max(12, int(height * 0.045)),
        )
    # The candidate insertion order preserves the familiar upper-right
    # placement only when the sampled composition offers no better alternative.
    return min(
        combined,
        key=lambda position: (
            combined[position], position[1], -position[0]
        ),
    )


def add_presenter_overlay(
    clip,
    *,
    expression: str = "talk",
    corner: str = "auto",
    acting_direction: dict | None = None,
    max_duration: float = 3.5,
    duration_fraction: float = 0.46,
    audio_activity: list[float] | None = None,
    audio_activity_fps: int = 25,
    audio_offset: float = 0.0,
):
    """Composite Stack with scene-specific acting and audio-reactive mouth motion."""
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
    clip_duration = float(clip.duration or 0)
    if width < 360 or height < 360 or clip_duration < 1.5:
        return clip
    try:
        fraction = _clamp(float(duration_fraction), 0.2, 0.8)
        cap = max(0.8, min(float(max_duration), 8.0))
    except (TypeError, ValueError):
        fraction, cap = 0.46, 3.5
    target_h = min(int(height * 0.34), 380)
    target_w = int(target_h * 480 / 560)
    # Placement is chosen from the actual scene frames, not an alternating
    # left/right template. Explicit legacy corners remain supported for callers
    # that intentionally request a fixed side.
    if corner == "auto":
        x, y = _choose_overlay_position(clip, (target_w, target_h))
    else:
        x = (
            max(12, width - target_w - int(width * 0.035))
            if corner == "right" else int(width * 0.035)
        )
        y = max(12, int(height * 0.045))
    # The placement scorer never enters the lower subtitle-safe band.
    duration = min(clip_duration * fraction, cap)

    @lru_cache(maxsize=4)
    def rendered_frame(time_seconds: float) -> Image.Image:
        mouth_open = 0.0
        if audio_activity and audio_activity_fps > 0:
            activity_index = int(
                max(0.0, audio_offset + time_seconds) * audio_activity_fps
            )
            if activity_index < len(audio_activity):
                mouth_open = audio_activity[activity_index]
        animation_time = max(0.0, audio_offset + time_seconds)
        return build_presenter_frame(
            animation_time,
            (target_w, target_h),
            expression,
            action=action,
            gaze=gaze,
            wardrobe=wardrobe,
            intensity=intensity,
            mouth_open=mouth_open,
        )

    def frame(t):
        return np.asarray(rendered_frame(float(t)).convert("RGB"))

    fade_duration = min(0.22, duration * 0.18)

    def mask_frame(t):
        alpha = np.asarray(
            rendered_frame(float(t)).getchannel("A"), dtype=np.float32
        ) / 255.0
        # Fade the host in and out so the character never pops over evidence
        # or disappears on a hard cut. The animation timeline itself remains
        # episode-relative and deterministic.
        def smoothstep(value):
            value = min(1.0, max(0.0, value))
            return value * value * (3.0 - 2.0 * value)

        fade_in = smoothstep(float(t) / fade_duration)
        fade_out = smoothstep((duration - float(t)) / fade_duration)
        return alpha * min(fade_in, fade_out)

    overlay = VideoClip(frame, duration=duration).with_mask(
        VideoClip(mask_frame, is_mask=True, duration=duration)
    ).with_position((x, y))
    return CompositeVideoClip([clip, overlay], size=(width, height)).with_duration(float(clip.duration))
