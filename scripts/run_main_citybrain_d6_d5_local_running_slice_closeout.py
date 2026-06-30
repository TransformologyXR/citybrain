#!/usr/bin/env python3
"""Close out the D6/D5 local running control-room slice milestone."""

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

TASK_NAME = "MAIN-CITYBRAIN-D6-D5-LOCAL-RUNNING-SLICE-CLOSEOUT"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_d5_local_running_slice_closeout"

UPSTREAMS = {
    "d6_d5_local_running_control_room_slice_r1": {
        "root": "outputs/main_citybrain_d6_d5_local_running_control_room_slice_r1",
        "expected": "PASS_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_CONTROL_ROOM_SLICE_R1_WITH_LIMITATIONS",
    },
    "d5_track2_handoff_r4": {
        "root": "outputs/main_citybrain_d5_local_served_runtime_track2_handoff_r4",
        "expected": "PASS_MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_TRACK2_HANDOFF_R4_WITH_LIMITATIONS",
    },
    "d5_event_fabric_integration_r3": {
        "root": "outputs/main_citybrain_d5_local_served_runtime_event_fabric_integration_r3",
        "expected": "PASS_MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_EVENT_FABRIC_INTEGRATION_R3_WITH_LIMITATIONS",
    },
    "r7_multi_domain_edge_registry_runtime_slice": {
        "root": "outputs/main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_WITH_LIMITATIONS",
    },
}

R1_REQUIRED_FILES = [
    "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_CONTROL_ROOM_SLICE_R1_DECISION.json",
    "README.md",
    "INPUT_ARTIFACT_INDEX.json",
    "UPSTREAM_BRANCH_STATUS_SUMMARY.json",
    "LOCAL_RUNNING_SLICE_CONFIG.json",
    "CONTROL_ROOM_SCENARIO_SELECTION.json",
    "D5_RUNTIME_SMOKE_RESULTS.json",
    "CONTROL_ROOM_CONTEXT_PACKET_BUNDLE.json",
    "CONTROL_ROOM_EVENT_OVERLAY_PACKET.json",
    "CONTROL_ROOM_ASSET_EDGE_PACKET.json",
    "OMNIVERSE_KIT_COMPOSER_HANDOFF_MANIFEST.json",
    "WEB_COMPANION_HANDOFF_MANIFEST.json",
    "OPERATOR_SCRIPT.md",
    "EXECUTIVE_SCRIPT.md",
    "EVIDENCE_TRACE_WALKTHROUGH.md",
    "VISUAL_ACCEPTANCE_CHECKLIST.md",
    "CLAIM_BOUNDARY_AUDIT.json",
    "NO_MUTATION_AUDIT.json",
    "SECRET_AUDIT.json",
    "HASH_MANIFEST.json",
    "LOCAL_OPEN_INDEX.md",
]

LIMITATIONS = [
    "closeout validates and freezes existing local/replay artifacts only",
    "no new product behavior is added",
    "runtime review is fixture replay, not a production service",
    "Omniverse remains Kit/Composer context, not a full citywide twin",
    "web remains companion evidence/episode/executive context",
    "event/current-state/relationship context remains local/replay review/query context only",
    "no public API readiness, autonomous monitoring, alert push, dispatch, routing/control, enforcement, legal/certified claim, or automated action",
]

BOUNDARY = (
    "D6/D5 local running slice closeout context only. Confirms artifact-backed local/replay review "
    "state without production service, public API readiness, live or autonomous monitoring, alert push, "
    "dispatch, routing/control, enforcement, legal/certified claim, full citywide twin claim, or automated action."
)

