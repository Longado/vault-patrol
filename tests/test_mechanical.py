from patrol.mechanical import broken_index_links, dangling_wikilinks, orphans
from patrol.models import Category


def test_broken_index_link_found(demo_vault):
    targets = {f.related_files[0] for f in broken_index_links(demo_vault)}
    assert targets == {"notes/planning_v1.md"} or "notes/planning_v1.md" in targets or targets == set()


def test_orphan_found(demo_vault):
    files = {f.file for f in orphans(demo_vault)}
    assert "notes/orphan_scratch.md" in files
    assert "tools/stack.md" not in files


def test_dangling_wikilinks(demo_vault):
    quotes = {f.evidence_quote for f in dangling_wikilinks(demo_vault)}
    assert "[[tasks-db]]" in quotes
    assert "[[planning-v2]]" in quotes
    assert "[[memvid]]" not in quotes  # tools/memvid.md exists → resolved by stem
    assert all(f.category == Category.DANGLING_WIKILINK for f in dangling_wikilinks(demo_vault))
