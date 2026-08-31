import pytest
from src.core.geometric_aligner import find_aligned_boundary_tokens, align_tokens


def _bizness_plan_boundary():
    return [
        {"text": "Мы", "start_char": 0, "end_char": 2},
        {"text": " ", "start_char": 2, "end_char": 3},
        {"text": "написали", "start_char": 3, "end_char": 11},
        {"text": " ", "start_char": 11, "end_char": 12},
        {"text": "бизнес-план", "start_char": 12, "end_char": 23},
        {"text": ".", "start_char": 23, "end_char": 24},
    ]


def test_direction_a_small_target_nested_in_merged_boundary():
    target = {"text": "бизнес", "start_char": 12, "end_char": 18}
    result = find_aligned_boundary_tokens(target, _bizness_plan_boundary())
    assert len(result) == 1 and result[0]["text"] == "бизнес-план"


def test_direction_a_all_split_pieces_map_to_same_merged_token():
    targets = [
        {"text": "бизнес", "start_char": 12, "end_char": 18},
        {"text": "-", "start_char": 18, "end_char": 19},
        {"text": "план", "start_char": 19, "end_char": 23},
    ]
    result = align_tokens(targets, _bizness_plan_boundary())
    for entry in result:
        assert [b["text"] for b in entry["boundary_tokens"]] == ["бизнес-план"]


# Direction B (real example, the one that broke the original one-directional
# rule): "Открой веб-сайт компании." -- UDPipe MERGED "веб-сайт"; Mystem
# SPLIT it into ['веб', '-', 'сайт'].

def _veb_sayt_boundary():
    return [
        {"text": "Открой", "start_char": 0, "end_char": 6},
        {"text": " ", "start_char": 6, "end_char": 7},
        {"text": "веб", "start_char": 7, "end_char": 10},
        {"text": "-", "start_char": 10, "end_char": 11},
        {"text": "сайт", "start_char": 11, "end_char": 15},
        {"text": " ", "start_char": 15, "end_char": 16},
        {"text": "компании", "start_char": 16, "end_char": 24},
        {"text": ".", "start_char": 24, "end_char": 25},
    ]


def test_direction_b_merged_target_finds_all_split_boundary_pieces():
    target = {"text": "веб-сайт", "start_char": 7, "end_char": 15}
    result = find_aligned_boundary_tokens(target, _veb_sayt_boundary())
    assert [b["text"] for b in result] == ["веб", "-", "сайт"]


def test_direction_b_via_align_tokens():
    targets = [{"text": "веб-сайт", "start_char": 7, "end_char": 15}]
    result = align_tokens(targets, _veb_sayt_boundary())
    assert [b["text"] for b in result[0]["boundary_tokens"]] == ["веб", "-", "сайт"]


# Touching (adjacent, non-overlapping) spans must be excluded.

def test_touching_spans_are_excluded():
    target = {"text": "middle", "start_char": 5, "end_char": 10}
    boundary = [
        {"text": "before", "start_char": 0, "end_char": 5},
        {"text": "exact", "start_char": 5, "end_char": 10},
        {"text": "after", "start_char": 10, "end_char": 15},
    ]
    result = find_aligned_boundary_tokens(target, boundary)
    assert len(result) == 1 and result[0]["text"] == "exact"


# A partial crossing (neither span fully contains the other) was never
# observed in real data and is treated as a likely offset bug -- it must
# be excluded, not silently accepted the way raw overlap would accept it.

def test_partial_crossing_without_containment_raises():
    target = {"text": "middle", "start_char": 5, "end_char": 10}
    boundary = [
        {"text": "crosses_left", "start_char": 3, "end_char": 7},
        {"text": "crosses_right", "start_char": 8, "end_char": 12},
    ]
    with pytest.raises(ValueError):
        find_aligned_boundary_tokens(target, boundary)


def test_partial_crossing_candidate_filtered_out_even_with_a_real_match_present():
    target = {"text": "middle", "start_char": 5, "end_char": 10}
    boundary = [
        {"text": "crosses_left", "start_char": 3, "end_char": 7},  # excluded
        {"text": "exact", "start_char": 5, "end_char": 10},         # included
    ]
    result = find_aligned_boundary_tokens(target, boundary)
    assert [b["text"] for b in result] == ["exact"]


def test_exact_equal_spans_align():
    target = {"text": "слово", "start_char": 10, "end_char": 15}
    boundary = [{"text": "слово", "start_char": 10, "end_char": 15}]
    result = find_aligned_boundary_tokens(target, boundary)
    assert len(result) == 1 and result[0]["text"] == "слово"


# Zero matches must raise loudly, never silently drop the token.

def test_zero_match_raises_with_target_text_and_offsets():
    target = {"text": "фантом", "start_char": 100, "end_char": 106}
    boundary = [{"text": "слово", "start_char": 0, "end_char": 5}]
    with pytest.raises(ValueError, match=r"'фантом'.*\[100:106\)"):
        find_aligned_boundary_tokens(target, boundary)


def test_align_tokens_propagates_the_error():
    targets = [{"text": "фантом", "start_char": 100, "end_char": 106}]
    boundary = [{"text": "слово", "start_char": 0, "end_char": 5}]
    with pytest.raises(ValueError):
        align_tokens(targets, boundary)


def test_align_tokens_handles_mixed_directions_in_one_document():
    targets = [
        {"text": "бизнес", "start_char": 12, "end_char": 18},
        {"text": "веб-сайт", "start_char": 30, "end_char": 38},
    ]
    boundary = [
        {"text": "бизнес-план", "start_char": 12, "end_char": 23},
        {"text": "веб", "start_char": 30, "end_char": 33},
        {"text": "-", "start_char": 33, "end_char": 34},
        {"text": "сайт", "start_char": 34, "end_char": 38},
    ]
    result = align_tokens(targets, boundary)
    assert [b["text"] for b in result[0]["boundary_tokens"]] == ["бизнес-план"]
    assert [b["text"] for b in result[1]["boundary_tokens"]] == ["веб", "-", "сайт"]