import sys
sys.path.insert(0, "/home/claude")

from src.core.gender_concord_engine import decide_gender_error, decide_for_concord_pairs


def _controller_tok(text, start, end):
    """Controller: only needs span offsets, gender comes from Mystem alignment."""
    return {"text": text, "start_char": start, "end_char": end}


def _dependent_tok(text, start, end, feats="_"):
    """Dependent: needs span offsets (for the typo-exclusion alignment)
    AND its own UDPipe feats string (gender is read directly from this,
    not from Mystem)."""
    return {"text": text, "start_char": start, "end_char": end, "feats": feats}


def _boundary(text, start, end, gr_readings=None):
    b = {"text": text, "start_char": start, "end_char": end}
    if gr_readings is not None:
        b["analysis"] = [{"gr": gr} for gr in gr_readings]
    return b


def test_no_data_when_controller_has_no_mystem_analysis():
    controller = _controller_tok("хмфг", 0, 4)
    dependent = _dependent_tok("большая", 5, 12, feats="Case=Nom|Degree=Pos|Gender=Fem|Number=Sing")
    boundary_tokens = [
        _boundary("хмфг", 0, 4),  # no analysis key -- unrecognized token
        _boundary("большая", 5, 12),
    ]
    result = decide_gender_error(controller, dependent, boundary_tokens, {})
    assert result == {"status": "no_data"}


def test_excluded_when_controller_is_a_typo_takes_priority_over_no_data():
    controller = _controller_tok("кофэ", 0, 4)
    dependent = _dependent_tok("большая", 5, 12, feats="Case=Nom|Degree=Pos|Gender=Fem|Number=Sing")
    boundary_tokens = [
        _boundary("кофэ", 0, 4),  # empty analysis, real typo shape
        _boundary("большая", 5, 12),
    ]
    excluded_spans = {(0, 4): "possible_typo"}
    result = decide_gender_error(controller, dependent, boundary_tokens, excluded_spans)
    assert result == {"status": "excluded", "reason": "possible_typo"}


def test_excluded_when_dependent_is_a_typo():
    controller = _controller_tok("книга", 0, 5)
    dependent = _dependent_tok("блшая", 6, 11, feats="Case=Nom|Degree=Pos|Gender=Fem|Number=Sing")
    boundary_tokens = [
        _boundary("книга", 0, 5, ["S,жен,неод=им,ед"]),
        _boundary("блшая", 6, 11),  # empty analysis -- real typo shape
    ]
    excluded_spans = {(6, 11): "possible_typo"}
    result = decide_gender_error(controller, dependent, boundary_tokens, excluded_spans)
    assert result == {"status": "excluded", "reason": "possible_typo"}


def test_correct_when_genders_cleanly_match():
    controller = _controller_tok("книга", 0, 5)
    dependent = _dependent_tok("большая", 6, 13, feats="Case=Nom|Degree=Pos|Gender=Fem|Number=Sing")
    boundary_tokens = [
        _boundary("книга", 0, 5, ["S,жен,неод=им,ед"]),
        _boundary("большая", 6, 13),  # dependent's gender no longer read from here
    ]
    result = decide_gender_error(controller, dependent, boundary_tokens, {})
    assert result == {
        "status": "correct", "matched_genders": {"fem"},
        "expected": {"fem"}, "found": {"fem"},
    }


def test_error_when_genders_cleanly_mismatch():
    controller = _controller_tok("окно", 0, 4)
    dependent = _dependent_tok("большая", 5, 12, feats="Case=Nom|Degree=Pos|Gender=Fem|Number=Sing")
    boundary_tokens = [
        _boundary("окно", 0, 4, ["S,сред,неод=(вин,ед|им,ед)"]),
        _boundary("большая", 5, 12),
    ]
    result = decide_gender_error(controller, dependent, boundary_tokens, {})
    assert result == {"status": "error", "expected": {"neut"}, "found": {"fem"}}


def test_genuine_masc_fem_confusion_on_syncretic_adjective_now_detected():
    controller = _controller_tok("книга", 8, 13)  # "Большой книга" -- fem, nominative
    dependent = _dependent_tok("Большой", 0, 7, feats="Case=Nom|Degree=Pos|Gender=Masc|Number=Sing")
    boundary_tokens = [
        _boundary("Большой", 0, 7),
        _boundary("книга", 8, 13, ["S,жен,неод=им,ед"]),
    ]
    result = decide_gender_error(controller, dependent, boundary_tokens, {})
    assert result["status"] == "error"
    assert result["expected"] == {"fem"}
    assert result["found"] == {"masc"}


