from __future__ import annotations

import json
import unittest

from pydantic import ValidationError

from packages.ask_v11.packets import (
    AnswerContract,
    AnswerPacket,
    BoundaryResult,
    BoundaryScreenPacket,
    CheckReport,
    CheckVerdict,
    CheckVerdictKind,
    EvidenceFlags,
    EvidencePacket,
    ExecutionContract,
    FlowEnvelope,
    IntentFamily,
    IntentPacket,
    RouteKind,
    RouteSelection,
    SeverityLabel,
    StageFailure,
    DegradedResponseDecision,
    TemplateRef,
)


def _answer_contract() -> AnswerContract:
    return AnswerContract(shape="known_unknown_claimability")


def _execution_contract_payload() -> dict:
    return {
        "route": {"kind": "template_call"},
        "template_ref": {"template_id": "entity_profile", "version": "1.0"},
        "args": {"entity_ref": "asset:lon:charger:42"},
        "required_sources": [
            {"source_id": "mobility_access_assets", "source_type": "fixture"}
        ],
        "retrieval_plan": {
            "groups": [
                {
                    "group_id": "asset_profile",
                    "source_refs": ["mobility_access_assets"],
                    "args": {"entity_ref": "asset:lon:charger:42"},
                }
            ]
        },
        "derived_features": [
            {
                "feature_id": "asset_distance_bucket",
                "source_fields": ["asset.location", "event.location"],
                "derivation": "deterministic spatial bucket",
            }
        ],
        "answer_contract": _answer_contract().model_dump(mode="json"),
    }


class AskV11PacketContractTests(unittest.TestCase):
    def test_valid_minimal_intent_packet_passes(self) -> None:
        packet = IntentPacket(
            intent_family=IntentFamily.subject_answer,
            confidence=0.86,
        )
        self.assertEqual(packet.intent_family, IntentFamily.subject_answer)

    def test_invalid_g1_enum_fails(self) -> None:
        with self.assertRaises(ValidationError):
            BoundaryScreenPacket(boundary="meta_product_question")

    def test_g1_enum_does_not_include_meta_product_question(self) -> None:
        self.assertNotIn(
            "meta_product_question",
            {item.value for item in BoundaryResult},
        )

    def test_valid_execution_contract_passes(self) -> None:
        packet = ExecutionContract.model_validate(_execution_contract_payload())
        self.assertEqual(packet.route.kind, RouteKind.template_call)

    def test_execution_contract_missing_answer_contract_fails(self) -> None:
        payload = _execution_contract_payload()
        payload.pop("answer_contract")
        with self.assertRaises(ValidationError):
            ExecutionContract.model_validate(payload)

    def test_evidence_packet_can_represent_no_data(self) -> None:
        packet = EvidencePacket(
            confidence=0.0,
            gaps=["no matching source rows"],
            flags=EvidenceFlags(no_data=True),
            not_executed=["G5:source_returned_no_rows"],
        )
        self.assertTrue(packet.flags.no_data)

    def test_check_report_supports_required_verdicts(self) -> None:
        report = CheckReport(
            verdicts=[
                CheckVerdict(
                    verdict=CheckVerdictKind.downgrade,
                    claim="nearby roadworks affect charger availability",
                    reason="proximity is not causality",
                ),
                CheckVerdict(
                    verdict=CheckVerdictKind.stale_flag,
                    reason="source snapshot is outside freshness window",
                ),
                CheckVerdict(
                    verdict=CheckVerdictKind.contradiction_flag,
                    reason="source rows disagree",
                    refs=["evidence:1", "evidence:2"],
                ),
                CheckVerdict(
                    verdict=CheckVerdictKind.abstain_required,
                    reason="no accepted source for legal determination",
                ),
            ],
            overall_claimability="not_claimable",
        )
        self.assertEqual(len(report.verdicts), 4)

    def test_answer_packet_requires_check_report_linkage(self) -> None:
        with self.assertRaises(ValidationError):
            AnswerPacket.model_validate({"knowns": ["bounded fact"]})

    def test_flow_envelope_captures_failures_and_degradation(self) -> None:
        envelope = FlowEnvelope(
            run_id="run-001",
            stage_failures=[
                StageFailure(
                    stage_id="G5",
                    failure_class="source_timeout",
                    reason="template source did not return in budget",
                )
            ],
            degraded_response_decision=DegradedResponseDecision(
                decision="no_data",
                reason="G5 failed without patching downstream stages",
                stage_id="G5",
            ),
        )
        self.assertEqual(envelope.stage_failures[0].stage_id, "G5")
        self.assertEqual(envelope.degraded_response_decision.decision, "no_data")

    def test_severity_enum_supports_sev_0_to_4_only(self) -> None:
        self.assertEqual(
            {item.value for item in SeverityLabel},
            {
                "sev_0_clean",
                "sev_1_taxonomy_reporting_only",
                "sev_2_acceptable_but_weak",
                "sev_3_audit_uncertain",
                "sev_4_real_failure",
            },
        )

    def test_downstream_packet_schemas_do_not_contain_raw_query(self) -> None:
        downstream_models = [
            ExecutionContract,
            EvidencePacket,
            CheckReport,
            AnswerPacket,
        ]
        for model in downstream_models:
            schema_text = json.dumps(model.model_json_schema())
            self.assertNotIn("raw_query", schema_text)
            self.assertNotIn("raw_query", model.model_fields)

    def test_downstream_packets_reject_nested_raw_query(self) -> None:
        payload = _execution_contract_payload()
        payload["args"]["raw_query"] = "show me this raw user query"
        with self.assertRaises(ValidationError):
            ExecutionContract.model_validate(payload)

    def test_gap_and_refuse_routes_are_tagged(self) -> None:
        self.assertEqual(
            RouteSelection(kind="gap", gap_id="missing_template").gap_id,
            "missing_template",
        )
        self.assertEqual(
            RouteSelection(kind="refuse", refusal_class="action_shaped").refusal_class,
            "action_shaped",
        )
        with self.assertRaises(ValidationError):
            RouteSelection(kind="gap")

    def test_template_call_requires_template_ref(self) -> None:
        with self.assertRaises(ValidationError):
            ExecutionContract(
                route=RouteSelection(kind="template_call"),
                answer_contract=_answer_contract(),
            )


if __name__ == "__main__":
    unittest.main()
