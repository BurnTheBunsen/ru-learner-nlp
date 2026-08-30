import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def analyzer():
    with patch("src.adapters.mystem_adapter.Mystem") as mock_mystem_cls:
        mock_instance = MagicMock()
        mock_mystem_cls.return_value = mock_instance
        from src.adapters.mystem_adapter import MystemAnalyzer
        instance = MystemAnalyzer()
        yield instance


# --- Offset computation & the trailing-artifact clip ---

def test_offsets_computed_via_cumulative_position(analyzer):
    analyzer.mystem.analyze.return_value = [
        {"analysis": [{"lex": "я", "wt": 0.99, "gr": "SPRO,ед,1-л=им"}], "text": "Я"},
        {"text": " "},
        {"analysis": [{"lex": "любить", "wt": 1, "gr": "V,несов,пе=непрош,ед,изъяв,1-л"}], "text": "люблю"},
        {"text": "\n"},  # trailing artifact -- input has no newline
    ]

    tokens = analyzer.analyze_text("Я люблю")

    assert tokens[0]["text"] == "Я"
    assert tokens[0]["start_char"] == 0
    assert tokens[0]["end_char"] == 1
    assert tokens[2]["text"] == "люблю"
    assert tokens[2]["start_char"] == 2
    assert tokens[2]["end_char"] == 7


def test_trailing_newline_artifact_is_dropped(analyzer):
    # Observed behaviour: mystem's binary always appends a
    # trailing '\n' fragment beyond the actual input length. It shouldn't
    # appear as a token, and produce an out-of-bounds offset.
    analyzer.mystem.analyze.return_value = [
        {"analysis": [{"lex": "кофе", "wt": 0.99, "gr": "S,неод=..."}], "text": "кофе"},
        {"text": "\n"},
    ]

    tokens = analyzer.analyze_text("кофе")  # note: no trailing newline in the real input

    assert len(tokens) == 1
    assert tokens[0]["text"] == "кофе"
    assert tokens[0]["end_char"] == 4  # == len("кофе"), nothing beyond it


def test_partial_overrun_fragment_is_clipped_defensively(analyzer):
    # Defensive case: even if a fragment only PARTIALLY overruns the
    # input (not observed in practice, but tests were not exhaustive),
    # it must be clipped rather than trusted.
    analyzer.mystem.analyze.return_value = [
        {"analysis": [{"lex": "кофе", "wt": 0.99, "gr": "S,неод=..."}], "text": "кофе.\n"},
    ]

    tokens = analyzer.analyze_text("кофе")

    assert tokens[0]["text"] == "кофе"
    assert tokens[0]["end_char"] == 4


# --- has_analysis / is_uncertain: whitespace, punctuation, foreign, valid words ---

def test_whitespace_fragment_has_no_analysis_and_is_not_uncertain(analyzer):
    analyzer.mystem.analyze.return_value = [{"text": " "}]
    tokens = analyzer.analyze_text(" ")
    assert tokens[0]["has_analysis"] is False
    assert tokens[0]["analysis"] is None
    assert tokens[0]["is_uncertain"] is False


def test_punctuation_fragment_has_no_analysis(analyzer):
    analyzer.mystem.analyze.return_value = [{"text": "."}]
    tokens = analyzer.analyze_text(".")
    assert tokens[0]["has_analysis"] is False
    assert tokens[0]["is_uncertain"] is False


def test_foreign_word_has_empty_analysis_and_is_uncertain(analyzer):
    # Real fixture shape for "IT"
    analyzer.mystem.analyze.return_value = [{"analysis": [], "text": "IT"}]
    tokens = analyzer.analyze_text("IT")
    assert tokens[0]["has_analysis"] is True
    assert tokens[0]["analysis"] == []
    assert tokens[0]["is_uncertain"] is True


def test_valid_word_is_not_uncertain(analyzer):
    # Real fixture shape for "кофе"
    analyzer.mystem.analyze.return_value = [
        {"analysis": [{"lex": "кофе", "wt": 0.9999765932, "gr": "S,неод=..."}], "text": "кофе"}
    ]
    tokens = analyzer.analyze_text("кофе")
    assert tokens[0]["has_analysis"] is True
    assert tokens[0]["is_uncertain"] is False


