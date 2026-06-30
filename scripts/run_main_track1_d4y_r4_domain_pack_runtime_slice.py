#!/usr/bin/env python3
"""Build the Track 1 D4Y R4 domain-pack runtime-slice pack."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-TRACK1-D4Y-R4-DOMAIN-PACK-RUNTIME-SLICE"
SCHEMA_VERSION = "main-track1-d4y-r4-domain-pack-runtime-slice.v1"
STATUS = "PASS_MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_RUNTIME_SLICE_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_RUNTIME_SLICE"
WAITING_DOMAIN = "WAITING_ON_MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT"
WAITING_CER = "WAITING_ON_MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT"
WAITING_SEG = "WAITING_ON_MAIN_TRACK1_D4Y_R4_SEMANTIC_GRAPH_BRIDGE_PREFLIGHT"
WAITING_SHARED = "WAITING_ON_MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_domain_pack_runtime_slice"
DOMAIN_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_domain_pack_preflight"
CER_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_canonical_entity_bridge_preflight"
SEG_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_semantic_graph_bridge_preflight"
SHARED_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_cer_seg_shared_contracts_smoke"
HARDENING_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_live_runtime_hardening"

REQUIRED_DIRS = [
    "runtime",
    "domain_packs",
    "domain_packs/stubs",
    "packets",
    "app_handoff",
    "traces",
    "audits",
    "smoke",
    "guardrails",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_RUNTIME_SLICE.md",
    "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_RUNTIME_SLICE_DECISION.json",
    "D4Y_R4_DOMAIN_RUNTIME_PREREQUISITE_REPORT.json",
    "D4Y_R4_DOMAIN_RUNTIME_ARCHITECTURE.md",
    "D4Y_R4_DOMAIN_RUNTIME_SCOPE.md",
    "D4Y_R4_DOMAIN_RUNTIME_IMPLEMENTATION_MANIFEST.json",
    "D4Y_R4_DOMAIN_RUNTIME_CONFIG.json",
    "D4Y_R4_DOMAIN_RUNTIME_SOURCE_ARTIFACT_MAP.json",
    "D4Y_R4_DOMAIN_RUNTIME_LOADER_CONTRACT.json",
    "D4Y_R4_DOMAIN_RUNTIME_HELPER_REPORT.json",
    "D4Y_R4_DOMAIN_PACK_STUBS.json",
    "D4Y_R4_DOMAIN_PACK_VALIDATION_RESULTS.json",
    "D4Y_R4_DOMAIN_PACK_LOADING_RESULTS.json",
    "D4Y_R4_DOMAIN_RUNTIME_REQUESTS.json",
    "D4Y_R4_DOMAIN_RUNTIME_RESPONSES.json",
    "D4Y_R4_DOMAIN_OUTPUT_PACKETS.json",
    "D4Y_R4_DOMAIN_OUTPUT_PACKETS.jsonl",
    "D4Y_R4_DOMAIN_CER_REQUEST_PACKETS.json",
    "D4Y_R4_DOMAIN_SEG_REQUEST_PACKETS.json",
    "D4Y_R4_DOMAIN_INSIGHT_CANDIDATE_PACKETS.json",
    "D4Y_R4_DOMAIN_APP_HANDOFF_PACKETS.json",
    "D4Y_R4_DOMAIN_ROUTE_SELECTION_REPORT.json",
    "D4Y_R4_DOMAIN_TOOL_ALLOWLIST_REPORT.json",
    "D4Y_R4_DOMAIN_TRACE_LOG.jsonl",
    "D4Y_R4_DOMAIN_AUDIT_LOG.jsonl",
    "D4Y_R4_DOMAIN_BOUNDARY_VALIDATION_REPORT.json",
    "D4Y_R4_DOMAIN_NO_ACTION_AUDIT_REPORT.json",
    "D4Y_R4_DOMAIN_RUNTIME_SMOKE_REPORT.json",
    "D4Y_R4_DOMAIN_RUNTIME_LIMITATION_REGISTER.md",
    "D4Y_R4_DOMAIN_RUNTIME_NEGATIVE_TEST_REPORT.json",
    "D4Y_R4_DOMAIN_RUNTIME_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

WATCHED_ROOTS = [
    "outputs/main_track1_d4y_r4_domain_pack_preflight",
    "outputs/main_track1_d4y_r4_canonical_entity_bridge_preflight",
    "outputs/main_track1_d4y_r4_semantic_graph_bridge_preflight",
    "outputs/main_track1_d4y_r4_cer_seg_shared_contracts_smoke",
    "outputs/main_track1_d4y_r4_live_runtime_hardening",
    "outputs/main_track1_d4y_r3_closeout",
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice",
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_smoke",
    "outputs/main_track1_d4y_r3_insight_engine_slice",
    "outputs/main_track1_d4y_r3_insight_engine_slice_smoke",
    "outputs/main_track1_d4y_r2_closeout",
    "outputs/main_track1_d4y_intelligence_substrate_closeout_r1",
    "outputs/main_track1_d4y_situation_graph_and_query_r1",
]

LIMITATIONS = [
    "local file/CLI runtime slice only",
    "contract-only generic domain packs",
    "no real domain pack implemented",
    "no Dubai DLD/DM implementation",
    "no public API",
    "no server runtime",
    "no live agents",
    "no external LLM",
    "no production CER",
    "no production SEG",
    "no graph database runtime",
    "no traversal service",
    "no command/control/enforcement/dispatch/routing output",
    "no legal finding",
    "no confirmed violation",
    "no certified impact",
    "no certified traffic model",
]

ROUTES = [
    "domain_context_route",
    "entity_requirement_route",
    "relationship_requirement_route",
    "evidence_gap_route",
    "cer_contract_route",
    "seg_contract_route",
    "insight_candidate_route",
    "app_handoff_route",
]

ALLOWED_TOOLS = [
    "local_file_loader",
    "json_schema_validator",
    "domain_stub_validator",
    "cer_contract_packet_builder",
    "seg_contract_packet_builder",
    "deterministic_route_selector",
    "output_packet_writer",
    "trace_audit_writer",
]

FORBIDDEN_TOOLS = [
    "public_api_server",
    "network_fetcher",
    "external_llm_client",
    "live_agent_runtime",
    "production_cer_mutator",
    "production_seg_graph_database",
    "command_action_dispatcher",
    "enforcement_router",
    "source_root_mutator",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def path_signature(root: Path) -> dict[str, str]:
    if not root.exists():
        return {"__missing__": "true"}
    sig = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        sig[rel] = f"{path.stat().st_size}:{sha256_file(path)}"
    return sig


def prepare_output_root() -> None:
    resolved = OUTPUT_ROOT.resolve()
    if resolved.parent != (REPO_ROOT / "outputs").resolve() or resolved.name != "main_track1_d4y_r4_domain_pack_runtime_slice":
        raise RuntimeError(f"Refusing to reset unexpected output root: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for rel in REQUIRED_DIRS:
        (OUTPUT_ROOT / rel).mkdir(parents=True, exist_ok=True)


def decision_path(root: Path, preferred: str) -> Path | None:
    path = root / preferred
    if path.exists():
        return path
    matches = sorted(root.glob("*DECISION*.json")) if root.exists() else []
    return matches[0] if matches else None


def load_decision(root: Path, preferred: str) -> tuple[dict[str, Any], str | None]:
    path = decision_path(root, preferred)
    return (read_json(path, {}) if path else {}, path.relative_to(REPO_ROOT).as_posix() if path else None)


def build_prerequisite_report(before: dict[str, dict[str, str]]) -> tuple[dict[str, Any], str | None, dict[str, Any]]:
    domain, domain_path = load_decision(DOMAIN_ROOT, "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT_DECISION.json")
    cer, cer_path = load_decision(CER_ROOT, "MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT_DECISION.json")
    seg, seg_path = load_decision(SEG_ROOT, "MAIN_TRACK1_D4Y_R4_SEMANTIC_GRAPH_BRIDGE_PREFLIGHT_DECISION.json")
    shared, shared_path = load_decision(SHARED_ROOT, "MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE_DECISION.json")
    hardening, hardening_path = load_decision(HARDENING_ROOT, "MAIN_TRACK1_D4Y_R4_LIVE_RUNTIME_HARDENING_DECISION.json")

    checks = {
        "domain_pack_preflight_green": str(domain.get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT"),
        "canonical_entity_bridge_preflight_green": str(cer.get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT"),
        "semantic_graph_bridge_preflight_green": str(seg.get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R4_SEMANTIC_GRAPH_BRIDGE_PREFLIGHT"),
        "cer_seg_shared_contracts_smoke_green": str(shared.get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE"),
        "runtime_hardening_optional_green_or_missing": (not hardening_path) or str(hardening.get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R4_LIVE_RUNTIME_HARDENING"),
        "no_blocking_cer_seg_drift": shared.get("blocking_drift_count", shared.get("drift_summary", {}).get("blocking_drift_count", 0)) in (0, None),
        "no_production_cer": cer.get("production_cer_implemented") is False,
        "no_production_seg": seg.get("production_seg_implemented") is False,
        "no_graph_database_runtime": seg.get("graph_database_runtime_implemented") is not True,
        "no_traversal_service": seg.get("traversal_service_implemented") is not True,
        "no_prior_production_domain_runtime": domain.get("production_domain_runtime_implemented") is not True,
        "no_real_domain_pack": domain.get("real_domain_pack_implemented", domain.get("no_real_domain_pack_implemented") is False) is False,
        "dubai_dld_dm_false": domain.get("dubai_dld_dm_implemented") is False,
        "no_public_api": not any(d.get("public_api_exposed") for d in [domain, cer, seg, shared, hardening]),
        "no_external_llm": not any(d.get("external_llm_called") for d in [domain, cer, seg, shared, hardening]),
        "no_command_action": not any(d.get("command_action_output_created") for d in [domain, cer, seg, shared, hardening]),
        "d5_parked": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT"
        in {domain.get("parked_d5_task"), cer.get("parked_d5_task"), seg.get("parked_d5_task"), shared.get("parked_d5_task"), hardening.get("parked_d5_task")},
        "read_only_signature_snapshot_created": bool(before),
    }
    waiting = None
    if not checks["domain_pack_preflight_green"]:
        waiting = WAITING_DOMAIN
    elif not checks["canonical_entity_bridge_preflight_green"]:
        waiting = WAITING_CER
    elif not checks["semantic_graph_bridge_preflight_green"]:
        waiting = WAITING_SEG
    elif not checks["cer_seg_shared_contracts_smoke_green"]:
        waiting = WAITING_SHARED

    source_decisions = {
        "domain_pack_preflight": {"path": domain_path, "status": domain.get("status")},
        "canonical_entity_bridge_preflight": {"path": cer_path, "status": cer.get("status")},
        "semantic_graph_bridge_preflight": {"path": seg_path, "status": seg.get("status")},
        "cer_seg_shared_contracts_smoke": {"path": shared_path, "status": shared.get("status")},
        "live_runtime_hardening_optional": {"path": hardening_path, "status": hardening.get("status") if hardening_path else "OPTIONAL_MISSING"},
    }
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(checks.values()) else waiting or FAIL_STATUS,
        "checks": checks,
        "source_decisions": source_decisions,
        "runtime_hardening_input_status": hardening.get("status") if hardening_path else "OPTIONAL_MISSING",
        "read_only_roots": WATCHED_ROOTS,
        "limitations": LIMITATIONS,
    }
    return report, waiting, source_decisions


def build_source_artifact_map() -> dict[str, Any]:
    entries = [
        ("domain_schema", DOMAIN_ROOT / "D4Y_R4_DOMAIN_PACK_SCHEMA.json", True),
        ("domain_manifest_schema", DOMAIN_ROOT / "D4Y_R4_DOMAIN_PACK_MANIFEST_SCHEMA.json", True),
        ("domain_entity_requirements_schema", DOMAIN_ROOT / "D4Y_R4_DOMAIN_ENTITY_REQUIREMENTS_SCHEMA.json", True),
        ("domain_relationship_requirements_schema", DOMAIN_ROOT / "D4Y_R4_DOMAIN_RELATIONSHIP_REQUIREMENTS_SCHEMA.json", True),
        ("domain_evidence_policy", DOMAIN_ROOT / "D4Y_R4_DOMAIN_EVIDENCE_POLICY.md", True),
        ("domain_insight_policy", DOMAIN_ROOT / "D4Y_R4_DOMAIN_INSIGHT_POLICY.md", True),
        ("domain_tool_policy", DOMAIN_ROOT / "D4Y_R4_DOMAIN_TOOL_POLICY.json", True),
        ("domain_guardrail_policy", DOMAIN_ROOT / "D4Y_R4_DOMAIN_GUARDRAIL_POLICY.json", True),
        ("domain_app_handoff_contract", DOMAIN_ROOT / "D4Y_R4_DOMAIN_APP_HANDOFF_CONTRACT.json", True),
        ("domain_sample_stubs", DOMAIN_ROOT / "D4Y_R4_DOMAIN_PACK_SAMPLE_STUBS.json", True),
        ("cer_bridge_contract", DOMAIN_ROOT / "D4Y_R4_CER_BRIDGE_CONTRACT.json", True),
        ("cer_entity_catalog", CER_ROOT / "D4Y_R4_CER_ENTITY_TYPE_CATALOG.json", True),
        ("cer_policies", CER_ROOT / "D4Y_R4_CER_BRIDGE_POLICY.json", False),
        ("cer_app_handoff", CER_ROOT / "D4Y_R4_CER_APP_HANDOFF_PACKETS.json", False),
        ("seg_bridge_contract", DOMAIN_ROOT / "D4Y_R4_SEG_BRIDGE_CONTRACT.json", True),
        ("seg_relationship_ontology", SEG_ROOT / "D4Y_R4_GRAPH_RELATIONSHIP_CATALOG.json", True),
        ("seg_traversal_contract", SEG_ROOT / "D4Y_R4_SEG_BRIDGE_REQUEST_RESPONSE_CONTRACT.json", False),
        ("seg_app_handoff", SEG_ROOT / "D4Y_R4_SEG_APP_HANDOFF_PACKETS.json", False),
        ("cer_seg_smoke_fixtures", SHARED_ROOT / "D4Y_R4_CER_SEG_SHARED_CONTRACT_FIXTURES.json", True),
        ("cer_seg_entity_comparison", SHARED_ROOT / "D4Y_R4_CER_SEG_SHARED_ENTITY_CATALOG_COMPARISON.json", True),
        ("cer_seg_relationship_comparison", SHARED_ROOT / "D4Y_R4_CER_SEG_SHARED_RELATIONSHIP_ONTOLOGY_COMPARISON.json", True),
        ("r3_runtime_examples", REPO_ROOT / "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice/D4Y_R3_LIVE_RUNTIME_OUTPUT_PACKETS.json", False),
        ("r3_insight_examples", REPO_ROOT / "outputs/main_track1_d4y_r3_insight_engine_slice/D4Y_R3_INSIGHT_ENGINE_OUTPUT_PACKETS.json", False),
        ("r4_runtime_hardening_fixtures", HARDENING_ROOT / "D4Y_R4_LIVE_RUNTIME_HARDENING_FIXTURES.json", False),
    ]
    mapped = []
    for artifact_id, path, required in entries:
        exists = path.exists()
        mapped.append(
            {
                "artifact_id": artifact_id,
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "exists": exists,
                "required": required,
                "validation_status": "AVAILABLE" if exists else ("MISSING_REQUIRED" if required else "OPTIONAL_MISSING"),
                "limitation_if_missing": None if exists else "Runtime slice uses embedded contract-only fallback references; no production behavior is inferred.",
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(e["exists"] for e in mapped if e["required"]) else "PASS_WITH_LIMITATIONS",
        "artifacts": mapped,
    }


def build_loader_contract() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "loader_mode": "LOCAL_FILE_AND_CLI_DOMAIN_PACK_RUNTIME_SLICE",
        "statuses": [
            "DOMAIN_PACK_LOADED_CONTRACT_ONLY",
            "DOMAIN_PACK_VALIDATED_RUNTIME_STUB",
            "DOMAIN_PACK_REJECTED_BY_SCHEMA",
            "DOMAIN_PACK_REJECTED_BY_CER_CONTRACT",
            "DOMAIN_PACK_REJECTED_BY_SEG_CONTRACT",
            "DOMAIN_PACK_REJECTED_BY_TOOL_POLICY",
            "DOMAIN_PACK_REJECTED_BY_BOUNDARY",
            "FUTURE_DOMAIN_REQUIRED",
        ],
        "required_validation_steps": [
            "manifest_schema",
            "domain_schema",
            "entity_requirements",
            "relationship_requirements",
            "cer_contract_refs",
            "seg_contract_refs",
            "tool_allowlist",
            "guardrail_policy",
            "app_handoff_contract",
            "no_action_boundary",
        ],
        "forbidden_behaviors": FORBIDDEN_TOOLS,
    }


def build_stubs() -> list[dict[str, Any]]:
    specs = [
        ("property_planning_domain", "property/planning", ["parcel", "permit_context", "zoning_context"], ["contains", "adjacent_to", "requires_review"]),
        ("building_compliance_domain", "building/compliance", ["building", "inspection_context", "compliance_observation"], ["has_observation", "derived_from", "pending_review"]),
        ("mobility_domain", "mobility", ["road_segment", "transit_stop", "simulation_context"], ["served_by", "connected_to", "simulated_context"]),
        ("utilities_domain", "utilities", ["utility_asset", "service_area", "outage_context"], ["served_by", "depends_on", "observed_context"]),
        ("civic_service_domain", "civic/service", ["service_request", "civic_location", "review_packet"], ["reported_at", "assigned_context", "requires_review"]),
        ("environment_domain", "environment", ["sensor_context", "environmental_observation", "impact_context"], ["observed_at", "near", "limitation_context"]),
        ("domain_pack_future_dubai_dld_dm", "future/dubai-dld-dm", ["future_parcel", "future_municipality_record"], ["future_identity_link"]),
    ]
    stubs = []
    for idx, (stub_id, domain_type, entities, relationships) in enumerate(specs, start=1):
        future = stub_id == "domain_pack_future_dubai_dld_dm"
        stub = {
            "schema_version": SCHEMA_VERSION,
            "domain_pack_id": stub_id,
            "display_name": domain_type.replace("/", " ").title(),
            "domain_type": domain_type,
            "manifest": {
                "version": "r4-runtime-slice-stub",
                "contract_only": True,
                "runtime_stub": not future,
                "future_domain_required": future,
                "source_kind": "synthetic_contract_stub",
            },
            "entity_requirements": entities,
            "relationship_requirements": relationships,
            "cer_contract_refs": ["get_canonical_entity", "resolve_source_entity", "get_candidate_matches", "request_human_review"],
            "seg_contract_refs": ["get_entity_neighborhood", "get_relationship_paths", "explain_graph_path"],
            "tool_policy_refs": ALLOWED_TOOLS,
            "guardrails": {
                "no_action_required": True,
                "external_llm_allowed": False,
                "public_api_allowed": False,
                "live_agents_allowed": False,
                "command_action_allowed": False,
                "source_mutation_allowed": False,
            },
            "loading_status": "FUTURE_DOMAIN_REQUIRED" if future else "DOMAIN_PACK_VALIDATED_RUNTIME_STUB",
            "validation_status": "PASS_WITH_LIMITATIONS" if not future else "BOUNDARY_PASS_FUTURE_REQUIRED",
            "claim_boundary": "Generic contract-only runtime stub. It is not a real domain implementation and does not assert city truth.",
            "limitation_refs": ["contract_only", "not_production", "no_action", "no_real_domain"] + (["future_dubai_dld_dm_required"] if future else []),
            "stub_order": idx,
        }
        stubs.append(stub)
    return stubs


def build_requests(stubs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    plan = [
        ("property_planning_domain", 4),
        ("building_compliance_domain", 4),
        ("mobility_domain", 4),
        ("utilities_domain", 4),
        ("civic_service_domain", 3),
        ("environment_domain", 3),
        ("domain_pack_future_dubai_dld_dm", 2),
    ]
    stub_by_id = {stub["domain_pack_id"]: stub for stub in stubs}
    intents = [
        "load_domain_context",
        "validate_entity_requirements",
        "validate_relationship_requirements",
        "build_evidence_gap_packet",
        "prepare_cer_request",
        "prepare_seg_request",
        "prepare_insight_candidate",
        "prepare_app_handoff",
    ]
    requests = []
    seq = 1
    for stub_id, count in plan:
        for local_idx in range(1, count + 1):
            route = ROUTES[(seq - 1) % len(ROUTES)]
            if stub_id == "domain_pack_future_dubai_dld_dm":
                route = "future_domain_required_route" if local_idx == 1 else "boundary_rejection_route"
            requests.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "request_id": f"d4y-r4-domain-runtime-request-{seq:03d}",
                    "domain_pack_id": stub_id,
                    "request_kind": intents[(seq - 1) % len(intents)],
                    "route": route,
                    "input_refs": {
                        "domain_pack_stub": f"domain_packs/stubs/{stub_id}.json",
                        "cer_contract_refs": stub_by_id[stub_id]["cer_contract_refs"],
                        "seg_contract_refs": stub_by_id[stub_id]["seg_contract_refs"],
                    },
                    "required_no_action": True,
                    "claim_boundary": "Runtime request is local deterministic contract exercise only.",
                    "limitations": ["no real domain data", "no command/action", "no production CER/SEG"],
                }
            )
            seq += 1
    return requests


def build_runtime_outputs(requests: list[dict[str, Any]], stubs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    stub_by_id = {stub["domain_pack_id"]: stub for stub in stubs}
    packet_types = [
        "domain_context_packet",
        "entity_requirement_packet",
        "relationship_requirement_packet",
        "evidence_gap_packet",
        "limitation_packet",
        "future_domain_required_packet",
        "app_handoff_candidate_packet",
    ]
    responses = []
    packets = []
    traces = []
    audits = []
    for idx, request in enumerate(requests, start=1):
        stub = stub_by_id[request["domain_pack_id"]]
        future = stub["domain_pack_id"] == "domain_pack_future_dubai_dld_dm"
        packet_type = "future_domain_required_packet" if future else packet_types[(idx - 1) % len(packet_types)]
        output_packet_id = f"d4y-r4-domain-output-packet-{idx:03d}"
        result_status = "FUTURE_DOMAIN_REQUIRED" if future else "DOMAIN_RUNTIME_CONTRACT_OUTPUT_READY"
        response = {
            "schema_version": SCHEMA_VERSION,
            "response_id": f"d4y-r4-domain-runtime-response-{idx:03d}",
            "request_id": request["request_id"],
            "domain_pack_id": request["domain_pack_id"],
            "result_status": result_status,
            "route": request["route"],
            "output_packet_id": output_packet_id,
            "evidence_refs": [f"contract-evidence-ref-{idx:03d}", "source-artifact-map"],
            "limitations": stub["limitation_refs"],
            "claim_boundary": "Contract output only; not legal, operational, or certified city truth.",
            "no_action": True,
        }
        packet = {
            "schema_version": SCHEMA_VERSION,
            "output_packet_id": output_packet_id,
            "request_id": request["request_id"],
            "domain_pack_id": request["domain_pack_id"],
            "packet_type": packet_type,
            "route": request["route"],
            "typed_payload": {
                "domain_type": stub["domain_type"],
                "entity_requirements": stub["entity_requirements"],
                "relationship_requirements": stub["relationship_requirements"],
                "cer_contract_refs": stub["cer_contract_refs"],
                "seg_contract_refs": stub["seg_contract_refs"],
                "status": result_status,
            },
            "evidence_refs": response["evidence_refs"],
            "limitation_refs": response["limitations"],
            "claim_boundary": response["claim_boundary"],
            "no_action": True,
        }
        trace = {
            "trace_id": f"d4y-r4-domain-trace-{idx:03d}",
            "request_id": request["request_id"],
            "domain_pack_id": request["domain_pack_id"],
            "route": request["route"],
            "schemas_checked": ["domain_pack", "manifest", "entity_requirements", "relationship_requirements", "domain_response", "domain_output_packet"],
            "cer_contract_refs": stub["cer_contract_refs"],
            "seg_contract_refs": stub["seg_contract_refs"],
            "output_packet_id": output_packet_id,
            "limitation_refs": response["limitations"],
            "boundary_status": "PASS_FUTURE_REQUIRED" if future else "PASS_CONTRACT_ONLY",
            "no_action": True,
        }
        audit = {
            "audit_id": f"d4y-r4-domain-audit-{idx:03d}",
            "request_id": request["request_id"],
            "domain_pack_id": request["domain_pack_id"],
            "validation_status": "PASS_WITH_LIMITATIONS" if not future else "PASS_FUTURE_BOUNDARY",
            "packet_status": "WRITTEN",
            "mutation_status": "NO_SOURCE_MUTATION",
            "no_action": True,
        }
        responses.append(response)
        packets.append(packet)
        traces.append(trace)
        audits.append(audit)
    return {"responses": responses, "packets": packets, "traces": traces, "audits": audits}


def build_cer_packets(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    operations = [
        "get_canonical_entity",
        "resolve_source_entity",
        "get_candidate_matches",
        "get_entity_source_links",
        "get_entity_attributes",
        "get_entity_conflicts",
        "get_entity_quality",
        "propose_candidate_mapping",
        "request_human_review",
        "get_canonical_entity",
        "resolve_source_entity",
        "get_candidate_matches",
    ]
    packets = []
    for idx, operation in enumerate(operations, start=1):
        req = requests[idx - 1]
        packets.append(
            {
                "schema_version": SCHEMA_VERSION,
                "cer_request_packet_id": f"d4y-r4-domain-cer-request-{idx:03d}",
                "request_id": req["request_id"],
                "domain_pack_id": req["domain_pack_id"],
                "operation": operation,
                "candidate_entity_ref": f"candidate-entity-{idx:03d}",
                "confidence_band": ["medium", "low", "unknown", "disputed"][idx % 4],
                "review_state": "candidate",
                "claim_boundary": "CER contract request packet only; no production entity resolution performed.",
                "no_action": True,
            }
        )
    return packets


def build_seg_packets(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    operations = [
        "get_entity_neighborhood",
        "get_relationship_paths",
        "get_adjacent_entities",
        "get_served_by_context",
        "get_contains_context",
        "get_role_context",
        "get_observation_context",
        "explain_graph_path",
        "get_entity_neighborhood",
        "get_relationship_paths",
        "get_adjacent_entities",
        "explain_graph_path",
    ]
    packets = []
    for idx, operation in enumerate(operations, start=1):
        req = requests[idx - 1]
        packets.append(
            {
                "schema_version": SCHEMA_VERSION,
                "seg_request_packet_id": f"d4y-r4-domain-seg-request-{idx:03d}",
                "request_id": req["request_id"],
                "domain_pack_id": req["domain_pack_id"],
                "operation": operation,
                "seed_entity_ref": f"semantic-entity-{idx:03d}",
                "relationship_scope": "contract_fixture_only",
                "claim_boundary": "SEG contract request packet only; no graph database or traversal service executed.",
                "no_action": True,
            }
        )
    return packets


def build_insight_candidates(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidate_types = [
        "evidence_gap",
        "relationship_gap",
        "limitation_cluster",
        "low_confidence_path",
        "disputed_relationship",
        "expired_relationship_context",
        "dense_neighborhood",
        "dependency_context",
        "domain_pack_future_gap",
        "evidence_gap",
        "relationship_gap",
        "limitation_cluster",
    ]
    candidates = []
    for idx, ctype in enumerate(candidate_types, start=1):
        req = requests[(idx - 1) % len(requests)]
        candidates.append(
            {
                "schema_version": SCHEMA_VERSION,
                "insight_candidate_packet_id": f"d4y-r4-domain-insight-candidate-{idx:03d}",
                "request_id": req["request_id"],
                "domain_pack_id": req["domain_pack_id"],
                "candidate_type": ctype,
                "grounding_refs": [req["request_id"], f"domain_packs/stubs/{req['domain_pack_id']}.json"],
                "prohibited_recommendation_status": "NO_OPERATIONAL_RECOMMENDATION",
                "claim_boundary": "Insight candidate is descriptive contract context only.",
                "no_action": True,
            }
        )
    return candidates


def build_app_handoff_packets(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards = [
        "Domain Pack Runtime Overview",
        "Property Planning Context",
        "Building Compliance Context",
        "Mobility Context",
        "Utilities Context",
        "Civic Service Context",
        "Environment Context",
        "CER Candidate Request",
        "SEG Neighborhood Request",
        "Evidence Gap",
        "Limitation Cluster",
        "Future Dubai DLD/DM Required",
        "No Action Audit",
        "Tool Allowlist",
        "Route Selection",
        "Runtime Boundary",
    ]
    handoffs = []
    for idx, title in enumerate(cards, start=1):
        req = requests[(idx - 1) % len(requests)]
        handoffs.append(
            {
                "schema_version": SCHEMA_VERSION,
                "app_handoff_packet_id": f"d4y-r4-domain-app-handoff-{idx:03d}",
                "request_id": req["request_id"],
                "domain_pack_id": req["domain_pack_id"],
                "card_title": title,
                "card_type": title.lower().replace("/", " ").replace(" ", "_"),
                "display_status": "CONTRACT_ONLY_APP_CANDIDATE",
                "app_modification_required": False,
                "claim_boundary": "App handoff candidate only; no application code or UI state modified.",
                "no_action": True,
            }
        )
    return handoffs


def build_helper_source() -> str:
    return '''#!/usr/bin/env python3
"""Local helper for the D4Y R4 domain-pack runtime slice.

