from src.core.concord_extractor import find_concord_pairs, parse_feats


def _tok(id_, text, upos, head, deprel, feats="_"):
    return {"id": id_, "text": text, "lemma": text, "upos": upos, "xpos": "_",
            "feats": feats, "head": head, "deprel": deprel, "deps": "_", "misc": "_"}


# Real tokens from gender_agreement_diagnostics_report.json "Он взял свою книгу."
REFLEXIVE_POSSESSIVE_SENTENCE = [
    _tok("1", "Он", "PRON", "2", "nsubj", feats="Case=Nom|Gender=Masc|Number=Sing|Person=3"),
    _tok("2", "взял", "VERB", "0", "root",
         feats="Aspect=Perf|Gender=Masc|Mood=Ind|Number=Sing|Tense=Past|VerbForm=Fin|Voice=Act"),
    _tok("3", "свою", "DET", "4", "det", feats="Case=Acc|Gender=Fem|Number=Sing"),
    _tok("4", "книгу", "NOUN", "2", "obj", feats="Animacy=Inan|Case=Acc|Gender=Fem|Number=Sing"),
    _tok("5", ".", "PUNCT", "2", "punct"),
]


def test_reflexive_possessive_agrees_with_possessed_noun_not_possessor():
    results = find_concord_pairs(REFLEXIVE_POSSESSIVE_SENTENCE)
    det_pairs = [r for r in results if r["construction"] == "determiner"]
    assert len(det_pairs) == 1
    assert det_pairs[0]["controller"]["text"] == "книгу"  # possessed noun, not "Он"
    assert det_pairs[0]["dependent"]["text"] == "свою"


def test_reflexive_possessive_sentence_also_finds_subject_verb_pair():
    results = find_concord_pairs(REFLEXIVE_POSSESSIVE_SENTENCE)
    sv_pairs = [r for r in results if r["construction"] == "subject_verb"]
    assert len(sv_pairs) == 1
    assert sv_pairs[0]["controller"]["text"] == "Он"
    assert sv_pairs[0]["dependent"]["text"] == "взял"


# Relationships confirmed (deprel/head/upos), ids
# assigned for a complete sentence "Стол был большой."
PREDICATE_VIA_COPULA_SENTENCE = [
    _tok("1", "Стол", "NOUN", "3", "nsubj", feats="Gender=Masc|Number=Sing|Case=Nom"),
    _tok("2", "был", "AUX", "3", "cop", feats="Gender=Masc|Number=Sing|Tense=Past|VerbForm=Fin"),
    _tok("3", "большой", "ADJ", "0", "root", feats="Gender=Masc|Number=Sing|Variant=Full"),
    _tok("4", ".", "PUNCT", "3", "punct"),
]


def test_long_form_predicate_adjective_found_via_nsubj_not_amod():
    results = find_concord_pairs(PREDICATE_VIA_COPULA_SENTENCE)
    pred_pairs = [r for r in results if r["construction"] == "predicate_adjective"]
    assert len(pred_pairs) == 1
    assert pred_pairs[0]["controller"]["text"] == "Стол"
    assert pred_pairs[0]["dependent"]["text"] == "большой"
    # confirms this is NOT also (incorrectly) picked up as attributive
    assert not any(r["construction"] == "attributive" for r in results)


ATTRIBUTIVE_AGREEMENT_SENTENCE = [
    _tok("1", "Большая", "ADJ", "2", "amod", feats="Gender=Fem|Number=Sing|Case=Nom"),
    _tok("2", "книга", "NOUN", "3", "nsubj", feats="Gender=Fem|Number=Sing|Case=Nom|Animacy=Inan"),
    _tok("3", "лежит", "VERB", "0", "root", feats="Aspect=Imp|Mood=Ind|Number=Sing|Person=3|Tense=Pres"),
    _tok("4", "на", "ADP", "5", "case"),
    _tok("5", "столе", "NOUN", "3", "obl", feats="Gender=Masc|Number=Sing|Case=Loc|Animacy=Inan"),
    _tok("6", ".", "PUNCT", "3", "punct"),
]


def test_attributive_adjective_found_via_amod():
    results = find_concord_pairs(ATTRIBUTIVE_AGREEMENT_SENTENCE)
    attr_pairs = [r for r in results if r["construction"] == "attributive"]
    assert len(attr_pairs) == 1
    assert attr_pairs[0]["controller"]["text"] == "книга"
    assert attr_pairs[0]["dependent"]["text"] == "Большая"


