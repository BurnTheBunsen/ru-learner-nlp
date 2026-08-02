import re
import string

# Constants
PATTERN_WHITESPACE = re.compile(r'[\xa0\t\n\r]+')
PATTERN_ELLIPSIS = re.compile(r'\.{2,}')
PATTERN_EMAIL = re.compile(r'[\w.+-]+@[\w-]+\.\w{2,}')
PATTERN_URL = re.compile(r'(?:http[s]?://|www\.)[\w\-./?=&%]+')
PATTERN_MULTIPLE_SPACES = re.compile(r' +')

def remove_hidden_breaks(raw_text:str) -> str:
    return PATTERN_WHITESPACE.sub(' ', raw_text)

def normalize_ellipses(raw_text:str) -> str:
    return PATTERN_ELLIPSIS.sub('...', raw_text)

def mask_email(raw_text:str) -> str:
    return PATTERN_EMAIL.sub('[EMAIL]', raw_text)

def mask_url(raw_text:str) -> str:
    return PATTERN_URL.sub('[URL]', raw_text)

def collapse_spaces(raw_text:str) -> str:
    return PATTERN_MULTIPLE_SPACES.sub(' ', raw_text)

def sanitize_text(raw_text:str) -> str:
    pipeline_steps = [
        remove_hidden_breaks,
        normalize_ellipses,
        mask_email,
        mask_url,
        collapse_spaces
    ]

    processed_text = str(raw_text)
    for step in pipeline_steps:
        processed_text = step(processed_text)

    return processed_text.strip()