# Walks a UDPipe-parsed sentence to find gender-concord pairs: a
# controller noun and a dependent token whose Gender feature should
# match it. Parallel to argument_extractor.py's job for H2 (case), but
# for H1' (gender concord).

def parse_feats(feats_str: str) -> dict:
    if not feats_str or feats_str == "_":
        return {}
    out = {}
    for part in feats_str.split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k] = v
    return out


def _by_id(tokens: list[dict], token_id: str) -> dict | None:
    for t in tokens:
        if t["id"] == token_id:
            return t
    return None


def find_concord_pairs(tokens: list[dict]) -> list[dict]:
    """
    tokens: one sentence's worth of UdpipeAnalyzer.extract_tokens() output.

    Returns a list of dicts, one per concord pair found:
        {
            "controller": dict,   # the token whose gender is authoritative
            "dependent": dict,    # the token that should agree with it
            "construction": str,  # "attributive" | "determiner" |
                                   # "predicate_adjective" | "subject_verb"
        }

    Reports structure only. Does not itself compare genders or decide
    correctness. That's gender_concord_engine.py's job downstream.
    """
    results = []

    for token in tokens:
        # Shape A: dependent modifies a NOUN head directly (amod/det)
        if token["deprel"] in ("amod", "det"):
            head = _by_id(tokens, token["head"])
            if head and head["upos"] == "NOUN":
                if token["deprel"] == "det":
                    if token.get("lemma", "").lower() in ("его", "её", "их"):
                        continue
                    if "Gender" not in parse_feats(token.get("feats", "_")):
                        continue
                construction = "attributive" if token["deprel"] == "amod" else "determiner"
                results.append({"controller": head, "dependent": token, "construction": construction})

        # Shape B: token is the syntactic head, controller is its nsubj
        # dependent (predicate adjectives, both short- and long-form;
        # and ordinary subject-verb agreement)
        if token["deprel"] == "nsubj":
            head = _by_id(tokens, token["head"])
            if head and head["upos"] == "ADJ":
                results.append({"controller": token, "dependent": head, "construction": "predicate_adjective"})
            elif head and head["upos"] == "VERB":
                results.append({"controller": token, "dependent": head, "construction": "subject_verb"})

    return results
