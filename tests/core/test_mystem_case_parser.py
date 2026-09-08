from src.core.mystem_case_parser import extract_cases_from_gr, extract_cases_from_analysis


# Every real gr string captured, all six cases, four declensions

def test_clean_single_case_readings():
    assert extract_cases_from_gr("S,муж,неод=род,ед") == {"gen"}       # стола
    assert extract_cases_from_gr("S,муж,неод=дат,ед") == {"dat"}       # столу
    assert extract_cases_from_gr("S,муж,неод=твор,ед") == {"ins"}      # столом
    assert extract_cases_from_gr("S,муж,неод=пр,ед") == {"loc"}        # столе
    assert extract_cases_from_gr("S,жен,неод=им,ед") == {"nom"}        # книга
    assert extract_cases_from_gr("S,жен,неод=вин,ед") == {"acc"}       # книгу
    assert extract_cases_from_gr("S,муж,од=им,ед") == {"nom"}          # друг
    assert extract_cases_from_gr("S,муж,од=дат,ед") == {"dat"}         # другу
    assert extract_cases_from_gr("S,муж,од=пр,ед") == {"loc"}          # друге


def test_masc_inanimate_nom_acc_syncretism():
    # 'стол' identical gr string in both nominative and accusative context
    assert extract_cases_from_gr("S,муж,неод=(вин,ед|им,ед)") == {"acc", "nom"}


def test_neuter_nom_acc_syncretism():
    # 'окно' same pattern as masculine inanimate
    assert extract_cases_from_gr("S,сред,неод=(вин,ед|им,ед)") == {"acc", "nom"}


def test_masc_animate_gen_acc_syncretism():
    # 'друга' confirmed real: animate nouns syncretize gen/acc, not nom/acc
    assert extract_cases_from_gr("S,муж,од=(вин,ед|род,ед)") == {"acc", "gen"}


def test_feminine_dat_loc_syncretism():
    # 'книге' -- confirmed real in both dative and locative contexts
    assert extract_cases_from_gr("S,жен,неод=(пр,ед|дат,ед)") == {"loc", "dat"}


def test_three_way_genitive_singular_nominative_accusative_plural_syncretism():
    # Confirmed real, NOT predicted in advance: 'ножки', 'обложки',
    # 'окна', 'рамы' all showed this exact 3-way alternation.
    assert extract_cases_from_gr("S,жен,неод=(вин,мн|род,ед|им,мн)") == {"acc", "gen", "nom"}
    assert extract_cases_from_gr("S,сред,неод=(вин,мн|род,ед|им,мн)") == {"acc", "gen", "nom"}


def test_non_declining_pos_have_no_case():
    assert extract_cases_from_gr("PART=") == set()
    assert extract_cases_from_gr("PR=") == set()
    assert extract_cases_from_gr("ADV,прдк=") == set()


def test_short_form_adjective_has_no_case():
    # 'доволен' -- short-form adjectives don't decline for case in
    # Russian, only long-form ones do. Confirmed real: no case token
    # anywhere in the string despite having '=' and feature content.
    assert extract_cases_from_gr("A=ед,кр,муж") == set()


def test_verb_has_no_case():
    assert extract_cases_from_gr("V,несов,пе=непрош,ед,изъяв,1-л") == set()
    assert extract_cases_from_gr("V,нп=прош,ед,изъяв,муж,сов") == set()


def test_no_false_positive_substring_match_inside_adjacent_feature_word():
    # 'непрош' contains no case codes, but regression-guards against a
    # regex matching 'пр' as a substring inside a longer word like
    # 'прдк' or 'непрош' rather than requiring a real word boundary.
    assert extract_cases_from_gr("V,несов,нп=непрош,ед,изъяв,3-л") == set()


def test_the_confirmed_wrong_lemma_case_drugom():
    # Real, documented limitation: 'другом' (intended instrumental of
    # 'друг') was analyzed ONLY as 'другой'+prepositional. The parser's
    # job is just to correctly extract what Mystem actually returned --
    # confirming it does NOT invent an 'ins' reading that isn't there.
    result = extract_cases_from_gr("APRO=(пр,ед,муж|пр,ед,сред)")
    assert result == {"loc"}
    assert "ins" not in result  # the correct case is genuinely absent


# extract_cases_from_analysis: full reading lists

def test_extract_from_full_analysis_list():
    analysis = [{"lex": "стол", "wt": 1, "gr": "S,муж,неод=(вин,ед|им,ед)"}]
    assert extract_cases_from_analysis(analysis) == {"acc", "nom"}


def test_extract_unions_across_multiple_readings():
    # Different lemma candidates each contribute their cases; union,
    # not just the top reading, per the lemma-permissive design.
    analysis = [
        {"lex": "стол", "wt": 0.6, "gr": "S,муж,неод=твор,ед"},
        {"lex": "стола", "wt": 0.4, "gr": "S,жен,неод=род,мн"},
    ]
    assert extract_cases_from_analysis(analysis) == {"ins", "gen"}


def test_extract_from_empty_or_none_analysis():
    assert extract_cases_from_analysis([]) == set()
    assert extract_cases_from_analysis(None) == set()


def test_extract_skips_readings_with_no_case():
    analysis = [
        {"lex": "довольный", "wt": 1, "gr": "A=ед,кр,муж"},
        {"lex": "стол", "wt": 1, "gr": "S,муж,неод=твор,ед"},
    ]
    assert extract_cases_from_analysis(analysis) == {"ins"}
