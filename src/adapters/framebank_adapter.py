# Looks up expected case/preposition patterns for Russian verbs from the
# Russian FrameBank offline dictionary release
# (github.com/olesar/framebank), framebank_dict_cx_items.txt.

import csv
import logging
import re
from typing import Iterable

logger = logging.getLogger(__name__)

CASE_PATTERN = re.compile(r'^S(nom|gen|dat|acc|ins|loc)$')
PREDICATE_RANK = 'Предикат'


def _parse_single(form: str) -> dict:
    segments = [s.strip() for s in form.split('+')]
    match = CASE_PATTERN.match(segments[-1])

    if not match:
        return {"case": None, "preposition": None, "parseable": False, "raw": form}

    case = match.group(1)
    preposition = ' '.join(segments[:-1]) if len(segments) > 1 else None

    if preposition is not None and '/' in preposition:
        # A literal '/' inside what would be the preposition text is not
        # a real preposition -- it's an unhandled alternation notation
        # that isn't wrapped in '{...}' (e.g. "в / на + Sacc"). Flag it
        # rather than silently accept a garbled preposition string that
        # would never match anything real.
        return {"case": None, "preposition": None, "parseable": False, "raw": form}

    return {"case": case, "preposition": preposition, "parseable": True, "raw": form}


def parse_form(form: str) -> list:
    """
    One or more {case, preposition, parseable, raw} dicts. Most Forms
    yield exactly one. A '{A / B}' alternation where every side parses
    yields one dict per side (both readings are valid). If any side
    doesn't reduce to a case pattern, the whole alternation comes back
    as a single unparseable entry rather than guessed.
    """
    form = form.strip()

    if form.startswith('{') and form.endswith('}'):
        sides = [_parse_single(s.strip()) for s in form[1:-1].split('/')]
        if all(s['parseable'] for s in sides):
            return sides
        return [{"case": None, "preposition": None, "parseable": False, "raw": form}]

    return [_parse_single(form)]


def build_index_from_rows(rows: Iterable[dict]) -> dict:
    """verb_lemma -> list of parsed argument-slot dicts, from raw TSV row dicts."""
    index: dict = {}
    for row in rows:
        if row.get('Rank') == PREDICATE_RANK:
            continue

        for parsed in parse_form(row['Form']):
            slot = {
                'constr_index': row['ConstrIndex'],
                'place': row['Place'],
                'case': parsed['case'],
                'preposition': parsed['preposition'],
                'parseable': parsed['parseable'],
                'raw_form': parsed['raw'],
                'role': row.get('Role'),
                'rank': row.get('Rank'),
                'sem_class': row.get('SemClass'),  # not yet mapped to Animacy -- see class docstring
            }

            for lemma in (l.strip() for l in row['KeyLexemes'].split(',')):
                if lemma:
                    index.setdefault(lemma, []).append(slot)

    return index


class FrameBankAdapter:
    """
    sem_class is exposed per-slot but NOT used as a lookup key -- its
    values are free-text semantic classes (e.g. 'лицо', 'абстрактный',
    'лицо; пропозиция'), not a clean Animate/Inanimate binary. Mapping
    it to UD's Animacy feature is a deliberate decision for later, not
    guessed here.
    """

    def __init__(self, dict_cx_items_path: str):
        # utf-8-sig: strips a UTF-8 BOM if present (plain 'utf-8' leaves
        # '\ufeff' merged into the first header name,
        # turning 'ConstrIndex' into '\ufeffConstrIndex' and breaking
        # every row['ConstrIndex'] lookup with a KeyError)
        with open(dict_cx_items_path, encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE)
            self.index = build_index_from_rows(reader)
        logger.info(f"Loaded FrameBank index: {len(self.index)} verb lemmas from {dict_cx_items_path}")

    def slots_for_verb(self, verb_lemma: str) -> list:
        """All parsed argument slots FrameBank records for this verb lemma."""
        return self.index.get(verb_lemma, [])

    def expected_cases(self, verb_lemma: str, preposition: str = None) -> set:
        """
        Cases FrameBank records for verb_lemma governed by preposition
        (None for a bare, prepositionless argument). Only parseable
        slots. Empty set if unattested -- caller decides how to treat
        that (e.g. skip rather than flag as an error). Can legitimately
        have more than one member (a verb+preposition pair attested
        with different cases across different constructions/senses, or
        a clean '{A / B}' alternation).
        """
        return {
            s['case'] for s in self.slots_for_verb(verb_lemma)
            if s['parseable'] and s['preposition'] == preposition
        }