"""Turn a PatrolResult into a PR: report file + the safe mechanical edits."""
from __future__ import annotations

from pathlib import Path

from .models import Category, Finding, PatrolResult
from .vault import Vault

REPORT_NAME = "PATROL_REPORT.md"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")[:120]


def _row(f: Finding) -> str:
    rel = ", ".join(f.related_files) if f.related_files else "—"
    proof = f"`{f.counter_evidence_file}`: `{_cell(f.counter_evidence_quote)}`" if f.counter_evidence_file else "—"
    return (f"| `{f.category.value}` | `{f.file}` | `{_cell(f.evidence_quote)}` | {proof} | {rel} "
            f"| **{f.proposed_action.value}** | {f.reasoning} |")


TABLE_HEAD = ["| category | file | evidence | proof in other note | related | action | why |",
              "|---|---|---|---|---|---|---|"]


def _drop_summary(r: PatrolResult) -> str:
    detail = " ".join(f"{k} {v}" for k, v in sorted(r.drop_reasons.items()) if v)
    return f"{r.dropped}" + (f" ({detail})" if detail else "")


def _header(r: PatrolResult) -> list[str]:
    return [
        f"# Vault patrol report",
        "",
        f"- vault: `{r.vault}`",
        f"- anchor commit: `{r.anchor_sha or 'n/a'}`",
        f"- model: `{r.model_version or 'skipped'}` · prompt: `{r.prompt_version}`",
        f"- mechanical findings: {len(r.mechanical)} · semantic findings kept: {len(r.semantic)} · dropped by verification: {_drop_summary(r)}",
        f"- model calls: {r.model_calls} · notes too large to send: {r.notes_truncated}",
        "",
        "Subtraction only: this PR deletes dead index lines and proposes edits. Nothing new is created.",
        "",
    ]


def render_report(r: PatrolResult) -> str:
    """The full flat table, written to PATROL_REPORT.md and printed by the CLI."""
    rows = [_row(f) for f in [*r.mechanical, *r.semantic]] or ["| — | — | — | — | — | — | vault is clean |"]
    return "\n".join([*_header(r), *TABLE_HEAD, *rows, ""])


def render_pr_body(r: PatrolResult) -> str:
    """Same content, arranged for a human opening the PR: the semantic findings up front,
    the long mechanical lists folded away by category."""
    out = [*_header(r)]
    if r.semantic:
        out += ["## Semantic findings", "", *TABLE_HEAD, *[_row(f) for f in r.semantic], ""]
    by_category: dict[str, list] = {}
    for f in r.mechanical:
        by_category.setdefault(f.category.value, []).append(f)
    if by_category:
        out += ["## Mechanical findings", ""]
        for cat, findings in by_category.items():
            out += [f"<details><summary>{cat} ({len(findings)})</summary>", "",
                    *TABLE_HEAD, *[_row(f) for f in findings], "", "</details>", ""]
    if not r.semantic and not by_category:
        out += ["Vault is clean.", ""]
    out += [f"Full flat table: [`{REPORT_NAME}`]({REPORT_NAME}) in this PR.", ""]
    return "\n".join(out)


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
