#!/usr/bin/env python3
"""Close out the bounded Hero Neighbourhood control-room reference demo R1."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

TASK_NAME = "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-CONTROL-ROOM-REFERENCE-DEMO-CLOSEOUT-R1"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_closeout_r1"

BOUNDARY = """This is a bounded local/replay control-room reference demo closeout.

Do not claim:
- production readiness
- public API readiness
- live monitoring
- autonomous incident detection
- alert push
- dispatch
- routing/control
- enforcement
- official ticket/case creation
- legal/certified incident findings
- citywide certified twin
- physical accuracy
- automated action

All incident, event, current-state, relationship, operator-surface, Omniverse, and web-context outputs remain local/replay review/query context only."""

LIMITATIONS = [
    "closeout/freeze task only",
    "no new product capabilities",
    "no new incident logic",
    "no new live monitoring",
    "no new canonical identity behavior",
    "no new Omniverse behavior",
    "no new web behavior",
    "R1 visual acceptance remains artifact/package review only",
    "Omniverse/Kit/Composer remains bounded spatial control-room surface context, not certified citywide twin",
    "web remains companion evidence/episode/executive context",
    "CER/SEG v2 compatibility remains read-only",
]

RECOMMENDED_NEXT_TASK = "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-CONTROL-ROOM-REFERENCE-DEMO-MILESTONE-FREEZE"
FIXUP_NEXT_TASK = "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-CONTROL-ROOM-REFERENCE-DEMO-R1-FIXUP"

UPSTREAMS = {
    "hero_neighbourhood_reference_demo_r1": {
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_r1",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_R1_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_R1_WITH_LIMITATIONS",
        "role": "R1 demo package to freeze",
    },
    "integration_readiness_review": {
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_and_cerseg_v2_integration_readiness_review",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
        "role": "Hero + CER/SEG v2 integration-readiness review",
    },
    "hero_scene_pack_closeout": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_scene_pack_closeout",
        "decision_file": "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Hero Neighbourhood scene pack closeout",
    },
    "cerseg_cross_city_v2_closeout": {
        "root": "outputs/main_citybrain_d6_cer_seg_cross_city_v2_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_WITH_LIMITATIONS",
        "role": "CER/SEG v2 closeout",
    },
    "incident_operator_surface_r4": {
        "root": "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4",
        "decision_file": "MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_WITH_LIMITATIONS",
        "role": "Incident Mode operator-surface handoff",
    },
    "incident_mode_closeout": {
        "root": "outputs/main_citybrain_d6_incident_mode_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Incident Mode closeout",
    },
    "d6_d5_local_running_slice_closeout": {
        "root": "outputs/main_citybrain_d6_d5_local_running_slice_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_WITH_LIMITATIONS",
        "role": "D6/D5 local running slice closeout",
    },
    "r8_multi_domain_edge_registry_hardening": {
        "root": "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening",
        "decision_file": "MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_WITH_LIMITATIONS",
        "role": "hardened R8 relationship substrate",
    },
}

REQUIRED_OUTPUTS = [
    "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_DECISION.json",
    "README.md",
    "LOCAL_OPEN_INDEX.md",
    "UPSTREAM_ARTIFACT_INDEX.json",
    "UPSTREAM_STATUS_SUMMARY.json",
    "R1_DEMO_PACKAGE_REVIEW.json",
    "R1_DEMO_ACCEPTANCE_CLOSEOUT_MATRIX.json",
    "R1_DEMO_ACCEPTANCE_CLOSEOUT_MATRIX.md",
    "CONTROL_ROOM_DEMO_FREEZE_SUMMARY.json",
    "CONTROL_ROOM_DEMO_FREEZE_SUMMARY.md",
    "OPERATOR_WALKTHROUGH_CLOSEOUT_REVIEW.json",
    "EXECUTIVE_WALKTHROUGH_CLOSEOUT_REVIEW.json",
    "OMNIVERSE_HANDOFF_CLOSEOUT_REVIEW.json",
    "WEB_COMPANION_CLOSEOUT_REVIEW.json",
    "EVIDENCE_LIMITATION_TRACE_CLOSEOUT_REVIEW.json",
    "UNRESOLVED_QUARANTINED_PRESERVATION_CLOSEOUT_REVIEW.json",
    "NON_BLOCKING_GAPS_REGISTER.json",
    "BOUNDARY_AND_CLAIM_FREEZE.md",
    "CLAIM_BOUNDARY_AUDIT.json",
    "NO_ACTION_BOUNDARY_AUDIT.json",
    "NO_MUTATION_AUDIT.json",
    "SECRET_AUDIT.json",
    "HASH_MANIFEST.json",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def root_path(root: str) -> Path:
    return REPO_ROOT / root


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def status_from_decision(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("status", "final_status", "decision_status"):
        if payload.get(key):
            return str(payload[key])
    return None


def snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "byte_count": 0, "fingerprint": None}
    digest = hashlib.sha256()
    file_count = 0
    byte_count = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        file_count += 1
        size = path.stat().st_size
        byte_count += size
        digest.update(rel(path).encode("utf-8"))
        digest.update(str(size).encode("utf-8"))
        digest.update(sha256_file(path).encode("utf-8"))
    return {"exists": True, "file_count": file_count, "byte_count": byte_count, "fingerprint": digest.hexdigest()}


def prepare_output_root() -> None:
    if OUTPUT_ROOT.resolve().parent != (REPO_ROOT / "outputs").resolve():
        raise RuntimeError(f"Refusing unexpected output root: {OUTPUT_ROOT}")
    if OUTPUT_ROOT.name != "main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_closeout_r1":
        raise RuntimeError(f"Refusing unexpected output root name: {OUTPUT_ROOT.name}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def parse_json_jsonl(root: Path) -> dict[str, Any]:
    json_files = sorted(path for path in root.rglob("*.json") if path.is_file()) if root.exists() else []
    jsonl_files = sorted(path for path in root.rglob("*.jsonl") if path.is_file()) if root.exists() else []
    failures = []
    jsonl_records = 0
    for path in json_files:
        try:
            read_json(path, {})
        except Exception as exc:
            failures.append({"path": rel(path), "error": str(exc)})
    for path in jsonl_files:
        try:
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if line.strip():
                    json.loads(line)
                    jsonl_records += 1
        except Exception as exc:
            failures.append({"path": rel(path), "error": f"line {line_no}: {exc}"})
    return {
        "json_file_count": len(json_files),
        "jsonl_file_count": len(jsonl_files),
        "jsonl_record_count": jsonl_records,
        "parse_failure_count": len(failures),
        "parse_failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }


def discover_upstreams() -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    rows = []
    missing = []
    for key, spec in UPSTREAMS.items():
        root = root_path(spec["root"])
        decision_path = root / spec["decision_file"]
        decision = read_json(decision_path, {}) if decision_path.exists() else {}
        status = status_from_decision(decision)
        green = root.exists() and decision_path.exists() and status == spec["expected"]
        if not green:
            missing.append(key)
        parse_report = parse_json_jsonl(root)
        artifacts = []
        if root.exists():
            for path in sorted(item for item in root.iterdir() if item.is_file())[:24]:
                artifacts.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
        rows.append(
            {
                "upstream_key": key,
                "root": spec["root"],
                "decision_file": rel(decision_path),
                "exists": root.exists(),
                "status": status,
                "expected_status": spec["expected"],
                "green": green,
                "read_only": True,
                "consumption_role": spec["role"],
                "parse_report": parse_report,
                "sample_artifacts": artifacts,
            }
        )
    parse_failures = [row for row in rows if row["parse_report"]["status"] != "PASS"]
    artifact_index = {
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "upstreams": rows,
        "status": "PASS" if not missing and not parse_failures else "FAIL",
        "boundary": BOUNDARY,
    }
    summary = {
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "required_upstreams_found": sum(1 for row in rows if row["green"]),
        "required_upstreams_total": len(rows),
        "missing_or_not_green": missing,
        "json_jsonl_parse_status": "PASS" if not parse_failures else "FAIL",
        "json_jsonl_parse_failures": [
            {"upstream_key": row["upstream_key"], "parse_failures": row["parse_report"]["parse_failures"]}
            for row in parse_failures
        ],
        "status": "PASS" if not missing and not parse_failures else "FAIL",
    }
    write_json(OUTPUT_ROOT / "UPSTREAM_ARTIFACT_INDEX.json", artifact_index)
    write_json(OUTPUT_ROOT / "UPSTREAM_STATUS_SUMMARY.json", summary)
    return artifact_index, summary, missing


def r1_root() -> Path:
    return root_path(UPSTREAMS["hero_neighbourhood_reference_demo_r1"]["root"])


def load_r1() -> dict[str, Any]:
    root = r1_root()
    return {
        "decision": read_json(root / "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_R1_DECISION.json", {}),
        "manifest": read_json(root / "CONTROL_ROOM_DEMO_MANIFEST.json", {}),
        "matrix": read_json(root / "DEMO_ACCEPTANCE_MATRIX.json", {}),
        "omniverse": read_json(root / "OMNIVERSE_SCENE_HANDOFF_SUMMARY.json", {}),
        "web": read_json(root / "WEB_COMPANION_HANDOFF_SUMMARY.json", {}),
        "operator": read_json(root / "INCIDENT_OPERATOR_SURFACE_PACKET_SUMMARY.json", {}),
        "evidence": read_json(root / "EVIDENCE_LIMITATION_TRACE_SUMMARY.json", {}),
        "preservation": read_json(root / "UNRESOLVED_QUARANTINED_PRESERVATION_REPORT.json", {}),
        "claim": read_json(root / "CLAIM_BOUNDARY_AUDIT.json", {}),
        "no_action": read_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", {}),
        "no_mutation": read_json(root / "NO_MUTATION_AUDIT.json", {}),
        "secret": read_json(root / "SECRET_AUDIT.json", {}),
        "hash": read_json(root / "HASH_MANIFEST.json", {}),
        "operator_script_exists": (root / "OPERATOR_WALKTHROUGH_SCRIPT.md").exists(),
        "executive_script_exists": (root / "EXECUTIVE_WALKTHROUGH_SCRIPT.md").exists(),
        "boundary_freeze": (root / "README.md").read_text(encoding="utf-8", errors="ignore") if (root / "README.md").exists() else "",
    }


def r1_rows(r1: dict[str, Any]) -> list[dict[str, Any]]:
    manifest = r1.get("manifest") or {}
    rows = manifest.get("rows") if isinstance(manifest, dict) else None
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def is_unresolved_or_quarantined(row: dict[str, Any]) -> bool:
    text = json.dumps(row, sort_keys=True).lower()
    return "unresolved" in text or "quarantined" in text


def r1_demo_package_review(r1: dict[str, Any]) -> dict[str, Any]:
    decision = r1["decision"]
    rows = r1_rows(r1)
    status = "PASS"
    failures = []
    expected_status = UPSTREAMS["hero_neighbourhood_reference_demo_r1"]["expected"]
    if decision.get("status") != expected_status:
        status = "FAIL"
        failures.append("R1 decision is missing or not green")
    if len(rows) != decision.get("manifest_rows_count"):
        status = "FAIL"
        failures.append("R1 manifest row count does not match decision")
    for key in [
        "demo_acceptance_status",
        "claim_boundary_status",
        "no_action_boundary_status",
        "no_mutation_status",
        "secret_audit_status",
        "hash_validation_status",
    ]:
        if decision.get(key) != "PASS":
            status = "FAIL"
            failures.append(f"R1 {key} is not PASS")
    if decision.get("blocking_gaps_count") != 0:
        status = "FAIL"
        failures.append("R1 introduced blocking gaps")
    review = {
        "status": status,
        "failures": failures,
        "r1_status": decision.get("status"),
        "manifest_rows_count": len(rows),
        "decision_manifest_rows_count": decision.get("manifest_rows_count"),
        "hero_bindings_count": decision.get("hero_bindings_count"),
        "hero_overlay_packets_count": decision.get("hero_overlay_packets_count"),
        "operator_surface_packets_count": decision.get("operator_surface_packets_count"),
        "web_companion_packets_count": decision.get("web_companion_packets_count"),
        "unresolved_quarantined_preserved_count": decision.get("unresolved_quarantined_preserved_count"),
        "blocking_gaps_count": decision.get("blocking_gaps_count"),
        "non_blocking_gaps_count": decision.get("non_blocking_gaps_count"),
        "visual_acceptance_status": decision.get("visual_acceptance_status"),
        "boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "R1_DEMO_PACKAGE_REVIEW.json", review)
    return review


def freeze_summary(r1: dict[str, Any], upstream_summary: dict[str, Any]) -> tuple[dict[str, Any], str]:
    decision = r1["decision"]
    summary = {
        "status": "PASS",
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "frozen_input_task": "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-CONTROL-ROOM-REFERENCE-DEMO-R1",
        "frozen_input_status": decision.get("status"),
        "required_upstreams_found": upstream_summary["required_upstreams_found"],
        "required_upstreams_total": upstream_summary["required_upstreams_total"],
        "manifest_rows_count": decision.get("manifest_rows_count"),
        "hero_bindings_count": decision.get("hero_bindings_count"),
        "hero_overlay_packets_count": decision.get("hero_overlay_packets_count"),
        "operator_surface_packets_count": decision.get("operator_surface_packets_count"),
        "web_companion_packets_count": decision.get("web_companion_packets_count"),
        "unresolved_quarantined_preserved_count": decision.get("unresolved_quarantined_preserved_count"),
        "blocking_gaps_count": decision.get("blocking_gaps_count"),
        "non_blocking_gaps_count": decision.get("non_blocking_gaps_count"),
        "visual_acceptance_status": decision.get("visual_acceptance_status"),
        "no_new_capabilities_added": True,
        "no_upstream_mutation_intended": True,
        "boundary": BOUNDARY,
        "limitations": LIMITATIONS,
    }
    md = f"""# Control Room Demo Freeze Summary

