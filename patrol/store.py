"""Firestore anchor store. Optional: unset FIRESTORE_COLLECTION and nothing is written."""
from __future__ import annotations

import datetime as dt
import logging
import os

from .models import PatrolResult

log = logging.getLogger(__name__)


def record_run(repo: str, result: PatrolResult, pr_url: str | None) -> None:
    coll = os.getenv("FIRESTORE_COLLECTION")
    if not coll:
        return
    try:
        from google.cloud import firestore  # imported lazily so local runs need no GCP creds

        db = firestore.Client()
        db.collection(coll).add({
            "repo": repo,
            "anchor_sha": result.anchor_sha,
            "pr_url": pr_url,
            "mechanical": len(result.mechanical),
            "semantic": len(result.semantic),
            "dropped": result.dropped,
            "model_version": result.model_version,
            "prompt_version": result.prompt_version,
            "ran_at": dt.datetime.now(dt.timezone.utc),
        })
    except Exception as e:  # never let bookkeeping break the patrol
        log.warning("firestore write failed: %s", e)


def last_anchor(repo: str) -> str | None:
    coll = os.getenv("FIRESTORE_COLLECTION")
    if not coll:
        return None
    try:
        from google.cloud import firestore

        db = firestore.Client()
        q = db.collection(coll).where("repo", "==", repo).order_by("ran_at", direction="DESCENDING").limit(1)
        docs = list(q.stream())
        return docs[0].to_dict().get("anchor_sha") if docs else None
    except Exception as e:
        log.warning("firestore read failed: %s", e)
        return None