def test_correct_syncretic_adjective_in_genuine_oblique_context():
    # Same lexeme, real confirmed diagnostic data for the CORRECT
    # oblique usage: "Она не видела большой книги." -- UDPipe correctly
    # read Case=Gen|Gender=Fem when the grammar actually called for it.
    # Confirms this isn't just UDPipe being unable to produce the fem
    # reading at all -- it makes a real, context-appropriate choice.
    controller = _controller_tok("книги", 20, 26)  # genitive, fem
    dependent = _dependent_tok("большой", 12, 19, feats="Case=Gen|Degree=Pos|Gender=Fem|Number=Sing")
    boundary_tokens = [
        _boundary("большой", 12, 19),
        _boundary("книги", 20, 26, ["S,жен,неод=род,ед"]),
    ]
    result = decide_gender_error(controller, dependent, boundary_tokens, {})
    assert result["status"] == "correct"
    assert result["matched_genders"] == {"fem"}


def test_common_gender_noun_excluded_not_compared():
    controller = _controller_tok("сирота", 0, 6)
    dependent = _dependent_tok("большой", 7, 15, feats="Case=Nom|Degree=Pos|Gender=Masc|Number=Sing")
    boundary_tokens = [
        _boundary("сирота", 0, 6, ["S,мж,од=им,ед"]),
        _boundary("большой", 7, 15),
    ]
    result = decide_gender_error(controller, dependent, boundary_tokens, {})
    assert result == {"status": "excluded", "reason": "common_gender_noun"}


def test_present_tense_dependent_with_no_gender_marking_is_no_data_not_error():
    # Regression test for the real confirmed present-tense bug, now
    # sourced from UDPipe's absent Gender feature instead of Mystem's --
    # "Студент читает книгу.": present-tense "читает" genuinely carries
    # no Gender feature at all.
    controller = _controller_tok("студент", 0, 7)
    dependent = _dependent_tok("читает", 8, 14, feats="Aspect=Imp|Mood=Ind|Number=Sing|Person=3|Tense=Pres")
    boundary_tokens = [
        _boundary("студент", 0, 7, ["S,муж,од=им,ед"]),
        _boundary("читает", 8, 14),
    ]
    result = decide_gender_error(controller, dependent, boundary_tokens, {})
    assert result == {"status": "no_data"}


def test_genuine_mismatch_still_caught_when_dependent_has_real_but_wrong_gender():
    # Confirms the no_data fix doesn't weaken real error detection --
    # a genuine mismatch still has a real Gender feature (just wrong),
    # so it's unaffected by the empty-genders check. Real feats from
    # the earlier ungrammatical-concord diagnostic ("Она умён.").
    controller = _controller_tok("она", 0, 3)
    dependent = _dependent_tok("умён", 4, 8, feats="Degree=Pos|Gender=Masc|Number=Sing|Variant=Short")
    boundary_tokens = [
        _boundary("она", 0, 3, ["SPRO,ед,3-л,жен=им"]),
        _boundary("умён", 4, 8),
    ]
    result = decide_gender_error(controller, dependent, boundary_tokens, {})
    assert result["status"] == "error"
    assert result["found"] == {"masc"}


def test_decide_for_concord_pairs_batch_preserves_order_and_attaches_fields():
    pairs = [
        {
            "controller": _controller_tok("книга", 0, 5),
            "dependent": _dependent_tok("большая", 6, 13, feats="Case=Nom|Degree=Pos|Gender=Fem|Number=Sing"),
            "construction": "attributive",
        },
        {
            "controller": _controller_tok("окно", 20, 24),
            "dependent": _dependent_tok("большая", 25, 32, feats="Case=Nom|Degree=Pos|Gender=Fem|Number=Sing"),
            "construction": "attributive",
        },
    ]
    boundary_tokens = [
        _boundary("книга", 0, 5, ["S,жен,неод=им,ед"]),
        _boundary("большая", 6, 13),
        _boundary("окно", 20, 24, ["S,сред,неод=(вин,ед|им,ед)"]),
        _boundary("большая", 25, 32),
    ]
    results = decide_for_concord_pairs(pairs, boundary_tokens, {})
    assert results[0]["status"] == "correct"
    assert results[0]["construction"] == "attributive"
    assert results[0]["controller"]["text"] == "книга"
    assert results[1]["status"] == "error"
    assert results[1]["dependent"]["text"] == "большая"