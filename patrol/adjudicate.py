"""Code decides. The model proposes; nothing reaches the PR without passing these gates."""
from __future__ import annotations

import logging
import re

from .models import Finding
from .vault import Vault, nfc

log = logging.getLogger(__name__)

MAX_SEMANTIC_FINDINGS = 12
# Models routinely re-type a quoted line without its markdown emphasis: `file.md` comes back
# as file.md, **bold** as bold. Both sides are stripped identically, so this forgives
# decoration and nothing else — a paraphrase still fails.
DECORATION_RE = re.compile(r"[`*]+")


def _norm(s: str) -> str:
    return DECORATION_RE.sub("", re.sub(r"\s+", " ", nfc(s))).strip()


def evidence_present(v: Vault, f: Finding) -> bool:
    note = v.get(nfc(f.file))
    if note is None or not f.evidence_quote.strip():
        return False
    return _norm(f.evidence_quote) in _norm(note.text)


def _reject_reason(v: Vault, f: Finding) -> str | None:
    """None means the finding survives. Otherwise the reason it does not."""
    if f.verdict != "rot":
        return "unsure"
    if v.get(nfc(f.file)) is None:
        return "file_missing"
    if not evidence_present(v, f):
        return "quote_not_found"
    return None


def adjudicate(v: Vault, proposed: list[Finding]) -> tuple[list[Finding], dict[str, int]]:
    """Keep only findings with verdict=rot, a real file and verbatim evidence; dedupe; cap.
    Returns (kept, reasons) where reasons counts every rejection by cause."""
    kept: list[Finding] = []
    seen: set[tuple[str, str, str]] = set()
    reasons: dict[str, int] = {}

    def drop(f: Finding, reason: str) -> None:
        reasons[reason] = reasons.get(reason, 0) + 1
        log.info("dropped [%s] %s: %r", reason, f.file, f.evidence_quote[:80])

    for f in proposed:
        reason = _reject_reason(v, f)
        if reason:
            drop(f, reason)
            continue
        key = (f.category.value, nfc(f.file), _norm(f.evidence_quote))
        if key in seen:
            drop(f, "duplicate")
            continue
        seen.add(key)
        kept.append(f.model_copy(update={"file": nfc(f.file)}))

    for f in kept[MAX_SEMANTIC_FINDINGS:]:
        drop(f, "over_cap")
    return kept[:MAX_SEMANTIC_FINDINGS], reasons
