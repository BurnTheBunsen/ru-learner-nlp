import logging
from pymystem3 import Mystem

logger = logging.getLogger(__name__)


class MystemAnalyzer:
    """
    Wraps pymystem3's Mystem to produce token dicts with character-exact
    offsets and a normalized 'is_uncertain' signal, isolating callers from
    Mystem's volatile raw JSON shape.
    """

    def __init__(self, mystem_bin: str = None):
        kwargs = {"mystem_bin": mystem_bin} if mystem_bin else {}
        logger.info(f"Loading Mystem (mystem_bin={mystem_bin or 'auto'})")
        self.mystem = Mystem(**kwargs)

    def analyze_text(self, sanitized_text: str) -> list[dict]:
        """
        Runs Mystem's analyze() and returns a list of dicts, one per
        fragment -- including whitespace/punctuation fragments. Callers
        that only want word-like tokens should filter on has_analysis.

        Each dict:
            text:          the literal fragment text
            start_char:    offset within sanitized_text
            end_char:      offset within sanitized_text
            has_analysis:  True if the raw fragment had an 'analysis' key
                           at all (whitespace/punctuation never do)
            analysis:      the raw list of candidate readings (lex/wt/gr/
                           qual), or None if has_analysis is False
            is_uncertain:  True if this fragment's morphology should NOT
                           be trusted as a confident dictionary match
                           (see class docstring)
        """
        raw_fragments = self.mystem.analyze(sanitized_text)

        tokens = []
        cursor = 0
        text_len = len(sanitized_text)

        for fragment in raw_fragments:
            if cursor >= text_len:
                # Past the end of the real input: this is the trailing
                # artifact fragment the mystem binary always appends (or
                # anything else that might follow it). Not real content.
                break

            frag_text = fragment.get("text", "")
            end = cursor + len(frag_text)

            if end > text_len:
                # Partial overrun but clip defensively rather than
                # trust it blindly if it ever does.
                frag_text = frag_text[: text_len - cursor]
                end = text_len

            has_analysis = "analysis" in fragment
            analysis = fragment.get("analysis") if has_analysis else None

            tokens.append({
                "text": frag_text,
                "start_char": cursor,
                "end_char": end,
                "has_analysis": has_analysis,
                "analysis": analysis,
                "is_uncertain": self._is_uncertain(has_analysis, analysis),
            })

            cursor = end

        return tokens

    @staticmethod
    def _is_uncertain(has_analysis: bool, analysis) -> bool:
        """
        See class docstring for the empirical basis. Not applicable (False)
        for non-word fragments (whitespace/punctuation), since "uncertain
        morphology" presumes there was a word to be uncertain about.
        """
        if not has_analysis:
            return False
        if not analysis:
            return True
        return all(reading.get("qual") == "bastard" for reading in analysis)