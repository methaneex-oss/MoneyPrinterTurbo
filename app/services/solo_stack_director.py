"""Episode-aware acting direction for the recurring Solo Stack host.

The director reads the actual opening narration and topic, then emits a compact,
reproducible scene direction. It deliberately does not cycle through a fixed
animation playlist. New semantic cues can be added without changing the
character's identity or voice.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_WORD = re.compile(r"[^\W_]+", re.UNICODE)

_CUES = {
    "surprised": re.compile(r"\b(surprising|unexpected|shocking|really|actually|suddenly|wow|turns out)\b", re.I),
    "skeptical": re.compile(r"\b(overpriced|expensive|claim|promise|marketing|limited|hidden|but|however|fails?|problem|catch)\b", re.I),
    "thinking": re.compile(r"\b(consider|whether|decide|depends|trade[- ]off|question|compare|evaluate)\b", re.I),
    "celebrate": re.compile(r"\b(saved|faster|works|useful|excellent|success|genuinely|worth it|solved)\b", re.I),
    "concerned": re.compile(r"\b(risk|privacy|security|wrong|missed|inaccurate|danger|warning|caution)\b", re.I),
    "explaining": re.compile(r"\b(how|why|step|process|workflow|first|then|because|means|feature)\b", re.I),
}
_ACTIONS = {
    "surprised": ("react", "surprised", "camera"),
    "skeptical": ("lean", "skeptical", "evidence"),
    "thinking": ("think", "thoughtful", "up"),
    "celebrate": ("celebrate", "pleased", "camera"),
    "concerned": ("warn", "concerned", "evidence"),
    "explaining": ("present", "engaged", "evidence"),
    "curious": ("question", "curious", "camera"),
}
_WARDROBE_CUES = {
    "studio": re.compile(r"\b(studio|creator|youtube|channel|video|recording)\b", re.I),
    "smart": re.compile(r"\b(proposal|client|business|pricing|subscription|freelance|invoice)\b", re.I),
    "creative": re.compile(r"\b(design|creative|image|art|brand|visual)\b", re.I),
}


def _clean(value: Any, limit: int = 5000) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(_CONTROL.sub(" ", value).split())[:limit]


def plan_performance(script: str, subject: str = "") -> dict[str, str | float]:
    """Derive one grounded, repeatable opening performance from episode content."""
    narration = _clean(script)
    topic = _clean(subject, 500)
    context = f"{topic}. {narration[:1800]}"
    scored = []
    for emotion, pattern in _CUES.items():
        matches = list(pattern.finditer(context))
        if matches:
            # Repeated cues are meaningful, but cap their influence so one
            # keyword cannot dominate the entire acting choice.
            scored.append((min(len(matches), 3), matches[-1].start(), emotion))
    if scored:
        emotion = max(scored, key=lambda item: (item[0], item[1], item[2]))[2]
    elif "?" in narration[:220]:
        emotion = "curious"
    else:
        emotion = "explaining"

    action, expression, gaze = _ACTIONS[emotion]
    digest = hashlib.sha256(f"{topic}\0{narration[:600]}".encode("utf-8")).digest()
    # Micro-variation is stable per episode, while the semantic action is
    # determined by the narration. This prevents random, unreviewable acting.
    intensity = round(0.72 + (digest[0] / 255.0) * 0.22, 2)
    wardrobe = "base"
    if _WARDROBE_CUES["smart"].search(topic):
        wardrobe = "smart"
    elif _WARDROBE_CUES["creative"].search(topic):
        wardrobe = "creative"
    elif _WARDROBE_CUES["studio"].search(topic) and digest[1] > 190:
        wardrobe = "studio"

    return {
        "emotion": emotion,
        "action": action,
        "expression": expression,
        "gaze": gaze,
        "intensity": intensity,
        "wardrobe": wardrobe,
        "seed": digest[2],
    }
