import os

import pytest

from src.adapters.udpipe_adapter import UdpipeAnalyzer
from src.adapters.mystem_adapter import MystemAnalyzer
from src.adapters.framebank_adapter import FrameBankAdapter
from src.pipeline.extraction_runner import run_extraction_on_essay, write_tier1_csv, write_tier2_csv


UDPIPE_MODEL_PATH = os.environ.get("UDPIPE_MODEL_PATH", r"D:\RIDGE LASSO POLY\ru-learner-nlp\models\russian-syntagrus-ud-2.5-191206.udpipe")
MYSTEM_BIN = os.environ.get("MYSTEM_BIN")
FRAMEBANK_DICT_PATH = os.environ.get(
    "FRAMEBANK_DICT_PATH", "data/framebank/framebank_dict_cx_items.txt"
)

pytestmark = pytest.mark.skipif(
    not UDPIPE_MODEL_PATH,
    reason="UDPIPE_MODEL_PATH not set -- skipping real-bindings integration test, per project convention",
)


# Small, deliberately mixed synthetic essay -- some constructions expected
# to be correct, some deliberately wrong, covering both hypotheses. NOT
# real learner data (§7 item 7 still open) -- this is the "test the
# pipeline on simulated text before real essays arrive" step.
SYNTHETIC_ESSAY = """
Она умна. Он не видит стола. Большая книга лежит на столе.
Студент читает книгу. Стол был большой. Он взял свою книгу. Она умён.
"""


@pytest.fixture(scope="module")
def real_adapters():
    if not os.path.exists(FRAMEBANK_DICT_PATH):
        pytest.skip(f"FrameBank dict not found at {FRAMEBANK_DICT_PATH} -- set FRAMEBANK_DICT_PATH")
    udpipe = UdpipeAnalyzer(UDPIPE_MODEL_PATH)
    mystem = MystemAnalyzer(MYSTEM_BIN)
    framebank = FrameBankAdapter(FRAMEBANK_DICT_PATH)
    return udpipe, mystem, framebank


def test_runs_end_to_end_without_raising(real_adapters):
    udpipe, mystem, framebank = real_adapters
    # Should not raise -- first real confirmation the whole chain
    # (sanitize -> segment -> extract_tokens -> analyze_text -> exclude
    # -> extract+decide both hypotheses) actually connects correctly
    # against real bindings, not just mocked interfaces.
    result = run_extraction_on_essay("synthetic_1", SYNTHETIC_ESSAY, udpipe, mystem, framebank)
    assert "tier1_rows" in result
    assert "tier2_row" in result


def test_produces_rows_for_both_hypotheses(real_adapters):
    udpipe, mystem, framebank = real_adapters
    result = run_extraction_on_essay("synthetic_1", SYNTHETIC_ESSAY, udpipe, mystem, framebank)
    hypotheses_seen = {r["hypothesis"] for r in result["tier1_rows"]}
    assert "H1_gender" in hypotheses_seen
    assert "H2_case" in hypotheses_seen


def test_tier2_row_has_sane_values(real_adapters):
    udpipe, mystem, framebank = real_adapters
    result = run_extraction_on_essay("synthetic_1", SYNTHETIC_ESSAY, udpipe, mystem, framebank)
    tier2 = result["tier2_row"]
    assert tier2["num_sentences"] > 0
    assert tier2["E_case_per_1k"] >= 0
    # Confirms error detection actually fires on real bindings, not
    # just correct/no_data paths -- "Она умён." is a deliberate
    # mismatch. >= 0 alone would pass even if detection were broken.
    assert tier2["E_gender_per_1k"] > 0


def test_print_full_output_for_manual_inspection(real_adapters, capsys):
    """
    Not a real assertion-based test -- deliberately prints everything so
    the actual real-binding output can be eyeballed, the same way every
    scratchpad diagnostic this project has used works. Given how many
    real surprises earlier diagnostics turned up against mocked
    assumptions, the first real run of this file deserves a human look,
    not just a handful of assertions that might pass for the wrong
    reason.
    """
    udpipe, mystem, framebank = real_adapters
    result = run_extraction_on_essay("synthetic_1", SYNTHETIC_ESSAY, udpipe, mystem, framebank)

    with capsys.disabled():
        print("\n=== tier1_rows ===")
        for row in result["tier1_rows"]:
            print(row)
        print("\n=== tier2_row ===")
        print(result["tier2_row"])


def test_writes_real_csv_files(real_adapters, tmp_path):
    udpipe, mystem, framebank = real_adapters
    result = run_extraction_on_essay("synthetic_1", SYNTHETIC_ESSAY, udpipe, mystem, framebank)

    tier1_path = tmp_path / "tier1_token.csv"
    tier2_path = tmp_path / "tier2_essay.csv"
    write_tier1_csv(str(tier1_path), result["tier1_rows"])
    write_tier2_csv(str(tier2_path), [result["tier2_row"]])

    assert tier1_path.exists()
    assert tier2_path.exists()