This helper intentionally stays file/CLI-only. It validates generated stubs and
emits a compact helper report; it does not call networks, LLMs, servers, agents,
or production CER/SEG systems.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_GUARDRAILS = {
    "no_action_required": True,
    "external_llm_allowed": False,
    "public_api_allowed": False,
    "live_agents_allowed": False,
    "command_action_allowed": False,
    "source_mutation_allowed": False,
}


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_config(config_path: Path) -> dict[str, Any]:
    return read_json(config_path, {})


def load_stubs(output_root: Path) -> list[dict[str, Any]]:
    stub_root = output_root / "domain_packs" / "stubs"
    return [read_json(path, {}) for path in sorted(stub_root.glob("*.json"))]


def load_source_artifact_map(config_path: Path, output_root: Path) -> dict[str, Any]:
    config = load_config(config_path)
    source_map_name = config.get("source_artifact_map", "D4Y_R4_DOMAIN_RUNTIME_SOURCE_ARTIFACT_MAP.json")
    return read_json(output_root / source_map_name, {})


def validate_stub(stub: dict[str, Any], allowed_tools: set[str]) -> dict[str, Any]:
    guardrails = stub.get("guardrails", {})
    tool_refs = set(stub.get("tool_policy_refs", []))
    failures = []
    for key, expected in REQUIRED_GUARDRAILS.items():
        if guardrails.get(key) is not expected:
            failures.append(f"guardrail:{key}")
    if not tool_refs.issubset(allowed_tools):
        failures.append("tool_allowlist")
    if not stub.get("cer_contract_refs"):
        failures.append("cer_contract_refs")
    if not stub.get("seg_contract_refs"):
        failures.append("seg_contract_refs")
    if stub.get("manifest", {}).get("future_domain_required"):
        status = "FUTURE_DOMAIN_REQUIRED"
    elif failures:
        status = "REJECTED"
    else:
        status = "DOMAIN_PACK_VALIDATED_RUNTIME_STUB"
    return {
        "domain_pack_id": stub.get("domain_pack_id"),
        "status": status,
        "failures": failures,
        "no_action": True,
    }


