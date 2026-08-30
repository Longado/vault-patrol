"""Turn a PatrolResult into a PR: report file + the safe mechanical edits."""
from __future__ import annotations

from pathlib import Path

from .models import Category, Finding, PatrolResult
from .vault import Vault

REPORT_NAME = "PATROL_REPORT.md"


def _row(f: Finding) -> str:
    quote = f.evidence_quote.replace("|", "\\|").replace("\n", " ")[:120]
    rel = ", ".join(f.related_files) if f.related_files else "—"
    return f"| `{f.category.value}` | `{f.file}` | `{quote}` | {rel} | **{f.proposed_action.value}** | {f.reasoning} |"


def render_report(r: PatrolResult) -> str:
    head = [
        f"# Vault patrol report",
        "",
        f"- vault: `{r.vault}`",
        f"- anchor commit: `{r.anchor_sha or 'n/a'}`",
        f"- model: `{r.model_version or 'skipped'}` · prompt: `{r.prompt_version}`",
        f"- mechanical findings: {len(r.mechanical)} · semantic findings kept: {len(r.semantic)} · dropped by verification: {r.dropped}",
        "",
        "Subtraction only: this PR deletes dead index lines and proposes edits. Nothing new is created.",
        "",
        "| category | file | evidence | related | action | why |",
        "|---|---|---|---|---|---|",
    ]
    rows = [_row(f) for f in [*r.mechanical, *r.semantic]] or ["| — | — | — | — | — | vault is clean |"]
    return "\n".join([*head, *rows, ""])


def apply_mechanical_edits(v: Vault, r: PatrolResult) -> dict[str, str]:
    """Return {rel_path: new_text} for edits safe enough to apply in the PR itself.
    Only broken index links are removed; everything else stays a proposal."""
    if not v.index:
        return {}
    dead = {f.evidence_quote for f in r.mechanical if f.category == Category.BROKEN_LINK}
    if not dead:
        return {}
    lines = v.index.text.splitlines(keepends=True)
    kept = [ln for ln in lines if not any(d in ln for d in dead)]
    return {v.index.rel_path: "".join(kept)}


def write_pr_files(root: Path, v: Vault, r: PatrolResult) -> list[str]:
    edits = {**apply_mechanical_edits(v, r), REPORT_NAME: render_report(r)}
    for rel, text in edits.items():
        (root / rel).write_text(text, encoding="utf-8")
    return sorted(edits)
