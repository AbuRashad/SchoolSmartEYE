""""Optional Ollama Cloud/local summary adapter for specialist agents.

LLM output is advisory only. Deterministic findings/evidence remain authoritative;
provider errors fall back to the deterministic summary. No tools or actions are exposed.
Only the specialist label and validated aggregate metrics are sent to the provider.
"""
from __future__ import annotations

import json
import os
from typing import Any

import httpx

MAX_SUMMARY_LENGTH = 500
DEFAULT_TIMEOUT_SECONDS = 12.0


def ollama_enabled() -> bool:
    return os.getenv("SCHOOLSMARTEYE_LLM_PROVIDER", "deterministic").strip().lower() == "ollama"


def _ollama_chat_url() -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "https://ollama.com").strip().rstrip("/")
    if not base_url.startswith(("https://", "http://")):
        raise ValueError("OLLAMA_BASE_URL must be an HTTP(S) URL")
    return f"{base_url}/api/chat"


def generate_specialist_summary(
    agent_name: str,
    metrics: dict[str, int | float],
    fallback_summary: str,
) -> tuple[str, bool]:
    """Return an LLM-generated bounded summary or the deterministic fallback."""
    if not ollama_enabled():
        return fallback_summary, False

    model = os.getenv("OLLAMA_MODEL", "").strip()
    api_key = os.getenv("OLLAMA_API_KEY", "").strip()
    if not model:
        return fallback_summary, False

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    system_prompt = (
        "You are a specialist summarizer in a school intelligence system. "
        "Use only the supplied aggregate metrics. Never infer individual causes, "
        "identify people, invent evidence, or recommend punitive actions. "
        "Return one concise plain-text summary of at most 60 words. "
        "The output is advisory and requires human review."
    )
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {"agent": agent_name, "aggregate_metrics": metrics},
                    ensure_ascii=True,
                    allow_nan=False,
                ),
            },
        ],
        "options": {"temperature": 0.1},
    }

    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT_SECONDS, follow_redirects=False) as client:
            response = client.post(_ollama_chat_url(), headers=headers, json=payload)
            response.raise_for_status()
            body: dict[str, Any] = response.json()
        summary = body.get("message", {}).get("content", "")
        if not isinstance(summary, str):
            return fallback_summary, False
        summary = " ".join(summary.split()).strip()
        if not summary or len(summary) > MAX_SUMMARY_LENGTH:
            return fallback_summary, False
        return summary, True
    except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError):
        # Fail closed: deterministic output remains available and secrets are not logged.
        return fallback_summary, False
