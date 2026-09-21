from src.core.decision_engine import decide_case_error, decide_for_targets


def test_no_data_when_verb_unattested():
    result = decide_case_error(set(), {"text": "x", "start_char": 0, "end_char": 1}, [], {})
    assert result == {"status": "no_data"}


def test_excluded_when_boundary_token_is_a_typo():
    target = {"text": "кофэ", "start_char": 0, "end_char": 4}
    boundary_tokens = [{"text": "кофэ", "start_char": 0, "end_char": 4, "analysis": []}]
    excluded_spans = {(0, 4): "possible_typo"}
    result = decide_case_error({"acc"}, target, boundary_tokens, excluded_spans)
    assert result == {"status": "excluded", "reason": "possible_typo"}


def test_excluded_when_boundary_token_is_a_sanitizer_placeholder():
    target = {"text": "URL", "start_char": 5, "end_char": 8}
    boundary_tokens = [{"text": "URL", "start_char": 5, "end_char": 8, "analysis": []}]
    excluded_spans = {(5, 8): "sanitizer_placeholder"}
    result = decide_case_error({"acc"}, target, boundary_tokens, excluded_spans)
    assert result == {"status": "excluded", "reason": "sanitizer_placeholder"}


def test_correct_when_case_matches():
    # Real gr string: 'книгу'
    target = {"text": "книгу", "start_char": 0, "end_char": 5}
    boundary_tokens = [{
        "text": "книгу", "start_char": 0, "end_char": 5,
        "analysis": [{"lex": "книга", "wt": 1, "gr": "S,жен,неод=вин,ед"}],
    }]
    result = decide_case_error({"acc"}, target, boundary_tokens, {})
    assert result == {
        "status": "correct", "matched_cases": {"acc"},
        "expected": {"acc"}, "found": {"acc"},
    }


def test_correct_via_syncretism_alternative():
    # Real gr string: 'книге' -- dat/loc syncretism. Expected 'dat',
    # Mystem's reading offers {'loc','dat'} -- overlap exists.
    target = {"text": "книге", "start_char": 0, "end_char": 5}
    boundary_tokens = [{
        "text": "книге", "start_char": 0, "end_char": 5,
        "analysis": [{"lex": "книга", "wt": 1, "gr": "S,жен,неод=(пр,ед|дат,ед)"}],
    }]
    result = decide_case_error({"dat"}, target, boundary_tokens, {})
    assert result["status"] == "correct"
    assert result["matched_cases"] == {"dat"}


def test_error_when_case_does_not_match():
    # Real gr string: 'стола' (genitive), but expected dative.
    target = {"text": "стола", "start_char": 0, "end_char": 5}
    boundary_tokens = [{
        "text": "стола", "start_char": 0, "end_char": 5,
        "analysis": [{"lex": "стол", "wt": 1, "gr": "S,муж,неод=род,ед"}],
    }]
    result = decide_case_error({"dat"}, target, boundary_tokens, {})
    assert result == {"status": "error", "expected": {"dat"}, "found": {"gen"}}


def test_error_unions_across_multiple_boundary_tokens_direction_b():
    # Real Direction B case: UDPipe merged "веб-сайт" into one target
    # token, Mystem split it into ['веб', '-', 'сайт']. The case-bearing
    # morphology sits on 'сайт'; must still be found via the union.
    target = {"text": "веб-сайт", "start_char": 0, "end_char": 8}
    boundary_tokens = [
        {"text": "веб", "start_char": 0, "end_char": 3, "analysis": [{"lex": "веб", "wt": 1, "gr": "S,муж,неод=(вин,ед|им,ед)"}]},
        {"text": "-", "start_char": 3, "end_char": 4},
        {"text": "сайт", "start_char": 4, "end_char": 8, "analysis": [{"lex": "сайт", "wt": 1, "gr": "S,муж,неод=вин,ед"}]},
    ]
    result = decide_case_error({"acc"}, target, boundary_tokens, {})
    assert result["status"] == "correct"
    assert result["matched_cases"] == {"acc"}


def test_multi_member_expected_cases_partial_overlap():
    # FrameBank alternation (e.g. "{Sdat / для + Sgen}") gives expected
    # = {'dat','gen'}; Mystem reading only supports 'dat' -- still correct.
    target = {"text": "столу", "start_char": 0, "end_char": 5}
    boundary_tokens = [{
        "text": "столу", "start_char": 0, "end_char": 5,
        "analysis": [{"lex": "стол", "wt": 1, "gr": "S,муж,неод=дат,ед"}],
    }]
    result = decide_case_error({"dat", "gen"}, target, boundary_tokens, {})
    assert result["status"] == "correct"
    assert result["matched_cases"] == {"dat"}


