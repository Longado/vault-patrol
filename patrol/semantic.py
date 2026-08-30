"""One model judgment per vault. Loops, retries and verification live in code, not here."""
from __future__ import annotations

import os
import re
from pathlib import Path

from google import genai
from google.genai import types

from .models import SemanticReport
from .vault import Vault

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "semantic.md"
DEFAULT_MODEL = "gemini-3.5-flash"
MAX_CONTEXT_CHARS = 350_000  # stay well under the model window; larger vaults are truncated by file order


def prompt_version() -> str:
    m = re.search(r"prompt_version:\s*(\S+)", PROMPT_PATH.read_text())
    return m.group(1) if m else "unknown"


def _client() -> genai.Client:
    if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true":
        return genai.Client(
            vertexai=True,
            project=os.environ["GOOGLE_CLOUD_PROJECT"],
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_GENAI_USE_VERTEXAI=true) is required")
    return genai.Client(api_key=key)


def render_vault(v: Vault) -> str:
    parts = []
    for n in v.notes:
        parts.append(f'<note path="{n.rel_path}">\n{n.text}\n</note>')
    body = "\n\n".join(parts)
    if len(body) > MAX_CONTEXT_CHARS:
        body = body[:MAX_CONTEXT_CHARS] + "\n<!-- truncated -->"
    return body


def judge(v: Vault, model: str | None = None) -> tuple[SemanticReport, str]:
    """Single structured call. Returns (report, model_id). Raises on transport errors; caller retries."""
    model_id = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
    client = _client()
    resp = client.models.generate_content(
        model=model_id,
        contents=render_vault(v),
        config=types.GenerateContentConfig(
            system_instruction=PROMPT_PATH.read_text(),
            response_mime_type="application/json",
            response_schema=SemanticReport,
            temperature=0,
        ),
    )
    parsed = resp.parsed
    if parsed is None:
        parsed = SemanticReport.model_validate_json(resp.text)
    return parsed, model_id
