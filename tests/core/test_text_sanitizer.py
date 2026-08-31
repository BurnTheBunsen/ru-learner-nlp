import pytest
from src.core.text_sanitizer import (
    normalize_unicode,
    strip_soft_hyphens,
    remove_hidden_breaks,
    normalize_ellipses,
    normalize_repeated_hyphens,
    mask_email,
    mask_url,
    collapse_spaces,
    sanitize_text
)


def test_normalize_unicode_converts_to_nfc():
    # 'й' as NFD (base letter 'и' + combining breve U+0306) vs. its
    # precomposed NFC form (U+0439). Visually identical, byte-different.
    decomposed = "и\u0306"
    precomposed = "\u0439"
    assert normalize_unicode(decomposed) == precomposed


def test_remove_hidden_breaks():
    test_string = "Слово\tСлово\nСлово\rСлово\xa0Слово"
    expected_string = "Слово Слово Слово Слово Слово"
    assert remove_hidden_breaks(test_string) == expected_string


def test_strip_soft_hyphens():
    # Regression test: found leaking through unstripped in the real
    # diagnostic run, sitting inside a token as "интер\xadнет".
    test_string = "интер\u00adнет-магазин"
    expected_string = "интернет-магазин"
    assert strip_soft_hyphens(test_string) == expected_string


def test_strip_soft_hyphens_no_op_when_absent():
    test_string = "обычное слово без мягкого переноса"
    assert strip_soft_hyphens(test_string) == test_string


def test_normalize_repeated_hyphens_collapses_doubled_hyphen():
    # Regression test: "интернет--магазине" (keystroke-repeat typo) was
    # confirmed via the real diagnostic run to tokenize as two separate
    # bare-hyphen PUNCT tokens rather than crashing -- harmless, but
    # noise the pipeline doesn't need to carry through.
    test_string = "интернет--магазине"
    expected_string = "интернет-магазине"
    assert normalize_repeated_hyphens(test_string) == expected_string


def test_normalize_repeated_hyphens_collapses_longer_runs():
    test_string = "странно----написано"
    expected_string = "странно-написано"
    assert normalize_repeated_hyphens(test_string) == expected_string


def test_normalize_repeated_hyphens_preserves_single_hyphen():
    test_string = "социально-экономическая"
    assert normalize_repeated_hyphens(test_string) == test_string


def test_normalize_ellipses_collapses_excessive_dots():
    test_string = "Подожди...... что?"
    expected_string = "Подожди... что?"
    assert normalize_ellipses(test_string) == expected_string


def test_normalize_ellipses_preserves_double_dot():
    test_string = "Занятие началось.. потом закончилось."
    assert normalize_ellipses(test_string) == test_string


def test_mask_email():
    test_string = "Свяжитесь с admin@university.ru для помощи."
    expected_string = "Свяжитесь с [EMAIL] для помощи."
    assert mask_email(test_string) == expected_string


def test_mask_email_preserves_trailing_punctuation():
    test_string = "Пишите на admin@site.ru, если что."
    expected_string = "Пишите на [EMAIL], если что."
    assert mask_email(test_string) == expected_string


def test_mask_url():
    test_string = "Посетите https://website.com или www.test.ru"
    expected_string = "Посетите [URL] или [URL]"
    assert mask_url(test_string) == expected_string


def test_mask_url_preserves_trailing_sentence_punctuation():
    # Regression test: PATTERN_URL's character class includes '.', so a
    # naive match on "www.site.ru." would swallow the sentence-final
    # period along with the URL.
    test_string = "Заходите на www.site.ru. Хорошего дня!"
    expected_string = "Заходите на [URL]. Хорошего дня!"
    assert mask_url(test_string) == expected_string


def test_mask_url_handles_embedded_credentials():
    test_string = "Ссылка: http://user@site.com/page для входа."
    expected_string = "Ссылка: [URL] для входа."
    assert mask_url(test_string) == expected_string


def test_collapse_spaces():
    raw_string = "Это   очень    много  пробелов."
    expected_result = "Это очень много пробелов."
    assert collapse_spaces(raw_string) == expected_result


def test_sanitize_text_applies_all_rules_in_sequence():
    raw_string = "  Смотри www.site.ru\n\tдля инфо.... Пиши user@mail.ru!!  "
    expected_result = "Смотри [URL] для инфо... Пиши [EMAIL]!!"
    assert sanitize_text(raw_string) == expected_result


def test_sanitize_text_preserves_sentence_boundary_after_url():
    # This is the case that would previously break UDPipe's downstream
    # sentence segmentation: the period after the URL must survive.
    raw_string = "Смотри www.site.ru. Потом пиши."
    expected_result = "Смотри [URL]. Потом пиши."
    assert sanitize_text(raw_string) == expected_result


def test_sanitize_text_normalizes_unicode_form():
    decomposed = "и\u0306" + "олк"  # decomposed 'й' + "олк" -> "йолк"
    result = sanitize_text(decomposed)
    assert result == "\u0439олк"


def test_sanitize_text_strips_soft_hyphen_and_collapses_doubled_hyphen():
    raw = "Я купил это в интер\u00adнет--магазине."
    expected = "Я купил это в интернет-магазине."
    assert sanitize_text(raw) == expected