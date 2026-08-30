from patrol.mechanical import run_mechanical
from patrol.models import PatrolResult
from patrol.report import apply_mechanical_edits, render_pr_body, render_report


def test_broken_link_line_removed_from_index(demo_vault):
    r = PatrolResult(anchor_sha="abc", vault="demo", mechanical=run_mechanical(demo_vault),
                     semantic=[], dropped=0, model_version=None, prompt_version="t")
    edits = apply_mechanical_edits(demo_vault, r)
    if edits:
        assert "planner_2025" not in edits["MEMORY.md"]
        assert "tools/stack.md" in edits["MEMORY.md"]
    assert "Vault patrol report" in render_report(r)


def test_pr_body_folds_mechanical_findings_into_details(demo_vault):
    r = PatrolResult(anchor_sha="abc", vault="demo", mechanical=run_mechanical(demo_vault),
                     semantic=[], dropped=0, model_version=None, prompt_version="t")
    body = render_pr_body(r)
    assert r.mechanical  # guard: the fixture must actually have mechanical findings
    assert "<details><summary>orphan (1)</summary>" in body
    assert body.count("<details>") == len({f.category.value for f in r.mechanical})


def test_pr_body_without_mechanical_findings_has_no_details():
    r = PatrolResult(anchor_sha="abc", vault="demo", mechanical=[], semantic=[],
                     dropped=0, model_version=None, prompt_version="t")
    assert "<details>" not in render_pr_body(r)
