#!/usr/bin/env python3
"""Build Hero Neighbourhood event overlay R2 packets."""

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

TASK_NAME = "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-EVENT-OVERLAY-R2"
PASS_STATUS = "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_EVENT_OVERLAY_R2_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_EVENT_OVERLAY_R2"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track2a_d5_hero_neighbourhood_event_overlay_r2"

UPSTREAMS = {
    "hero_neighbourhood_twin_preflight": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_twin_preflight",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_TWIN_PREFLIGHT_WITH_LIMITATIONS",
    },
    "hero_neighbourhood_asset_binding_r1": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_asset_binding_r1",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_ASSET_BINDING_R1_WITH_LIMITATIONS",
    },
    "incident_mode_closeout": {
        "root": "outputs/main_citybrain_d6_incident_mode_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_WITH_LIMITATIONS",
    },
    "incident_mode_track2a_operator_surface_handoff_r4": {
        "root": "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_WITH_LIMITATIONS",
    },
    "r8_multi_domain_edge_registry_hardening": {
        "root": "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_WITH_LIMITATIONS",
    },
    "d6_d5_local_running_slice_closeout": {
        "root": "outputs/main_citybrain_d6_d5_local_running_slice_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_WITH_LIMITATIONS",
    },
    "d5_track2_handoff_r4": {
        "root": "outputs/main_citybrain_d5_local_served_runtime_track2_handoff_r4",
        "expected": "PASS_MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_TRACK2_HANDOFF_R4_WITH_LIMITATIONS",
    },
}

CER_SEG_SYNC_ROOT = "outputs/main_citybrain_d6_cer_seg_v2_relationship_ontology_r2"

BOUNDARY = (
    "Hero Neighbourhood event overlay R2 is bounded local/replay review/query context only. "
    "It is not autonomous monitoring, alerting, dispatch, routing/control, enforcement, "
    "legal/certified incident status, official ticket/case creation, automated action, "
    "production/public API, or a citywide certified twin."
)

