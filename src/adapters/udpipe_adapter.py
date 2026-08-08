import logging
from ufal.udpipe import Model, Pipeline, ProcessingError

logger = logging.getLogger(__name__)

class UdpipeAnalyzer:
    def __init__(self, model_path: str):
        logger.info(f"Loading UDPipe model from {model_path}")
        self.model= Model.load(str(model_path))
        if not self.model:
            logger.error("Failed to load UDPipe model!")
            raise RuntimeError("Failed to load UDPipe model!")
        self.segmenter_pipeline = Pipeline(self.model, "tokenize", Pipeline.NONE, Pipeline.NONE, "conllu")
        self.analyzer_pipeline = Pipeline(self.model, "tokenize", Pipeline.DEFAULT, Pipeline.DEFAULT, "conllu" )

    def _parse_sentences_from_conllu(self, conllu:str) -> list[str]:
        lines = conllu.split("\n")
        return [
            line.split("# text = ")[1]
            for line in lines if line.startswith("# text = ")
        ]

    def segment_sentences(self, sanitized_text:str) -> list[str]:
        error = ProcessingError()
        conllu_output = self.segmenter_pipeline.process(sanitized_text, error)
        return self._parse_sentences_from_conllu(conllu_output)

    def extract_tokens(self, sentence: str) -> list[dict]:
        error = ProcessingError()
        conllu_output = self.analyzer_pipeline.process(sentence, error)
        words = self._extract_words_from_conllu(conllu_output)
        offsets = self._calculate_offsets(words, sentence)

        return self._build_token_dictionaries(conllu_output, offsets)

    def _extract_words_from_conllu(self, conllu_output:str) -> list[str]:
        lines = [line for line in conllu_output.split('\n') if line and not line.startswith('#')]
        return [line.split('\t')[1] for line in lines if len(line.split('\t')) > 1]

    def _calculate_offsets(self, words:list[str], raw_sentence:str) -> list[tuple[int, int]]:
        offsets = []
        current_index = 0

        for word in words:
            start_index = raw_sentence.find(word, current_index)
            end_index = start_index + len(word)
            offsets.append((start_index, end_index))
            current_index = end_index
        return offsets

    def _build_token_dictionaries(self, conllu_output: str, offsets: list[tuple[int, int]]) -> list[dict]:
        lines = [line for line in conllu_output.split('\n') if line and not line.startswith('#')]
        tokens = []
        for i, line in enumerate(lines):
            parts = line.split('\t')
            if len(parts) == 10:
                token_data = {
                    "id": parts[0],
                    "text": parts[1],
                    "lemma": parts[2],
                    "upos": parts[3],  # Universal Part of Speech
                    "xpos": parts[4],  # Language-specific Part of Speech
                    "feats": parts[5],  # Morphological features
                    "head": parts[6],  # ID of the parent token
                    "deprel": parts[7],  # Dependency relationship
                    "deps": parts[8],  # Enhanced dependency graph
                    "misc": parts[9],  # Spacing
                    "start_index": offsets[i][0],
                    "end_index": offsets[i][1]
                }
                tokens.append(token_data)
        return tokens