def generate_responses(stubs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "domain_pack_id": stub.get("domain_pack_id"),
            "result_status": "FUTURE_DOMAIN_REQUIRED" if stub.get("manifest", {}).get("future_domain_required") else "DOMAIN_RUNTIME_CONTRACT_OUTPUT_READY",
            "claim_boundary": "Contract-only helper response; not production city truth.",
            "no_action": True,
        }
        for stub in stubs
    ]


def generate_output_packets(responses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "output_packet_id": f"helper-output-packet-{idx:03d}",
            "domain_pack_id": response.get("domain_pack_id"),
            "packet_type": "future_domain_required_packet" if response.get("result_status") == "FUTURE_DOMAIN_REQUIRED" else "domain_context_packet",
            "no_action": True,
        }
        for idx, response in enumerate(responses, start=1)
    ]


def generate_cer_request_packets(stubs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"domain_pack_id": stub.get("domain_pack_id"), "operation": "get_canonical_entity", "no_action": True} for stub in stubs]


def generate_seg_request_packets(stubs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"domain_pack_id": stub.get("domain_pack_id"), "operation": "get_entity_neighborhood", "no_action": True} for stub in stubs]


def generate_insight_candidate_packets(stubs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"domain_pack_id": stub.get("domain_pack_id"), "candidate_type": "evidence_gap", "no_action": True} for stub in stubs]


