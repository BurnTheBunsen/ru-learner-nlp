from src.adapters.framebank_adapter import parse_form, build_index_from_rows, FrameBankAdapter


def test_bare_case():
    assert parse_form("Snom") == [{"case": "nom", "preposition": None, "parseable": True, "raw": "Snom"}]


def test_single_word_preposition():
    assert parse_form("по + Sdat") == [{"case": "dat", "preposition": "по", "parseable": True, "raw": "по + Sdat"}]
    assert parse_form("о + Sloc") == [{"case": "loc", "preposition": "о", "parseable": True, "raw": "о + Sloc"}]
    assert parse_form("за + Sacc") == [{"case": "acc", "preposition": "за", "parseable": True, "raw": "за + Sacc"}]
    assert parse_form("из-за + Sgen") == [{"case": "gen", "preposition": "из-за", "parseable": True, "raw": "из-за + Sgen"}]


def test_multi_word_preposition():
    result = parse_form("с + помощью + Sgen")[0]
    assert result["case"] == "gen"
    assert result["preposition"] == "с помощью"
    assert result["parseable"] is True


def test_clausal_forms_are_unparseable_not_guessed():
    for form in ["что + CL", "Rel + CL", "CLi", "«CL»", "Vinf", "ADVPRO"]:
        result = parse_form(form)[0]
        assert result["parseable"] is False, f"{form!r} should be unparseable"
        assert result["case"] is None


def test_ambiguous_curly_brace_alternation_is_unparseable():
    result = parse_form("{ADV / PRоткуда + Sx}")
    assert len(result) == 1
    assert result[0]["parseable"] is False
    assert result[0]["case"] is None


def test_clean_alternation_yields_both_readings():
    result = parse_form("{Sdat / для + Sgen}")
    assert len(result) == 2
    assert result[0] == {"case": "dat", "preposition": None, "parseable": True, "raw": "Sdat"}
    assert result[1] == {"case": "gen", "preposition": "для", "parseable": True, "raw": "для + Sgen"}


def test_no_spaces_around_plus():
    result = parse_form("по+Sdat")[0]
    assert result == {"case": "dat", "preposition": "по", "parseable": True, "raw": "по+Sdat"}


def test_extra_internal_whitespace():
    result = parse_form("по   +   Sdat")[0]
    assert result["case"] == "dat"
    assert result["preposition"] == "по"


def test_surrounding_whitespace_on_bare_form():
    result = parse_form("  Snom  ")[0]
    assert result == {"case": "nom", "preposition": None, "parseable": True, "raw": "Snom"}


def test_empty_form_does_not_crash():
    result = parse_form("")[0]
    assert result["parseable"] is False
    assert result["case"] is None


#Known, documented limitations

def test_known_limitation_case_sensitivity():
    # Not evidenced in the real sample, but worth documenting rather
    # than silently assuming: matching is currently case-sensitive.
    # If the real file ever has non-canonical casing, this will NOT match.
    result = parse_form("snom")[0]
    assert result["parseable"] is False, (
        "parse_form is case-sensitive by design; lowercase 'snom' is "
        "currently NOT recognized. If real data has this, revisit."
    )


def test_known_limitation_unwrapped_slash_alternation():
    result = parse_form("в / на + Sacc")[0]
    assert result["parseable"] is False


#build_index_from_rows / FrameBankAdapter: real sample rows

