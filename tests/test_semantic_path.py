"""Semantic path without the network: the model is stubbed, code adjudication is real."""
from pathlib import Path

from patrol import runner
from patrol.models import Action, Category, Finding, SemanticReport

DEMO = Path(__file__).resolve().parent.parent / "demo-vault"


def _f(file, quote, verdict="rot"):
    return Finding(reasoning="r", category=Category.STALE_ACTIVE_REFERENCE, file=file,
                   evidence_quote=quote, proposed_action=Action.MARK_HISTORICAL, verdict=verdict)


def test_patrol_path_keeps_only_verified_findings(monkeypatch):
    canned = SemanticReport(reasoning="stub", findings=[
        _f("tools/memvid.md", "Status: live."),                 # verbatim → kept
        _f("tools/memvid.md", "Status: retired since 7-03."),   # fabricated quote → dropped
        _f("tools/stack.md", "It is the primary retrieval path; grep is the fallback.", "unsure"),  # verbatim but unsure → dropped
    ])
    monkeypatch.setattr(runner, "judge", lambda v, model=None: (canned, "stub-model"))

    res = runner.patrol_path(DEMO, use_model=True)

    assert len(res.semantic) == 1
    assert res.semantic[0].evidence_quote == "Status: live."
    assert res.dropped == 2
    assert res.model_version == "stub-model"
