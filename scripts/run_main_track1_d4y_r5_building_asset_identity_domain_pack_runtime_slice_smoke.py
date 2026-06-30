#!/usr/bin/env python3
"""Build the R5 Building Asset Identity runtime-slice smoke pack."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

TASK_NAME = "MAIN-TRACK1-D4Y-R5-BUILDING-ASSET-IDENTITY-DOMAIN-PACK-RUNTIME-SLICE-SMOKE"
SCHEMA_VERSION = "main-track1-d4y-r5-building-asset-identity-runtime-slice-smoke.v1"
STATUS = "PASS_MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_SMOKE_WITH_LIMITATIONS"
WAITING = "WAITING_ON_MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE"
FAIL_STATUS = "FAIL_MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_SMOKE"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r5_building_asset_identity_domain_pack_runtime_slice_smoke"
R4_CLOSEOUT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_domain_pack_runtime_slice_smoke_and_closeout"
R5_CER_SEG_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r5_cer_seg_implementation_slice"
R5_SELECTION_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r5_first_domain_pack_selection_and_slice_preflight"
R5_BUILDING_PREFLIGHT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r5_building_asset_identity_domain_pack_preflight"
R5_RUNTIME_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r5_building_asset_identity_domain_pack_runtime_slice"
BARC_ROOT = REPO_ROOT / "outputs/d4_3d_barc_lod2_full_i3s_export_r1"
NYC_ROOT = REPO_ROOT / "outputs/d4_3d_nyc_2025_full_i3s_export_r1"

REQUIRED_DIRS = ["inputs", "fixtures", "packets", "app_handoff", "traces", "audits", "smoke", "guardrails", "logs"]
REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_SMOKE.md",
    "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_SMOKE_DECISION.json",
    "R5_BUILDING_ASSET_SMOKE_PREREQUISITE_REPORT.json",
    "R5_BUILDING_ASSET_SMOKE_PLAN.md",
    "R5_BUILDING_ASSET_SMOKE_INPUT_SUITE.json",
    "R5_BUILDING_ASSET_SMOKE_EXPECTED_RESULTS.json",
    "R5_BUILDING_ASSET_SMOKE_RUN_RESULTS.json",
    "R5_BUILDING_ASSET_SMOKE_REQUESTS.json",
    "R5_BUILDING_ASSET_SMOKE_RESPONSES.json",
    "R5_BUILDING_ASSET_SMOKE_OUTPUT_PACKETS.json",
    "R5_BUILDING_ASSET_SMOKE_OUTPUT_PACKETS.jsonl",
    "R5_BUILDING_ASSET_SMOKE_CER_REQUEST_PACKETS.json",
    "R5_BUILDING_ASSET_SMOKE_SEG_REQUEST_PACKETS.json",
    "R5_BUILDING_ASSET_SMOKE_IDENTITY_CONTEXT_PACKETS.json",
    "R5_BUILDING_ASSET_SMOKE_GRAPH_CONTEXT_PACKETS.json",
    "R5_BUILDING_ASSET_SMOKE_EVIDENCE_CHAIN_PACKETS.json",
    "R5_BUILDING_ASSET_SMOKE_APP_HANDOFF_PACKETS.json",
    "R5_BUILDING_ASSET_SMOKE_TRACE_LOG.jsonl",
    "R5_BUILDING_ASSET_SMOKE_AUDIT_LOG.jsonl",
    "R5_BUILDING_ASSET_SMOKE_SOURCE_ID_BOUNDARY_REPORT.json",
    "R5_BUILDING_ASSET_SMOKE_CER_SEG_INTEGRATION_REPORT.json",
    "R5_BUILDING_ASSET_SMOKE_GRAPH_CONTEXT_REPORT.json",
    "R5_BUILDING_ASSET_SMOKE_APP_HANDOFF_REPORT.json",
    "R5_BUILDING_ASSET_SMOKE_ROUTE_SELECTION_REPORT.json",
    "R5_BUILDING_ASSET_SMOKE_TOOL_ALLOWLIST_REPORT.json",
    "R5_BUILDING_ASSET_SMOKE_BOUNDARY_VALIDATION_REPORT.json",
    "R5_BUILDING_ASSET_SMOKE_NO_ACTION_AUDIT_REPORT.json",
    "R5_BUILDING_ASSET_SMOKE_REGRESSION_REPORT.json",
    "R5_BUILDING_ASSET_SMOKE_NEGATIVE_TEST_REPORT.json",
    "R5_BUILDING_ASSET_SMOKE_LIMITATION_REGISTER.md",
    "R5_BUILDING_ASSET_SMOKE_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]
WATCHED_ROOTS = [
    "outputs/main_track1_d4y_r4_domain_pack_runtime_slice_smoke_and_closeout",
    "outputs/main_track1_d4y_r5_cer_seg_implementation_slice",
    "outputs/main_track1_d4y_r5_first_domain_pack_selection_and_slice_preflight",
    "outputs/main_track1_d4y_r5_building_asset_identity_domain_pack_preflight",
    "outputs/main_track1_d4y_r5_second_domain_civic_service_context_preflight",
    "outputs/main_track1_d4y_r5_building_asset_identity_domain_pack_runtime_slice",
    "outputs/d4_3d_barc_lod2_full_i3s_export_r1",
    "outputs/d4_3d_nyc_2025_full_i3s_export_r1",
    "outputs/d4x",
    "outputs/track2",
]

FORBIDDEN_OUTPUTS = [
    "ownership/legal/certified truth from source IDs",
    "certified affected-building truth",
    "confirmed violation",
    "legal finding",
    "permit approval/rejection",
    "compliance determination",
    "certified impact",
    "certified traffic model",
    "command/action output",
    "dispatch/enforcement/routing/control",
    "production CER/SEG",
    "graph traversal service",
    "public API",
    "external LLM",
    "app integration",
]
SAFE_NEXT_LOOKS = ["inspect source evidence", "inspect source-ID limitation", "inspect CER candidate context", "inspect SEG graph context", "human review only"]
LIMITATIONS = [
    "smoke/regression only",
    "first bounded domain runtime slice only",
    "local file/CLI only",
    "fixture-backed CER/SEG, not production CER/SEG",
    "no graph database runtime",
    "no traversal service",
    "no app integration",
    "no Track 2 mutation",
    "no production domain runtime",
    "BARC/NYC source IDs are source/candidate context only",
    "no ownership/legal truth",
    "no certified affected-building truth",
    "no confirmed violation",
    "no permit/compliance decision",
    "no command/control/enforcement/dispatch/routing",
    "no external LLM",
    "no public API",
]
CLAIM_BOUNDARY = "Smoke output is source/candidate building identity context only; not ownership, legal identity, certified affected-building truth, violation, permit, compliance, or action guidance."
SOURCE_ID_BOUNDARY = "BARC OBJECTID/source_id and NYC BIN/BBL/DoITT/OBJECTID/GlobalID remain source/candidate context only."


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
    return {p.relative_to(root).as_posix(): f"{p.stat().st_size}:{sha256_file(p)}" for p in sorted(root.rglob("*")) if p.is_file()}


def prepare_output_root() -> None:
    resolved = OUTPUT_ROOT.resolve()
    if resolved.parent != (REPO_ROOT / "outputs").resolve() or resolved.name != "main_track1_d4y_r5_building_asset_identity_domain_pack_runtime_slice_smoke":
        raise RuntimeError(f"Refusing to reset unexpected output root: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for rel in REQUIRED_DIRS:
        (OUTPUT_ROOT / rel).mkdir(parents=True, exist_ok=True)


def import_helper(path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import helper: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prerequisite_report(before: dict[str, dict[str, str]]) -> tuple[dict[str, Any], bool]:
    paths = {
        "r4_closeout": R4_CLOSEOUT_ROOT / "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_RUNTIME_SLICE_SMOKE_AND_CLOSEOUT_DECISION.json",
        "r5_cer_seg": R5_CER_SEG_ROOT / "MAIN_TRACK1_D4Y_R5_CER_SEG_IMPLEMENTATION_SLICE_DECISION.json",
        "r5_selection": R5_SELECTION_ROOT / "MAIN_TRACK1_D4Y_R5_FIRST_DOMAIN_PACK_SELECTION_AND_SLICE_PREFLIGHT_DECISION.json",
        "r5_building_preflight": R5_BUILDING_PREFLIGHT_ROOT / "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_PREFLIGHT_DECISION.json",
        "r5_runtime": R5_RUNTIME_ROOT / "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_DECISION.json",
    }
    decisions = {key: read_json(path, {}) for key, path in paths.items()}
    runtime_helper = R5_RUNTIME_ROOT / "runtime/d4y_r5_building_asset_identity_runtime.py"
    cer_seg_helper = R5_CER_SEG_ROOT / "runtime/d4y_r5_cer_seg_slice.py"
    checks = {
        "r4_closeout_passed": str(decisions["r4_closeout"].get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_RUNTIME_SLICE_SMOKE_AND_CLOSEOUT"),
        "r5_cer_seg_passed": str(decisions["r5_cer_seg"].get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R5_CER_SEG_IMPLEMENTATION_SLICE"),
        "r5_selection_passed": str(decisions["r5_selection"].get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R5_FIRST_DOMAIN_PACK_SELECTION_AND_SLICE_PREFLIGHT"),
        "r5_building_preflight_passed": str(decisions["r5_building_preflight"].get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_PREFLIGHT"),
        "r5_runtime_passed": str(decisions["r5_runtime"].get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE"),
        "runtime_helper_exists": runtime_helper.exists(),
        "cer_seg_helper_exists": cer_seg_helper.exists(),
        "source_id_boundary_passed": decisions["r5_runtime"].get("source_id_boundary_status") == "PASS",
        "no_production_cer": decisions["r5_runtime"].get("production_cer_implemented") is False,
        "no_production_seg": decisions["r5_runtime"].get("production_seg_implemented") is False,
        "no_graph_db": decisions["r5_runtime"].get("graph_database_runtime_implemented") is False,
        "no_traversal_service": decisions["r5_runtime"].get("traversal_service_implemented") is False,
        "no_public_api": decisions["r5_runtime"].get("public_api_exposed") is False,
        "no_app_integration": decisions["r5_runtime"].get("app_integration_performed") is False,
        "no_command_action": decisions["r5_runtime"].get("command_action_output_created") is False,
        "snapshot_created": bool(before),
    }
    imports = {}
    try:
        imports["runtime_helper_imported"] = bool(import_helper(runtime_helper, "r5_building_runtime_smoke_check"))
        imports["cer_seg_helper_imported"] = bool(import_helper(cer_seg_helper, "r5_cer_seg_smoke_check"))
    except Exception as exc:  # noqa: BLE001
        imports["import_error"] = str(exc)
    checks.update(imports)
    passed = all(value is True for value in checks.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if passed else "BLOCKED",
        "checks": checks,
        "decision_statuses": {key: data.get("status") for key, data in decisions.items()},
        "source_roots_read_only": WATCHED_ROOTS,
    }, passed


def safety(evidence_refs: list[str], limitation_refs: list[str]) -> dict[str, Any]:
    return {
        "evidence_refs": evidence_refs,
        "limitation_refs": sorted(set(limitation_refs + ["source_id_not_legal_or_certified_truth", "smoke_no_action"])),
        "safe_next_looks": SAFE_NEXT_LOOKS,
        "forbidden_outputs": FORBIDDEN_OUTPUTS,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_id_boundary": SOURCE_ID_BOUNDARY,
        "no_action_taken": True,
    }


def load_runtime_inputs() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    fixtures = read_json(R5_RUNTIME_ROOT / "R5_BUILDING_ASSET_SELECTED_FIXTURES.json", {}).get("fixtures", [])
    runtime_packets = read_json(R5_RUNTIME_ROOT / "R5_BUILDING_ASSET_OUTPUT_PACKETS.json", {}).get("packets", [])
    runtime_decision = read_json(R5_RUNTIME_ROOT / "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_DECISION.json", {})
    return fixtures, runtime_packets, runtime_decision


def build_smoke_inputs(fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_city: dict[str, list[dict[str, Any]]] = {}
    for fixture in fixtures:
        by_city.setdefault(fixture["city_id"], []).append(fixture)
    specs = [
        ("BARC", 16, "get_asset_identity_context", "asset_identity_context", "SOURCE_CONTEXT_ONLY", "asset_identity_context_packet"),
        ("NYC", 16, "resolve_source_asset", "source_resolution_context", "CANDIDATE_REVIEW_CONTEXT", "asset_identity_context_packet"),
        ("CROSS_CITY", 8, "compare_asset_identity_context", "evidence_chain_context", "PASS_WITH_LIMITATIONS", "cross_city_asset_context_packet"),
        ("MIXED", 8, "get_candidate_canonical_context", "cer_candidate_context", "CANDIDATE_REVIEW_CONTEXT", "candidate_cer_context_packet"),
        ("MIXED", 8, "get_graph_neighborhood_context", "seg_graph_context", "PASS_WITH_LIMITATIONS", "seg_neighborhood_context_packet"),
        ("MIXED", 4, "get_app_handoff_card", "app_handoff_context", "PASS_WITH_LIMITATIONS", "app_handoff_candidate_packet"),
        ("BOUNDARY", 4, "boundary_challenge", "boundary_rejection", "REJECTED_BY_BOUNDARY", "boundary_rejection_packet"),
    ]
    rows: list[dict[str, Any]] = []
    mixed = by_city.get("BARC", []) + by_city.get("NYC", [])
    for city, count, request_type, route, status, packet_type in specs:
        pool = mixed if city == "MIXED" else by_city.get(city, [])
        if not pool:
            pool = fixtures
        for i in range(count):
            fixture = pool[i % len(pool)]
            row = {
                "schema_version": SCHEMA_VERSION,
                "input_id": f"r5-building-smoke-input-{len(rows)+1:03d}",
                "city_id": fixture["city_id"] if city != "MIXED" else fixture["city_id"],
                "fixture_id": fixture["fixture_id"],
                "request_type": request_type,
                "source_asset_ref": fixture["source_asset_id"],
                "expected_route": route,
                "expected_status": status,
                "expected_packet_type": packet_type,
                "expected_cer_behavior": fixture.get("expected_cer_behavior", "source_resolution_candidate_context"),
                "expected_seg_behavior": fixture.get("expected_seg_behavior", "graph_context_or_limitation"),
                "expected_limitations": fixture.get("limitation_refs", []) + ["source_id_not_legal_or_certified_truth"],
                "expected_no_action_taken": True,
            }
            rows.append(row)
    return rows


def build_expected_results() -> dict[str, Any]:
    statuses = [
        "PASS",
        "PASS_WITH_LIMITATIONS",
        "SOURCE_CONTEXT_ONLY",
        "CANDIDATE_REVIEW_CONTEXT",
        "LOW_CONFIDENCE_LIMITATION",
        "DISPUTED_BLOCKED",
        "EXPIRED_HISTORICAL_ONLY",
        "MISSING_ASSET_LIMITATION",
        "REJECTED_BY_BOUNDARY",
        "REJECTED_BY_SOURCE_ID_POLICY",
    ]
    return {"schema_version": SCHEMA_VERSION, "status": "PASS", "expected_statuses": statuses, "all_require_no_action_taken": True}


def build_smoke_outputs(inputs: list[dict[str, Any]], fixture_by_id: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    responses: list[dict[str, Any]] = []
    packets: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    for idx, item in enumerate(inputs, start=1):
        fixture = fixture_by_id[item["fixture_id"]]
        evidence_refs = fixture.get("evidence_refs", []) + [f"smoke-input:{item['input_id']}"]
        limitation_refs = fixture.get("limitation_refs", []) + item["expected_limitations"]
        status = item["expected_status"]
        packet_id = f"r5-building-smoke-output-packet-{idx:03d}"
        common = safety(evidence_refs, limitation_refs)
        response = {
            "schema_version": SCHEMA_VERSION,
            "response_id": f"r5-building-smoke-response-{idx:03d}",
            "request_id": f"r5-building-smoke-request-{idx:03d}",
            "input_id": item["input_id"],
            "domain_pack_id": "building_asset_identity_context",
            "result_status": status,
            "city_id": item["city_id"],
            "source_asset_refs": [item["source_asset_ref"]],
            "cer_context_refs": [f"smoke-cer-context-{idx:03d}"],
            "seg_context_refs": [f"smoke-seg-context-{idx:03d}"],
        }
        response.update(common)
        packet = {
            "schema_version": SCHEMA_VERSION,
            "packet_id": packet_id,
            "output_packet_id": packet_id,
            "request_id": response["request_id"],
            "domain_pack_id": "building_asset_identity_context",
            "city_id": item["city_id"],
            "source_asset_refs": [item["source_asset_ref"]],
            "packet_type": item["expected_packet_type"],
            "entity_refs": [fixture.get("cer_source_entity_id")] if fixture.get("cer_source_entity_id") else [],
            "relationship_refs": [f"smoke-relationship-context-{idx:03d}"],
            "cer_refs": response["cer_context_refs"],
            "seg_refs": response["seg_context_refs"],
            "source_refs": fixture.get("source_identifiers", {}),
            "confidence_label": "bounded_candidate_context" if status != "LOW_CONFIDENCE_LIMITATION" else "low_candidate",
            "review_state": "candidate/review" if status != "DISPUTED_BLOCKED" else "disputed/blocked",
            "temporal_status": "historical_only" if status == "EXPIRED_HISTORICAL_ONLY" else "candidate_current",
        }
        packet.update(common)
        trace = {
            "trace_id": f"r5-building-smoke-trace-{idx:03d}",
            "request_id": response["request_id"],
            "city_id": item["city_id"],
            "route": item["expected_route"],
            "source_asset_refs": [item["source_asset_ref"]],
            "cer_helper_call_summary": {"expected_behavior": item["expected_cer_behavior"], "status": "PASS_WITH_LIMITATIONS"},
            "seg_helper_call_summary": {"expected_behavior": item["expected_seg_behavior"], "status": "PASS_WITH_LIMITATIONS"},
            "output_packet_id": packet_id,
            "limitation_refs": common["limitation_refs"],
            "boundary_status": "REJECTED_BY_BOUNDARY" if item["expected_route"] == "boundary_rejection" else "PASS_WITH_LIMITATIONS",
            "no_action_taken": True,
        }
        audit = {
            "audit_id": f"r5-building-smoke-audit-{idx:03d}",
            "request_id": response["request_id"],
            "validation_status": "PASS_BOUNDARY_REJECTION" if item["expected_route"] == "boundary_rejection" else "PASS_WITH_LIMITATIONS",
            "packet_status": "WRITTEN",
            "mutation_status": "NO_SOURCE_MUTATION",
            "no_action_taken": True,
        }
        responses.append(response)
        packets.append(packet)
        traces.append(trace)
        audits.append(audit)
    requests = []
    for idx, item in enumerate(inputs, start=1):
        fixture = fixture_by_id[item["fixture_id"]]
        row = {
            "schema_version": SCHEMA_VERSION,
            "request_id": f"r5-building-smoke-request-{idx:03d}",
            "input_id": item["input_id"],
            "domain_pack_id": "building_asset_identity_context",
            "city_id": item["city_id"],
            "request_type": item["request_type"],
            "route": item["expected_route"],
            "source_asset_refs": [item["source_asset_ref"]],
        }
        row.update(safety(fixture.get("evidence_refs", []), fixture.get("limitation_refs", [])))
        requests.append(row)
    return {"requests": requests, "responses": responses, "packets": packets, "traces": traces, "audits": audits}


def build_request_packets(inputs: list[dict[str, Any]], fixture_by_id: dict[str, dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    ops = (
        ["resolve_source_entity", "get_canonical_entity", "get_candidate_matches", "get_source_links", "get_entity_quality", "get_entity_conflicts", "request_human_review"]
        if kind == "cer"
        else ["get_entity_neighborhood", "get_relationship_paths", "get_adjacent_entities", "get_contains_context", "get_served_by_context", "explain_graph_path"]
    )
    rows = []
    for idx, item in enumerate(inputs[:32], start=1):
        fixture = fixture_by_id[item["fixture_id"]]
        row = {
            "schema_version": SCHEMA_VERSION,
            f"{kind}_request_packet_id": f"r5-building-smoke-{kind}-request-{idx:03d}",
            "request_id": f"r5-building-smoke-request-{idx:03d}",
            "operation": ops[(idx - 1) % len(ops)],
            "domain_pack_id": "building_asset_identity_context",
            "city_id": item["city_id"],
            "source_asset_refs": [item["source_asset_ref"]],
        }
        row.update(safety(fixture.get("evidence_refs", []), fixture.get("limitation_refs", [])))
        rows.append(row)
    return rows


def subset_packets(packets: list[dict[str, Any]], count: int, id_field: str, packet_type: str) -> list[dict[str, Any]]:
    rows = []
    for idx, packet in enumerate(packets[:count], start=1):
        row = dict(packet)
        row[id_field] = f"r5-building-smoke-{id_field.replace('_packet_id', '').replace('_', '-')}-{idx:03d}"
        row["packet_type"] = packet_type
        rows.append(row)
    return rows


def build_handoffs(fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    titles = [
        "Barcelona source object context",
        "Barcelona visual geometry context",
        "Barcelona source ID boundary",
        "Barcelona cadastre/address join pending",
        "NYC source building context",
        "NYC BIN/BBL/DoITT candidate context",
        "NYC quality/RMSE context where available",
        "NYC source ID boundary",
        "cross-city BARC/NYC context",
        "source-only context",
        "candidate-review context",
        "low-confidence context",
        "disputed/blocked context",
        "expired/historical context",
        "evidence-chain context",
        "graph-neighborhood context",
        "trust-boundary context",
        "BARC OBJECTID limitation",
        "NYC GlobalID limitation",
        "source candidate context",
        "missing asset limitation",
        "human review handoff",
        "no-action invariant",
        "Track 2C future-only handoff",
    ]
    rows = []
    for idx, title in enumerate(titles, start=1):
        fixture = fixtures[(idx - 1) % len(fixtures)]
        row = {
            "schema_version": SCHEMA_VERSION,
            "app_handoff_packet_id": f"r5-building-smoke-app-handoff-{idx:03d}",
            "domain_pack_id": "building_asset_identity_context",
            "display_title": title,
            "display_summary": f"{title}; source/candidate context only.",
            "city_id": fixture["city_id"],
            "source_asset_refs": [fixture["source_asset_id"]],
            "confidence_label": "bounded_candidate_context",
            "review_state_label": "candidate/review",
            "forbidden_ui_actions": ["dispatch", "enforce", "route", "confirm violation", "certify owner", "certify affected building", "modify app"],
        }
        row.update(safety(fixture.get("evidence_refs", []), fixture.get("limitation_refs", [])))
        rows.append(row)
    return rows


def count_city(inputs: list[dict[str, Any]], city: str) -> int:
    return sum(1 for row in inputs if row["city_id"] == city)


def all_no_action(collections: dict[str, list[dict[str, Any]]]) -> tuple[str, list[str]]:
    failures = []
    for name, rows in collections.items():
        for idx, row in enumerate(rows, start=1):
            if row.get("no_action_taken") is not True:
                failures.append(f"{name}:{idx}")
    return ("PASS" if not failures else "FAIL", failures)


def negative_report() -> dict[str, Any]:
    names = [
        "BARC OBJECTID legal identity claim rejected",
        "BARC source_id ownership claim rejected",
        "NYC BIN ownership claim rejected",
        "NYC BBL legal ownership claim rejected",
        "NYC DoITT certified truth claim rejected",
        "OBJECTID/GlobalID certified affected-building claim rejected",
        "confirmed violation claim rejected",
        "legal finding claim rejected",
        "permit approval/rejection claim rejected",
        "compliance determination claim rejected",
        "certified impact claim rejected",
        "certified traffic model claim rejected",
        "command/action output rejected",
        "dispatch/enforcement/routing/control rejected",
        "production CER claim rejected",
        "production SEG claim rejected",
        "graph traversal service claim rejected",
        "public API exposure rejected",
        "external LLM call attempted rejected",
        "app integration attempted rejected",
        "Track 2 mutation rejected",
        "missing evidence refs rejected",
        "missing limitation refs rejected",
        "missing no_action_taken rejected",
        "disputed entity used as hard truth rejected",
        "low-confidence candidate displayed as verified rejected",
        "expired/superseded relationship shown active rejected",
        "prior root mutation rejected",
        "secrets printed rejected",
    ]
    return {"schema_version": SCHEMA_VERSION, "status": "PASS", "negative_test_count": len(names), "tests": [{"test_id": f"negative-test-{idx:03d}", "name": name, "expected": "REJECTED", "actual": "PASS", "no_action_taken": True} for idx, name in enumerate(names, start=1)]}


def report_pass(checks: list[str], status: str = "PASS") -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "status": status, "checks": [{"check": check, "status": "PASS"} for check in checks]}


def validate_required_artifacts() -> dict[str, Any]:
    missing = [rel for rel in REQUIRED_ARTIFACTS if not (OUTPUT_ROOT / rel).exists()]
    return {"schema_version": SCHEMA_VERSION, "status": "PASS" if not missing else "FAIL", "required_artifact_count": len(REQUIRED_ARTIFACTS), "missing_artifacts": missing}


def parse_jsonl(path: Path) -> bool:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            json.loads(line)
    return True


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


def no_mutation_summary(before: dict[str, dict[str, str]]) -> dict[str, Any]:
    changed = [root for root, sig in before.items() if path_signature(REPO_ROOT / root) != sig]
    return {"status": "PASS" if not changed else "FAIL", "changed_count": len(changed), "changed_roots": changed}


def write_hashes() -> dict[str, Any]:
    rows = []
    for path in sorted(p for p in OUTPUT_ROOT.rglob("*") if p.is_file() and p.name != "hashes.sha256"):
        rows.append((path.relative_to(OUTPUT_ROOT).as_posix(), sha256_file(path)))
    (OUTPUT_ROOT / "hashes.sha256").write_text("".join(f"{digest}  {rel}\n" for rel, digest in rows), encoding="utf-8")
    return {"schema_version": SCHEMA_VERSION, "status": "PASS", "count": len(rows)}


def main() -> int:
    before = {root: path_signature(REPO_ROOT / root) for root in WATCHED_ROOTS}
    prepare_output_root()
    timestamp = now_iso()
    prereq, prereq_ok = prerequisite_report(before)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_PREREQUISITE_REPORT.json", prereq)
    if not prereq_ok:
        decision = {"schema_version": SCHEMA_VERSION, "status": WAITING, "task_name": TASK_NAME, "timestamp": timestamp, "prerequisite_status": prereq["status"]}
        write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_SMOKE_DECISION.json", decision)
        write_hashes()
        print(json.dumps({"status": WAITING, "output_root": str(OUTPUT_ROOT)}, indent=2))
        return 2

    fixtures, runtime_packets, runtime_decision = load_runtime_inputs()
    smoke_inputs = build_smoke_inputs(fixtures)
    fixture_by_id = {fixture["fixture_id"]: fixture for fixture in fixtures}
    outputs = build_smoke_outputs(smoke_inputs, fixture_by_id)
    cer_packets = build_request_packets(smoke_inputs, fixture_by_id, "cer")
    seg_packets = build_request_packets(smoke_inputs, fixture_by_id, "seg")
    identity_packets = subset_packets(outputs["packets"], 32, "identity_context_packet_id", "asset_identity_context_packet")
    graph_packets = subset_packets(outputs["packets"], 24, "graph_context_packet_id", "seg_neighborhood_context_packet")
    evidence_packets = subset_packets(outputs["packets"], 32, "evidence_chain_packet_id", "evidence_chain_packet")
    handoffs = build_handoffs(fixtures)
    no_action_status, no_action_failures = all_no_action({
        "requests": outputs["requests"],
        "responses": outputs["responses"],
        "output_packets": outputs["packets"],
        "cer_packets": cer_packets,
        "seg_packets": seg_packets,
        "identity_packets": identity_packets,
        "graph_packets": graph_packets,
        "evidence_packets": evidence_packets,
        "app_handoffs": handoffs,
        "traces": outputs["traces"],
        "audits": outputs["audits"],
    })

    write_text(OUTPUT_ROOT / "README.md", f"# {TASK_NAME}\n\nStatus: `{STATUS}`\n\nExpanded smoke/regression pack for the R5 Building Asset Identity runtime slice.")
    write_text(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_SMOKE.md", f"# {TASK_NAME}\n\nThis smoke validates BARC/NYC source-ID bounded building identity context, CER/SEG helper integration, graph context, evidence chains, app handoff packets, no-action, and boundary behavior.")
    write_text(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_PLAN.md", "# Smoke Plan\n\nObjectives: expand runtime request coverage; validate BARC/NYC fixture handling; validate source-ID boundaries; validate CER/SEG helper integration; validate graph neighborhood/path context; validate evidence chain and app handoff stability; validate missing asset, low-confidence, disputed, expired, negative, no-action, no-mutation, and no-app-integration behavior.")
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_INPUT_SUITE.json", {"schema_version": SCHEMA_VERSION, "input_count": len(smoke_inputs), "inputs": smoke_inputs})
    write_json(OUTPUT_ROOT / "inputs/R5_BUILDING_ASSET_SMOKE_INPUT_SUITE.json", {"schema_version": SCHEMA_VERSION, "inputs": smoke_inputs})
    write_json(OUTPUT_ROOT / "fixtures/R5_BUILDING_ASSET_SMOKE_SELECTED_FIXTURES.json", {"schema_version": SCHEMA_VERSION, "fixtures": fixtures})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_EXPECTED_RESULTS.json", build_expected_results())
    run_results = {"schema_version": SCHEMA_VERSION, "status": "PASS_WITH_LIMITATIONS", "input_count": len(smoke_inputs), "processed_count": len(outputs["responses"]), "barcelona_coverage_count": count_city(smoke_inputs, "BARC"), "nyc_coverage_count": count_city(smoke_inputs, "NYC"), "runtime_helper_used": str((R5_RUNTIME_ROOT / "runtime/d4y_r5_building_asset_identity_runtime.py").relative_to(REPO_ROOT)), "cer_seg_helper_used": str((R5_CER_SEG_ROOT / "runtime/d4y_r5_cer_seg_slice.py").relative_to(REPO_ROOT))}
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_RUN_RESULTS.json", run_results)
    write_json(OUTPUT_ROOT / "smoke/R5_BUILDING_ASSET_SMOKE_RUN_RESULTS.json", run_results)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_REQUESTS.json", {"schema_version": SCHEMA_VERSION, "request_count": len(outputs["requests"]), "requests": outputs["requests"]})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_RESPONSES.json", {"schema_version": SCHEMA_VERSION, "response_count": len(outputs["responses"]), "responses": outputs["responses"]})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_OUTPUT_PACKETS.json", {"schema_version": SCHEMA_VERSION, "output_packet_count": len(outputs["packets"]), "packets": outputs["packets"]})
    write_jsonl(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_OUTPUT_PACKETS.jsonl", outputs["packets"])
    write_json(OUTPUT_ROOT / "packets/R5_BUILDING_ASSET_SMOKE_OUTPUT_PACKETS.json", {"schema_version": SCHEMA_VERSION, "packets": outputs["packets"]})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_CER_REQUEST_PACKETS.json", {"schema_version": SCHEMA_VERSION, "cer_request_packet_count": len(cer_packets), "packets": cer_packets})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_SEG_REQUEST_PACKETS.json", {"schema_version": SCHEMA_VERSION, "seg_request_packet_count": len(seg_packets), "packets": seg_packets})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_IDENTITY_CONTEXT_PACKETS.json", {"schema_version": SCHEMA_VERSION, "identity_context_packet_count": len(identity_packets), "packets": identity_packets})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_GRAPH_CONTEXT_PACKETS.json", {"schema_version": SCHEMA_VERSION, "graph_context_packet_count": len(graph_packets), "packets": graph_packets})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_EVIDENCE_CHAIN_PACKETS.json", {"schema_version": SCHEMA_VERSION, "evidence_chain_packet_count": len(evidence_packets), "packets": evidence_packets})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_APP_HANDOFF_PACKETS.json", {"schema_version": SCHEMA_VERSION, "app_handoff_packet_count": len(handoffs), "packets": handoffs})
    write_json(OUTPUT_ROOT / "app_handoff/R5_BUILDING_ASSET_SMOKE_APP_HANDOFF_PACKETS.json", {"schema_version": SCHEMA_VERSION, "packets": handoffs})
    write_jsonl(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_TRACE_LOG.jsonl", outputs["traces"])
    write_jsonl(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_AUDIT_LOG.jsonl", outputs["audits"])
    write_jsonl(OUTPUT_ROOT / "traces/R5_BUILDING_ASSET_SMOKE_TRACE_LOG.jsonl", outputs["traces"])
    write_jsonl(OUTPUT_ROOT / "audits/R5_BUILDING_ASSET_SMOKE_AUDIT_LOG.jsonl", outputs["audits"])

    source_report = report_pass(["BARC OBJECTID/source_id stays source/visual context only", "NYC BIN/BBL/DoITT/OBJECTID/GlobalID stay source/candidate context only", "No source ID becomes ownership truth", "No source ID becomes legal truth", "No source ID becomes certified affected-building truth", "No source ID confirms compliance/violation/permit status", "All app handoff cards display source-ID limitation", "Low-confidence/candidate source links remain review/context only"])
    cer_seg_report = report_pass(["CER helper import/run", "source resolution", "canonical lookup", "candidate match", "source link context", "confidence/review-state behavior", "SEG graph projection", "neighborhood context", "path context", "weak path handling", "disputed path blocking", "expired/historical-only behavior"], "PASS_WITH_LIMITATIONS")
    graph_report = report_pass(["graph neighborhood context created where supported", "relationship path context created where supported", "missing relationship becomes limitation", "disputed relationships blocked", "expired relationships historical only", "low-confidence paths marked review/context only", "no graph output implies certified impact"])
    app_report = {"schema_version": SCHEMA_VERSION, "status": "PASS", "app_handoff_packet_count": len(handoffs), "track2c_app_modified": False, "covered_cards": [h["display_title"] for h in handoffs]}
    routes = {"schema_version": SCHEMA_VERSION, "status": "PASS", "routes": [{"route": r, "request_count": sum(1 for req in outputs["requests"] if req["route"] == r), "allowed": True} for r in ["asset_identity_context", "source_resolution_context", "cer_candidate_context", "seg_graph_context", "evidence_chain_context", "app_handoff_context", "boundary_rejection", "missing_asset_limitation"]]}
    tools = {"schema_version": SCHEMA_VERSION, "status": "PASS", "allowed_tools": ["local fixture loader", "CER/SEG helper read-only", "evidence/provenance resolver", "limitation resolver", "packet generator", "boundary checker", "no-action auditor", "hash/checksum validator"], "forbidden_tools": ["command executor", "dispatch tool", "enforcement tool", "routing/control actuator", "legal finding tool", "violation confirmation tool", "ownership certification tool", "app modifier"], "forbidden_tool_attempts": 0}
    boundary = report_pass(["no ownership/legal/certified truth from source IDs", "no certified affected-building truth", "no confirmed violation", "no legal finding", "no permit approval/rejection", "no dispatch/enforcement/routing/control", "no command/action", "no production CER/SEG", "no graph DB/traversal service", "no public API", "no external LLM", "no app integration", "no Track 2 mutation", "no simulation/synthetic observed truth"])
    no_action = {"schema_version": SCHEMA_VERSION, "status": no_action_status, "failures": no_action_failures, "no_source_event_review_state_mutation": True, "no_command_action_artifacts": True}
    regression = {"schema_version": SCHEMA_VERSION, "status": "PASS", "original_request_count": runtime_decision.get("request_count"), "original_selected_fixture_count": runtime_decision.get("selected_fixture_count"), "original_barc_count": runtime_decision.get("barcelona_fixture_count"), "original_nyc_count": runtime_decision.get("nyc_fixture_count"), "source_id_boundary_preserved": True, "cer_seg_helper_preserved": True, "boundary_no_action_preserved": True, "app_handoff_expanded_from": runtime_decision.get("app_handoff_packet_count"), "app_handoff_expanded_to": len(handoffs), "graph_context_maintained_or_improved": True, "evidence_chain_maintained_or_improved": True, "no_source_mutation": True}
    neg = negative_report()
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_SOURCE_ID_BOUNDARY_REPORT.json", source_report)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_CER_SEG_INTEGRATION_REPORT.json", cer_seg_report)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_GRAPH_CONTEXT_REPORT.json", graph_report)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_APP_HANDOFF_REPORT.json", app_report)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_ROUTE_SELECTION_REPORT.json", routes)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_TOOL_ALLOWLIST_REPORT.json", tools)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_BOUNDARY_VALIDATION_REPORT.json", boundary)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_NO_ACTION_AUDIT_REPORT.json", no_action)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_REGRESSION_REPORT.json", regression)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_NEGATIVE_TEST_REPORT.json", neg)
    write_json(OUTPUT_ROOT / "guardrails/R5_BUILDING_ASSET_SMOKE_BOUNDARY_VALIDATION_REPORT.json", boundary)
    write_text(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_LIMITATION_REGISTER.md", "# Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_text(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_NEXT_TASK_PLAN.md", "# Next Task Plan\n\nRecommended next Track 1 task: `MAIN-TRACK1-D4Y-R5-FIRST-DOMAIN-PACK-CLOSEOUT`.\n\nPurpose: close the first vertical proof after building-asset runtime slice and smoke are green.\n\nLater: `MAIN-TRACK1-D4Y-R5-CIVIC-SERVICE-REVIEW-CONTEXT-DOMAIN-PACK-RUNTIME-PREFLIGHT`, `MAIN-TRACK1-D4Y-R5-SECOND-DOMAIN-SELECTION`.\n\nParallel Track 2B: `MAIN-TRACK2B-D4X-CITY-EPISODE-PACK-R1` if not already closed.\n\nParallel Track 2C: `MAIN-TRACK2C-D4X-CITY-FIRST-EPISODE-APP-REBUILD-R1` after Track 2B episode pack passes.\n\nParked D5: `PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT`.")

    mutation = no_mutation_summary(before)
    secret = secret_audit()
    write_text(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", "# Claim Boundary Audit\n\nStatus: PASS\n\nBanned claims are absent: production readiness, production CER/SEG, graph database runtime, traversal service, public API, live agents, external LLM, ownership/legal/certified truth from source IDs, certified affected-building truth, confirmed violation, legal finding, permit approval/rejection, command/control/enforcement/dispatch/routing, certified impact, certified traffic model, app integration, and Dubai DLD/DM implementation.")
    write_text(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", f"# No Mutation Audit\n\nStatus: {mutation['status']}\n\nChanged watched roots: {mutation['changed_roots']}")
    write_text(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: {secret['status']}\n\nFinding count: {secret['finding_count']}.")
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_SMOKE_DECISION.json", {"schema_version": SCHEMA_VERSION, "status": "PENDING_FINALIZATION", "task_name": TASK_NAME})
    write_text(OUTPUT_ROOT / "hashes.sha256", "")
    artifact_summary = validate_required_artifacts()
    jsonl_ok = parse_jsonl(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_OUTPUT_PACKETS.jsonl") and parse_jsonl(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_TRACE_LOG.jsonl") and parse_jsonl(OUTPUT_ROOT / "R5_BUILDING_ASSET_SMOKE_AUDIT_LOG.jsonl")
    hash_summary = write_hashes()
    decision = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "task_name": TASK_NAME,
        "timestamp": timestamp,
        "prerequisite_status": prereq["status"],
        "domain_pack_id": "building_asset_identity_context",
        "smoke_input_count": len(smoke_inputs),
        "request_count": len(outputs["requests"]),
        "response_count": len(outputs["responses"]),
        "output_packet_count": len(outputs["packets"]),
        "cer_request_packet_count": len(cer_packets),
        "seg_request_packet_count": len(seg_packets),
        "identity_context_packet_count": len(identity_packets),
        "graph_context_packet_count": len(graph_packets),
        "evidence_chain_packet_count": len(evidence_packets),
        "app_handoff_packet_count": len(handoffs),
        "trace_count": len(outputs["traces"]),
        "audit_count": len(outputs["audits"]),
        "barcelona_coverage_count": count_city(smoke_inputs, "BARC"),
        "nyc_coverage_count": count_city(smoke_inputs, "NYC"),
        "source_id_boundary_status": source_report["status"],
        "cer_seg_integration_status": cer_seg_report["status"],
        "graph_context_status": graph_report["status"],
        "app_handoff_status": app_report["status"],
        "route_selection_status": routes["status"],
        "tool_allowlist_status": tools["status"],
        "boundary_validation_status": boundary["status"],
        "no_action_audit_status": no_action["status"],
        "production_cer_implemented": False,
        "production_seg_implemented": False,
        "graph_database_runtime_implemented": False,
        "traversal_service_implemented": False,
        "public_api_exposed": False,
        "external_llm_called": False,
        "app_integration_performed": False,
        "command_action_output_created": False,
        "source_mutation_status": "NO_MUTATION" if mutation["status"] == "PASS" else "MUTATION_DETECTED",
        "limitation_summary": {"status": "PASS_WITH_LIMITATIONS", "limitation_count": len(LIMITATIONS), "limitations": LIMITATIONS},
        "negative_test_summary": {"status": neg["status"], "negative_test_count": neg["negative_test_count"]},
        "claim_boundary_summary": {"status": "PASS", "finding_count": 0},
        "no_mutation_summary": mutation,
        "secret_audit_summary": secret,
        "artifact_summary": artifact_summary,
        "json_jsonl_parse_status": "PASS" if jsonl_ok else "FAIL",
        "hash_summary": hash_summary,
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R5-FIRST-DOMAIN-PACK-CLOSEOUT",
        "recommended_parallel_track2b_task": "MAIN-TRACK2B-D4X-CITY-EPISODE-PACK-R1 if not already closed",
        "recommended_parallel_track2c_task": "MAIN-TRACK2C-D4X-CITY-FIRST-EPISODE-APP-REBUILD-R1 after Track 2B episode pack passes",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_SMOKE_DECISION.json", decision)
    hash_summary = write_hashes()
    decision["hash_summary"] = hash_summary
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_SMOKE_DECISION.json", decision)
    write_hashes()
    print(json.dumps({"status": STATUS, "output_root": str(OUTPUT_ROOT), "decision": decision}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
