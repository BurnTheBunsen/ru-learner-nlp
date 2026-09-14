# Extracts grammatical gender from Mystem's gr string, parallel to
# mystem_case_parser.py's case extraction. Feeds the gender-concord
# hypothesis (H1', replacing aspect).

import re

_GENDER_MAP = {"муж": "masc", "жен": "fem", "сред": "neut", "мж": "common"}


def extract_genders_from_gr(gr_string: str) -> set:
    """
    gr_string: the raw 'gr' value from one Mystem reading (e.g.
    "S,муж,неод=(вин,ед|им,ед)" or "A=ед,кр,жен").

    Returns a set of genders found anywhere in the string:
    {'masc', 'fem', 'neut', 'common'} (any subset, including empty).
    Empty for non-declining/non-agreeing forms (PR=, CONJ=, ADV=,
    plural verb forms, etc.). These simply contain none of the four
    tag strings, no special-casing needed.
    """
    genders = set()
    if not gr_string:
        return genders
    for ru, en in _GENDER_MAP.items():
        if re.search(r'\b' + ru + r'\b', gr_string):
            genders.add(en)
    return genders


def extract_genders_from_analysis(analysis_list) -> set:
    """
    analysis_list: the 'analysis' list from a Mystem fragment dict (may
    be None or [], per mystem_adapter.py's confirmed shapes).

    Unions genders across every offered reading, regardless of lemma
    (deliberately lemma-permissive).
    """
    genders = set()
    if not analysis_list:
        return genders
    for reading in analysis_list:
        genders |= extract_genders_from_gr(reading.get("gr", ""))
    return genders


def is_common_gender(genders: set) -> bool:
    """
    Convenience check for the exclusion decision: True if 'common' is
    among the genders found. Callers building the concord Target should
    treat this as "exclude this noun", not "compare against Masc/Fem".
    """
    return "common" in genders
