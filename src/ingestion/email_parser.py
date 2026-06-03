"""
Email ingestion — polls an IMAP mailbox and extracts feedback text.
Configure IMAP_HOST, IMAP_USER, IMAP_PASS in .env to activate.

Usage:
    from src.ingestion.email_parser import fetch_emails
    emails = fetch_emails()          # returns list of plain-text strings
"""
import imaplib
import email
from email.header import decode_header
import os
import logging

logger = logging.getLogger(__name__)

IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
IMAP_USER = os.getenv("IMAP_USER", "")
IMAP_PASS = os.getenv("IMAP_PASS", "")
IMAP_FOLDER = os.getenv("IMAP_FOLDER", "INBOX")
MAX_EMAILS = int(os.getenv("EMAIL_BATCH_SIZE", "20"))


def _decode_str(value: str) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def _extract_body(msg) -> str:
    """Walk MIME parts and extract plain-text body."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(
                msg.get_content_charset() or "utf-8", errors="replace"
            )
    return ""


def fetch_emails(mark_seen: bool = True) -> list[dict]:
    """
    Connect to IMAP, fetch unseen emails, return list of
    {"subject": str, "body": str, "from": str} dicts.
    Returns [] if IMAP credentials are not configured.
    """
    if not IMAP_USER or not IMAP_PASS:
        logger.warning("[Email] IMAP credentials not configured — skipping.")
        return []

    results = []
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(IMAP_USER, IMAP_PASS)
        mail.select(IMAP_FOLDER)

        _, data = mail.search(None, "UNSEEN")
        ids = data[0].split()[-MAX_EMAILS:]  # take the latest N

        for uid in ids:
            _, msg_data = mail.fetch(uid, "(RFC822)")
            if not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            entry = {
                "from": _decode_str(msg.get("From", "")),
                "subject": _decode_str(msg.get("Subject", "")),
                "body": _extract_body(msg),
            }
            results.append(entry)

            if mark_seen:
                mail.store(uid, "+FLAGS", "\\Seen")

        mail.logout()
        logger.info(f"[Email] Fetched {len(results)} emails")
    except Exception as e:
        logger.error(f"[Email] IMAP error: {e}")

    return results


def ingest_emails():
    """Fetch emails and queue each one as a Celery task."""
    from src.tasks import process_feedback

    emails = fetch_emails()
    queued = 0
    for e in emails:
        text = f"Subject: {e['subject']}\n\n{e['body']}".strip()
        if text:
            process_feedback.delay(text, source="email")
            queued += 1
    return {"fetched": len(emails), "queued": queued}