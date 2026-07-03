from __future__ import annotations

import unittest

from packages.ask_v11.concept_bindings import ConceptBindingRegistry
from packages.ask_v11.packets import (
    AnswerContract,
    ConceptBindingStatus,
    ExecutionContract,
    IntentFamily,
    RetrievalGroup,
    RetrievalPlan,
    RouteKind,
    SourceRef,
    TemplateDeclaration,
)
from packages.ask_v11.registry_seed import CONCEPT_SEED_FAMILIES
from packages.ask_v11.templates import (
    RegistryValidationError,
    TemplateNotFoundError,
    TemplateRegistry,
    instantiate_execution_contract,
    validate_template_declaration,
)


class AskV11RegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.concepts = ConceptBindingRegistry()
        self.templates = TemplateRegistry()

    def test_registry_has_exactly_eight_concept_seed_families(self) -> None:
        self.assertEqual(
            self.concepts.list_seed_families(),
            [
                "charger_asset_availability",
                "access_impact_blockage",
                "live_service_status",
                "planning_legal_determination",
                "certified_geometry",
                "official_case_ticket",
                "source_ownership_who_to_ask",
                "live_external_context",
            ],
        )
        self.assertEqual(len(CONCEPT_SEED_FAMILIES), 8)

    def test_unknown_concept_returns_unknown_concept_without_growth(self) -> None:
        before = self.concepts.list_seed_families()
        binding = self.concepts.lookup_concept("quantum pavement mood")
        after = self.concepts.list_seed_families()
        self.assertEqual(binding.status, ConceptBindingStatus.unknown_concept)
        self.assertEqual(before, after)
        self.assertIn("registry triage", binding.claimability)

    def test_charger_availability_is_known_external_not_ingested(self) -> None:
        binding = self.concepts.lookup_concept("charger availability")
        self.assertEqual(
            binding.status,
            ConceptBindingStatus.known_external_not_ingested,
        )
        self.assertIn("current charger availability", binding.cannot_claim)
        self.assertIn("operator", binding.owner)

    def test_access_impact_distinguishes_proximity_from_confirmed_blockage(self) -> None:
        binding = self.concepts.lookup_concept("access impact")
        self.assertEqual(binding.status, ConceptBindingStatus.derived_field)
        self.assertIn("Proximity can be derived", binding.claimability)
        self.assertIn(
            "confirmed access blockage from proximity alone",
            binding.cannot_claim,
        )

    def test_board_meta_template_exists_and_is_ui_help_static(self) -> None:
        template = self.templates.get_template("board_meta_help", "1.0")
        self.assertIn(IntentFamily.board_meta, template.intent_families)
        self.assertEqual(template.answer_contract.shape, "ui_help_static")
        self.assertEqual(template.required_sources, [])
        self.assertEqual(template.retrieval_plan.groups, [])

    def test_entity_profile_template_declares_sources_plan_and_answer_contract(self) -> None:
        template = self.templates.get_template("entity_profile", "1.0")
        self.assertTrue(template.required_sources)
        self.assertTrue(template.retrieval_plan.groups)
        self.assertEqual(
            template.answer_contract.shape,
            "known_unknown_claimability",
        )

    def test_template_registry_lookup_unknown_template_fails_or_returns_gap_cleanly(self) -> None:
        with self.assertRaises(TemplateNotFoundError):
            self.templates.get_template("not_registered", "1.0")

    def test_template_instantiation_returns_execution_contract(self) -> None:
        contract = self.templates.instantiate_execution_contract(
            "entity_profile",
            "1.0",
            {"entity_ref": "asset:lon:charger:42"},
        )
        self.assertIsInstance(contract, ExecutionContract)
        self.assertEqual(contract.route.kind, RouteKind.template_call)
        self.assertEqual(contract.template_ref.template_id, "entity_profile")

    def test_template_instantiation_copies_registered_plan_not_runtime_plan(self) -> None:
        template = self.templates.get_template("entity_profile", "1.0")
        contract = self.templates.instantiate_execution_contract(
            "entity_profile",
            "1.0",
            {"entity_ref": "asset:lon:charger:42"},
        )
        self.assertEqual(
            contract.retrieval_plan.model_dump(mode="json"),
            template.retrieval_plan.model_dump(mode="json"),
        )
        contract.retrieval_plan.groups[0].group_id = "mutated"
        fresh = self.templates.instantiate_execution_contract(
            "entity_profile",
            "1.0",
            {"entity_ref": "asset:lon:charger:42"},
        )
        self.assertEqual(fresh.retrieval_plan.groups[0].group_id, "entity_profile_lookup")
        with self.assertRaises(RegistryValidationError):
            self.templates.instantiate_execution_contract(
                "entity_profile",
                "1.0",
                {"entity_ref": "asset:lon:charger:42"},
                retrieval_plan=RetrievalPlan(groups=[]),
            )

    def test_instantiation_rejects_raw_query_in_args(self) -> None:
        with self.assertRaises(RegistryValidationError):
            self.templates.instantiate_execution_contract(
                "entity_profile",
                "1.0",
                {"entity_ref": "asset:lon:charger:42", "nested": {"raw_query": "x"}},
            )

    def test_template_declaration_rejects_nested_raw_query(self) -> None:
        payload = {
            "template_id": "bad_template",
            "version": "1.0",
            "intent_families": ["entity_profile"],
            "required_args": ["entity_ref"],
            "required_sources": [],
            "retrieval_plan": {"groups": []},
            "answer_contract": {"shape": "known_unknown_claimability"},
            "notes": "raw query should not appear here",
            "derived_features": [
                {
                    "feature_id": "bad",
                    "source_fields": ["raw_query"],
                    "derivation": "raw_query",
                }
            ],
        }
        with self.assertRaises(RegistryValidationError):
            validate_template_declaration(payload)

    def test_retrieval_plan_is_flat_no_nested_groups(self) -> None:
        payload = {
            "template_id": "nested_plan",
            "version": "1.0",
            "intent_families": ["entity_profile"],
            "required_args": ["entity_ref"],
            "required_sources": [
                {"source_id": "fixture:nested", "source_type": "fixture"}
            ],
            "retrieval_plan": {
                "groups": [
                    {
                        "group_id": "outer",
                        "source_refs": ["fixture:nested"],
                        "args": {"groups": [{"group_id": "inner"}]},
                    }
                ]
            },
            "answer_contract": {"shape": "known_unknown_claimability"},
        }
        with self.assertRaises(RegistryValidationError):
            validate_template_declaration(payload)

    def test_no_future_flow_templates_have_logic(self) -> None:
        future_prefixes = ("watch", "brief", "diff", "incident")
        for template in self.templates.list_templates():
            self.assertFalse(template.template_id.startswith(future_prefixes))
            self.assertNotIn("future flow", (template.notes or "").lower())

    def test_all_templates_validate(self) -> None:
        templates = self.templates.list_templates()
        self.assertEqual(
            [template.template_id for template in templates],
            [
                "board_meta_help",
                "entity_profile",
                "external_context_need",
                "patch_queue_query",
                "source_record_profile",
                "subject_answer",
            ],
        )
        for template in templates:
            self.assertTrue(validate_template_declaration(template))

    def test_missing_required_args_yields_clarify_contract_not_fabricated_plan(self) -> None:
        contract = self.templates.instantiate_execution_contract(
            "entity_profile",
            "1.0",
            {},
        )
        self.assertEqual(contract.route.kind, RouteKind.clarify)
        self.assertEqual(contract.args["missing_args"], ["entity_ref"])
        self.assertEqual(
            contract.retrieval_plan.groups[0].group_id,
            "entity_profile_lookup",
        )

    def test_template_declaration_required_fields_are_enforced(self) -> None:
        with self.assertRaises(RegistryValidationError):
            validate_template_declaration({"version": "1.0", "answer_contract": {"shape": "x"}})
        with self.assertRaises(RegistryValidationError):
            validate_template_declaration({"template_id": "x", "answer_contract": {"shape": "x"}})
        with self.assertRaises(RegistryValidationError):
            validate_template_declaration({"template_id": "x", "version": "1.0"})

    def test_retrieval_group_requires_group_id(self) -> None:
        with self.assertRaises(RegistryValidationError):
            validate_template_declaration(
                {
                    "template_id": "bad_group",
                    "version": "1.0",
                    "intent_families": ["entity_profile"],
                    "required_sources": [
                        {"source_id": "fixture:bad", "source_type": "fixture"}
                    ],
                    "retrieval_plan": {
                        "groups": [
                            {
                                "source_refs": ["fixture:bad"],
                                "args": {"entity_ref": "{entity_ref}"},
                            }
                        ]
                    },
                    "answer_contract": {"shape": "known_unknown_claimability"},
                }
            )

    def test_module_level_instantiation_uses_default_registry(self) -> None:
        contract = instantiate_execution_contract(
            "board_meta_help",
            "1.0",
            {"help_topic": "export"},
            route_kind="ui_help",
        )
        self.assertEqual(contract.route.kind, RouteKind.ui_help)
        self.assertEqual(contract.answer_contract.shape, "ui_help_static")

    def test_custom_registry_accepts_valid_template(self) -> None:
        template = TemplateDeclaration(
            template_id="custom_fixture",
            version="1.0",
            intent_families=[IntentFamily.subject_answer],
            required_args=["subject_ref"],
            required_sources=[SourceRef(source_id="fixture:custom")],
            retrieval_plan=RetrievalPlan(
                groups=[
                    RetrievalGroup(
                        group_id="custom_lookup",
                        source_refs=["fixture:custom"],
                        args={"subject_ref": "{subject_ref}"},
                    )
                ]
            ),
            answer_contract=AnswerContract(shape="known_unknown_claimability"),
        )
        registry = TemplateRegistry([template])
        self.assertEqual(registry.get_template("custom_fixture").template_id, "custom_fixture")


if __name__ == "__main__":
    unittest.main()