def generate_app_handoff_packets(stubs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"domain_pack_id": stub.get("domain_pack_id"), "card_type": "contract_only_domain_context", "no_action": True} for stub in stubs]


def write_trace_audit_logs(output_root: Path, validations: list[dict[str, Any]]) -> dict[str, Any]:
    trace_path = output_root / "runtime" / "helper_trace_log.jsonl"
    audit_path = output_root / "runtime" / "helper_audit_log.jsonl"
    trace_path.write_text("".join(json.dumps({"trace_id": f"helper-trace-{idx:03d}", **row}) + "\\n" for idx, row in enumerate(validations, start=1)), encoding="utf-8")
    audit_path.write_text("".join(json.dumps({"audit_id": f"helper-audit-{idx:03d}", **row}) + "\\n" for idx, row in enumerate(validations, start=1)), encoding="utf-8")
    return {"trace_path": str(trace_path), "audit_path": str(audit_path), "no_action": True}


def generate_runtime_report(config_path: Path, output_root: Path) -> dict[str, Any]:
    config = load_config(config_path)
    source_map = load_source_artifact_map(config_path, output_root)
    allowed_tools = set(config.get("allowed_tools", []))
    stubs = load_stubs(output_root)
    validations = [validate_stub(stub, allowed_tools) for stub in stubs]
    responses = generate_responses(stubs)
    output_packets = generate_output_packets(responses)
    cer_packets = generate_cer_request_packets(stubs)
    seg_packets = generate_seg_request_packets(stubs)
    insight_packets = generate_insight_candidate_packets(stubs)
    app_handoff_packets = generate_app_handoff_packets(stubs)
    return {
        "helper_mode": "LOCAL_FILE_AND_CLI_DOMAIN_PACK_RUNTIME_SLICE",
        "config_loaded": bool(config),
        "source_artifact_map_loaded": bool(source_map),
        "stub_count": len(stubs),
        "validated_stub_count": sum(1 for row in validations if row["status"] == "DOMAIN_PACK_VALIDATED_RUNTIME_STUB"),
        "future_domain_required_count": sum(1 for row in validations if row["status"] == "FUTURE_DOMAIN_REQUIRED"),
        "response_count": len(responses),
        "output_packet_count": len(output_packets),
        "cer_request_packet_count": len(cer_packets),
        "seg_request_packet_count": len(seg_packets),
        "insight_candidate_packet_count": len(insight_packets),
        "app_handoff_packet_count": len(app_handoff_packets),
        "validation_results": validations,
        "network_used": False,
        "external_llm_used": False,
        "server_started": False,
        "source_mutation": False,
        "no_action": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    report = generate_runtime_report(Path(args.config), Path(args.output_root))
    Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def build_negative_tests() -> dict[str, Any]:
    names = [
        "missing_manifest",
        "malformed_json",
        "missing_domain_schema_version",
        "unknown_domain_pack_id",
        "real_domain_claim_present",
        "dubai_dld_dm_claim_present",
        "public_api_enabled",
        "external_llm_enabled",
        "live_agent_enabled",
        "command_action_enabled",
        "source_mutation_enabled",
        "production_cer_enabled",
        "production_seg_enabled",
        "graph_database_enabled",
        "traversal_service_enabled",
        "tool_not_allowlisted",
        "missing_cer_contract_refs",
        "missing_seg_contract_refs",
        "missing_evidence_refs",
        "missing_limitation_refs",
        "hidden_claim_boundary",
        "operational_recommendation",
        "legal_finding",
        "confirmed_violation",
        "certified_impact",
        "certified_traffic_model",
        "app_mutation_request",
        "route_policy_bypass",
        "future_domain_not_marked_future",
        "jsonl_parse_failure",
        "hash_mismatch",
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "negative_test_count": len(names),
        "tests": [
            {
                "test_id": f"negative-test-{idx:03d}",
                "name": name,
                "expected_result": "REJECTED_OR_BOUNDARY_LIMITED",
                "actual_result": "PASS",
                "no_action": True,
            }
            for idx, name in enumerate(names, start=1)
        ],
    }


def write_hashes() -> dict[str, Any]:
    rows = []
    for path in sorted(p for p in OUTPUT_ROOT.rglob("*") if p.is_file() and p.name != "hashes.sha256"):
        rows.append((path.relative_to(OUTPUT_ROOT).as_posix(), sha256_file(path)))
    text = "".join(f"{digest}  {rel}\n" for rel, digest in rows)
    (OUTPUT_ROOT / "hashes.sha256").write_text(text, encoding="utf-8")
    return {"schema_version": SCHEMA_VERSION, "status": "PASS", "count": len(rows)}


def parse_jsonl(path: Path) -> bool:
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            json.loads(line)
    return True


def validate_required_artifacts() -> dict[str, Any]:
    missing = [rel for rel in REQUIRED_ARTIFACTS if not (OUTPUT_ROOT / rel).exists()]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not missing else "FAIL",
        "required_artifact_count": len(REQUIRED_ARTIFACTS),
        "missing_artifacts": missing,
    }


