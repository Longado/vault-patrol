"""Load a markdown vault into an immutable snapshot. Pure code, no LLM."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

INDEX_CANDIDATES = ("MEMORY.md", "INDEX.md", "index.md", "README.md")
MD_LINK_RE = re.compile(r"\]\(([^)\s#]+?\.md)(?:#[^)]*)?\)")
WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
MD_DIR_LINK_RE = re.compile(r"\]\(([^)\s#]+/)\)")
MAX_FILE_BYTES = 64_000


@dataclass(frozen=True)
class Note:
    rel_path: str
    text: str

    @property
    def stem(self) -> str:
        return Path(self.rel_path).stem


@dataclass(frozen=True)
class Vault:
    root: Path
    notes: tuple[Note, ...]
    index_path: str | None

    def get(self, rel_path: str) -> Note | None:
        return next((n for n in self.notes if n.rel_path == rel_path), None)

    @property
    def index(self) -> Note | None:
        return self.get(self.index_path) if self.index_path else None


def nfc(s: str) -> str:
    """macOS writes NFD paths; normalise before any comparison."""
    return unicodedata.normalize("NFC", s)


def load_vault(root: Path) -> Vault:
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"vault root not found: {root}")
    notes = []
    for p in sorted(root.rglob("*.md")):
        if any(part.startswith(".") for part in p.relative_to(root).parts):
            continue
        raw = p.read_bytes()[:MAX_FILE_BYTES]
        notes.append(Note(nfc(str(p.relative_to(root))), raw.decode("utf-8", errors="replace")))
    index_path = next((c for c in INDEX_CANDIDATES if (root / c).is_file()), None)
    return Vault(root=root, notes=tuple(notes), index_path=index_path)


def md_links(note: Note) -> tuple[str, ...]:
    """Relative markdown links to .md files, resolved against the note's directory."""
    base = Path(note.rel_path).parent
    return tuple(nfc(str((base / m).as_posix())).replace("./", "") for m in MD_LINK_RE.findall(note.text))


def wiki_links(note: Note) -> tuple[str, ...]:
    return tuple(nfc(m.strip()) for m in WIKI_LINK_RE.findall(note.text))


def folder_links(note: Note) -> tuple[str, ...]:
    """Links to a directory rather than a file, e.g. `[sources/](sources/)`.
    An index bullet pointing at a folder vouches for everything inside it."""
    base = Path(note.rel_path).parent
    return tuple(nfc(str((base / m).as_posix())).replace("./", "").rstrip("/") + "/"
                 for m in MD_DIR_LINK_RE.findall(note.text))
