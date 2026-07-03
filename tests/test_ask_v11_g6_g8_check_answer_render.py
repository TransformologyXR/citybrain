from __future__ import annotations

from datetime import datetime
import json
import unittest

from packages.ask_v11.answer_assembly import answer_assemble
from packages.ask_v11.checks import evidence_validate
from packages.ask_v11.full_spine import run_ask_v11_full_fixture_spine
from packages.ask_v11.packets import (
    CheckKind,
    CheckReport,
    CheckVerdictKind,
    ConceptBindingStatus,
    EvidenceFlags,
    EvidencePacket,
    FlowRunInput,
    IntentFamily,
    IntentPacket,
    SourceRef,
)
from packages.ask_v11.render_validation import validate_render
from packages.ask_v11.rendering import render_answer
from packages.ask_v11.resolver import intent_and_binding_resolver
from packages.ask_v11.templates import TemplateRegistry


def _flow(raw_query: str, **kwargs) -> FlowRunInput:
    return FlowRunInput(run_id="p3-test-run", raw_query=raw_query, **kwargs)


def _contract(template_id: str, args: dict | None = None):
    return TemplateRegistry().instantiate_execution_contract(template_id, "1.0", args or {})


def _entity_contract(entity_ref: str = "asset:ev:wood-lane"):
    return _contract("entity_profile", {"entity_ref": entity_ref})


def _source_ref(source_id: str = "fixture:test", **kwargs) -> SourceRef:
    return SourceRef(source_id=source_id, source_type="fixture", title=source_id, **kwargs)


def _simple_evidence(**kwargs) -> EvidencePacket:
    payload = {
        "facts": [{"fact_id": "fact:1", "text": "Retained fixture fact."}],
        "source_refs": [_source_ref()],
        "lineage": ["test"],
        "confidence": 0.9,
    }
    payload.update(kwargs)
    return EvidencePacket(**payload)


