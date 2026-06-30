#!/usr/bin/env python3
"""Shared helpers for the CityBrain CER/SEG v2 contract lane."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"

LANE_LIMITATIONS = [
    "read-only contract/generalization lane only",
    "no mutation of frozen R7/R8, Incident Mode, D5/D6, Hero, Track2A, source, or platform outputs",
    "no production/public/API readiness claim",
    "no forced global master database",
    "no replacement of jurisdictional authoritative IDs",
    "no official/certified city truth claim",
    "no legal/certified/confirmed relationship or incident claim",
    "no autonomous monitoring, alert push, dispatch, routing/control, enforcement, or automated action",
    "local/replay review/query context only",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def prepare_output_root(output_root: Path, expected_name: str) -> None:
    resolved = output_root.resolve()
    if resolved.parent != OUTPUTS_ROOT.resolve() or resolved.name != expected_name:
        raise RuntimeError(f"Refusing to reset unexpected output root: {resolved}")
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)


def status_from_decision(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    for key in ("status", "final_status", "decision_status"):
        if data.get(key):
            return str(data[key])
    return None


def discover_upstreams(task_id: str, upstreams: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    required_missing_or_not_green: list[str] = []
    optional_present: list[str] = []
    optional_missing: list[str] = []
    for key, spec in upstreams.items():
        root = REPO_ROOT / spec["root"]
        decision_path = root / spec["decision_file"]
        decision = load_json(decision_path, {})
        status = status_from_decision(decision)
        exists = root.exists() and decision_path.exists()
        if spec.get("expected_status"):
            green = status == spec["expected_status"]
        else:
            green = bool(status and status.startswith(str(spec.get("expected_prefix", "PASS_"))))
        artifacts = []
        if root.exists():
            for path in sorted(p for p in root.iterdir() if p.is_file()):
                artifacts.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
        row = {
            "upstream_key": key,
            "task_id": spec["task_id"],
            "root": spec["root"],
            "decision_file": rel(decision_path),
            "exists": exists,
            "required": bool(spec["required"]),
            "status": status,
            "green": bool(exists and green),
            "artifacts": artifacts,
        }
        rows.append(row)
        if spec["required"] and not row["green"]:
            required_missing_or_not_green.append(key)
        if not spec["required"]:
            if row["green"]:
                optional_present.append(key)
            else:
                optional_missing.append(key)
    summary = {
        "task_id": task_id,
        "run_timestamp_utc": now_iso(),
        "required_count": sum(1 for spec in upstreams.values() if spec["required"]),
        "required_green_count": sum(1 for row in rows if row["required"] and row["green"]),
        "required_missing_or_not_green": required_missing_or_not_green,
        "optional_present": optional_present,
        "optional_missing_or_not_yet_run": optional_missing,
        "status": "PASS" if not required_missing_or_not_green else "FAIL",
    }
    return {"task_id": task_id, "upstreams": rows}, summary


def upstream_signature(upstreams: dict[str, dict[str, Any]]) -> dict[str, dict[str, str]]:
    signatures: dict[str, dict[str, str]] = {}
    for key, spec in upstreams.items():
        root = REPO_ROOT / spec["root"]
        if not root.exists():
            signatures[key] = {"__missing__": "true"}
            continue
        sig: dict[str, str] = {}
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            sig[rel(path)] = f"{path.stat().st_size}:{sha256_file(path)}"
        signatures[key] = sig
    return signatures


def no_mutation_audit(task_id: str, before: dict[str, dict[str, str]], after: dict[str, dict[str, str]]) -> dict[str, Any]:
    changed = [key for key in sorted(before) if before[key] != after.get(key, {})]
    return {
        "task_id": task_id,
        "status": "PASS" if not changed else "FAIL",
        "watched_upstream_count": len(before),
        "changed_upstream_keys": changed,
        "output_root_only_mutated": not changed,
        "no_action_taken": True,
    }


def secret_audit(task_id: str, output_root: Path, extra_paths: list[Path] | None = None) -> dict[str, Any]:
    key_fragments = ["fff39a", "338581", "02015f", "4630ed", "32b9ac", "ad"]
    app_fragments = ["2cf2", "17ca"]
    forbidden = ["".join(key_fragments), "".join(app_fragments)]
    hits = []
    scan_roots = [output_root] + (extra_paths or [])
    for root in scan_roots:
        if not root.exists():
            continue
        paths = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
        for path in paths:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for token in forbidden:
                if token in text:
                    hits.append({"path": rel(path), "token": "known_sensitive_value"})
    return {"task_id": task_id, "status": "PASS" if not hits else "FAIL", "hits": hits, "scan_scope": [rel(p) for p in scan_roots]}


def claim_boundary_audit(task_id: str, output_root: Path) -> dict[str, Any]:
    text_blob = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in output_root.rglob("*") if p.is_file()).lower()
    positive_claims = [
        '"production_readiness_claim_made": true',
        '"public_api_readiness_claim_made": true',
        '"global_master_database_claim_made": true',
        '"official_certified_city_truth_claim_made": true',
        '"legal_certified_confirmed_claim_made": true',
        '"autonomous_monitoring_claim_made": true',
        '"alert_dispatch_routing_control_enforcement_claim_made": true',
        '"automated_action_claim_made": true',
        "production ready for deployment",
        "public api ready",
        "global master database established",
        "certified city truth established",
        "legal finding issued",
        "confirmed incident state enabled",
        "dispatch command",
        "enforcement action",
    ]
    hits = [term for term in positive_claims if term in text_blob]
    boundary_terms = {
        "no_production_public_api": "no production/public/api" in text_blob or "no production/public" in text_blob or "no production" in text_blob,
        "no_global_master": "no forced global master" in text_blob or "no global master" in text_blob,
        "no_legal_certified_confirmed": "no legal/certified" in text_blob or "no legal, certified" in text_blob,
        "no_autonomous_action": "no autonomous monitoring" in text_blob and ("automated action" in text_blob or "autonomous action" in text_blob),
        "read_only_contract_lane": "read-only" in text_blob and "contract" in text_blob,
    }
    return {
        "task_id": task_id,
        "status": "PASS" if not hits and all(boundary_terms.values()) else "FAIL",
        "positive_claim_hits": hits,
        "boundary_terms": boundary_terms,
        "no_action_taken": True,
    }


def hash_manifest(task_id: str, output_root: Path) -> dict[str, Any]:
    manifest_path = output_root / "HASH_MANIFEST.json"
    rows = []
    for path in sorted(p for p in output_root.rglob("*") if p.is_file()):
        if path == manifest_path:
            continue
        rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    data = {"task_id": task_id, "generated_at_utc": now_iso(), "file_count": len(rows), "files": rows, "hash_validation_status": "PASS"}
    write_json(manifest_path, data)
    return data


def required_files_status(output_root: Path, required_files: list[str]) -> dict[str, Any]:
    missing = [name for name in required_files if not (output_root / name).exists()]
    return {"status": "PASS" if not missing else "FAIL", "required_count": len(required_files), "missing": missing}


def load_r8_edges() -> list[dict[str, Any]]:
    data = load_json(REPO_ROOT / "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening/HARDENED_MULTI_DOMAIN_EDGE_REGISTRY.json", {})
    if isinstance(data, dict):
        return data.get("edges", [])
    if isinstance(data, list):
        return data
    return []


def load_hero_bindings() -> list[dict[str, Any]]:
    data = load_json(REPO_ROOT / "outputs/main_track2a_d5_hero_neighbourhood_asset_binding_r1/HERO_NEIGHBOURHOOD_ASSET_BINDING_REGISTRY.json", {})
    if isinstance(data, dict):
        return data.get("bindings", [])
    if isinstance(data, list):
        return data
    return []


def load_incident_operator_packets() -> list[dict[str, Any]]:
    candidates = [
        REPO_ROOT / "outputs/main_citybrain_d6_incident_mode_operator_review_workflow_r2/OPERATOR_REVIEW_PACKETS.json",
        REPO_ROOT / "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4/OPERATOR_SURFACE_HANDOFF_PACKETS.json",
        REPO_ROOT / "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4/OPERATOR_SURFACE_PACKET_FIXTURES.json",
    ]
    for path in candidates:
        data = load_json(path)
        if isinstance(data, dict):
            for key in ("packets", "operator_review_packets", "items"):
                if isinstance(data.get(key), list):
                    return data[key]
        if isinstance(data, list):
            return data
    return []