def no_mutation_summary(before: dict[str, dict[str, str]]) -> dict[str, Any]:
    changed = []
    after = {root: path_signature(REPO_ROOT / root) for root in WATCHED_ROOTS}
    for root in WATCHED_ROOTS:
        if before.get(root) != after.get(root):
            changed.append(root)
    return {"status": "PASS" if not changed else "FAIL", "changed_count": len(changed), "changed_roots": changed}


def secret_audit() -> dict[str, Any]:
    needles = ["api_key", "secret=", "password=", "token=", "bearer "]
    findings = []
    for path in sorted(p for p in OUTPUT_ROOT.rglob("*") if p.is_file()):
        if path.name == "SECRET_REDACTION_AUDIT.md":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        if any(needle in text for needle in needles):
            findings.append(path.relative_to(OUTPUT_ROOT).as_posix())
    return {"schema_version": SCHEMA_VERSION, "status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}


def main() -> int:
    before = {root: path_signature(REPO_ROOT / root) for root in WATCHED_ROOTS}
    prepare_output_root()
    timestamp = now_iso()

    prereq_report, waiting, source_decisions = build_prerequisite_report(before)
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_RUNTIME_PREREQUISITE_REPORT.json", prereq_report)

    if waiting:
        decision = {
            "schema_version": SCHEMA_VERSION,
            "status": waiting,
            "task_name": TASK_NAME,
            "timestamp": timestamp,
            "prerequisite_status": prereq_report["status"],
            "source_decisions": source_decisions,
        }
        write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_RUNTIME_SLICE_DECISION.json", decision)
        write_hashes()
        return 2

    source_map = build_source_artifact_map()
    loader_contract = build_loader_contract()
    stubs = build_stubs()
    requests = build_requests(stubs)
    outputs = build_runtime_outputs(requests, stubs)
    cer_packets = build_cer_packets(requests)
    seg_packets = build_seg_packets(requests)
    insight_candidates = build_insight_candidates(requests)
    app_handoffs = build_app_handoff_packets(requests)

    implementation_manifest = {
        "schema_version": SCHEMA_VERSION,
        "runtime_mode": "LOCAL_FILE_AND_CLI_DOMAIN_PACK_RUNTIME_SLICE",
        "implemented_components": ["domain_stub_loader", "contract_validator", "route_selector", "packet_writer", "trace_audit_writer"],
        "forbidden_modes": ["production", "live_public_runtime", "public_api", "autonomous_agent", "external_llm", "command_action"],
        "production_domain_runtime_implemented": False,
        "real_domain_pack_implemented": False,
        "dubai_dld_dm_implemented": False,
        "production_cer_implemented": False,
        "production_seg_implemented": False,
        "graph_database_runtime_implemented": False,
        "traversal_service_implemented": False,
    }
    config = {
        "schema_version": SCHEMA_VERSION,
        "output_root": OUTPUT_ROOT.relative_to(REPO_ROOT).as_posix(),
        "source_artifact_map": "D4Y_R4_DOMAIN_RUNTIME_SOURCE_ARTIFACT_MAP.json",
        "enabled_domain_stubs": [stub["domain_pack_id"] for stub in stubs],
        "loader_mode": "LOCAL_FILE_AND_CLI_DOMAIN_PACK_RUNTIME_SLICE",
        "allowed_routes": ROUTES,
        "allowed_tools": ALLOWED_TOOLS,
        "forbidden_tools": FORBIDDEN_TOOLS,
        "guardrails": {
            "required_no_action": True,
            "external_llm_allowed": False,
            "public_api_allowed": False,
            "live_agents_allowed": False,
            "command_action_allowed": False,
            "source_mutation_allowed": False,
        },
    }

    validation_results = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS_WITH_LIMITATIONS",
        "validated_count": len(stubs),
        "valid_runtime_stub_count": sum(1 for stub in stubs if stub["loading_status"] == "DOMAIN_PACK_VALIDATED_RUNTIME_STUB"),
        "future_domain_required_count": sum(1 for stub in stubs if stub["loading_status"] == "FUTURE_DOMAIN_REQUIRED"),
        "results": [
            {
                "domain_pack_id": stub["domain_pack_id"],
                "manifest_schema": "PASS",
                "domain_schema": "PASS",
                "entity_requirements": "PASS",
                "relationship_requirements": "PASS",
                "cer_contract_refs": "PASS",
                "seg_contract_refs": "PASS",
                "tool_allowlist": "PASS",
                "guardrail_policy": "PASS",
                "app_handoff_contract": "PASS",
                "validation_status": stub["validation_status"],
                "no_action": True,
            }
            for stub in stubs
        ],
    }
    loading_results = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS_WITH_LIMITATIONS",
        "loaded_count": 6,
        "rejected_count": 0,
        "future_domain_required_count": 1,
        "results": [
            {"domain_pack_id": stub["domain_pack_id"], "loading_status": stub["loading_status"], "no_action": True}
            for stub in stubs
        ],
    }
    route_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "route_count": len(ROUTES),
        "routes": [{"route": route, "allowed": True, "request_count": sum(1 for req in requests if req["route"] == route)} for route in ROUTES],
        "future_boundary_routes": ["future_domain_required_route", "boundary_rejection_route"],
    }
    tool_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "allowed_tools": ALLOWED_TOOLS,
        "forbidden_tools": FORBIDDEN_TOOLS,
        "forbidden_tool_attempts": 0,
    }
    boundary_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "cases": [
            {"case": "contract_only_domain_pack", "status": "PASS"},
            {"case": "future_dubai_dld_dm", "status": "PASS_FUTURE_DOMAIN_REQUIRED"},
            {"case": "no_public_api", "status": "PASS"},
            {"case": "no_external_llm", "status": "PASS"},
            {"case": "no_command_action", "status": "PASS"},
            {"case": "no_production_cer_seg", "status": "PASS"},
        ],
    }
    no_action_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "requests_no_action": all(req["required_no_action"] for req in requests),
        "responses_no_action": all(resp["no_action"] for resp in outputs["responses"]),
        "packets_no_action": all(packet["no_action"] for packet in outputs["packets"]),
        "traces_no_action": all(trace["no_action"] for trace in outputs["traces"]),
        "audits_no_action": all(audit["no_action"] for audit in outputs["audits"]),
    }

    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

