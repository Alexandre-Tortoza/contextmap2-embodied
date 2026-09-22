"""Ports isolating deterministic application logic from external runtimes."""

from __future__ import annotations

from typing import Protocol

from contextmap2_embodied.contracts import TargetQuery
from contextmap2_embodied.models import (
    NavigationResult,
    QueryResolution,
    ResolvedNavigationTarget,
)


class ContextQueryPort(Protocol):
    """Semantic/graph query boundary for one loaded ContextMap artifact."""

    def resolve(self, query: TargetQuery) -> QueryResolution:
        """Resolve a typed query without inventing missing semantics."""


class TargetGroundingPort(Protocol):
    """Boundary that converts one resolved entity into a navigation target."""

    def ground(self, entity_id: str) -> ResolvedNavigationTarget:
        """Ground an entity to a navigation pose with an explicit derivation."""


class NavigatorPort(Protocol):
    """High-level navigation boundary.

    Implementations may wrap Nav2, a simulator fake, or another deterministic navigation stack.
    The port deliberately contains no velocity command API.
    """

    def navigate_to(self, target: ResolvedNavigationTarget) -> NavigationResult:
        """Navigate to one already-grounded target pose."""
