"""Deterministic ASK v1.1 Template Registry and compiler primitive."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from .packets import (
    ExecutionContract,
    IntentFamily,
    RouteKind,
    RouteSelection,
    TemplateDeclaration,
    TemplateRef,
    _contains_raw_query_key,
)
from .registry_seed import TEMPLATE_SEED_DECLARATIONS


REGISTRY_OWNED_TEMPLATE_FIELDS = frozenset(
    {
        "required_sources",
        "retrieval_plan",
        "derived_features",
        "answer_contract",
    }
)


class RegistryValidationError(ValueError):
    """Raised when registry data violates ASK v1.1 compiler discipline."""


class TemplateNotFoundError(KeyError):
    """Raised when a requested template declaration is not registered."""


def _as_template_declaration(template: TemplateDeclaration | dict[str, Any]) -> TemplateDeclaration:
    try:
        return (
            template
            if isinstance(template, TemplateDeclaration)
            else TemplateDeclaration.model_validate(template)
        )
    except ValidationError as exc:
        raise RegistryValidationError(str(exc)) from exc


def _reject_nested_retrieval_plan(value: Any, path: str = "retrieval_plan") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"groups", "retrieval_plan"}:
                raise RegistryValidationError(
                    f"nested retrieval plan is not allowed at {path}.{key}"
                )
            _reject_nested_retrieval_plan(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_nested_retrieval_plan(item, f"{path}[{index}]")


def _contains_raw_query_token(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            key == "raw_query" or _contains_raw_query_token(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple, set)):
        return any(_contains_raw_query_token(item) for item in value)
    return isinstance(value, str) and value.strip().lower() == "raw_query"


def validate_template_declaration(template: TemplateDeclaration | dict[str, Any]) -> bool:
    declaration = _as_template_declaration(template)
    if not declaration.template_id:
        raise RegistryValidationError("template_id missing")
    if not declaration.version:
        raise RegistryValidationError("version missing")
    if declaration.answer_contract is None:
        raise RegistryValidationError("answer_contract missing")
    if not declaration.intent_families:
        raise RegistryValidationError("at least one intent_family is required")
    for family in declaration.intent_families:
        if not isinstance(family, IntentFamily):
            raise RegistryValidationError(f"unsupported intent_family: {family!r}")
    for group in declaration.retrieval_plan.groups:
        if not group.group_id:
            raise RegistryValidationError("retrieval group missing group_id")
        _reject_nested_retrieval_plan(group.args)
    declaration_payload = declaration.model_dump(mode="python", exclude_none=True)
    if _contains_raw_query_key(declaration_payload) or _contains_raw_query_token(
        declaration_payload
    ):
        raise RegistryValidationError("TemplateDeclaration contains raw_query")
    return True


class TemplateRegistry:
    """Template declarations are the only source of executable ASK contracts."""

    def __init__(self, templates: list[TemplateDeclaration] | None = None) -> None:
        declarations = list(templates or TEMPLATE_SEED_DECLARATIONS)
        self._templates: dict[tuple[str, str], TemplateDeclaration] = {}
        for declaration in declarations:
            validate_template_declaration(declaration)
            key = (declaration.template_id, declaration.version)
            if key in self._templates:
                raise RegistryValidationError(
                    f"duplicate template declaration: {declaration.template_id}@{declaration.version}"
                )
            self._templates[key] = declaration.model_copy(deep=True)

    def get_template(self, template_id: str, version: str | None = None) -> TemplateDeclaration:
        if version is not None:
            declaration = self._templates.get((template_id, version))
            if declaration is None:
                raise TemplateNotFoundError(f"unknown template: {template_id}@{version}")
            return declaration.model_copy(deep=True)

        matches = [
            declaration
            for (candidate_id, _), declaration in self._templates.items()
            if candidate_id == template_id
        ]
        if not matches:
            raise TemplateNotFoundError(f"unknown template: {template_id}")
        if len(matches) > 1:
            raise RegistryValidationError(
                f"template version required for {template_id}; found {len(matches)} versions"
            )
        return matches[0].model_copy(deep=True)

    def list_templates(self) -> list[TemplateDeclaration]:
        return [
            declaration.model_copy(deep=True)
            for declaration in sorted(
                self._templates.values(),
                key=lambda item: (item.template_id, item.version),
            )
        ]

    def list_templates_for_intent(
        self, intent_family: IntentFamily
    ) -> list[TemplateDeclaration]:
        return [
            declaration.model_copy(deep=True)
            for declaration in self.list_templates()
            if intent_family in declaration.intent_families
        ]

    def instantiate_execution_contract(
        self,
        template_id: str,
        version: str | None,
        args: dict[str, Any],
        route_kind: str | RouteKind = RouteKind.template_call,
        **runtime_overrides: Any,
    ) -> ExecutionContract:
        forbidden_overrides = REGISTRY_OWNED_TEMPLATE_FIELDS.intersection(
            runtime_overrides
        )
        if forbidden_overrides:
            raise RegistryValidationError(
                "runtime may not override registry-owned template fields: "
                + ", ".join(sorted(forbidden_overrides))
            )
        if runtime_overrides:
            raise RegistryValidationError(
                "unsupported runtime override(s): "
                + ", ".join(sorted(runtime_overrides.keys()))
            )
        if _contains_raw_query_key(args):
            raise RegistryValidationError("args may not contain raw_query")

        declaration = self.get_template(template_id, version)
        missing_args = [
            required_arg
            for required_arg in declaration.required_args
            if args.get(required_arg) in (None, "", [], {})
        ]
        effective_route_kind = RouteKind(route_kind)
        compiled_args = dict(args)
        if missing_args:
            effective_route_kind = RouteKind.clarify
            compiled_args["missing_args"] = missing_args

        route = RouteSelection(kind=effective_route_kind)
        return ExecutionContract(
            route=route,
            template_ref=TemplateRef(
                template_id=declaration.template_id,
                version=declaration.version,
            ),
            args=compiled_args,
            required_sources=[
                item.model_copy(deep=True) for item in declaration.required_sources
            ],
            retrieval_plan=declaration.retrieval_plan.model_copy(deep=True),
            derived_features=[
                item.model_copy(deep=True) for item in declaration.derived_features
            ],
            answer_contract=declaration.answer_contract.model_copy(deep=True),
        )


DEFAULT_TEMPLATE_REGISTRY = TemplateRegistry()


def get_template(template_id: str, version: str | None = None) -> TemplateDeclaration:
    return DEFAULT_TEMPLATE_REGISTRY.get_template(template_id, version)


def list_templates() -> list[TemplateDeclaration]:
    return DEFAULT_TEMPLATE_REGISTRY.list_templates()


def list_templates_for_intent(intent_family: IntentFamily) -> list[TemplateDeclaration]:
    return DEFAULT_TEMPLATE_REGISTRY.list_templates_for_intent(intent_family)


def instantiate_execution_contract(
    template_id: str,
    version: str | None,
    args: dict[str, Any],
    route_kind: str | RouteKind = RouteKind.template_call,
    **runtime_overrides: Any,
) -> ExecutionContract:
    return DEFAULT_TEMPLATE_REGISTRY.instantiate_execution_contract(
        template_id,
        version,
        args,
        route_kind,
        **runtime_overrides,
    )
