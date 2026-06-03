"""
Text cleaning and normalisation pipeline.
Strips HTML, normalises whitespace, removes noise.
"""
import re
import unicodedata


# Patterns compiled once at import time for speed
_HTML_TAG = re.compile(r"<[^>]+>")
_URL = re.compile(r"https?://\S+|www\.\S+")
_EMAIL_ADDR = re.compile(r"\S+@\S+\.\S+")
_MULTI_SPACE = re.compile(r"\s+")
_SPECIAL = re.compile(r"[^\w\s.,!?'\"-]")
_REPEATED_PUNCT = re.compile(r"([!?.]){3,}")


def remove_html(text: str) -> str:
    return _HTML_TAG.sub(" ", text)


def remove_urls(text: str) -> str:
    return _URL.sub("[URL]", text)


def remove_emails(text: str) -> str:
    return _EMAIL_ADDR.sub("[EMAIL]", text)


def normalise_unicode(text: str) -> str:
    """Convert unicode to closest ASCII equivalent where possible."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def clean_text(text: str, lowercase: bool = True) -> str:
    """
    Full cleaning pipeline. Returns cleaned string.

    Steps:
      1. Strip HTML tags
      2. Remove URLs and email addresses
      3. Normalise unicode
      4. Remove non-essential special characters
      5. Collapse repeated punctuation (!!!!! → !)
      6. Collapse whitespace
      7. Optionally lowercase
    """
    if not text or not text.strip():
        return ""

    text = remove_html(text)
    text = remove_urls(text)
    text = remove_emails(text)
    text = normalise_unicode(text)
    text = _SPECIAL.sub(" ", text)
    text = _REPEATED_PUNCT.sub(r"\1", text)
    text = _MULTI_SPACE.sub(" ", text)
    text = text.strip()

    if lowercase:
        text = text.lower()

    return text


def truncate(text: str, max_chars: int = 2000) -> str:
    """Hard-truncate to avoid blowing LLM token budgets."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "…"