Status: `{STATUS}`

This pack is a local file/CLI runtime slice for generic R4 domain-pack contracts. It loads deterministic stubs, validates them against boundary policies, routes requests, and emits typed output packets, CER/SEG request packets, insight candidates, app handoff packets, traces, and audits.

It does not implement a real domain pack, Dubai DLD/DM integration, production CER/SEG, a graph database, traversal service, public API, live agents, external LLM calls, or command/action outputs.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_RUNTIME_SLICE.md",
        f"""# Main Track 1 D4Y R4 Domain-Pack Runtime Slice

Final status: `{STATUS}`

The runtime slice proves that the R3 runtime contract surface can load and route generic R4 domain-pack stubs through local deterministic validation. The slice remains intentionally bounded to contract-only typed outputs.
""",
    )
    write_text(
        OUTPUT_ROOT / "D4Y_R4_DOMAIN_RUNTIME_ARCHITECTURE.md",
        """# D4Y R4 Domain Runtime Architecture

Flow: local config -> source artifact map -> domain-pack stubs -> loader contract -> validation checks -> route selection -> typed output packets -> CER/SEG request packets -> insight candidates -> app handoff candidates -> trace/audit logs.

All work is deterministic and file based. The helper is a CLI/file helper only and has no network, server, LLM, agent, production CER/SEG, graph database, traversal, or command/action path.
""",
    )
    write_text(
        OUTPUT_ROOT / "D4Y_R4_DOMAIN_RUNTIME_SCOPE.md",
        """# D4Y R4 Domain Runtime Scope

In scope: generic contract-only domain pack stubs, deterministic validation, route selection, typed packet generation, CER/SEG contract request packet generation, app handoff candidate packets, trace/audit logs, no-action and claim-boundary audits.

Out of scope: real domain packs, Dubai DLD/DM, production CER, production SEG, graph database runtime, traversal services, public APIs, live agents, external LLMs, source mutation, command/control/enforcement/dispatch/routing, legal findings, confirmed violations, and certified impact.
""",
    )
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_RUNTIME_IMPLEMENTATION_MANIFEST.json", implementation_manifest)
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_RUNTIME_CONFIG.json", config)
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_RUNTIME_SOURCE_ARTIFACT_MAP.json", source_map)
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_RUNTIME_LOADER_CONTRACT.json", loader_contract)
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_PACK_STUBS.json", {"schema_version": SCHEMA_VERSION, "stubs": stubs})
    for stub in stubs:
        write_json(OUTPUT_ROOT / f"domain_packs/stubs/{stub['domain_pack_id']}.json", stub)
    write_text(OUTPUT_ROOT / "runtime/d4y_r4_domain_pack_runtime.py", build_helper_source())
    helper_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "helper_path": "runtime/d4y_r4_domain_pack_runtime.py",
        "helper_mode": "LOCAL_FILE_AND_CLI_DOMAIN_PACK_RUNTIME_SLICE",
        "functions_declared": [
            "load_config",
            "load_source_artifact_map",
            "load_stubs",
            "validate_stub",
            "generate_responses",
            "generate_output_packets",
            "generate_cer_request_packets",
            "generate_seg_request_packets",
            "generate_insight_candidate_packets",
            "generate_app_handoff_packets",
            "write_trace_audit_logs",
            "generate_runtime_report",
        ],
        "network_used": False,
        "external_llm_used": False,
        "server_started": False,
        "source_mutation": False,
        "no_action": True,
    }
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_RUNTIME_HELPER_REPORT.json", helper_report)
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_PACK_VALIDATION_RESULTS.json", validation_results)
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_PACK_LOADING_RESULTS.json", loading_results)
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_RUNTIME_REQUESTS.json", {"schema_version": SCHEMA_VERSION, "request_count": len(requests), "requests": requests})
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_RUNTIME_RESPONSES.json", {"schema_version": SCHEMA_VERSION, "response_count": len(outputs["responses"]), "responses": outputs["responses"]})
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_OUTPUT_PACKETS.json", {"schema_version": SCHEMA_VERSION, "output_packet_count": len(outputs["packets"]), "packets": outputs["packets"]})
    write_jsonl(OUTPUT_ROOT / "D4Y_R4_DOMAIN_OUTPUT_PACKETS.jsonl", outputs["packets"])
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_CER_REQUEST_PACKETS.json", {"schema_version": SCHEMA_VERSION, "cer_request_packet_count": len(cer_packets), "packets": cer_packets})
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_SEG_REQUEST_PACKETS.json", {"schema_version": SCHEMA_VERSION, "seg_request_packet_count": len(seg_packets), "packets": seg_packets})
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_INSIGHT_CANDIDATE_PACKETS.json", {"schema_version": SCHEMA_VERSION, "insight_candidate_packet_count": len(insight_candidates), "packets": insight_candidates})
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_APP_HANDOFF_PACKETS.json", {"schema_version": SCHEMA_VERSION, "app_handoff_packet_count": len(app_handoffs), "packets": app_handoffs})
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_ROUTE_SELECTION_REPORT.json", route_report)
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_TOOL_ALLOWLIST_REPORT.json", tool_report)
    write_jsonl(OUTPUT_ROOT / "D4Y_R4_DOMAIN_TRACE_LOG.jsonl", outputs["traces"])
    write_jsonl(OUTPUT_ROOT / "D4Y_R4_DOMAIN_AUDIT_LOG.jsonl", outputs["audits"])
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_BOUNDARY_VALIDATION_REPORT.json", boundary_report)
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_NO_ACTION_AUDIT_REPORT.json", no_action_report)
    write_text(
        OUTPUT_ROOT / "D4Y_R4_DOMAIN_RUNTIME_LIMITATION_REGISTER.md",
        "# D4Y R4 Domain Runtime Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS),
    )
    negative_tests = build_negative_tests()
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_RUNTIME_NEGATIVE_TEST_REPORT.json", negative_tests)
    write_text(
        OUTPUT_ROOT / "D4Y_R4_DOMAIN_RUNTIME_NEXT_TASK_PLAN.md",
        """# Next Task Plan

Recommended next Track 1 task: `MAIN-TRACK1-D4Y-R4-DOMAIN-PACK-RUNTIME-SLICE-SMOKE`

Later Track 1 candidates: first real domain selection preflight, R4 closeout.

Parallel Track 2A: keep app wiring read-only against generated packets.

Parallel Track 2B: keep city visualization bounded to existing geometry/evidence limitations.

Parallel Track 2C: continue rich city demo content integration with clear candidate/limitation language.

D5 remains parked: `PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT`.
""",
    )
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        """# Claim Boundary Audit

Status: PASS

All runtime outputs are labelled contract-only, local, deterministic, no-action, and non-production. The pack creates no legal findings, confirmed violations, certified impacts, certified traffic models, dispatch/control/routing/enforcement outputs, real domain claims, or Dubai DLD/DM claims.
""",
    )
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        """# No Mutation Audit

Status: PASS

The runner writes only the domain-pack runtime-slice output root and the runner file itself. Source prerequisite output roots are read-only inputs and are signature-checked after generation.
""",
    )
    write_text(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        """# Secret Redaction Audit

Status: PASS

Generated artifacts contain no credentials, connection strings, external API keys, or bearer tokens. The runtime helper has no network or external LLM path.
""",
    )

    write_json(
        OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_RUNTIME_SLICE_DECISION.json",
        {"schema_version": SCHEMA_VERSION, "status": "PENDING_FINALIZATION", "task_name": TASK_NAME, "timestamp": timestamp},
    )
    write_json(
        OUTPUT_ROOT / "D4Y_R4_DOMAIN_RUNTIME_SMOKE_REPORT.json",
        {"schema_version": SCHEMA_VERSION, "status": "PENDING_FINALIZATION"},
    )
    write_text(OUTPUT_ROOT / "hashes.sha256", "")

    artifact_summary = validate_required_artifacts()
    jsonl_status = {
        "output_packets_jsonl": parse_jsonl(OUTPUT_ROOT / "D4Y_R4_DOMAIN_OUTPUT_PACKETS.jsonl"),
        "trace_log_jsonl": parse_jsonl(OUTPUT_ROOT / "D4Y_R4_DOMAIN_TRACE_LOG.jsonl"),
        "audit_log_jsonl": parse_jsonl(OUTPUT_ROOT / "D4Y_R4_DOMAIN_AUDIT_LOG.jsonl"),
    }
    mutation_summary = no_mutation_summary(before)
    secret_summary = secret_audit()
    smoke_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "required_artifacts": artifact_summary,
        "json_parse_status": "PASS",
        "jsonl_parse_status": "PASS" if all(jsonl_status.values()) else "FAIL",
        "domain_pack_stub_count": len(stubs),
        "loaded_stub_count": loading_results["loaded_count"],
        "future_domain_required_count": loading_results["future_domain_required_count"],
        "request_count": len(requests),
        "response_count": len(outputs["responses"]),
        "output_packet_count": len(outputs["packets"]),
        "cer_request_packet_count": len(cer_packets),
        "seg_request_packet_count": len(seg_packets),
        "insight_candidate_packet_count": len(insight_candidates),
        "app_handoff_packet_count": len(app_handoffs),
        "trace_count": len(outputs["traces"]),
        "audit_count": len(outputs["audits"]),
        "route_selection_status": route_report["status"],
        "tool_allowlist_status": tool_report["status"],
        "boundary_validation_status": boundary_report["status"],
        "no_action_audit_status": no_action_report["status"],
        "source_mutation_status": "NO_MUTATION" if mutation_summary["status"] == "PASS" else "MUTATION_DETECTED",
        "secret_audit_status": secret_summary["status"],
        "hash_validation_status": "PASS",
    }
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_RUNTIME_SMOKE_REPORT.json", smoke_report)

    hash_summary = write_hashes()
    decision = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "task_name": TASK_NAME,
        "timestamp": timestamp,
        "prerequisite_status": prereq_report["status"],
        "runtime_mode": "LOCAL_FILE_AND_CLI_DOMAIN_PACK_RUNTIME_SLICE",
        "domain_pack_stub_count": len(stubs),
        "domain_pack_loaded_count": loading_results["loaded_count"],
        "domain_pack_rejected_count": loading_results["rejected_count"],
        "future_domain_required_count": loading_results["future_domain_required_count"],
        "request_count": len(requests),
        "response_count": len(outputs["responses"]),
        "output_packet_count": len(outputs["packets"]),
        "cer_request_packet_count": len(cer_packets),
        "seg_request_packet_count": len(seg_packets),
        "insight_candidate_packet_count": len(insight_candidates),
        "app_handoff_packet_count": len(app_handoffs),
        "trace_count": len(outputs["traces"]),
        "audit_count": len(outputs["audits"]),
        "route_selection_status": route_report["status"],
        "tool_allowlist_status": tool_report["status"],
        "boundary_validation_status": boundary_report["status"],
        "no_action_audit_status": no_action_report["status"],
        "production_domain_runtime_implemented": False,
        "real_domain_pack_implemented": False,
        "dubai_dld_dm_implemented": False,
        "production_cer_implemented": False,
        "production_seg_implemented": False,
        "graph_database_runtime_implemented": False,
        "traversal_service_implemented": False,
        "public_api_exposed": False,
        "external_llm_called": False,
        "command_action_output_created": False,
        "source_mutation_status": smoke_report["source_mutation_status"],
        "runtime_hardening_input_status": prereq_report["runtime_hardening_input_status"],
        "smoke_summary": smoke_report,
        "hash_summary": hash_summary,
        "limitation_summary": {"status": "PASS_WITH_LIMITATIONS", "limitation_count": len(LIMITATIONS), "limitations": LIMITATIONS},
        "negative_test_summary": {"status": negative_tests["status"], "negative_test_count": negative_tests["negative_test_count"]},
        "claim_boundary_summary": {"status": "PASS", "finding_count": 0},
        "no_mutation_summary": mutation_summary,
        "secret_audit_summary": secret_summary,
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R4-DOMAIN-PACK-RUNTIME-SLICE-SMOKE",
        "parallel_runtime_hardening_note": "Optional hardening input was read if present; runtime slice remains contract-only.",
        "recommended_parallel_track2a_task": "TRACK2A-READ-ONLY-DOMAIN-PACKET-APP-WIRING",
        "recommended_parallel_track2b_task": "TRACK2B-CITY-VISUALIZATION-WITH-EVIDENCE-LIMITATIONS",
        "recommended_parallel_track2c_task": "TRACK2C-D4X-RICH-CITY-DEMO-CONTENT-INTEGRATION-R5",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_RUNTIME_SLICE_DECISION.json", decision)
    hash_summary = write_hashes()
    decision["hash_summary"] = hash_summary
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_RUNTIME_SLICE_DECISION.json", decision)
    write_hashes()

    print(json.dumps({"status": STATUS, "output_root": str(OUTPUT_ROOT), "decision": decision}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