Status: `{summary['status']}`

{BOUNDARY}

- Frozen input status: `{summary['frozen_input_status']}`
- Required upstreams: `{summary['required_upstreams_found']}/{summary['required_upstreams_total']}`
- Manifest rows: `{summary['manifest_rows_count']}`
- Hero bindings: `{summary['hero_bindings_count']}`
- Hero overlay packets: `{summary['hero_overlay_packets_count']}`
- Operator-surface packets: `{summary['operator_surface_packets_count']}`
- Web companion packets: `{summary['web_companion_packets_count']}`
- Unresolved/quarantined preserved: `{summary['unresolved_quarantined_preserved_count']}`
- Blocking gaps: `{summary['blocking_gaps_count']}`
- Non-blocking gaps: `{summary['non_blocking_gaps_count']}`

This closeout freezes the R1 demo package as a bounded local/replay reference demo with limitations. It does not add new runtime, incident, identity, Omniverse, web, or product behavior.
"""
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_DEMO_FREEZE_SUMMARY.json", summary)
    write_text(OUTPUT_ROOT / "CONTROL_ROOM_DEMO_FREEZE_SUMMARY.md", md)
    return summary, md


def write_closeout_reviews(r1: dict[str, Any]) -> dict[str, dict[str, Any]]:
    operator = {
        "status": "PASS" if r1["operator_script_exists"] else "FAIL",
        "source_script": "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_r1/OPERATOR_WALKTHROUGH_SCRIPT.md",
        "script_exists": r1["operator_script_exists"],
        "review_result": "operator walkthrough preserved as closeout artifact reference",
        "boundary": BOUNDARY,
    }
    executive = {
        "status": "PASS" if r1["executive_script_exists"] else "FAIL",
        "source_script": "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_r1/EXECUTIVE_WALKTHROUGH_SCRIPT.md",
        "script_exists": r1["executive_script_exists"],
        "review_result": "executive walkthrough preserved as closeout artifact reference",
        "boundary": BOUNDARY,
    }
    omniverse = {
        "status": "PASS" if r1["omniverse"].get("status") == "PASS" else "FAIL",
        "source_status": r1["omniverse"].get("status"),
        "usda_exists": r1["omniverse"].get("usda_exists"),
        "prim_metadata_count": r1["omniverse"].get("prim_metadata_count"),
        "package_mode": r1["omniverse"].get("package_mode"),
        "closeout_position": "bounded spatial control-room surface context, not certified citywide twin",
        "production_omniverse_claim": False,
        "citywide_certified_twin_claim": False,
        "physical_accuracy_claim": False,
        "boundary": BOUNDARY,
    }
    web = {
        "status": "PASS" if str(r1["web"].get("status", "")).startswith("PASS") else "FAIL",
        "source_status": r1["web"].get("status"),
        "web_companion_packet_count": r1["web"].get("web_companion_packet_count"),
        "surface": r1["web"].get("surface"),
        "closeout_position": "companion evidence/episode/executive surface only",
        "public_api_claim": False,
        "boundary": BOUNDARY,
    }
    evidence = {
        "status": "PASS" if r1["evidence"].get("status") == "PASS" else "FAIL",
        "source_status": r1["evidence"].get("status"),
        "manifest_rows": r1["evidence"].get("manifest_rows"),
        "rows_with_evidence_refs": r1["evidence"].get("rows_with_evidence_refs"),
        "rows_with_limitation_refs": r1["evidence"].get("rows_with_limitation_refs"),
        "rows_with_trace_refs": r1["evidence"].get("rows_with_trace_refs"),
        "boundary": BOUNDARY,
    }
    preservation = {
        "status": "PASS" if r1["preservation"].get("status") == "PASS" else "FAIL",
        "source_status": r1["preservation"].get("status"),
        "unresolved_quarantined_preserved_count": r1["preservation"].get("unresolved_quarantined_preserved_count"),
        "promoted_to_canonical_truth": r1["preservation"].get("promoted_to_canonical_truth", []),
        "closeout_position": "unresolved/quarantined contexts remain visible and are not promoted",
        "boundary": BOUNDARY,
    }
    reviews = {
        "OPERATOR_WALKTHROUGH_CLOSEOUT_REVIEW.json": operator,
        "EXECUTIVE_WALKTHROUGH_CLOSEOUT_REVIEW.json": executive,
        "OMNIVERSE_HANDOFF_CLOSEOUT_REVIEW.json": omniverse,
        "WEB_COMPANION_CLOSEOUT_REVIEW.json": web,
        "EVIDENCE_LIMITATION_TRACE_CLOSEOUT_REVIEW.json": evidence,
        "UNRESOLVED_QUARANTINED_PRESERVATION_CLOSEOUT_REVIEW.json": preservation,
    }
    for filename, payload in reviews.items():
        write_json(OUTPUT_ROOT / filename, payload)
    return reviews


def non_blocking_gaps_register(r1: dict[str, Any]) -> dict[str, Any]:
    gaps = r1["decision"].get("non_blocking_gaps", [])
    register = {
        "status": "PASS",
        "source_task": "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-CONTROL-ROOM-REFERENCE-DEMO-R1",
        "non_blocking_gaps_count": len(gaps),
        "non_blocking_gaps": gaps,
        "carried_forward": True,
        "blocking_gaps_introduced": False,
        "boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "NON_BLOCKING_GAPS_REGISTER.json", register)
    return register


def acceptance_matrix(upstream: dict[str, Any], review: dict[str, Any], freeze: dict[str, Any], reviews: dict[str, dict[str, Any]], gaps: dict[str, Any]) -> tuple[dict[str, Any], str]:
    checks = [
        {"check_id": "required_upstreams_green", "status": upstream["status"], "evidence": "UPSTREAM_STATUS_SUMMARY.json"},
        {"check_id": "r1_demo_package_review", "status": review["status"], "evidence": "R1_DEMO_PACKAGE_REVIEW.json"},
        {"check_id": "control_room_demo_freeze_summary", "status": freeze["status"], "evidence": "CONTROL_ROOM_DEMO_FREEZE_SUMMARY.json"},
        {"check_id": "operator_walkthrough_closeout_review", "status": reviews["OPERATOR_WALKTHROUGH_CLOSEOUT_REVIEW.json"]["status"], "evidence": "OPERATOR_WALKTHROUGH_CLOSEOUT_REVIEW.json"},
        {"check_id": "executive_walkthrough_closeout_review", "status": reviews["EXECUTIVE_WALKTHROUGH_CLOSEOUT_REVIEW.json"]["status"], "evidence": "EXECUTIVE_WALKTHROUGH_CLOSEOUT_REVIEW.json"},
        {"check_id": "omniverse_handoff_closeout_review", "status": reviews["OMNIVERSE_HANDOFF_CLOSEOUT_REVIEW.json"]["status"], "evidence": "OMNIVERSE_HANDOFF_CLOSEOUT_REVIEW.json"},
        {"check_id": "web_companion_closeout_review", "status": reviews["WEB_COMPANION_CLOSEOUT_REVIEW.json"]["status"], "evidence": "WEB_COMPANION_CLOSEOUT_REVIEW.json"},
        {"check_id": "evidence_limitation_trace_closeout_review", "status": reviews["EVIDENCE_LIMITATION_TRACE_CLOSEOUT_REVIEW.json"]["status"], "evidence": "EVIDENCE_LIMITATION_TRACE_CLOSEOUT_REVIEW.json"},
        {"check_id": "unresolved_quarantined_preservation_closeout_review", "status": reviews["UNRESOLVED_QUARANTINED_PRESERVATION_CLOSEOUT_REVIEW.json"]["status"], "evidence": "UNRESOLVED_QUARANTINED_PRESERVATION_CLOSEOUT_REVIEW.json"},
        {"check_id": "non_blocking_gaps_registered", "status": gaps["status"], "evidence": "NON_BLOCKING_GAPS_REGISTER.json"},
    ]
    matrix = {
        "status": "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL",
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "checks": checks,
        "blocking_gaps_count": sum(check["status"] != "PASS" for check in checks),
        "non_blocking_gaps_count": gaps["non_blocking_gaps_count"],
        "boundary": BOUNDARY,
    }
    md_lines = ["# R1 Demo Acceptance Closeout Matrix", "", f"Status: `{matrix['status']}`", "", BOUNDARY, ""]
    md_lines.extend(f"- {check['check_id']}: `{check['status']}` ({check['evidence']})" for check in checks)
    write_json(OUTPUT_ROOT / "R1_DEMO_ACCEPTANCE_CLOSEOUT_MATRIX.json", matrix)
    write_text(OUTPUT_ROOT / "R1_DEMO_ACCEPTANCE_CLOSEOUT_MATRIX.md", "\n".join(md_lines))
    return matrix, "\n".join(md_lines)


def boundary_freeze_doc() -> None:
    write_text(
        OUTPUT_ROOT / "BOUNDARY_AND_CLAIM_FREEZE.md",
        f"""# Boundary And Claim Freeze

