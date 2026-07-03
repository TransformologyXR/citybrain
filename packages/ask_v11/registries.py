"""Registry facade for ASK v1.1 P1."""

from .concept_bindings import (
    ConceptBindingRegistry,
    list_seed_families,
    lookup_concept,
    lookup_many,
)
from .templates import (
    RegistryValidationError,
    TemplateNotFoundError,
    TemplateRegistry,
    get_template,
    instantiate_execution_contract,
    list_templates,
    list_templates_for_intent,
    validate_template_declaration,
)

__all__ = [
    "ConceptBindingRegistry",
    "RegistryValidationError",
    "TemplateNotFoundError",
    "TemplateRegistry",
    "get_template",
    "instantiate_execution_contract",
    "list_seed_families",
    "list_templates",
    "list_templates_for_intent",
    "lookup_concept",
    "lookup_many",
    "validate_template_declaration",
]