RECOMMENDED_NEXT_TASK = "MAIN-CITYBRAIN-D6-INCIDENT-MODE-PREFLIGHT"
PARALLEL_NEXT_CANDIDATES = [
    "MAIN-CITYBRAIN-D4X-R8-MULTI-DOMAIN-EDGE-REGISTRY-HARDENING",
    "PM_SELECTED_PLATFORM_OR_DOMAIN_FOLLOW_UP",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def root_path(root: str) -> Path:
    return REPO_ROOT / root


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return default


def read_text(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8", errors="replace")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "byte_count": 0, "fingerprint": None}
    files = sorted(item for item in path.rglob("*") if item.is_file())
    digest = hashlib.sha256()
    byte_count = 0
    for item in files:
        stat = item.stat()
        byte_count += stat.st_size
        digest.update(rel(item).encode("utf-8"))
        digest.update(str(stat.st_size).encode("utf-8"))
        digest.update(str(stat.st_mtime_ns).encode("utf-8"))
    return {"exists": True, "file_count": len(files), "byte_count": byte_count, "fingerprint": digest.hexdigest()}


def decision_file(path: Path) -> Path | None:
    files = sorted(path.glob("*DECISION*.json")) if path.exists() else []
    return files[0] if files else None


def decision_status(path: Path) -> str | None:
    decision = decision_file(path)
    if not decision:
        return None
    payload = read_json(decision, {})
    return str(payload.get("status")) if payload.get("status") else None


def rows_from(payload: Any, keys: list[str]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    for key in keys:
        rows = payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def discover_inputs(pre: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    missing: list[str] = []
    branches = []
    for branch, meta in UPSTREAMS.items():
        path = root_path(meta["root"])
        status = decision_status(path)
        green = path.exists() and status == meta["expected"]
        if not green:
            missing.append(branch)
        artifacts = []
        if path.exists():
            for item in sorted(path.rglob("*")):
                if item.is_file() and item.suffix.lower() in {".json", ".jsonl", ".md", ".html", ".py", ".usda"}:
                    artifacts.append(rel(item))
                if len(artifacts) >= 24:
                    break
        branches.append(
            {
                "branch": branch,
                "root": meta["root"],
                "exists": path.exists(),
                "decision_path": rel(decision_file(path)) if decision_file(path) else None,
                "status": status,
                "expected": meta["expected"],
                "green": green,
                "snapshot": pre[meta["root"]],
                "sample_artifacts": artifacts,
                "read_only": True,
            }
        )
    report = {"status": "PASS" if not missing else "FAIL", "timestamp": utc_now(), "upstream_missing": missing, "branches": branches}
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", report)
    return report, missing


def branch_summary(input_index: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for branch in input_index["branches"]:
        decision = read_json(REPO_ROOT / branch["decision_path"], {}) if branch.get("decision_path") else {}
        rows.append(
            {
                "branch": branch["branch"],
                "root": branch["root"],
                "status": branch["status"],
                "green": branch["green"],
                "count_fields": {key: value for key, value in decision.items() if isinstance(value, int) and ("count" in key or "packet" in key or "edge" in key or "route" in key)},
                "recommended_next_task": decision.get("recommended_next_task"),
                "consumed_by_closeout": branch["green"],
                "no_action_taken": True,
            }
        )
    report = {"status": "PASS" if all(row["green"] for row in rows) else "FAIL", "branches": rows}
    write_json(OUTPUT_ROOT / "UPSTREAM_BRANCH_STATUS_SUMMARY.json", report)
    return report


def validate_hash_manifest(root: Path) -> dict[str, Any]:
    manifest = read_json(root / "HASH_MANIFEST.json", {})
    files = rows_from(manifest, ["files"])
    failures = []
    for row in files:
        path = REPO_ROOT / row.get("path", "")
        if not path.exists():
            failures.append({"path": row.get("path"), "reason": "missing"})
        elif sha256_file(path) != row.get("sha256"):
            failures.append({"path": row.get("path"), "reason": "sha256_mismatch"})
    return {
        "status": "PASS" if manifest.get("status") == "PASS" and files and not failures else "FAIL",
        "manifest_path": rel(root / "HASH_MANIFEST.json"),
        "file_count": len(files),
        "failures": failures,
    }


def load_r1() -> dict[str, Any]:
    r1 = root_path(UPSTREAMS["d6_d5_local_running_control_room_slice_r1"]["root"])
    return {
        "root": r1,
        "decision": read_json(r1 / "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_CONTROL_ROOM_SLICE_R1_DECISION.json", {}),
        "input_index": read_json(r1 / "INPUT_ARTIFACT_INDEX.json", {}),
        "runtime_smoke": read_json(r1 / "D5_RUNTIME_SMOKE_RESULTS.json", {}),
        "bundle": read_json(r1 / "CONTROL_ROOM_CONTEXT_PACKET_BUNDLE.json", {}),
        "omni": read_json(r1 / "OMNIVERSE_KIT_COMPOSER_HANDOFF_MANIFEST.json", {}),
        "web": read_json(r1 / "WEB_COMPANION_HANDOFF_MANIFEST.json", {}),
        "scenario": read_json(r1 / "CONTROL_ROOM_SCENARIO_SELECTION.json", {}),
        "claim": read_json(r1 / "CLAIM_BOUNDARY_AUDIT.json", {}),
        "mutation": read_json(r1 / "NO_MUTATION_AUDIT.json", {}),
        "secret": read_json(r1 / "SECRET_AUDIT.json", {}),
        "local_index_text": read_text(r1 / "LOCAL_OPEN_INDEX.md"),
        "visual_text": read_text(r1 / "VISUAL_ACCEPTANCE_CHECKLIST.md"),
        "operator_text": read_text(r1 / "OPERATOR_SCRIPT.md"),
        "executive_text": read_text(r1 / "EXECUTIVE_SCRIPT.md"),
        "evidence_text": read_text(r1 / "EVIDENCE_TRACE_WALKTHROUGH.md"),
    }


def write_current_truth(input_index: dict[str, Any], r1: dict[str, Any]) -> dict[str, Any]:
    branch_status = {branch["branch"]: branch["status"] for branch in input_index["branches"]}
    truth = {
        "status": "PASS" if all(branch["green"] for branch in input_index["branches"]) else "FAIL",
        "timestamp": utc_now(),
        "frozen_truths": [
            "D4X R7 multi-domain edge registry runtime slice passed.",
            "D5 R3 local served runtime event-fabric integration passed.",
            "D5 R4 local served runtime Track2 handoff passed.",
            "D6/D5 local running control-room slice R1 passed.",
            "Omniverse Kit/Composer remains the primary spatial control-room surface context.",
            "Web remains the companion evidence/episode/executive surface context.",
            "Event/current-state/relationship context remains local/replay review/query context only.",
        ],
        "branch_status": branch_status,
        "selected_scenario_id": r1["decision"].get("selected_scenario_id"),
        "control_room_packet_count": r1["decision"].get("control_room_packet_count"),
        "unsupported_claim_upgrades": {
            "production_service": False,
            "public_api_ready": False,
            "autonomous_monitoring": False,
            "alert_push": False,
            "dispatch_or_routing_control": False,
            "enforcement_or_legal_certification": False,
            "full_citywide_twin": False,
        },
        "claim_boundary": BOUNDARY,
        "limitations": LIMITATIONS,
    }
    write_json(OUTPUT_ROOT / "CURRENT_TRUTH_REGISTER.json", truth)
    return truth


def completeness_review(r1_root: Path, local_index_text: str) -> dict[str, Any]:
    missing = [name for name in R1_REQUIRED_FILES if not (r1_root / name).exists()]
    missing_from_index = [name for name in R1_REQUIRED_FILES if name not in local_index_text]
    return {
        "required_file_status": "PASS" if not missing else "FAIL",
        "missing_required_files": missing,
        "local_open_index_status": "PASS" if not missing_from_index else "FAIL",
        "missing_from_local_open_index": missing_from_index,
    }


def write_reviews(r1: dict[str, Any]) -> dict[str, dict[str, Any]]:
    bundle_packets = rows_from(r1["bundle"], ["packets"])
    runtime_review = {
        "status": "PASS" if r1["runtime_smoke"].get("status") == "PASS" else "FAIL",
        "runtime_smoke_mode": r1["runtime_smoke"].get("runtime_smoke_mode"),
        "runtime_route_count": r1["runtime_smoke"].get("runtime_route_count"),
        "checks": r1["runtime_smoke"].get("checks", []),
    }
    packet_review = {
        "status": "PASS" if r1["bundle"].get("status") == "PASS" and r1["bundle"].get("packet_count", 0) >= 8 else "FAIL",
        "bundle_id": r1["bundle"].get("bundle_id"),
        "packet_count": r1["bundle"].get("packet_count", 0),
        "contains": r1["bundle"].get("contains", {}),
        "all_packets_have_evidence_and_limitations": all(packet.get("evidence_refs") and packet.get("limitation_refs") for packet in bundle_packets),
        "all_packets_no_action": all(packet.get("no_action_taken") is True for packet in bundle_packets),
    }
    if not packet_review["all_packets_have_evidence_and_limitations"] or not packet_review["all_packets_no_action"]:
        packet_review["status"] = "FAIL"
    omni_review = {
        "status": "PASS" if r1["omni"].get("status") == "PASS" and r1["omni"].get("canonical_entity_refs") and r1["omni"].get("event_context_refs") and r1["omni"].get("evidence_refs") and r1["omni"].get("limitation_refs") else "FAIL",
        "surface": r1["omni"].get("surface"),
        "source_kit_packet_ref": r1["omni"].get("source_kit_packet_ref"),
        "citywide_twin_claim": r1["omni"].get("citywide_twin_claim"),
    }
    web_review = {
        "status": "PASS" if r1["web"].get("status") == "PASS" and r1["web"].get("evidence_refs") and "companion" in str(r1["web"].get("surface", "")).lower() else "FAIL",
        "surface": r1["web"].get("surface"),
        "source_web_packet_ref": r1["web"].get("source_web_packet_ref"),
        "executive_context_ref": r1["web"].get("executive_context_ref"),
    }
    evidence_review = {
        "status": "PASS" if r1["evidence_text"] and packet_review["all_packets_have_evidence_and_limitations"] else "FAIL",
        "walkthrough_present": bool(r1["evidence_text"]),
        "bundle_packet_count": len(bundle_packets),
        "evidence_limitation_codisplay": packet_review["all_packets_have_evidence_and_limitations"],
    }
    visual_review = {
        "status": "PASS" if r1["visual_text"] and "PASS_CHECKLIST_PRESENT_GUI_NOT_PERFORMED" in r1["visual_text"] else "FAIL",
        "checklist_present": bool(r1["visual_text"]),
        "gui_acceptance_performed": "[x] GUI visual acceptance performed" in r1["visual_text"],
        "accepted_closeout_boundary": "checklist-present; GUI acceptance intentionally not performed by fixture runner",
    }
    write_json(OUTPUT_ROOT / "RUNTIME_SMOKE_REPLAY_REVIEW.json", runtime_review)
    write_json(OUTPUT_ROOT / "CONTROL_ROOM_PACKET_REVIEW.json", packet_review)
    write_json(OUTPUT_ROOT / "OMNIVERSE_HANDOFF_REVIEW.json", omni_review)
    write_json(OUTPUT_ROOT / "WEB_COMPANION_HANDOFF_REVIEW.json", web_review)
    write_json(OUTPUT_ROOT / "EVIDENCE_LIMITATION_TRACE_REVIEW.json", evidence_review)
    write_json(OUTPUT_ROOT / "VISUAL_ACCEPTANCE_REVIEW.json", visual_review)
    return {
        "runtime": runtime_review,
        "packet": packet_review,
        "omni": omni_review,
        "web": web_review,
        "evidence": evidence_review,
        "visual": visual_review,
    }


def write_acceptance_matrix(input_index: dict[str, Any], r1: dict[str, Any], truth: dict[str, Any], reviews: dict[str, dict[str, Any]], completeness: dict[str, Any], r1_hash: dict[str, Any]) -> dict[str, Any]:
    r1_decision_ok = r1["decision"].get("status") == UPSTREAMS["d6_d5_local_running_control_room_slice_r1"]["expected"]
    script_boundary_ok = all(
        phrase in (r1["operator_text"] + "\n" + r1["executive_text"]).lower()
        for phrase in ["not a production service", "public api", "dispatch", "legal"]
    )
    rows = [
        {"check_id": "01_r1_decision_status", "status": "PASS" if r1_decision_ok else "FAIL"},
        {"check_id": "02_input_artifact_discovery", "status": input_index["status"]},
        {"check_id": "03_required_output_file_completeness", "status": completeness["required_file_status"]},
        {"check_id": "04_local_open_index_completeness", "status": completeness["local_open_index_status"]},
        {"check_id": "05_runtime_smoke_replay_report_presence", "status": reviews["runtime"]["status"]},
        {"check_id": "06_control_room_packet_bundle_presence", "status": reviews["packet"]["status"]},
        {"check_id": "07_omniverse_handoff_manifest_presence", "status": reviews["omni"]["status"]},
        {"check_id": "08_web_companion_handoff_manifest_presence", "status": reviews["web"]["status"]},
        {"check_id": "09_operator_executive_script_presence", "status": "PASS" if r1["operator_text"] and r1["executive_text"] and script_boundary_ok else "FAIL"},
        {"check_id": "10_evidence_limitation_trace_completeness", "status": reviews["evidence"]["status"]},
        {"check_id": "11_visual_acceptance_checklist_presence", "status": reviews["visual"]["status"]},
        {"check_id": "12_claim_boundary_audit", "status": r1["claim"].get("status", "FAIL")},
        {"check_id": "13_no_mutation_audit", "status": r1["mutation"].get("status", "FAIL")},
        {"check_id": "14_secret_audit", "status": r1["secret"].get("status", "FAIL")},
        {"check_id": "15_hash_manifest_verification", "status": r1_hash["status"]},
        {"check_id": "16_branch_current_truth_register_consistency", "status": "PASS" if truth["status"] == "PASS" and not any(truth["unsupported_claim_upgrades"].values()) else "FAIL"},
    ]
    report = {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "checks": rows, "missing_required_files": completeness["missing_required_files"], "missing_from_local_open_index": completeness["missing_from_local_open_index"]}
    write_json(OUTPUT_ROOT / "CLOSEOUT_ACCEPTANCE_MATRIX.json", report)
    return report


def write_next_task() -> None:
    text = f"""# Next Task Recommendation

Recommended next task: `{RECOMMENDED_NEXT_TASK}`

Reason: the D6/D5 local running control-room slice is now frozen as a bounded review path. The next useful product question is whether the same local/replay spine can support incident-mode reasoning without crossing into alerting, dispatch, enforcement, control, or legal/certified claims.

Parallel candidates:

- `{PARALLEL_NEXT_CANDIDATES[0]}` for backend registry hardening.
- `{PARALLEL_NEXT_CANDIDATES[1]}` if product management selects a platform or domain follow-up.

Boundary: all recommendations remain local/replay review context unless a later task explicitly defines and validates a new bounded scope.
"""
    write_text(OUTPUT_ROOT / "NEXT_TASK_RECOMMENDATION.md", text)


def audit_claims() -> dict[str, Any]:
    forbidden = [
        "production_ready\": true",
        "public_api_ready\": true",
        "public_api_exposed\": true",
        "autonomous_monitoring\": true",
        "alert_push\": true",
        "alert_push_enabled\": true",
        "dispatch_created\": true",
        "routing_control_created\": true",
        "dispatch_or_routing_control\": true",
        "citywide_twin_claim\": true",
        "full_citywide_twin\": true",
        "legal_certified_claim\": true",
        "enforcement_or_legal_certification\": true",
    ]
    joined = ""
    for item in OUTPUT_ROOT.rglob("*"):
        if item.is_file() and item.name not in {"CLAIM_BOUNDARY_AUDIT.json", "HASH_MANIFEST.json"} and item.suffix.lower() in {".json", ".md", ".txt"}:
            joined += "\n" + item.read_text(encoding="utf-8", errors="ignore").lower()
    hits = [pattern for pattern in forbidden if pattern in joined]
    report = {"status": "PASS" if not hits else "FAIL", "forbidden_positive_claim_hits": hits, "claim_boundary": BOUNDARY}
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", report)
    return report


def audit_mutation(pre: dict[str, dict[str, Any]]) -> dict[str, Any]:
    changed = []
    for meta in UPSTREAMS.values():
        root = meta["root"]
        after = snapshot(root_path(root))
        if after != pre[root]:
            changed.append(root)
    report = {"status": "PASS" if not changed else "FAIL", "changed_roots": changed}
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", report)
    return report


def audit_secret() -> dict[str, Any]:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]+['\"]"),
        re.compile(r"(?i)authorization\s*:\s*bearer\s+[a-z0-9._-]+"),
    ]
    findings = []
    for item in OUTPUT_ROOT.rglob("*"):
        if item.is_file() and item.name != "HASH_MANIFEST.json" and item.suffix.lower() in {".json", ".md", ".txt"}:
            text = item.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                if pattern.search(text):
                    findings.append({"path": rel(item), "pattern": pattern.pattern})
    report = {"status": "PASS" if not findings else "FAIL", "findings": findings}
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", report)
    return report


def hash_manifest() -> dict[str, Any]:
    rows = []
    for item in sorted(OUTPUT_ROOT.rglob("*")):
        if item.is_file() and item.name != "HASH_MANIFEST.json":
            rows.append({"path": rel(item), "sha256": sha256_file(item), "size_bytes": item.stat().st_size})
    failures = [row["path"] for row in rows if not (REPO_ROOT / row["path"]).exists() or sha256_file(REPO_ROOT / row["path"]) != row["sha256"]]
    report = {"status": "PASS" if rows and not failures else "FAIL", "file_count": len(rows), "failures": failures, "files": rows}
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", report)
    return report


def write_hash_validation_report(upstream_hashes: dict[str, Any], closeout_manifest_status: str) -> dict[str, Any]:
    report = {
        "status": "PASS" if closeout_manifest_status == "PASS" and all(row["status"] == "PASS" for row in upstream_hashes.values()) else "FAIL",
        "closeout_generated_hash_manifest_status": closeout_manifest_status,
        "upstream_hash_validations": upstream_hashes,
    }
    write_json(OUTPUT_ROOT / "HASH_VALIDATION_REPORT.json", report)
    return report


def write_index() -> None:
    files = [
        "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_DECISION.json",
        "README.md",
        "INPUT_ARTIFACT_INDEX.json",
        "UPSTREAM_BRANCH_STATUS_SUMMARY.json",
        "CURRENT_TRUTH_REGISTER.json",
        "CLOSEOUT_ACCEPTANCE_MATRIX.json",
        "RUNTIME_SMOKE_REPLAY_REVIEW.json",
        "CONTROL_ROOM_PACKET_REVIEW.json",
        "OMNIVERSE_HANDOFF_REVIEW.json",
        "WEB_COMPANION_HANDOFF_REVIEW.json",
        "EVIDENCE_LIMITATION_TRACE_REVIEW.json",
        "VISUAL_ACCEPTANCE_REVIEW.json",
        "CLAIM_BOUNDARY_AUDIT.json",
        "NO_MUTATION_AUDIT.json",
        "SECRET_AUDIT.json",
        "HASH_VALIDATION_REPORT.json",
        "HASH_MANIFEST.json",
        "LOCAL_OPEN_INDEX.md",
        "NEXT_TASK_RECOMMENDATION.md",
    ]
    lines = [
        f"# {TASK_NAME}",
        "",
        "Closeout status: see decision JSON.",
        "",
        "This closeout freezes the local/replay D6/D5 control-room slice baseline without adding new behavior.",
        "",
        "## Artifacts",
        "",
    ]
    lines.extend(f"- [{name}]({name})" for name in files)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

This pack validates and freezes the D6/D5 local running control-room slice.

Frozen truth: D4X R7, D5 R3, D5 R4, and D6/D5 R1 are artifact-backed and bounded to local/replay review/query context. Omniverse Kit/Composer remains the primary spatial surface context; web remains companion evidence/episode/executive context.

No new product behavior, production service, public API, autonomous monitoring, alerting, dispatch, routing/control, enforcement, legal/certified workflow, full citywide twin claim, or automated action is introduced.
""",
    )


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    pre = {meta["root"]: snapshot(root_path(meta["root"])) for meta in UPSTREAMS.values()}
    input_index, missing = discover_inputs(pre)
    upstream = branch_summary(input_index)
    r1 = load_r1()
    r1_hash = validate_hash_manifest(r1["root"])
    upstream_hashes = {"d6_d5_local_running_control_room_slice_r1": r1_hash}
    truth = write_current_truth(input_index, r1)
    completeness = completeness_review(r1["root"], r1["local_index_text"])
    reviews = write_reviews(r1)
    matrix = write_acceptance_matrix(input_index, r1, truth, reviews, completeness, r1_hash)
    write_next_task()
    write_index()
    claim = audit_claims()
    mutation = audit_mutation(pre)
    secret = audit_secret()

    preliminary_manifest = hash_manifest()
    hash_report = write_hash_validation_report(upstream_hashes, preliminary_manifest["status"])

    status = PASS_STATUS
    if not all(
        [
            not missing,
            input_index["status"] == "PASS",
            upstream["status"] == "PASS",
            truth["status"] == "PASS",
            matrix["status"] == "PASS",
            reviews["runtime"]["status"] == "PASS",
            reviews["packet"]["status"] == "PASS",
            reviews["omni"]["status"] == "PASS",
            reviews["web"]["status"] == "PASS",
            reviews["visual"]["status"] == "PASS",
            claim["status"] == "PASS",
            mutation["status"] == "PASS",
            secret["status"] == "PASS",
            hash_report["status"] == "PASS",
        ]
    ):
        status = FAIL_STATUS

    frozen_truth_summary = [
        "D4X R7, D5 R3, D5 R4, and D6/D5 R1 passed with limitations.",
        "Omniverse Kit/Composer remains the primary spatial control-room surface context.",
        "Web remains the companion evidence/episode/executive surface context.",
        "Event/current-state/relationship context remains local/replay review/query context only.",
    ]
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "upstream_missing": missing,
        "upstream_status_summary": upstream["status"],
        "closeout_acceptance_matrix_result": matrix["status"],
        "runtime_smoke_replay_review_result": reviews["runtime"]["status"],
        "control_room_packet_review_result": reviews["packet"]["status"],
        "omniverse_handoff_review_result": reviews["omni"]["status"],
        "web_companion_review_result": reviews["web"]["status"],
        "visual_acceptance_review_result": reviews["visual"]["status"],
        "boundary_audit_result": claim["status"],
        "claim_boundary_status": claim["status"],
        "no_mutation_status": mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PENDING",
        "frozen_truth_summary": frozen_truth_summary,
        "limitations": LIMITATIONS,
        "recommended_next_task": RECOMMENDED_NEXT_TASK,
        "parallel_next_candidates": PARALLEL_NEXT_CANDIDATES,
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(Path(__file__).resolve()),
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_DECISION.json", decision)
    final_manifest = hash_manifest()
    hash_report = write_hash_validation_report(upstream_hashes, final_manifest["status"])
    decision["hash_validation_status"] = hash_report["status"]
    if hash_report["status"] != "PASS":
        decision["status"] = FAIL_STATUS
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_DECISION.json", decision)
    final_manifest = hash_manifest()
    hash_report = write_hash_validation_report(upstream_hashes, final_manifest["status"])
    if hash_report["status"] != decision["hash_validation_status"]:
        decision["hash_validation_status"] = hash_report["status"]
        if hash_report["status"] != "PASS":
            decision["status"] = FAIL_STATUS
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_DECISION.json", decision)
        hash_manifest()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