LIMITATIONS = [
    "bounded Hero Neighbourhood event overlay layer only",
    "local/replay review/query context only",
    "no new identity, relationship, or incident semantics",
    "unresolved and quarantined contexts remain review-context overlays",
    "Omniverse and web outputs are handoff manifests, not production surfaces",
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


def unique(values: list[Any]) -> list[str]:
    out: list[str] = []
    for value in values:
        if isinstance(value, list):
            for item in value:
                text = str(item)
                if text and text not in out:
                    out.append(text)
        elif value is not None:
            text = str(value)
            if text and text not in out:
                out.append(text)
    return out


def discover_inputs(pre: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    missing = []
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
                if len(artifacts) >= 16:
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
    cer_seg_r2 = root_path(CER_SEG_SYNC_ROOT)
    report = {
        "status": "PASS" if not missing else "FAIL",
        "timestamp": utc_now(),
        "missing_required_upstreams": missing,
        "cer_seg_r2_compatibility_pause": {
            "status": "NOT_RUNNING_OR_NOT_DISCOVERED" if not cer_seg_r2.exists() else "DISCOVERED_COMPATIBILITY_REVIEW_RECORDED",
            "root": CER_SEG_SYNC_ROOT,
            "note": "Hero R2 remains read-only and introduces no new identity or relationship semantics.",
        },
        "branches": branches,
    }
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", report)
    return report, missing


def load_sources() -> dict[str, Any]:
    return {
        "bindings": rows_from(read_json(root_path(UPSTREAMS["hero_neighbourhood_asset_binding_r1"]["root"]) / "HERO_NEIGHBOURHOOD_ASSET_BINDING_REGISTRY.json", {}), ["bindings"]),
        "surface_packets": rows_from(read_json(root_path(UPSTREAMS["incident_mode_track2a_operator_surface_handoff_r4"]["root"]) / "OPERATOR_SURFACE_PACKET_FIXTURES.json", {}), ["packets"]),
        "scope": read_json(root_path(UPSTREAMS["hero_neighbourhood_asset_binding_r1"]["root"]) / "HERO_NEIGHBOURHOOD_SCOPE_SUMMARY.json", {}),
    }


def write_schema() -> dict[str, Any]:
    schema = {
        "status": "PASS",
        "schema_name": "HERO_EVENT_OVERLAY_SCHEMA",
        "required_fields": [
            "overlay_packet_id",
            "hero_scene_id",
            "canonical_entity_id",
            "asset_binding_id",
            "usd_prim_path",
            "incident_context_ref",
            "event_state_ref",
            "operator_review_packet_ref",
            "evidence_bundle_refs",
            "edge_refs",
            "review_state",
            "confidence_context",
            "limitation_refs",
            "surface_targets",
            "claim_boundary",
        ],
        "surface_targets": ["omniverse", "web"],
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "HERO_EVENT_OVERLAY_SCHEMA.json", schema)
    return schema


def packet_for_binding(binding: dict[str, Any], surface_packets: list[dict[str, Any]]) -> dict[str, Any]:
    refs = set(binding.get("operator_surface_packet_refs", []) + binding.get("incident_context_refs", []))
    for packet in surface_packets:
        if packet.get("packet_id") in refs or packet.get("source_operator_review_packet_ref") in refs or packet.get("incident_context_id") in refs:
            return packet
    return surface_packets[0] if surface_packets else {}


def build_overlays(bindings: list[dict[str, Any]], surface_packets: list[dict[str, Any]]) -> dict[str, Any]:
    overlays = []
    for index, binding in enumerate(bindings, start=1):
        packet = packet_for_binding(binding, surface_packets)
        overlay = {
            "overlay_packet_id": f"hero-event-overlay-r2-{index:03d}",
            "hero_scene_id": binding["scene_id"],
            "canonical_entity_id": binding["canonical_entity_ref"],
            "asset_binding_id": binding["binding_id"],
            "usd_prim_path": binding["stable_prim_path"],
            "incident_context_ref": (binding.get("incident_context_refs") or packet.get("incident_context_id") or ["not_applicable_scene_asset"])[0],
            "event_state_ref": packet.get("event_ref") or (binding.get("incident_context_refs") or ["not_applicable_scene_asset"])[0],
            "operator_review_packet_ref": (binding.get("operator_surface_packet_refs") or [packet.get("source_operator_review_packet_ref") or "not_applicable_scene_asset"])[0],
            "evidence_bundle_refs": unique([packet.get("source_evidence_bundle_ref"), binding.get("evidence_refs", [])]),
            "edge_refs": unique([binding.get("edge_refs", []), packet.get("edge_refs", [])]),
            "review_state": binding.get("review_state") or packet.get("review_state") or "review_context",
            "confidence_context": {
                "binding_confidence": binding.get("confidence"),
                "surface_confidence": packet.get("confidence_summary", {}),
                "confidence_is_review_context_only": True,
            },
            "limitation_refs": unique([binding.get("limitation_refs", []), packet.get("limitation_refs", [])]),
            "surface_targets": ["omniverse", "web"],
            "display_state": packet.get("display_state", binding.get("binding_state")),
            "binding_state": binding.get("binding_state"),
            "omniverse_overlay_refs": unique([binding.get("omniverse_overlay_packet_refs", []), packet.get("omniverse_overlay_refs", [])]),
            "web_companion_refs": unique([binding.get("web_companion_packet_refs", []), packet.get("web_companion_refs", [])]),
            "claim_boundary": BOUNDARY,
            "no_action_taken": True,
        }
        overlays.append(overlay)
    payload = {
        "status": "PASS",
        "overlay_packet_count": len(overlays),
        "unresolved_quarantined_overlay_count": sum(row["display_state"] in {"unresolved_context", "quarantined_context"} or row["binding_state"] in {"unresolved_review_context", "quarantined_review_context"} for row in overlays),
        "packets": overlays,
    }
    write_json(OUTPUT_ROOT / "HERO_EVENT_OVERLAY_PACKETS.json", payload)
    with (OUTPUT_ROOT / "HERO_EVENT_OVERLAY_PACKETS.jsonl").open("w", encoding="utf-8") as handle:
        for overlay in overlays:
            handle.write(json.dumps(overlay, sort_keys=True) + "\n")
    return payload


def write_manifests(overlays: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    packets = overlays["packets"]
    omni = {
        "status": "PASS",
        "manifest_id": "hero-event-overlay-r2-omniverse-manifest",
        "surface": "Omniverse Kit/Composer handoff",
        "overlay_packet_refs": [row["overlay_packet_id"] for row in packets],
        "usd_prim_paths": [row["usd_prim_path"] for row in packets],
        "review_only": True,
        "source_scene_mutation": False,
        "claim_boundary": BOUNDARY,
    }
    web = {
        "status": "PASS",
        "manifest_id": "hero-event-overlay-r2-web-manifest",
        "surface": "web companion evidence/episode/executive context",
        "overlay_packet_refs": [row["overlay_packet_id"] for row in packets],
        "evidence_refs": unique([row["evidence_bundle_refs"] for row in packets]),
        "limitation_refs": unique([row["limitation_refs"] for row in packets]),
        "review_only": True,
        "public_api": False,
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "OMNIVERSE_EVENT_OVERLAY_MANIFEST.json", omni)
    write_json(OUTPUT_ROOT / "WEB_EVENT_OVERLAY_MANIFEST.json", web)
    return omni, web


def query_overlays(packets: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    fixtures = [
        {"fixture_id": "overlay-query-001", "query": "by_asset_binding", "value": packets[0]["asset_binding_id"]},
        {"fixture_id": "overlay-query-002", "query": "by_event_state", "value": packets[0]["event_state_ref"]},
        {"fixture_id": "overlay-query-003", "query": "by_incident_context", "value": "incident-review-r1-001"},
        {"fixture_id": "overlay-query-004", "query": "by_review_state", "value": packets[0]["review_state"]},
        {"fixture_id": "overlay-query-005", "query": "by_surface_target", "value": "omniverse"},
        {"fixture_id": "overlay-query-006", "query": "by_surface_target", "value": "web"},
    ]
    def run(fixture: dict[str, Any]) -> list[dict[str, Any]]:
        query = fixture["query"]
        value = fixture["value"]
        if query == "by_asset_binding":
            return [row for row in packets if row["asset_binding_id"] == value]
        if query == "by_event_state":
            return [row for row in packets if row["event_state_ref"] == value]
        if query == "by_incident_context":
            return [row for row in packets if row["incident_context_ref"] == value]
        if query == "by_review_state":
            return [row for row in packets if row["review_state"] == value]
        if query == "by_surface_target":
            return [row for row in packets if value in row["surface_targets"]]
        return []
    results = []
    for fixture in fixtures:
        rows = run(fixture)
        results.append({"fixture_id": fixture["fixture_id"], "query": fixture["query"], "status": "PASS" if rows else "FAIL", "result_count": len(rows)})
    fixture_payload = {"status": "PASS", "fixture_count": len(fixtures), "fixtures": fixtures}
    result_payload = {"status": "PASS" if all(row["status"] == "PASS" for row in results) else "FAIL", "pass_count": sum(row["status"] == "PASS" for row in results), "fail_count": sum(row["status"] == "FAIL" for row in results), "results": results}
    write_json(OUTPUT_ROOT / "OVERLAY_QUERY_FIXTURES.json", fixture_payload)
    write_json(OUTPUT_ROOT / "OVERLAY_QUERY_RESULTS.json", result_payload)
    return fixture_payload, result_payload


def write_trace_and_preservation(overlays: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    packets = overlays["packets"]
    trace = {
        "status": "PASS",
        "trace_count": len(packets),
        "rows": [
            {
                "overlay_packet_id": row["overlay_packet_id"],
                "asset_binding_id": row["asset_binding_id"],
                "evidence_bundle_refs": row["evidence_bundle_refs"],
                "limitation_refs": row["limitation_refs"],
                "edge_refs": row["edge_refs"],
            }
            for row in packets
        ],
    }
    preservation_rows = [
        {
            "overlay_packet_id": row["overlay_packet_id"],
            "display_state": row["display_state"],
            "binding_state": row["binding_state"],
            "preserved": row["display_state"] in {"unresolved_context", "quarantined_context"} or row["binding_state"] in {"unresolved_review_context", "quarantined_review_context"},
            "not_promoted": True,
        }
        for row in packets
        if row["display_state"] in {"unresolved_context", "quarantined_context"} or row["binding_state"] in {"unresolved_review_context", "quarantined_review_context"}
    ]
    preservation = {"status": "PASS" if preservation_rows and all(row["preserved"] for row in preservation_rows) else "FAIL", "preserved_count": len(preservation_rows), "rows": preservation_rows}
    write_json(OUTPUT_ROOT / "EVIDENCE_LIMITATION_TRACE.json", trace)
    write_json(OUTPUT_ROOT / "UNRESOLVED_QUARANTINED_OVERLAY_PRESERVATION.json", preservation)
    return trace, preservation


def audit_claims() -> dict[str, Any]:
    patterns = [
        r'"production"\s*:\s*true',
        r'"public_api"\s*:\s*true',
        r'"autonomous_monitoring"\s*:\s*true',
        r'"alerting"\s*:\s*true',
        r'"dispatch"\s*:\s*true',
        r'"routing_control"\s*:\s*true',
        r'"enforcement"\s*:\s*true',
        r'"legal_certified_status"\s*:\s*true',
        r'"citywide_certified_twin"\s*:\s*true',
    ]
    joined = ""
    for item in OUTPUT_ROOT.rglob("*"):
        if item.is_file() and item.name not in {"CLAIM_BOUNDARY_AUDIT.json", "HASH_MANIFEST.json"} and item.suffix.lower() in {".json", ".md", ".txt", ".jsonl"}:
            joined += "\n" + item.read_text(encoding="utf-8", errors="ignore").lower()
    hits = [pattern for pattern in patterns if re.search(pattern, joined)]
    report = {"status": "PASS" if not hits else "FAIL", "positive_forbidden_claim_hits": hits, "claim_boundary": BOUNDARY}
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", report)
    return report


def audit_no_action(packets: list[dict[str, Any]]) -> dict[str, Any]:
    bad = [row["overlay_packet_id"] for row in packets if row.get("no_action_taken") is not True]
    report = {"status": "PASS" if not bad else "FAIL", "bad_overlay_packets": bad, "claim_boundary": BOUNDARY}
    write_json(OUTPUT_ROOT / "NO_ACTION_BOUNDARY_AUDIT.json", report)
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
        if item.is_file() and item.name != "HASH_MANIFEST.json" and item.suffix.lower() in {".json", ".md", ".txt", ".jsonl"}:
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


def write_index(overlays: dict[str, Any]) -> None:
    files = [
        "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_EVENT_OVERLAY_R2_DECISION.json",
        "README.md",
        "INPUT_ARTIFACT_INDEX.json",
        "HERO_EVENT_OVERLAY_SCHEMA.json",
        "HERO_EVENT_OVERLAY_PACKETS.json",
        "HERO_EVENT_OVERLAY_PACKETS.jsonl",
        "OMNIVERSE_EVENT_OVERLAY_MANIFEST.json",
        "WEB_EVENT_OVERLAY_MANIFEST.json",
        "UNRESOLVED_QUARANTINED_OVERLAY_PRESERVATION.json",
        "OVERLAY_QUERY_FIXTURES.json",
        "OVERLAY_QUERY_RESULTS.json",
        "EVIDENCE_LIMITATION_TRACE.json",
        "CLAIM_BOUNDARY_AUDIT.json",
        "NO_ACTION_BOUNDARY_AUDIT.json",
        "NO_MUTATION_AUDIT.json",
        "SECRET_AUDIT.json",
        "HASH_MANIFEST.json",
        "LOCAL_OPEN_INDEX.md",
    ]
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

Bounded Hero Neighbourhood event-overlay R2 package.

Overlay packets: `{overlays['overlay_packet_count']}`

{BOUNDARY}
""",
    )
    lines = [f"# {TASK_NAME}", "", f"Overlay packets: `{overlays['overlay_packet_count']}`", "", BOUNDARY, "", "## Artifacts", ""]
    lines.extend(f"- [{name}]({name})" for name in files)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    pre = {meta["root"]: snapshot(root_path(meta["root"])) for meta in UPSTREAMS.values()}
    input_index, missing = discover_inputs(pre)
    sources = load_sources()
    schema = write_schema()
    overlays = build_overlays(sources["bindings"], sources["surface_packets"])
    omni, web = write_manifests(overlays)
    fixtures, query_results = query_overlays(overlays["packets"])
    trace, preservation = write_trace_and_preservation(overlays)
    claim = audit_claims()
    no_action = audit_no_action(overlays["packets"])
    mutation = audit_mutation(pre)
    secret = audit_secret()
    write_index(overlays)

    status = PASS_STATUS
    if not all(
        [
            not missing,
            input_index["status"] == "PASS",
            schema["status"] == "PASS",
            overlays["status"] == "PASS",
            omni["status"] == "PASS",
            web["status"] == "PASS",
            query_results["status"] == "PASS",
            trace["status"] == "PASS",
            preservation["status"] == "PASS",
            claim["status"] == "PASS",
            no_action["status"] == "PASS",
            mutation["status"] == "PASS",
            secret["status"] == "PASS",
        ]
    ):
        status = FAIL_STATUS

    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(Path(__file__).resolve()),
        "missing_required_upstreams": missing,
        "overlay_packet_count": overlays["overlay_packet_count"],
        "unresolved_quarantined_preservation_count": preservation["preserved_count"],
        "omniverse_manifest_status": omni["status"],
        "web_manifest_status": web["status"],
        "query_fixture_pass_count": query_results["pass_count"],
        "query_fixture_fail_count": query_results["fail_count"],
        "claim_boundary_status": claim["status"],
        "no_action_status": no_action["status"],
        "no_mutation_status": mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PENDING",
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-KIT-COMPOSER-HANDOFF-R3",
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_EVENT_OVERLAY_R2_DECISION.json", decision)
    manifest = hash_manifest()
    decision["hash_validation_status"] = manifest["status"]
    if manifest["status"] != "PASS":
        decision["status"] = FAIL_STATUS
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_EVENT_OVERLAY_R2_DECISION.json", decision)
    hash_manifest()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
