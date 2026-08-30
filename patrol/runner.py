"""Control flow. Every loop and retry is here; the model is called exactly once per patrol."""
from __future__ import annotations

import logging
import shutil
import tempfile
import time
from pathlib import Path

from google.genai import errors as genai_errors
from pydantic import ValidationError

from . import github_ops
from .adjudicate import adjudicate
from .mechanical import run_mechanical
from .models import PatrolResult
from .report import REPORT_NAME, write_pr_files
from .semantic import judge, prompt_version
from .vault import load_vault

log = logging.getLogger(__name__)
BRANCH = "vault-patrol/report"
MODEL_RETRIES = 2


def _is_transient(e: Exception) -> bool:
    """Retry rate limits, server faults and transport hiccups. A malformed schema or a
    bad key will fail identically on the next attempt, so surface it immediately."""
    if isinstance(e, ValidationError):
        return False
    if isinstance(e, genai_errors.APIError):
        return e.code == 429 or e.code >= 500
    return True


def patrol_path(root: Path, anchor_sha: str | None = None, use_model: bool = True) -> PatrolResult:
    v = load_vault(root)
    mechanical = run_mechanical(v)
    semantic, dropped, model_id, truncated = [], 0, None, 0
    if use_model:
        for attempt in range(MODEL_RETRIES + 1):
            try:
                report, model_id, truncated = judge(v)
                semantic, dropped = adjudicate(v, report.findings)
                break
            except Exception as e:
                if not _is_transient(e):
                    log.error("model call failed permanently: %s", e)
                    raise
                log.warning("model call failed (attempt %d): %s", attempt + 1, e)
                if attempt == MODEL_RETRIES:
                    raise
                time.sleep(2 * (attempt + 1))
    return PatrolResult(
        anchor_sha=anchor_sha, vault=str(root), mechanical=mechanical, semantic=semantic,
        dropped=dropped, notes_truncated=truncated, model_version=model_id,
        prompt_version=prompt_version(),
    )


def patrol_repo(repo_full: str, ref: str | None = None, use_model: bool = True) -> tuple[PatrolResult, str | None]:
    """Clone → patrol → PR. Returns (result, pr_url). Re-running updates the open PR
    instead of opening a second one, so repeated pushes stay idempotent."""
    work = Path(tempfile.mkdtemp(prefix="patrol-"))
    try:
        sha = github_ops.clone(repo_full, work, ref)
        result = patrol_path(work, sha, use_model=use_model)
        if not result.mechanical and not result.semantic:
            return result, None
        v = load_vault(work)
        files = write_pr_files(work, v, result)
        github_ops.push_branch(work, BRANCH, files, f"patrol: {len(result.mechanical)} mechanical, {len(result.semantic)} semantic findings @ {sha[:7]}")
        body = (work / REPORT_NAME).read_text()
        pr_url = github_ops.open_pr(
            repo_full, BRANCH, github_ops.default_branch(repo_full),
            f"Vault patrol: {len(result.mechanical) + len(result.semantic)} rot findings", body,
        )
        return result, pr_url
    finally:
        shutil.rmtree(work, ignore_errors=True)
