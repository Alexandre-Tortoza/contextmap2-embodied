"""Deterministic MissionPlan execution.

The executor contains no LLM, ROS, or Gazebo dependency. It consumes typed ports so the exact
same plan can be tested with fakes and later executed through ContextMap2 + Nav2 adapters.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from contextmap2_embodied.contracts import MissionPlan, NavigateTo, Repeat, ResolveTarget
from contextmap2_embodied.models import NavigationResult, ResolvedNavigationTarget
from contextmap2_embodied.ports import ContextQueryPort, NavigatorPort, TargetGroundingPort


class ExecutionError(RuntimeError):
    """Base class for deterministic mission execution failures."""


class TargetResolutionError(ExecutionError):
    """Raised when a symbolic query cannot be resolved uniquely."""


class UnknownTargetError(ExecutionError):
    """Raised when a navigation step refers to an unresolved symbol."""


class NavigationExecutionError(ExecutionError):
    """Raised when the navigation adapter reports a non-success result."""


class _ExecutionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StepRecord(_ExecutionModel):
    """Audit record for one executed high-level step."""

    path: str
    kind: Literal["resolve_target", "navigate_to"]
    status: Literal["succeeded", "failed"]
    symbol: str
    entity_id: str | None = None
    detail: str = ""


class MissionExecutionReport(_ExecutionModel):
    """Machine-readable deterministic execution result."""

    status: Literal["succeeded", "failed"]
    records: tuple[StepRecord, ...]
    completed_navigation_steps: int
    failure: str | None = None


class MissionExecutor:
    """Execute a validated mission using deterministic ports."""

    def __init__(
        self,
        *,
        query: ContextQueryPort,
        grounding: TargetGroundingPort,
        navigator: NavigatorPort,
    ) -> None:
        self._query = query
        self._grounding = grounding
        self._navigator = navigator

    def execute(self, plan: MissionPlan) -> MissionExecutionReport:
        """Execute a plan until completion or first deterministic failure."""
        symbols: dict[str, ResolvedNavigationTarget] = {}
        records: list[StepRecord] = []
        completed_navigation_steps = 0

        try:
            for index, step in enumerate(plan.steps):
                completed_navigation_steps += self._execute_step(
                    step=step,
                    path=str(index),
                    symbols=symbols,
                    records=records,
                )
        except ExecutionError as error:
            return MissionExecutionReport(
                status="failed",
                records=tuple(records),
                completed_navigation_steps=completed_navigation_steps,
                failure=str(error),
            )

        return MissionExecutionReport(
            status="succeeded",
            records=tuple(records),
            completed_navigation_steps=completed_navigation_steps,
        )

    def _execute_step(
        self,
        *,
        step: ResolveTarget | NavigateTo | Repeat,
        path: str,
        symbols: dict[str, ResolvedNavigationTarget],
        records: list[StepRecord],
    ) -> int:
        if isinstance(step, ResolveTarget):
            self._resolve(step=step, path=path, symbols=symbols, records=records)
            return 0

        if isinstance(step, NavigateTo):
            self._navigate(step=step, path=path, symbols=symbols, records=records)
            return 1

        if isinstance(step, Repeat):
            count = 0
            for repetition in range(step.count):
                for index, nested in enumerate(step.steps):
                    count += self._execute_step(
                        step=nested,
                        path=f"{path}.repeat[{repetition}].{index}",
                        symbols=symbols,
                        records=records,
                    )
            return count

        raise TypeError(f"unsupported step type: {type(step)!r}")

    def _resolve(
        self,
        *,
        step: ResolveTarget,
        path: str,
        symbols: dict[str, ResolvedNavigationTarget],
        records: list[StepRecord],
    ) -> None:
        resolution = self._query.resolve(step.query)
        entity_id = resolution.resolved_entity_id

        if entity_id is None:
            detail = resolution.detail or (
                f"query for {step.name!r} returned status {resolution.status!r} "
                f"with {len(resolution.candidates)} candidate(s)"
            )
            records.append(
                StepRecord(
                    path=path,
                    kind="resolve_target",
                    status="failed",
                    symbol=step.name,
                    detail=detail,
                )
            )
            raise TargetResolutionError(detail)

        target = self._grounding.ground(entity_id)
        symbols[step.name] = target
        records.append(
            StepRecord(
                path=path,
                kind="resolve_target",
                status="succeeded",
                symbol=step.name,
                entity_id=entity_id,
                detail=target.derivation,
            )
        )

    def _navigate(
        self,
        *,
        step: NavigateTo,
        path: str,
        symbols: dict[str, ResolvedNavigationTarget],
        records: list[StepRecord],
    ) -> None:
        target = symbols.get(step.target)
        if target is None:
            detail = f"target symbol {step.target!r} has not been resolved"
            records.append(
                StepRecord(
                    path=path,
                    kind="navigate_to",
                    status="failed",
                    symbol=step.target,
                    detail=detail,
                )
            )
            raise UnknownTargetError(detail)

        result: NavigationResult = self._navigator.navigate_to(target)
        if result.status != "succeeded":
            detail = result.detail or f"navigation returned {result.status!r}"
            records.append(
                StepRecord(
                    path=path,
                    kind="navigate_to",
                    status="failed",
                    symbol=step.target,
                    entity_id=target.entity_id,
                    detail=detail,
                )
            )
            raise NavigationExecutionError(detail)

        records.append(
            StepRecord(
                path=path,
                kind="navigate_to",
                status="succeeded",
                symbol=step.target,
                entity_id=target.entity_id,
                detail=result.detail,
            )
        )