def test_present_tense_verb_is_not_flagged_as_subject_verb_pair():
    results = find_concord_pairs(ATTRIBUTIVE_AGREEMENT_SENTENCE)
    sv_pairs = [r for r in results if r["construction"] == "subject_verb"]
    assert len(sv_pairs) == 1
    assert sv_pairs[0]["dependent"]["text"] == "лежит"


PLURAL_PAST_TENSE_SENTENCE = [
    _tok("1", "Студенты", "NOUN", "2", "nsubj", feats="Number=Plur|Case=Nom|Animacy=Anim"),
    _tok("2", "читали", "VERB", "0", "root", feats="Aspect=Imp|Mood=Ind|Number=Plur|Tense=Past|VerbForm=Fin"),
    _tok("3", "книгу", "NOUN", "2", "obj", feats="Gender=Fem|Number=Sing|Case=Acc|Animacy=Inan"),
    _tok("4", ".", "PUNCT", "2", "punct"),
]


def test_plural_subject_verb_pair_still_structurally_found():
    results = find_concord_pairs(PLURAL_PAST_TENSE_SENTENCE)
    sv_pairs = [r for r in results if r["construction"] == "subject_verb"]
    assert len(sv_pairs) == 1
    assert "Gender" not in parse_feats(sv_pairs[0]["dependent"]["feats"])


def test_no_pairs_found_in_sentence_with_no_agreement_targets():
    empty_ish = [
        _tok("1", "и", "CCONJ", "0", "root"),
        _tok("2", ".", "PUNCT", "1", "punct"),
    ]
    assert find_concord_pairs(empty_ish) == []


INVARIANT_POSSESSIVE_EGO_SENTENCE = [
    _tok("1", "Он", "PRON", "2", "nsubj", feats="Case=Nom|Gender=Masc|Number=Sing|Person=3"),
    _tok("2", "взял", "VERB", "0", "root",
         feats="Aspect=Perf|Gender=Masc|Mood=Ind|Number=Sing|Tense=Past|VerbForm=Fin|Voice=Act"),
    _tok("3", "его", "DET", "4", "det", feats="_"),
    _tok("4", "книгу", "NOUN", "2", "obj", feats="Animacy=Inan|Case=Acc|Gender=Fem|Number=Sing"),
    _tok("5", ".", "PUNCT", "2", "punct"),
]


def test_invariant_possessive_ego_produces_no_determiner_pair():
    results = find_concord_pairs(INVARIANT_POSSESSIVE_EGO_SENTENCE)
    assert not any(r["construction"] == "determiner" for r in results)


INVARIANT_POSSESSIVE_EYO_SENTENCE = [
    _tok("1", "Он", "PRON", "2", "nsubj", feats="Case=Nom|Gender=Masc|Number=Sing|Person=3"),
    _tok("2", "взял", "VERB", "0", "root",
         feats="Aspect=Perf|Gender=Masc|Mood=Ind|Number=Sing|Tense=Past|VerbForm=Fin|Voice=Act"),
    _tok("3", "её", "PRON", "4", "nmod", feats="Case=Gen|Gender=Fem|Number=Sing|Person=3"),
    _tok("4", "книгу", "NOUN", "2", "obj", feats="Animacy=Inan|Case=Acc|Gender=Fem|Number=Sing"),
    _tok("5", ".", "PUNCT", "2", "punct"),
]


def test_invariant_possessive_eyo_produces_no_determiner_pair_despite_having_gender():
    results = find_concord_pairs(INVARIANT_POSSESSIVE_EYO_SENTENCE)
    assert not any(r["construction"] == "determiner" for r in results)


def test_invariant_possessive_eyo_would_be_wrongly_accepted_without_the_lemma_guard():
    hypothetical = [
        _tok("1", "Он", "PRON", "2", "nsubj", feats="Gender=Masc"),
        _tok("2", "взял", "VERB", "0", "root", feats="Gender=Masc"),
        _tok("3", "её", "DET", "4", "det", feats="Case=Gen|Gender=Fem|Number=Sing"),
        _tok("4", "книгу", "NOUN", "2", "obj", feats="Gender=Fem"),
    ]
    results = find_concord_pairs(hypothetical)
    assert not any(r["construction"] == "determiner" for r in results)
