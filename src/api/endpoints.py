"""
FastAPI application — all REST endpoints.

Run with:
    uvicorn src.api.endpoints:app --reload --port 8000
"""
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional
import datetime
import logging

from src.database import get_db, init_db, Feedback, TrendAlert
from src.tasks import process_feedback
from src.api.middleware import LoggingMiddleware, RateLimitMiddleware, require_api_key
from src.intelligence.trend_detector import get_category_stats
# Updated import route to match core folder layouts 
from src.actions.reports import generate_summary_report

logger = logging.getLogger(__name__)

# ── App setup ─────────────────────────────────────────────

app = FastAPI(
    title="Feedback Intelligence API",
    description="Ingest, process, and analyse user feedback at scale.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS Middleware Update ────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://multi-source-feedback-system.vercel.app"  # Added production frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Initialise DB tables on startup
init_db()


# ── Pydantic schemas ──────────────────────────────────────

class FeedbackIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000, description="Feedback text")
    source: Optional[str] = Field("api", description="Source identifier")


class FeedbackOut(BaseModel):
    id: int
    source: str
    raw_text: str
    category: str
    sentiment: str
    confidence: float
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class StatsOut(BaseModel):
    total: int
    hours: int
    categories: dict
    sentiments: dict
    sources: dict
    hourly: dict


# ── Endpoints ─────────────────────────────────────────────

@app.get("/health", tags=["system"])
def health():
    """Health check endpoint — returns 200 if server is up."""
    return {"status": "ok", "timestamp": datetime.datetime.utcnow().isoformat()}


@app.post("/feedback", tags=["feedback"], response_model=dict)
def submit_feedback(
    payload: FeedbackIn,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
):
    """
    Submit a single feedback item for async processing.
    Returns a task ID — check /feedback for results after a few seconds.
    """
    task = process_feedback.delay(payload.text, source=payload.source)
    logger.info(f"[API] Queued feedback task {task.id}")
    return {"status": "queued", "task_id": task.id}


@app.get("/feedback", tags=["feedback"])
def list_feedback(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
):
    """
    List feedback with optional filters.
    Supports pagination via limit/offset.
    """
    q = db.query(Feedback)

    if category:
        q = q.filter(Feedback.category == category)
    if sentiment:
        q = q.filter(Feedback.sentiment == sentiment)
    if source:
        q = q.filter(Feedback.source == source)

    total = q.count()
    items = q.order_by(Feedback.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": f.id,
                "source": f.source,
                "text": f.raw_text[:300],
                "category": f.category,
                "sentiment": f.sentiment,
                "confidence": f.confidence,
                "created_at": f.created_at.isoformat(),
            }
            for f in items
        ],
    }


@app.get("/feedback/{feedback_id}", tags=["feedback"])
def get_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
):
    """Get a single feedback item by ID."""
    item = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return {
        "id": item.id,
        "source": item.source,
        "raw_text": item.raw_text,
        "cleaned_text": item.cleaned_text,
        "category": item.category,
        "sentiment": item.sentiment,
        "confidence": item.confidence,
        "created_at": item.created_at.isoformat(),
        "processed_at": item.processed_at.isoformat() if item.processed_at else None,
    }


@app.get("/stats", tags=["analytics"])
def get_stats(
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
):
    """Return category/sentiment distribution for the last N hours."""
    return get_category_stats(db=db, hours=hours)


@app.get("/report", tags=["analytics"])
def get_report(
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
):
    """Generate a full AI-powered summary report."""
    return generate_summary_report(hours=hours, db=db)


@app.get("/alerts", tags=["analytics"])
def get_alerts(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
):
    """Return recent trend alerts."""
    alerts = (
        db.query(TrendAlert)
        .order_by(TrendAlert.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": a.id,
            "type": a.alert_type,
            "category": a.category,
            "count": a.count,
            "message": a.message,
            "created_at": a.created_at.isoformat(),
        }
    ]


@app.post("/ingest/batch", tags=["ingestion"])
def ingest_batch(
    payload: dict,
    _: None = Depends(require_api_key),
):
    """
    Batch ingest endpoint — accepts {"items": ["text1", "text2", ...]}
    Queues each item as a separate Celery task.
    """
    items = payload.get("items", [])
    if not isinstance(items, list) or len(items) == 0:
        raise HTTPException(status_code=400, detail="'items' must be a non-empty list")
    if len(items) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 items per batch")

    task_ids = []
    for text in items:
        if isinstance(text, str) and text.strip():
            task = process_feedback.delay(text, source="batch")
            task_ids.append(task.id)

    return {"status": "queued", "count": len(task_ids), "task_ids": task_ids[:10]}
