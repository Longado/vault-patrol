from patrol.adjudicate import adjudicate
from patrol.models import Action, Category, Finding


def _f(file, quote, verdict="rot"):
    return Finding(reasoning="r", category=Category.STALE_ACTIVE_REFERENCE, file=file,
                   evidence_quote=quote, proposed_action=Action.MARK_HISTORICAL, verdict=verdict)


def test_verbatim_evidence_kept(demo_vault):
    kept, reasons = adjudicate(demo_vault, [_f("tools/memvid.md", "Status: live.")])
    assert len(kept) == 1 and reasons == {}


def test_fabricated_evidence_dropped(demo_vault):
    kept, reasons = adjudicate(demo_vault, [_f("tools/memvid.md", "Status: retired.")])
    assert kept == [] and reasons == {"quote_not_found": 1}


def test_unknown_file_dropped(demo_vault):
    kept, reasons = adjudicate(demo_vault, [_f("tools/nope.md", "Status: live.")])
    assert kept == [] and reasons == {"file_missing": 1}


def test_unsure_dropped_and_dedupe(demo_vault):
    proposed = [_f("tools/memvid.md", "Status: live.", "unsure"),
                _f("tools/memvid.md", "Status:  live."), _f("tools/memvid.md", "Status: live.")]
    kept, reasons = adjudicate(demo_vault, proposed)
    assert len(kept) == 1
    assert reasons == {"unsure": 1, "duplicate": 1}


def test_quote_missing_only_markdown_decoration_is_kept(demo_vault):
    """tools/stack.md says `[[memvid]]`; a model that drops the emphasis still cited it."""
    quote = "use the Memvid MCP server (see [[memvid]])"
    kept, reasons = adjudicate(demo_vault, [_f("tools/stack.md", f"**{quote}**")])
    assert len(kept) == 1 and reasons == {}


def test_paraphrase_is_still_dropped(demo_vault):
    kept, reasons = adjudicate(demo_vault, [_f("tools/stack.md", "use Memvid for semantic search")])
    assert kept == [] and reasons == {"quote_not_found": 1}
