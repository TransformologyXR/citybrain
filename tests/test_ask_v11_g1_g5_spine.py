from __future__ import annotations

import json
import unittest

from packages.ask_v11.argument_resolution import resolve_arguments
from packages.ask_v11.boundary import boundary_screen
from packages.ask_v11.compiler import route_select_and_compile
from packages.ask_v11.packets import (
    AnswerPacket,
    BoundaryResult,
    BoundaryScreenPacket,
    CheckReport,
    ClarificationPacket,
    EvidencePacket,
    FlowRunInput,
    IntentFamily,
    IntentPacket,
    RouteKind,
)
from packages.ask_v11.resolver import intent_and_binding_resolver
from packages.ask_v11.spine import run_g1_g5_spine
from packages.ask_v11.template_execution import template_execute
from packages.ask_v11.templates import TemplateRegistry


def _flow(raw_query: str, **kwargs) -> FlowRunInput:
    return FlowRunInput(run_id="test-run", raw_query=raw_query, **kwargs)


def _clear_boundary() -> BoundaryScreenPacket:
    return BoundaryScreenPacket(boundary=BoundaryResult.clear)


class AskV11G1G5SpineTests(unittest.TestCase):
    def test_g1_board_meta_question_is_clear(self) -> None:
        packet = boundary_screen(_flow("Can this board alert someone?"))
        self.assertEqual(packet.boundary, BoundaryResult.clear)

    def test_g1_imperative_alert_is_action_shaped(self) -> None:
        packet = boundary_screen(_flow("Alert someone now"))
        self.assertEqual(packet.boundary, BoundaryResult.action_shaped)

    def test_g1_create_case_imperative_is_action_shaped(self) -> None:
        packet = boundary_screen(_flow("Create a case"))
        self.assertEqual(packet.boundary, BoundaryResult.action_shaped)

    def test_g1_prediction_question_is_prediction_or_finding(self) -> None:
        packet = boundary_screen(_flow("Will this get worse?"))
        self.assertEqual(packet.boundary, BoundaryResult.prediction_or_finding)

    def test_g1_never_returns_meta_product_question(self) -> None:
        packet = boundary_screen(_flow("Does this create a case?"))
        self.assertEqual(packet.boundary, BoundaryResult.clear)
        self.assertNotEqual(packet.boundary.value, "meta_product_question")
        self.assertNotIn("meta_product_question", {item.value for item in BoundaryResult})

    def test_g2_board_meta_intent_for_product_capability_question(self) -> None:
        intent = intent_and_binding_resolver(
            _flow("What can this cockpit do?"),
            _clear_boundary(),
        )
        self.assertEqual(intent.intent_family, IntentFamily.board_meta)
        self.assertEqual(intent.resolver_telemetry["args"]["help_topic"], "general_capability")

    def test_g2_external_context_need_for_live_charger_availability(self) -> None:
        intent = intent_and_binding_resolver(
            _flow("Is live charger availability known for Wood Lane?"),
            _clear_boundary(),
        )
        self.assertEqual(intent.intent_family, IntentFamily.external_context_need)
        self.assertTrue(intent.concept_bindings)
        self.assertEqual(intent.concept_bindings[0].family, "charger_asset_availability")

    def test_g2_entity_profile_from_selected_item(self) -> None:
        intent = intent_and_binding_resolver(
            _flow("What do we know about this asset?", selected_item_ref="asset:ev:wood-lane"),
            _clear_boundary(),
        )
        self.assertEqual(intent.intent_family, IntentFamily.entity_profile)
        self.assertEqual(intent.resolver_telemetry["args"]["entity_ref"], "asset:ev:wood-lane")

    def test_g2_unanchored_city_question_marks_clarification_need(self) -> None:
        intent = intent_and_binding_resolver(
            _flow("What is happening around this?"),
            _clear_boundary(),
        )
        self.assertEqual(intent.intent_family, IntentFamily.subject_answer)
        self.assertTrue(intent.context_flags.requires_selected_item)
        self.assertEqual(intent.clarification_candidates, ["subject_ref"])

    def test_g2_attaches_concept_binding_from_registry(self) -> None:
        intent = intent_and_binding_resolver(
            _flow("Do we have confirmed access impact for Wood Lane?"),
            _clear_boundary(),
        )
        self.assertEqual(intent.intent_family, IntentFamily.external_context_need)
        self.assertEqual(intent.concept_bindings[0].family, "access_impact_blockage")

    def test_g3_board_meta_compiles_registered_ui_help_template(self) -> None:
        intent = intent_and_binding_resolver(
            _flow("Can this board alert someone?"),
            _clear_boundary(),
        )
        contract = route_select_and_compile(intent, _clear_boundary())
        self.assertEqual(contract.route.kind, RouteKind.ui_help)
        self.assertEqual(contract.template_ref.template_id, "board_meta_help")
        self.assertEqual(contract.answer_contract.shape, "ui_help_static")

    def test_g3_entity_profile_compiles_registered_template(self) -> None:
        intent = intent_and_binding_resolver(
            _flow("What do we know about this asset?", selected_item_ref="asset:ev:wood-lane"),
            _clear_boundary(),
        )
        contract = route_select_and_compile(intent, _clear_boundary())
        self.assertEqual(contract.template_ref.template_id, "entity_profile")
        self.assertEqual(contract.route.kind, RouteKind.template_call)

    def test_g3_missing_template_returns_gap_without_plan(self) -> None:
        seed = TemplateRegistry().get_template("board_meta_help", "1.0")
        missing_registry = TemplateRegistry([seed])
        intent = IntentPacket(
            intent_family=IntentFamily.entity_profile,
            confidence=0.9,
            resolver_telemetry={"args": {"entity_ref": "asset:ev:wood-lane"}},
        )
        contract = route_select_and_compile(
            intent,
            _clear_boundary(),
            template_registry=missing_registry,
        )
        self.assertEqual(contract.route.kind, RouteKind.gap)
        self.assertEqual(contract.retrieval_plan.groups, [])

    def test_g3_does_not_override_registry_owned_fields(self) -> None:
        intent = intent_and_binding_resolver(
            _flow("What do we know about this asset?", selected_item_ref="asset:ev:wood-lane"),
            _clear_boundary(),
        )
        registry = TemplateRegistry()
        template = registry.get_template("entity_profile", "1.0")
        contract = route_select_and_compile(intent, _clear_boundary(), template_registry=registry)
        self.assertEqual(
            contract.retrieval_plan.model_dump(mode="json"),
            template.retrieval_plan.model_dump(mode="json"),
        )
        self.assertEqual(
            contract.required_sources[0].source_id,
            template.required_sources[0].source_id,
        )

    def test_g3_refuses_non_clear_boundary_without_g5(self) -> None:
        boundary = boundary_screen(_flow("Alert someone now"))
        intent = intent_and_binding_resolver(_flow("Alert someone now"), boundary)
        contract = route_select_and_compile(intent, boundary)
        self.assertEqual(contract.route.kind, RouteKind.refuse)
        self.assertEqual(contract.route.refusal_class, "action_shaped")

    def test_g4_fills_entity_ref_from_selected_item(self) -> None:
        intent = IntentPacket(intent_family=IntentFamily.entity_profile, confidence=0.9)
        contract = TemplateRegistry().instantiate_execution_contract("entity_profile", "1.0", {})
        resolved = resolve_arguments(
            contract,
            intent,
            _flow("What do we know about this asset?", selected_item_ref="asset:ev:wood-lane"),
        )
        self.assertEqual(resolved.args["entity_ref"], "asset:ev:wood-lane")
        self.assertEqual(resolved.route.kind, RouteKind.template_call)

    def test_g4_missing_required_entity_ref_returns_one_clarification(self) -> None:
        intent = IntentPacket(intent_family=IntentFamily.entity_profile, confidence=0.9)
        contract = TemplateRegistry().instantiate_execution_contract("entity_profile", "1.0", {})
        resolved = resolve_arguments(contract, intent, _flow("What do we know about this asset?"))
        self.assertIsInstance(resolved, ClarificationPacket)
        self.assertEqual(resolved.target_field, "entity_ref")

    def test_g4_does_not_invent_entity_ref(self) -> None:
        intent = IntentPacket(intent_family=IntentFamily.entity_profile, confidence=0.9)
        contract = TemplateRegistry().instantiate_execution_contract("entity_profile", "1.0", {})
        resolved = resolve_arguments(contract, intent, _flow("What do we know about this asset?"))
        self.assertIsInstance(resolved, ClarificationPacket)
        self.assertNotIn("entity_ref", contract.args)

    def test_g5_board_meta_returns_static_evidence_not_answer(self) -> None:
        contract = TemplateRegistry().instantiate_execution_contract(
            "board_meta_help",
            "1.0",
            {"help_topic": "alerting_capability"},
            route_kind="ui_help",
        )
        evidence = template_execute(contract)
        self.assertIsInstance(evidence, EvidencePacket)
        self.assertNotIsInstance(evidence, AnswerPacket)
        self.assertTrue(evidence.facts)
        self.assertIn("alert", evidence.not_executed)

    def test_g5_entity_profile_returns_fixture_evidence(self) -> None:
        contract = TemplateRegistry().instantiate_execution_contract(
            "entity_profile",
            "1.0",
            {"entity_ref": "asset:ev:wood-lane"},
        )
        evidence = template_execute(contract)
        self.assertFalse(evidence.flags.no_data)
        self.assertEqual(evidence.rows[0]["entity_ref"], "asset:ev:wood-lane")

    def test_g5_unknown_entity_returns_no_data_evidence(self) -> None:
        contract = TemplateRegistry().instantiate_execution_contract(
            "entity_profile",
            "1.0",
            {"entity_ref": "asset:ev:unknown"},
        )
        evidence = template_execute(contract)
        self.assertTrue(evidence.flags.no_data)
        self.assertTrue(evidence.gaps)

    def test_g5_external_context_need_marks_not_executed(self) -> None:
        contract = TemplateRegistry().instantiate_execution_contract(
            "external_context_need",
            "1.0",
            {"concept": "charger_asset_availability"},
        )
        evidence = template_execute(contract)
        self.assertTrue(evidence.flags.no_data)
        self.assertIn("production_retrieval", evidence.not_executed)

    def test_g5_patch_queue_query_returns_rows(self) -> None:
        contract = TemplateRegistry().instantiate_execution_contract(
            "patch_queue_query",
            "1.0",
            {"queue_filter": "pending"},
        )
        evidence = template_execute(contract)
        self.assertEqual(len(evidence.rows), 2)
        self.assertEqual(evidence.facts[0]["count"], 2)

    def test_g5_no_raw_query_in_evidence_packet(self) -> None:
        contract = TemplateRegistry().instantiate_execution_contract(
            "entity_profile",
            "1.0",
            {"entity_ref": "asset:ev:wood-lane"},
        )
        evidence = template_execute(contract)
        self.assertNotIn("raw_query", json.dumps(evidence.model_dump(mode="json")))

    def test_spine_meta_product_question_reaches_ui_help_evidence(self) -> None:
        result = run_g1_g5_spine(_flow("Can this board alert someone?"))
        self.assertEqual(result.outcome, "evidence")
        self.assertEqual(result.execution_contract.route.kind, RouteKind.ui_help)
        self.assertTrue(result.evidence_packet.facts)

    def test_spine_imperative_action_stops_before_g5(self) -> None:
        result = run_g1_g5_spine(_flow("Alert someone now"))
        self.assertEqual(result.outcome, "refuse")
        self.assertIsNone(result.evidence_packet)
        self.assertNotIn("G5", [hop.stage_id for hop in result.envelope.trace_hops])

    def test_spine_unanchored_city_ask_returns_one_clarification(self) -> None:
        result = run_g1_g5_spine(_flow("What is happening around this?"))
        self.assertEqual(result.outcome, "clarify")
        self.assertEqual(result.clarification_packet.target_field, "subject_ref")
        self.assertIsNone(result.evidence_packet)

    def test_spine_selected_item_followup_reaches_evidence(self) -> None:
        result = run_g1_g5_spine(
            _flow("What do we know about this asset?", selected_item_ref="asset:ev:wood-lane")
        )
        self.assertEqual(result.outcome, "evidence")
        self.assertFalse(result.evidence_packet.flags.no_data)

    def test_spine_gap_route_stops_without_execution(self) -> None:
        def unknown_resolver(flow_input, boundary_packet):
            return IntentPacket(intent_family=IntentFamily.unknown, confidence=0.9)

        result = run_g1_g5_spine(
            _flow("Explain the unsupported thing"),
            resolver_func=unknown_resolver,
        )
        self.assertEqual(result.outcome, "gap")
        self.assertIsNone(result.evidence_packet)
        self.assertNotIn("G5", [hop.stage_id for hop in result.envelope.trace_hops])

    def test_spine_trace_hops_are_emitted(self) -> None:
        result = run_g1_g5_spine(
            _flow("What do we know about this asset?", selected_item_ref="asset:ev:wood-lane")
        )
        self.assertEqual(
            [hop.stage_id for hop in result.envelope.trace_hops],
            ["G1", "G2", "G3", "G4", "G5"],
        )

    def test_spine_stage_failure_degrades_without_silent_patch(self) -> None:
        def failing_executor(contract):
            raise RuntimeError("fixture executor failed")

        result = run_g1_g5_spine(
            _flow("What do we know about this asset?", selected_item_ref="asset:ev:wood-lane"),
            template_executor_func=failing_executor,
        )
        self.assertEqual(result.outcome, "degraded")
        self.assertEqual(result.envelope.stage_failures[0].stage_id, "G5")
        self.assertEqual(result.envelope.degraded_response_decision.stage_id, "G5")

    def test_spine_does_not_emit_check_report_answer_packet_or_render(self) -> None:
        result = run_g1_g5_spine(
            _flow("What do we know about this asset?", selected_item_ref="asset:ev:wood-lane")
        )
        self.assertIsInstance(result.evidence_packet, EvidencePacket)
        self.assertNotIsInstance(result.evidence_packet, CheckReport)
        self.assertFalse(hasattr(result, "answer_packet"))
        self.assertFalse(hasattr(result, "check_report"))
        self.assertFalse(hasattr(result, "rendered_text"))


if __name__ == "__main__":
    unittest.main()
