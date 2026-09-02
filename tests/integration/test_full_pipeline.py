"""
End-to-end integration test: sanitize_text -> UdpipeAnalyzer ->
MystemAnalyzer -> align_tokens, run against REAL bindings on real
essay-like text.

Requires a real UDPipe model. Skipped automatically if not configured:

    export UDPIPE_MODEL_PATH=/path/to/model.udpipe
    export MYSTEM_BIN=/path/to/mystem   # optional, pymystem3 auto-downloads otherwise
    pytest tests/integration/ -v
"""

import os
from pathlib import Path
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
MODEL_PATH = os.environ.get("UDPIPE_MODEL_PATH")
MYSTEM_BIN = os.environ.get("MYSTEM_BIN")

pytestmark = pytest.mark.skipif(
    not MODEL_PATH,
    reason="Set UDPIPE_MODEL_PATH to a real .udpipe model file to run this integration test.",
)


@pytest.fixture(scope="module")
def pipeline():
    from src.core.text_sanitizer import sanitize_text
    from src.adapters.udpipe_adapter import UdpipeAnalyzer
    from src.adapters.mystem_adapter import MystemAnalyzer
    from src.core.geometric_aligner import align_tokens

    udpipe = UdpipeAnalyzer(MODEL_PATH)
    mystem = MystemAnalyzer(MYSTEM_BIN) if MYSTEM_BIN else MystemAnalyzer()

    def run(raw_text: str) -> dict:
        sanitized = sanitize_text(raw_text)

        sentences = udpipe.segment_sentences(sanitized)
        target_tokens = []
        for s in sentences:
            target_tokens.extend(udpipe.extract_tokens(s["text"], base_offset=s["start_char"]))

        boundary_tokens = mystem.analyze_text(sanitized)
        aligned = align_tokens(target_tokens, boundary_tokens)

        return {
            "sanitized": sanitized,
            "sentences": sentences,
            "target_tokens": target_tokens,
            "boundary_tokens": boundary_tokens,
            "aligned": aligned,
        }

    return run


# --- Baseline: does the chain even run, and do offsets survive it? ---

def test_clean_essay_runs_end_to_end(pipeline):
    result = pipeline("Я изучаю русский язык уже два года. Это очень интересно, но трудно.")
    assert len(result["target_tokens"]) > 0
    assert len(result["aligned"]) == len(result["target_tokens"])


def test_target_offsets_match_sanitized_text(pipeline):
    # Round-trip check through the WHOLE chain, including the sanitizer's
    # own text mutation -- not just each adapter tested in isolation.
    result = pipeline("Я изучаю русский язык уже два года.")
    sanitized = result["sanitized"]
    for token in result["target_tokens"]:
        assert sanitized[token["start_char"]:token["end_char"]] == token["text"]


def test_boundary_tokens_cover_sanitized_text_with_no_gaps(pipeline):
    # Confirms Mystem's gapless-coverage guarantee (which
    # geometric_aligner's zero-match error relies on) holds on real,
    # sanitizer-processed, multi-sentence text -- not just short toy
    # strings.
    raw = "Я изучаю русский язык уже два года. Это очень интересно, но трудно."
    result = pipeline(raw)
    reconstructed = "".join(t["text"] for t in result["boundary_tokens"])
    assert reconstructed == result["sanitized"]


# --- Multi-sentence offset coordination ---

def test_multi_sentence_essay_offsets_stay_consistent(pipeline):
    raw = (
        "Первое предложение об учёбе. Второе предложение о жизни в России. "
        "Третье предложение про будущие планы и работу."
    )
    result = pipeline(raw)

    assert len(result["sentences"]) == 3

    # Every target token across ALL sentences (not just the first) must
    # still round-trip against the full sanitized text.
    for token in result["target_tokens"]:
        assert result["sanitized"][token["start_char"]:token["end_char"]] == token["text"]

    # Every target token, from every sentence, must successfully align.
    # align_tokens() raises on any failure, so reaching this line without
    # exception across a 3-sentence essay is itself the assertion.
    assert len(result["aligned"]) == len(result["target_tokens"])



