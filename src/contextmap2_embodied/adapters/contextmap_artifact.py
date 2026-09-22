"""Deterministic semantic/graph queries over the public ContextMap2 artifact reader.

This module deliberately consumes only the public reader surface. It does not parse artifact files
itself and it does not infer new ontology terms. Semantic matching is exact after whitespace trim
and Unicode case-folding. Spatial predicates keep ContextMap2 direction and only relations whose
persisted state is "supported" can satisfy a relation constraint.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self

from contextmap2_embodied.contracts import (
    ContainsConstraint,
    RelationConstraint,
    SemanticSelector,
    TargetQuery,
    TargetSelector,
)
from contextmap2_embodied.models import QueryCandidate, QueryResolution


class _EnumLike(Protocol):
    value: str


class _HypothesisLike(Protocol):
    label: str


class _SemanticStateLike(Protocol):
    status: _EnumLike
    hypotheses: tuple[_HypothesisLike, ...]


class _EntityLike(Protocol):
    entity_id: object
    semantic_state: _SemanticStateLike


class _EntityReferenceLike(Protocol):
    entity_id: object


class _RelationLike(Protocol):
    relation_id: object
    subject: _EntityReferenceLike
    predicate: _EnumLike
    object: _EntityReferenceLike
    state: _EnumLike


class _CapabilitySetLike(Protocol):
    content: tuple[_EnumLike, ...]


class _MetadataLike(Protocol):
    capabilities: _CapabilitySetLike


class _ManifestLike(Protocol):
    context_map_id: str


class ArtifactReaderLike(Protocol):
    """Minimal public ContextMapArtifactReader surface used by the query adapter."""

    manifest: _ManifestLike

    def metadata(self) -> _MetadataLike:
        """Return map metadata."""

    def entities(self) -> Iterator[_EntityLike]:
        """Stream entities."""

    def relations(self) -> Iterator[_RelationLike]:
        """Stream relations."""

    def close(self) -> None:
        """Release reader resources."""


@dataclass(frozen=True)
class _EntityView:
    entity_id: str
    semantic_status: str
    labels: tuple[str, ...]


@dataclass(frozen=True)
class _RelationView:
    relation_id: str
    subject_id: str
    predicate: str
    object_id: str
    state: str


def _normalize_label(label: str) -> str:
    return label.strip().casefold()


class ContextMapArtifactQuery:
    """Read-only query adapter over one ContextMap2 artifact.

    Entity and relation records are snapshotted because they are small graph-level records. The
    authoritative geometry remains untouched and lazy in ContextMap2's own reader.
    """

    def __init__(self, reader: ArtifactReaderLike, *, owns_reader: bool = False) -> None:
        self._reader = reader
        self._owns_reader = owns_reader
        self._closed = False

        metadata = reader.metadata()
        self.context_map_id = str(reader.manifest.context_map_id)
        self.capabilities = frozenset(item.value for item in metadata.capabilities.content)

        entities = (
            _EntityView(
                entity_id=str(entity.entity_id),
                semantic_status=entity.semantic_state.status.value,
                labels=tuple(hypothesis.label for hypothesis in entity.semantic_state.hypotheses),
            )
            for entity in reader.entities()
        )
        self._entities = {entity.entity_id: entity for entity in entities}

        self._relations = tuple(
            _RelationView(
                relation_id=str(relation.relation_id),
                subject_id=str(relation.subject.entity_id),
                predicate=relation.predicate.value,
                object_id=str(relation.object.entity_id),
                state=relation.state.value,
            )
            for relation in reader.relations()
        )

    @classmethod
    def open(
        cls,
        path: Path,
        *,
        dependency_paths: Mapping[str, Path] | None = None,
        verify_hashes: bool = False,
    ) -> Self:
        """Open the artifact through ContextMap2's public ContextMapArtifactReader."""
        try:
            from contextmap.artifact import ContextMapArtifactReader
        except ImportError as error:
            raise RuntimeError(
                "ContextMap2 is not installed; install the 'contextmap' optional dependency"
            ) from error

        reader = ContextMapArtifactReader.open(
            path,
            dependency_paths=dependency_paths,
            verify_hashes=verify_hashes,
        )
        return cls(reader, owns_reader=True)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Release the owned ContextMap2 reader, if this adapter opened it."""
        if self._closed:
            return
        if self._owns_reader:
            self._reader.close()
        self._closed = True

    def resolve(self, query: TargetQuery) -> QueryResolution:
        """Resolve a typed query conservatively against persisted entities and relations."""
        if self._closed:
            raise RuntimeError("the ContextMap artifact query adapter is closed")

        if "entities" not in self.capabilities:
            return QueryResolution(
                status="not_found",
                detail="artifact does not declare the entities capability",
            )

        confident, uncertain, reasons = self._selector_matches(query.selector)
        relation_ids: dict[str, set[str]] = {
            entity_id: set() for entity_id in confident | uncertain
        }

        if query.relations or query.contains:
            if "relations" not in self.capabilities:
                return QueryResolution(
                    status="not_found",
                    detail="query requires relations but artifact does not declare that capability",
                )

        for constraint in query.relations:
            confident, uncertain = self._apply_relation_constraint(
                confident=confident,
                uncertain=uncertain,
                reasons=reasons,
                relation_ids=relation_ids,
                constraint=constraint,
            )

        for constraint in query.contains:
            confident, uncertain = self._apply_contains_constraint(
                confident=confident,
                uncertain=uncertain,
                reasons=reasons,
                relation_ids=relation_ids,
                constraint=constraint,
            )

        all_ids = sorted(confident | uncertain)
        candidates = tuple(
            self._candidate(
                entity_id=entity_id,
                relation_ids=relation_ids.get(entity_id, set()),
                uncertain=entity_id in uncertain,
                reasons=reasons.get(entity_id, set()),
            )
            for entity_id in all_ids
        )

        if len(confident) == 1 and not uncertain:
            return QueryResolution(
                status="resolved",
                candidates=candidates,
                detail="exactly one certain candidate satisfies the query",
            )
        if candidates:
            return QueryResolution(
                status="ambiguous",
                candidates=candidates,
                detail=(
                    "query is not uniquely resolved: "
                    f"{len(confident)} certain and {len(uncertain)} uncertain candidate(s)"
                ),
            )
        return QueryResolution(status="not_found", detail="no entity satisfies the query")

    def _selector_matches(
        self,
        selector: TargetSelector,
    ) -> tuple[set[str], set[str], dict[str, set[str]]]:
        if selector.kind == "entity":
            if selector.entity_id in self._entities:
                return {selector.entity_id}, set(), {}
            return set(), set(), {}

        return self._semantic_matches(selector)

    def _semantic_matches(
        self,
        selector: SemanticSelector,
    ) -> tuple[set[str], set[str], dict[str, set[str]]]:
        expected = _normalize_label(selector.label)
        confident: set[str] = set()
        uncertain: set[str] = set()
        reasons: dict[str, set[str]] = {}

        for entity in self._entities.values():
            labels = {_normalize_label(label) for label in entity.labels}
            if expected not in labels:
                continue
            if entity.semantic_status == "unambiguous":
                confident.add(entity.entity_id)
            else:
                uncertain.add(entity.entity_id)
                reasons.setdefault(entity.entity_id, set()).add(
                    f"semantic state is {entity.semantic_status}"
                )

        return confident, uncertain, reasons

    def _apply_relation_constraint(
        self,
        *,
        confident: set[str],
        uncertain: set[str],
        reasons: dict[str, set[str]],
        relation_ids: dict[str, set[str]],
        constraint: RelationConstraint,
    ) -> tuple[set[str], set[str]]:
        object_confident, object_uncertain, _ = self._selector_matches(constraint.object)
        next_confident: set[str] = set()
        next_uncertain: set[str] = set()

        for subject_id in confident | uncertain:
            certain_hits = [
                relation
                for relation in self._relations
                if relation.state == "supported"
                and relation.subject_id == subject_id
                and relation.predicate == constraint.predicate
                and relation.object_id in object_confident
            ]
            uncertain_hits = [
                relation
                for relation in self._relations
                if relation.state == "supported"
                and relation.subject_id == subject_id
                and relation.predicate == constraint.predicate
                and relation.object_id in object_uncertain
            ]

            hits = (*certain_hits, *uncertain_hits)
            if not hits:
                continue

            relation_ids.setdefault(subject_id, set()).update(
                relation.relation_id for relation in hits
            )
            if subject_id in uncertain or not certain_hits:
                next_uncertain.add(subject_id)
                if not certain_hits:
                    reasons.setdefault(subject_id, set()).add(
                        f"relation {constraint.predicate} depends on uncertain object semantics"
                    )
            else:
                next_confident.add(subject_id)

        return next_confident, next_uncertain

    def _apply_contains_constraint(
        self,
        *,
        confident: set[str],
        uncertain: set[str],
        reasons: dict[str, set[str]],
        relation_ids: dict[str, set[str]],
        constraint: ContainsConstraint,
    ) -> tuple[set[str], set[str]]:
        object_confident, object_uncertain, _ = self._semantic_matches(
            SemanticSelector(label=constraint.semantic)
        )
        next_confident: set[str] = set()
        next_uncertain: set[str] = set()

        for subject_id in confident | uncertain:
            contained_certain: set[str] = set()
            contained_uncertain: set[str] = set()
            hit_ids: set[str] = set()

            for relation in self._relations:
                if (
                    relation.state != "supported"
                    or relation.subject_id != subject_id
                    or relation.predicate != "contains"
                ):
                    continue
                if relation.object_id in object_confident:
                    contained_certain.add(relation.object_id)
                    hit_ids.add(relation.relation_id)
                elif relation.object_id in object_uncertain:
                    contained_uncertain.add(relation.object_id)
                    hit_ids.add(relation.relation_id)

            minimum_possible = len(contained_certain)
            maximum_possible = minimum_possible + len(contained_uncertain)
            accepted = [
                self._count_is_accepted(count, constraint)
                for count in range(minimum_possible, maximum_possible + 1)
            ]

            if not any(accepted):
                continue

            relation_ids.setdefault(subject_id, set()).update(hit_ids)
            if subject_id in uncertain or not all(accepted):
                next_uncertain.add(subject_id)
                if not all(accepted):
                    reasons.setdefault(subject_id, set()).add(
                        "containment count depends on uncertain object semantics"
                    )
            else:
                next_confident.add(subject_id)

        return next_confident, next_uncertain

    @staticmethod
    def _count_is_accepted(count: int, constraint: ContainsConstraint) -> bool:
        if count < constraint.min_count:
            return False
        if constraint.max_count is not None and count > constraint.max_count:
            return False
        return True

    def _candidate(
        self,
        *,
        entity_id: str,
        relation_ids: set[str],
        uncertain: bool,
        reasons: set[str],
    ) -> QueryCandidate:
        entity = self._entities[entity_id]
        return QueryCandidate(
            entity_id=entity_id,
            semantic_labels=tuple(sorted(entity.labels)),
            semantic_status=entity.semantic_status,
            relation_ids=tuple(sorted(relation_ids)),
            uncertain=uncertain,
            uncertainty_reasons=tuple(sorted(reasons)),
        )
