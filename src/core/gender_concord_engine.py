# Decision phase for H1' (gender concord): compares a controller noun's
# Target gender (Mystem's fixed lexical reading) against a dependent
# token's Boundary gender. Parallel to decision_engine.py's role for H2
# (case), deliberately separate rather than merged -- same reasoning as
# concord_extractor.py being separate from argument_extractor.py.

from src.core.geometric_aligner import find_aligned_boundary_tokens
from src.core.mystem_gender_parser import extract_genders_from_analysis, is_common_gender

# UDPipe's Gender values are capitalized but Mystem's parser uses lowercase (masc/fem/neut).
_UDPIPE_GENDER_MAP = {"Masc": "masc", "Fem": "fem", "Neut": "neut"}


def parse_feats(feats_str: str) -> dict:
    """
    Local copy of the same utility already in argument_extractor.py and
    concord_extractor.py -- duplicated rather than imported, same
    reasoning as concord_extractor.py's own copy: keeps this file from
    depending on the extractor layer for a trivial utility.
    """
    if not feats_str or feats_str == "_":
        return {}
    out = {}
    for part in feats_str.split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k] = v
    return out


def _dependent_gender_from_udpipe(dependent_token: dict) -> set:
    """
    Reads Gender directly off the dependent's own UDPipe feats --
    already disambiguated in context, already paired with the actual
    case used, no reconstruction needed (see module docstring for why
    this is now trusted). Returns an empty set for forms that
    genuinely carry no Gender feature (present/future tense verbs,
    plural forms) -- NOT an error signal, a real structural fact.
    """
    feats = parse_feats(dependent_token.get("feats", "_"))
    gender = feats.get("Gender")
    if gender in _UDPIPE_GENDER_MAP:
        return {_UDPIPE_GENDER_MAP[gender]}
    return set()


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
    keys which are UDPipe tokens. controller_token's span is used to align to
    Mystem for its Target gender; dependent_token's own feats supply
    its Boundary gender directly, its span used only for the exclusion
    check.
    boundary_tokens: the full Mystem boundary list for the essay.
    excluded_spans: token_reliability.exclusion_reasons_by_span() output.

    Returns one of:
        {"status": "no_data"}          # controller's OR dependent's
                                        # gender undetermined
        {"status": "excluded", "reason": ...}
        {"status": "correct", "matched_genders": {...}, "expected": {...}, "found": {...}}
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

    dependent_aligned = find_aligned_boundary_tokens(dependent_token, boundary_tokens)

    for b in dependent_aligned:
        reason = excluded_spans.get((b["start_char"], b["end_char"]))
        if reason:
            return {"status": "excluded", "reason": reason}

    dependent_genders = _dependent_gender_from_udpipe(dependent_token)

    if not dependent_genders:
        return {"status": "no_data"}

    matched = controller_genders & dependent_genders
    if matched:
        return {"status": "correct", "matched_genders": matched, "expected": controller_genders,
                "found": dependent_genders}

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