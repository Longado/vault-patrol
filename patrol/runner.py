"""Control flow. Every loop and retry is here; the model is called exactly once per patrol."""
from __future__ import annotations

import logging
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from google.genai import errors as genai_errors
from pydantic import ValidationError

from . import github_ops
from .adjudicate import adjudicate
from .mechanical import run_mechanical
from .models import PatrolResult
from .report import render_pr_body, write_pr_files
from .semantic import judge, plan_batches, prompt_version
from .vault import load_vault

log = logging.getLogger(__name__)
BRANCH = "vault-patrol/report"
MODEL_RETRIES = 2
MAX_PARALLEL_CALLS = 4


def _is_transient(e: Exception) -> bool:
    """Retry rate limits, server faults and transport hiccups. A malformed schema or a
    bad key will fail identically on the next attempt, so surface it immediately."""
    if isinstance(e, ValidationError):
        return False
    if isinstance(e, genai_errors.APIError):
        return e.code == 429 or e.code >= 500
    return True


def _judge_with_retry(notes: list) -> tuple[list, str]:
    """One batch, retried in place. Returns (findings, model_id)."""
    for attempt in range(MODEL_RETRIES + 1):
        try:
            report, model_id = judge(notes)
            return report.findings, model_id
        except Exception as e:
            if not _is_transient(e):
                log.error("model call failed permanently: %s", e)
                raise
            log.warning("model call failed (attempt %d): %s", attempt + 1, e)
            if attempt == MODEL_RETRIES:
                raise
            time.sleep(2 * (attempt + 1))
    raise AssertionError("unreachable")


def patrol_path(root: Path, anchor_sha: str | None = None, use_model: bool = True) -> PatrolResult:
    v = load_vault(root)
    mechanical = run_mechanical(v)
    semantic, reasons, model_id, truncated, calls = [], {}, None, 0, 0
    if use_model:
        batches, oversized = plan_batches(v)
        truncated, calls = len(oversized), len(batches)
        log.info("semantic layer: %d note(s) in %d batch(es)", len(v.notes), calls)
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_CALLS) as pool:
            results = list(pool.map(_judge_with_retry, batches))
        proposed = [f for findings, _ in results for f in findings]
        model_id = next((m for _, m in results), None)
        semantic, reasons = adjudicate(v, proposed)
    return PatrolResult(
        anchor_sha=anchor_sha, vault=str(root), mechanical=mechanical, semantic=semantic,
        dropped=sum(reasons.values()), drop_reasons=reasons, notes_truncated=truncated,
        model_calls=calls, model_version=model_id, prompt_version=prompt_version(),
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
        pr_url = github_ops.open_pr(
            repo_full, BRANCH, github_ops.default_branch(repo_full),
            f"Vault patrol: {len(result.mechanical) + len(result.semantic)} rot findings",
            render_pr_body(result),
        )
        return result, pr_url
    finally:
        shutil.rmtree(work, ignore_errors=True)
