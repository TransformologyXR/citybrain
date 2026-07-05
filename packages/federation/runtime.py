"""Local/replay federation substrate for CityBrain Push 7 Lane A."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


ALLOWED_SCORE_BANDS = {
    "fixture_only",
    "sample_replay",
    "source_backed_local",
    "checked_local",
    "reviewed_local",
    "federation_candidate",
}

FORBIDDEN_SCORE_BANDS = {
    "official_citywide_truth",
    "certified",
    "legal_authority",
    "production_live",
}

UNIVERSAL_NON_CLAIMS = [
    "No production API.",
    "No URL fetch / live retrieval.",
    "No live LLM authority.",
    "No official case/ticket submission.",
    "No dispatch/control/enforcement execution.",
    "No legal/certified finding.",
    "No autonomous workflow.",
    "No live Kit control.",
    "No full citywide twin claim.",
    "No VSS-as-fact-source.",
    "No real cross-city operational claim; federation is fixture/synthetic unless explicitly sourced and checked.",
    "No sealed ASK G1-G8 runtime change.",
    "No protected R7 runtime drift.",
    "All execution adapters are registry/preflight/not_executed unless explicitly authorized in a later phase.",
    "Feature branches only; INFRA owns canonical integration.",
]

NOT_EXECUTED = [
    "production_api",
    "url_fetch",
    "live_retrieval",
    "live_llm_call",
    "official_case_ticket_submission",
    "dispatch_control_enforcement_execution",
    "legal_certified_finding",
    "autonomous_workflow",
    "live_kit_control",
    "cross_city_operational_claim",
    "production_federation",
]

FORBIDDEN_STRUCTURAL_TOKENS = [
    '"score_band": "official_citywide_truth"',
    '"score_band": "certified"',
    '"score_band": "legal_authority"',
    '"score_band": "production_live"',
    '"production_api_used": true',
    '"url_fetch_used": true',
    '"live_retrieval_used": true',
    '"live_llm_call": true',
    '"official_submission_created": true',
    '"dispatch_control_enforcement_created": true',
    '"legal_certified_finding_created": true',
    '"execution_status": "executed"',
    '"real_cross_city_claim": true',
    '"real_dubai_coverage_claimed": true',
    '"real_government_source_integration_claimed": true',
    '"production_twin_claimed": true',
]


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def stable_id(prefix: str, *parts: Any) -> str:
    return f"{prefix}:{stable_hash([prefix, *parts])[:16]}"


def unique(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in (None, "", []):
            continue
        if isinstance(value, list):
            for nested in unique(value):
                if nested not in seen:
                    seen.add(nested)
                    result.append(nested)
            continue
        text = str(value)
        if text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _required_errors(row: dict[str, Any], required: list[str], row_id: str) -> list[str]:
    return [f"{row_id}:missing:{key}" for key in required if row.get(key) in (None, "", [])]


def _required_ref_errors(row: dict[str, Any], row_id: str) -> list[str]:
    return _required_errors(row, ["evidence_refs", "limitation_refs", "trace_refs", "check_report_ref", "authority_envelope_ref", "cannot_claim"], row_id)


@dataclass(frozen=True)
class DepartmentLocalNode:
    node_id: str
    node_label: str
    department_or_domain: str
    city_scope: str
    owned_source_classes: list[str]
    owned_packet_types: list[str]
    authority_levels_supported: list[str]
    data_maturity_summary: dict[str, Any]
    federation_policy_ref: str
    evidence_refs: list[str]
    limitation_refs: list[str]
    trace_refs: list[str]
    check_report_ref: str
    authority_envelope_ref: str
    cannot_claim: list[str]
    schema_version: str = "main-citybrain.federation.department_local_node.r1"

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "schema_version": self.schema_version,
            "node_label": self.node_label,
            "department_or_domain": self.department_or_domain,
            "city_scope": self.city_scope,
            "owned_source_classes": list(self.owned_source_classes),
            "owned_packet_types": list(self.owned_packet_types),
            "authority_levels_supported": list(self.authority_levels_supported),
            "data_maturity_summary": dict(self.data_maturity_summary),
            "federation_policy_ref": self.federation_policy_ref,
            "evidence_refs": list(self.evidence_refs),
            "limitation_refs": list(self.limitation_refs),
            "trace_refs": list(self.trace_refs),
            "check_report_ref": self.check_report_ref,
            "authority_envelope_ref": self.authority_envelope_ref,
            "cannot_claim": list(self.cannot_claim),
        }


@dataclass(frozen=True)
class NodeCapabilityManifest:
    capability_manifest_id: str
    node_ref: str
    capability_tags: list[str]
    can_emit_packet_types: list[str]
    can_receive_packet_types: list[str]
    local_only_packet_types: list[str]
    review_required: bool
    execution_status: str
    evidence_refs: list[str]
    limitation_refs: list[str]
    trace_refs: list[str]
    check_report_ref: str
    authority_envelope_ref: str
    cannot_claim: list[str]
    schema_version: str = "main-citybrain.federation.node_capability_manifest.r1"

    def as_dict(self) -> dict[str, Any]:
        return {
            "capability_manifest_id": self.capability_manifest_id,
            "schema_version": self.schema_version,
            "node_ref": self.node_ref,
            "capability_tags": list(self.capability_tags),
            "can_emit_packet_types": list(self.can_emit_packet_types),
            "can_receive_packet_types": list(self.can_receive_packet_types),
            "local_only_packet_types": list(self.local_only_packet_types),
            "review_required": self.review_required,
            "execution_status": self.execution_status,
            "evidence_refs": list(self.evidence_refs),
            "limitation_refs": list(self.limitation_refs),
            "trace_refs": list(self.trace_refs),
            "check_report_ref": self.check_report_ref,
            "authority_envelope_ref": self.authority_envelope_ref,
            "cannot_claim": list(self.cannot_claim),
        }


@dataclass(frozen=True)
class DataMaturityScore:
    data_maturity_id: str
    target_ref: str
    target_type: str
    source_class: str
    freshness_status: str
    completeness_status: str
    provenance_status: str
    authority_status: str
    review_status: str
    score_band: str
    evidence_refs: list[str]
    limitation_refs: list[str]
    trace_refs: list[str]
    check_report_ref: str
    authority_envelope_ref: str
    cannot_claim: list[str]
    schema_version: str = "main-citybrain.federation.data_maturity_score.r1"

    def as_dict(self) -> dict[str, Any]:
        return {
            "data_maturity_id": self.data_maturity_id,
            "schema_version": self.schema_version,
            "target_ref": self.target_ref,
            "target_type": self.target_type,
            "source_class": self.source_class,
            "freshness_status": self.freshness_status,
            "completeness_status": self.completeness_status,
            "provenance_status": self.provenance_status,
            "authority_status": self.authority_status,
            "review_status": self.review_status,
            "score_band": self.score_band,
            "evidence_refs": list(self.evidence_refs),
            "limitation_refs": list(self.limitation_refs),
            "trace_refs": list(self.trace_refs),
            "check_report_ref": self.check_report_ref,
            "authority_envelope_ref": self.authority_envelope_ref,
            "cannot_claim": list(self.cannot_claim),
        }


@dataclass(frozen=True)
class SourceRefreshPolicy:
    source_refresh_policy_id: str
    source_class: str
    owner_node_ref: str
    refresh_mode: str
    refresh_cadence: str
    allowed_input_modes: list[str]
    production_api_used: bool
    url_fetch_used: bool
    live_retrieval_used: bool
    evidence_refs: list[str]
    limitation_refs: list[str]
    trace_refs: list[str]
    check_report_ref: str
    authority_envelope_ref: str
    cannot_claim: list[str]
    schema_version: str = "main-citybrain.federation.source_refresh_policy.r1"

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_refresh_policy_id": self.source_refresh_policy_id,
            "schema_version": self.schema_version,
            "source_class": self.source_class,
            "owner_node_ref": self.owner_node_ref,
            "refresh_mode": self.refresh_mode,
            "refresh_cadence": self.refresh_cadence,
            "allowed_input_modes": list(self.allowed_input_modes),
            "production_api_used": self.production_api_used,
            "url_fetch_used": self.url_fetch_used,
            "live_retrieval_used": self.live_retrieval_used,
            "evidence_refs": list(self.evidence_refs),
            "limitation_refs": list(self.limitation_refs),
            "trace_refs": list(self.trace_refs),
            "check_report_ref": self.check_report_ref,
            "authority_envelope_ref": self.authority_envelope_ref,
            "cannot_claim": list(self.cannot_claim),
        }


@dataclass(frozen=True)
class SourceRefreshRunRecord:
    source_refresh_run_id: str
    source_refresh_policy_ref: str
    source_class: str
    owner_node_ref: str
    run_mode: str
    run_status: str
    production_api_used: bool
    url_fetch_used: bool
    live_retrieval_used: bool
    execution_status: str
    evidence_refs: list[str]
    limitation_refs: list[str]
    trace_refs: list[str]
    check_report_ref: str
    authority_envelope_ref: str
    cannot_claim: list[str]
    schema_version: str = "main-citybrain.federation.source_refresh_run_record.r1"

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_refresh_run_id": self.source_refresh_run_id,
            "schema_version": self.schema_version,
            "source_refresh_policy_ref": self.source_refresh_policy_ref,
            "source_class": self.source_class,
            "owner_node_ref": self.owner_node_ref,
            "run_mode": self.run_mode,
            "run_status": self.run_status,
            "production_api_used": self.production_api_used,
            "url_fetch_used": self.url_fetch_used,
            "live_retrieval_used": self.live_retrieval_used,
            "execution_status": self.execution_status,
            "evidence_refs": list(self.evidence_refs),
            "limitation_refs": list(self.limitation_refs),
            "trace_refs": list(self.trace_refs),
            "check_report_ref": self.check_report_ref,
            "authority_envelope_ref": self.authority_envelope_ref,
            "cannot_claim": list(self.cannot_claim),
        }


@dataclass(frozen=True)
class FederationBoundaryDecision:
    federation_boundary_decision_id: str
    packet_ref: str
    origin_node_ref: str
    destination_scope_ref: str
    decision: str
    share_policy: str
    reason: str
    real_cross_city_claim: bool
    evidence_refs: list[str]
    limitation_refs: list[str]
    trace_refs: list[str]
    check_report_ref: str
    authority_envelope_ref: str
    cannot_claim: list[str]
    schema_version: str = "main-citybrain.federation.boundary_decision.r1"

    def as_dict(self) -> dict[str, Any]:
        return {
            "federation_boundary_decision_id": self.federation_boundary_decision_id,
            "schema_version": self.schema_version,
            "packet_ref": self.packet_ref,
            "origin_node_ref": self.origin_node_ref,
            "destination_scope_ref": self.destination_scope_ref,
            "decision": self.decision,
            "share_policy": self.share_policy,
            "reason": self.reason,
            "real_cross_city_claim": self.real_cross_city_claim,
            "evidence_refs": list(self.evidence_refs),
            "limitation_refs": list(self.limitation_refs),
            "trace_refs": list(self.trace_refs),
            "check_report_ref": self.check_report_ref,
            "authority_envelope_ref": self.authority_envelope_ref,
            "cannot_claim": list(self.cannot_claim),
        }


@dataclass(frozen=True)
class FederatedPacketEnvelope:
    federated_packet_id: str
    origin_node_ref: str
    destination_scope_ref: str
    packet_ref: str
    packet_type: str
    share_policy: str
    data_maturity_ref: str
    evidence_refs: list[str]
    limitation_refs: list[str]
    trace_refs: list[str]
    check_report_ref: str
    authority_envelope_ref: str
    federation_boundary_decision_ref: str
    not_executed: list[str]
    cannot_claim: list[str]
    schema_version: str = "main-citybrain.federation.federated_packet_envelope.r2"

    def as_dict(self) -> dict[str, Any]:
        return {
            "federated_packet_id": self.federated_packet_id,
            "schema_version": self.schema_version,
            "origin_node_ref": self.origin_node_ref,
            "destination_scope_ref": self.destination_scope_ref,
            "packet_ref": self.packet_ref,
            "packet_type": self.packet_type,
            "share_policy": self.share_policy,
            "data_maturity_ref": self.data_maturity_ref,
            "evidence_refs": list(self.evidence_refs),
            "limitation_refs": list(self.limitation_refs),
            "trace_refs": list(self.trace_refs),
            "check_report_ref": self.check_report_ref,
            "authority_envelope_ref": self.authority_envelope_ref,
            "federation_boundary_decision_ref": self.federation_boundary_decision_ref,
            "not_executed": list(self.not_executed),
            "cannot_claim": list(self.cannot_claim),
        }


@dataclass(frozen=True)
class SyntheticCityPack:
    synthetic_city_id: str
    synthetic_node_manifests: list[dict[str, Any]]
    synthetic_source_records: list[dict[str, Any]]
    synthetic_federated_packets: list[dict[str, Any]]
    synthetic_cross_city_recall_pairs: list[dict[str, Any]]
    real_dubai_coverage_claimed: bool
    real_government_source_integration_claimed: bool
    production_twin_claimed: bool
    cannot_claim: list[str]
    schema_version: str = "main-citybrain.federation.synthetic_city_pack.r2"

    def as_dict(self) -> dict[str, Any]:
        return {
            "synthetic_city_id": self.synthetic_city_id,
            "schema_version": self.schema_version,
            "synthetic_node_manifests": list(self.synthetic_node_manifests),
            "synthetic_source_records": list(self.synthetic_source_records),
            "synthetic_federated_packets": list(self.synthetic_federated_packets),
            "synthetic_cross_city_recall_pairs": list(self.synthetic_cross_city_recall_pairs),
            "real_dubai_coverage_claimed": self.real_dubai_coverage_claimed,
            "real_government_source_integration_claimed": self.real_government_source_integration_claimed,
            "production_twin_claimed": self.production_twin_claimed,
            "cannot_claim": list(self.cannot_claim),
        }


@dataclass(frozen=True)
class CrossCityRecallFixture:
    cross_city_recall_fixture_id: str
    source_city_scope: str
    comparison_city_scope: str
    source_packet_ref: str
    comparison_packet_ref: str
    match_basis: str
    synthetic_fixture_only: bool
    real_cross_city_claim: bool
    authority_status: str
    evidence_refs: list[str]
    limitation_refs: list[str]
    trace_refs: list[str]
    check_report_ref: str
    authority_envelope_ref: str
    not_executed: list[str]
    cannot_claim: list[str]
    schema_version: str = "main-citybrain.federation.cross_city_recall_fixture.r3"

    def as_dict(self) -> dict[str, Any]:
        return {
            "cross_city_recall_fixture_id": self.cross_city_recall_fixture_id,
            "schema_version": self.schema_version,
            "source_city_scope": self.source_city_scope,
            "comparison_city_scope": self.comparison_city_scope,
            "source_packet_ref": self.source_packet_ref,
            "comparison_packet_ref": self.comparison_packet_ref,
            "match_basis": self.match_basis,
            "synthetic_fixture_only": self.synthetic_fixture_only,
            "real_cross_city_claim": self.real_cross_city_claim,
            "authority_status": self.authority_status,
            "evidence_refs": list(self.evidence_refs),
            "limitation_refs": list(self.limitation_refs),
            "trace_refs": list(self.trace_refs),
            "check_report_ref": self.check_report_ref,
            "authority_envelope_ref": self.authority_envelope_ref,
            "not_executed": list(self.not_executed),
            "cannot_claim": list(self.cannot_claim),
        }


def validate_department_local_node(node: dict[str, Any]) -> dict[str, Any]:
    row_id = str(node.get("node_id", "<missing-node-id>"))
    required = [
        "node_id",
        "schema_version",
        "node_label",
        "department_or_domain",
        "city_scope",
        "owned_source_classes",
        "owned_packet_types",
        "authority_levels_supported",
        "data_maturity_summary",
        "federation_policy_ref",
        "evidence_refs",
        "limitation_refs",
        "trace_refs",
        "check_report_ref",
        "authority_envelope_ref",
        "cannot_claim",
    ]
    errors = _required_errors(node, required, row_id)
    if "authority_level_3" not in json.dumps(node.get("authority_levels_supported", [])).lower():
        errors.append(f"{row_id}:missing_authority_level_3_support_marker")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def validate_data_maturity_score(score: dict[str, Any]) -> dict[str, Any]:
    row_id = str(score.get("data_maturity_id", "<missing-data-maturity-id>"))
    required = [
        "data_maturity_id",
        "target_ref",
        "target_type",
        "source_class",
        "freshness_status",
        "completeness_status",
        "provenance_status",
        "authority_status",
        "review_status",
        "score_band",
        "evidence_refs",
        "limitation_refs",
        "trace_refs",
        "check_report_ref",
        "authority_envelope_ref",
        "cannot_claim",
    ]
    errors = _required_errors(score, required, row_id)
    band = score.get("score_band")
    if band in FORBIDDEN_SCORE_BANDS:
        errors.append(f"{row_id}:forbidden_score_band:{band}")
    if band not in ALLOWED_SCORE_BANDS:
        errors.append(f"{row_id}:unsupported_score_band:{band}")
    errors.extend(_required_ref_errors(score, row_id))
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def validate_source_refresh_policy(policy: dict[str, Any]) -> dict[str, Any]:
    row_id = str(policy.get("source_refresh_policy_id", "<missing-source-refresh-policy-id>"))
    required = [
        "source_refresh_policy_id",
        "source_class",
        "owner_node_ref",
        "refresh_mode",
        "refresh_cadence",
        "allowed_input_modes",
        "production_api_used",
        "url_fetch_used",
        "live_retrieval_used",
        "evidence_refs",
        "limitation_refs",
        "trace_refs",
        "check_report_ref",
        "authority_envelope_ref",
        "cannot_claim",
    ]
    errors = _required_errors(policy, required, row_id)
    for flag in ["production_api_used", "url_fetch_used", "live_retrieval_used"]:
        if policy.get(flag) is not False:
            errors.append(f"{row_id}:{flag}_must_be_false")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def validate_source_refresh_run_record(run: dict[str, Any]) -> dict[str, Any]:
    row_id = str(run.get("source_refresh_run_id", "<missing-source-refresh-run-id>"))
    required = [
        "source_refresh_run_id",
        "source_refresh_policy_ref",
        "source_class",
        "owner_node_ref",
        "run_mode",
        "run_status",
        "production_api_used",
        "url_fetch_used",
        "live_retrieval_used",
        "execution_status",
        "evidence_refs",
        "limitation_refs",
        "trace_refs",
        "check_report_ref",
        "authority_envelope_ref",
        "cannot_claim",
    ]
    errors = _required_errors(run, required, row_id)
    for flag in ["production_api_used", "url_fetch_used", "live_retrieval_used"]:
        if run.get(flag) is not False:
            errors.append(f"{row_id}:{flag}_must_be_false")
    if run.get("execution_status") != "not_executed":
        errors.append(f"{row_id}:execution_status_not_not_executed")
    if run.get("run_mode") not in {"local_replay_snapshot", "fixture_regeneration", "manual_review_registry"}:
        errors.append(f"{row_id}:unsupported_run_mode:{run.get('run_mode')}")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def validate_federated_packet_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    row_id = str(envelope.get("federated_packet_id", "<missing-federated-packet-id>"))
    required = [
        "federated_packet_id",
        "schema_version",
        "origin_node_ref",
        "destination_scope_ref",
        "packet_ref",
        "packet_type",
        "share_policy",
        "data_maturity_ref",
        "evidence_refs",
        "limitation_refs",
        "trace_refs",
        "check_report_ref",
        "authority_envelope_ref",
        "federation_boundary_decision_ref",
        "not_executed",
        "cannot_claim",
    ]
    errors = _required_errors(envelope, required, row_id)
    errors.extend(_required_ref_errors(envelope, row_id))
    if "production_federation" not in envelope.get("not_executed", []):
        errors.append(f"{row_id}:missing_production_federation_not_executed_marker")
    if envelope.get("share_policy") not in {"local_only", "metadata_only_federation_fixture", "synthetic_fixture_only", "review_required_before_share"}:
        errors.append(f"{row_id}:unsupported_share_policy:{envelope.get('share_policy')}")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def validate_synthetic_city_pack(pack: dict[str, Any]) -> dict[str, Any]:
    errors = _required_errors(
        pack,
        [
            "synthetic_city_id",
            "synthetic_node_manifests",
            "synthetic_source_records",
            "synthetic_federated_packets",
            "synthetic_cross_city_recall_pairs",
            "real_dubai_coverage_claimed",
            "real_government_source_integration_claimed",
            "production_twin_claimed",
            "cannot_claim",
        ],
        str(pack.get("synthetic_city_id", "<missing-synthetic-city-id>")),
    )
    if pack.get("synthetic_city_id") != "dubai_synthetic":
        errors.append("synthetic_pack:synthetic_city_id_must_be_dubai_synthetic")
    for flag in ["real_dubai_coverage_claimed", "real_government_source_integration_claimed", "production_twin_claimed"]:
        if pack.get(flag) is not False:
            errors.append(f"synthetic_pack:{flag}_must_be_false")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def validate_cross_city_recall_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    row_id = str(fixture.get("cross_city_recall_fixture_id", "<missing-cross-city-recall-fixture-id>"))
    required = [
        "cross_city_recall_fixture_id",
        "source_city_scope",
        "comparison_city_scope",
        "source_packet_ref",
        "comparison_packet_ref",
        "match_basis",
        "synthetic_fixture_only",
        "real_cross_city_claim",
        "authority_status",
        "evidence_refs",
        "limitation_refs",
        "trace_refs",
        "check_report_ref",
        "authority_envelope_ref",
        "not_executed",
        "cannot_claim",
    ]
    errors = _required_errors(fixture, required, row_id)
    errors.extend(_required_ref_errors(fixture, row_id))
    if fixture.get("synthetic_fixture_only") is not True:
        errors.append(f"{row_id}:synthetic_fixture_only_must_be_true")
    if fixture.get("real_cross_city_claim") is not False:
        errors.append(f"{row_id}:real_cross_city_claim_must_be_false")
    if fixture.get("authority_status") != "non_authoritative_fixture":
        errors.append(f"{row_id}:authority_status_must_be_non_authoritative_fixture")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def boundary_scan(payload: Any) -> dict[str, Any]:
    blob = json.dumps(payload, sort_keys=True).lower()
    hits = [token for token in FORBIDDEN_STRUCTURAL_TOKENS if token in blob]
    return {"status": "PASS" if not hits else "FAIL", "forbidden_structural_hits": hits}
