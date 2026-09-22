from __future__ import annotations

from types import SimpleNamespace

from contextmap2_embodied.adapters.contextmap_artifact import ContextMapArtifactQuery
from contextmap2_embodied.contracts import TargetQuery


def _enum(value: str) -> SimpleNamespace:
    return SimpleNamespace(value=value)


def _entity(
    entity_id: str,
    label: str,
    *,
    status: str = "unambiguous",
    alternatives: tuple[str, ...] = (),
) -> SimpleNamespace:
    hypotheses = tuple(SimpleNamespace(label=item) for item in (label, *alternatives))
    return SimpleNamespace(
        entity_id=entity_id,
        semantic_state=SimpleNamespace(
            status=_enum(status),
            hypotheses=hypotheses,
        ),
    )


def _relation(
    relation_id: str,
    subject: str,
    predicate: str,
    obj: str,
    *,
    state: str = "supported",
) -> SimpleNamespace:
    return SimpleNamespace(
        relation_id=relation_id,
        subject=SimpleNamespace(entity_id=subject),
        predicate=_enum(predicate),
        object=SimpleNamespace(entity_id=obj),
        state=_enum(state),
    )


class _Reader:
    def __init__(
        self,
        entities: tuple[SimpleNamespace, ...],
        relations: tuple[SimpleNamespace, ...],
    ) -> None:
        self.manifest = SimpleNamespace(context_map_id="test-map")
        self._entities = entities
        self._relations = relations
        self._closed = False

    def metadata(self) -> SimpleNamespace:
        return SimpleNamespace(
            capabilities=SimpleNamespace(content=(_enum("entities"), _enum("relations")))
        )

    def entities(self):
        return iter(self._entities)

    def relations(self):
        return iter(self._relations)

    def close(self) -> None:
        self._closed = True


def test_resolves_door_next_to_wooden_pallet() -> None:
    reader = _Reader(
        entities=(
            _entity("door-1", "door"),
            _entity("door-2", "door"),
            _entity("pallet-1", "wooden pallet"),
        ),
        relations=(_relation("rel-1", "door-1", "next_to", "pallet-1"),),
    )
    query = ContextMapArtifactQuery(reader)

    result = query.resolve(
        TargetQuery.model_validate(
            {
                "selector": {"kind": "semantic", "label": "door"},
                "relations": [
                    {
                        "predicate": "next_to",
                        "object": {
                            "kind": "semantic",
                            "label": "wooden pallet",
                        },
                    }
                ],
            }
        )
    )

    assert result.status == "resolved"
    assert result.resolved_entity_id == "door-1"
    assert result.candidates[0].relation_ids == ("rel-1",)


def test_rejected_or_unresolved_relation_does_not_satisfy_constraint() -> None:
    reader = _Reader(
        entities=(
            _entity("door-1", "door"),
            _entity("pallet-1", "wooden pallet"),
        ),
        relations=(
            _relation(
                "rel-1",
                "door-1",
                "next_to",
                "pallet-1",
                state="unresolved",
            ),
        ),
    )
    query = ContextMapArtifactQuery(reader)

    result = query.resolve(
        TargetQuery.model_validate(
            {
                "selector": {"kind": "semantic", "label": "door"},
                "relations": [
                    {
                        "predicate": "next_to",
                        "object": {
                            "kind": "semantic",
                            "label": "wooden pallet",
                        },
                    }
                ],
            }
        )
    )

    assert result.status == "not_found"


def test_ambiguous_semantic_hypothesis_is_not_promoted_to_truth() -> None:
    reader = _Reader(
        entities=(
            _entity(
                "door-1",
                "door",
                status="ambiguous",
                alternatives=("opening",),
            ),
        ),
        relations=(),
    )
    query = ContextMapArtifactQuery(reader)

    result = query.resolve(
        TargetQuery.model_validate({"selector": {"kind": "semantic", "label": "door"}})
    )

    assert result.status == "ambiguous"
    assert result.resolved_entity_id is None
    assert result.candidates[0].uncertain is True


def test_contains_exactly_three_chairs() -> None:
    reader = _Reader(
        entities=(
            _entity("corridor-a", "corridor"),
            _entity("corridor-b", "corridor"),
            _entity("chair-1", "chair"),
            _entity("chair-2", "chair"),
            _entity("chair-3", "chair"),
            _entity("chair-4", "chair"),
        ),
        relations=(
            _relation("a-1", "corridor-a", "contains", "chair-1"),
            _relation("a-2", "corridor-a", "contains", "chair-2"),
            _relation("a-3", "corridor-a", "contains", "chair-3"),
            _relation("b-1", "corridor-b", "contains", "chair-1"),
            _relation("b-2", "corridor-b", "contains", "chair-2"),
            _relation("b-3", "corridor-b", "contains", "chair-3"),
            _relation("b-4", "corridor-b", "contains", "chair-4"),
        ),
    )
    query = ContextMapArtifactQuery(reader)

    result = query.resolve(
        TargetQuery.model_validate(
            {
                "selector": {"kind": "semantic", "label": "corridor"},
                "contains": [
                    {
                        "semantic": "chair",
                        "min_count": 3,
                        "max_count": 3,
                    }
                ],
            }
        )
    )

    assert result.status == "resolved"
    assert result.resolved_entity_id == "corridor-a"


def test_label_matching_is_casefold_exact_without_synonym_expansion() -> None:
    reader = _Reader(
        entities=(_entity("pallet-1", "Wooden Pallet"),),
        relations=(),
    )
    query = ContextMapArtifactQuery(reader)

    exact = query.resolve(
        TargetQuery.model_validate({"selector": {"kind": "semantic", "label": " wooden pallet "}})
    )
    synonym = query.resolve(
        TargetQuery.model_validate({"selector": {"kind": "semantic", "label": "wood skid"}})
    )

    assert exact.status == "resolved"
    assert synonym.status == "not_found"
