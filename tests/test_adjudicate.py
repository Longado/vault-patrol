from patrol.adjudicate import adjudicate
from patrol.models import Action, Category, Finding


COUNTER_FILE = "notes/changelog.md"
COUNTER_QUOTE = "2026-07-03: llm-wiki daemon retired."


def _f(file, quote, verdict="rot", *, category=Category.STALE_ACTIVE_REFERENCE,
       counter_file=COUNTER_FILE, counter_quote=COUNTER_QUOTE):
    return Finding(reasoning="r", category=category, file=file, evidence_quote=quote,
                   counter_evidence_file=counter_file, counter_evidence_quote=counter_quote,
                   proposed_action=Action.MARK_HISTORICAL, verdict=verdict)


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


def test_cross_note_finding_without_counter_quote_is_dropped(demo_vault):
    kept, reasons = adjudicate(demo_vault, [
        _f("tools/memvid.md", "Status: live.", counter_file="", counter_quote="")])
    assert kept == [] and reasons == {"counter_evidence_missing": 1}


def test_counter_quote_pointing_at_itself_is_dropped(demo_vault):
    kept, reasons = adjudicate(demo_vault, [
        _f("tools/memvid.md", "Status: live.",
           counter_file="tools/memvid.md", counter_quote="Status: live.")])
    assert kept == [] and reasons == {"counter_evidence_missing": 1}


def test_invented_counter_quote_is_dropped(demo_vault):
    """The hole this closes: a real quote carrying a rationale nothing in the vault supports."""
    kept, reasons = adjudicate(demo_vault, [
        _f("tools/memvid.md", "Status: live.",
           counter_quote="2026-07-03: memvid deleted from disk after review.")])
    assert kept == [] and reasons == {"counter_evidence_not_found": 1}


def test_real_counter_quote_is_kept(demo_vault):
    kept, reasons = adjudicate(demo_vault, [
        _f("tools/memvid.md", "Status: live.",
           counter_quote="2026-07-03: Memvid MCP server removed from settings.json")])
    assert len(kept) == 1 and reasons == {}


def test_pinned_old_version_needs_no_counter_quote(demo_vault):
    kept, reasons = adjudicate(demo_vault, [
        _f("tools/llm_starter.md", 'MODEL = "claude-3-5-sonnet-20240620"',
           category=Category.PINNED_OLD_VERSION, counter_file="", counter_quote="")])
    assert len(kept) == 1 and reasons == {}
