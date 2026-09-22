from __future__ import annotations

import pytest
from pydantic import ValidationError

from contextmap2_embodied.contracts import MissionPlan


def test_acceptance_shape_is_representable() -> None:
    plan = MissionPlan.model_validate(
        {
            "steps": [
                {
                    "kind": "resolve_target",
                    "name": "corridor_x",
                    "query": {
                        "selector": {
                            "kind": "semantic",
                            "label": "corridor X",
                        }
                    },
                },
                {
                    "kind": "navigate_to",
                    "target": "corridor_x",
                },
                {
                    "kind": "resolve_target",
                    "name": "door_by_pallet",
                    "query": {
                        "selector": {
                            "kind": "semantic",
                            "label": "door",
                        },
                        "relations": [
                            {
                                "predicate": "next_to",
                                "object": {
                                    "kind": "semantic",
                                    "label": "wooden pallet",
                                },
                            }
                        ],
                    },
                },
                {
                    "kind": "navigate_to",
                    "target": "door_by_pallet",
                },
                {
                    "kind": "navigate_to",
                    "target": "corridor_x",
                },
            ]
        }
    )

    assert plan.schema_version == "mission-plan-v1"
    assert len(plan.steps) == 5


def test_repeat_is_bounded_and_representable() -> None:
    plan = MissionPlan.model_validate(
        {
            "steps": [
                {
                    "kind": "repeat",
                    "count": 3,
                    "steps": [
                        {
                            "kind": "resolve_target",
                            "name": "corridor_three_chairs",
                            "query": {
                                "selector": {
                                    "kind": "semantic",
                                    "label": "corridor",
                                },
                                "contains": [
                                    {
                                        "semantic": "chair",
                                        "min_count": 3,
                                        "max_count": 3,
                                    }
                                ],
                            },
                        },
                        {
                            "kind": "navigate_to",
                            "target": "corridor_three_chairs",
                        },
                        {
                            "kind": "navigate_to",
                            "target": "corridor_b",
                        },
                    ],
                }
            ]
        }
    )

    repeat = plan.steps[0]
    assert repeat.kind == "repeat"
    assert repeat.count == 3


def test_unbounded_repeat_is_rejected() -> None:
    with pytest.raises(ValidationError):
        MissionPlan.model_validate(
            {
                "steps": [
                    {
                        "kind": "repeat",
                        "count": 101,
                        "steps": [
                            {
                                "kind": "navigate_to",
                                "target": "corridor_x",
                            }
                        ],
                    }
                ]
            }
        )


def test_unknown_low_level_action_is_rejected() -> None:
    with pytest.raises(ValidationError):
        MissionPlan.model_validate(
            {
                "steps": [
                    {
                        "kind": "publish_cmd_vel",
                        "linear_x": 1.0,
                    }
                ]
            }
        )
