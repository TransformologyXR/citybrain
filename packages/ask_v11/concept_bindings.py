"""Deterministic ASK v1.1 Concept-Binding Registry."""

from __future__ import annotations

from .packets import ConceptBinding, ConceptBindingStatus
from .registry_seed import (
    CONCEPT_ALIASES,
    CONCEPT_SEED_BINDINGS,
    CONCEPT_SEED_FAMILIES,
)


def _normalize_concept(concept: str) -> str:
    return " ".join(concept.strip().lower().replace("_", " ").split())


class ConceptBindingRegistry:
    """Narrow v1 seed registry.

    Unknown concepts are returned as `unknown_concept` findings. The registry
    never grows during lookup; demand-led growth belongs to a later triage path.
    """

    def __init__(
        self,
        seed_bindings: dict[str, ConceptBinding] | None = None,
        aliases: dict[str, str] | None = None,
    ) -> None:
        self._seed_bindings = dict(seed_bindings or CONCEPT_SEED_BINDINGS)
        self._aliases = dict(aliases or CONCEPT_ALIASES)

    def list_seed_families(self) -> list[str]:
        return list(CONCEPT_SEED_FAMILIES)

    def lookup_concept(self, concept: str) -> ConceptBinding:
        normalized = _normalize_concept(concept)
        key = normalized.replace(" ", "_")
        family = self._aliases.get(normalized, key)
        binding = self._seed_bindings.get(family)
        if binding is not None:
            return binding.model_copy(deep=True, update={"concept": concept})
        return ConceptBinding(
            concept=concept,
            family="unknown_concept",
            status=ConceptBindingStatus.unknown_concept,
            claimability=(
                "Unknown concept. Record demand for registry triage; do not "
                "create a family or claim support automatically."
            ),
            cannot_claim=[
                f"support for unknown concept '{concept}'",
                "new registry family without demand-led triage",
            ],
        )

    def lookup_many(self, concepts: list[str]) -> list[ConceptBinding]:
        return [self.lookup_concept(concept) for concept in concepts]


DEFAULT_CONCEPT_BINDING_REGISTRY = ConceptBindingRegistry()


def lookup_concept(concept: str) -> ConceptBinding:
    return DEFAULT_CONCEPT_BINDING_REGISTRY.lookup_concept(concept)


def lookup_many(concepts: list[str]) -> list[ConceptBinding]:
    return DEFAULT_CONCEPT_BINDING_REGISTRY.lookup_many(concepts)


def list_seed_families() -> list[str]:
    return DEFAULT_CONCEPT_BINDING_REGISTRY.list_seed_families()