HYPHEN_CASES = {
    "loanword_prefix__internet_magazin": "Я купил это в интернет-магазине.",
    "loanword_prefix__web_sayt": "Открой веб-сайт компании.",
    "loanword_prefix__biznes_plan": "Мы написали бизнес-план.",
    "loanword_prefix__onlayn_kurs": "Я записался на онлайн-курс.",
    "loanword_prefix__press_konferentsiya": "Президент провёл пресс-конференцию.",
    "loanword_prefix__video_urok": "Посмотри этот видео-урок.",
    "compound_adj__sotsialno_ekonomicheskaya": "Это социально-экономическая проблема.",
    "compound_adj__istoriko_kulturny": "Это историко-культурный памятник.",
    "compound_adj__yugo_zapadny": "Ветер дует с юго-западной стороны.",
    "compound_adj__voenno_politicheskiy": "Это военно-политический союз.",
    "reduplication__ele_ele": "Он еле-еле успел на поезд.",
    "reduplication__chut_chut": "Добавь чуть-чуть соли.",
    "reduplication__davnym_davno": "Это было давным-давно.",
    "indefinite_particle__kto_to": "Кто-то постучал в дверь.",
    "indefinite_particle__chto_nibud": "Дай мне что-нибудь поесть.",
    "indefinite_particle__gde_to": "Он живёт где-то в Москве.",
    "indefinite_particle__koe_chto": "Я знаю кое-что важное.",
    "po_adverb__po_russki": "Я говорю по-русски.",
    "po_adverb__po_moyemu": "По-моему, это правильно.",
    "po_adverb__po_novomu": "Мы начали жить по-новому.",
    "apposition_noun__divan_krovat": "Мы купили диван-кровать.",
    "apposition_noun__vagon_restoran": "В поезде есть вагон-ресторан.",
    "apposition_noun__kreslo_krovat": "У нас есть кресло-кровать.",
    "color_adj__belo_siniy": "У него бело-синий флаг.",
    "color_adj__temno_zeleny": "Она купила тёмно-зелёное платье.",
    "proper_noun__saltykov_shchedrin": "Салтыков-Щедрин был писателем.",
    "numeric_range__10_20": "Страницы 10-20 важны.",
    "numeric_range__2023_2024": "Это данные за 2023-2024 год.",
    "learner_noise__spaced_hyphen": "Я купил это в интернет - магазине.",
    "learner_noise__soft_hyphen_embedded": "Я купил это в интер\u00adнет-магазине.",
    "learner_noise__doubled_hyphen": "Я купил это в интернет--магазине.",
    "chained__po_nastoyashchemu_to": "Он по-настоящему-то не хотел.",
}


@pytest.mark.parametrize("text", HYPHEN_CASES.values(), ids=HYPHEN_CASES.keys())
def test_all_known_hyphen_cases_align_without_error(pipeline, text):
    # No assertion on WHICH direction each case takes -- that's already
    # characterized. The assertion is simply that align_tokens doesn't
    # raise, for every one of the 30 real cases, including the 3
    # confirmed Direction-B ones (web_sayt, onlayn_kurs, saltykov_shchedrin)
    # that broke the original one-directional containment rule.
    result = pipeline(text)
    assert len(result["aligned"]) == len(result["target_tokens"])


def test_internet_magazine_tokenization_comma_vs_period(pipeline):
    comma_sentence = "Я купил это в интернет-магазине, вчера."
    period_sentence = "Я купил это в интернет-магазине."

    comma_result = pipeline(comma_sentence)
    period_result = pipeline(period_sentence)

    print(f"\ncomma variant targets:    {[t['text'] for t in comma_result['target_tokens']]}")
    print(f"comma variant boundary:   {[b['text'] for b in comma_result['boundary_tokens']]}")
    print(f"period variant targets:   {[t['text'] for t in period_result['target_tokens']]}")
    print(f"period variant boundary:  {[b['text'] for b in period_result['boundary_tokens']]}")

    assert len(comma_result["aligned"]) == len(comma_result["target_tokens"])
    assert len(period_result["aligned"]) == len(period_result["target_tokens"])


