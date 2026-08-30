import logging
from ufal.udpipe import Model, Pipeline, ProcessingError

logger = logging.getLogger(__name__)

_WHITESPACE_EQUIVALENTS = str.maketrans({
    '\xa0': ' ',
    '\t': ' ',
    '\r': ' ',
    '\n': ' ',
})


class UdpipeAnalyzer:
    def __init__(self, model_path: str):
        logger.info(f"Loading UDPipe model from {model_path}")
        self.model = Model.load(str(model_path))
        if not self.model:
            logger.error("Failed to load UDPipe model!")
            raise RuntimeError(f"Failed to load UDPipe model from {model_path}")

        self.segmenter_pipeline = Pipeline(self.model, "tokenize", Pipeline.NONE, Pipeline.NONE, "conllu")
        self.analyzer_pipeline = Pipeline(self.model, "tokenize", Pipeline.DEFAULT, Pipeline.DEFAULT, "conllu")

    def segment_sentences(self, sanitized_text: str) -> list[dict]:
        """
        Segments a raw (already-sanitized) text block into individual
        sentences, and records each sentence's character offset within
        that text.

        Returns a list of dicts: {"text": str, "start_char": int, "end_char": int}.

        Callers (e.g. extraction_runner) MUST pass each sentence's
        start_char into extract_tokens(..., base_offset=...). Without
        this, token offsets from extract_tokens are relative to the
        individual sentence, not the full essay -- which silently
        breaks any comparison against a gold standard annotated on the
        full essay text, since offsets from different sentences would
        all start back near 0.
        """
        normalized_text = sanitized_text.translate(_WHITESPACE_EQUIVALENTS)

        error = ProcessingError()
        conllu_output = self.segmenter_pipeline.process(normalized_text, error)

        if error.occurred():
            message = f"UDPipe sentence segmentation failed: {error.message}"
            logger.error(message)
            raise RuntimeError(message)

        sentences = [
            line.split("# text = ")[1].strip()
            for line in conllu_output.split("\n")
            if line.startswith("# text = ")
        ]

        return self._attach_sentence_offsets(sentences, normalized_text)

    def _attach_sentence_offsets(self, sentences: list[str], full_text: str) -> list[dict]:
        current_index = 0
        result = []

        for sentence in sentences:
            start_char = full_text.find(sentence, current_index)

            if start_char == -1:
                error_msg = (
                    f"Sentence alignment failed: could not locate segmented "
                    f"sentence in source text after index {current_index}: "
                    f"'{sentence}'"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

            end_char = start_char + len(sentence)
            result.append({
                "text": sentence,
                "start_char": start_char,
                "end_char": end_char,
            })
            current_index = end_char

        return result

    def extract_tokens(self, sentence: str, base_offset: int = 0) -> list[dict]:
        """
        Analyzes a single sentence and returns deterministic syntactic
        tokens with character-exact offsets.

        base_offset should be the sentence's own start_char within the
        full essay (as returned by segment_sentences), so the resulting
        token offsets are essay-global rather than sentence-local.
        Defaults to 0 for standalone/single-sentence use.
        """
        normalized_sentence = sentence.translate(_WHITESPACE_EQUIVALENTS)

        error = ProcessingError()
        conllu_output = self.analyzer_pipeline.process(normalized_sentence, error)

        if error.occurred():
            message = f"UDPipe token analysis failed: {error.message}"
            logger.error(message)
            raise RuntimeError(message)

        # 1. Parse raw CoNLL-U into token dictionaries (filtering MWTs/Empty Nodes)
        tokens = self._parse_conllu_to_dicts(conllu_output)

        # 2. Attach absolute string offsets for Containment Logic alignment
        return self._attach_offsets(tokens, normalized_sentence, base_offset)

    def _parse_conllu_to_dicts(self, conllu_output: str) -> list[dict]:
        """
        Parses CoNLL-U format in a single O(N) pass.
        Strictly drops Multi-Word Tokens (MWTs) and Empty Nodes to ensure
        physical offset alignment mathematically succeeds.
        """
        tokens = []
        for line in conllu_output.split('\n'):
            if not line or line.startswith('#'):
                continue

            parts = line.split('\t')
            if len(parts) != 10:
                continue

            # DEFENSIVE PARSING: A standard physical token ID is purely numeric (e.g., '5').
            if not parts[0].isdigit():
                continue

            tokens.append({
                "id": parts[0],
                "text": parts[1],
                "lemma": parts[2],
                "upos": parts[3],
                "xpos": parts[4],
                "feats": parts[5],
                "head": parts[6],
                "deprel": parts[7],
                "deps": parts[8],
                "misc": parts[9]
            })
        return tokens

    def _attach_offsets(self, tokens: list[dict], raw_sentence: str, base_offset: int = 0) -> list[dict]:
        """
        Calculates start_char and end_char using a continuous sliding
        window, relative to raw_sentence, then shifts both by
        base_offset so they end up relative to the full essay when the
        caller supplies the sentence's own position (see extract_tokens).
        """
        current_index = 0

        for token in tokens:
            word = token["text"]
            start_char = raw_sentence.find(word, current_index)

            if start_char == -1:
                # Flawless failure state logging for thesis debugging
                error_msg = f"Alignment failed: '{word}' not found after index {current_index} in: {raw_sentence}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            end_char = start_char + len(word)

            # Attach directly to the dictionary matching the MystemAdapter schema
            token["start_char"] = start_char + base_offset
            token["end_char"] = end_char + base_offset

            current_index = end_char

        return tokens