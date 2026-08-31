import re
import unicodedata

# Constants
PATTERN_WHITESPACE = re.compile(r'[\xa0\t\n\r]+')
PATTERN_SOFT_HYPHEN = re.compile(r'\u00ad')
PATTERN_ELLIPSIS = re.compile(r'\.{4,}')
PATTERN_REPEATED_HYPHEN = re.compile(r'-{2,}')
PATTERN_EMAIL = re.compile(r'[\w.+-]+@[\w-]+\.\w{2,}')
PATTERN_URL = re.compile(r'(?:http[s]?://|www\.)[\w\-./?=&%@]+')
PATTERN_MULTIPLE_SPACES = re.compile(r' +')

_TRAILING_PUNCTUATION = '.,;:!?'


def normalize_unicode(raw_text: str) -> str:
    """
    Forces a single Unicode normalization form (NFC) on the raw text.
    """
    return unicodedata.normalize('NFC', raw_text)


def strip_soft_hyphens(raw_text: str) -> str:
    """
    Removes invisible soft hyphens (U+00AD) entirely.
    """
    return PATTERN_SOFT_HYPHEN.sub('', raw_text)


def remove_hidden_breaks(raw_text: str) -> str:
    return PATTERN_WHITESPACE.sub(' ', raw_text)


def normalize_ellipses(raw_text: str) -> str:
    """
    Collapses runs of 4+ dots down to a standard 3-dot ellipsis.
    """
    return PATTERN_ELLIPSIS.sub('...', raw_text)


def normalize_repeated_hyphens(raw_text: str) -> str:
    """
    Collapses runs of 2+ consecutive hyphens down to a single hyphen.
    """
    return PATTERN_REPEATED_HYPHEN.sub('-', raw_text)


def _mask_with_boundary(pattern: re.Pattern, raw_text: str, placeholder: str) -> str:
    """
    Replaces every match of `pattern` with `placeholder`, but strips any
    trailing sentence punctuation caught inside the match back out into
    the surrounding text.
    """
    def _replace(match: re.Match) -> str:
        matched_text = match.group(0)
        trimmed = matched_text.rstrip(_TRAILING_PUNCTUATION)
        suffix = matched_text[len(trimmed):]
        return placeholder + suffix

    return pattern.sub(_replace, raw_text)


def mask_email(raw_text: str) -> str:
    return _mask_with_boundary(PATTERN_EMAIL, raw_text, '[EMAIL]')


def mask_url(raw_text: str) -> str:
    return _mask_with_boundary(PATTERN_URL, raw_text, '[URL]')


def collapse_spaces(raw_text: str) -> str:
    return PATTERN_MULTIPLE_SPACES.sub(' ', raw_text)


def sanitize_text(raw_text: str) -> str:
    # mask_url runs before mask_email: a URL that embeds credentials
    # (e.g. "http://user@site.com") would otherwise have its "user@site"
    # portion partially consumed by the email pattern first, leaving
    # mask_url to match a mangled remainder.
    pipeline_steps = [
        normalize_unicode,
        strip_soft_hyphens,
        remove_hidden_breaks,
        normalize_ellipses,
        normalize_repeated_hyphens,
        mask_url,
        mask_email,
        collapse_spaces,
    ]

    processed_text = str(raw_text)
    for step in pipeline_steps:
        processed_text = step(processed_text)

    return processed_text.strip()