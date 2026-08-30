"""Structured contracts between code and the model. reasoning comes FIRST on purpose."""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Category(str, Enum):
    # mechanical (code-detected)
    BROKEN_LINK = "broken_link"
    ORPHAN = "orphan"
    DANGLING_WIKILINK = "dangling_wikilink"
    # semantic (model-judged, code-verified)
    STALE_ACTIVE_REFERENCE = "stale_active_reference"
    PINNED_OLD_VERSION = "pinned_old_version"
    OVERLAP_CLUSTER = "overlap_cluster"
    HARD_CONFLICT = "hard_conflict"
    FALSIFIED_CLAIM = "falsified_claim"


class Action(str, Enum):
    """Subtraction-only. The agent may never propose new tasks or new notes."""
    DELETE_LINE = "delete_line"
    MARK_HISTORICAL = "mark_historical"
    MERGE_INTO = "merge_into"
    ADD_ARBITRATION_LINE = "add_arbitration_line"
    NEEDS_HUMAN = "needs_human"


class Finding(BaseModel):
    reasoning: str = Field(description="Why this is rot. Written before the verdict.")
    category: Category
    file: str = Field(description="Vault-relative path of the primary file.")
    evidence_quote: str = Field(description="Verbatim substring copied from `file` that proves the finding. Must exist exactly.")
    related_files: list[str] = Field(default_factory=list)
    proposed_action: Action
    verdict: Literal["rot", "unsure"] = Field(description="'unsure' when evidence is ambiguous; code will drop it.")


class SemanticReport(BaseModel):
    reasoning: str
    findings: list[Finding]


class PatrolResult(BaseModel):
    anchor_sha: str | None
    vault: str
    mechanical: list[Finding]
    semantic: list[Finding]
    dropped: int = Field(description="Model findings rejected by code-level verification.")
    notes_truncated: int = Field(default=0, description="Notes the model never saw because the vault exceeded the context budget.")
    model_version: str | None
    prompt_version: str
