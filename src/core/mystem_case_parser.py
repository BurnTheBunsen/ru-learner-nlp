# Extracts Russian cases (FrameBank's Latin abbreviations: nom/gen/dat/
# acc/ins/loc) from a Mystem 'gr' string.

import re

CASE_MAP = {
    'им': 'nom',
    'род': 'gen',
    'дат': 'dat',
    'вин': 'acc',
    'твор': 'ins',
    'пр': 'loc',
}

_CASE_TOKEN_PATTERN = re.compile(r'\b(' + '|'.join(CASE_MAP) + r')\b')


def extract_cases_from_gr(gr: str) -> set:
    """
    Cases found in a single Mystem 'gr' string. Empty set for
    non-declining POS (particles, prepositions, short-form adjectives)
    or a gr string with no case marking.
    """
    if '=' not in gr:
        return set()

    _, rest = gr.split('=', 1)
    return {CASE_MAP[m] for m in _CASE_TOKEN_PATTERN.findall(rest)}


def extract_cases_from_analysis(analysis: list) -> set:
    """Union of cases across every reading in a Mystem 'analysis' list."""
    cases = set()
    for reading in analysis or []:
        gr = reading.get('gr')
        if gr:
            cases |= extract_cases_from_gr(gr)
    return cases
