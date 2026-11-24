"""Solo Stack narration pacing controls for compatible Kokoro-FastAPI servers.

Kokoro-FastAPI's SSML adapter currently maps prosody rate and breaks to its
native rate/pause tokens. It does not provide arbitrary emotional acting or
pitch control, so this module deliberately limits itself to subtle pacing.
"""
from __future__ import annotations

import re
from xml.sax.saxutils import escape

from app.services.solo_stack_director import plan_performance

_RATE_BY_EMOTION = {
    "thinking": 92,
    "concerned": 94,
    "skeptical": 95,
    "surprised": 105,
    "celebrate": 104,
    "explaining": 100,
    "curious": 98,
}


def build_kokoro_performance_ssml(text: str) -> str:
    """Build safe SSML with subtle sentence-level pace changes; voice stays fixed."""
    clean = " ".join(str(text or "").split())
    if not clean:
        return "<speak></speak>"
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", clean) if part.strip()]
    if not sentences:
        sentences = [clean]
    rendered = []
    for sentence in sentences:
        direction = plan_performance(sentence, "")
        emotion = str(direction.get("emotion", "explaining"))
        rate = _RATE_BY_EMOTION.get(emotion, 100)
        rendered.append(f'<prosody rate="{rate}%">{escape(sentence)}</prosody>')
    return "<speak>" + '<break time="180ms"/>'.join(rendered) + "</speak>"
