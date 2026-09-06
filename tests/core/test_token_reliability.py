from src.core.token_reliability import (
    find_placeholder_spans,
    classify_uncertain_tokens,
    orthographic_error_rate_per_1k,
    exclusion_reasons_by_span,
)


def test_find_placeholder_spans():
    text = "Смотри [URL] и пиши на [EMAIL]!"
    spans = find_placeholder_spans(text)
    assert spans == [(7, 12), (23, 30)]
    assert text[7:12] == "[URL]"
    assert text[23:30] == "[EMAIL]"


def test_find_placeholder_spans_none_present():
    assert find_placeholder_spans("Обычный текст без масок.") == []


#classify_uncertain_tokens: real confirmed cases

def test_placeholder_derived_token_classified_as_sanitizer_placeholder():
    text = "Смотри материалы на [URL] для помощи."
    url_start = text.index("[URL]")
    boundary_tokens = [
        {"text": "URL", "start_char": url_start + 1, "end_char": url_start + 4, "is_uncertain": True, "has_analysis": True},
    ]
    result = classify_uncertain_tokens(text, boundary_tokens)
    assert len(result) == 1
    assert result[0]["exclusion_reason"] == "sanitizer_placeholder"


def test_genuine_typo_classified_as_possible_typo():
    text = "Я люблю пить кофэ по утрам."
    kofe_start = text.index("кофэ")
    boundary_tokens = [
        {"text": "кофэ", "start_char": kofe_start, "end_char": kofe_start + 4, "is_uncertain": True, "has_analysis": True},
    ]
    result = classify_uncertain_tokens(text, boundary_tokens)
    assert len(result) == 1
    assert result[0]["exclusion_reason"] == "possible_typo"


def test_certain_tokens_are_not_included():
    text = "Я люблю кофе."
    boundary_tokens = [
        {"text": "кофе", "start_char": 8, "end_char": 12, "is_uncertain": False, "has_analysis": True},
    ]
    assert classify_uncertain_tokens(text, boundary_tokens) == []


def test_token_adjacent_to_but_not_inside_placeholder_is_not_classified_as_placeholder():
    text = "Слово [URL] рядом."
    word_start = text.index("рядом")
    boundary_tokens = [
        {"text": "рядом", "start_char": word_start, "end_char": word_start + 5, "is_uncertain": True, "has_analysis": True},
    ]
    result = classify_uncertain_tokens(text, boundary_tokens)
    assert result[0]["exclusion_reason"] == "possible_typo"


def test_mixed_essay_2_scenario():
    # Mirrors the real essay_2.txt integration result: one genuine typo
    # ("коффе") and one placeholder-derived uncertain token ("URL").
    text = "Пил коффе и читал материалы на [URL] для помощи."
    koffe_start = text.index("коффе")
    url_start = text.index("[URL]")
    boundary_tokens = [
        {"text": "коффе", "start_char": koffe_start, "end_char": koffe_start + 5, "is_uncertain": True, "has_analysis": True},
        {"text": "URL", "start_char": url_start + 1, "end_char": url_start + 4, "is_uncertain": True, "has_analysis": True},
        {"text": "читал", "start_char": 0, "end_char": 0, "is_uncertain": False, "has_analysis": True},
    ]
    result = classify_uncertain_tokens(text, boundary_tokens)
    reasons = {t["text"]: t["exclusion_reason"] for t in result}
    assert reasons == {"коффе": "possible_typo", "URL": "sanitizer_placeholder"}


#orthographic_error_rate_per_1k

def test_orthographic_error_rate_counts_only_possible_typo():
    boundary_tokens = [
        {"has_analysis": True} for _ in range(10)
    ]  # 10 word-like tokens
    classified = [
        {"exclusion_reason": "possible_typo"},
        {"exclusion_reason": "sanitizer_placeholder"},  # must NOT count
    ]
    rate = orthographic_error_rate_per_1k(boundary_tokens, classified)
    assert rate == 100.0  # 1 typo / 10 words * 1000


def test_orthographic_error_rate_zero_when_no_word_tokens():
    assert orthographic_error_rate_per_1k([], []) == 0.0


def test_orthographic_error_rate_ignores_non_word_boundary_tokens():
    boundary_tokens = [
        {"has_analysis": True},
        {"has_analysis": True},
        {"has_analysis": False},  # whitespace/punctuation, must not count in denominator
    ]
    classified = [{"exclusion_reason": "possible_typo"}]
    rate = orthographic_error_rate_per_1k(boundary_tokens, classified)
    assert rate == 500.0  # 1 typo / 2 word tokens * 1000


#exclusion_reasons_by_span

def test_exclusion_reasons_by_span_lookup():
    classified = [
        {"start_char": 5, "end_char": 9, "exclusion_reason": "possible_typo"},
        {"start_char": 20, "end_char": 23, "exclusion_reason": "sanitizer_placeholder"},
    ]
    lookup = exclusion_reasons_by_span(classified)
    assert lookup == {(5, 9): "possible_typo", (20, 23): "sanitizer_placeholder"}