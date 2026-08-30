from patrol.mechanical import broken_index_links, dangling_wikilinks, orphans
from patrol.models import Category
from patrol.vault import load_vault


def test_broken_index_link_found(demo_vault):
    targets = {f.related_files[0] for f in broken_index_links(demo_vault)}
    assert targets == {"notes/planner_2025.md"}  # planning_v1.md exists; planner_2025.md is the seeded dead link


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


def test_note_linked_only_from_another_note_is_not_orphan(tmp_path):
    """Reachability is vault-wide: the index need not name every file directly."""
    (tmp_path / "MEMORY.md").write_text("- [Hub](hub.md)\n")
    (tmp_path / "hub.md").write_text("See [deep note](sub/deep.md) and [[sibling]].\n")
    (tmp_path / "sibling.md").write_text("sibling\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub/deep.md").write_text("deep\n")
    (tmp_path / "lonely.md").write_text("nobody links me\n")

    found = {f.file for f in orphans(load_vault(tmp_path))}
    assert found == {"lonely.md"}


def test_folder_bullet_in_index_vouches_for_its_contents(tmp_path):
    (tmp_path / "MEMORY.md").write_text("- [sources/](sources/) — raw material\n")
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources/a.md").write_text("a\n")
    (tmp_path / "sources/b.md").write_text("b\n")
    (tmp_path / "stray.md").write_text("stray\n")

    found = {f.file for f in orphans(load_vault(tmp_path))}
    assert found == {"stray.md"}
