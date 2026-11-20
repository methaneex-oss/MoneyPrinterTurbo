"""Narration-aware scene planning for the local video compositor.

The planner uses the script and the actual material-source manifest. It does not
invent facts or call an LLM: it aligns each material query with the most relevant
script paragraph and produces a concise editorial heading for the existing renderer.
"""
from __future__ import annotations

import re
from typing import Any


_CONTROL_CHARS = re.compile(r"[\\x00-\\x1f\\x7f-\\x9f]")
_WORDS = re.compile(r"[^\\W_]+", re.UNICODE)
_SENTENCE_END = re.compile(r"(?<=[.!?。！？])\\s+")
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by",
    "for", "from", "had", "has", "have", "he", "her", "his", "in",
    "into", "is", "it", "its", "of", "on", "or", "our", "she", "that",
    "the", "their", "them", "there", "these", "they", "this", "those",
    "to", "was", "we", "were", "what", "when", "where", "which", "who",
    "will", "with", "you", "your",
}
_MAX_HEADING_LENGTH = 72


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(_CONTROL_CHARS.sub(" ", value).split()).strip()


def _tokens(value: str) -> set[str]:
    return {
        token.casefold()
        for token in _WORDS.findall(value)
        if len(token) > 1 and token.casefold() not in _STOP_WORDS
    }


def split_script_sections(script: str) -> list[str]:
    """Split narration into usable paragraphs, with sentence fallback."""
    cleaned = _clean_text(script)
    if not cleaned:
        return []
    paragraphs = [
        _clean_text(part)
        for part in re.split(r"\\n\\s*\\n", str(script))
        if _clean_text(part)
    ]
    if len(paragraphs) > 1:
        return paragraphs
    sentences = [
        _clean_text(part)
        for part in _SENTENCE_END.split(cleaned)
        if _clean_text(part)
    ]
    return sentences or [cleaned]


def _heading(paragraph: str) -> str:
    sentences = _SENTENCE_END.split(paragraph, maxsplit=1)
    heading = _clean_text(sentences[0] if sentences else paragraph)
    if len(heading) > _MAX_HEADING_LENGTH:
        heading = heading[: _MAX_HEADING_LENGTH - 1].rsplit(" ", 1)[0].rstrip()
        heading = (heading or paragraph[: _MAX_HEADING_LENGTH - 1]) + "…"
    return heading


def _match_paragraph(query: str, paragraphs: list[str], query_index: int, query_count: int) -> str:
    query_tokens = _tokens(query)
    if not paragraphs:
        return _clean_text(query)
    if not query_tokens:
        return paragraphs[min(len(paragraphs) - 1, query_index * len(paragraphs) // max(1, query_count))]

    scored = []
    expected_position = query_index / max(1, query_count - 1)
    for index, paragraph in enumerate(paragraphs):
        paragraph_tokens = _tokens(paragraph)
        coverage = len(query_tokens & paragraph_tokens) / len(query_tokens)
        position = index / max(1, len(paragraphs) - 1)
        # Lexical relevance dominates; chronology only resolves close matches.
        score = coverage + max(0.0, 1.0 - abs(position - expected_position)) * 0.025
        scored.append((score, -index, paragraph))
    best_score, _, best_paragraph = max(scored)
    if best_score <= 0.025:
        fallback_index = min(
            len(paragraphs) - 1,
            query_index * len(paragraphs) // max(1, query_count),
        )
        return paragraphs[fallback_index]
    return best_paragraph


def plan_scene(query: str, narration: str) -> dict[str, str]:
    """Return grounded scene metadata; no factual content is generated."""
    query = _clean_text(query)
    narration = _clean_text(narration)
    heading = _heading(narration) if narration else query
    return {
        "query": query,
        "narration": narration,
        "heading": heading or query,
        "intent": "narrative" if narration else "topic",
    }


def build_scene_labels(
    script: str,
    source_groups: dict[str, str] | None,
) -> dict[str, str]:
    """Map each material path to the heading of its best-matching script section."""
    if not isinstance(source_groups, dict) or not source_groups:
        return {}
    paragraphs = split_script_sections(script)
    queries = list(dict.fromkeys(
        _clean_text(query) for query in source_groups.values() if _clean_text(query)
    ))
    query_positions = {query: index for index, query in enumerate(queries)}
    labels: dict[str, str] = {}
    for source_path, raw_query in source_groups.items():
        query = _clean_text(raw_query)
        if not query:
            continue
        index = query_positions.get(query, 0)
        narration = _match_paragraph(query, paragraphs, index, len(queries))
        scene = plan_scene(query, narration)
        labels[source_path] = scene["heading"]
    return labels
