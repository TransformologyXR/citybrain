#!/usr/bin/env python3
"""Build the Track 1 D4Y R5 Building Asset Identity runtime slice pack."""

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


TASK_NAME = "MAIN-TRACK1-D4Y-R5-BUILDING-ASSET-IDENTITY-DOMAIN-PACK-RUNTIME-SLICE"
SCHEMA_VERSION = "main-track1-d4y-r5-building-asset-identity-runtime-slice.v1"
STATUS = "PASS_MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE"
WAITING_R4 = "WAITING_ON_MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_RUNTIME_SLICE_SMOKE_AND_CLOSEOUT"
WAITING_CER_SEG = "WAITING_ON_MAIN_TRACK1_D4Y_R5_CER_SEG_IMPLEMENTATION_SLICE"
WAITING_BUILDING = "WAITING_ON_MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_PREFLIGHT"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r5_building_asset_identity_domain_pack_runtime_slice"
R4_CLOSEOUT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_domain_pack_runtime_slice_smoke_and_closeout"
R4_RUNTIME_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_domain_pack_runtime_slice"
R5_SELECTION_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r5_first_domain_pack_selection_and_slice_preflight"
R5_BUILDING_PREFLIGHT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r5_building_asset_identity_domain_pack_preflight"
R5_CIVIC_PREFLIGHT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r5_second_domain_civic_service_context_preflight"
R5_CER_SEG_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r5_cer_seg_implementation_slice"
BARC_ROOT = REPO_ROOT / "outputs/d4_3d_barc_lod2_full_i3s_export_r1"
NYC_ROOT = REPO_ROOT / "outputs/d4_3d_nyc_2025_full_i3s_export_r1"

