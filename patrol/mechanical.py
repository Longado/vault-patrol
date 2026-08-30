"""Deterministic checks. Anything a regex can find never goes to the model."""
from __future__ import annotations

from .models import Action, Category, Finding
from .vault import Vault, md_links, wiki_links


def broken_index_links(v: Vault) -> list[Finding]:
    if not v.index:
        return []
    existing = {n.rel_path for n in v.notes}
    return [
        Finding(
            reasoning="Index links to a file that does not exist; a dead index entry misleads every reader.",
            category=Category.BROKEN_LINK,
            file=v.index.rel_path,
            evidence_quote=f"({target})",
            related_files=[target],
            proposed_action=Action.DELETE_LINE,
            verdict="rot",
        )
        for target in md_links(v.index)
        if target not in existing
    ]


def orphans(v: Vault) -> list[Finding]:
    if not v.index:
        return []
    linked = set(md_links(v.index))
    return [
        Finding(
            reasoning="File exists but nothing in the index points to it; unreachable notes are a dead lake.",
            category=Category.ORPHAN,
            file=n.rel_path,
            evidence_quote=n.text[:80].strip() or n.rel_path,
            proposed_action=Action.NEEDS_HUMAN,
            verdict="rot",
        )
        for n in v.notes
        if n.rel_path != v.index.rel_path and n.rel_path not in linked
    ]


def dangling_wikilinks(v: Vault) -> list[Finding]:
    stems = {n.stem for n in v.notes} | {n.rel_path.removesuffix(".md") for n in v.notes}
    out = []
    for n in v.notes:
        for target in wiki_links(n):
            if target in stems or target.removesuffix(".md") in stems:
                continue
            out.append(
                Finding(
                    reasoning="[[wikilink]] points at a note that does not exist (may be a planned note; flagged, not deleted).",
                    category=Category.DANGLING_WIKILINK,
                    file=n.rel_path,
                    evidence_quote=f"[[{target}]]",
                    proposed_action=Action.NEEDS_HUMAN,
                    verdict="rot",
                )
            )
    return out


def run_mechanical(v: Vault) -> list[Finding]:
    return [*broken_index_links(v), *orphans(v), *dangling_wikilinks(v)]
