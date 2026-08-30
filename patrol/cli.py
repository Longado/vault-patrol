"""Local entry point. Same code path the Cloud Run service uses."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .report import render_report
from .runner import patrol_path, patrol_repo


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vault-patrol")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run", help="patrol a local vault directory, print report")
    p.add_argument("path")
    p.add_argument("--no-model", action="store_true", help="mechanical layer only")
    r = sub.add_parser("repo", help="clone owner/name, patrol, open PR")
    r.add_argument("repo")
    r.add_argument("--ref")
    r.add_argument("--no-model", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if a.cmd == "run":
        res = patrol_path(Path(a.path), use_model=not a.no_model)
        print(render_report(res))
        return 0
    res, pr = patrol_repo(a.repo, a.ref, use_model=not a.no_model)
    print(render_report(res))
    print(f"PR: {pr or 'none (clean or already patrolled)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
