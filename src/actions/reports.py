"""
Report generator — produces JSON and text summaries of feedback data.
PDF generation is available if reportlab is installed (pip install reportlab).
"""
import os
import logging
import datetime
from collections import Counter

logger = logging.getLogger(__name__)


def generate_summary_report(hours: int = 24, db=None) -> dict:
    """
    Generate a structured summary report for the last N hours.
    Returns a dict suitable for JSON serialisation.
    """
    from src.database import SessionLocal, Feedback
    from src.intelligence.ai_prompts import summarise_feedback

    close_db = db is None
    if db is None:
        db = SessionLocal()

    try:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
        items = db.query(Feedback).filter(Feedback.created_at >= cutoff).all()

        if not items or len(items) == 0:
            return {"status": "no_data", "hours": hours, "total": 0}

        texts = [f.raw_text for f in items]
        categories = Counter(f.category for f in items)
        sentiments = Counter(f.sentiment for f in items)

        # AI summary (graceful degradation if OpenAI not configured)
        ai_summary = summarise_feedback(texts)

        # Top feedback samples per category
        samples = {}
        for cat in categories:
            cat_items = [f.raw_text[:200] for f in items if f.category == cat][:3]
            samples[cat] = cat_items

        total_count = len(items)
        report = {
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "period_hours": hours,
            "total": total_count,
            "categories": dict(categories.most_common()),
            "sentiments": dict(sentiments),
            "sentiment_ratio": {
                "positive_pct": round(sentiments.get("positive", 0) / total_count * 100, 1),
                "negative_pct": round(sentiments.get("negative", 0) / total_count * 100, 1),
                "neutral_pct": round(sentiments.get("neutral", 0) / total_count * 100, 1),
            },
            "ai_summary": ai_summary,
            "top_samples": samples,
        }

        logger.info(f"[Reports] Generated report: {total_count} items over {hours}h")
        return report

    finally:
        if close_db:
            db.close()


def generate_text_report(hours: int = 24) -> str:
    """Generate a plain-text version of the summary report."""
    report = generate_summary_report(hours)

    if report.get("status") == "no_data":
        return f"No feedback data in the last {hours} hours."

    lines = [
        f"FEEDBACK INTELLIGENCE REPORT",
        f"Generated: {report['generated_at']}",
        f"Period: last {hours} hours",
        f"{'='*50}",
        f"",
        f"TOTAL FEEDBACK: {report['total']}",
        f"",
        f"CATEGORIES:",
    ]
    for cat, count in report["categories"].items():
        pct = round(count / report["total"] * 100)
        lines.append(f"  {cat:15s} {count:4d}  ({pct}%)")

    lines += [
        f"",
        f"SENTIMENT:",
        f"  Positive: {report['sentiment_ratio']['positive_pct']}%",
        f"  Negative: {report['sentiment_ratio']['negative_pct']}%",
        f"  Neutral:  {report['sentiment_ratio']['neutral_pct']}%",
        f"",
        f"AI SUMMARY:",
        report.get("ai_summary", "Unavailable"),
        f"",
    ]

    return "\n".join(lines)


def save_report(path: str = "reports", hours: int = 24) -> str:
    """Save a JSON report to disk and return the file path."""
    import json

    os.makedirs(path, exist_ok=True)
    filename = f"report_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(path, filename)

    report = generate_summary_report(hours)
    with open(filepath, "w") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info(f"[Reports] Saved report to {filepath}")
    return filepath