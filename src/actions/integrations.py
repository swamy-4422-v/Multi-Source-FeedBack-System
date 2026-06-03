"""
Third-party integrations — push processed feedback to external tools.
Configure each integration via .env variables.

Supported:
  - Slack (SLACK_WEBHOOK_URL)
  - Jira  (JIRA_URL, JIRA_EMAIL, JIRA_TOKEN, JIRA_PROJECT_KEY)
  - Notion (NOTION_TOKEN, NOTION_DATABASE_ID)
"""
import os
import logging
import httpx

logger = logging.getLogger(__name__)


# ── Jira ──────────────────────────────────────────────────

JIRA_URL = os.getenv("JIRA_URL", "")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
JIRA_TOKEN = os.getenv("JIRA_TOKEN", "")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "FEED")
JIRA_ISSUE_TYPE = os.getenv("JIRA_ISSUE_TYPE", "Bug")


def create_jira_issue(feedback_text: str, category: str, sentiment: str) -> dict | None:
    """
    Create a Jira issue from high-priority feedback.
    Returns the created issue dict or None on failure.
    """
    if not all([JIRA_URL, JIRA_EMAIL, JIRA_TOKEN]):
        logger.debug("[Jira] Credentials not configured — skipping.")
        return None

    issue_type = "Bug" if category == "bug" else "Task"
    summary = f"[Feedback] {category.title()}: {feedback_text[:80]}"

    payload = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [{
                    "type": "paragraph",
                    "content": [{
                        "type": "text",
                        "text": (
                            f"Category: {category}\n"
                            f"Sentiment: {sentiment}\n\n"
                            f"Original feedback:\n{feedback_text}"
                        ),
                    }],
                }],
            },
            "issuetype": {"name": issue_type},
            "labels": [f"feedback-{category}", f"sentiment-{sentiment}"],
        }
    }

    try:
        resp = httpx.post(
            f"{JIRA_URL.rstrip('/')}/rest/api/3/issue",
            auth=(JIRA_EMAIL, JIRA_TOKEN),
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"[Jira] Created issue {data.get('key')}")
        return {"id": data.get("id"), "key": data.get("key"), "status": "success"}
    except Exception as e:
        logger.error(f"[Jira] Error: {e}")
        return None


# ── Notion ────────────────────────────────────────────────

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DB_ID = os.getenv("NOTION_DATABASE_ID", "")


def add_to_notion(feedback_text: str, category: str, sentiment: str) -> dict | None:
    """Append a feedback row to a Notion database."""
    if not all([NOTION_TOKEN, NOTION_DB_ID]):
        logger.debug("[Notion] Credentials not configured — skipping.")
        return None

    payload = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": feedback_text[:200]}}]
            },
            "Category": {
                "select": {"name": category}
            },
            "Sentiment": {
                "select": {"name": sentiment}
            },
        },
    }

    try:
        resp = httpx.post(
            "https://api.notion.com/v1/pages",
            headers={
                "Authorization": f"Bearer {NOTION_TOKEN}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"[Notion] Page created: {data.get('id')}")
        return {"id": data.get("id"), "status": "success"}
    except Exception as e:
        logger.error(f"[Notion] Error: {e}")
        return None


# ── Orchestrator ─────────────────────────────────────────

def run_all_integrations(feedback_text: str, category: str, sentiment: str) -> dict:
    """Run all configured integrations for a single feedback item."""
    results = {}

    # Jira: only for bugs and security issues
    if category in ("bug", "security"):
        jira_res = create_jira_issue(feedback_text, category, sentiment)
        if jira_res:
            results["jira"] = jira_res

    # Notion: log everything
    notion_res = add_to_notion(feedback_text, category, sentiment)
    if notion_res:
        results["notion"] = notion_res

    return results