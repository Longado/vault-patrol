"""Code decides. The model proposes; nothing reaches the PR without passing these gates."""
from __future__ import annotations

import logging
import re

from .models import Category, Finding
from .vault import Vault, nfc

log = logging.getLogger(__name__)

# A finding in one of these categories is a claim ABOUT TWO NOTES: it is only true if the other
# note actually says what the model says it says. So the model must quote that sentence too, and
# code checks it the same way it checks the first quote. Without this, a real quote can carry an
# invented rationale (measured 2026-08-30: a true MEMORY.md quote justified by a deletion record
# that does not exist anywhere in the vault).
CROSS_NOTE_CATEGORIES = frozenset({
    Category.STALE_ACTIVE_REFERENCE,
    Category.HARD_CONFLICT,
    Category.FALSIFIED_CLAIM,
    Category.OVERLAP_CLUSTER,
})
# Models routinely re-type a quoted line without its markdown emphasis: `file.md` comes back
# as file.md, **bold** as bold. Both sides are stripped identically, so this forgives
# decoration and nothing else — a paraphrase still fails.
DECORATION_RE = re.compile(r"[`*]+")


def _norm(s: str) -> str:
    return DECORATION_RE.sub("", re.sub(r"\s+", " ", nfc(s))).strip()


def quote_present(v: Vault, rel_path: str, quote: str) -> bool:
    note = v.get(nfc(rel_path))
    if note is None or not quote.strip():
        return False
    return _norm(quote) in _norm(note.text)


def evidence_present(v: Vault, f: Finding) -> bool:
    return quote_present(v, f.file, f.evidence_quote)


def _reject_reason(v: Vault, f: Finding) -> str | None:
    """None means the finding survives. Otherwise the reason it does not."""
    if f.verdict != "rot":
        return "unsure"
    if v.get(nfc(f.file)) is None:
        return "file_missing"
    if not evidence_present(v, f):
        return "quote_not_found"
    if f.category in CROSS_NOTE_CATEGORIES:
        other = nfc(f.counter_evidence_file)
        if not other or not f.counter_evidence_quote.strip() or other == nfc(f.file):
            return "counter_evidence_missing"
        if not quote_present(v, other, f.counter_evidence_quote):
            return "counter_evidence_not_found"
    return None


def adjudicate(v: Vault, proposed: list[Finding]) -> tuple[list[Finding], dict[str, int]]:
    """Keep only findings with verdict=rot, a real file, verbatim evidence, and — for
    cross-note categories — a verbatim counter-quote in the note that contradicts it.
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
    return kept, reasons
