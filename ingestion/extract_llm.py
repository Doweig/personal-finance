"""Optional LLM helpers for difficult email formats."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from email import message_from_bytes, policy
from pathlib import Path


def _plain_text_from_eml(filepath: str | Path) -> tuple[str, str]:
    filepath = Path(filepath)
    msg = message_from_bytes(filepath.read_bytes(), policy=policy.compat32)
    subject = msg.get("Subject", "")

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
                else:
                    body = part.get_payload(decode=False)
                if body:
                    break
    else:
        payload = msg.get_payload(decode=True)
        if isinstance(payload, bytes):
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")
        else:
            body = msg.get_payload(decode=False) or ""

    return subject, body


def build_codex_prompt(filepath: str | Path) -> str:
    """Build a prompt for Codex/ChatGPT manual extraction."""
    subject, body = _plain_text_from_eml(filepath)
    return f"""Extract structured data from this P&L email.
Return ONLY valid JSON with keys:
- restaurant_name (string)
- month (YYYY-MM-01)
- restaurant_code (string or null)
- pl (object with keys: revenue, revenue_n1, food_cost, beverage_cost, total_fb_cost, total_other_expenses, total_monthly_exp, gop_before_fee, other_special_fee, monthly_provision, gop_net, rebate; numeric or null)
- dividend (object with keys: total_thb, my_share_thb; numeric) OR null

Subject:
{subject}

Body:
{body}
"""


def extract_with_openai(filepath: str | Path, model: str = "gpt-4.1-mini", api_key: str | None = None) -> dict:
    """Call OpenAI Chat Completions API to extract structured JSON."""
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY is not set")

    prompt = build_codex_prompt(filepath)
    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "You extract financial data from restaurant P&L emails. Return JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
    }

    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API error: {detail}") from e

    content = data["choices"][0]["message"]["content"]
    return json.loads(content)

