"""Deterministic editorial checks for short-form video scripts.

This module does not claim to fact-check claims against external sources. It
surfaces measurable script properties and marks factual claims that need source
verification before publication.
"""
from __future__ import annotations

import re
from collections import Counter

_WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)?", re.UNICODE)
_SENTENCE = re.compile(r"""(?<=[.!?。！？])["'”’)]*\s+""")
_NUMBER_OR_QUANTITY = re.compile(
    r"(?<!\w)(?:[$€£₦]\s*)?\d[\d,]*(?:\.\d+)?\s*(?:%|percent|per cent|million|billion|trillion|thousand|"
    r"years?|months?|days?|hours?|minutes?|seconds?|weeks?|degrees?|kg|km|miles?|cm|mm|meters?|metres?|"
    r"°[CF]|[CF]elsius|[CF]ahrenheit|ms|MB|GB|TB|Hz|kHz|MHz|GHz|watts?|kilowatts?)?(?=$|[^\w])",
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
    sentence_word_counts = [len(_WORD.findall(part)) for part in sentences]
    sentence_openings = [
        tuple(token.casefold() for token in _WORD.findall(part)[:3])
        for part in sentences
        if _WORD.findall(part)
    ]
    opening_counts = Counter(sentence_openings)
    repeated_openings = sorted(
        " ".join(opening_tokens)
        for opening_tokens, count in opening_counts.items()
        if count > 1
    )
    long_sentence_numbers = [
        index + 1
        for index, count in enumerate(sentence_word_counts)
        if count > 28
    ]
    average_sentence_words = (
        round(sum(sentence_word_counts) / len(sentence_word_counts), 1)
        if sentence_word_counts else 0.0
    )
    quantities = list(dict.fromkeys(match.group(0).strip() for match in _NUMBER_OR_QUANTITY.finditer(text)))
    absolutes = list(dict.fromkeys(match.group(0).lower() for match in _ABSOLUTE_CLAIMS.finditer(text)))

    warnings = []
    if not text:
        warnings.append("empty_script")
    if opening and _GENERIC_OPENING.search(opening):
        warnings.append("generic_opening")
    if opening and len(opening_words) > 25:
        warnings.append("opening_sentence_too_long_for_short_form")
    if long_sentence_numbers:
        warnings.append("long_sentences_check_spoken_cadence")
    if repeated_openings:
        warnings.append("repeated_sentence_openings")
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
        "average_sentence_words": average_sentence_words,
        "sentence_word_counts": sentence_word_counts,
        "long_sentence_numbers": long_sentence_numbers,
        "repeated_sentence_openings": repeated_openings,
        "estimated_narration_seconds_at_150_wpm": round(len(words) / 2.5, 1),
        "opening_sentence": opening[:240],
        "opening_word_count": len(opening_words),
        "numeric_claims_to_verify": quantities,
        "absolute_claim_terms_to_review": absolutes,
        "fact_check_status": "not_independently_verified",
        "warnings": warnings,
    }



_SOLO_STACK_HOOK_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "can", "do", "does", "for", "from",
    "how", "i", "if", "in", "into", "is", "it", "its", "of", "on", "or",
    "our", "the", "their", "this", "to", "vs", "we", "what", "when", "with",
    "you", "your", "review", "comparison", "tool", "tools",
}


def audit_solo_stack_script(script: str, subject: str = "") -> dict:
    """Check Solo Stack's opening structure without pretending to fact-check it.

    This is a deterministic editorial preflight. Topic overlap is a lightweight
    lexical signal, not semantic proof; numeric and factual claims remain
    independently unverified until evidence is reviewed.
    """
    report = audit_script(script)
    opening = str(report.get("opening_sentence") or "").strip()
    opening_tokens = [token.casefold() for token in _WORD.findall(opening)]
    subject_tokens = {
        token.casefold()
        for token in _WORD.findall(str(subject or ""))
        if token.casefold() not in _SOLO_STACK_HOOK_STOPWORDS
    }
    matched_terms = sorted(
        topic_term
        for topic_term in subject_tokens
        if any(
            token == topic_term
            or (
                min(len(token), len(topic_term)) >= 5
                and (token.startswith(topic_term) or topic_term.startswith(token))
            )
            for token in opening_tokens
        )
    )
    is_question = opening.rstrip("\"'”’)]").endswith("?")
    hook_warnings = []
    if not opening:
        hook_warnings.append("missing_opening_hook")
    elif not is_question:
        hook_warnings.append("opening_hook_must_be_a_question")
    if opening and not 5 <= len(opening_tokens) <= 24:
        hook_warnings.append("opening_hook_length_outside_5_to_24_words")
    if opening and _GENERIC_OPENING.search(opening):
        hook_warnings.append("opening_hook_is_generic")
    if subject_tokens and not matched_terms:
        hook_warnings.append("opening_hook_topic_specificity_unconfirmed")

    warnings = list(dict.fromkeys(report["warnings"] + hook_warnings))
    return {
        **report,
        "opening_hook": {
            "text": opening,
            "is_question": is_question,
            "subject_terms": sorted(subject_tokens),
            "matched_subject_terms": matched_terms,
            "topic_specificity_confirmed": bool(matched_terms),
            "structural_warnings": hook_warnings,
        },
        "warnings": warnings,
        "editorial_status": (
            "structural_checks_passed" if not warnings
            else "editorial_review_required"
        ),
        "fact_check_status": "not_independently_verified",
    }
