"""Small deterministic adapters for tests and early application bring-up."""

from __future__ import annotations

from dataclasses import dataclass, field

from contextmap2_embodied.contracts import TargetQuery
from contextmap2_embodied.models import (
    NavigationResult,
    Pose2D,
    QueryCandidate,
    QueryResolution,
    ResolvedNavigationTarget,
)


@dataclass
class InMemoryContextMap:
    """Fixture-only query and grounding adapter keyed by semantic label or entity id."""

    semantic_index: dict[str, tuple[str, ...]]
    targets: dict[str, ResolvedNavigationTarget]

    def resolve(self, query: TargetQuery) -> QueryResolution:
        """Resolve the small selector subset used by deterministic unit tests."""
        selector = query.selector
        if selector.kind == "entity":
            ids = (selector.entity_id,) if selector.entity_id in self.targets else ()
        else:
            ids = self.semantic_index.get(selector.label, ())

        candidates = tuple(
            QueryCandidate(entity_id=entity_id, semantic_labels=())
            for entity_id in ids
            if entity_id in self.targets
        )

        if len(candidates) == 1:
            return QueryResolution(status="resolved", candidates=candidates)
        if not candidates:
            return QueryResolution(status="not_found", detail="no matching fixture entity")
        return QueryResolution(
            status="ambiguous",
            candidates=candidates,
            detail="fixture query matched multiple entities",
        )

    def ground(self, entity_id: str) -> ResolvedNavigationTarget:
        """Return the pre-grounded fixture target."""
        return self.targets[entity_id]


@dataclass
class RecordingNavigator:
    """Navigator fake that records high-level goals in execution order."""

    visited: list[str] = field(default_factory=list)
    fail_on_entity: str | None = None

    def navigate_to(self, target: ResolvedNavigationTarget) -> NavigationResult:
        """Record one navigation request and optionally inject a failure."""
        self.visited.append(target.entity_id)
        if target.entity_id == self.fail_on_entity:
            return NavigationResult(status="failed", detail="injected navigation failure")
        return NavigationResult(
            status="succeeded",
            final_pose=Pose2D(
                frame_id=target.pose.frame_id,
                x=target.pose.x,
                y=target.pose.y,
                yaw=target.pose.yaw,
            ),
        )
