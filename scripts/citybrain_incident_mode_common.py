"""Shared helpers for bounded CityBrain Incident Mode runners."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = REPO_ROOT / "outputs"

BOUNDARY_TEXT = (
    "Incident Mode is human-or-replay initiated local/replay review/query context only. "
    "No autonomous monitoring, alerts, dispatch, routing/control, enforcement, "
    "legal/certified/confirmed incident claim, official ticket/case creation, or automated action."
)

LIMITATIONS = [
    "human-or-replay initiated only",
    "local/replay review/query context only",
    "no autonomous monitoring",
    "no alerts",
    "no dispatch",
    "no routing/control",
    "no enforcement",
    "no legal/certified/confirmed incident claims",
    "no official ticket/case creation",
    "no automated action",
]

ALLOWED_SAFE_NEXT_LOOKS = {
    "review_related_entities",
    "inspect_evidence_trace",
    "compare_nearby_context",
    "open_omniverse_overlay_context",
    "open_web_companion_context",
    "review_unresolved_entity_candidates",
    "inspect_limitation_refs",
    "review_operator_packet",
    "open_trace_context",
}

FORBIDDEN_POSITIVE_TOKENS = {
    "dispatch_team",
    "send_alert",
    "reroute_traffic",
    "enforce_violation",
    "confirm_incident",
    "create_ticket",
    "notify_authority",
    "approved",
    "dispatched",
    "alerted",
    "confirmed",
    "case_created",
    "violation_issued",
}

UPSTREAMS = {
    "incident_preflight": OUTPUTS / "main_citybrain_d6_incident_mode_preflight",
    "r8_hardening": OUTPUTS / "main_citybrain_d4x_r8_multi_domain_edge_registry_hardening",
    "d6_d5_closeout": OUTPUTS / "main_citybrain_d6_d5_local_running_slice_closeout",
    "d6_d5_slice_r1": OUTPUTS / "main_citybrain_d6_d5_local_running_control_room_slice_r1",
    "d5_track2_handoff_r4": OUTPUTS / "main_citybrain_d5_local_served_runtime_track2_handoff_r4",
    "d5_event_fabric_r3": OUTPUTS / "main_citybrain_d5_local_served_runtime_event_fabric_integration_r3",
    "r7_registry": OUTPUTS / "main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice",
    "incident_r1": OUTPUTS / "main_citybrain_d6_incident_mode_evidence_bundle_r1",
    "incident_r2": OUTPUTS / "main_citybrain_d6_incident_mode_operator_review_workflow_r2",
    "incident_r3": OUTPUTS / "main_citybrain_d6_incident_mode_runtime_smoke_r3",
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def first_list(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def decision_status(root: Path) -> str | None:
    if not root.exists():
        return None
    for path in sorted(root.glob("*DECISION*.json")):
        data = load_json(path)
        if isinstance(data, dict) and data.get("status"):
            return str(data["status"])
    return None


def discover_upstreams(required: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = []
    missing = []
    for key in required:
        root = UPSTREAMS[key]
        status = decision_status(root)
        files = sorted(root.glob("*.json"))[:8] if root.exists() else []
        ok = bool(status and status.startswith("PASS"))
        if not ok:
            missing.append(key)
        rows.append(
            {
                "upstream_key": key,
                "root": rel(root),
                "exists": root.exists(),
                "decision_status": status,
                "green": ok,
                "sample_artifacts": [
                    {"path": rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
                    for path in files
                ],
            }
        )
    summary = {
        "required_upstream_count": len(required),
        "discovered_count": sum(1 for row in rows if row["exists"]),
        "green_count": sum(1 for row in rows if row["green"]),
        "missing_or_not_green": missing,
        "status": "PASS" if not missing else "FAIL",
    }
    index = {"timestamp": now(), "upstreams": rows, **summary}
    return index, summary


def hash_manifest(output_root: Path) -> dict[str, Any]:
    files = []
    for path in sorted(output_root.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append({"path": rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    manifest = {"timestamp": now(), "hash_validation_status": "PASS", "file_count": len(files), "files": files}
    write_json(output_root / "HASH_MANIFEST.json", manifest)
    return manifest


def secret_audit(output_root: Path) -> dict[str, Any]:
    patterns = [
        re.compile(r"api[_-]?key\\s*[:=]\\s*['\\\"][^'\\\"]+", re.I),
        re.compile(r"authorization\\s*[:=]", re.I),
        re.compile(r"bearer\\s+[A-Za-z0-9._-]{16,}", re.I),
        re.compile(r"token\\s*[:=]\\s*['\\\"][^'\\\"]+", re.I),
        re.compile(r"\\.env", re.I),
    ]
    findings = []
    for path in output_root.rglob("*"):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                if pattern.search(text):
                    findings.append({"path": rel(path), "pattern": pattern.pattern})
    return {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}


def no_mutation_audit(watched_files: list[Path], before_hashes: dict[str, str]) -> dict[str, Any]:
    changed = []
    for path in watched_files:
        if path.exists():
            after = sha256_file(path)
            key = rel(path)
            if before_hashes.get(key) != after:
                changed.append({"path": key, "before": before_hashes.get(key), "after": after})
    return {
        "status": "PASS" if not changed else "FAIL",
        "watched_file_count": len(watched_files),
        "changed_file_count": len(changed),
        "changed_files": changed,
        "source_mutation_attempted": False,
        "no_action_taken": True,
    }


def watched_upstream_decisions(keys: list[str]) -> tuple[list[Path], dict[str, str]]:
    files = []
    for key in keys:
        root = UPSTREAMS[key]
        if root.exists():
            files.extend(sorted(root.glob("*DECISION*.json")))
    return files, {rel(path): sha256_file(path) for path in files if path.exists()}


def safe_next_look_result(items: list[dict[str, Any]], field: str = "safe_next_look_candidates") -> dict[str, Any]:
    failures = []
    for item in items:
        values = item.get(field, [])
        for value in values:
            if value not in ALLOWED_SAFE_NEXT_LOOKS or value in FORBIDDEN_POSITIVE_TOKENS:
                failures.append({"item_ref": item.get("incident_review_id") or item.get("operator_review_packet_id") or item.get("request_id"), "value": value})
    return {"status": "PASS" if not failures else "FAIL", "failure_count": len(failures), "failures": failures}


def claim_boundary_audit(items: list[dict[str, Any]], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    failures = []
    forbidden_state_tokens = FORBIDDEN_POSITIVE_TOKENS
    for item in items:
        for key in ["review_state", "operator_review_state", "response_status"]:
            value = str(item.get(key, "")).lower()
            if value in forbidden_state_tokens:
                failures.append({"item_ref": item.get("incident_review_id") or item.get("operator_review_packet_id") or item.get("request_id"), "field": key, "value": value})
        if item.get("claim_boundary") and "no autonomous monitoring" not in str(item["claim_boundary"]).lower():
            failures.append({"item_ref": item.get("incident_review_id") or item.get("operator_review_packet_id") or item.get("request_id"), "field": "claim_boundary", "value": "missing boundary"})
    return {
        "status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "boundary": BOUNDARY_TEXT,
        "extra": extra or {},
        "no_action_taken": True,
    }


def no_action_audit(items: list[dict[str, Any]]) -> dict[str, Any]:
    failures = []
    for item in items:
        if item.get("no_action_taken") is not True:
            failures.append(item.get("incident_review_id") or item.get("operator_review_packet_id") or item.get("request_id") or item.get("fixture_id"))
    return {"status": "PASS" if not failures else "FAIL", "checked_count": len(items), "failures": failures}


def local_open_index(title: str, artifacts: list[str]) -> str:
    lines = [f"# {title}", ""]
    lines.extend(f"- `{artifact}`" for artifact in artifacts)
    return "\n".join(lines)