def test_documented_false_positive_wrong_lemma_drugom():
    # Confirmed real limitation (mystem_case_parser.py): 'другом'
    # (intended: 'друг'+instrumental) was analyzed ONLY as
    # 'другой'+prepositional -- no instrumental reading offered at
    # all. This test documents the resulting false-positive, it does
    # NOT assert this is correct/desired behavior.
    target = {"text": "другом", "start_char": 0, "end_char": 6}
    boundary_tokens = [{
        "text": "другом", "start_char": 0, "end_char": 6,
        "analysis": [{"lex": "другой", "wt": 0.7491774038, "gr": "APRO=(пр,ед,муж|пр,ед,сред)"}],
    }]
    result = decide_case_error({"ins"}, target, boundary_tokens, {})
    assert result["status"] == "error"  # false positive: learner was actually correct
    assert result["found"] == {"loc"}


def test_no_data_takes_priority_over_exclusion_check():
    # An unattested verb/preposition combo should short-circuit before
    # even attempting alignment -- no need to walk boundary_tokens.
    result = decide_case_error(set(), {"text": "x", "start_char": 0, "end_char": 1}, "not_a_real_list_but_unused", {})
    assert result == {"status": "no_data"}


def test_decide_for_targets_batch_preserves_order_and_attaches_target():
    targets = [
        {"target": {"text": "стола", "start_char": 0, "end_char": 5}, "expected_cases": {"dat"}},
        {"target": {"text": "столу", "start_char": 6, "end_char": 11}, "expected_cases": {"dat"}},
    ]
    boundary_tokens = [
        {"text": "стола", "start_char": 0, "end_char": 5, "analysis": [{"lex": "стол", "wt": 1, "gr": "S,муж,неод=род,ед"}]},
        {"text": "столу", "start_char": 6, "end_char": 11, "analysis": [{"lex": "стол", "wt": 1, "gr": "S,муж,неод=дат,ед"}]},
    ]
    results = decide_for_targets(targets, boundary_tokens, {})
    assert results[0]["status"] == "error"
    assert results[0]["target"]["text"] == "стола"
    assert results[1]["status"] == "correct"
    assert results[1]["target"]["text"] == "столу"

def test_negated_accusative_expected_but_genitive_found_is_now_correct():
    # "не вижу стола" -- expected_cases from FrameBank is {'acc'} (the
    # verb's citation-form valency), but the argument is genitive under
    # negation. Before the fix this was a false-positive error.
    target = {"text": "стола", "start_char": 0, "end_char": 5}
    boundary_tokens = [{
        "text": "стола", "start_char": 0, "end_char": 5,
        "analysis": [{"lex": "стол", "wt": 1, "gr": "S,муж,неод=род,ед"}],
    }]
    result = decide_case_error({"acc"}, target, boundary_tokens, {}, is_negated=True)
    assert result["status"] == "correct"
    assert result["matched_cases"] == {"gen"}


def test_negation_without_accusative_in_expected_does_not_get_genitive_bonus():
    # Negation is present, but expected_cases doesn't include 'acc' at
    # all (e.g. a dative-governing verb) -- the free-variation rule is
    # specifically about the accusative/genitive direct-object
    # alternation, so it should NOT apply here.
    target = {"text": "стола", "start_char": 0, "end_char": 5}
    boundary_tokens = [{
        "text": "стола", "start_char": 0, "end_char": 5,
        "analysis": [{"lex": "стол", "wt": 1, "gr": "S,муж,неод=род,ед"}],
    }]
    result = decide_case_error({"dat"}, target, boundary_tokens, {}, is_negated=True)
    assert result["status"] == "error"
    assert result["expected"] == {"dat"}


def test_non_negated_accusative_case_error_is_still_flagged_as_error():
    # Without negation, a genitive reading where accusative was expected
    # is still a real error -- confirms the fix doesn't loosen anything
    # for the non-negated (H2 baseline) case.
    target = {"text": "стола", "start_char": 0, "end_char": 5}
    boundary_tokens = [{
        "text": "стола", "start_char": 0, "end_char": 5,
        "analysis": [{"lex": "стол", "wt": 1, "gr": "S,муж,неод=род,ед"}],
    }]
    result = decide_case_error({"acc"}, target, boundary_tokens, {}, is_negated=False)
    assert result["status"] == "error"
    assert result["expected"] == {"acc"}
    assert result["found"] == {"gen"}


def test_excluded_span_takes_priority_over_negation_logic():
    target = {"text": "стола", "start_char": 0, "end_char": 5}
    boundary_tokens = [{
        "text": "стола", "start_char": 0, "end_char": 5,
        "analysis": [{"lex": "стол", "wt": 1, "gr": "S,муж,неод=род,ед"}],
    }]
    excluded_spans = {(0, 5): "possible_typo"}
    result = decide_case_error({"acc"}, target, boundary_tokens, excluded_spans, is_negated=True)
    assert result == {"status": "excluded", "reason": "possible_typo"}