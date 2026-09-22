"""Domain models shared by query, grounding, and execution layers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DomainModel(BaseModel):
    """Strict immutable model used across deterministic layers."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Pose2D(DomainModel):
    """Navigation pose expressed in a named frame."""

    frame_id: str = Field(min_length=1)
    x: float
    y: float
    yaw: float = 0.0


class QueryCandidate(DomainModel):
    """One candidate returned by the ContextMap query layer."""

    entity_id: str = Field(min_length=1)
    semantic_labels: tuple[str, ...] = ()
    relation_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


class QueryResolution(DomainModel):
    """Deterministic outcome of resolving one target query."""

    status: Literal["resolved", "not_found", "ambiguous"]
    candidates: tuple[QueryCandidate, ...] = ()
    detail: str = ""

    @property
    def resolved_entity_id(self) -> str | None:
        """Return the selected entity only when resolution is unique."""
        if self.status != "resolved" or len(self.candidates) != 1:
            return None
        return self.candidates[0].entity_id


class ResolvedNavigationTarget(DomainModel):
    """ContextMap entity grounded to one safe navigation pose."""

    entity_id: str = Field(min_length=1)
    pose: Pose2D
    derivation: str = Field(min_length=1)
    evidence_refs: tuple[str, ...] = ()


class NavigationResult(DomainModel):
    """Result returned by the navigation adapter."""

    status: Literal["succeeded", "failed", "cancelled"]
    final_pose: Pose2D | None = None
    detail: str = ""
