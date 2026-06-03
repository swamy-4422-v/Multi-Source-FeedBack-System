"""
Sentiment analyser.

Tier 1 (default): fast keyword-based scoring — zero dependencies, runs instantly.
Tier 2 (optional): transformers pipeline — more accurate, requires GPU/CPU warmup.

Set USE_TRANSFORMERS=true in .env to enable Tier 2.
"""
import os
import logging

logger = logging.getLogger(__name__)

USE_TRANSFORMERS = os.getenv("USE_TRANSFORMERS", "false").lower() == "true"

# ── Tier 1: keyword scorer ────────────────────────────────

POSITIVE_WORDS = {
    "good", "great", "love", "excellent", "amazing", "awesome", "fantastic",
    "perfect", "happy", "pleased", "satisfied", "helpful", "easy", "fast",
    "reliable", "recommend", "outstanding", "brilliant", "superb", "thanks",
    "thank", "wonderful", "best", "smooth", "intuitive", "clean",
}

# Added critical missing baseline negation metrics to balance keyword matrix
NEGATIVE_WORDS = {
    "bad", "poor", "hate", "terrible", "awful", "worst", "broken", "slow",
    "crash", "error", "bug", "useless", "frustrating", "annoying", "confusing",
    "difficult", "ugly", "expensive", "disappointed", "fail", "failure",
    "problem", "issue", "wrong", "missing", "stuck", "lost", "angry",
}

INTENSIFIERS = {"very", "really", "extremely", "absolutely", "totally", "so"}
NEGATORS = {"not", "no", "never", "don't", "didn't", "won't", "can't", "isn't", "wasn't"}


def _keyword_sentiment(text: str) -> tuple[str, float]:
    """
    Returns (label, confidence) using weighted keyword matching.
    Accounts for negators and intensifiers.
    """
    words = text.lower().split()
    score = 0.0
    i = 0

    while i < len(words):
        word = words[i].strip(".,!?")
        multiplier = 1.0

        # look back for negator
        if i > 0 and words[i - 1].strip(".,") in NEGATORS:
            multiplier = -1.0

        # look back for intensifier
        if i > 0 and words[i - 1].strip(".,") in INTENSIFIERS:
            multiplier *= 1.5

        if word in POSITIVE_WORDS:
            score += 1.0 * multiplier
        elif word in NEGATIVE_WORDS:
            score -= 1.0 * multiplier

        i += 1

    if score > 0:
        label = "positive"
        confidence = min(score / max(len(words) * 0.1, 1), 1.0)
    elif score < 0:
        label = "negative"
        confidence = min(abs(score) / max(len(words) * 0.1, 1), 1.0)
    else:
        label = "neutral"
        confidence = 0.5

    return label, round(confidence, 3)


# ── Tier 2: transformers pipeline ────────────────────────

_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        from transformers import pipeline
        logger.info("[Analyzer] Loading transformers sentiment pipeline...")
        _pipeline = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
            truncation=True,
            max_length=512,
        )
        logger.info("[Analyzer] Pipeline ready.")
    return _pipeline


def _transformers_sentiment(text: str) -> tuple[str, float]:
    try:
        pipe = _get_pipeline()
        result = pipe(text[:512])[0]
        label = result["label"].lower()          # POSITIVE / NEGATIVE
        if label not in ("positive", "negative"):
            label = "neutral"
        return label, round(result["score"], 3)
    except Exception as e:
        logger.error(f"[Analyzer] Transformers error: {e} — falling back to keyword")
        return _keyword_sentiment(text)


# ── Public API ────────────────────────────────────────────

def analyze_sentiment(text: str) -> tuple[str, float]:
    """
    Returns (sentiment_label, confidence_score).
    sentiment_label: "positive" | "negative" | "neutral"
    confidence_score: 0.0 – 1.0
    """
    if not text or not text.strip():
        return "neutral", 0.0

    if USE_TRANSFORMERS:
        return _transformers_sentiment(text)
    return _keyword_sentiment(text)