"""
Trend detection — spots unusual spikes in feedback categories or sentiments
over rolling time windows and creates TrendAlert records.
"""
import logging
import datetime
from collections import Counter

logger = logging.getLogger(__name__)

# Spike threshold: alert if count in last window > N × average of previous windows
SPIKE_MULTIPLIER = float(2.0)
MIN_COUNT_TO_ALERT = int(3)  # ignore tiny counts

# Window sizes in minutes
SHORT_WINDOW_MINUTES = 30
LONG_WINDOW_MINUTES = 240


def _get_recent_feedback(db, minutes: int) -> list:
    """Fetch feedback created within the last `minutes` minutes."""
    from src.database import Feedback
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(minutes=minutes)
    return db.query(Feedback).filter(Feedback.created_at >= cutoff).all()


def detect_trends(db=None) -> list[dict]:
    """
    Compare category/sentiment counts in the SHORT_WINDOW vs LONG_WINDOW.
    Returns list of alert dicts. Also saves TrendAlert rows to DB.
    """
    from src.database import SessionLocal, TrendAlert

    close_db = db is None
    if db is None:
        db = SessionLocal()

    alerts = []
    try:
        short_items = _get_recent_feedback(db, SHORT_WINDOW_MINUTES)
        long_items = _get_recent_feedback(db, LONG_WINDOW_MINUTES)

        # Early exit check if database has no records in the long window
        if not long_items:
            if close_db:
                db.close()
            return []

        # Count by category
        short_cat = Counter(f.category for f in short_items)
        long_cat = Counter(f.category for f in long_items)

        # Expected rate in short window = long count × (short/long ratio)
        ratio = SHORT_WINDOW_MINUTES / LONG_WINDOW_MINUTES

        for cat, short_count in short_cat.items():
            if short_count < MIN_COUNT_TO_ALERT:
                continue
            long_count = long_cat.get(cat, 0)
            expected = max(long_count * ratio, 1)
            if short_count > expected * SPIKE_MULTIPLIER:
                message = (
                    f"Spike in '{cat}' feedback: {short_count} items in the last "
                    f"{SHORT_WINDOW_MINUTES} min (expected ~{expected:.1f})."
                )
                alert = {
                    "alert_type": "category_spike",
                    "category": cat,
                    "count": short_count,
                    "message": message,
                }
                alerts.append(alert)
                logger.warning(f"[Trend] {message}")

                row = TrendAlert(
                    alert_type="category_spike",
                    message=message,
                    category=cat,
                    count=short_count,
                )
                db.add(row)

        # Count negative sentiment spike
        short_neg = sum(1 for f in short_items if f.sentiment == "negative")
        long_neg = sum(1 for f in long_items if f.sentiment == "negative")
        expected_neg = max(long_neg * ratio, 1)

        if short_neg >= MIN_COUNT_TO_ALERT and short_neg > expected_neg * SPIKE_MULTIPLIER:
            message = (
                f"Negative sentiment spike: {short_neg} items in {SHORT_WINDOW_MINUTES} min."
            )
            alert = {
                "alert_type": "sentiment_spike",
                "category": "negative_sentiment",
                "count": short_neg,
                "message": message,
            }
            alerts.append(alert)
            logger.warning(f"[Trend] {message}")
            db.add(TrendAlert(
                alert_type="sentiment_spike",
                message=message,
                category="negative_sentiment",
                count=short_neg,
            ))

        db.commit()

    except Exception as e:
        logger.error(f"[Trend] Detection error: {e}")
        db.rollback()
    finally:
        if close_db:
            db.close()

    return alerts


def get_category_stats(db=None, hours: int = 24) -> dict:
    """
    Returns category and sentiment distribution for the last N hours.
    Used by the dashboard API.
    """
    from src.database import SessionLocal, Feedback
    close_db = db is None
    if db is None:
        db = SessionLocal()

    try:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
        items = db.query(Feedback).filter(Feedback.created_at >= cutoff).all()

        categories = Counter(f.category for f in items)
        sentiments = Counter(f.sentiment for f in items)
        sources = Counter(f.source for f in items)

        # Build hourly time series (last 24 h, 1-h buckets)
        hourly = {}
        for f in items:
            bucket = f.created_at.strftime("%Y-%m-%dT%H:00")
            hourly[bucket] = hourly.get(bucket, 0) + 1

        return {
            "total": len(items),
            "hours": hours,
            "categories": dict(categories),
            "sentiments": dict(sentiments),
            "sources": dict(sources),
            "hourly": dict(sorted(hourly.items())),
        }
    finally:
        if close_db:
            db.close()