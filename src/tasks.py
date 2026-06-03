from src.config import celery_app
from src.processing.cleaner import clean_text
from src.processing.analyzer import analyze_sentiment
from src.processing.categorizer import categorize
from src.database import SessionLocal, Feedback
import datetime
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def process_feedback(self, raw_text: str, source: str = "api"):
    """
    Main async task: clean → analyse → categorise → store.
    Retries up to 3 times on failure with exponential back-off.
    """
    db = SessionLocal()
    try:
        cleaned = clean_text(raw_text)
        sentiment, confidence = analyze_sentiment(cleaned)
        category = categorize(cleaned)

        row = Feedback(
            source=source,
            raw_text=raw_text,
            cleaned_text=cleaned,
            category=category,
            sentiment=sentiment,
            confidence=confidence,
            processed_at=datetime.datetime.utcnow(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)

        logger.info(f"[Task] Processed feedback id={row.id} cat={category} sent={sentiment}")
        return {"status": "done", "id": row.id, "category": category, "sentiment": sentiment}

    except Exception as exc:
        db.rollback()
        logger.error(f"[Task] Failed: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    finally:
        db.close()


@celery_app.task
def run_trend_detection():
    """
    Scheduled task — detect spikes in feedback categories.
    Called periodically (e.g. every 10 minutes via Celery Beat).
    """
    from src.intelligence.trend_detector import detect_trends
    alerts = detect_trends()
    logger.info(f"[Trend] Generated {len(alerts)} alerts")
    return alerts