class AskV11G6G8Tests(unittest.TestCase):
    def test_g6_no_data_yields_insufficient_no_data(self) -> None:
        evidence = EvidencePacket(flags=EvidenceFlags(no_data=True), gaps=["no rows"])
        report = evidence_validate(evidence, _entity_contract())
        self.assertEqual(report.overall_claimability, "not_claimable")
        self.assertIn(CheckVerdictKind.insufficient_no_data, {v.verdict for v in report.verdicts})

    def test_g6_empty_sources_downgrades_source_depth(self) -> None:
        evidence = EvidencePacket(facts=[{"fact_id": "f", "text": "fact"}], confidence=0.5)
        report = evidence_validate(evidence, _entity_contract())
        source_depth = next(item for item in report.checks if item.check == CheckKind.source_depth)
        self.assertEqual(source_depth.status, "fail")
        self.assertIn(CheckVerdictKind.abstain_required, {v.verdict for v in report.verdicts})

    def test_g6_known_external_not_ingested_yields_abstain_or_not_claimable(self) -> None:
        flow = _flow("Is live charger availability known for Wood Lane?")
        intent = intent_and_binding_resolver(flow, boundary_packet=__import__("packages.ask_v11.boundary", fromlist=["boundary_screen"]).boundary_screen(flow))
        contract = _contract("external_context_need", {"concept": "charger_asset_availability"})
        evidence = EvidencePacket(flags=EvidenceFlags(no_data=True), gaps=["source not ingested"], source_refs=[_source_ref()])
        report = evidence_validate(evidence, contract, intent)
        self.assertIn(report.overall_claimability, {"not_claimable", "abstain_required"})
        self.assertTrue(report.abstains)

    def test_g6_proximity_does_not_become_causality(self) -> None:
        evidence = _simple_evidence(
            facts=[{"fact_id": "near", "text": "A nearby works record is adjacent to the asset."}]
        )
        report = evidence_validate(evidence, _entity_contract())
        self.assertTrue(any(d.reason == "proximity is not causality" for d in report.claim_downgrades))

    def test_g6_candidate_link_downgrades_claim(self) -> None:
        evidence = _simple_evidence(rows=[{"row_id": "r1", "candidate": True, "claim": "asset link"}])
        report = evidence_validate(evidence, _entity_contract())
        self.assertTrue(any("candidate" in d.reason for d in report.claim_downgrades))

    def test_g6_contradiction_flag_blocks_claimable(self) -> None:
        evidence = _simple_evidence(rows=[
            {"claimable_field": "status", "claim_value": "open"},
            {"claimable_field": "status", "claim_value": "closed"},
        ])
        report = evidence_validate(evidence, _entity_contract())
        self.assertEqual(report.overall_claimability, "contradicted")
        self.assertIn(CheckVerdictKind.contradiction_flag, {v.verdict for v in report.verdicts})

    def test_g6_stale_source_yields_stale_flag(self) -> None:
        evidence = _simple_evidence(
            source_refs=[
                SourceRef(
                    source_id="fixture:old",
                    source_type="retained_source",
                    title="Old retained source",
                    observed_at=datetime(2024, 1, 1),
                )
            ]
        )
        report = evidence_validate(evidence, _entity_contract())
        self.assertEqual(report.overall_claimability, "stale")
        self.assertIn(CheckVerdictKind.stale_flag, {v.verdict for v in report.verdicts})

    def test_g6_partial_result_adds_coverage_limit(self) -> None:
        evidence = _simple_evidence(flags=EvidenceFlags(partial_result=True))
        report = evidence_validate(evidence, _entity_contract())
        self.assertTrue(report.coverage_limits)
        self.assertEqual(report.overall_claimability, "partially_claimable")

    def test_g6_binding_status_findings_are_specific(self) -> None:
        flow = _flow("Is live charger availability known for Wood Lane?")
        from packages.ask_v11.boundary import boundary_screen

        intent = intent_and_binding_resolver(flow, boundary_screen(flow))
        report = evidence_validate(_simple_evidence(), _entity_contract(), intent)
        self.assertTrue(report.binding_findings)
        self.assertIn("Current availability", report.binding_findings[0].finding)

    def test_g6_check_report_contains_required_check_kinds(self) -> None:
        report = evidence_validate(_simple_evidence(), _entity_contract())
        self.assertEqual(
            {check.check for check in report.checks},
            {
                CheckKind.source_depth,
                CheckKind.freshness_staleness,
                CheckKind.candidate_inferred_link_confidence,
                CheckKind.proximity_vs_causality,
                CheckKind.contradiction,
                CheckKind.coverage_limits,
                CheckKind.binding_status,
            },
        )

    def test_g7_requires_check_report(self) -> None:
        with self.assertRaises(ValueError):
            answer_assemble(_simple_evidence(), None, _entity_contract())

    def test_g7_no_data_answer_has_unknowns_and_cannot_claim(self) -> None:
        evidence = EvidencePacket(flags=EvidenceFlags(no_data=True), gaps=["no matching fixture"], source_refs=[_source_ref()])
        report = evidence_validate(evidence, _entity_contract())
        answer = answer_assemble(evidence, report, _entity_contract())
        self.assertTrue(answer.unknowns)
        self.assertTrue(answer.cannot_claim)

    def test_g7_downgrade_preserved_in_answer_packet(self) -> None:
        evidence = _simple_evidence(facts=[{"fact_id": "near", "text": "A nearby works record is near the asset."}])
        report = evidence_validate(evidence, _entity_contract())
        answer = answer_assemble(evidence, report, _entity_contract())
        joined = " ".join(answer.knowns + answer.cannot_claim)
        self.assertIn("nearby/proximity context only", joined)

    def test_g7_abstain_preserved_in_cannot_claim(self) -> None:
        intent = IntentPacket(
            intent_family=IntentFamily.external_context_need,
            confidence=0.9,
            concept_bindings=[
                {
                    "concept": "charger availability",
                    "family": "charger_asset_availability",
                    "status": ConceptBindingStatus.known_external_not_ingested,
                    "cannot_claim": ["current charger availability"],
                }
            ],
        )
        report = evidence_validate(_simple_evidence(), _entity_contract(), intent)
        answer = answer_assemble(_simple_evidence(), report, _entity_contract(), intent)
        self.assertIn("current charger availability", " ".join(answer.cannot_claim))

    def test_g7_contradiction_does_not_pick_winner(self) -> None:
        evidence = _simple_evidence(rows=[
            {"claimable_field": "status", "claim_value": "open"},
            {"claimable_field": "status", "claim_value": "closed"},
        ])
        report = evidence_validate(evidence, _entity_contract())
        answer = answer_assemble(evidence, report, _entity_contract())
        self.assertIn("does not choose a winner", " ".join(answer.knowns))

    def test_g7_staleness_goes_to_coverage_note(self) -> None:
        evidence = _simple_evidence(
            source_refs=[SourceRef(source_id="old", source_type="retained", observed_at=datetime(2024, 1, 1))]
        )
        report = evidence_validate(evidence, _entity_contract())
        answer = answer_assemble(evidence, report, _entity_contract())
        self.assertIn("older than freshness policy", " ".join(answer.coverage_note.limitations))

    def test_g7_citations_from_source_refs(self) -> None:
        answer = answer_assemble(_simple_evidence(), evidence_validate(_simple_evidence(), _entity_contract()), _entity_contract())
        self.assertEqual(answer.citations[0].source_ref, "fixture:test")

    def test_g7_answer_packet_has_check_report_ref(self) -> None:
        answer = answer_assemble(_simple_evidence(), evidence_validate(_simple_evidence(), _entity_contract()), _entity_contract())
        self.assertEqual(answer.check_report_ref, "check:g6")

    def test_g7_not_executed_preserved(self) -> None:
        evidence = _simple_evidence(not_executed=["production_retrieval"])
        answer = answer_assemble(evidence, evidence_validate(evidence, _entity_contract()), _entity_contract())
        self.assertIn("production_retrieval", answer.not_executed)

    def test_g7_no_raw_query_in_answer_packet(self) -> None:
        evidence = _simple_evidence()
        answer = answer_assemble(evidence, evidence_validate(evidence, _entity_contract()), _entity_contract())
        self.assertNotIn("raw_query", json.dumps(answer.model_dump(mode="json")))

    def test_g8_renders_from_answer_packet_only(self) -> None:
        evidence = _simple_evidence()
        answer = answer_assemble(evidence, evidence_validate(evidence, _entity_contract()), _entity_contract())
        captured = {}

        def proposal(packet):
            captured["type"] = type(packet).__name__
            return "- No claim: " + "\n- No claim: ".join(packet.cannot_claim) if packet.cannot_claim else "Known:\n- Safe retained fact."

        render_answer(answer, proposal_fn=proposal)
        self.assertEqual(captured["type"], "AnswerPacket")

    def test_g8_preserves_cannot_claim_text(self) -> None:
        evidence = _simple_evidence(facts=[{"fact_id": "near", "text": "A nearby works record is near the asset."}])
        answer = answer_assemble(evidence, evidence_validate(evidence, _entity_contract()), _entity_contract())
        rendered = render_answer(answer)
        for claim in answer.cannot_claim:
            self.assertIn(claim, rendered.text)

    def test_g8_preserves_no_data_wording(self) -> None:
        evidence = EvidencePacket(flags=EvidenceFlags(no_data=True), gaps=["no matching fixture"], source_refs=[_source_ref()])
        answer = answer_assemble(evidence, evidence_validate(evidence, _entity_contract()), _entity_contract())
        rendered = render_answer(answer)
        self.assertIn("No retained", rendered.text)

    def test_g8_blocks_unsupported_causal_language(self) -> None:
        evidence = _simple_evidence(facts=[{"fact_id": "near", "text": "A nearby works record is near the asset."}])
        answer = answer_assemble(evidence, evidence_validate(evidence, _entity_contract()), _entity_contract())
        result = render_answer(answer, proposal_fn=lambda _: "Known:\n- It caused confirmed impact.")
        self.assertTrue(result.degraded)

    def test_g8_blocks_official_action_language(self) -> None:
        answer = answer_assemble(_simple_evidence(), evidence_validate(_simple_evidence(), _entity_contract()), _entity_contract())
        result = render_answer(answer, proposal_fn=lambda _: "Known:\n- A ticket created and alert sent.")
        self.assertTrue(result.degraded)

    def test_g8_blocks_live_external_claim_when_not_ingested(self) -> None:
        evidence = _simple_evidence()
        intent = IntentPacket(
            intent_family=IntentFamily.external_context_need,
            confidence=0.9,
            concept_bindings=[
                {
                    "concept": "charger availability",
                    "status": ConceptBindingStatus.known_external_not_ingested,
                    "cannot_claim": ["current charger availability"],
                }
            ],
        )
        report = evidence_validate(evidence, _entity_contract(), intent)
        answer = answer_assemble(evidence, report, _entity_contract(), intent)
        result = render_answer(answer, proposal_fn=lambda _: "Known:\n- Live charger status is available and current.")
        self.assertTrue(result.degraded)

    def test_g8_blocks_certified_or_legal_claim_when_not_claimable(self) -> None:
        evidence = _simple_evidence()
        intent = IntentPacket(
            intent_family=IntentFamily.external_context_need,
            confidence=0.9,
            concept_bindings=[
                {
                    "concept": "certified geometry",
                    "status": ConceptBindingStatus.known_external_not_ingested,
                    "cannot_claim": ["certified boundary", "official legal determination"],
                }
            ],
        )
        report = evidence_validate(evidence, _entity_contract(), intent)
        answer = answer_assemble(evidence, report, _entity_contract(), intent)
        result = render_answer(answer, proposal_fn=lambda _: "Known:\n- Certified geometry is confirmed and legal status is approved.")
        self.assertTrue(result.degraded)

    def test_g8_blocks_source_names_not_in_citations(self) -> None:
        answer = answer_assemble(_simple_evidence(), evidence_validate(_simple_evidence(), _entity_contract()), _entity_contract())
        validation = validate_render("Known:\n- Safe.\nCitations:\n- Source: invented-source", answer)
        self.assertFalse(validation.valid)

    def test_g8_rejects_attempt_to_un_downgrade(self) -> None:
        evidence = _simple_evidence(facts=[{"fact_id": "near", "text": "A nearby works record is near the asset."}])
        answer = answer_assemble(evidence, evidence_validate(evidence, _entity_contract()), _entity_contract())
        validation = validate_render("Known:\n- The asset is affected by the works.", answer)
        self.assertFalse(validation.valid)

    def test_g8_returns_degraded_response_on_validation_failure(self) -> None:
        answer = answer_assemble(_simple_evidence(), evidence_validate(_simple_evidence(), _entity_contract()), _entity_contract())
        result = render_answer(answer, proposal_fn=lambda _: "Known:\n- case opened.")
        self.assertTrue(result.degraded)
        self.assertIn("Render validation failed", result.text)

    def test_full_spine_board_meta_returns_safe_rendered_answer(self) -> None:
        result = run_ask_v11_full_fixture_spine(_flow("Can this board alert someone?"))
        self.assertEqual(result.outcome, "rendered")
        self.assertIn("No official external action was executed.", result.rendered_response.text)

    def test_full_spine_entity_profile_runs_g6_g7_g8(self) -> None:
        result = run_ask_v11_full_fixture_spine(
            _flow("What do we know about this asset?", selected_item_ref="asset:ev:wood-lane")
        )
        self.assertEqual(result.outcome, "rendered")
        self.assertIsInstance(result.check_report, CheckReport)
        self.assertIsNotNone(result.answer_packet)
        self.assertIsNotNone(result.rendered_response)

    def test_full_spine_external_context_need_cannot_claim_live_fact(self) -> None:
        result = run_ask_v11_full_fixture_spine(_flow("Is live charger availability known for Wood Lane?"))
        self.assertEqual(result.outcome, "rendered")
        self.assertIn("current charger availability", " ".join(result.answer_packet.cannot_claim))
        self.assertNotIn("is available", result.rendered_response.text.lower())

    def test_full_spine_unknown_entity_renders_no_data(self) -> None:
        result = run_ask_v11_full_fixture_spine(
            _flow("Show profile for asset:ev:unknown")
        )
        self.assertEqual(result.outcome, "rendered")
        self.assertIn("No retained", result.rendered_response.text)

    def test_full_spine_proximity_asset_does_not_claim_access_blockage(self) -> None:
        result = run_ask_v11_full_fixture_spine(
            _flow("What do we know about this asset?", selected_item_ref="asset:ev:wood-lane")
        )
        text = result.rendered_response.text.lower()
        self.assertIn("nearby/proximity context only", text)
        self.assertNotIn("confirmed impact", text.replace("no claim:", ""))

    def test_full_spine_imperative_action_still_stops_before_g6(self) -> None:
        result = run_ask_v11_full_fixture_spine(_flow("Alert someone now"))
        self.assertEqual(result.outcome, "refuse")
        self.assertIsNone(result.check_report)
        self.assertNotIn("G6", [hop.stage_id for hop in result.envelope.trace_hops])

    def test_full_spine_clarification_still_stops_before_g6(self) -> None:
        result = run_ask_v11_full_fixture_spine(_flow("What is happening around this?"))
        self.assertEqual(result.outcome, "clarify")
        self.assertIsNone(result.check_report)
        self.assertNotIn("G6", [hop.stage_id for hop in result.envelope.trace_hops])

    def test_full_spine_trace_hops_include_g6_g7_g8_when_evidence_exists(self) -> None:
        result = run_ask_v11_full_fixture_spine(_flow("Can this board alert someone?"))
        self.assertEqual(
            [hop.stage_id for hop in result.envelope.trace_hops],
            ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"],
        )

    def test_full_spine_stage_failure_degrades_without_silent_patch(self) -> None:
        def failing_check(evidence_packet, execution_contract, intent_packet):
            raise RuntimeError("check failed")

        result = run_ask_v11_full_fixture_spine(
            _flow("Can this board alert someone?"),
            check_func=failing_check,
        )
        self.assertEqual(result.outcome, "degraded")
        self.assertEqual(result.envelope.stage_failures[0].stage_id, "G6")

    def test_full_spine_no_future_flow_logic(self) -> None:
        result = run_ask_v11_full_fixture_spine(_flow("Can this board alert someone?"))
        self.assertNotIn("watch", result.rendered_response.text.lower())
        self.assertNotIn("brief", result.rendered_response.text.lower())
        self.assertNotIn("incident flow", result.rendered_response.text.lower())


if __name__ == "__main__":
    unittest.main()
