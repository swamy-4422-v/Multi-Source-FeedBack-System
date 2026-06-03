"""
Alert system — sends notifications via Slack, email, or webhook
when trends or high-urgency feedback are detected.

Configure in .env:
  SLACK_WEBHOOK_URL    — Slack incoming webhook
  ALERT_EMAIL_TO       — recipient email
  ALERT_EMAIL_FROM     — sender email (requires SMTP settings)
"""
import os
import json
import logging
import httpx

logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")


# ── Slack ─────────────────────────────────────────────────

def send_slack_alert(message: str, category: str = "", urgency: str = "medium") -> bool:
    """Send a Slack message via incoming webhook. Returns True on success."""
    if not SLACK_WEBHOOK_URL:
        logger.info(f"[Alerts] Slack not configured. Message: {message}")
        return False

    colour = {"high": "#e74c3c", "medium": "#f39c12", "low": "#2ecc71"}.get(urgency, "#95a5a6")
    emoji = {"high": ":rotating_light:", "medium": ":warning:", "low": ":information_source:"}.get(urgency, "")

    payload = {
        "attachments": [{
            "color": colour,
            "title": f"{emoji} Feedback Intelligence Alert",
            "text": message,
            "fields": [
                {"title": "Category", "value": category or "—", "short": True},
                {"title": "Urgency", "value": urgency.title(), "short": True},
            ],
            "footer": "Feedback Intelligence Platform",
        }]
    }

    try:
        resp = httpx.post(
            SLACK_WEBHOOK_URL,
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
        resp.raise_for_status()
        logger.info(f"[Alerts] Slack alert sent: {message[:60]}")
        return True
    except Exception as e:
        logger.error(f"[Alerts] Slack error: {e}")
        return False


# ── Email ─────────────────────────────────────────────────

def send_email_alert(subject: str, body: str) -> bool:
    """Send an email alert via SMTP. Requires SMTP_* env vars."""
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    from_addr = os.getenv("ALERT_EMAIL_FROM", smtp_user)

    if not all([smtp_host, smtp_user, ALERT_EMAIL_TO]):
        logger.info(f"[Alerts] Email not configured. Subject: {subject}")
        return False

    import smtplib
    from email.mime.text import MIMEText

    try:
        msg = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = ALERT_EMAIL_TO

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        logger.info(f"[Alerts] Email sent: {subject}")
        return True
    except Exception as e:
        logger.error(f"[Alerts] Email error: {e}")
        return False


# ── High-urgency checker ──────────────────────────────────

def check_and_alert_urgency(feedback_text: str, category: str, sentiment: str, urgency: str = "medium") -> None:
    """
    Called after each feedback is processed.
    Fires alerts for high-urgency or high-volume negative feedback.
    """
    if urgency == "high" or (sentiment == "negative" and category == "bug"):
        message = (
            f"High-urgency feedback received.\n\n"
            f"Category: {category} | Sentiment: {sentiment} | Urgency: {urgency.upper()}\n\n"
            f"Text: {feedback_text[:300]}"
        )
        send_slack_alert(message, category=category, urgency=urgency)
        send_email_alert(
            subject=f"[Feedback Alert] High urgency {category} feedback",
            body=message,
        )


# ── Trend alert dispatcher ────────────────────────────────

def dispatch_trend_alerts(alerts: list[dict]) -> None:
    """Send all trend alerts detected by trend_detector."""
    for alert in alerts:
        message = alert.get("message", "")
        category = alert.get("category", "")
        send_slack_alert(message, category=category, urgency="high")
        send_email_alert(
            subject=f"[Trend Alert] Spike in {category}",
            body=message,
        )