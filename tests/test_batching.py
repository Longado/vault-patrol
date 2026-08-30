"""Batching replaces truncation: every note gets sent, with the index in every batch."""
from patrol import semantic
from patrol.vault import load_vault


def _vault(tmp_path, n_notes, note_chars):
    (tmp_path / "MEMORY.md").write_text("# index\n")
    for i in range(n_notes):
        (tmp_path / f"n{i}.md").write_text("x" * note_chars + "\n")
    return load_vault(tmp_path)


def test_large_vault_is_split_and_every_note_is_sent(tmp_path, monkeypatch):
    monkeypatch.setattr(semantic, "MAX_CONTEXT_CHARS", 1_000)
    v = _vault(tmp_path, n_notes=10, note_chars=300)

    batches, oversized = semantic.plan_batches(v)

    assert oversized == []
    assert len(batches) > 1
    assert all(b[0].rel_path == "MEMORY.md" for b in batches)  # index prepended to each batch
    sent = {n.rel_path for b in batches for n in b}
    assert sent == {n.rel_path for n in v.notes}  # nothing dropped on the floor


def test_note_too_big_for_one_call_is_reported_not_silently_cut(tmp_path, monkeypatch):
    monkeypatch.setattr(semantic, "MAX_CONTEXT_CHARS", 1_000)
    v = _vault(tmp_path, n_notes=1, note_chars=5_000)

    batches, oversized = semantic.plan_batches(v)

    assert [n.rel_path for n in oversized] == ["n0.md"]
    assert all("n0.md" not in {n.rel_path for n in b} for b in batches)


def test_max_notes_per_batch_env_knob_caps_batch_size(tmp_path, monkeypatch):
    monkeypatch.setenv("PATROL_MAX_NOTES_PER_BATCH", "3")
    v = _vault(tmp_path, n_notes=10, note_chars=10)  # would fit one batch on chars alone

    batches, oversized = semantic.plan_batches(v)

    assert oversized == []
    assert len(batches) == 4  # 3 + 3 + 3 + 1, index note excluded from the count
    assert all(len(b) <= 4 for b in batches)  # index + at most 3
