"""Lightweight, offline ranking of stock-footage candidates for a scene.

The provider's search order remains the fallback. When Pixabay supplies descriptive
tags, candidates are re-ranked by lexical coverage of the scene query; no external
model, API call, or additional dependency is required.
"""
from __future__ import annotations

import re
from typing import Any, Iterable


_STOP_WORDS = {
    "a", "an", "and", "at", "by", "for", "from", "in", "into", "of",
    "on", "or", "the", "to", "with", "near", "over", "under",
}


def _terms(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", str(value or "").casefold())
        if len(token) > 1 and token not in _STOP_WORDS
    }


def _candidate_tags(candidate: Any) -> str:
    source_info = getattr(candidate, "source_info", None)
    if not isinstance(source_info, dict):
        return ""
    tags = source_info.get("tags", "")
    return tags if isinstance(tags, str) else ""


def rank_visual_candidates(scene_query: str, candidates: Iterable[Any]) -> list[Any]:
    """Rank one scene's candidates by descriptive tag overlap, stably.

    Candidates without tags retain provider order. When tags exist, the score is
    query-token coverage (intersection / query token count); stable ordering breaks
    ties so provider relevance remains useful. This is a retrieval heuristic, not
    image understanding, and deliberately makes no semantic claim about pixels.
    """
    items = list(candidates)
    query_terms = _terms(scene_query)
    if not query_terms:
        return items

    scored = []
    has_tagged_candidate = False
    for index, candidate in enumerate(items):
        tags = _candidate_tags(candidate)
        tag_terms = _terms(tags)
        has_tagged_candidate = has_tagged_candidate or bool(tag_terms)
        coverage = len(query_terms & tag_terms) / len(query_terms) if tag_terms else 0.0
        scored.append((coverage, index, candidate))

    if not has_tagged_candidate:
        return items
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [candidate for _score, _index, candidate in scored]
