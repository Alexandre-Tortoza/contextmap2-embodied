"""Typed boundaries between language interpretation and deterministic execution.

These contracts are intentionally independent of ROS, Gazebo, RAI, and the ContextMap2
filesystem layout. External adapters translate their native representations into these models.
"""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

RelationPredicateName: TypeAlias = Literal[
    "next_to",
    "above",
    "below",
    "in_front_of",
    "behind",
    "inside",
    "contains",
    "intersects",
    "touching",
    "on_top_of",
    "leaning_against",
]
"""Canonical relation names currently exported by ContextMap2's relation taxonomy."""


class ContractModel(BaseModel):
    """Base model with strict, immutable contract semantics."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class SemanticSelector(ContractModel):
    """Select candidates by an open-vocabulary semantic label."""

    kind: Literal["semantic"] = "semantic"
    label: str = Field(min_length=1)


class EntitySelector(ContractModel):
    """Select one entity by its ContextMap-scoped identifier."""

    kind: Literal["entity"] = "entity"
    entity_id: str = Field(min_length=1)


TargetSelector = Annotated[
    SemanticSelector | EntitySelector,
    Field(discriminator="kind"),
]


class RelationConstraint(ContractModel):
    """Require a canonical ContextMap relation to another selected entity.

    Direction is preserved exactly as ContextMap2 stores it: candidate predicate object.
    """

    predicate: RelationPredicateName
    object: TargetSelector


class ContainsConstraint(ContractModel):
    """Require a container candidate to contain a number of semantic entities."""

    semantic: str = Field(min_length=1)
    min_count: int = Field(default=1, ge=1)
    max_count: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_count_range(self) -> ContainsConstraint:
        """Reject an inverted cardinality range."""
        if self.max_count is not None and self.max_count < self.min_count:
            raise ValueError("max_count must be greater than or equal to min_count")
        return self


class TargetQuery(ContractModel):
    """Deterministic query that the ContextMap adapter must evaluate."""

    selector: TargetSelector
    relations: tuple[RelationConstraint, ...] = ()
    contains: tuple[ContainsConstraint, ...] = ()


class ResolveTarget(ContractModel):
    """Resolve a symbolic target from the ContextMap artifact."""

    kind: Literal["resolve_target"] = "resolve_target"
    name: str = Field(min_length=1, pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")
    query: TargetQuery


class NavigateTo(ContractModel):
    """Navigate to a target previously resolved by name."""

    kind: Literal["navigate_to"] = "navigate_to"
    target: str = Field(min_length=1, pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")


ExecutableStep = Annotated[
    ResolveTarget | NavigateTo,
    Field(discriminator="kind"),
]


class Repeat(ContractModel):
    """Repeat a bounded sequence of deterministic high-level actions."""

    kind: Literal["repeat"] = "repeat"
    count: int = Field(ge=1, le=100)
    steps: tuple[ExecutableStep, ...] = Field(min_length=1)


MissionStep = Annotated[
    ResolveTarget | NavigateTo | Repeat,
    Field(discriminator="kind"),
]


class MissionPlan(ContractModel):
    """Versioned, replayable mission boundary.

    The LLM may propose this object, but robot motion only begins after it validates and passes
    later semantic and navigation preflight checks.
    """

    schema_version: Literal["mission-plan-v1"] = "mission-plan-v1"
    steps: tuple[MissionStep, ...] = Field(min_length=1)
