"""One model judgment per vault. Loops, retries and verification live in code, not here."""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from google import genai
from google.genai import types

from .models import SemanticReport
from .vault import Note, Vault

log = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "semantic.md"
DEFAULT_MODEL = "gemini-3.5-flash"
MAX_CONTEXT_CHARS = 350_000  # per model call; a vault larger than this is split across calls
# ponytail: unlimited (char budget alone) — measured 2026-08-30 on the 175-note vault with
# prompt 2026-08-30.3: unlimited = 9 real / 1 false in 2 calls (79s); 40/batch = 3 real / 8 false
# in 5 calls (114s); 20/batch = 4 real / 8 false in 9 calls (295s). Small batches lose the
# cross-vault context that separates "archived project" from "dated research note", and flood
# the report with one folder's worth of look-alike false positives. Override per run with
# PATROL_MAX_NOTES_PER_BATCH if a future vault behaves differently.
MAX_NOTES_PER_BATCH = 0  # 0 = unlimited


def max_notes_per_batch() -> int:
    """0 / unset = unlimited. Smaller batches cost more calls but the model reads each note
    more closely; see the 召回实验 table in docs/HANDOFF.md."""
    raw = os.getenv("PATROL_MAX_NOTES_PER_BATCH", "")
    return int(raw) if raw.strip().isdigit() else MAX_NOTES_PER_BATCH


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


def _block(n: Note) -> str:
    kind = "record" if n.is_record else "live"
    return f'<note path="{n.rel_path}" kind="{kind}">\n{n.text}\n</note>'


def render_notes(notes: list[Note]) -> str:
    return "\n\n".join(_block(n) for n in notes)


def plan_batches(v: Vault) -> tuple[list[list[Note]], list[Note]]:
    """Split the vault into batches that each fit the per-call budget, with the index note
    prepended to every batch so each call keeps its bearings. Returns (batches, oversized)
    where oversized notes are the ones that do not fit even alone."""
    index = v.index
    head = [index] if index else []
    head_len = len(_block(index)) + 2 if index else 0
    body = [n for n in v.notes if index is None or n.rel_path != index.rel_path]

    cap = max_notes_per_batch()
    batches: list[list[Note]] = []
    oversized: list[Note] = []
    current: list[Note] = []
    used = head_len
    for n in body:
        size = len(_block(n)) + 2
        if head_len + size > MAX_CONTEXT_CHARS:
            oversized.append(n)
            continue
        if (used + size > MAX_CONTEXT_CHARS or (cap and len(current) >= cap)) and current:
            batches.append(head + current)
            current, used = [], head_len
        current.append(n)
        used += size
    if current or not batches:
        batches.append(head + current)
    if oversized:
        log.warning("%d note(s) exceed the %d-char per-call budget on their own and were not sent: %s",
                    len(oversized), MAX_CONTEXT_CHARS, ", ".join(n.rel_path for n in oversized))
    return batches, oversized


def judge(notes: list[Note], model: str | None = None) -> tuple[SemanticReport, str]:
    """One structured call over one batch. Returns (report, model_id).
    Raises on transport errors; runner.py owns the loop and decides what is worth retrying."""
    model_id = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
    client = _client()
    resp = client.models.generate_content(
        model=model_id,
        contents=render_notes(notes),
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
