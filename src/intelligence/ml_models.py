"""
ML model management — training, evaluation, and prediction.

Models stored in models/ directory as pickle files.
"""
import os
import pickle
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Pointing to the central models directory at root level
MODELS_DIR = Path(os.getenv("MODELS_DIR", "models"))
MODELS_DIR.mkdir(exist_ok=True)


# ── Sentiment model ───────────────────────────────────────

SENTIMENT_MODEL_PATH = MODELS_DIR / "sentiment_model.pkl"


def train_sentiment_model(texts: list[str], labels: list[str]) -> dict:
    """
    Train a TF-IDF + LogisticRegression sentiment classifier.
    labels must be: 'positive', 'negative', or 'neutral'

    Returns evaluation metrics.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    from sklearn.pipeline import Pipeline
    import numpy as np

    if len(texts) < 10:
        raise ValueError("Need at least 10 labelled examples to train.")

    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=15000, ngram_range=(1, 2),
                                   sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=1000, C=2.0, class_weight="balanced")),
    ])

    scores = cross_val_score(pipe, texts, labels, cv=min(5, len(texts) // 2),
                              scoring="f1_weighted")
    pipe.fit(texts, labels)

    with open(SENTIMENT_MODEL_PATH, "wb") as f:
        pickle.dump(pipe, f)

    metrics = {
        "f1_mean": round(float(np.mean(scores)), 3),
        "f1_std": round(float(np.std(scores)), 3),
        "samples": len(texts),
        "model_path": str(SENTIMENT_MODEL_PATH),
    }
    logger.info(f"[ML] Sentiment model trained: {metrics}")
    return metrics


def predict_sentiment(text: str) -> tuple[str, float]:
    """Predict sentiment using trained model. Falls back to keyword analyser."""
    if not SENTIMENT_MODEL_PATH.exists():
        from src.processing.analyzer import _keyword_sentiment
        return _keyword_sentiment(text)
    try:
        with open(SENTIMENT_MODEL_PATH, "rb") as f:
            pipe = pickle.load(f)
        label = pipe.predict([text])[0]
        proba = pipe.predict_proba([text])[0]
        confidence = round(float(max(proba)), 3)
        return label, confidence
    except Exception as e:
        logger.error(f"[ML] Predict error: {e}")
        from src.processing.analyzer import _keyword_sentiment
        return _keyword_sentiment(text)


# ── Category model ────────────────────────────────────────

# Updated to match the expected path name in categorizer.py
CATEGORY_MODEL_PATH = MODELS_DIR / "classifier.pkl"


def train_category_model(texts: list[str], labels: list[str]) -> dict:
    """Train a category classifier."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    from sklearn.pipeline import Pipeline
    import numpy as np

    if len(texts) < 10:
        raise ValueError("Need at least 10 labelled examples to train.")

    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=15000, ngram_range=(1, 2))),
        ("clf", LogisticRegression(max_iter=1000, C=1.0, class_weight="balanced")),
    ])
    scores = cross_val_score(pipe, texts, labels,
                              cv=min(5, len(texts) // 2), scoring="f1_weighted")
    pipe.fit(texts, labels)

    # Deconstruct and save as tuple to match the load structure in categorizer.py
    vectorizer = pipe.named_steps["tfidf"]
    clf = pipe.named_steps["clf"]

    with open(CATEGORY_MODEL_PATH, "wb") as f:
        pickle.dump((vectorizer, clf), f)

    metrics = {
        "f1_mean": round(float(np.mean(scores)), 3),
        "f1_std": round(float(np.std(scores)), 3),
        "samples": len(texts),
        "model_path": str(CATEGORY_MODEL_PATH),
    }
    logger.info(f"[ML] Category model trained: {metrics}")
    return metrics


def predict_category(text: str) -> str:
    """Predict category using trained model. Falls back to keyword categoriser."""
    if not CATEGORY_MODEL_PATH.exists():
        from src.processing.categorizer import _keyword_categorize
        return _keyword_categorize(text)
    try:
        with open(CATEGORY_MODEL_PATH, "rb") as f:
            vectorizer, model = pickle.load(f)
        X = vectorizer.transform([text])
        return model.predict(X)[0]
    except Exception as e:
        logger.error(f"[ML] Category predict error: {e}")
        from src.processing.categorizer import _keyword_categorize
        return _keyword_categorize(text)


# ── Model info ────────────────────────────────────────────

def list_models() -> list[dict]:
    """Return metadata about all saved models."""
    result = []
    for path in MODELS_DIR.glob("*.pkl"):
        stat = path.stat()
        result.append({
            "name": path.name,
            "path": str(path),
            "size_kb": round(stat.st_size / 1024, 1),
        })
    return result