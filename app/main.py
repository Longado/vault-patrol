"""Cloud Run service: GitHub push webhook → background patrol → PR."""
from __future__ import annotations

import hashlib
import hmac
import logging
import os

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

from patrol.runner import BRANCH, patrol_repo

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
log = logging.getLogger("vault-patrol")
app = FastAPI(title="vault-patrol")


def _verify(body: bytes, signature: str | None) -> None:
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(500, "GITHUB_WEBHOOK_SECRET not configured")
    if not signature or not signature.startswith("sha256="):
        raise HTTPException(401, "missing signature")
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(401, "bad signature")


def _run(repo: str, ref: str | None) -> None:
    try:
        result, pr = patrol_repo(repo, ref)
        log.info("patrolled %s @ %s: %d mechanical / %d semantic / %d dropped → %s",
                 repo, result.anchor_sha, len(result.mechanical), len(result.semantic), result.dropped, pr)
    except Exception:
        log.exception("patrol failed for %s", repo)


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.post("/webhook")
async def webhook(request: Request, bg: BackgroundTasks,
                  x_hub_signature_256: str | None = Header(default=None),
                  x_github_event: str | None = Header(default=None)) -> dict:
    body = await request.body()
    _verify(body, x_hub_signature_256)
    if x_github_event == "ping":
        return {"status": "pong"}
    if x_github_event != "push":
        return {"status": "ignored", "event": x_github_event}
    payload = await request.json()
    repo = payload.get("repository", {}).get("full_name")
    ref = payload.get("ref", "")
    if not repo:
        raise HTTPException(400, "no repository in payload")
    if ref.endswith(BRANCH) or "vault-patrol" in payload.get("pusher", {}).get("name", ""):
        return {"status": "ignored", "reason": "own branch"}
    default = payload.get("repository", {}).get("default_branch", "main")
    if ref != f"refs/heads/{default}":
        return {"status": "ignored", "reason": f"not default branch ({ref})"}
    bg.add_task(_run, repo, payload.get("after"))
    return {"status": "accepted", "repo": repo, "sha": payload.get("after")}


class RunRequest(BaseModel):
    repo: str
    ref: str | None = None


@app.post("/run")
def run_now(req: RunRequest, bg: BackgroundTasks, authorization: str | None = Header(default=None)) -> dict:
    """Manual trigger for demos; protected by the same shared secret."""
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if not secret or authorization != f"Bearer {secret}":
        raise HTTPException(401, "unauthorized")
    if "/" not in req.repo:
        raise HTTPException(400, "repo must be owner/name")
    bg.add_task(_run, req.repo, req.ref)
    return {"status": "accepted", "repo": req.repo}
