"""
Pytest test suite.
Run with:  pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient
from src.api.endpoints import app
from src.processing.cleaner import clean_text
from src.processing.analyzer import analyze_sentiment
from src.processing.categorizer import categorize

client = TestClient(app)


# ── Health ────────────────────────────────────────────────

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── Feedback submission ───────────────────────────────────

def test_submit_feedback_returns_queued():
    r = client.post("/feedback", json={"text": "The app is really great!"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "queued"
    assert "task_id" in data


def test_submit_empty_text_fails():
    r = client.post("/feedback", json={"text": ""})
    assert r.status_code == 422  # Pydantic min_length validation contract


def test_submit_with_source():
    r = client.post("/feedback", json={"text": "Login broken", "source": "typeform"})
    assert r.status_code == 200


# ── List feedback ─────────────────────────────────────────

def test_list_feedback():
    r = client.get("/feedback")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data


def test_list_feedback_with_filters():
    r = client.get("/feedback?category=bug&limit=10")
    assert r.status_code == 200


def test_list_feedback_pagination():
    r = client.get("/feedback?limit=5&offset=0")
    assert r.status_code == 200
    assert r.json()["limit"] == 5


# ── Stats ─────────────────────────────────────────────────

def test_stats_endpoint():
    r = client.get("/stats")
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "categories" in data
    assert "sentiments" in data


# ── Batch ingest ──────────────────────────────────────────

def test_batch_ingest():
    r = client.post("/ingest/batch", json={
        "items": ["App crashes", "Love the new feature", "Invoice wrong"]
    })
    assert r.status_code == 200
    assert r.json()["count"] == 3


def test_batch_ingest_empty_fails():
    r = client.post("/ingest/batch", json={"items": []})
    assert r.status_code == 400


# ── Processing unit tests ─────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("The app is <b>great</b>!!!", "the app is great !"),
    ("  Hello   World  ", "hello world"),
    ("Visit https://example.com for help", "visit url for help"),
])
def test_clean_text(text, expected):
    result = clean_text(text)
    assert result == expected


@pytest.mark.parametrize("text,expected_sentiment", [
    ("This product is excellent and I love it!", "positive"),
    ("The app keeps crashing and it's terrible", "negative"),
    ("I received my order", "neutral"),
])
def test_sentiment(text, expected_sentiment):
    sentiment, confidence = analyze_sentiment(text)
    assert sentiment == expected_sentiment
    assert 0.0 <= confidence <= 1.0


@pytest.mark.parametrize("text,expected_category", [
    ("The app crashes every time I open it", "bug"),
    ("Please add a dark mode option", "feature"),
    ("I was charged twice on my invoice", "billing"),
    ("How do I configure the settings?", "support"),
])
def test_categorize(text, expected_category):
    assert categorize(text) == expected_category


# ── 404 handling ──────────────────────────────────────────

def test_feedback_not_found():
    r = client.get("/feedback/99999999")
    assert r.status_code == 404