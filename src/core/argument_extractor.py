def parse_feats(feats_str: str) -> dict:
    """
    UDPipe/CoNLL-U FEATS is a '|'-joined Key=Value string, or '_' for none.
    Token dicts from UdpipeAnalyzer store this raw. Callers needing e.g.
    Aspect, Polarity, or Gender must parse it themselves.
    """
    if not feats_str or feats_str == "_":
        return {}
    out = {}
    for part in feats_str.split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k] = v
    return out


def _children(tokens: list[dict], parent_id: str, deprel: str | None = None) -> list[dict]:
    return [t for t in tokens if t["head"] == parent_id and (deprel is None or t["deprel"] == deprel)]


def is_negated(tokens: list[dict], verb_token: dict) -> bool:
    """
    Confirmed representation: a direct advmod child with text 'не'.
    Does NOT check the Polarity feature. Confirmed absent/null on the
    real test sentences.
    """
    return any(
        c["text"].lower() == "не"
        for c in _children(tokens, verb_token["id"], "advmod")
    )


def reconstruct_preposition(tokens: list[dict], argument_token: dict) -> str | None:
    """
    Returns None if the argument is a bare case (e.g. dative "помогает
    другу", no preposition). Confirmed real construction from the
    diagnostic run's verb_plus_dative_no_prep sentence.
    """
    case_children = _children(tokens, argument_token["id"], "case")
    if not case_children:
        return None

    case_token = case_children[0]
    fixed_children = sorted(
        _children(tokens, case_token["id"], "fixed"),
        key=lambda t: int(t["id"]),
    )
    words = [case_token["text"]] + [f["text"] for f in fixed_children]
    return " ".join(words)


def extract_verb_arguments(tokens: list[dict]) -> list[dict]:
    """
    tokens: one sentence's worth of UdpipeAnalyzer.extract_tokens() output.

    Returns a list of dicts, one per argument found:
        {
            "verb_token": dict,
            "argument_token": dict,
            "preposition": str | None,   # FrameBank-format, e.g. "с помощью"
            "is_negated": bool,
        }

    Does not itself do FrameBank lookup or case-checking, that's
    decision_engine.py's job, downstream. This only produces the
    (verb, preposition, argument) tuples decision_engine currently takes.
    """
    results = []
    for token in tokens:
        if token["upos"] != "VERB":
            continue

        arguments = [
            a for a in _children(tokens, token["id"])
            if a["deprel"] in ("obj", "iobj", "obl")
        ]

        for argument in arguments:
            results.append({
                "verb_token": token,
                "argument_token": argument,
                "preposition": reconstruct_preposition(tokens, argument),
                "is_negated": is_negated(tokens, token),
            })

    return results