REAL_SAMPLE_ROWS = [
    {"ConstrIndex": "201", "Place": "1", "Form": "Snom", "Role": "субъект психологического состояния", "Rank": "Субъект", "SemClass": "лицо", "KeyLexemes": "волноваться"},
    {"ConstrIndex": "201", "Place": "2", "Form": "волноваться", "Role": "-", "Rank": "Предикат", "SemClass": "-", "KeyLexemes": "волноваться"},
    {"ConstrIndex": "202", "Place": "1", "Form": "Snom", "Role": "субъект психологического состояния", "Rank": "Субъект", "SemClass": "лицо", "KeyLexemes": "волноваться"},
    {"ConstrIndex": "202", "Place": "2", "Form": "волноваться", "Role": "-", "Rank": "Предикат", "SemClass": "-", "KeyLexemes": "волноваться"},
    {"ConstrIndex": "202", "Place": "3", "Form": "из-за + Sgen", "Role": "причина", "Rank": "Периферия", "SemClass": "абстрактный", "KeyLexemes": "волноваться"},
    {"ConstrIndex": "203", "Place": "3", "Form": "за + Sacc", "Role": "причина", "Rank": "Периферия", "SemClass": "-", "KeyLexemes": "волноваться"},
    {"ConstrIndex": "204", "Place": "3", "Form": "что + CL", "Role": "причина", "Rank": "Клауза", "SemClass": "пропозиция", "KeyLexemes": "волноваться"},
    {"ConstrIndex": "209", "Place": "3", "Form": "о + Sloc", "Role": "причина", "Rank": "Периферия", "SemClass": "лицо; пропозиция", "KeyLexemes": "волноваться"},
    {"ConstrIndex": "210", "Place": "3", "Form": "по + Sdat", "Role": "причина", "Rank": "Периферия", "SemClass": '"повод", "причина"', "KeyLexemes": "волноваться"},
    {"ConstrIndex": "221", "Place": "3", "Form": "{ADV / PRоткуда + Sx}", "Role": "начальная точка", "Rank": "Периферия", "SemClass": "место", "KeyLexemes": "выступать,выступить"},
]


def test_predicate_rows_are_excluded_from_index():
    index = build_index_from_rows(REAL_SAMPLE_ROWS)
    slots = index["волноваться"]
    assert all(s["rank"] != "Предикат" for s in slots)
    assert len(slots) == 7


def test_expected_cases_bare_subject():
    adapter = FrameBankAdapter.__new__(FrameBankAdapter)
    adapter.index = build_index_from_rows(REAL_SAMPLE_ROWS)
    assert adapter.expected_cases("волноваться", preposition=None) == {"nom"}


def test_expected_cases_with_various_prepositions():
    adapter = FrameBankAdapter.__new__(FrameBankAdapter)
    adapter.index = build_index_from_rows(REAL_SAMPLE_ROWS)
    assert adapter.expected_cases("волноваться", preposition="из-за") == {"gen"}
    assert adapter.expected_cases("волноваться", preposition="за") == {"acc"}
    assert adapter.expected_cases("волноваться", preposition="о") == {"loc"}
    assert adapter.expected_cases("волноваться", preposition="по") == {"dat"}


def test_clausal_slot_never_surfaces_in_expected_cases():
    adapter = FrameBankAdapter.__new__(FrameBankAdapter)
    adapter.index = build_index_from_rows(REAL_SAMPLE_ROWS)
    for prep in [None, "что", "из-за", "за", "о", "по"]:
        assert None not in adapter.expected_cases("волноваться", preposition=prep)


def test_aspectual_pair_both_lemmas_share_the_same_slots():
    index = build_index_from_rows(REAL_SAMPLE_ROWS)
    assert index["выступать"] == index["выступить"]


def test_unparseable_curly_brace_slot_excluded_from_expected_cases():
    adapter = FrameBankAdapter.__new__(FrameBankAdapter)
    adapter.index = build_index_from_rows(REAL_SAMPLE_ROWS)
    slots = adapter.slots_for_verb("выступать")
    assert any(not s["parseable"] for s in slots)
    assert adapter.expected_cases("выступать", preposition=None) == set()


def test_unknown_verb_returns_empty_set():
    adapter = FrameBankAdapter.__new__(FrameBankAdapter)
    adapter.index = build_index_from_rows(REAL_SAMPLE_ROWS)
    assert adapter.expected_cases("несуществующийглагол", preposition=None) == set()


#KeyLexemes formatting

