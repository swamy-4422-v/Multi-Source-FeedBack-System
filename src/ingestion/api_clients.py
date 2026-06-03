"""
Third-party API polling clients.
Each client fetches recent items and queues them for processing.

Supported sources (configure via .env):
  - INTERCOM_TOKEN   — Intercom conversations
  - ZENDESK_SUBDOMAIN / ZENDESK_EMAIL / ZENDESK_TOKEN — Zendesk tickets
"""
import os
import logging
import httpx

logger = logging.getLogger(__name__)

INTERCOM_TOKEN = os.getenv("INTERCOM_TOKEN", "")
ZENDESK_SUBDOMAIN = os.getenv("ZENDESK_SUBDOMAIN", "")
ZENDESK_EMAIL = os.getenv("ZENDESK_EMAIL", "")
ZENDESK_TOKEN = os.getenv("ZENDESK_TOKEN", "")


# ── Intercom ──────────────────────────────────────────────

def fetch_intercom_conversations(limit: int = 20) -> list[str]:
    """Fetch latest Intercom conversations and return body texts."""
    if not INTERCOM_TOKEN:
        logger.warning("[Intercom] Token not configured — skipping.")
        return []

    url = "https://api.intercom.io/conversations"
    headers = {
        "Authorization": f"Bearer {INTERCOM_TOKEN}",
        "Accept": "application/json",
    }
    params = {"per_page": limit, "order": "desc", "sort": "created_at"}

    texts = []
    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        for conv in resp.json().get("conversations", []):
            body = conv.get("conversation_message", {}).get("body", "")
            if body:
                texts.append(body)
        logger.info(f"[Intercom] Fetched {len(texts)} conversations")
    except Exception as e:
        logger.error(f"[Intercom] Error: {e}")
    return texts


# ── Zendesk ───────────────────────────────────────────────

def fetch_zendesk_tickets(limit: int = 20) -> list[str]:
    """Fetch latest Zendesk tickets and return description texts."""
    if not all([ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, ZENDESK_TOKEN]):
        logger.warning("[Zendesk] Credentials not configured — skipping.")
        return []

    url = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/tickets.json"
    auth = (f"{ZENDESK_EMAIL}/token", ZENDESK_TOKEN)
    params = {"per_page": limit, "sort_by": "created_at", "sort_order": "desc"}

    texts = []
    try:
        resp = httpx.get(url, auth=auth, params=params, timeout=10)
        resp.raise_for_status()
        for ticket in resp.json().get("tickets", []):
            desc = ticket.get("description", "")
            if desc:
                texts.append(desc)
        logger.info(f"[Zendesk] Fetched {len(texts)} tickets")
    except Exception as e:
        logger.error(f"[Zendesk] Error: {e}")
    return texts


# ── Orchestrator ─────────────────────────────────────────

def ingest_all_apis() -> dict:
    """Pull from all configured API sources and queue tasks."""
    from src.tasks import process_feedback

    results = {"intercom": 0, "zendesk": 0}

    intercom_texts = fetch_intercom_conversations()
    for text in intercom_texts:
        process_feedback.delay(text, source="intercom")
    results["intercom"] = len(intercom_texts)

    zendesk_texts = fetch_zendesk_tickets()
    for text in zendesk_texts:
        process_feedback.delay(text, source="zendesk")
    results["zendesk"] = len(zendesk_texts)

    return results