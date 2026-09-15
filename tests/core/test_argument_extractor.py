from src.core.argument_extractor import (
    extract_verb_arguments,
    reconstruct_preposition,
    is_negated,
    parse_feats,
)


def _tok(id_, text, upos, head, deprel, feats="_"):
    return {"id": id_, "text": text, "lemma": text, "upos": upos, "xpos": "_",
            "feats": feats, "head": head, "deprel": deprel, "deps": "_", "misc": "_"}


# "Он сделал это с помощью брата." -- real tokens from the uploaded report.
MULTIWORD_PREP_SENTENCE = [
    _tok("1", "Он", "PRON", "2", "nsubj"),
    _tok("2", "сделал", "VERB", "0", "root", feats="Aspect=Perf|Mood=Ind|Tense=Past|VerbForm=Fin"),
    _tok("3", "это", "PRON", "2", "obj"),
    _tok("4", "с", "ADP", "6", "case"),
    _tok("5", "помощью", "NOUN", "4", "fixed"),
    _tok("6", "брата", "NOUN", "2", "obl"),
    _tok("7", ".", "PUNCT", "2", "punct"),
]


def test_multiword_preposition_reconstructed_with_framebank_plus_format():
    argument = MULTIWORD_PREP_SENTENCE[5]  # "брата"
    assert reconstruct_preposition(MULTIWORD_PREP_SENTENCE, argument) == "с + помощью"


def test_extract_verb_arguments_finds_both_the_bare_obj_and_the_prepositional_obl():
    # "сделал" governs two arguments: "это" (obj, bare, no preposition --
    # the direct object "did this") and "брата" (obl, with "с помощью").
    # Confirms extract_verb_arguments doesn't assume one argument per verb.
    results = extract_verb_arguments(MULTIWORD_PREP_SENTENCE)
    assert len(results) == 2

    by_text = {r["argument_token"]["text"]: r for r in results}
    assert by_text["это"]["preposition"] is None
    assert by_text["брата"]["preposition"] == "с + помощью"
    assert all(r["is_negated"] is False for r in results)


# "Он не вижу стола." (negation_genitive_trigger shape) is reconstructed
# from the diagnostic script's summary: separate advmod "не" token,
# Polarity feature null on the verb.
NEGATED_GENITIVE_SENTENCE = [
    _tok("1", "Я", "PRON", "3", "nsubj"),
    _tok("2", "не", "PART", "3", "advmod"),
    _tok("3", "вижу", "VERB", "0", "root", feats="Aspect=Imp|Mood=Ind|Tense=Pres|VerbForm=Fin"),
    _tok("4", "стола", "NOUN", "3", "obj"),
    _tok("5", ".", "PUNCT", "3", "punct"),
]


def test_negation_detected_via_advmod_not_polarity_feature():
    verb = NEGATED_GENITIVE_SENTENCE[2]
    assert is_negated(NEGATED_GENITIVE_SENTENCE, verb) is True
    # confirms we're not relying on a Polarity feature that doesn't exist
    assert "Polarity" not in parse_feats(verb["feats"])


def test_extract_verb_arguments_flags_negated_construction():
    results = extract_verb_arguments(NEGATED_GENITIVE_SENTENCE)
    assert len(results) == 1
    assert results[0]["is_negated"] is True
    assert results[0]["preposition"] is None  # bare genitive, no preposition


# "Она помогает другу." is bare dative, no preposition (the real
# construction that confirms preposition must be optional, not assumed
# present whenever an argument is found).
BARE_DATIVE_SENTENCE = [
    _tok("1", "Она", "PRON", "2", "nsubj"),
    _tok("2", "помогает", "VERB", "0", "root", feats="Aspect=Imp|Tense=Pres"),
    _tok("3", "другу", "NOUN", "2", "iobj"),
    _tok("4", ".", "PUNCT", "2", "punct"),
]


def test_bare_case_argument_has_no_preposition():
    results = extract_verb_arguments(BARE_DATIVE_SENTENCE)
    assert len(results) == 1
    assert results[0]["argument_token"]["deprel"] == "iobj"
    assert results[0]["preposition"] is None


def test_parse_feats_handles_underscore_and_pipe_format():
    assert parse_feats("_") == {}
    assert parse_feats("Aspect=Imp|VerbForm=Inf") == {"Aspect": "Imp", "VerbForm": "Inf"}
