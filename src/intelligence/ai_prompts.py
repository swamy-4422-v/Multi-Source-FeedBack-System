"""
OpenAI-powered intelligence functions.
All functions gracefully degrade if OPENAI_API_KEY is not set.
"""
import os
import logging

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL = "gpt-4o-mini"


def _client():
    """Lazy OpenAI client — only imported if key is available."""
    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-your"):
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=OPENAI_API_KEY)
    except ImportError:
        logger.error("[AI] openai package not installed")
        return None


def _chat(system: str, user: str, max_tokens: int = 300) -> str | None:
    """Generic chat completion helper. Returns None on failure."""
    client = _client()
    if not client:
        return None
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"[AI] OpenAI error: {e}")
        return None


# ── Public prompt functions ───────────────────────────────

def summarise_feedback(texts: list[str], max_items: int = 30) -> str:
    """
    Summarise a batch of feedback items into key themes.
    Returns a human-readable summary string.
    Falls back to a simple count string if OpenAI is unavailable.
    """
    if not texts:
        return "No feedback to summarise."

    sample = texts[:max_items]
    joined = "\n".join(f"- {t[:300]}" for t in sample)

    result = _chat(
        system=(
            "You are a product analyst. Summarise the key themes, pain points, "
            "and positive signals from user feedback. Be concise — 3-5 bullet points max."
        ),
        user=f"Here are {len(sample)} pieces of user feedback:\n\n{joined}",
        max_tokens=400,
    )

    if result:
        return result

    # Fallback: basic stats summary
    return (
        f"Received {len(texts)} feedback items. "
        "OpenAI summarisation unavailable — set OPENAI_API_KEY to enable."
    )


def classify_urgency(text: str) -> str:
    """
    Returns 'high', 'medium', or 'low' urgency.
    Falls back to rule-based urgency scoring.
    """
    HIGH_WORDS = {"urgent", "asap", "critical", "down", "outage", "immediately",
                  "emergency", "broken", "crash", "data loss"}

    result = _chat(
        system=(
            "Classify the urgency of this user feedback as exactly one word: "
            "'high', 'medium', or 'low'. Reply with only that word."
        ),
        user=text[:500],
        max_tokens=5
    )

    if result and result.lower() in ("high", "medium", "low"):
        return result.lower()

    # Fallback: keyword rule
    text_lower = text.lower()
    if any(w in text_lower for w in HIGH_WORDS):
        return "high"
    return "medium"


def generate_response_draft(feedback: str, category: str, sentiment: str) -> str:
    """
    Generate a draft customer response for a support agent to review and send.
    """
    result = _chat(
        system=(
            "You are a helpful and empathetic customer support agent. "
            "Write a brief, professional draft response to this user feedback. "
            "Acknowledge their experience, address the issue, and offer next steps. "
            "Keep it under 100 words."
        ),
        user=(
            f"Category: {category}\nSentiment: {sentiment}\n\n"
            f"Feedback: {feedback[:800]}"
        ),
        max_tokens=200,
    )
    return result or "Thank you for your feedback. Our team will look into this shortly."


def extract_action_items(text: str) -> list[str]:
    """
    Extract concrete action items or feature requests from feedback text.
    Returns list of strings.
    """
    result = _chat(
        system=(
            "Extract specific, actionable items from this feedback. "
            "Return a JSON array of short strings (max 10 words each). "
            "Example: [\"Fix login crash on iOS\", \"Add dark mode\"]. "
            "Return only the JSON array, nothing else."
        ),
        user=text[:800],
        max_tokens=200,
    )

    if result:
        import json
        try:
            # Clean up potential markdown formatting block if the LLM includes it
            cleaned_result = result.strip().strip("`").replace("json", "").strip()
            items = json.loads(cleaned_result)
            if isinstance(items, list):
                return [str(i) for i in items]
        except json.JSONDecodeError:
            pass

    return []