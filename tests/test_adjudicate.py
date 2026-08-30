from patrol.adjudicate import adjudicate
from patrol.models import Action, Category, Finding


def _f(file, quote, verdict="rot"):
    return Finding(reasoning="r", category=Category.STALE_ACTIVE_REFERENCE, file=file,
                   evidence_quote=quote, proposed_action=Action.MARK_HISTORICAL, verdict=verdict)


def test_verbatim_evidence_kept(demo_vault):
    kept, dropped = adjudicate(demo_vault, [_f("tools/memvid.md", "Status: live.")])
    assert len(kept) == 1 and dropped == 0


def test_fabricated_evidence_dropped(demo_vault):
    kept, dropped = adjudicate(demo_vault, [_f("tools/memvid.md", "Status: retired.")])
    assert kept == [] and dropped == 1


def test_unknown_file_dropped(demo_vault):
    kept, dropped = adjudicate(demo_vault, [_f("tools/nope.md", "Status: live.")])
    assert kept == [] and dropped == 1


def test_unsure_dropped_and_dedupe(demo_vault):
    proposed = [_f("tools/memvid.md", "Status: live.", "unsure"),
                _f("tools/memvid.md", "Status:  live."), _f("tools/memvid.md", "Status: live.")]
    kept, dropped = adjudicate(demo_vault, proposed)
    assert len(kept) == 1 and dropped == 2
