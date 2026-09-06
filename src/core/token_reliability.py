import re

PLACEHOLDER_PATTERN = re.compile(r'\[URL\]|\[EMAIL\]')


def find_placeholder_spans(sanitized_text: str) -> list[tuple[int, int]]:
    """(start, end) spans of sanitizer-inserted [URL]/[EMAIL] masks."""
    return [(m.start(), m.end()) for m in PLACEHOLDER_PATTERN.finditer(sanitized_text)]


def _is_within(token: dict, spans: list[tuple[int, int]]) -> bool:
    return any(s <= token["start_char"] and token["end_char"] <= e for s, e in spans)


def classify_uncertain_tokens(sanitized_text: str, boundary_tokens: list[dict]) -> list[dict]:
    """
    Every is_uncertain boundary token, each with an added
    'exclusion_reason': 'sanitizer_placeholder' or 'possible_typo'.
    """
    spans = find_placeholder_spans(sanitized_text)
    classified = []
    for token in boundary_tokens:
        if not token.get("is_uncertain"):
            continue
        reason = "sanitizer_placeholder" if _is_within(token, spans) else "possible_typo"
        classified.append({**token, "exclusion_reason": reason})
    return classified


def orthographic_error_rate_per_1k(boundary_tokens: list[dict], classified_uncertain: list[dict]) -> float:
    """
    Descriptive essay-level stat: possible_typo tokens per 1000 word-like
    boundary tokens (has_analysis True). Excludes placeholders. Not part
    of H1/H2 -- descriptive only, per the Tier 1 decision.
    """
    word_like = [t for t in boundary_tokens if t.get("has_analysis")]
    if not word_like:
        return 0.0
    typo_count = sum(1 for t in classified_uncertain if t["exclusion_reason"] == "possible_typo")
    return (typo_count / len(word_like)) * 1000


def exclusion_reasons_by_span(classified_uncertain: list[dict]) -> dict:
    """
    (start_char, end_char) -> exclusion_reason. For decision_engine.py to
    skip a boundary token when tallying case/aspect errors.
    """
    return {(t["start_char"], t["end_char"]): t["exclusion_reason"] for t in classified_uncertain}