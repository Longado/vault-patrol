"""Code decides. The model proposes; nothing reaches the PR without passing these gates."""
from __future__ import annotations

import re

from .models import Finding
from .vault import Vault, nfc

MAX_SEMANTIC_FINDINGS = 12


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", nfc(s)).strip()


def evidence_present(v: Vault, f: Finding) -> bool:
    note = v.get(nfc(f.file))
    if note is None or not f.evidence_quote.strip():
        return False
    return _norm(f.evidence_quote) in _norm(note.text)


def adjudicate(v: Vault, proposed: list[Finding]) -> tuple[list[Finding], int]:
    """Keep only findings with verdict=rot, a real file, verbatim evidence; dedupe; cap."""
    kept: list[Finding] = []
    seen: set[tuple[str, str, str]] = set()
    for f in proposed:
        if f.verdict != "rot" or not evidence_present(v, f):
            continue
        key = (f.category.value, nfc(f.file), _norm(f.evidence_quote))
        if key in seen:
            continue
        seen.add(key)
        kept.append(f.model_copy(update={"file": nfc(f.file)}))
    kept = kept[:MAX_SEMANTIC_FINDINGS]
    return kept, len(proposed) - len(kept)