def test_confirmed_direction_b_cases_produce_multiple_boundary_tokens(pipeline):
    # Specifically re-confirms the fix: these three real words need
    # MORE THAN ONE boundary token per target, because UDPipe merges
    # them into one span while Mystem splits them into several.
    direction_b_cases = {
        "веб-сайт": "Открой веб-сайт компании.",
        "онлайн-курс": "Я записался на онлайн-курс.",
        "Салтыков-Щедрин": "Салтыков-Щедрин был писателем.",
    }
    for merged_word, sentence in direction_b_cases.items():
        result = pipeline(sentence)
        matching_targets = [t for t in result["target_tokens"] if merged_word in t["text"] or t["text"] in merged_word]
        assert matching_targets, f"couldn't find a target token for {merged_word!r} in {result['target_tokens']}"

        entry = next(e for e in result["aligned"] if e["target"] in matching_targets)
        assert len(entry["boundary_tokens"]) > 1, (
            f"{merged_word!r} was expected to need multiple boundary tokens "
            f"(confirmed Direction B case), got {entry['boundary_tokens']}"
        )


# --- Typos: does is_uncertain actually surface through the full chain? ---

def test_typo_essay_flags_uncertain_boundary_tokens(pipeline):
    raw = "Я люблю пить кофэ по утрам."  # "кофэ" is a real confirmed typo case
    result = pipeline(raw)

    uncertain_boundary_tokens = [b for b in result["boundary_tokens"] if b.get("is_uncertain")]
    assert uncertain_boundary_tokens, (
        f"expected at least one is_uncertain boundary token for a known typo, "
        f"got boundary_tokens={result['boundary_tokens']}"
    )


def test_bastard_guessed_typo_is_flagged_not_silently_trusted(pipeline):

    raw = "Хочешь коффе?"
    result = pipeline(raw)
    coffee_fragment = next(b for b in result["boundary_tokens"] if b["text"] == "коффе")
    assert coffee_fragment["is_uncertain"] is True


# --- Messy real-world text: sanitizer + both adapters + aligner together ---

def test_messy_whitespace_and_hyphen_essay_runs_clean(pipeline):
    raw = (
        "Я\u00a0купил\u00a0это в интер\u00adнет--магазине.  "
        "Потом я\tпошёл домой."
    )
    result = pipeline(raw)
    assert len(result["aligned"]) == len(result["target_tokens"])


def test_url_and_email_essay_runs_clean(pipeline):
    raw = "Смотри www.example.ru для информации. Пиши на student@university.ru!"
    result = pipeline(raw)
    assert len(result["aligned"]) == len(result["target_tokens"])
    # The mask placeholder itself must survive as real, alignable tokens.
    texts = [t["text"] for t in result["target_tokens"]]
    assert any("URL" in t for t in texts) or any("EMAIL" in t for t in texts)


# --- Essay-scale: multiple phenomena combined in one connected text ---
# Everything above tests one phenomenon at a time. Real essays don't --
# a typo sits next to a hyphenated compound sits next to irregular
# spacing, all interacting. Loaded from fixtures/*.txt rather than
# inlined, so a real anonymized essay can be dropped in later without
# touching any test code.

def _fixture_essays():
    return sorted(FIXTURES_DIR.glob("*.txt"))


@pytest.mark.parametrize("essay_path", _fixture_essays(), ids=lambda p: p.stem)
def test_fixture_essay_runs_end_to_end(pipeline, essay_path):
    raw = essay_path.read_text(encoding="utf-8")
    result = pipeline(raw)

    assert len(result["target_tokens"]) > 0
    assert len(result["aligned"]) == len(result["target_tokens"])

    for token in result["target_tokens"]:
        assert result["sanitized"][token["start_char"]:token["end_char"]] == token["text"]

    reconstructed = "".join(t["text"] for t in result["boundary_tokens"])
    assert reconstructed == result["sanitized"]

    multi_boundary_count = sum(1 for e in result["aligned"] if len(e["boundary_tokens"]) > 1)
    uncertain_count = sum(1 for b in result["boundary_tokens"] if b.get("is_uncertain"))
    print(
        f"\n{essay_path.name}: {len(result['sentences'])} sentences, "
        f"{len(result['target_tokens'])} targets, "
        f"{multi_boundary_count} multi-boundary alignments, "
        f"{uncertain_count} uncertain boundary tokens"
    )

    multi_boundary_targets = [e["target"]["text"] for e in result["aligned"] if len(e["boundary_tokens"]) > 1]
    uncertain_texts = [b["text"] for b in result["boundary_tokens"] if b.get("is_uncertain")]
    print(f"    multi-boundary targets: {multi_boundary_targets}")
    print(f"    uncertain boundary tokens: {uncertain_texts}")