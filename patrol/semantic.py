"""One model judgment per vault. Loops, retries and verification live in code, not here."""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from google import genai
from google.genai import types

from .models import SemanticReport
from .vault import Vault

log = logging.getLogger(__name__)

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


def render_vault(v: Vault) -> tuple[str, int]:
    """Render whole notes until the budget is spent. Returns (body, notes_not_sent)."""
    parts, used = [], 0
    for n in v.notes:
        block = f'<note path="{n.rel_path}">\n{n.text}\n</note>'
        if used + len(block) > MAX_CONTEXT_CHARS:
            break
        parts.append(block)
        used += len(block) + 2
    truncated = len(v.notes) - len(parts)
    if truncated:
        log.warning("vault exceeds the %d-char context budget: %d of %d notes were not sent to the model",
                    MAX_CONTEXT_CHARS, truncated, len(v.notes))
        parts.append("<!-- truncated -->")
    return "\n\n".join(parts), truncated


def judge(v: Vault, model: str | None = None) -> tuple[SemanticReport, str, int]:
    """Single structured call. Returns (report, model_id, notes_truncated).
    Raises on transport errors; runner.py decides what is worth retrying."""
    model_id = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
    client = _client()
    body, truncated = render_vault(v)
    resp = client.models.generate_content(
        model=model_id,
        contents=body,
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
    return parsed, model_id, truncated
