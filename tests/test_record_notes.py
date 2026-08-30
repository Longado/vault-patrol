"""A dated log is never 'out of date' — it records what was true on its date."""
import pytest

from patrol.adjudicate import adjudicate
from patrol.models import Action, Category, Finding
from patrol.vault import load_vault

STALE_LINE = "Use the memvid MCP server for every semantic lookup.\n"
COUNTER = "2026-07-03: memvid removed from settings.json.\n"


def _vault(tmp_path, note_name, body=STALE_LINE):
    (tmp_path / "MEMORY.md").write_text("- [changelog](changelog.md)\n")
    (tmp_path / "changelog.md").write_text(COUNTER)
    (tmp_path / note_name).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / note_name).write_text(body)
    return load_vault(tmp_path)


def _f(file):
    return Finding(reasoning="r", category=Category.STALE_ACTIVE_REFERENCE, file=file,
                   evidence_quote=STALE_LINE.strip(), counter_evidence_file="changelog.md",
                   counter_evidence_quote=COUNTER.strip(),
                   proposed_action=Action.MARK_HISTORICAL, verdict="rot")


@pytest.mark.parametrize("name,body", [
    ("2026-04-19-notes.md", STALE_LINE),                       # dated filename
    ("study_notes.md", "---\ndate: 2026-04-19\n---\n" + STALE_LINE),  # frontmatter date
    ("ai_native_study/deep.md", STALE_LINE),                   # folder named ...study...
    ("research/deep.md", STALE_LINE),
    ("archive/deep.md", STALE_LINE),
])
def test_stale_finding_on_a_record_note_is_dropped(tmp_path, name, body):
    v = _vault(tmp_path, name, body)
    assert v.get(name).is_record
    kept, reasons = adjudicate(v, [_f(name)])
    assert kept == [] and reasons == {"record_note": 1}


def test_same_text_in_a_live_note_is_kept(tmp_path):
    v = _vault(tmp_path, "stack.md")
    assert not v.get("stack.md").is_record
    kept, reasons = adjudicate(v, [_f("stack.md")])
    assert len(kept) == 1 and reasons == {}


def test_record_note_can_still_serve_as_counter_evidence(tmp_path):
    """Records are excluded as targets, not as proof."""
    (tmp_path / "MEMORY.md").write_text("- [stack](stack.md)\n")
    (tmp_path / "stack.md").write_text(STALE_LINE)
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs/2026-07-03-changes.md").write_text(COUNTER)
    v = load_vault(tmp_path)

    f = _f("stack.md").model_copy(update={"counter_evidence_file": "logs/2026-07-03-changes.md"})
    kept, reasons = adjudicate(v, [f])
    assert len(kept) == 1 and reasons == {}
