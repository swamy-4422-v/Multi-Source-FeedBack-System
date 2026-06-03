"""
Feedback categoriser.

Tier 1 (default): keyword matching — instant, no dependencies.
Tier 2 (optional): trained scikit-learn TF-IDF + LogReg model.

Set USE_ML_CATEGORIZER=true in .env to enable Tier 2 after training.
"""
import os
import logging

logger = logging.getLogger(__name__)

USE_ML = os.getenv("USE_ML_CATEGORIZER", "false").lower() == "true"
MODEL_PATH = os.getenv("MODEL_PATH", "models/classifier.pkl")

# ── Keyword rules ─────────────────────────────────────────

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "bug": [
        "error", "crash", "broken", "bug", "fail", "failure", "exception",
        "traceback", "not working", "doesn't work", "won't load", "freeze",
        "hang", "stuck", "glitch", "wrong result", "incorrect",
    ],
    "feature": [
        "add", "want", "suggest", "feature", "improve", "enhancement",
        "would like", "could you", "please add", "wish", "idea", "proposal",
        "request", "missing", "should have", "it would be nice",
    ],
    "billing": [
        "charge", "refund", "invoice", "payment", "price", "cost", "fee",
        "subscription", "cancel", "billing", "overcharged", "credit card",
        "receipt", "money", "paid", "plan",
    ],
    "performance": [
        "slow", "fast", "speed", "lag", "latency", "timeout", "loading",
        "performance", "response time", "heavy", "memory", "cpu",
    ],
    "support": [
        "help", "how do i", "how to", "setup", "configure", "install",
        "tutorial", "documentation", "guide", "question", "understand",
        "confused", "not sure", "explain",
    ],
    "security": [
        "security", "vulnerability", "hack", "breach", "password", "auth",
        "login", "access", "permission", "ssl", "certificate", "token",
    ],
}

PRIORITY_ORDER = ["bug", "security", "billing", "performance", "feature", "support"]


def _keyword_categorize(text: str) -> str:
    """Score each category by keyword hits; return highest-scoring."""
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[cat] = score

    if not scores:
        return "general"

    # Tie-break by priority order
    max_score = max(scores.values())
    candidates = [c for c, s in scores.items() if s == max_score]

    for cat in PRIORITY_ORDER:
        if cat in candidates:
            return cat

    return candidates[0]


# ── ML model (optional) ───────────────────────────────────

_model = None
_vectorizer = None


def _load_model():
    global _model, _vectorizer
    if _model is None:
        import pickle
        if not os.path.exists(MODEL_PATH):
            logger.warning(f"[Categorizer] Model not found at {MODEL_PATH} — using keywords.")
            return False
        with open(MODEL_PATH, "rb") as f:
            _vectorizer, _model = pickle.load(f)
        logger.info("[Categorizer] ML model loaded.")
    return True


def _ml_categorize(text: str) -> str:
    if not _load_model():
        return _keyword_categorize(text)
    try:
        X = _vectorizer.transform([text])
        return _model.predict(X)[0]
    except Exception as e:
        logger.error(f"[Categorizer] ML predict error: {e}")
        return _keyword_categorize(text)


# ── Training helper ───────────────────────────────────────

def train_model(texts: list[str], labels: list[str]) -> None:
    """
    Train and save the TF-IDF + LogisticRegression classifier.

    Example:
        train_model(
            texts=["app crashes on startup", "please add dark mode"],
            labels=["bug", "feature"]
        )
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    import pickle

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=10000, ngram_range=(1, 2))),
        ("clf", LogisticRegression(max_iter=1000, C=1.0)),
    ])
    pipe.fit(texts, labels)

    # Save (vectorizer, model) tuple for compatibility
    vectorizer = pipe.named_steps["tfidf"]
    clf = pipe.named_steps["clf"]

    with open(MODEL_PATH, "wb") as f:
        pickle.dump((vectorizer, clf), f)

    logger.info(f"[Categorizer] Model saved to {MODEL_PATH}")


# ── Public API ────────────────────────────────────────────

def categorize(text: str) -> str:
    """
    Returns category string:
    'bug' | 'feature' | 'billing' | 'performance' | 'support' | 'security' | 'general'
    """
    if not text or not text.strip():
        return "general"
    if USE_ML:
        return _ml_categorize(text)
    return _keyword_categorize(text)