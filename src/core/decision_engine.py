from src.core.geometric_aligner import find_aligned_boundary_tokens
from src.core.mystem_case_parser import extract_cases_from_analysis


def decide_case_error(
    expected_cases: set,
    target_token: dict,
    boundary_tokens: list,
    excluded_spans: dict,
    is_negated: bool = False,
) -> dict:
    """
    expected_cases: FrameBank's result for this target's governing
    verb+preposition (may be empty -- unattested combination).
    boundary_tokens: the full Mystem boundary list for the essay.
    excluded_spans: token_reliability.exclusion_reasons_by_span() output.
    is_negated: whether the target's governing verb is negated (from
        argument_extractor_draft.is_negated). Defaults to False so
        existing callers/tests that don't pass it keep working
        unchanged.

    Returns one of:
        {"status": "no_data"}
        {"status": "excluded", "reason": ...}
        {"status": "correct", "matched_cases": {...}}
        {"status": "error", "expected": {...}, "found": {...}}
    """
    if not expected_cases:
        return {"status": "no_data"}

    aligned = find_aligned_boundary_tokens(target_token, boundary_tokens)

    for b in aligned:
        reason = excluded_spans.get((b["start_char"], b["end_char"]))
        if reason:
            return {"status": "excluded", "reason": reason}

    found_cases = set()
    for b in aligned:
        found_cases |= extract_cases_from_analysis(b.get("analysis"))

    accepted_cases = set(expected_cases)
    if is_negated and "acc" in expected_cases:
        accepted_cases.add("gen")

    matched = accepted_cases & found_cases
    if matched:
        return {"status": "correct", "matched_cases": matched, "expected": expected_cases, "found": found_cases}

    return {"status": "error", "expected": expected_cases, "found": found_cases}


def decide_for_targets(targets_with_expected_cases: list, boundary_tokens: list, excluded_spans: dict) -> list:
    """
    targets_with_expected_cases: [{"target": token, "expected_cases": set,
    "is_negated": bool}, ...] -- produced by
    argument_extractor_draft.extract_verb_arguments() + a FrameBank
    lookup step (see build_targets_from_extraction below). "is_negated"
    defaults to False if absent, for backward compatibility with older
    callers built before the extractor existed.

    One decision dict per entry, target included, same order.
    """
    return [
        {
            **decide_case_error(
                t["expected_cases"],
                t["target"],
                boundary_tokens,
                excluded_spans,
                is_negated=t.get("is_negated", False),
            ),
            "target": t["target"],
        }
        for t in targets_with_expected_cases
    ]