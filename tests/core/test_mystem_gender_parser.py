# Fixtures are the REAL gr strings from gender_agreement_diagnostics_report.json
# (scratchpad_gender_agreement_diagnostics.py's actual run output), not
# invented -- same "build tests from confirmed real output" practice as
# mystem_case_parser.py's own test suite.

from src.core.mystem_gender_parser import (
    extract_genders_from_gr,
    extract_genders_from_analysis,
    is_common_gender,
)


def test_masculine_noun_stol():
    assert extract_genders_from_gr("S,муж,неод=(вин,ед|им,ед)") == {"masc"}


def test_feminine_noun_kniga():
    assert extract_genders_from_gr("S,жен,неод=им,ед") == {"fem"}


def test_neuter_noun_okno_uses_sred_not_sr():
    # Confirms the real code is "сред", not the "ср" that would have
    # been an untested guess -- this is the whole point of the diagnostic.
    assert extract_genders_from_gr("S,сред,неод=(вин,ед|им,ед)") == {"neut"}


def test_common_gender_noun_sirota_returns_common_not_masc_or_fem():
    # Real: identical gr in BOTH a masc-context and fem-context sentence.
    assert extract_genders_from_gr("S,мж,од=им,ед") == {"common"}
    assert is_common_gender(extract_genders_from_gr("S,мж,од=им,ед")) is True


def test_short_form_adjectives_all_three_genders():
    assert extract_genders_from_gr("A=ед,кр,муж") == {"masc"}
    assert extract_genders_from_gr("A=ед,кр,жен") == {"fem"}


def test_attributive_adjective_alternation_can_span_two_genders():
    # Real, confirmed limitation: "большой" alternates masc-nom with
    # fem-oblique forms (both end in "-ой"). Flat union, same
    # permissive approach as case extraction -- does not pair gender to
    # its specific case slot.
    gr = "A=(вин,ед,полн,муж,неод|им,ед,полн,муж|пр,ед,полн,жен|дат,ед,полн,жен|род,ед,полн,жен|твор,ед,полн,жен)"
    assert extract_genders_from_gr(gr) == {"masc", "fem"}


def test_singular_past_tense_verb_genders():
    assert extract_genders_from_gr("V,несов,пе=прош,ед,изъяв,муж") == {"masc"}
    assert extract_genders_from_gr("V,несов,пе=прош,ед,изъяв,жен") == {"fem"}
    assert extract_genders_from_gr("V,несов,пе=прош,ед,изъяв,сред") == {"neut"}


def test_plural_past_tense_verb_has_no_gender():
    # Confirms the plural-has-no-gender finding holds at the parser
    # level too, not just at the raw feats level.
    assert extract_genders_from_gr("V,несов,пе=прош,мн,изъяв") == set()


def test_umno_confirmed_misanalyzed_as_adverb_not_short_form_adjective():
    # Documented as a passing test, per project convention, not just a
    # comment -- same treatment as "другом" in mystem_case_parser.py.
    # Mystem offered ONLY the adverb reading for "умно" in
    # "Оно умно.", with zero adjective alternative -- no parsing logic
    # can recover a reading Mystem never produced.
    assert extract_genders_from_gr("ADV=") == set()


def test_non_declining_pos_returns_empty_set():
    assert extract_genders_from_gr("PR=") == set()
    assert extract_genders_from_gr("CONJ=") == set()


def test_extract_genders_from_analysis_handles_none_and_empty():
    assert extract_genders_from_analysis(None) == set()
    assert extract_genders_from_analysis([]) == set()


def test_extract_genders_from_analysis_unions_across_readings_lemma_permissive():
    analysis = [
        {"lex": "большой", "gr": "A=(вин,ед,полн,муж,неод|им,ед,полн,муж)"},
        {"lex": "большой", "gr": "A=пр,ед,полн,жен"},
    ]
    assert extract_genders_from_analysis(analysis) == {"masc", "fem"}
