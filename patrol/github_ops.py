"""Git + GitHub side effects. Called by code after judgment, never from inside the model call."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import requests

API = "https://api.github.com"
BOT_NAME = "vault-patrol[bot]"
BOT_EMAIL = "vault-patrol@users.noreply.github.com"


def _token() -> str:
    t = os.getenv("GITHUB_TOKEN")
    if not t:
        raise RuntimeError("GITHUB_TOKEN is required for clone/push/PR")
    return t


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def clone(repo_full: str, dest: Path, ref: str | None = None) -> str:
    """Clone owner/name into dest, return HEAD sha."""
    url = f"https://x-access-token:{_token()}@github.com/{repo_full}.git"
    subprocess.run(["git", "clone", "--quiet", "--depth", "50", url, str(dest)], check=True, capture_output=True)
    if ref:
        _git(dest, "checkout", "--quiet", ref)
    return _git(dest, "rev-parse", "HEAD")


def push_branch(dest: Path, branch: str, files: list[str], message: str) -> None:
    _git(dest, "config", "user.name", BOT_NAME)
    _git(dest, "config", "user.email", BOT_EMAIL)
    _git(dest, "checkout", "--quiet", "-B", branch)
    _git(dest, "add", "--", *files)
    _git(dest, "commit", "--quiet", "-m", message)
    _git(dest, "push", "--quiet", "--force", "origin", branch)


def open_pr(repo_full: str, branch: str, base: str, title: str, body: str) -> str:
    h = {"Authorization": f"Bearer {_token()}", "Accept": "application/vnd.github+json"}
    existing = requests.get(f"{API}/repos/{repo_full}/pulls", headers=h,
                            params={"head": f"{repo_full.split('/')[0]}:{branch}", "state": "open"}, timeout=30)
    existing.raise_for_status()
    if existing.json():
        pr = existing.json()[0]
        requests.patch(pr["url"], headers=h, json={"title": title, "body": body}, timeout=30).raise_for_status()
        return pr["html_url"]
    r = requests.post(f"{API}/repos/{repo_full}/pulls", headers=h,
                      json={"title": title, "head": branch, "base": base, "body": body}, timeout=30)
    r.raise_for_status()
    return r.json()["html_url"]


def default_branch(repo_full: str) -> str:
    h = {"Authorization": f"Bearer {_token()}", "Accept": "application/vnd.github+json"}
    r = requests.get(f"{API}/repos/{repo_full}", headers=h, timeout=30)
    r.raise_for_status()
    return r.json()["default_branch"]
