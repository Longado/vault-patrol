"""Load a markdown vault into an immutable snapshot. Pure code, no LLM."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

INDEX_CANDIDATES = ("MEMORY.md", "INDEX.md", "index.md", "README.md")
IGNORE_FILE = ".patrolignore"
MD_LINK_RE = re.compile(r"\]\(([^)\s#]+?\.md)(?:#[^)]*)?\)")
WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
MD_DIR_LINK_RE = re.compile(r"\]\(([^)\s#]+/)\)")
MAX_FILE_BYTES = 64_000
DATED_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
FRONTMATTER_DATE_RE = re.compile(r"^date:", re.MULTILINE)
RECORD_DIR_WORDS = ("study", "research", "log", "archive", "history")


@dataclass(frozen=True)
class Note:
    rel_path: str
    text: str

    @property
    def stem(self) -> str:
        return Path(self.rel_path).stem

    @property
    def is_record(self) -> bool:
        """A dated log rather than a live instruction. Records are allowed to describe a dead
        project in the present tense — that is what a record is for — so the stale/falsified
        checks skip them. Decided by the filename, the frontmatter and the folder, never by
        the model."""
        path = Path(self.rel_path)
        if DATED_NAME_RE.match(path.name):
            return True
        if self.text.startswith("---"):
            end = self.text.find("\n---", 3)
            if end != -1 and FRONTMATTER_DATE_RE.search(self.text[:end]):
                return True
        return any(w in part.lower() for part in path.parts[:-1] for w in RECORD_DIR_WORDS)


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


def ignore_patterns(root: Path) -> tuple[str, ...]:
    """gitignore-style lines from .patrolignore. Blank lines and `#` comments are skipped."""
    f = root / IGNORE_FILE
    if not f.is_file():
        return ()
    lines = (ln.strip() for ln in f.read_text(encoding="utf-8", errors="replace").splitlines())
    return tuple(ln for ln in lines if ln and not ln.startswith("#"))


def is_ignored(rel_path: str, patterns: tuple[str, ...]) -> bool:
    """Match the path itself, and every parent directory written with a trailing slash."""
    parts = rel_path.split("/")
    candidates = [rel_path] + ["/".join(parts[: i + 1]) + "/" for i in range(len(parts) - 1)]
    return any(fnmatch(c, pat) for c in candidates for pat in patterns)


def load_vault(root: Path) -> Vault:
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"vault root not found: {root}")
    patterns = ignore_patterns(root)
    notes = []
    for p in sorted(root.rglob("*.md")):
        rel = nfc(str(p.relative_to(root)))
        if any(part.startswith(".") for part in p.relative_to(root).parts):
            continue
        if is_ignored(rel, patterns):
            continue
        raw = p.read_bytes()[:MAX_FILE_BYTES]
        notes.append(Note(rel, raw.decode("utf-8", errors="replace")))
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
