"""
Webhook ingestion — receives POST payloads from external services
(Typeform, Intercom, Zendesk, custom forms, etc.) and queues them.
"""
from fastapi import APIRouter, Request, HTTPException, Header
from src.tasks import process_feedback
import hashlib
import hmac
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingestion"])

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify HMAC-SHA256 signature for trusted webhook sources."""
    if not WEBHOOK_SECRET:
        return True  # skip verification in dev
    expected = hmac.new(
        WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature or "")


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    x_signature: str = Header(default=""),
):
    """Generic webhook endpoint. Accepts JSON with a 'text' field."""
    body_bytes = await request.body()

    if WEBHOOK_SECRET and not verify_signature(body_bytes, x_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    text = body.get("text") or body.get("message") or body.get("content", "")

    if not str(text).strip():
        raise HTTPException(status_code=400, detail="No text content found")

    task = process_feedback.delay(str(text), source="webhook")
    logger.info(f"[Webhook] Queued task {task.id}")
    return {"status": "queued", "task_id": task.id}


@router.post("/typeform")
async def receive_typeform(request: Request):
    """Typeform-specific webhook format."""
    body = await request.json()
    answers = body.get("form_response", {}).get("answers", [])
    text_parts = [
        str(a.get("text", "")) for a in answers if a.get("type") == "text"
    ]
    text = " ".join(text_parts).strip()
    if not text:
        return {"status": "skipped", "reason": "no text answers"}
    task = process_feedback.delay(text, source="typeform")
    return {"status": "queued", "task_id": task.id}