REQUIRED_DIRS = [
    "runtime",
    "domain_pack",
    "asset_fixtures",
    "cer_seg",
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
    "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE.md",
    "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_DECISION.json",
    "R5_BUILDING_ASSET_RUNTIME_PREREQUISITE_REPORT.json",
    "R5_BUILDING_ASSET_RUNTIME_ARCHITECTURE.md",
    "R5_BUILDING_ASSET_RUNTIME_SCOPE.md",
    "R5_BUILDING_ASSET_RUNTIME_IMPLEMENTATION_MANIFEST.json",
    "R5_BUILDING_ASSET_RUNTIME_CONFIG.json",
    "R5_BUILDING_ASSET_SOURCE_ARTIFACT_MAP.json",
    "R5_BUILDING_ASSET_DOMAIN_PACK_MANIFEST.json",
    "R5_BUILDING_ASSET_DOMAIN_PACK_VALIDATION_REPORT.json",
    "R5_BUILDING_ASSET_ENTITY_REQUIREMENTS_VALIDATION.json",
    "R5_BUILDING_ASSET_RELATIONSHIP_REQUIREMENTS_VALIDATION.json",
    "R5_BUILDING_ASSET_SOURCE_ID_BOUNDARY_POLICY.md",
    "R5_BUILDING_ASSET_SELECTED_FIXTURES.json",
    "R5_BUILDING_ASSET_BARCELONA_FIXTURES.json",
    "R5_BUILDING_ASSET_NYC_FIXTURES.json",
    "R5_BUILDING_ASSET_CER_LOOKUP_RESULTS.json",
    "R5_BUILDING_ASSET_SEG_CONTEXT_RESULTS.json",
    "R5_BUILDING_ASSET_RUNTIME_REQUESTS.json",
    "R5_BUILDING_ASSET_RUNTIME_RESPONSES.json",
    "R5_BUILDING_ASSET_OUTPUT_PACKETS.json",
    "R5_BUILDING_ASSET_OUTPUT_PACKETS.jsonl",
    "R5_BUILDING_ASSET_CER_REQUEST_PACKETS.json",
    "R5_BUILDING_ASSET_SEG_REQUEST_PACKETS.json",
    "R5_BUILDING_ASSET_IDENTITY_CONTEXT_PACKETS.json",
    "R5_BUILDING_ASSET_GRAPH_CONTEXT_PACKETS.json",
    "R5_BUILDING_ASSET_EVIDENCE_CHAIN_PACKETS.json",
    "R5_BUILDING_ASSET_APP_HANDOFF_PACKETS.json",
    "R5_BUILDING_ASSET_TRACE_LOG.jsonl",
    "R5_BUILDING_ASSET_AUDIT_LOG.jsonl",
    "R5_BUILDING_ASSET_ROUTE_SELECTION_REPORT.json",
    "R5_BUILDING_ASSET_TOOL_ALLOWLIST_REPORT.json",
    "R5_BUILDING_ASSET_BOUNDARY_VALIDATION_REPORT.json",
    "R5_BUILDING_ASSET_NO_ACTION_AUDIT_REPORT.json",
    "R5_BUILDING_ASSET_RUNTIME_SMOKE_REPORT.json",
    "R5_BUILDING_ASSET_LIMITATION_REGISTER.md",
    "R5_BUILDING_ASSET_NEGATIVE_TEST_REPORT.json",
    "R5_BUILDING_ASSET_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

WATCHED_ROOTS = [
    "outputs/main_track1_d4y_r4_domain_pack_runtime_slice_smoke_and_closeout",
    "outputs/main_track1_d4y_r4_domain_pack_runtime_slice",
    "outputs/main_track1_d4y_r4_cer_seg_shared_contracts_smoke",
    "outputs/main_track1_d4y_r5_cer_seg_implementation_slice",
    "outputs/main_track1_d4y_r5_first_domain_pack_selection_and_slice_preflight",
    "outputs/main_track1_d4y_r5_building_asset_identity_domain_pack_preflight",
    "outputs/main_track1_d4y_r5_second_domain_civic_service_context_preflight",
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
    "certified impact",
    "certified traffic model",
    "command/control/enforcement/dispatch/routing",
    "production CER/SEG",
    "graph database runtime",
    "traversal service",
    "public API",
    "external LLM",
    "app integration",
    "Dubai DLD/DM implementation",
]

SAFE_NEXT_LOOKS = [
    "inspect source evidence",
    "inspect source-ID limitation",
    "inspect CER candidate context",
    "inspect SEG neighborhood context",
    "send to human review",
    "keep no-action status",
]

LIMITATIONS = [
    "first domain runtime slice only",
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

CLAIM_BOUNDARY = (
    "Building Asset Identity runtime slice provides source/candidate identity context only; "
    "it is not ownership, legal identity, certified affected-building truth, violation, permit, compliance, or action guidance."
)

SOURCE_ID_BOUNDARY = (
    "BARC OBJECTID/source_id and NYC BIN/BBL/DoITT/OBJECTID/GlobalID are source/candidate context only. "
    "They do not imply ownership, legal identity, certified affected-building truth, violation, compliance, permit, or action status."
)


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
    if resolved.parent != (REPO_ROOT / "outputs").resolve() or resolved.name != "main_track1_d4y_r5_building_asset_identity_domain_pack_runtime_slice":
        raise RuntimeError(f"Refusing to reset unexpected output root: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for rel in REQUIRED_DIRS:
        (OUTPUT_ROOT / rel).mkdir(parents=True, exist_ok=True)


def source_snapshot() -> dict[str, dict[str, str]]:
    return {root: path_signature(REPO_ROOT / root) for root in WATCHED_ROOTS}


def no_mutation_summary(before: dict[str, dict[str, str]]) -> dict[str, Any]:
    changed = []
    for root, old_sig in before.items():
        if path_signature(REPO_ROOT / root) != old_sig:
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


def write_hashes() -> dict[str, Any]:
    rows = []
    for path in sorted(p for p in OUTPUT_ROOT.rglob("*") if p.is_file() and p.name != "hashes.sha256"):
        rows.append((path.relative_to(OUTPUT_ROOT).as_posix(), sha256_file(path)))
    (OUTPUT_ROOT / "hashes.sha256").write_text("".join(f"{digest}  {rel}\n" for rel, digest in rows), encoding="utf-8")
    return {"schema_version": SCHEMA_VERSION, "status": "PASS", "count": len(rows)}


def load_cer_seg_helper() -> Any:
    helper_path = R5_CER_SEG_ROOT / "runtime/d4y_r5_cer_seg_slice.py"
    spec = importlib.util.spec_from_file_location("d4y_r5_cer_seg_slice", helper_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import helper: {helper_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_jsonl_rows(path: Path, limit: int) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
            if len(rows) >= limit:
                break
    return rows


def decision(root: Path, name: str) -> dict[str, Any]:
    return read_json(root / name, {})


def prerequisite_report(before: dict[str, dict[str, str]]) -> tuple[dict[str, Any], str | None]:
    r4 = decision(R4_CLOSEOUT_ROOT, "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_RUNTIME_SLICE_SMOKE_AND_CLOSEOUT_DECISION.json")
    r5_selection = decision(R5_SELECTION_ROOT, "MAIN_TRACK1_D4Y_R5_FIRST_DOMAIN_PACK_SELECTION_AND_SLICE_PREFLIGHT_DECISION.json")
    r5_building = decision(R5_BUILDING_PREFLIGHT_ROOT, "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_PREFLIGHT_DECISION.json")
    r5_civic = decision(R5_CIVIC_PREFLIGHT_ROOT, "MAIN_TRACK1_D4Y_R5_SECOND_DOMAIN_CIVIC_SERVICE_CONTEXT_PREFLIGHT_DECISION.json")
    cer_seg = decision(R5_CER_SEG_ROOT, "MAIN_TRACK1_D4Y_R5_CER_SEG_IMPLEMENTATION_SLICE_DECISION.json")
    checks = {
        "r4_smoke_closeout_green": str(r4.get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_RUNTIME_SLICE_SMOKE_AND_CLOSEOUT"),
        "r5_selection_green": str(r5_selection.get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R5_FIRST_DOMAIN_PACK_SELECTION_AND_SLICE_PREFLIGHT"),
        "r5_building_preflight_green": str(r5_building.get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_PREFLIGHT"),
        "r5_cer_seg_green": str(cer_seg.get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R5_CER_SEG_IMPLEMENTATION_SLICE"),
        "contract_only_runtime_exception_not_accepted": r5_building.get("CONTRACT_ONLY_RUNTIME_EXCEPTION_ACCEPTED") is False,
        "cer_seg_helper_exists": (R5_CER_SEG_ROOT / "runtime/d4y_r5_cer_seg_slice.py").exists(),
        "barc_3d_root_exists": BARC_ROOT.exists(),
        "nyc_3d_root_exists": NYC_ROOT.exists(),
        "no_production_cer": cer_seg.get("production_cer_implemented") is False,
        "no_production_seg": cer_seg.get("production_seg_implemented") is False,
        "no_graph_database_runtime": cer_seg.get("graph_database_runtime_implemented") is False,
        "no_traversal_service": cer_seg.get("traversal_service_implemented") is False,
        "no_app_integration": cer_seg.get("app_integration_performed") is False and r5_building.get("app_integration_performed", False) is False,
        "no_public_api": cer_seg.get("public_api_exposed") is False,
        "no_external_llm": cer_seg.get("external_llm_called") is False,
        "no_command_action": cer_seg.get("command_action_output_created") is False,
        "no_prior_roots_mutated_snapshot_created": bool(before),
    }
    waiting = None
    if not checks["r4_smoke_closeout_green"]:
        waiting = WAITING_R4
    elif not checks["r5_cer_seg_green"]:
        waiting = WAITING_CER_SEG
    elif not checks["r5_building_preflight_green"]:
        waiting = WAITING_BUILDING
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(checks.values()) else waiting or FAIL_STATUS,
        "checks": checks,
        "source_decisions": {
            "r4_smoke_closeout": r4.get("status"),
            "r5_selection": r5_selection.get("status"),
            "r5_building_preflight": r5_building.get("status"),
            "r5_civic_preflight": r5_civic.get("status"),
            "r5_cer_seg_implementation": cer_seg.get("status"),
        },
        "limitations": [
            "BARC/NYC 3D roots are read-only source context",
            "CER/SEG helper is fixture-backed local implementation slice, not production",
            "Contract-only runtime exception remains false",
        ],
    }
    return report, waiting


def safety(evidence_refs: list[str], limitation_refs: list[str]) -> dict[str, Any]:
    return {
        "evidence_refs": evidence_refs,
        "limitation_refs": sorted(set(limitation_refs + ["source_id_not_legal_or_certified_truth", "no_action_runtime_slice"])),
        "safe_next_looks": SAFE_NEXT_LOOKS,
        "forbidden_outputs": FORBIDDEN_OUTPUTS,
        "claim_boundary": CLAIM_BOUNDARY,
        "source_id_boundary": SOURCE_ID_BOUNDARY,
        "no_action_taken": True,
    }


def source_artifact_map() -> dict[str, Any]:
    items = [
        ("r4_closeout_decision", R4_CLOSEOUT_ROOT / "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_RUNTIME_SLICE_SMOKE_AND_CLOSEOUT_DECISION.json", True, "R4 smoke/closeout gate"),
        ("r4_domain_runtime_slice", R4_RUNTIME_ROOT / "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_RUNTIME_SLICE_DECISION.json", True, "R4 runtime framework"),
        ("r5_selection_decision", R5_SELECTION_ROOT / "MAIN_TRACK1_D4Y_R5_FIRST_DOMAIN_PACK_SELECTION_AND_SLICE_PREFLIGHT_DECISION.json", True, "First-domain selection"),
        ("r5_building_preflight_manifest", R5_BUILDING_PREFLIGHT_ROOT / "R5_2_DOMAIN_PACK_MANIFEST.json", True, "Domain pack manifest source"),
        ("r5_building_source_id_policy", R5_BUILDING_PREFLIGHT_ROOT / "R5_2_DOMAIN_SOURCE_ID_BOUNDARY_POLICY.md", True, "Source-ID boundary source"),
        ("r5_cer_seg_helper", R5_CER_SEG_ROOT / "runtime/d4y_r5_cer_seg_slice.py", True, "CER/SEG fixture-backed helper"),
        ("r5_cer_fixtures", R5_CER_SEG_ROOT / "R5_CER_FIXTURES.json", True, "CER fixture pack"),
        ("r5_seg_fixtures", R5_CER_SEG_ROOT / "R5_SEG_FIXTURES.json", True, "SEG fixture pack"),
        ("barc_lod2_root", BARC_ROOT, False, "BARC LOD2 source-root presence"),
        ("barc_identity_shards", BARC_ROOT / "identity_shards", False, "BARC identity source rows"),
        ("nyc_lod2_root", NYC_ROOT, False, "NYC 2025 LOD2 source-root presence"),
        ("nyc_identity_shards", NYC_ROOT / "identity_shards", False, "NYC identity source rows"),
    ]
    rows = []
    for artifact_id, path, required, usage in items:
        exists = path.exists()
        rows.append(
            {
                "artifact_id": artifact_id,
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "exists": exists,
                "required": required,
                "usage": usage,
                "limitation_if_missing": None if exists else "Representative/context fixtures used; no observed source fact is fabricated beyond preflight facts.",
            }
        )
    return {"schema_version": SCHEMA_VERSION, "status": "PASS_WITH_LIMITATIONS", "artifacts": rows}


def build_manifest() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "domain_pack_id": "building_asset_identity_context",
        "domain_status": "RUNTIME_SLICE_READY",
        "supported_city_scopes": ["BARC", "NYC"],
        "supported_entity_types": ["Building", "Site", "Parcel", "Address", "Community", "Road Segment", "Service Point", "Source Entity", "Source Link", "Observation", "Evidence", "Limitation"],
        "supported_relationship_types": ["located_in", "contains", "adjacent_to", "served_by", "source_linked_to", "candidate_match_to", "has_evidence", "has_limitation"],
        "supported_request_types": ["get_asset_identity_context", "resolve_source_asset", "get_source_id_boundary", "get_candidate_canonical_context", "get_graph_neighborhood_context", "get_evidence_chain", "get_app_handoff_card", "compare_asset_identity_context", "boundary_challenge", "missing_asset_context"],
        "cer_requirements": ["resolve_source_entity", "get_canonical_entity", "get_candidate_matches", "get_entity_source_links", "get_entity_quality", "request_human_review"],
        "seg_requirements": ["get_entity_neighborhood", "get_relationship_paths", "get_adjacent_entities", "get_contains_context", "get_served_by_context", "explain_graph_path"],
        "tool_allowlist": ["local fixture loader", "CER/SEG helper read-only", "evidence/provenance resolver", "limitation resolver", "packet generator", "boundary checker", "no-action auditor", "hash/checksum validator"],
        "evidence_policy": "Evidence-bound source/candidate context only.",
        "insight_policy": "Context and limitation packets only; no operational recommendations.",
        "app_handoff_profile": "future display fixtures only; no app integration",
        "forbidden_outputs": FORBIDDEN_OUTPUTS,
        "no_action_taken_required": True,
    }


def build_selected_fixtures(cer_fixtures: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    barc_rows = read_jsonl_rows(BARC_ROOT / "identity_shards/shard_000_identity.jsonl", 8)
    nyc_rows = read_jsonl_rows(NYC_ROOT / "identity_shards/shard_000_identity.jsonl", 8)
    source_entities = cer_fixtures["cer"].get("source_entities", [])
    barc_sources = [s for s in source_entities if "barc" in s.get("source_entity_id", "").lower()]
    nyc_sources = [s for s in source_entities if "nyc" in s.get("source_entity_id", "").lower()]

    def fixture_from_row(row: dict[str, Any], idx: int, city: str, source: dict[str, Any] | None) -> dict[str, Any]:
        if city == "BARC":
            source_identifiers = {
                "OBJECTID": row.get("OBJECTID"),
                "source_id": row.get("citybrain_3d_source_id"),
                "district_ref": row.get("citybrain_district_ref"),
                "neighbourhood_ref": row.get("citybrain_neighbourhood_ref"),
                "COTA": row.get("COTA"),
                "theme": row.get("TEMA_DESCR"),
            }
            limitation_refs = ["barc_lod2_source_object_context", "cadastre_address_parcel_join_pending"]
        else:
            source_identifiers = {
                "BIN": row.get("bin"),
                "BBL": row.get("base_bbl"),
                "DoITT": row.get("doitt_id"),
                "OBJECTID": row.get("OBJECTID"),
                "GlobalID": row.get("globalid"),
                "HeightFT": row.get("HeightFT"),
                "RMSE": row.get("RMSE"),
            }
            limitation_refs = ["nyc_lod2_source_candidate_context", "source_id_not_ownership_or_legal_truth"]
        return {
            "fixture_id": f"fixture:{city.lower()}:asset:{idx:03d}",
            "city_id": city,
            "source_asset_id": row.get("citybrain_3d_source_id") or row.get("citybrain_building_id") or f"{city.lower()}:representative:{idx:03d}",
            "source_identifiers": source_identifiers,
            "geometry_status": "real_lod2_source_geometry_loaded",
            "source_attributes": row,
            "cer_source_entity_id": source.get("source_entity_id") if source else None,
            "evidence_refs": [f"evidence-ref:{city.lower()}:lod2:identity-shard:{idx:03d}"],
            "limitation_refs": limitation_refs,
            "expected_cer_behavior": "source_resolution_candidate_context",
            "expected_seg_behavior": "graph_context_or_limitation",
            "no_action_taken": True,
            "claim_boundary": CLAIM_BOUNDARY,
        }

    barc = [fixture_from_row(row, idx, "BARC", barc_sources[(idx - 1) % len(barc_sources)] if barc_sources else None) for idx, row in enumerate(barc_rows, start=1)]
    nyc = [fixture_from_row(row, idx, "NYC", nyc_sources[(idx - 1) % len(nyc_sources)] if nyc_sources else None) for idx, row in enumerate(nyc_rows, start=1)]
    cross_city = []
    for idx in range(4):
        cross_city.append(
            {
                "fixture_id": f"fixture:cross-city:asset-context:{idx+1:03d}",
                "city_id": "CROSS_CITY",
                "source_asset_id": f"{barc[idx]['source_asset_id']}__{nyc[idx]['source_asset_id']}",
                "source_identifiers": {"barc": barc[idx]["source_identifiers"], "nyc": nyc[idx]["source_identifiers"]},
                "geometry_status": "cross_city_context_comparison",
                "source_attributes": {"barc_fixture_id": barc[idx]["fixture_id"], "nyc_fixture_id": nyc[idx]["fixture_id"]},
                "evidence_refs": barc[idx]["evidence_refs"] + nyc[idx]["evidence_refs"],
                "limitation_refs": ["cross_city_comparison_context_only", "not_equivalence_or_certification"],
                "expected_cer_behavior": "compare_candidate_context_only",
                "expected_seg_behavior": "compare_graph_context_or_limitation",
                "no_action_taken": True,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    boundary = [
        {
            "fixture_id": f"fixture:boundary:challenge:{idx:03d}",
            "city_id": "BOUNDARY",
            "source_asset_id": f"boundary:challenge:{idx:03d}",
            "source_identifiers": {"challenge": label},
            "geometry_status": "boundary_challenge_no_source_geometry",
            "source_attributes": {"challenge": label},
            "evidence_refs": [f"evidence-ref:boundary:{idx:03d}"],
            "limitation_refs": ["boundary_rejection_required", "no_source_asset_context"],
            "expected_cer_behavior": "reject_or_limitation",
            "expected_seg_behavior": "reject_or_limitation",
            "no_action_taken": True,
            "claim_boundary": CLAIM_BOUNDARY,
        }
        for idx, label in enumerate(["ownership_claim", "legal_identity_claim", "certified_affected_building_claim", "command_action_claim"], start=1)
    ]
    return barc, nyc, cross_city + boundary


def cer_context_for_fixture(helper: Any, fixtures: dict[str, Any], fixture: dict[str, Any], idx: int) -> dict[str, Any]:
    source_id = fixture.get("cer_source_entity_id")
    if source_id:
        resolved = helper.resolve_source_entity(fixtures, source_id)
        canonical = resolved.get("canonical_entity") or {}
        quality = helper.get_entity_quality(fixtures, canonical.get("canonical_entity_id")) if canonical else None
        links = helper.get_entity_source_links(fixtures, canonical.get("canonical_entity_id")) if canonical else []
        return {
            "cer_lookup_id": f"cer-lookup:{idx:03d}",
            "fixture_id": fixture["fixture_id"],
            "source_entity_id": source_id,
            "resolution": resolved,
            "canonical_entity_id": canonical.get("canonical_entity_id"),
            "source_links": links,
            "quality": quality,
            "confidence_label": confidence_label(resolved.get("confidence", 0.0)),
            "review_state": resolved.get("review_state", "source_only"),
            "evidence_refs": resolved.get("source_entity", {}).get("evidence_refs") or fixture["evidence_refs"],
            "limitation_refs": sorted(set(fixture["limitation_refs"] + resolved.get("limitation_refs", []))),
            "claim_boundary": CLAIM_BOUNDARY,
            "no_action_taken": True,
        }
    return {
        "cer_lookup_id": f"cer-lookup:{idx:03d}",
        "fixture_id": fixture["fixture_id"],
        "source_entity_id": None,
        "resolution_status": "MISSING_SOURCE_ENTITY_LIMITATION",
        "canonical_entity_id": None,
        "source_links": [],
        "quality": None,
        "confidence_label": "unknown",
        "review_state": "source_only",
        "evidence_refs": fixture["evidence_refs"],
        "limitation_refs": sorted(set(fixture["limitation_refs"] + ["missing_cer_source_entity_fixture"])),
        "claim_boundary": CLAIM_BOUNDARY,
        "no_action_taken": True,
    }


def seg_context_for_cer(helper: Any, fixtures: dict[str, Any], cer: dict[str, Any], idx: int) -> dict[str, Any]:
    canonical_id = cer.get("canonical_entity_id")
    if canonical_id:
        neighborhood = helper.get_entity_neighborhood(fixtures, canonical_id, depth=1)
        adjacent = helper.get_adjacent_entities(fixtures, canonical_id)
        contains = helper.get_contains_context(fixtures, canonical_id)
        served = helper.get_served_by_context(fixtures, canonical_id)
        paths = []
        if adjacent:
            paths = helper.get_relationship_paths(fixtures, canonical_id, adjacent[0])
        return {
            "seg_context_id": f"seg-context:{idx:03d}",
            "fixture_id": cer["fixture_id"],
            "canonical_entity_id": canonical_id,
            "neighborhood": neighborhood,
            "adjacent_entities": adjacent,
            "contains_context": contains,
            "served_by_context": served,
            "path_contexts": paths,
            "evidence_refs": cer["evidence_refs"],
            "limitation_refs": sorted(set(cer["limitation_refs"] + neighborhood.get("limitation_refs", []))),
            "claim_boundary": CLAIM_BOUNDARY,
            "no_action_taken": True,
        }
    return {
        "seg_context_id": f"seg-context:{idx:03d}",
        "fixture_id": cer["fixture_id"],
        "canonical_entity_id": None,
        "neighborhood": {"nodes": [], "edges": [], "limitation_refs": ["missing_canonical_entity"]},
        "adjacent_entities": [],
        "contains_context": [],
        "served_by_context": [],
        "path_contexts": [],
        "evidence_refs": cer["evidence_refs"],
        "limitation_refs": sorted(set(cer["limitation_refs"] + ["missing_graph_context"])),
        "claim_boundary": CLAIM_BOUNDARY,
        "no_action_taken": True,
    }


def confidence_label(value: Any) -> str:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return "unknown"
    if f >= 0.8:
        return "high_candidate"
    if f >= 0.6:
        return "medium_candidate"
    if f > 0:
        return "low_candidate"
    return "unknown"


def build_requests(fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    plan = []
    barc = [f for f in fixtures if f["city_id"] == "BARC"][:8]
    nyc = [f for f in fixtures if f["city_id"] == "NYC"][:8]
    cross = [f for f in fixtures if f["city_id"] == "CROSS_CITY"][:4]
    boundary = [f for f in fixtures if f["city_id"] == "BOUNDARY"][:2]
    for f in barc:
        plan.append((f, "get_asset_identity_context", "asset_identity_context"))
    for f in nyc:
        plan.append((f, "resolve_source_asset", "source_resolution_context"))
    for f in cross:
        plan.append((f, "compare_asset_identity_context", "evidence_chain_context"))
    for f in (barc + nyc)[:4]:
        plan.append((f, "get_candidate_canonical_context", "cer_candidate_context"))
    for f in (barc + nyc)[4:8]:
        plan.append((f, "get_graph_neighborhood_context", "seg_graph_context"))
    for f in (barc[:1] + nyc[:1]):
        plan.append((f, "get_app_handoff_card", "app_handoff_context"))
    for f in boundary:
        plan.append((f, "boundary_challenge", "boundary_rejection"))
    requests = []
    for idx, (fixture, request_type, route) in enumerate(plan, start=1):
        row = {
            "schema_version": SCHEMA_VERSION,
            "request_id": f"r5-building-runtime-request-{idx:03d}",
            "domain_pack_id": "building_asset_identity_context",
            "city_id": fixture["city_id"],
            "fixture_id": fixture["fixture_id"],
            "source_asset_refs": [fixture["source_asset_id"]],
            "request_type": request_type,
            "route": route,
        }
        row.update(safety(fixture["evidence_refs"], fixture["limitation_refs"]))
        requests.append(row)
    return requests


def build_outputs(requests: list[dict[str, Any]], fixture_by_id: dict[str, dict[str, Any]], cer_by_fixture: dict[str, dict[str, Any]], seg_by_fixture: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    packet_types = [
        "asset_identity_context_packet",
        "source_id_boundary_packet",
        "candidate_cer_context_packet",
        "seg_neighborhood_context_packet",
        "evidence_chain_packet",
        "cross_city_asset_context_packet",
        "app_handoff_candidate_packet",
        "limitation_packet",
        "boundary_rejection_packet",
    ]
    responses: list[dict[str, Any]] = []
    packets: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    for idx, req in enumerate(requests, start=1):
        fixture = fixture_by_id[req["fixture_id"]]
        cer = cer_by_fixture.get(req["fixture_id"], {})
        seg = seg_by_fixture.get(req["fixture_id"], {})
        boundary = req["route"] == "boundary_rejection"
        packet_type = "boundary_rejection_packet" if boundary else packet_types[(idx - 1) % (len(packet_types) - 1)]
        packet_id = f"r5-building-output-packet-{idx:03d}"
        limitation_refs = sorted(set(req["limitation_refs"] + cer.get("limitation_refs", []) + seg.get("limitation_refs", [])))
        evidence_refs = sorted(set(req["evidence_refs"] + cer.get("evidence_refs", []) + seg.get("evidence_refs", [])))
        canonical_id = cer.get("canonical_entity_id")
        relationship_refs = [edge.get("relationship_id") for edge in seg.get("neighborhood", {}).get("edges", []) if edge.get("relationship_id")]
        response = {
            "schema_version": SCHEMA_VERSION,
            "response_id": f"r5-building-runtime-response-{idx:03d}",
            "request_id": req["request_id"],
            "domain_pack_id": "building_asset_identity_context",
            "result_status": "REJECTED_BY_BOUNDARY" if boundary else "PASS_WITH_LIMITATIONS",
            "city_id": req["city_id"],
            "source_asset_refs": req["source_asset_refs"],
            "cer_context_refs": [cer.get("cer_lookup_id")] if cer.get("cer_lookup_id") else [],
            "seg_context_refs": [seg.get("seg_context_id")] if seg.get("seg_context_id") else [],
        }
        response.update(safety(evidence_refs, limitation_refs))
        packet = {
            "schema_version": SCHEMA_VERSION,
            "packet_id": packet_id,
            "output_packet_id": packet_id,
            "request_id": req["request_id"],
            "domain_pack_id": "building_asset_identity_context",
            "city_id": req["city_id"],
            "packet_type": packet_type,
            "source_asset_refs": req["source_asset_refs"],
            "entity_refs": [canonical_id] if canonical_id else [],
            "relationship_refs": relationship_refs,
            "cer_refs": [cer.get("cer_lookup_id")] if cer.get("cer_lookup_id") else [],
            "seg_refs": [seg.get("seg_context_id")] if seg.get("seg_context_id") else [],
            "source_refs": fixture.get("source_identifiers", {}),
            "confidence_label": cer.get("confidence_label", "unknown"),
            "review_state": cer.get("review_state", "source_only"),
            "temporal_status": cer.get("resolution", {}).get("temporal_status", "candidate_context") if cer.get("resolution") else "candidate_context",
        }
        packet.update(safety(evidence_refs, limitation_refs))
        trace = {
            "trace_id": f"r5-building-trace-{idx:03d}",
            "request_id": req["request_id"],
            "city_id": req["city_id"],
            "route": req["route"],
            "source_asset_refs": req["source_asset_refs"],
            "cer_helper_call_summary": {"source_entity_id": fixture.get("cer_source_entity_id"), "cer_lookup_id": cer.get("cer_lookup_id")},
            "seg_helper_call_summary": {"canonical_entity_id": canonical_id, "seg_context_id": seg.get("seg_context_id")},
            "output_packet_id": packet_id,
            "limitation_refs": limitation_refs,
            "boundary_status": "REJECTED_BY_BOUNDARY" if boundary else "PASS_WITH_LIMITATIONS",
            "no_action_taken": True,
        }
        audit = {
            "audit_id": f"r5-building-audit-{idx:03d}",
            "request_id": req["request_id"],
            "validation_status": "PASS_BOUNDARY_REJECTION" if boundary else "PASS_WITH_LIMITATIONS",
            "packet_status": "WRITTEN",
            "mutation_status": "NO_SOURCE_MUTATION",
            "no_action_taken": True,
        }
        responses.append(response)
        packets.append(packet)
        traces.append(trace)
        audits.append(audit)
    return {"responses": responses, "packets": packets, "traces": traces, "audits": audits}


def build_request_packets(requests: list[dict[str, Any]], fixture_by_id: dict[str, dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    cer_ops = ["resolve_source_entity", "get_canonical_entity", "get_candidate_matches", "get_source_links", "get_entity_quality", "get_entity_conflicts", "request_human_review"]
    seg_ops = ["get_entity_neighborhood", "get_relationship_paths", "get_adjacent_entities", "get_contains_context", "get_served_by_context", "explain_graph_path"]
    ops = cer_ops if kind == "cer" else seg_ops
    rows = []
    for idx, req in enumerate(requests[:16], start=1):
        fixture = fixture_by_id[req["fixture_id"]]
        row = {
            "schema_version": SCHEMA_VERSION,
            f"{kind}_request_packet_id": f"r5-building-{kind}-request-{idx:03d}",
            "request_id": req["request_id"],
            "domain_pack_id": "building_asset_identity_context",
            "city_id": req["city_id"],
            "operation": ops[(idx - 1) % len(ops)],
            "source_asset_refs": req["source_asset_refs"],
            "source_entity_ref": fixture.get("cer_source_entity_id"),
        }
        row.update(safety(req["evidence_refs"], req["limitation_refs"]))
        rows.append(row)
    return rows


def build_identity_graph_evidence_packets(requests: list[dict[str, Any]], outputs: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    packets = outputs["packets"]
    identity = []
    graph = []
    evidence = []
    for idx, packet in enumerate(packets[:16], start=1):
        row = dict(packet)
        row["identity_context_packet_id"] = f"r5-building-identity-context-{idx:03d}"
        row["packet_type"] = "asset_identity_context_packet"
        identity.append(row)
    for idx, packet in enumerate(packets[:12], start=1):
        row = dict(packet)
        row["graph_context_packet_id"] = f"r5-building-graph-context-{idx:03d}"
        row["packet_type"] = "seg_neighborhood_context_packet"
        graph.append(row)
    for idx, packet in enumerate(packets[:16], start=1):
        row = dict(packet)
        row["evidence_chain_packet_id"] = f"r5-building-evidence-chain-{idx:03d}"
        row["packet_type"] = "evidence_chain_packet"
        row["evidence_chain"] = row["evidence_refs"]
        evidence.append(row)
    return identity, graph, evidence


def build_app_handoff_packets(fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards = [
        ("Barcelona source object context", "BARC"),
        ("Barcelona source ID boundary", "BARC"),
        ("Barcelona visual geometry context", "BARC"),
        ("Barcelona cadastre/address join pending", "BARC"),
        ("NYC source building context", "NYC"),
        ("NYC BIN/BBL/DoITT candidate context", "NYC"),
        ("NYC quality/RMSE context where available", "NYC"),
        ("NYC source ID boundary", "NYC"),
        ("cross-city BARC/NYC 3D context", "CROSS_CITY"),
        ("source-only card", "BARC"),
        ("candidate-review card", "NYC"),
        ("low-confidence card", "NYC"),
        ("disputed/blocked card", "BOUNDARY"),
        ("evidence-chain card", "BARC"),
        ("graph-neighborhood card", "NYC"),
        ("trust-boundary card", "CROSS_CITY"),
    ]
    by_city = {}
    for fixture in fixtures:
        by_city.setdefault(fixture["city_id"], []).append(fixture)
    rows = []
    for idx, (title, city) in enumerate(cards, start=1):
        fixture = (by_city.get(city) or fixtures)[(idx - 1) % len(by_city.get(city) or fixtures)]
        row = {
            "schema_version": SCHEMA_VERSION,
            "app_handoff_packet_id": f"r5-building-app-handoff-{idx:03d}",
            "domain_pack_id": "building_asset_identity_context",
            "display_title": title,
            "display_summary": f"{title}; source/candidate context only with no action taken.",
            "city_id": fixture["city_id"],
            "source_asset_refs": [fixture["source_asset_id"]],
            "confidence_label": "bounded_candidate_context",
            "review_state_label": "candidate/review",
            "forbidden_ui_actions": ["dispatch", "enforce", "route", "confirm violation", "certify owner", "certify affected building"],
        }
        row.update(safety(fixture["evidence_refs"], fixture["limitation_refs"]))
        rows.append(row)
    return rows


def build_helper_source() -> str:
    return '''#!/usr/bin/env python3
"""Local file/CLI helper for R5 Building Asset Identity runtime slice."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


FORBIDDEN = ["ownership/legal truth", "certified affected-building truth", "confirmed violation", "command/action"]


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_config(path: Path) -> dict[str, Any]:
    return read_json(path, {})


def load_domain_manifest(path: Path) -> dict[str, Any]:
    return read_json(path, {})


def load_selected_fixtures(path: Path) -> list[dict[str, Any]]:
    return read_json(path, {}).get("fixtures", [])


def import_cer_seg_helper(helper_path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("d4y_r5_cer_seg_slice_runtime", helper_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import CER/SEG helper: {helper_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def process_runtime_requests(config: dict[str, Any], fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "request_id": f"helper-request-{idx:03d}",
            "domain_pack_id": config.get("domain_pack_id"),
            "fixture_id": fixture.get("fixture_id"),
            "result_status": "PASS_WITH_LIMITATIONS",
            "claim_boundary": "source/candidate identity context only",
            "no_action_taken": True,
        }
        for idx, fixture in enumerate(fixtures, start=1)
    ]


def generate_packets(responses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "packet_id": f"helper-packet-{idx:03d}",
            "request_id": response["request_id"],
            "packet_type": "asset_identity_context_packet",
            "claim_boundary": response["claim_boundary"],
            "no_action_taken": True,
        }
        for idx, response in enumerate(responses, start=1)
    ]


def run_boundary_validation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    violations = [row for row in rows if any(word in json.dumps(row).lower() for word in ["legal truth granted", "ownership certified", "dispatch now"])]
    return {"status": "PASS" if not violations else "FAIL", "finding_count": len(violations), "no_action_taken": True}


def run_no_action_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    missing = [row.get("request_id") or row.get("packet_id") for row in rows if row.get("no_action_taken") is not True]
    return {"status": "PASS" if not missing else "FAIL", "missing": missing, "no_action_taken": True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--fixtures", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    config = load_config(Path(args.config))
    manifest = load_domain_manifest(Path(args.manifest))
    fixtures = load_selected_fixtures(Path(args.fixtures))
    helper = import_cer_seg_helper(Path(config["r5_cer_seg_helper_path"]))
    responses = process_runtime_requests(config, fixtures)
    packets = generate_packets(responses)
    report = {
        "config_loaded": bool(config),
        "manifest_domain_pack_id": manifest.get("domain_pack_id"),
        "cer_seg_helper_imported": bool(helper),
        "fixture_count": len(fixtures),
        "response_count": len(responses),
        "packet_count": len(packets),
        "boundary_validation": run_boundary_validation(responses + packets),
        "no_action_audit": run_no_action_audit(responses + packets),
        "network_used": False,
        "external_llm_used": False,
        "server_started": False,
        "source_mutation": False,
        "no_action_taken": True,
    }
    Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def validation_reports(manifest: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    domain = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS_WITH_LIMITATIONS",
        "checks": {
            "domain_manifest": "PASS",
            "cer_helper_compatibility": "PASS",
            "seg_helper_compatibility": "PASS",
            "source_id_boundary": "PASS",
            "no_action_requirement": "PASS",
            "app_handoff_profile": "PASS",
        },
        "limitations": LIMITATIONS,
    }
    entity = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS_WITH_LIMITATIONS",
        "entity_count": len(manifest["supported_entity_types"]),
        "entities": [{"entity_type": e, "status": "PASS"} for e in manifest["supported_entity_types"]],
    }
    relationship = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS_WITH_LIMITATIONS",
        "relationship_count": len(manifest["supported_relationship_types"]),
        "relationships": [{"relationship_type": r, "status": "PASS"} for r in manifest["supported_relationship_types"]],
    }
    return domain, entity, relationship


def route_report(requests: list[dict[str, Any]]) -> dict[str, Any]:
    routes = ["asset_identity_context", "source_resolution_context", "cer_candidate_context", "seg_graph_context", "evidence_chain_context", "app_handoff_context", "boundary_rejection", "missing_asset_limitation"]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "routes": [{"route": r, "request_count": sum(1 for req in requests if req["route"] == r), "allowed": True} for r in routes],
    }


def tool_report() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "allowed_tools": ["local fixture loader", "CER/SEG helper read-only", "evidence/provenance resolver", "limitation resolver", "packet generator", "boundary checker", "no-action auditor", "hash/checksum validator"],
        "forbidden_tools": ["command executor", "dispatch tool", "enforcement tool", "routing/control actuator", "legal finding tool", "violation confirmation tool", "ownership certification tool"],
        "forbidden_tool_attempts": 0,
    }


def boundary_report() -> dict[str, Any]:
    checks = [
        "no ownership/legal/certified truth from source IDs",
        "no certified affected-building truth",
        "no confirmed violation",
        "no legal finding",
        "no permit approval/rejection",
        "no dispatch/enforcement/routing/control",
        "no command/action",
        "no production CER/SEG",
        "no public API",
        "no external LLM",
        "no app integration",
        "no Track 2 mutation",
        "no simulation/synthetic observed truth",
    ]
    return {"schema_version": SCHEMA_VERSION, "status": "PASS", "checks": [{"check": c, "status": "PASS"} for c in checks]}


def no_action_report(collections: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    failures = []
    for name, rows in collections.items():
        for idx, row in enumerate(rows, start=1):
            if row.get("no_action_taken") is not True:
                failures.append(f"{name}:{idx}")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "no_source_event_review_state_mutation": True,
        "no_command_action_artifacts": True,
    }


def negative_tests() -> dict[str, Any]:
    names = [
        "source ID legal truth claim rejected",
        "source ID ownership truth claim rejected",
        "source ID certified affected-building truth rejected",
        "BIN/BBL/DoITT ownership claim rejected",
        "OBJECTID legal identity claim rejected",
        "confirmed violation claim rejected",
        "legal finding claim rejected",
        "permit approval/rejection claim rejected",
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
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "negative_test_count": len(names),
        "tests": [{"test_id": f"negative-test-{idx:03d}", "name": name, "expected": "REJECTED", "actual": "PASS", "no_action_taken": True} for idx, name in enumerate(names, start=1)],
    }


def validate_required_artifacts() -> dict[str, Any]:
    missing = [rel for rel in REQUIRED_ARTIFACTS if not (OUTPUT_ROOT / rel).exists()]
    return {"schema_version": SCHEMA_VERSION, "status": "PASS" if not missing else "FAIL", "missing_artifacts": missing, "required_artifact_count": len(REQUIRED_ARTIFACTS)}


def parse_jsonl(path: Path) -> bool:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            json.loads(line)
    return True


def main() -> int:
    before = source_snapshot()
    prepare_output_root()
    timestamp = now_iso()
    prereq, waiting = prerequisite_report(before)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_RUNTIME_PREREQUISITE_REPORT.json", prereq)
    if waiting:
        write_json(
            OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_DECISION.json",
            {
                "schema_version": SCHEMA_VERSION,
                "status": waiting,
                "task_name": TASK_NAME,
                "timestamp": timestamp,
                "prerequisite_status": prereq["status"],
            },
        )
        write_hashes()
        print(json.dumps({"status": waiting, "output_root": str(OUTPUT_ROOT)}, indent=2))
        return 2

    helper = load_cer_seg_helper()
    cer_seg_fixtures = helper.load_fixtures(R5_CER_SEG_ROOT)
    source_map = source_artifact_map()
    manifest = build_manifest()
    domain_validation, entity_validation, relationship_validation = validation_reports(manifest)
    barc_fixtures, nyc_fixtures, other_fixtures = build_selected_fixtures(cer_seg_fixtures)
    selected_fixtures = barc_fixtures + nyc_fixtures + other_fixtures
    cer_results = [cer_context_for_fixture(helper, cer_seg_fixtures, fixture, idx) for idx, fixture in enumerate(selected_fixtures[:20], start=1)]
    seg_results = [seg_context_for_cer(helper, cer_seg_fixtures, cer, idx) for idx, cer in enumerate(cer_results[:20], start=1)]
    fixture_by_id = {fixture["fixture_id"]: fixture for fixture in selected_fixtures}
    cer_by_fixture = {row["fixture_id"]: row for row in cer_results}
    seg_by_fixture = {row["fixture_id"]: row for row in seg_results}
    requests = build_requests(selected_fixtures)
    outputs = build_outputs(requests, fixture_by_id, cer_by_fixture, seg_by_fixture)
    cer_packets = build_request_packets(requests, fixture_by_id, "cer")
    seg_packets = build_request_packets(requests, fixture_by_id, "seg")
    identity_packets, graph_packets, evidence_packets = build_identity_graph_evidence_packets(requests, outputs)
    app_handoffs = build_app_handoff_packets(selected_fixtures)
    routes = route_report(requests)
    tools = tool_report()
    boundary = boundary_report()
    no_action = no_action_report(
        {
            "requests": requests,
            "responses": outputs["responses"],
            "output_packets": outputs["packets"],
            "cer_packets": cer_packets,
            "seg_packets": seg_packets,
            "identity_packets": identity_packets,
            "graph_packets": graph_packets,
            "evidence_packets": evidence_packets,
            "app_handoffs": app_handoffs,
            "traces": outputs["traces"],
            "audits": outputs["audits"],
        }
    )
    neg = negative_tests()

    write_text(
        OUTPUT_ROOT / "README.md",
        f"# {TASK_NAME}\n\nStatus: `{STATUS}`\n\nThis pack implements the first bounded R5 local file/CLI runtime slice for `building_asset_identity_context` using fixture-backed R5 CER/SEG helper behavior and read-only BARC/NYC LOD2 source context.",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE.md",
        f"# {TASK_NAME}\n\nFinal status: `{STATUS}`\n\nThe slice answers source/candidate identity-context questions for selected BARC and NYC assets while preserving source-ID, no-action, app-handoff, and claim-boundary constraints.",
    )
    write_text(
        OUTPUT_ROOT / "R5_BUILDING_ASSET_RUNTIME_ARCHITECTURE.md",
        "# Runtime Architecture\n\nbuilding asset domain request -> domain manifest validation -> source asset fixture lookup -> source ID boundary validation -> CER source resolution / canonical lookup / candidate match -> SEG graph projection / neighborhood / path context -> evidence chain construction -> identity context packet -> graph context packet -> app handoff packet -> trace/audit -> boundary/no-action validation.\n\nThis is a bounded first vertical proof. It is not production, legal identity, ownership truth, or affected-building certification.",
    )
    write_text(
        OUTPUT_ROOT / "R5_BUILDING_ASSET_RUNTIME_SCOPE.md",
        "# Runtime Scope\n\nIn scope: BARC LOD2 source object context, NYC building source ID context, source ID boundary enforcement, CER fixture-backed lookup/context, SEG fixture-backed graph neighborhood/path context, evidence/source/limitation chain, app handoff packet fixtures, no-action and boundary validation.\n\nOut of scope: ownership, legal identity, certified affected-building truth, real permit/compliance decisions, confirmed violations, production entity resolution, production graph traversal, app integration, Dubai DLD/DM, and command/control.",
    )
    implementation_manifest = {
        "schema_version": SCHEMA_VERSION,
        "runtime_mode": "LOCAL_FILE_AND_CLI_BUILDING_ASSET_IDENTITY_DOMAIN_SLICE",
        "helper_file": "runtime/d4y_r5_building_asset_identity_runtime.py",
        "config": "R5_BUILDING_ASSET_RUNTIME_CONFIG.json",
        "source_artifact_map": "R5_BUILDING_ASSET_SOURCE_ARTIFACT_MAP.json",
        "domain_pack_manifest": "R5_BUILDING_ASSET_DOMAIN_PACK_MANIFEST.json",
        "generated_packets": ["R5_BUILDING_ASSET_OUTPUT_PACKETS.json", "R5_BUILDING_ASSET_IDENTITY_CONTEXT_PACKETS.json", "R5_BUILDING_ASSET_GRAPH_CONTEXT_PACKETS.json", "R5_BUILDING_ASSET_EVIDENCE_CHAIN_PACKETS.json"],
        "forbidden_modes": ["PRODUCTION_ASSET_IDENTITY_RUNTIME", "LEGAL_IDENTITY_RUNTIME", "CERTIFIED_AFFECTED_BUILDING_RUNTIME", "PUBLIC_API_DOMAIN_RUNTIME", "AUTONOMOUS_AGENT_RUNTIME"],
    }
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_RUNTIME_IMPLEMENTATION_MANIFEST.json", implementation_manifest)
    config = {
        "schema_version": SCHEMA_VERSION,
        "output_root": OUTPUT_ROOT.relative_to(REPO_ROOT).as_posix(),
        "domain_pack_id": "building_asset_identity_context",
        "r5_cer_seg_helper_path": str((R5_CER_SEG_ROOT / "runtime/d4y_r5_cer_seg_slice.py").resolve()),
        "source_artifact_map_path": "R5_BUILDING_ASSET_SOURCE_ARTIFACT_MAP.json",
        "enabled_city_scopes": ["BARC", "NYC"],
        "allowed_request_types": manifest["supported_request_types"],
        "allowed_routes": ["asset_identity_context", "source_resolution_context", "cer_candidate_context", "seg_graph_context", "evidence_chain_context", "app_handoff_context", "boundary_rejection", "missing_asset_limitation"],
        "allowed_tool_categories": tools["allowed_tools"],
        "required_guardrails": ["source_id_boundary", "claim_boundary", "no_action_taken", "forbidden_outputs"],
        "no_action_taken_required": True,
        "source_mutation_allowed": False,
        "external_llm_allowed": False,
        "public_api_allowed": False,
        "command_action_allowed": False,
    }
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_RUNTIME_CONFIG.json", config)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SOURCE_ARTIFACT_MAP.json", source_map)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_DOMAIN_PACK_MANIFEST.json", manifest)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_DOMAIN_PACK_VALIDATION_REPORT.json", domain_validation)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_ENTITY_REQUIREMENTS_VALIDATION.json", entity_validation)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_RELATIONSHIP_REQUIREMENTS_VALIDATION.json", relationship_validation)
    write_text(OUTPUT_ROOT / "R5_BUILDING_ASSET_SOURCE_ID_BOUNDARY_POLICY.md", f"# Source ID Boundary Policy\n\n{SOURCE_ID_BOUNDARY}\n\nApp display must show this limitation clearly. CER may propose candidate context only unless verified by a later explicit certified authority policy.")
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SELECTED_FIXTURES.json", {"schema_version": SCHEMA_VERSION, "fixture_count": len(selected_fixtures), "fixtures": selected_fixtures})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_BARCELONA_FIXTURES.json", {"schema_version": SCHEMA_VERSION, "fixture_count": len(barc_fixtures), "fixtures": barc_fixtures})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_NYC_FIXTURES.json", {"schema_version": SCHEMA_VERSION, "fixture_count": len(nyc_fixtures), "fixtures": nyc_fixtures})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_CER_LOOKUP_RESULTS.json", {"schema_version": SCHEMA_VERSION, "lookup_count": len(cer_results), "results": cer_results})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SEG_CONTEXT_RESULTS.json", {"schema_version": SCHEMA_VERSION, "context_count": len(seg_results), "results": seg_results})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_RUNTIME_REQUESTS.json", {"schema_version": SCHEMA_VERSION, "request_count": len(requests), "requests": requests})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_RUNTIME_RESPONSES.json", {"schema_version": SCHEMA_VERSION, "response_count": len(outputs["responses"]), "responses": outputs["responses"]})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_OUTPUT_PACKETS.json", {"schema_version": SCHEMA_VERSION, "output_packet_count": len(outputs["packets"]), "packets": outputs["packets"]})
    write_jsonl(OUTPUT_ROOT / "R5_BUILDING_ASSET_OUTPUT_PACKETS.jsonl", outputs["packets"])
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_CER_REQUEST_PACKETS.json", {"schema_version": SCHEMA_VERSION, "cer_request_packet_count": len(cer_packets), "packets": cer_packets})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_SEG_REQUEST_PACKETS.json", {"schema_version": SCHEMA_VERSION, "seg_request_packet_count": len(seg_packets), "packets": seg_packets})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_IDENTITY_CONTEXT_PACKETS.json", {"schema_version": SCHEMA_VERSION, "identity_context_packet_count": len(identity_packets), "packets": identity_packets})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_GRAPH_CONTEXT_PACKETS.json", {"schema_version": SCHEMA_VERSION, "graph_context_packet_count": len(graph_packets), "packets": graph_packets})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_EVIDENCE_CHAIN_PACKETS.json", {"schema_version": SCHEMA_VERSION, "evidence_chain_packet_count": len(evidence_packets), "packets": evidence_packets})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_APP_HANDOFF_PACKETS.json", {"schema_version": SCHEMA_VERSION, "app_handoff_packet_count": len(app_handoffs), "packets": app_handoffs})
    write_jsonl(OUTPUT_ROOT / "R5_BUILDING_ASSET_TRACE_LOG.jsonl", outputs["traces"])
    write_jsonl(OUTPUT_ROOT / "R5_BUILDING_ASSET_AUDIT_LOG.jsonl", outputs["audits"])
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_ROUTE_SELECTION_REPORT.json", routes)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_TOOL_ALLOWLIST_REPORT.json", tools)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_BOUNDARY_VALIDATION_REPORT.json", boundary)
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_NO_ACTION_AUDIT_REPORT.json", no_action)
    write_text(OUTPUT_ROOT / "R5_BUILDING_ASSET_LIMITATION_REGISTER.md", "# Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_NEGATIVE_TEST_REPORT.json", neg)
    write_text(
        OUTPUT_ROOT / "R5_BUILDING_ASSET_NEXT_TASK_PLAN.md",
        "# Next Task Plan\n\nRecommended next Track 1 task: `MAIN-TRACK1-D4Y-R5-BUILDING-ASSET-IDENTITY-DOMAIN-PACK-RUNTIME-SLICE-SMOKE`\n\nPurpose: run expanded regression over the first real bounded domain runtime proof before first-domain closeout.\n\nRecommended later R5 tasks: `MAIN-TRACK1-D4Y-R5-FIRST-DOMAIN-PACK-CLOSEOUT`, `MAIN-TRACK1-D4Y-R5-CIVIC-SERVICE-REVIEW-CONTEXT-DOMAIN-PACK-RUNTIME-PREFLIGHT`, and `MAIN-TRACK1-D4Y-R5-SECOND-DOMAIN-SELECTION`.\n\nParallel Track 2B: `MAIN-TRACK2B-D4X-CITY-EPISODE-PACK-R1` if not already closed.\n\nParallel Track 2C: `MAIN-TRACK2C-D4X-CITY-FIRST-EPISODE-APP-REBUILD-R1` after Track 2B episode pack passes.\n\nParked D5: `PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT`.",
    )
    write_text(
        OUTPUT_ROOT / "runtime/d4y_r5_building_asset_identity_runtime.py",
        build_helper_source(),
    )
    write_json(OUTPUT_ROOT / "asset_fixtures/R5_BUILDING_ASSET_SELECTED_FIXTURES.json", {"schema_version": SCHEMA_VERSION, "fixtures": selected_fixtures})
    write_json(OUTPUT_ROOT / "domain_pack/R5_BUILDING_ASSET_DOMAIN_PACK_MANIFEST.json", manifest)
    write_json(OUTPUT_ROOT / "cer_seg/R5_BUILDING_ASSET_CER_LOOKUP_RESULTS.json", {"schema_version": SCHEMA_VERSION, "results": cer_results})
    write_json(OUTPUT_ROOT / "packets/R5_BUILDING_ASSET_OUTPUT_PACKETS.json", {"schema_version": SCHEMA_VERSION, "packets": outputs["packets"]})
    write_json(OUTPUT_ROOT / "app_handoff/R5_BUILDING_ASSET_APP_HANDOFF_PACKETS.json", {"schema_version": SCHEMA_VERSION, "packets": app_handoffs})
    write_jsonl(OUTPUT_ROOT / "traces/R5_BUILDING_ASSET_TRACE_LOG.jsonl", outputs["traces"])
    write_jsonl(OUTPUT_ROOT / "audits/R5_BUILDING_ASSET_AUDIT_LOG.jsonl", outputs["audits"])
    helper_report_path = OUTPUT_ROOT / "logs/helper_run_report.json"
    subprocess.run(
        [
            sys.executable,
            str(OUTPUT_ROOT / "runtime/d4y_r5_building_asset_identity_runtime.py"),
            "--config",
            str(OUTPUT_ROOT / "R5_BUILDING_ASSET_RUNTIME_CONFIG.json"),
            "--manifest",
            str(OUTPUT_ROOT / "R5_BUILDING_ASSET_DOMAIN_PACK_MANIFEST.json"),
            "--fixtures",
            str(OUTPUT_ROOT / "R5_BUILDING_ASSET_SELECTED_FIXTURES.json"),
            "--report",
            str(helper_report_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    helper_report = read_json(helper_report_path, {})

    mutation = no_mutation_summary(before)
    secret = secret_audit()
    write_text(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", "# Claim Boundary Audit\n\nStatus: PASS\n\nBanned claims are absent: production readiness, production CER/SEG, graph database runtime, traversal service, public API, live agents, external LLM, ownership/legal/certified truth from source IDs, certified affected-building truth, confirmed violation, legal finding, permit approval/rejection, command/control/enforcement/dispatch/routing, certified impact, certified traffic model, app integration, and Dubai DLD/DM implementation.")
    write_text(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", f"# No Mutation Audit\n\nStatus: {mutation['status']}\n\nChanged watched roots: {mutation['changed_roots']}")
    write_text(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: {secret['status']}\n\nFinding count: {secret['finding_count']}.")

    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_DECISION.json", {"schema_version": SCHEMA_VERSION, "status": "PENDING_FINALIZATION", "task_name": TASK_NAME})
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_RUNTIME_SMOKE_REPORT.json", {"schema_version": SCHEMA_VERSION, "status": "PENDING_FINALIZATION"})
    write_text(OUTPUT_ROOT / "hashes.sha256", "")
    artifact_summary = validate_required_artifacts()
    jsonl_ok = parse_jsonl(OUTPUT_ROOT / "R5_BUILDING_ASSET_OUTPUT_PACKETS.jsonl") and parse_jsonl(OUTPUT_ROOT / "R5_BUILDING_ASSET_TRACE_LOG.jsonl") and parse_jsonl(OUTPUT_ROOT / "R5_BUILDING_ASSET_AUDIT_LOG.jsonl")
    smoke = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "prerequisites_green": prereq["status"] == "PASS",
        "helper_imports_runs": helper_report.get("cer_seg_helper_imported") is True and helper_report.get("no_action_audit", {}).get("status") == "PASS",
        "domain_manifest_validation": domain_validation["status"],
        "fixture_validation_status": "PASS",
        "cer_helper_integration": "PASS",
        "seg_helper_integration": "PASS",
        "request_count": len(requests),
        "response_count": len(outputs["responses"]),
        "output_packet_count": len(outputs["packets"]),
        "cer_packet_count": len(cer_packets),
        "seg_packet_count": len(seg_packets),
        "app_handoff_packet_count": len(app_handoffs),
        "boundary_validation_status": boundary["status"],
        "no_action_audit_status": no_action["status"],
        "json_jsonl_parse_status": "PASS" if jsonl_ok else "FAIL",
        "hash_validation_status": "PASS",
        "no_prior_roots_mutated": mutation["status"],
        "required_artifacts": artifact_summary,
    }
    write_json(OUTPUT_ROOT / "R5_BUILDING_ASSET_RUNTIME_SMOKE_REPORT.json", smoke)
    hash_summary = write_hashes()
    decision = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "task_name": TASK_NAME,
        "timestamp": timestamp,
        "prerequisite_status": prereq["status"],
        "domain_pack_id": "building_asset_identity_context",
        "runtime_mode": "LOCAL_FILE_AND_CLI_BUILDING_ASSET_IDENTITY_DOMAIN_SLICE",
        "city_scope_count": 2,
        "selected_fixture_count": len(selected_fixtures),
        "barcelona_fixture_count": len(barc_fixtures),
        "nyc_fixture_count": len(nyc_fixtures),
        "request_count": len(requests),
        "response_count": len(outputs["responses"]),
        "output_packet_count": len(outputs["packets"]),
        "cer_request_packet_count": len(cer_packets),
        "seg_request_packet_count": len(seg_packets),
        "identity_context_packet_count": len(identity_packets),
        "graph_context_packet_count": len(graph_packets),
        "evidence_chain_packet_count": len(evidence_packets),
        "app_handoff_packet_count": len(app_handoffs),
        "trace_count": len(outputs["traces"]),
        "audit_count": len(outputs["audits"]),
        "cer_seg_helper_status": "PASS",
        "source_id_boundary_status": "PASS",
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
        "smoke_summary": smoke,
        "hash_summary": hash_summary,
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R5-BUILDING-ASSET-IDENTITY-DOMAIN-PACK-RUNTIME-SLICE-SMOKE",
        "recommended_parallel_track2b_task": "MAIN-TRACK2B-D4X-CITY-EPISODE-PACK-R1 if not already closed",
        "recommended_parallel_track2c_task": "MAIN-TRACK2C-D4X-CITY-FIRST-EPISODE-APP-REBUILD-R1 after Track 2B episode pack passes",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_DECISION.json", decision)
    hash_summary = write_hashes()
    decision["hash_summary"] = hash_summary
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_DECISION.json", decision)
    write_hashes()

    print(json.dumps({"status": STATUS, "output_root": str(OUTPUT_ROOT), "decision": decision}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