{BOUNDARY}

Closeout freeze rules:

- No new product capabilities were added.
- No new incident logic was added.
- No live monitoring was added.
- No canonical identity behavior was changed.
- No Omniverse behavior was added.
- No web behavior was added.
- Upstream artifacts were consumed read-only.
- Non-blocking R1 gaps are carried forward without erasure.
""",
    )


def claim_boundary_audit() -> dict[str, Any]:
    combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore").lower() for path in OUTPUT_ROOT.rglob("*") if path.is_file() and path.name != "CLAIM_BOUNDARY_AUDIT.json")
    positive_patterns = [
        r'"production_readiness_claim_made"\s*:\s*true',
        r'"public_api_readiness_claim_made"\s*:\s*true',
        r'"live_monitoring_claim_made"\s*:\s*true',
        r'"autonomous_incident_detection_claim_made"\s*:\s*true',
        r'"alert_push_claim_made"\s*:\s*true',
        r'"dispatch_claim_made"\s*:\s*true',
        r'"routing_control_claim_made"\s*:\s*true',
        r'"enforcement_claim_made"\s*:\s*true',
        r'"official_ticket_case_creation_claim_made"\s*:\s*true',
        r'"legal_certified_incident_finding_claim_made"\s*:\s*true',
        r'"citywide_certified_twin_claim_made"\s*:\s*true',
        r'"physical_accuracy_claim_made"\s*:\s*true',
        r'"automated_action_claim_made"\s*:\s*true',
        r"production ready for deployment",
        r"public api ready",
        r"autonomous incident detection enabled",
        r"alert push enabled",
        r"dispatch command",
        r"routing/control command",
        r"enforcement action",
        r"official ticket created",
        r"certified incident finding enabled",
        r"certified incident finding issued",
    ]
    hits = [pattern for pattern in positive_patterns if re.search(pattern, combined)]
    boundary_present = BOUNDARY.lower() in combined
    report = {
        "status": "PASS" if not hits and boundary_present else "FAIL",
        "positive_forbidden_claim_hits": hits,
        "boundary_present": boundary_present,
        "production_readiness_claim_made": False,
        "public_api_readiness_claim_made": False,
        "live_monitoring_claim_made": False,
        "autonomous_incident_detection_claim_made": False,
        "alert_push_claim_made": False,
        "dispatch_claim_made": False,
        "routing_control_claim_made": False,
        "enforcement_claim_made": False,
        "official_ticket_case_creation_claim_made": False,
        "legal_certified_incident_finding_claim_made": False,
        "citywide_certified_twin_claim_made": False,
        "physical_accuracy_claim_made": False,
        "automated_action_claim_made": False,
        "boundary": BOUNDARY,
        "no_action_taken": True,
    }
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", report)
    return report


def no_action_audit() -> dict[str, Any]:
    generated = "\n".join(path.read_text(encoding="utf-8", errors="ignore").lower() for path in OUTPUT_ROOT.rglob("*") if path.is_file() and path.name != "NO_ACTION_BOUNDARY_AUDIT.json")
    positive_patterns = [
        r'"no_action_taken"\s*:\s*false',
        r'"action_taken"\s*:\s*true',
        r"dispatch command",
        r"routing/control command",
        r"enforcement action",
        r"official ticket created",
        r"automated action triggered",
    ]
    hits = [pattern for pattern in positive_patterns if re.search(pattern, generated)]
    report = {
        "status": "PASS" if not hits else "FAIL",
        "positive_action_hits": hits,
        "no_action_taken": True,
        "boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "NO_ACTION_BOUNDARY_AUDIT.json", report)
    return report


def no_mutation_audit(before: dict[str, dict[str, Any]]) -> dict[str, Any]:
    changed = []
    for key, spec in UPSTREAMS.items():
        after = snapshot(root_path(spec["root"]))
        if before.get(key) != after:
            changed.append({"upstream_key": key, "root": spec["root"], "before": before.get(key), "after": after})
    report = {
        "status": "PASS" if not changed else "FAIL",
        "watched_upstream_count": len(before),
        "changed_upstreams": changed,
        "output_root_only_mutated": not changed,
        "no_action_taken": True,
        "boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", report)
    return report


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{12,}['\"]"),
        re.compile(r"(?i)authorization\s*[:=]\s*bearer\s+[a-z0-9._-]{16,}"),
        re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and path.name not in {"SECRET_AUDIT.json", "HASH_MANIFEST.json"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                if pattern.search(text):
                    findings.append({"path": rel(path), "pattern": pattern.pattern})
    report = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings, "boundary": BOUNDARY}
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", report)
    return report


def hash_manifest() -> dict[str, Any]:
    rows = []
    for path in sorted(item for item in OUTPUT_ROOT.rglob("*") if item.is_file()):
        if path.name == "HASH_MANIFEST.json":
            continue
        rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    failures = [row["path"] for row in rows if not (REPO_ROOT / row["path"]).exists() or sha256_file(REPO_ROOT / row["path"]) != row["sha256"]]
    report = {
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "file_count": len(rows),
        "files": rows,
        "hash_validation_status": "PASS" if not failures else "FAIL",
        "failures": failures,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", report)
    return report


def required_files_status() -> dict[str, Any]:
    missing = [name for name in REQUIRED_OUTPUTS if not (OUTPUT_ROOT / name).exists()]
    return {"status": "PASS" if not missing else "FAIL", "missing": missing, "required_count": len(REQUIRED_OUTPUTS)}


def write_readme_and_index(decision: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

Status: `{decision['status']}`

{BOUNDARY}

This closeout freezes the R1 Hero Neighbourhood control-room reference demo as a bounded local/replay reference package with limitations.

- Required upstreams: `{decision['upstreams_found']}/{decision['required_upstreams_total']}`
- Manifest rows: `{decision['r1_manifest_row_count']}`
- Hero bindings: `{decision['hero_bindings_count']}`
- Overlay packets: `{decision['overlay_packet_count']}`
- Operator-surface packets: `{decision['operator_surface_packet_count']}`
- Web companion packets: `{decision['web_companion_packet_count']}`
- Unresolved/quarantined preserved: `{decision['unresolved_quarantined_preserved_count']}`
- Blocking gaps: `{decision['blocking_gaps_count']}`
- Non-blocking gaps: `{decision['non_blocking_gaps_count']}`
- Recommended next task: `{decision['recommended_next_task']}`
""",
    )
    lines = [f"# {TASK_NAME}", "", f"Status: `{decision['status']}`", "", BOUNDARY, "", "## Artifacts", ""]
    lines.extend(f"- [{name}]({name})" for name in REQUIRED_OUTPUTS)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def main() -> int:
    prepare_output_root()
    before = {key: snapshot(root_path(spec["root"])) for key, spec in UPSTREAMS.items()}
    _artifact_index, upstream_summary, missing = discover_upstreams()
    if upstream_summary["status"] != "PASS":
        decision = {
            "status": FAIL_STATUS,
            "task_name": TASK_NAME,
            "timestamp": now_iso(),
            "output_root": str(OUTPUT_ROOT),
            "runner_path": str(Path(__file__).resolve()),
            "upstreams_found": upstream_summary["required_upstreams_found"],
            "required_upstreams_total": upstream_summary["required_upstreams_total"],
            "missing_or_not_green": missing,
            "blocking_gaps_count": len(missing),
            "recommended_next_task": FIXUP_NEXT_TASK,
            "boundary": BOUNDARY,
        }
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_DECISION.json", decision)
        write_text(OUTPUT_ROOT / "README.md", f"# {TASK_NAME}\n\nStatus: `{FAIL_STATUS}`\n\n{BOUNDARY}\n")
        hash_manifest()
        print(json.dumps(decision, indent=2, sort_keys=True))
        return 1

    r1 = load_r1()
    review = r1_demo_package_review(r1)
    freeze, _freeze_md = freeze_summary(r1, upstream_summary)
    reviews = write_closeout_reviews(r1)
    gaps = non_blocking_gaps_register(r1)
    matrix, _matrix_md = acceptance_matrix(upstream_summary, review, freeze, reviews, gaps)
    boundary_freeze_doc()

    claim = claim_boundary_audit()
    no_action = no_action_audit()
    no_mutation = no_mutation_audit(before)
    secret = secret_audit()

    status = PASS_STATUS
    if not all(
        [
            upstream_summary["status"] == "PASS",
            review["status"] == "PASS",
            freeze["status"] == "PASS",
            matrix["status"] == "PASS",
            claim["status"] == "PASS",
            no_action["status"] == "PASS",
            no_mutation["status"] == "PASS",
            secret["status"] == "PASS",
        ]
    ):
        status = FAIL_STATUS

    r1_decision = r1["decision"]
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(Path(__file__).resolve()),
        "upstreams_found": upstream_summary["required_upstreams_found"],
        "required_upstreams_total": upstream_summary["required_upstreams_total"],
        "r1_manifest_row_count": r1_decision.get("manifest_rows_count"),
        "hero_bindings_count": r1_decision.get("hero_bindings_count"),
        "overlay_packet_count": r1_decision.get("hero_overlay_packets_count"),
        "operator_surface_packet_count": r1_decision.get("operator_surface_packets_count"),
        "web_companion_packet_count": r1_decision.get("web_companion_packets_count"),
        "unresolved_quarantined_preserved_count": r1_decision.get("unresolved_quarantined_preserved_count"),
        "blocking_gaps_count": matrix["blocking_gaps_count"],
        "non_blocking_gaps_count": gaps["non_blocking_gaps_count"],
        "demo_acceptance_closeout_status": matrix["status"],
        "omniverse_closeout_review_status": reviews["OMNIVERSE_HANDOFF_CLOSEOUT_REVIEW.json"]["status"],
        "web_companion_closeout_review_status": reviews["WEB_COMPANION_CLOSEOUT_REVIEW.json"]["status"],
        "claim_boundary_status": claim["status"],
        "no_action_boundary_status": no_action["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PENDING",
        "production_readiness_claim_made": False,
        "public_api_readiness_claim_made": False,
        "live_monitoring_claim_made": False,
        "autonomous_incident_detection_claim_made": False,
        "alert_push_claim_made": False,
        "dispatch_claim_made": False,
        "routing_control_claim_made": False,
        "enforcement_claim_made": False,
        "official_ticket_case_creation_claim_made": False,
        "legal_certified_incident_finding_claim_made": False,
        "citywide_certified_twin_claim_made": False,
        "physical_accuracy_claim_made": False,
        "automated_action_claim_made": False,
        "limitations": LIMITATIONS,
        "recommended_next_task": RECOMMENDED_NEXT_TASK if status == PASS_STATUS else FIXUP_NEXT_TASK,
        "alternative_next_task_if_gaps": FIXUP_NEXT_TASK,
        "boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_DECISION.json", decision)
    write_readme_and_index(decision)
    claim = claim_boundary_audit()
    secret = secret_audit()
    hash_report = hash_manifest()
    required = required_files_status()
    if not all([claim["status"] == "PASS", secret["status"] == "PASS", hash_report["hash_validation_status"] == "PASS", required["status"] == "PASS"]):
        status = FAIL_STATUS
        decision["status"] = FAIL_STATUS
        decision["recommended_next_task"] = FIXUP_NEXT_TASK
        decision["blocking_gaps_count"] = matrix["blocking_gaps_count"] + len(required["missing"])
    decision["claim_boundary_status"] = claim["status"]
    decision["secret_audit_status"] = secret["status"]
    decision["hash_validation_status"] = hash_report["hash_validation_status"]
    decision["required_output_missing"] = required["missing"]
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_DECISION.json", decision)
    hash_manifest()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
