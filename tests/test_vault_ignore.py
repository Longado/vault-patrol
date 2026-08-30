"""`.patrolignore` keeps whole folders out of the snapshot entirely."""
from patrol.vault import load_vault


def test_patrolignore_excludes_folders_and_globs(tmp_path):
    (tmp_path / ".patrolignore").write_text("# raw material, never rot\nsources/\n*.draft.md\n")
    (tmp_path / "MEMORY.md").write_text("- [keep](keep.md)\n")
    (tmp_path / "keep.md").write_text("keep\n")
    (tmp_path / "notes.draft.md").write_text("draft\n")
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources/dump.md").write_text("dump\n")
    (tmp_path / "sources/nested").mkdir()
    (tmp_path / "sources/nested/deep.md").write_text("deep\n")

    paths = {n.rel_path for n in load_vault(tmp_path).notes}
    assert paths == {"MEMORY.md", "keep.md"}
