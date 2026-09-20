import sys
sys.path.insert(0, "/home/claude")

from src.core.gender_concord_engine import decide_gender_error, decide_for_concord_pairs


def _tok(text, start, end):
    return {"text": text, "start_char": start, "end_char": end}


def _boundary(text, start, end, gr_readings=None):
    b = {"text": text, "start_char": start, "end_char": end}
    if gr_readings is not None:
        b["analysis"] = [{"gr": gr} for gr in gr_readings]
    return b


def test_no_data_when_controller_has_no_mystem_analysis():
    controller = _tok("хмфг", 0, 4)
    dependent = _tok("большая", 5, 12)
    boundary_tokens = [
        _boundary("хмфг", 0, 4),  # no analysis key -- unrecognized token
        _boundary("большая", 5, 12, ["A=им,ед,полн,жен"]),
    ]
    result = decide_gender_error(controller, dependent, boundary_tokens, {})
    assert result == {"status": "no_data"}


def test_excluded_when_controller_is_a_typo_takes_priority_over_no_data():
    # Controller boundary token is BOTH excluded (typo) AND would have
    # empty genders
    controller = _tok("кофэ", 0, 4)
    dependent = _tok("большая", 5, 12)
    boundary_tokens = [
        _boundary("кофэ", 0, 4),  # empty analysis, real typo shape
        _boundary("большая", 5, 12, ["A=им,ед,полн,жен"]),
    ]
    excluded_spans = {(0, 4): "possible_typo"}
    result = decide_gender_error(controller, dependent, boundary_tokens, excluded_spans)
    assert result == {"status": "excluded", "reason": "possible_typo"}


def test_excluded_when_dependent_is_a_typo():
    controller = _tok("книга", 0, 5)
    dependent = _tok("блшая", 6, 11)
    boundary_tokens = [
        _boundary("книга", 0, 5, ["S,жен,неод=им,ед"]),
        _boundary("блшая", 6, 11),  # empty analysis -- real typo shape
    ]
    excluded_spans = {(6, 11): "possible_typo"}
    result = decide_gender_error(controller, dependent, boundary_tokens, excluded_spans)
    assert result == {"status": "excluded", "reason": "possible_typo"}


def test_correct_when_genders_cleanly_match():
    controller = _tok("книга", 0, 5)
    dependent = _tok("большая", 6, 13)
    boundary_tokens = [
        _boundary("книга", 0, 5, ["S,жен,неод=им,ед"]),
        _boundary("большая", 6, 13, ["A=им,ед,полн,жен"]),
    ]
    result = decide_gender_error(controller, dependent, boundary_tokens, {})
    assert result == {"status": "correct", "matched_genders": {"fem"}}


def test_error_when_genders_cleanly_mismatch():
    controller = _tok("окно", 0, 4)
    dependent = _tok("большая", 5, 12)
    boundary_tokens = [
        _boundary("окно", 0, 4, ["S,сред,неод=(вин,ед|им,ед)"]),
        _boundary("большая", 5, 12, ["A=им,ед,полн,жен"]),
    ]
    result = decide_gender_error(controller, dependent, boundary_tokens, {})
    assert result == {"status": "error", "expected": {"neut"}, "found": {"fem"}}


def test_correct_via_syncretic_dependent_alternative():
    # Real syncretic form: "большой" alternates masc-nom with
    # fem-oblique (see mystem_gender_parser.py test fixtures). Fem
    # genitive noun context -- matches via the fem branch of the
    # alternation, not the masc one.
    controller = _tok("книги", 0, 5)
    dependent = _tok("большой", 6, 14)
    boundary_tokens = [
        _boundary("книги", 0, 5, ["S,жен,неод=род,ед"]),
        _boundary("большой", 6, 14,
                   ["A=(вин,ед,полн,муж,неод|им,ед,полн,муж|пр,ед,полн,жен|дат,ед,полн,жен|род,ед,полн,жен|твор,ед,полн,жен)"]),
    ]
    result = decide_gender_error(controller, dependent, boundary_tokens, {})
    assert result["status"] == "correct"
    assert result["matched_genders"] == {"fem"}


def test_common_gender_noun_excluded_not_compared():
    controller = _tok("сирота", 0, 6)
    dependent = _tok("большой", 7, 15)
    boundary_tokens = [
        _boundary("сирота", 0, 6, ["S,мж,од=им,ед"]),
        _boundary("большой", 7, 15, ["A=им,ед,полн,муж"]),
    ]
    result = decide_gender_error(controller, dependent, boundary_tokens, {})
    assert result == {"status": "excluded", "reason": "common_gender_noun"}


def test_decide_for_concord_pairs_batch_preserves_order_and_attaches_fields():
    pairs = [
        {
            "controller": _tok("книга", 0, 5),
            "dependent": _tok("большая", 6, 13),
            "construction": "attributive",
        },
        {
            "controller": _tok("окно", 20, 24),
            "dependent": _tok("большая", 25, 32),
            "construction": "attributive",
        },
    ]
    boundary_tokens = [
        _boundary("книга", 0, 5, ["S,жен,неод=им,ед"]),
        _boundary("большая", 6, 13, ["A=им,ед,полн,жен"]),
        _boundary("окно", 20, 24, ["S,сред,неод=(вин,ед|им,ед)"]),
        _boundary("большая", 25, 32, ["A=им,ед,полн,жен"]),
    ]
    results = decide_for_concord_pairs(pairs, boundary_tokens, {})
    assert results[0]["status"] == "correct"
    assert results[0]["construction"] == "attributive"
    assert results[0]["controller"]["text"] == "книга"
    assert results[1]["status"] == "error"
    assert results[1]["dependent"]["text"] == "большая"
