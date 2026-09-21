# Bridges argument_extractor.extract_verb_arguments() (produces
# verb+preposition+argument tuples from a UDPipe-parsed sentence) to
# decision_engine.decide_for_targets() (needs {"target", "expected_cases",
# "is_negated"} dicts).

from src.core.argument_extractor import extract_verb_arguments


def build_targets_from_extraction(tokens: list[dict], framebank_adapter) -> list[dict]:
    """
    tokens: one sentence's UdpipeAnalyzer.extract_tokens() output.
    framebank_adapter: a FrameBankAdapter instance (already loaded).

    Returns: [{"target": argument_token, "expected_cases": set,
               "is_negated": bool}, ...] -- ready for
    decision_engine.decide_for_targets().
    """
    results = []
    for arg in extract_verb_arguments(tokens):
        expected_cases = framebank_adapter.expected_cases(
            arg["verb_token"]["lemma"],
            preposition=arg["preposition"],
        )
        results.append({
            "target": arg["argument_token"],
            "expected_cases": expected_cases,
            "is_negated": arg["is_negated"],
            "preposition": arg["preposition"],
        })
    return results