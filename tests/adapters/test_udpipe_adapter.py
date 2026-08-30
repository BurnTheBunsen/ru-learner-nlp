import pytest
from unittest.mock import patch, MagicMock
from src.adapters.udpipe_adapter import UdpipeAnalyzer

# Fixtures
@pytest.fixture
@patch("src.adapters.udpipe_adapter.Model")
@patch("src.adapters.udpipe_adapter.Pipeline")
def analyzer(mock_pipeline, mock_model):
    """
    Mocks the heavy C++ UDPipe bindings so we can test
    the parsing and offset math in isolation.
    """
    mock_model.load.return_value = MagicMock()
    # Instantiate with a dummy path; the model is mocked
    return UdpipeAnalyzer("dummy_path.udpipe")


# Test Cases
def test_parses_standard_conllu_to_dicts(analyzer):
    # Simulated output for "Я люблю"
    mock_conllu = (
        "# text = Я люблю\n"
        "1\tЯ\tя\tPRON\t_\tCase=Nom\t2\tnsubj\t_\t_\n"
        "2\tлюблю\tлюбить\tVERB\t_\tAspect=Imp\t0\troot\t_\t_\n"
    )

    tokens = analyzer._parse_conllu_to_dicts(mock_conllu)

    assert len(tokens) == 2
    assert tokens[0]["id"] == "1"
    assert tokens[0]["text"] == "Я"
    assert tokens[0]["feats"] == "Case=Nom"
    assert tokens[1]["deprel"] == "root"


def test_strictly_drops_empty_nodes(analyzer):
    # Simulated output containing an Empty Node (8.1)
    # which UDPipe inserts for elided verbs in learner Russian.
    mock_conllu = (
        "# text = Он в Москву\n"
        "1\tОн\tон\tPRON\t_\t_\t2\tnsubj\t_\t_\n"
        "8.1\tпоехал\tпоехать\tVERB\t_\t_\t_\t_\t_\t_\n"
        "2\tв\tв\tADP\t_\t_\t3\tcase\t_\t_\n"
        "3\tМоскву\tМосква\tPROPN\t_\t_\t0\troot\t_\t_\n"
    )

    tokens = analyzer._parse_conllu_to_dicts(mock_conllu)

    # It must completely ignore "8.1" and return exactly 3 tokens
    assert len(tokens) == 3
    assert tokens[0]["id"] == "1"
    assert tokens[1]["id"] == "2"
    assert tokens[2]["id"] == "3"


def test_attaches_correct_character_offsets(analyzer):
    # Simulating the parsed dictionary array
    tokens = [
        {"text": "диван"},
        {"text": "-"},
        {"text": "кровать"}
    ]
    raw_sentence = "диван-кровать"

    processed = analyzer._attach_offsets(tokens, raw_sentence)

    assert processed[0]["start_char"] == 0
    assert processed[0]["end_char"] == 5

    assert processed[1]["start_char"] == 5
    assert processed[1]["end_char"] == 6

    assert processed[2]["start_char"] == 6
    assert processed[2]["end_char"] == 13


def test_attaches_offsets_for_repeated_words(analyzer):
    # Text: "да да да"
    tokens = [
        {"text": "да"},
        {"text": "да"},
        {"text": "да"}
    ]
    raw_sentence = "да да да"

    processed = analyzer._attach_offsets(tokens, raw_sentence)

    # First "да"
    assert processed[0]["start_char"] == 0
    assert processed[0]["end_char"] == 2

    # Second "да" - Must jump the space and not reuse index 0
    assert processed[1]["start_char"] == 3
    assert processed[1]["end_char"] == 5

    # Third "да"
    assert processed[2]["start_char"] == 6
    assert processed[2]["end_char"] == 8

def test_extract_tokens_returns_tokens_with_offsets(analyzer):
    mock_conllu = (
        "# text = Я люблю\n"
        "1\tЯ\tя\tPRON\t_\tCase=Nom\t2\tnsubj\t_\t_\n"
        "2\tлюблю\tлюбить\tVERB\t_\tAspect=Imp\t0\troot\t_\t_\n"
    )
    analyzer.analyzer_pipeline.process.return_value = mock_conllu

    tokens = analyzer.extract_tokens("Я люблю")

    assert tokens[0]["start_char"] == 0
    assert tokens[1]["start_char"] == 2

def test_drops_lines_with_wrong_column_count(analyzer):
    mock_conllu = (
        "# text = test\n"
        "1\tтест\n"  # truncated/malformed line
        "2\tслово\tслово\tNOUN\t_\t_\t0\troot\t_\t_\n"
    )
    tokens = analyzer._parse_conllu_to_dicts(mock_conllu)
    assert len(tokens) == 1
    assert tokens[0]["id"] == "2"

def test_raises_value_error_on_corrupted_alignment(analyzer):
    tokens = [{"text": "фантом"}]
    raw_sentence = "Здесь нет этого слова"

    # The sliding window must violently crash if it cannot find the physical word
    with pytest.raises(ValueError, match="Alignment failed: 'фантом' not found"):
        analyzer._attach_offsets(tokens, raw_sentence)