def test_keylexemes_extra_whitespace_around_commas():
    rows = [{"ConstrIndex": "1", "Place": "1", "Form": "Snom", "Role": "-", "Rank": "Субъект", "SemClass": "-",
             "KeyLexemes": "делать,  сделать ,  переделать"}]
    index = build_index_from_rows(rows)
    assert set(index.keys()) == {"делать", "сделать", "переделать"}


def test_keylexemes_trailing_comma_does_not_create_empty_lemma():
    rows = [{"ConstrIndex": "1", "Place": "1", "Form": "Snom", "Role": "-", "Rank": "Субъект", "SemClass": "-",
             "KeyLexemes": "думать,"}]
    index = build_index_from_rows(rows)
    assert "" not in index
    assert set(index.keys()) == {"думать"}


def test_expected_cases_can_return_multiple_cases_for_one_preposition():
    rows = [
        {"ConstrIndex": "1", "Place": "3", "Form": "в + Sacc", "Role": "цель", "Rank": "Периферия", "SemClass": "-", "KeyLexemes": "верить"},
        {"ConstrIndex": "2", "Place": "3", "Form": "в + Sloc", "Role": "место", "Rank": "Периферия", "SemClass": "-", "KeyLexemes": "верить"},
    ]
    adapter = FrameBankAdapter.__new__(FrameBankAdapter)
    adapter.index = build_index_from_rows(rows)
    assert adapter.expected_cases("верить", preposition="в") == {"acc", "loc"}


def test_init_reads_real_tsv_file(tmp_path):
    tsv = (
        "ConstrIndex\tPlace\tForm\tRole\tRank\tSemClass\tKeyLexemes\n"
        "210\t3\tпо + Sdat\tпричина\tПериферия\tx\tволноваться\n"
        "211\t1\tSnom\tx\tСубъект\tлицо\tволноваться\n"
    )
    path = tmp_path / "framebank.tsv"
    path.write_text(tsv, encoding="utf-8")

    adapter = FrameBankAdapter(str(path))
    assert adapter.expected_cases("волноваться", preposition="по") == {"dat"}


def test_init_preserves_literal_quote_characters_in_fields(tmp_path):
    tsv = (
        "ConstrIndex\tPlace\tForm\tRole\tRank\tSemClass\tKeyLexemes\n"
        '210\t3\tпо + Sdat\tпричина\tПериферия\t"повод", "причина"\tволноваться\n'
    )
    path = tmp_path / "framebank.tsv"
    path.write_text(tsv, encoding="utf-8")

    adapter = FrameBankAdapter(str(path))
    slot = adapter.slots_for_verb("волноваться")[0]
    assert slot["sem_class"] == '"повод", "причина"'


def test_init_handles_utf8_bom(tmp_path):
    # Regression test for the confirmed real bug: a UTF-8 BOM prefix
    # (plausible for a Windows-exported file) merges into the first
    # header name under plain 'utf-8', turning 'ConstrIndex' into
    # '\ufeffConstrIndex' and breaking every row lookup with a KeyError.
    tsv = "ConstrIndex\tPlace\tForm\tRole\tRank\tSemClass\tKeyLexemes\n210\t3\tпо + Sdat\tx\tПериферия\tx\tволноваться\n"
    path = tmp_path / "framebank_bom.tsv"
    path.write_bytes(b'\xef\xbb\xbf' + tsv.encode("utf-8"))  # UTF-8 BOM bytes

    adapter = FrameBankAdapter(str(path))
    assert adapter.expected_cases("волноваться", preposition="по") == {"dat"}


def test_init_handles_trailing_blank_line(tmp_path):
    # Confirmed NOT a problem (csv.DictReader skips genuinely empty lines)
    # included as an explicit regression test rather than an
    # unverified assumption.
    tsv = "ConstrIndex\tPlace\tForm\tRole\tRank\tSemClass\tKeyLexemes\n210\t3\tпо + Sdat\tx\tПериферия\tx\tволноваться\n\n"
    path = tmp_path / "framebank_trailing.tsv"
    path.write_text(tsv, encoding="utf-8")

    adapter = FrameBankAdapter(str(path))
    assert len(adapter.slots_for_verb("волноваться")) == 1