from src.pipeline.build_targets_from_extraction import build_targets_from_extraction


def _tok(id_, text, upos, head, deprel, feats="_", lemma=None):
    return {"id": id_, "text": text, "lemma": lemma or text, "upos": upos, "xpos": "_",
            "feats": feats, "head": head, "deprel": deprel, "deps": "_", "misc": "_"}


class FakeFrameBankAdapter:
    """
    Minimal stand-in for FrameBankAdapter, matching the documented
    contract: expected_cases(verb_lemma, preposition=None) -> set.
    Records every call for assertion, so tests can confirm the glue
    passes the right lemma/preposition through, not just that the
    final dict shape looks right.
    """
    def __init__(self, table):
        self.table = table  # {(verb_lemma, preposition): set_of_cases}
        self.calls = []

    def expected_cases(self, verb_lemma, preposition=None):
        self.calls.append((verb_lemma, preposition))
        return self.table.get((verb_lemma, preposition), set())


# Same real sentence as test_argument_extractor.py's BARE_DATIVE_SENTENCE
# ("Она помогает другу.") -- bare dative, no preposition.
BARE_DATIVE_SENTENCE = [
    _tok("1", "Она", "PRON", "2", "nsubj"),
    _tok("2", "помогает", "VERB", "0", "root", feats="Aspect=Imp|Tense=Pres", lemma="помогать"),
    _tok("3", "другу", "NOUN", "2", "iobj", lemma="друг"),
    _tok("4", ".", "PUNCT", "2", "punct"),
]


def test_bare_argument_calls_expected_cases_with_preposition_none():
    adapter = FakeFrameBankAdapter({("помогать", None): {"dat"}})
    results = build_targets_from_extraction(BARE_DATIVE_SENTENCE, adapter)

    assert adapter.calls == [("помогать", None)]
    assert len(results) == 1
    assert results[0]["target"]["text"] == "другу"
    assert results[0]["expected_cases"] == {"dat"}
    assert results[0]["is_negated"] is False


# Same real sentence as test_argument_extractor.py's
# MULTIWORD_PREP_SENTENCE ("Он сделал это с помощью брата.") -- two
# arguments on one verb, one bare, one with a multi-word preposition.
MULTIWORD_PREP_SENTENCE = [
    _tok("1", "Он", "PRON", "2", "nsubj"),
    _tok("2", "сделал", "VERB", "0", "root", feats="Aspect=Perf|Tense=Past", lemma="сделать"),
    _tok("3", "это", "PRON", "2", "obj", lemma="это"),
    _tok("4", "с", "ADP", "6", "case"),
    _tok("5", "помощью", "NOUN", "4", "fixed"),
    _tok("6", "брата", "NOUN", "2", "obl", lemma="брат"),
    _tok("7", ".", "PUNCT", "2", "punct"),
]


def test_multiple_arguments_on_one_verb_each_get_their_own_lookup():
    # Real format confirmed against the real adapter + real file: plain
    # space, not " + ".
    adapter = FakeFrameBankAdapter({
        ("сделать", None): {"acc"},
        ("сделать", "с помощью"): {"gen"},
    })
    results = build_targets_from_extraction(MULTIWORD_PREP_SENTENCE, adapter)

    assert set(adapter.calls) == {("сделать", None), ("сделать", "с помощью")}
    by_text = {r["target"]["text"]: r for r in results}
    assert by_text["это"]["expected_cases"] == {"acc"}
    assert by_text["брата"]["expected_cases"] == {"gen"}


def test_unattested_combination_yields_empty_expected_cases_not_an_error():
    # verb/preposition combo missing from the table entirely -- glue
    # should pass through an empty set, matching decide_case_error's
    # {"status": "no_data"} contract, not raise or skip the target.
    adapter = FakeFrameBankAdapter({})  # nothing attested
    results = build_targets_from_extraction(BARE_DATIVE_SENTENCE, adapter)

    assert len(results) == 1
    assert results[0]["expected_cases"] == set()


# Same real sentence as test_argument_extractor.py's
# NEGATED_GENITIVE_SENTENCE ("Я не вижу стола.").
NEGATED_GENITIVE_SENTENCE = [
    _tok("1", "Я", "PRON", "3", "nsubj"),
    _tok("2", "не", "PART", "3", "advmod"),
    _tok("3", "вижу", "VERB", "0", "root", feats="Aspect=Imp|Tense=Pres", lemma="видеть"),
    _tok("4", "стола", "NOUN", "3", "obj", lemma="стол"),
    _tok("5", ".", "PUNCT", "3", "punct"),
]


def test_is_negated_passes_through_from_extractor():
    adapter = FakeFrameBankAdapter({("видеть", None): {"acc"}})
    results = build_targets_from_extraction(NEGATED_GENITIVE_SENTENCE, adapter)

    assert len(results) == 1
    assert results[0]["is_negated"] is True
    assert results[0]["target"]["text"] == "стола"