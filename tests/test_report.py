from patrol.mechanical import run_mechanical
from patrol.models import PatrolResult
from patrol.report import apply_mechanical_edits, render_report


def test_broken_link_line_removed_from_index(demo_vault):
    r = PatrolResult(anchor_sha="abc", vault="demo", mechanical=run_mechanical(demo_vault),
                     semantic=[], dropped=0, model_version=None, prompt_version="t")
    edits = apply_mechanical_edits(demo_vault, r)
    if edits:
        assert "planning_v1" not in edits["MEMORY.md"]
        assert "tools/stack.md" in edits["MEMORY.md"]
    assert "Vault patrol report" in render_report(r)
