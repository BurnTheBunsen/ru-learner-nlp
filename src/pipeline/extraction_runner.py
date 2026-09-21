# The actual pipeline orchestration:
# raw essay text -> sanitize -> UDPipe + Mystem -> exclusion classification -> per-sentence
# argument/concord extraction -> FrameBank lookup -> H2 (case) and H1'
# (gender concord) decisions -> tier1/tier2 row structures.

from src.core.text_sanitizer import sanitize_text
from src.core.token_reliability import classify_uncertain_tokens, exclusion_reasons_by_span, orthographic_error_rate_per_1k
from src.core.argument_extractor import extract_verb_arguments
from src.core.concord_extractor import find_concord_pairs
from src.core.decision_engine import decide_for_targets
from src.core.gender_concord_engine import decide_for_concord_pairs
from src.pipeline.build_targets_from_extraction import build_targets_from_extraction


def _serialize_set(s):
    return "|".join(sorted(s)) if s else ""


def _case_row(essay_id, sentence_index, target, decision):
    target_token = decision["target"]
    return {
        "essay_id": essay_id,
        "sentence_index": sentence_index,
        "hypothesis": "H2_case",
        "status": decision["status"],
        "target_text": target_token.get("text"),
        "target_start": target_token.get("start_char"),
        "target_end": target_token.get("end_char"),
        "dependent_text": "",
        "dependent_start": "",
        "dependent_end": "",
        "construction_or_preposition": target.get("preposition") or "(bare)",
        "is_negated": target.get("is_negated", ""),
        "expected": _serialize_set(decision.get("expected") or decision.get("matched_cases")),
        "found": _serialize_set(decision.get("found")),
        "exclusion_reason": decision.get("reason", ""),
    }


def _gender_row(essay_id, sentence_index, decision):
    controller = decision["controller"]
    dependent = decision["dependent"]
    return {
        "essay_id": essay_id,
        "sentence_index": sentence_index,
        "hypothesis": "H1_gender",
        "status": decision["status"],
        "target_text": controller.get("text"),
        "target_start": controller.get("start_char"),
        "target_end": controller.get("end_char"),
        "dependent_text": dependent.get("text"),
        "dependent_start": dependent.get("start_char"),
        "dependent_end": dependent.get("end_char"),
        "construction_or_preposition": decision.get("construction"),
        "is_negated": "",
        "expected": _serialize_set(decision.get("expected") or decision.get("matched_genders")),
        "found": _serialize_set(decision.get("found")),
        "exclusion_reason": decision.get("reason", ""),
    }


def run_extraction_on_essay(
    essay_id: str,
    raw_text: str,
    udpipe_analyzer,
    mystem_analyzer,
    framebank_adapter,
) -> dict:
    """
    Runs the full pipeline on one essay's raw text. Returns:
        {
            "tier1_rows": [dict, ...],
            "tier2_row": {essay_id, num_sentences, E_case_per_1k,
                          E_gender_per_1k, orthographic_error_rate_per_1k},
        }

    No file I/O here -- see write_tier1_csv/write_tier2_csv for that,
    kept separate so this function stays testable without a real
    filesystem or real adapters (pass in fakes/mocks with the same
    method signatures).
    """
    sanitized_text = sanitize_text(raw_text)
    sentences = udpipe_analyzer.segment_sentences(sanitized_text)
    boundary_tokens = mystem_analyzer.analyze_text(sanitized_text)

    classified_uncertain = classify_uncertain_tokens(sanitized_text, boundary_tokens)
    excluded_spans = exclusion_reasons_by_span(classified_uncertain)

    tier1_rows = []

    for sentence_index, sentence in enumerate(sentences):
        tokens = udpipe_analyzer.extract_tokens(sentence["text"], base_offset=sentence["start_char"])

        # H2 (case)
        targets = build_targets_from_extraction(tokens, framebank_adapter)
        case_decisions = decide_for_targets(targets, boundary_tokens, excluded_spans)
        for target, decision in zip(targets, case_decisions):
            tier1_rows.append(_case_row(essay_id, sentence_index, target, decision))

        # H1' (gender concord)
        pairs = find_concord_pairs(tokens)
        gender_decisions = decide_for_concord_pairs(pairs, boundary_tokens, excluded_spans)
        for decision in gender_decisions:
            tier1_rows.append(_gender_row(essay_id, sentence_index, decision))

    case_errors = sum(1 for r in tier1_rows if r["hypothesis"] == "H2_case" and r["status"] == "error")
    gender_errors = sum(1 for r in tier1_rows if r["hypothesis"] == "H1_gender" and r["status"] == "error")
    word_like_count = sum(1 for t in boundary_tokens if t.get("has_analysis"))

    per_1k = lambda count: (count / word_like_count * 1000) if word_like_count else 0.0

    tier2_row = {
        "essay_id": essay_id,
        "num_sentences": len(sentences),
        "E_case_per_1k": per_1k(case_errors),
        "E_gender_per_1k": per_1k(gender_errors),
        "orthographic_error_rate_per_1k": orthographic_error_rate_per_1k(boundary_tokens, classified_uncertain),
    }

    return {"tier1_rows": tier1_rows, "tier2_row": tier2_row}


TIER1_FIELDNAMES = [
    "essay_id", "sentence_index", "hypothesis", "status",
    "target_text", "target_start", "target_end",
    "dependent_text", "dependent_start", "dependent_end",
    "construction_or_preposition", "is_negated",
    "expected", "found", "exclusion_reason",
]

TIER2_FIELDNAMES = [
    "essay_id", "num_sentences", "E_case_per_1k", "E_gender_per_1k",
    "orthographic_error_rate_per_1k",
]


def write_tier1_csv(path: str, all_tier1_rows: list):
    import csv
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TIER1_FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_tier1_rows)


def write_tier2_csv(path: str, all_tier2_rows: list):
    import csv
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TIER2_FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_tier2_rows)
