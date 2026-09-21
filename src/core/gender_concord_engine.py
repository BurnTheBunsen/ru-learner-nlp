# Decision phase for H1' (gender concord): compares a controller noun's
# Target gender (Mystem's fixed lexical reading) against a dependent
# token's Boundary gender (also Mystem, same tool for both sides).
# Parallel to decision_engine.py's role for H2 (case), deliberately
# separate rather than merged with the same reasoning as concord_extractor.py
# being separate from argument_extractor.py.

from src.core.geometric_aligner import find_aligned_boundary_tokens
from src.core.mystem_gender_parser import extract_genders_from_analysis, is_common_gender


def _genders_for_token(target_token: dict, boundary_tokens: list) -> tuple[set, list]:
    aligned = find_aligned_boundary_tokens(target_token, boundary_tokens)
    genders = set()
    for b in aligned:
        genders |= extract_genders_from_analysis(b.get("analysis"))
    return genders, aligned


def decide_gender_error(
    controller_token: dict,
    dependent_token: dict,
    boundary_tokens: list,
    excluded_spans: dict,
) -> dict:
    """
    controller_token / dependent_token: from
    concord_extractor.find_concord_pairs()'s "controller"/"dependent"
    keys -- UDPipe tokens, used here only for their span offsets.
    boundary_tokens: the full Mystem boundary list for the essay.
    excluded_spans: token_reliability.exclusion_reasons_by_span() output.

    Returns one of:
        {"status": "no_data"}          # controller's gender undetermined
        {"status": "excluded", "reason": ...}
        {"status": "correct", "matched_genders": {...}}
        {"status": "error", "expected": {...}, "found": {...}}
    """
    controller_genders, controller_aligned = _genders_for_token(controller_token, boundary_tokens)

    for b in controller_aligned:
        reason = excluded_spans.get((b["start_char"], b["end_char"]))
        if reason:
            return {"status": "excluded", "reason": reason}

    if not controller_genders:
        return {"status": "no_data"}

    if is_common_gender(controller_genders):
        return {"status": "excluded", "reason": "common_gender_noun"}

    dependent_genders, dependent_aligned = _genders_for_token(dependent_token, boundary_tokens)

    for b in dependent_aligned:
        reason = excluded_spans.get((b["start_char"], b["end_char"]))
        if reason:
            return {"status": "excluded", "reason": reason}

    if not dependent_genders:
        # Present-tense verbs ("видит", "читает", "лежит") were
        # being flagged "error" here, not because of a genuine mismatch,
        # But because this code expected the gender marker output for them.
        return {"status": "no_data"}

    matched = controller_genders & dependent_genders
    if matched:
        return {"status": "correct", "matched_genders": matched, "expected": controller_genders, "found": dependent_genders}

    return {"status": "error", "expected": controller_genders, "found": dependent_genders}


def decide_for_concord_pairs(pairs: list, boundary_tokens: list, excluded_spans: dict) -> list:
    """
    pairs: concord_extractor.find_concord_pairs() output --
    [{"controller": token, "dependent": token, "construction": str}, ...].

    One decision dict per pair, controller/dependent/construction
    included, same order.
    """
    return [
        {
            **decide_gender_error(p["controller"], p["dependent"], boundary_tokens, excluded_spans),
            "controller": p["controller"],
            "dependent": p["dependent"],
            "construction": p["construction"],
        }
        for p in pairs
    ]
