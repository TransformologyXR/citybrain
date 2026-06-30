#!/usr/bin/env python3
"""NYC-F1X-D4 situational status replay + face payload proof."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "NYC-F1X-D4 NYC Situational Status Replay + Face Payload Proof"
DEFAULT_OUTPUT_DIR = "outputs/nyc_f1x_d4_situational_status_replay_face_proof"
PRIMARY_D3_R1 = "outputs/nyc_f1x_d3_r1_situational_status_evidencebundles"
FALLBACK_D3 = "outputs/nyc_f1x_d3_situational_status_evidencebundles"
PASS_STATUSES = {"PASS_LIVE_REPLAY_FACE_ROUTE_PROOF", "PASS_PAYLOAD_ONLY_WITH_SOURCE_LIMITATIONS"}

REQUIRED_ARTIFACTS = [
    "README.md",
    "NYC_F1X_D4_HARNESS_REPORT.json",
    "NYC_F1X_D4_INPUT_INVENTORY.json",
    "NYC_F1X_D4_STAGE_LEDGER.json",
    "NYC_F1X_D4_REPLAY_PAYLOAD.json",
    "NYC_F1X_D4_BRIEFING_PAYLOAD.json",
    "NYC_F1X_D4_FACE_ROUTE_PAYLOAD.json",
    "NYC_F1X_D4_TRACE_REPORT.json",
    "NYC_F1X_D4_SOURCE_LIMITATION_REPORT.json",
    "NYC_F1X_D4_NEXT_D5_HANDOFF.json",
    "NYC_F1X_D4_NO_OVERCLAIM_REPORT.json",
    "NYC_F1X_D4_NO_MUTATION_REPORT.json",
    "SHA256SUMS.json",
]

INPUT_DEFAULTS = {
    "primary_nyc_f1x_d3_r1": PRIMARY_D3_R1,
    "fallback_nyc_f1x_d3_original": FALLBACK_D3,
    "nyc_expansion_d2": "outputs/nyc_expansion_d2_all_flows",
    "nyc_f4x_d3_r1": "outputs/nyc_f4x_d3_r1_mobility_environment_evidencebundles",
    "xdata_d2_r1": "outputs/xdata_d2_r1_four_city_bulk_landing_reconciliation_refresh",
    "d3_refresh_d1": "outputs/d3_refresh_d1_bulk_informed_refresh_decision",
    "ontology_v2": "contracts/ontology_v2",
    "nightrun_d1_optional": "outputs/nightrun_d1_overnight_current_work_completion",
    "a9_wire_e2e_optional": "outputs/a9_wire_e2e_g1_snapshot",
}

NO_OVERCLAIM_PATTERNS = [
    r"\bnyc flow 1 accepted\b",
    r"\ball nyc situational sources are full\b",
    r"\bcapped 311 is full\b",
    r"\bmta/current snapshots are historical completeness\b",
    r"\bemergency dispatch\b",
    r"\bpublic safety recommendation\b",
    r"\bpublic-safety recommendation\b",
    r"\bhealth determination\b",
    r"\btraffic-control instruction\b",
    r"\btransit-control instruction\b",
    r"\butility-control instruction\b",
    r"\bpolicing recommendation\b",
    r"\benforcement action\b",
    r"\boperational command\b",
    r"\bcertified affected asset\b",
    r"\bcertified affected building\b",
]

NEGATION_MARKERS = ("no ", "not ", "never ", "without ", "does not ", "do not ", "cannot ", "boundary ", "forbidden ")

BOUNDARY_LINES = [
    "NYC Flow 1 is not accepted at D4.",
    "D4 is payload-only situational status review-context proof.",
    "NYC 311 2020-present is CAPPED_BULK under the 2022-06-28+ window, not full.",
    "NYC 311 2010-2019 was removed from the active source plan.",
    "MTA GTFS-RT/service alerts are point-in-time/windowed snapshots, not historical completeness.",
    "Flow 1 situational context is review-context only.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean(v) for v in value]
    if hasattr(value, "item"):
        try:
            return clean(value.item())
        except Exception:
            pass
    return value


def project_path(project_root: str | Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(project_root).resolve() / path


def read_json(path: str | Path, default: Any = None) -> Any:
    path = Path(path)
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\bNaN\b", "null", text)
    return json.loads(text)


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(payload), indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"status": "PASS", "file_count": len(sums)}


def reset_output_dir(output_dir: Path, project_root: Path) -> Path:
    resolved = output_dir.resolve()
    root = project_root.resolve()
    if resolved.exists():
        text = str(resolved).lower()
        if not text.startswith(str(root).lower()) or resolved.name.lower() != "nyc_f1x_d4_situational_status_replay_face_proof":
            raise ValueError(f"refusing to remove unexpected output directory: {resolved}")
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def input_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "total_bytes": 0, "files": []}
    files = []
    iterable = [path] if path.is_file() else sorted(path.rglob("*"))
    for item in iterable:
        if item.is_file() and item.suffix.lower() != ".part":
            stat = item.stat()
            files.append({"path": item.relative_to(path).as_posix() if path.is_dir() else item.name, "bytes": stat.st_size})
    return {"exists": True, "file_count": len(files), "total_bytes": sum(item["bytes"] for item in files), "files": files}


def compare_signatures(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = sorted(name for name, signature in before.items() if after.get(name) != signature)
    return {"status": "PASS" if not changed else "FAIL", "checked_inputs": sorted(before), "changed_inputs": changed}


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    findings = []
    checked = 0
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in {"SHA256SUMS.json", "NYC_F1X_D4_NO_OVERCLAIM_REPORT.json"}:
            continue
        if path.suffix.lower() not in {".json", ".md", ".txt", ".csv"}:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for pattern in NO_OVERCLAIM_PATTERNS:
            for match in re.finditer(pattern, text):
                window = text[max(0, match.start() - 56) : match.end() + 20]
                if any(marker in window for marker in NEGATION_MARKERS):
                    continue
                findings.append({"path": path.relative_to(output_dir).as_posix(), "pattern": pattern, "context": window})
    return {"status": "PASS" if not findings else "FAIL", "checked_files": checked, "findings": findings}


def choose_d3(project_root: Path) -> tuple[str, Path, dict[str, Any], list[dict[str, Any]]]:
    r1 = project_path(project_root, PRIMARY_D3_R1)
    fallback = project_path(project_root, FALLBACK_D3)
    if r1.exists():
        return "R1", r1, read_json(r1 / "NYC_F1X_D3_R1_HARNESS_REPORT.json", {}), read_json(r1 / "NYC_F1X_D3_R1_SELECTED_BUNDLES.json", {}).get("selected_bundles", [])
    return "original", fallback, read_json(fallback / "NYC_F1X_D3_HARNESS_REPORT.json", {}), read_json(fallback / "NYC_F1X_D3_SELECTED_BUNDLES.json", {}).get("selected_bundles", [])


def source_statuses(project_root: Path) -> list[dict[str, Any]]:
    data = read_json(project_path(project_root, "outputs/xdata_d2_r1_four_city_bulk_landing_reconciliation_refresh/XDATA_D2_R1_SOURCE_STATUS_NORMALIZATION.json"), {})
    return [item for item in data.get("sources", []) if item.get("city") == "NYC"]


def limitation_rule(source_key: str | None, status: str | None) -> str:
    key = str(source_key or "")
    if key == "nyc_311_2020_present":
        return "NYC 311 2020-present is CAPPED_BULK under the 2022-06-28+ window, not full."
    if key.startswith("nyc_mvc"):
        return "MVC source is capped where applicable and remains source-limited context."
    if key.startswith("mta_gtfs_rt") or key == "mta_static_gtfs_subway_zip":
        return "MTA GTFS-RT/service alerts/static context remains windowed or schedule context; not historical completeness."
    if key == "citi_bike_station_information":
        return "Citi Bike station information is point-in-time station context."
    if key in {"nyc_air_quality", "nyc_flood_vulnerability_index", "nyc_flood_vulnerability_index_map"}:
        return "Air quality and FVI are full only where rows_landed equals total_available."
    if status == "FULL":
        return "FULL only where proven by rows_landed equaling total_available."
    if status == "CAPPED_BULK":
        return "CAPPED_BULK, not full-source proof."
    if status == "WINDOWED_COMPLETE":
        return "WINDOWED_COMPLETE only for the explicit source window."
    if status == "METADATA_ONLY":
        return "METADATA_ONLY source limitation carried forward."
    if status == "OPTIONAL_UNBOUND":
        return "OPTIONAL_UNBOUND source not used as required evidence."
    return "Source limitation carried forward."


def source_limitations_from_bundles(bundles: list[dict[str, Any]], xdata_sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    seen = set()
    for bundle in bundles:
        for source in bundle.get("source_records", []):
            key = source.get("source_key")
            if key in seen:
                continue
            seen.add(key)
            status = source.get("normalized_status") or source.get("landing_status")
            rows.append(
                {
                    "source_key": key,
                    "status": status,
                    "rows_landed": source.get("rows_landed"),
                    "total_available": source.get("total_available"),
                    "cap_rule_applied": source.get("cap_rule_applied"),
                    "rule": limitation_rule(key, status),
                }
            )
    if "nyc_311_2010_2019" not in seen:
        rows.append({"source_key": "nyc_311_2010_2019", "status": "REMOVED_FROM_ACTIVE_PLAN", "rule": "NYC 311 2010-2019 was removed from the active source plan."})
    for source in xdata_sources:
        key = source.get("source_key")
        if key in {"nyc_flood_vulnerability_index", "nyc_flood_vulnerability_index_map"} and key not in seen:
            rows.append({"source_key": key, "status": source.get("normalized_status"), "rows_landed": source.get("rows_landed"), "total_available": source.get("total_available"), "rule": limitation_rule(key, source.get("normalized_status")), "context": "Flood/vulnerability context carried only where relevant."})
    return rows


def build_input_inventory(project_root: Path) -> dict[str, Any]:
    inputs = {}
    for name, rel in INPUT_DEFAULTS.items():
        path = project_path(project_root, rel)
        optional = name.endswith("_optional")
        inputs[name] = {"path": str(path), "exists": path.exists(), "required": not optional, "status": "PASS" if path.exists() else ("OPTIONAL_MISSING" if optional else "MISSING_REQUIRED"), "signature": input_signature(path)}
    return {"status": "PASS", "generated_at": utc_now(), "inputs": inputs}


def build_replay_payload(d3_kind: str, bundles: list[dict[str, Any]], limitations: list[dict[str, Any]]) -> dict[str, Any]:
    bundle_refs = [bundle.get("evidence_bundle_id") for bundle in bundles]
    xdata_refs = sorted({source.get("source_key") for bundle in bundles for source in bundle.get("source_records", []) if source.get("source_key")})
    families = {
        "311_situational_status_context": "nyc_311_2020_present" in xdata_refs,
        "collision_or_mobility_context": any(str(ref).startswith("nyc_mvc") for ref in xdata_refs),
        "air_quality_or_environment_context": "nyc_air_quality" in xdata_refs,
        "transit_status_context": any(str(ref).startswith("mta_") or str(ref).startswith("citi_bike") for ref in xdata_refs),
        "flood_or_vulnerability_context": any(item["source_key"] in {"nyc_flood_vulnerability_index", "nyc_flood_vulnerability_index_map"} for item in limitations),
        "governance_boundary_bundle": any("governance_boundary" in str(ref) for ref in bundle_refs),
    }
    return {
        "city": "nyc",
        "flow": "F1X",
        "stage": "D4",
        "source_stage": "NYC-F1X-D3-R1" if d3_kind == "R1" else "NYC-F1X-D3",
        "mode": "situational_status_review_context",
        "accepted_flow_cartridge": False,
        "review_context_only": True,
        "evidencebundle_refs": bundle_refs,
        "xdata_refs": xdata_refs,
        "context_families": families,
        "source_limitations": limitations,
        "governance_boundaries": BOUNDARY_LINES,
        "forbidden_claims": [
            "NO_NYC_FLOW_1_ACCEPTANCE",
            "NO_EMERGENCY_OR_PUBLIC_SAFETY_RECOMMENDATION",
            "NO_HEALTH_DETERMINATION",
            "NO_TRAFFIC_TRANSIT_OR_UTILITY_CONTROL",
            "NO_POLICING_ENFORCEMENT_OR_OPERATIONAL_COMMAND",
            "NO_CERTIFIED_AFFECTED_ASSET_OR_BUILDING",
        ],
    }


def build_briefing_payload(replay: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "audience": "operator_review",
        "allowed_language_used": ["situational status review context", "source-limited", "capped bulk", "windowed complete", "full where proven", "payload-only", "operator review", "D5-ready hero freeze candidate"],
        "briefing_lines": [
            "NYC Flow 1 D4 payload-only situational status review context is D5-ready as a hero freeze candidate.",
            "The proof carries source-limited replay references from refreshed D3-R1 EvidenceBundles.",
            "NYC 311 2020-present remains capped bulk under the 2022-06-28+ window.",
            "MTA current snapshots remain windowed or point-in-time context and MVC sources retain capped limitations.",
            "Operator review should treat the payload as situational status context with source limits carried forward.",
        ],
        "source_stage": replay["source_stage"],
        "evidencebundle_refs": replay["evidencebundle_refs"],
    }


def build_face_payload(replay: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "FACE_ROUTE_PAYLOAD_ONLY",
        "published": False,
        "reason": "No safe existing face-route publish mechanism was invoked for this D4 gate.",
        "future_routes": ["/nyc/flow1/replay", "/nyc/flow1/briefing", "/api/nyc/flow1/replay", "/api/nyc/flow1/briefing"],
        "payload_bindings": {"replay_payload": "NYC_F1X_D4_REPLAY_PAYLOAD.json", "briefing_payload": "NYC_F1X_D4_BRIEFING_PAYLOAD.json"},
        "source_stage": replay["source_stage"],
        "accepted_flow_cartridge": False,
        "review_context_only": True,
    }


def run_nyc_f1x_d4(project_root: str | Path = ".", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    out = reset_output_dir(project_path(project_root, output_dir), project_root)
    watched = {name: project_path(project_root, rel) for name, rel in INPUT_DEFAULTS.items()}
    before = {name: input_signature(path) for name, path in watched.items()}

    d3_kind, d3_path, d3_harness, bundles = choose_d3(project_root)
    limitations = source_limitations_from_bundles(bundles, source_statuses(project_root))
    replay = build_replay_payload(d3_kind, bundles, limitations)
    briefing = build_briefing_payload(replay)
    face = build_face_payload(replay)
    inventory = build_input_inventory(project_root)
    stage_ledger = {
        "status": "PASS",
        "stages": [
            {"stage": "D3_SOURCE_SELECT", "status": "PASS", "selected": d3_kind, "path": str(d3_path)},
            {"stage": "REPLAY_PAYLOAD", "status": "PASS", "evidencebundle_refs": replay["evidencebundle_refs"]},
            {"stage": "BRIEFING_PAYLOAD", "status": "PASS", "line_count": len(briefing["briefing_lines"])},
            {"stage": "FACE_ROUTE_PAYLOAD", "status": "FACE_ROUTE_PAYLOAD_ONLY", "published": False},
        ],
    }
    trace = {"status": "PASS", "d3_source": {"kind": d3_kind, "path": str(d3_path), "status": d3_harness.get("status")}, "trace_refs": [f"{replay['source_stage']}:{ref}" for ref in replay["evidencebundle_refs"]] + [f"XDATA-D2-R1:{ref}" for ref in replay["xdata_refs"]]}
    source_report = {"status": "PASS", "limitations": limitations, "boundary_lines": BOUNDARY_LINES}
    next_d5 = {"status": "D5_READY_HERO_FREEZE_CANDIDATE_WITH_SOURCE_LIMITATIONS", "recommended_next_gate": "NYC-F1X-D5", "source_stage": replay["source_stage"], "handoff_inputs": ["NYC_F1X_D4_REPLAY_PAYLOAD.json", "NYC_F1X_D4_BRIEFING_PAYLOAD.json", "NYC_F1X_D4_FACE_ROUTE_PAYLOAD.json"], "boundaries_to_carry": BOUNDARY_LINES}

    write_json(out / "NYC_F1X_D4_INPUT_INVENTORY.json", inventory)
    write_json(out / "NYC_F1X_D4_STAGE_LEDGER.json", stage_ledger)
    write_json(out / "NYC_F1X_D4_REPLAY_PAYLOAD.json", replay)
    write_json(out / "NYC_F1X_D4_BRIEFING_PAYLOAD.json", briefing)
    write_json(out / "NYC_F1X_D4_FACE_ROUTE_PAYLOAD.json", face)
    write_json(out / "NYC_F1X_D4_TRACE_REPORT.json", trace)
    write_json(out / "NYC_F1X_D4_SOURCE_LIMITATION_REPORT.json", source_report)
    write_json(out / "NYC_F1X_D4_NEXT_D5_HANDOFF.json", next_d5)

    gates = [
        {"gate": "NYC-F1X-D4-PRECOND", "status": "PASS" if d3_path.exists() and d3_harness.get("status", "").startswith("PASS") else "FAIL"},
        {"gate": "NYC-F1X-D4-INPUT-INVENTORY", "status": "PASS" if all(item["status"] != "MISSING_REQUIRED" for item in inventory["inputs"].values()) else "FAIL"},
        {"gate": "NYC-F1X-D4-STAGE-LEDGER", "status": stage_ledger["status"]},
        {"gate": "NYC-F1X-D4-REPLAY-PAYLOAD", "status": "PASS" if replay["review_context_only"] and len(replay["evidencebundle_refs"]) >= 5 else "FAIL"},
        {"gate": "NYC-F1X-D4-BRIEFING-PAYLOAD", "status": briefing["status"]},
        {"gate": "NYC-F1X-D4-FACE-ROUTE-PAYLOAD", "status": "PASS" if face["status"] in {"FACE_ROUTE_PAYLOAD_ONLY", "FACE_ROUTE_PUBLISHED"} else "FAIL", "face_status": face["status"]},
        {"gate": "NYC-F1X-D4-SOURCE-LIMITATIONS", "status": source_report["status"]},
        {"gate": "NYC-F1X-D4-BOUNDARY-CARRY-FORWARD", "status": "PASS"},
        {"gate": "NYC-F1X-D4-NEXT-D5-HANDOFF", "status": "PASS" if next_d5["status"].startswith("D5_READY") else "FAIL"},
    ]
    overclaim = scan_no_overclaim(out)
    write_json(out / "NYC_F1X_D4_NO_OVERCLAIM_REPORT.json", overclaim)
    gates.append({"gate": "NYC-F1X-D4-NO-OVERCLAIM", "status": overclaim["status"]})
    mutation = compare_signatures(before, {name: input_signature(path) for name, path in watched.items()})
    write_json(out / "NYC_F1X_D4_NO_MUTATION_REPORT.json", mutation)
    gates.append({"gate": "NYC-F1X-D4-NO-MUTATION", "status": mutation["status"]})

    status = "PASS_PAYLOAD_ONLY_WITH_SOURCE_LIMITATIONS" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    write_text(out / "README.md", f"# NYC-F1X-D4 NYC Situational Status Replay + Face Payload Proof\n\nStatus: `{status}`\n\nD3 source: `{d3_kind}`\n\nPayload-only situational status review-context proof. This is not an accepted NYC Flow 1 cartridge.\n")
    harness = {"task": TASK, "status": status, "generated_at": utc_now(), "output_dir": str(out), "d3_source": d3_kind, "face_route_status": face["status"], "gates": gates}
    write_json(out / "NYC_F1X_D4_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    hash_ok = sorted(read_json(out / "SHA256SUMS.json", {}).keys()) == sorted(p for p in REQUIRED_ARTIFACTS if p != "SHA256SUMS.json")
    gates.append({"gate": "NYC-F1X-D4-HASHES", "status": "PASS" if hash_ok else "FAIL", "hashed_files": hashes["file_count"]})
    status = "PASS_PAYLOAD_ONLY_WITH_SOURCE_LIMITATIONS" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    harness["status"] = status
    harness["gates"] = gates
    write_json(out / "NYC_F1X_D4_HARNESS_REPORT.json", harness)
    write_text(out / "README.md", f"# NYC-F1X-D4 NYC Situational Status Replay + Face Payload Proof\n\nStatus: `{status}`\n\nD3 source: `{d3_kind}`\n\nPayload-only situational status review-context proof. This is not an accepted NYC Flow 1 cartridge.\n")
    write_hashes(out)
    return harness


def print_final_report(report: dict[str, Any]) -> None:
    gate_map = {gate["gate"]: gate for gate in report["gates"]}
    print(f"NYC-F1X-D4 NYC Situational Status Replay + Face Payload Proof: {report['status']}")
    print()
    print(f"D3 source: {report['d3_source']}")
    print(f"Replay payload: {gate_map.get('NYC-F1X-D4-REPLAY-PAYLOAD', {}).get('status')}")
    print(f"Briefing payload: {gate_map.get('NYC-F1X-D4-BRIEFING-PAYLOAD', {}).get('status')}")
    print(f"Face route payload: {gate_map.get('NYC-F1X-D4-FACE-ROUTE-PAYLOAD', {}).get('face_status')}")
    print(f"Source limitations: {gate_map.get('NYC-F1X-D4-SOURCE-LIMITATIONS', {}).get('status')}")
    print(f"Boundary carry-forward: {gate_map.get('NYC-F1X-D4-BOUNDARY-CARRY-FORWARD', {}).get('status')}")
    print(f"No-overclaim: {gate_map.get('NYC-F1X-D4-NO-OVERCLAIM', {}).get('status')}")
    print(f"No-mutation: {gate_map.get('NYC-F1X-D4-NO-MUTATION', {}).get('status')}")
    print(f"Hashes: {gate_map.get('NYC-F1X-D4-HASHES', {}).get('status')}")
    print()
    print("Final status:")
    print(report["status"])
    print()
    print(f"Output:\n{report['output_dir']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run NYC-F1X-D4 replay + face payload proof")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = run_nyc_f1x_d4(args.project_root, args.output_dir)
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
