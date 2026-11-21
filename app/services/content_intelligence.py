"""Deterministic editorial checks for short-form video scripts.

This module does not claim to fact-check claims against external sources. It
surfaces measurable script properties and marks factual claims that need source
verification before publication.
"""
from __future__ import annotations

import re

_WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)?", re.UNICODE)
_SENTENCE = re.compile(r"(?<=[.!?。！？])\s+")
_NUMBER_OR_QUANTITY = re.compile(
    r"(?<!\w)(?:[$€£₦]\s*)?\d[\d,]*(?:\.\d+)?\s*(?:%|percent|per cent|million|billion|trillion|thousand|"
    r"years?|months?|days?|hours?|minutes?|degrees?|kg|km|miles?)?\b",
    re.IGNORECASE,
)
_ABSOLUTE_CLAIMS = re.compile(
    r"\b(always|never|only|first|last|largest|smallest|oldest|youngest|fastest|"
    r"slowest|impossible|guaranteed|proven|everyone|nobody|all|none|every)\b",
    re.IGNORECASE,
)
_GENERIC_OPENING = re.compile(
    r"^(welcome to|today we(?:'re| are)? going to|in this video|let'?s talk about)\b",
    re.IGNORECASE,
)


def audit_script(script: str) -> dict:
    """Return a transparent editorial report; never label it as fact-checked."""
    text = str(script or "").strip()
    words = _WORD.findall(text)
    sentences = [part.strip() for part in _SENTENCE.split(text) if part.strip()]
    opening = sentences[0] if sentences else ""
    opening_words = _WORD.findall(opening)
    quantities = list(dict.fromkeys(match.group(0).strip() for match in _NUMBER_OR_QUANTITY.finditer(text)))
    absolutes = list(dict.fromkeys(match.group(0).lower() for match in _ABSOLUTE_CLAIMS.finditer(text)))

    warnings = []
    if not text:
        warnings.append("empty_script")
    if opening and _GENERIC_OPENING.search(opening):
        warnings.append("generic_opening")
    if quantities:
        warnings.append("verify_numeric_claims_against_sources")
    if absolutes:
        warnings.append("review_absolute_or_superlative_claims")
    if len(words) < 35:
        warnings.append("short_script_check_target_duration")
    if len(words) > 220:
        warnings.append("long_script_check_target_duration")

    return {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "estimated_narration_seconds_at_150_wpm": round(len(words) / 2.5, 1),
        "opening_sentence": opening[:240],
        "opening_word_count": len(opening_words),
        "numeric_claims_to_verify": quantities,
        "absolute_claim_terms_to_review": absolutes,
        "fact_check_status": "not_independently_verified",
        "warnings": warnings,
    }
