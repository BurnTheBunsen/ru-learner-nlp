import pytest
from src.core.text_sanitizer import (
    remove_hidden_breaks,
    normalize_ellipses,
    mask_email,
    mask_url,
    collapse_spaces,
    sanitize_text
)

def test_remove_hidden_breaks():
    test_string = "Слово\tСлово\nСлово\rСлово\xa0Слово"
    expected_string = "Слово Слово Слово Слово Слово"
    assert remove_hidden_breaks(test_string) == expected_string

def test_normalize_ellipses():
    test_string = "Подожди...... что?"
    expected_string = "Подожди... что?"
    assert normalize_ellipses(test_string) == expected_string

def test_mask_email():
    test_string = "Свяжитесь с admin@university.ru для помощи."
    expected_string = "Свяжитесь с [EMAIL] для помощи."
    assert mask_email(test_string) == expected_string

def test_mask_url():
    test_string = "Посетите https://website.com или www.test.ru"
    expected_string = "Посетите [URL] или [URL]"
    assert mask_url(test_string) == expected_string

def test_collapse_spaces():
    raw_string = "Это   очень    много  пробелов."
    expected_result = "Это очень много пробелов."
    assert collapse_spaces(raw_string) == expected_result


def test_sanitize_text_applies_all_rules_in_sequence():
    raw_string = "  Смотри www.site.ru\n\tдля инфо.... Пиши user@mail.ru!!  "
    expected_result = "Смотри [URL] для инфо... Пиши [EMAIL]!!"
    assert sanitize_text(raw_string) == expected_result