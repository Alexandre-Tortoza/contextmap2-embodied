from __future__ import annotations

from contextmap2_embodied.contracts import MissionPlan
from contextmap2_embodied.execution import MissionExecutor
from contextmap2_embodied.fakes import InMemoryContextMap, RecordingNavigator
from contextmap2_embodied.models import Pose2D, ResolvedNavigationTarget


def _target(entity_id: str, x: float) -> ResolvedNavigationTarget:
    return ResolvedNavigationTarget(
        entity_id=entity_id,
        pose=Pose2D(frame_id="map", x=x, y=0.0),
        derivation="test fixture",
    )


def test_executor_runs_resolve_navigate_sequence() -> None:
    context_map = InMemoryContextMap(
        semantic_index={"corridor X": ("corridor-x",), "door": ("door-1",)},
        targets={
            "corridor-x": _target("corridor-x", 1.0),
            "door-1": _target("door-1", 2.0),
        },
    )
    navigator = RecordingNavigator()
    executor = MissionExecutor(query=context_map, grounding=context_map, navigator=navigator)

    plan = MissionPlan.model_validate(
        {
            "steps": [
                {
                    "kind": "resolve_target",
                    "name": "x",
                    "query": {
                        "selector": {"kind": "semantic", "label": "corridor X"}
                    },
                },
                {"kind": "navigate_to", "target": "x"},
                {
                    "kind": "resolve_target",
                    "name": "door",
                    "query": {
                        "selector": {"kind": "semantic", "label": "door"}
                    },
                },
                {"kind": "navigate_to", "target": "door"},
                {"kind": "navigate_to", "target": "x"},
            ]
        }
    )

    report = executor.execute(plan)

    assert report.status == "succeeded"
    assert report.completed_navigation_steps == 3
    assert navigator.visited == ["corridor-x", "door-1", "corridor-x"]


def test_executor_repeat_runs_exact_number_of_cycles() -> None:
    context_map = InMemoryContextMap(
        semantic_index={"corridor A": ("corridor-a",), "corridor B": ("corridor-b",)},
        targets={
            "corridor-a": _target("corridor-a", 1.0),
            "corridor-b": _target("corridor-b", 2.0),
        },
    )
    navigator = RecordingNavigator()
    executor = MissionExecutor(context_map=context_map, navigator=navigator)

    plan = MissionPlan.model_validate(
        {
            "steps": [
                {
                    "kind": "resolve_target",
                    "name": "a",
                    "query": {
                        "selector": {"kind": "semantic", "label": "corridor A"}
                    },
                },
                {
                    "kind": "resolve_target",
                    "name": "b",
                    "query": {
                        "selector": {"kind": "semantic", "label": "corridor B"}
                    },
                },
                {
                    "kind": "repeat",
                    "count": 3,
                    "steps": [
                        {"kind": "navigate_to", "target": "a"},
                        {"kind": "navigate_to", "target": "b"},
                    ],
                },
            ]
        }
    )

    report = executor.execute(plan)

    assert report.status == "succeeded"
    assert report.completed_navigation_steps == 6
    assert navigator.visited == [
        "corridor-a",
        "corridor-b",
        "corridor-a",
        "corridor-b",
        "corridor-a",
        "corridor-b",
    ]


def test_executor_stops_on_ambiguous_resolution() -> None:
    context_map = InMemoryContextMap(
        semantic_index={"door": ("door-1", "door-2")},
        targets={
            "door-1": _target("door-1", 1.0),
            "door-2": _target("door-2", 2.0),
        },
    )
    navigator = RecordingNavigator()
    executor = MissionExecutor(context_map=context_map, navigator=navigator)

    plan = MissionPlan.model_validate(
        {
            "steps": [
                {
                    "kind": "resolve_target",
                    "name": "door",
                    "query": {
                        "selector": {"kind": "semantic", "label": "door"}
                    },
                },
                {"kind": "navigate_to", "target": "door"},
            ]
        }
    )

    report = executor.execute(plan)

    assert report.status == "failed"
    assert report.completed_navigation_steps == 0
    assert navigator.visited == []
    assert "multiple entities" in (report.failure or "")


def test_executor_stops_on_navigation_failure() -> None:
    context_map = InMemoryContextMap(
        semantic_index={"corridor X": ("corridor-x",)},
        targets={"corridor-x": _target("corridor-x", 1.0)},
    )
    navigator = RecordingNavigator(fail_on_entity="corridor-x")
    executor = MissionExecutor(context_map=context_map, navigator=navigator)

    plan = MissionPlan.model_validate(
        {
            "steps": [
                {
                    "kind": "resolve_target",
                    "name": "x",
                    "query": {
                        "selector": {"kind": "semantic", "label": "corridor X"}
                    },
                },
                {"kind": "navigate_to", "target": "x"},
            ]
        }
    )

    report = executor.execute(plan)

    assert report.status == "failed"
    assert navigator.visited == ["corridor-x"]
    assert report.records[-1].status == "failed"