# --- is_uncertain: the two REAL typo failure modes ---

def test_typo_with_empty_analysis_is_uncertain(analyzer):
    # Real fixture shape for "кофэ"
    # described case: no dictionary match at all.
    analyzer.mystem.analyze.return_value = [{"analysis": [], "text": "кофэ"}]
    tokens = analyzer.analyze_text("кофэ")
    assert tokens[0]["is_uncertain"] is True


def test_typo_with_bastard_guess_is_uncertain(analyzer):
    # Real fixture shape for "коффе" -- a POPULATED analysis list, but
    # every reading is a guessed ('qual': 'bastard') match, not a real
    # dictionary hit. This is the case Findings.docx's "empty brackets"
    # description missed entirely, and the reason is_uncertain cannot
    # simply check "analysis is empty".
    analyzer.mystem.analyze.return_value = [
        {
            "analysis": [{"lex": "кофф", "wt": 0.5605515545, "qual": "bastard", "gr": "S,муж,неод=пр,ед"}],
            "text": "коффе",
        }
    ]
    tokens = analyzer.analyze_text("коффе")
    assert tokens[0]["has_analysis"] is True
    assert tokens[0]["analysis"][0]["wt"] == 0.5605515545
    assert tokens[0]["is_uncertain"] is True


def test_typo_with_high_weight_bastard_guess_is_still_uncertain(analyzer):
    # Real fixture shape for "универзитет" -- wt == 1 despite being a
    # guessed reading. Confirms is_uncertain must key off 'qual', not
    # 'wt': a high weight does NOT mean a confident dictionary match.
    analyzer.mystem.analyze.return_value = [
        {
            "analysis": [{"lex": "универзитет", "wt": 1, "qual": "bastard", "gr": "S,муж,неод=(вин,ед|им,ед)"}],
            "text": "универзитет",
        }
    ]
    tokens = analyzer.analyze_text("универзитет")
    assert tokens[0]["analysis"][0]["wt"] == 1
    assert tokens[0]["is_uncertain"] is True


def test_mixed_readings_uncertain_only_if_all_are_bastard(analyzer):
    # If even one candidate reading is a real dictionary match, the
    # fragment should not be flagged uncertain. Ambiguity between
    # readings is a separate concern from "no real match
    # was found at all".
    analyzer.mystem.analyze.return_value = [
        {
            "analysis": [
                {"lex": "коффе", "wt": 0.3, "qual": "bastard", "gr": "S,..."},
                {"lex": "кофе", "wt": 0.7, "gr": "S,..."},
            ],
            "text": "коффе",
        }
    ]
    tokens = analyzer.analyze_text("коффе")
    assert tokens[0]["is_uncertain"] is False


# --- Real hyphen examples from the diagnostic run, for concrete regression coverage ---

def test_hyphen_word_split_by_mystem_produces_separate_tokens(analyzer):
    # Real fixture: "онлайн-курс" -- Mystem split this one.
    analyzer.mystem.analyze.return_value = [
        {"analysis": [{"lex": "онлайн", "wt": 1, "gr": "ADV="}], "text": "онлайн"},
        {"text": "-"},
        {"analysis": [{"lex": "курс", "wt": 1, "gr": "S,муж,неод=..."}], "text": "курс"},
    ]
    tokens = analyzer.analyze_text("онлайн-курс")
    assert [t["text"] for t in tokens] == ["онлайн", "-", "курс"]
    assert tokens[1]["has_analysis"] is False  # the bare hyphen fragment


def test_hyphen_word_merged_by_mystem_produces_single_token(analyzer):
    # Real fixture: "бизнес-план" -- Mystem merged this one.
    analyzer.mystem.analyze.return_value = [
        {"analysis": [{"lex": "бизнес-план", "wt": 1, "gr": "S,муж,неод=..."}], "text": "бизнес-план"},
    ]
    tokens = analyzer.analyze_text("бизнес-план")
    assert len(tokens) == 1
    assert tokens[0]["text"] == "бизнес-план"
    assert tokens[0]["is_uncertain"] is False