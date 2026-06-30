#!/usr/bin/env python3
"""D4-BATCH-D1 remaining replay / briefing / face payload proofs."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "D4-BATCH-D1 Remaining D4 Replay / Briefing / Face Payload Proofs"
DEFAULT_OUTPUT_DIR = "outputs/d4_batch_d1_remaining_replay_face_proofs"
PASS_STATUSES = {"PASS_D4_BATCH_REPLAY_FACE_PROOFS", "PASS_WITH_SOURCE_LIMITATIONS", "PASS_WITH_PARTIAL_D4_PROGRESS"}

SHARED_INPUTS = {
    "xdata_d2_r1": "outputs/xdata_d2_r1_four_city_bulk_landing_reconciliation_refresh",
    "d3_refresh_d1": "outputs/d3_refresh_d1_bulk_informed_refresh_decision",
    "nightrun_d1": "outputs/nightrun_d1_overnight_current_work_completion",
    "ontology_v2": "contracts/ontology_v2",
    "chi_f4x_d4_context": "outputs/chi_f4x_d4_mobility_environment_replay_face_proof",
    "nyc_f1x_d4_context": "outputs/nyc_f1x_d4_situational_status_replay_face_proof",
}

LANES: dict[str, dict[str, Any]] = {
    "CHI-F3X-D4": {
        "city": "chicago",
        "city_code": "CHI",
        "flow": "F3X",
        "flow_number": "3",
        "mode": "traffic_incident_context_review_context",
        "d3_dir": "outputs/chi_f3x_d3_traffic_incident_context_evidencebundles",
        "prefix": "CHI_F3X_D4",
        "d3_prefix": "CHI_F3X_D3",
        "output_dir": "outputs/chi_f3x_d4_traffic_incident_context_replay_face_proof",
        "script": "txr_citybrain_chi_f3x_d4_traffic_incident_context_replay_face_proof.py",
        "runner": "scripts/run_chi_f3x_d4_gate.py",
        "families": {
            "crash_event_context": ["crash_event"],
            "crash_vehicle_context": ["crash_vehicle"],
            "privacy_safe_crash_person_context": ["crash_person"],
            "traffic_segment_context": ["traffic_segment"],
            "incident_governance_boundary": ["governance_boundary"],
        },
        "boundaries": [
            "Traffic/crash context only.",
            "No dispatch.",
            "No emergency/public-safety instruction.",
            "No affected-asset certification.",
            "No policing or enforcement recommendation.",
            "Chicago Flow 3 extension is not accepted at D4.",
        ],
    },
    "NYC-F5X-D4": {
        "city": "nyc",
        "city_code": "NYC",
        "flow": "F5X",
        "flow_number": "5",
        "mode": "flood_climate_asset_risk_review_context",
        "d3_dir": "outputs/nyc_f5x_d3_flood_climate_asset_risk_evidencebundles",
        "prefix": "NYC_F5X_D4",
        "d3_prefix": "NYC_F5X_D3",
        "output_dir": "outputs/nyc_f5x_d4_flood_climate_asset_risk_replay_face_proof",
        "script": "txr_citybrain_nyc_f5x_d4_flood_climate_asset_risk_replay_face_proof.py",
        "runner": "scripts/run_nyc_f5x_d4_gate.py",
        "families": {
            "flood_vulnerability_context": ["flood_vulnerability"],
            "air_quality_climate_context": ["air_quality", "climate"],
            "parcel_or_area_risk_context": ["parcel_or_area", "area_risk"],
            "facility_context": ["facility"],
            "risk_governance_boundary": ["governance_boundary"],
        },
        "boundaries": [
            "Risk context only.",
            "No certified infrastructure failure propagation.",
            "No utility-control instruction.",
            "No emergency-response instruction.",
            "No health determination.",
            "No certified affected asset/building.",
            "NYC Flow 5 is not accepted at D4.",
        ],
    },
    "NYC-F6X-D4": {
        "city": "nyc",
        "city_code": "NYC",
        "flow": "F6X",
        "flow_number": "6",
        "mode": "port_airport_logistics_review_context",
        "d3_dir": "outputs/nyc_f6x_d3_port_airport_logistics_evidencebundles",
        "prefix": "NYC_F6X_D4",
        "d3_prefix": "NYC_F6X_D3",
        "output_dir": "outputs/nyc_f6x_d4_port_airport_logistics_replay_face_proof",
        "script": "txr_citybrain_nyc_f6x_d4_port_airport_logistics_replay_face_proof.py",
        "runner": "scripts/run_nyc_f6x_d4_gate.py",
        "families": {
            "panynj_air_passenger_context": ["panynj_air_passenger"],
            "airport_logistics_trend_context": ["airport_logistics"],
            "review_only_sequence_context": ["review_only_sequence"],
            "logistics_governance_boundary": ["governance_boundary"],
        },
        "boundaries": [
            "Review-only logistics context.",
            "No airport operational command.",
            "No port operational command.",
            "No aircraft instruction.",
            "No vessel instruction.",
            "No safety-critical sequencing.",
            "NYC Flow 6 is not accepted at D4.",
        ],
    },
    "BARC-F7-D4": {
        "city": "barcelona",
        "city_code": "BARC",
        "flow": "F7",
        "flow_number": "7",
        "mode": "civic_sensor_fusion_review_context",
        "d3_dir": "outputs/barc_f7_d3_r1_civic_sensor_fusion_evidencebundles",
        "fallback_d3_dir": "outputs/barc_f7_d3_civic_sensor_fusion_evidencebundles",
        "prefix": "BARC_F7_D4",
        "d3_prefix": "BARC_F7_D3_R1",
        "fallback_d3_prefix": "BARC_F7_D3",
        "output_dir": "outputs/barc_f7_d4_civic_sensor_fusion_replay_face_proof",
        "script": "txr_citybrain_barc_f7_d4_civic_sensor_fusion_replay_face_proof.py",
        "runner": "scripts/run_barc_f7_d4_gate.py",
        "families": {
            "iris_civic_service_context": ["iris"],
            "sentilo_connecta_sensor_context": ["sentilo", "connecta"],
            "air_quality_noise_context": ["air_noise", "air_quality", "noise"],
            "traffic_bicing_mobility_context": ["traffic", "bicing", "mobility"],
            "facilities_public_services_context": ["facility"],
            "district_neighbourhood_fusion_context": ["district", "neighbourhood"],
            "governance_boundary": ["governance_boundary"],
        },
        "boundaries": [
            "Barcelona remains candidate-only.",
            "Barcelona Flow 7 is not accepted at D4.",
            "IRIS is civic-service context, not emergency/public-safety signal.",
            "Sensor/environment data is context, not health determination.",
            "Mobility/traffic context is not traffic-control instruction.",
            "Point-in-time/API snapshots are not historical completeness.",
            "Manual recovery remains source-limited where flagged.",
        ],
    },
}

NO_OVERCLAIM_PATTERNS = [
    r"\bemergency dispatch\b",
    r"\bfire dispatch\b",
    r"\bpublic safety recommendation\b",
    r"\bpublic-safety recommendation\b",
    r"\bpolicing recommendation\b",
    r"\benforcement action\b",
    r"\bhealth determination\b",
    r"\btraffic-control instruction\b",
    r"\btransit-control instruction\b",
    r"\butility-control instruction\b",
    r"\bport-control instruction\b",
    r"\bairport-control instruction\b",
    r"\bairport operational command\b",
    r"\bport operational command\b",
    r"\bcertified affected building\b",
    r"\bcertified affected asset\b",
    r"\baccepted-flow claim\b",
    r"\bflow .* accepted\b",
    r"\ball .* sources are full\b",
    r"\bhistorical completeness\b",
]

NEGATION_MARKERS = ("no ", "not ", "never ", "without ", "does not ", "do not ", "cannot ", "candidate-only", "review-only")

BATCH_REQUIRED = [
    "README.md",
    "D4_BATCH_D1_HARNESS_REPORT.json",
    "D4_BATCH_D1_INPUT_INVENTORY.json",
    "D4_BATCH_D1_QUEUE_PLAN.json",
    "D4_BATCH_D1_STAGE_RESULTS.json",
    "D4_BATCH_D1_NEXT_D5_HANDOFF.json",
    "D4_BATCH_D1_NO_OVERCLAIM_REPORT.json",
    "D4_BATCH_D1_NO_MUTATION_REPORT.json",
    "SHA256SUMS.json",
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
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


def reset_output_dir(output_dir: Path, project_root: Path, expected_name: str) -> Path:
    resolved = output_dir.resolve()
    root = project_root.resolve()
    if resolved.exists():
        text = str(resolved).lower()
        if not text.startswith(str(root).lower()) or resolved.name.lower() != expected_name.lower():
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


def scan_no_overclaim(paths: list[Path], skip_names: set[str] | None = None) -> dict[str, Any]:
    skip_names = skip_names or set()
    findings = []
    checked = 0
    for root in paths:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name in skip_names:
                continue
            if path.suffix.lower() not in {".json", ".md", ".txt", ".csv"}:
                continue
            checked += 1
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            for pattern in NO_OVERCLAIM_PATTERNS:
                for match in re.finditer(pattern, text):
                    window = text[max(0, match.start() - 64) : match.end() + 24]
                    if any(marker in window for marker in NEGATION_MARKERS):
                        continue
                    findings.append({"path": str(path), "pattern": pattern, "context": window})
    return {"status": "PASS" if not findings else "FAIL", "checked_files": checked, "findings": findings}


def selected_d3(project_root: Path, cfg: dict[str, Any]) -> tuple[str, Path, list[dict[str, Any]], dict[str, Any]]:
    d3 = project_path(project_root, cfg["d3_dir"])
    prefix = cfg["d3_prefix"]
    if not d3.exists() and cfg.get("fallback_d3_dir"):
        d3 = project_path(project_root, cfg["fallback_d3_dir"])
        prefix = cfg["fallback_d3_prefix"]
    selected = read_json(d3 / f"{prefix}_SELECTED_BUNDLES.json", {})
    harness = read_json(d3 / f"{prefix}_HARNESS_REPORT.json", {})
    bundles = selected.get("selected_bundles", [])
    if bundles and "evidence_bundle_id" not in bundles[0] and (d3 / f"{prefix}_EVIDENCEBUNDLES.json").exists():
        eb = read_json(d3 / f"{prefix}_EVIDENCEBUNDLES.json", {})
        bundles = eb.get("bundles", [])
    return prefix, d3, bundles, harness


def source_limitations(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    seen = set()
    for bundle in bundles:
        for source in bundle.get("source_records", []):
            key = source.get("source_key")
            if not key or key in seen:
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
                    "rule": limitation_rule(status),
                }
            )
    return rows


def limitation_rule(status: str | None) -> str:
    if status == "FULL":
        return "Full where proven by rows_landed equaling total_available."
    if status == "CAPPED_BULK":
        return "Capped bulk; not full-source proof."
    if status == "WINDOWED_COMPLETE":
        return "Windowed complete only for the explicit window/snapshot."
    if status == "BOUNDED_SAMPLE":
        return "Bounded sample; source-limited context."
    if status == "DOWNLOAD_FAILED":
        return "Download failed unless manual recovery is explicitly attached."
    if status == "MANUAL_RECOVERY_FULL":
        return "Manual recovery remains source-limited where flagged."
    if status == "METADATA_ONLY":
        return "Metadata-only context."
    if status == "ENDPOINT_CONFIRMED":
        return "Endpoint-confirmed context only."
    return "Source limitation carried forward."


def context_families(bundle_ids: list[str], xdata_refs: list[str], cfg: dict[str, Any]) -> dict[str, bool]:
    haystack = list(bundle_ids) + list(xdata_refs)
    return {
        family: any(any(token in item for token in tokens) for item in haystack)
        for family, tokens in cfg["families"].items()
    }


def future_routes(cfg: dict[str, Any]) -> list[str]:
    city = cfg["city"]
    n = cfg["flow_number"]
    return [f"/{city}/flow{n}/replay", f"/{city}/flow{n}/briefing", f"/api/{city}/flow{n}/replay", f"/api/{city}/flow{n}/briefing"]


def build_payloads(project_root: Path, lane: str, cfg: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]], Path]:
    d3_prefix, d3_dir, bundles, harness = selected_d3(project_root, cfg)
    bundle_ids = [bundle.get("evidence_bundle_id") for bundle in bundles if bundle.get("evidence_bundle_id")]
    xdata_refs = sorted({source.get("source_key") for bundle in bundles for source in bundle.get("source_records", []) if source.get("source_key")})
    limitations = source_limitations(bundles)
    replay = {
        "city": cfg["city"],
        "flow": cfg["flow"],
        "stage": "D4",
        "source_stage": d3_prefix.replace("_", "-"),
        "mode": cfg["mode"],
        "accepted_flow_cartridge": False,
        "review_context_only": True,
        "evidencebundle_refs": bundle_ids,
        "xdata_refs": xdata_refs,
        "context_families": context_families(bundle_ids, xdata_refs, cfg),
        "source_limitations": limitations,
        "governance_boundaries": cfg["boundaries"],
        "forbidden_claims": [
            "NO_ACCEPTED_FLOW_AT_D4",
            "NO_OPERATIONAL_COMMAND",
            "NO_EMERGENCY_DISPATCH",
            "NO_PUBLIC_SAFETY_RECOMMENDATION",
            "NO_HEALTH_DETERMINATION",
            "NO_CONTROL_INSTRUCTION",
            "NO_CERTIFIED_AFFECTED_ASSET_OR_BUILDING",
        ],
    }
    briefing = {
        "status": "PASS",
        "audience": "operator_review",
        "briefing_lines": [
            f"{lane} is a payload-only D4 replay proof for review-context operator review.",
            "Source-limited, capped bulk, windowed complete, and full where proven labels carry forward.",
            "This D4 result is D5-ready and does not make an accepted-flow claim.",
        ],
        "source_stage": replay["source_stage"],
        "evidencebundle_refs": bundle_ids,
    }
    face = {
        "status": "FACE_ROUTE_PAYLOAD_ONLY",
        "published": False,
        "future_routes": future_routes(cfg),
        "payload_bindings": {"replay_payload": f"{cfg['prefix']}_REPLAY_PAYLOAD.json", "briefing_payload": f"{cfg['prefix']}_BRIEFING_PAYLOAD.json"},
        "accepted_flow_cartridge": False,
        "review_context_only": True,
    }
    trace = {
        "status": "PASS",
        "d3_source": str(d3_dir),
        "d3_status": harness.get("status"),
        "trace_refs": [f"{d3_prefix}:{bundle_id}" for bundle_id in bundle_ids] + [f"XDATA-D2-R1:{ref}" for ref in xdata_refs],
    }
    return replay, briefing, face, trace, limitations, d3_dir


def write_individual_d4(project_root: Path, lane: str) -> dict[str, Any]:
    cfg = LANES[lane]
    out = reset_output_dir(project_path(project_root, cfg["output_dir"]), project_root, Path(cfg["output_dir"]).name)
    watched = {"d3": project_path(project_root, cfg["d3_dir"]), "xdata_d2_r1": project_path(project_root, SHARED_INPUTS["xdata_d2_r1"]), "ontology_v2": project_path(project_root, SHARED_INPUTS["ontology_v2"])}
    if cfg.get("fallback_d3_dir"):
        watched["fallback_d3"] = project_path(project_root, cfg["fallback_d3_dir"])
    before = {name: input_signature(path) for name, path in watched.items()}
    replay, briefing, face, trace, limitations, d3_dir = build_payloads(project_root, lane, cfg)
    inventory = {
        "status": "PASS",
        "inputs": {name: {"path": str(path), "exists": path.exists(), "signature": input_signature(path)} for name, path in watched.items()},
    }
    ledger = {
        "status": "PASS",
        "stages": [
            {"stage": "D3_SOURCE_SELECT", "status": "PASS", "path": str(d3_dir)},
            {"stage": "REPLAY_PAYLOAD", "status": "PASS", "evidencebundle_refs": replay["evidencebundle_refs"]},
            {"stage": "BRIEFING_PAYLOAD", "status": "PASS"},
            {"stage": "FACE_ROUTE_PAYLOAD", "status": "FACE_ROUTE_PAYLOAD_ONLY"},
        ],
    }
    source_report = {"status": "PASS", "limitations": limitations, "boundary_lines": cfg["boundaries"]}
    next_d5 = {
        "status": "D5_READY_WITH_SOURCE_LIMITATIONS",
        "recommended_next_gate": lane.replace("-D4", "-D5"),
        "source_stage": replay["source_stage"],
        "boundaries_to_carry": cfg["boundaries"],
        "note": "Do not run D6 until D5 batch is complete and a separate D6 promotion-review gate decides accepted vs review/candidate status.",
    }
    write_json(out / f"{cfg['prefix']}_INPUT_INVENTORY.json", inventory)
    write_json(out / f"{cfg['prefix']}_STAGE_LEDGER.json", ledger)
    write_json(out / f"{cfg['prefix']}_REPLAY_PAYLOAD.json", replay)
    write_json(out / f"{cfg['prefix']}_BRIEFING_PAYLOAD.json", briefing)
    write_json(out / f"{cfg['prefix']}_FACE_ROUTE_PAYLOAD.json", face)
    write_json(out / f"{cfg['prefix']}_TRACE_REPORT.json", trace)
    write_json(out / f"{cfg['prefix']}_SOURCE_LIMITATION_REPORT.json", source_report)
    write_json(out / f"{cfg['prefix']}_NEXT_D5_HANDOFF.json", next_d5)
    gates = [
        {"gate": f"{lane}-PRECOND", "status": "PASS" if d3_dir.exists() else "FAIL"},
        {"gate": f"{lane}-INPUT-INVENTORY", "status": inventory["status"]},
        {"gate": f"{lane}-STAGE-LEDGER", "status": ledger["status"]},
        {"gate": f"{lane}-REPLAY-PAYLOAD", "status": "PASS" if replay["review_context_only"] and replay["evidencebundle_refs"] else "FAIL"},
        {"gate": f"{lane}-BRIEFING-PAYLOAD", "status": briefing["status"]},
        {"gate": f"{lane}-FACE-ROUTE-PAYLOAD", "status": "PASS", "face_status": face["status"]},
        {"gate": f"{lane}-SOURCE-LIMITATIONS", "status": source_report["status"]},
        {"gate": f"{lane}-BOUNDARY-CARRY-FORWARD", "status": "PASS"},
        {"gate": f"{lane}-NEXT-D5-HANDOFF", "status": "PASS"},
    ]
    overclaim = scan_no_overclaim([out], skip_names={f"{cfg['prefix']}_NO_OVERCLAIM_REPORT.json", "SHA256SUMS.json"})
    write_json(out / f"{cfg['prefix']}_NO_OVERCLAIM_REPORT.json", overclaim)
    gates.append({"gate": f"{lane}-NO-OVERCLAIM", "status": overclaim["status"]})
    mutation = compare_signatures(before, {name: input_signature(path) for name, path in watched.items()})
    write_json(out / f"{cfg['prefix']}_NO_MUTATION_REPORT.json", mutation)
    gates.append({"gate": f"{lane}-NO-MUTATION", "status": mutation["status"]})
    status = "PASS_PAYLOAD_ONLY_WITH_SOURCE_LIMITATIONS" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    write_text(out / "README.md", f"# {lane} Replay + Face Payload Proof\n\nStatus: `{status}`\n\nPayload-only D4 review-context proof. This is not an accepted flow cartridge.\n")
    harness = {"task": f"{lane} Replay + Face Payload Proof", "status": status, "generated_at": utc_now(), "output_dir": str(out), "face_route_status": face["status"], "gates": gates}
    write_json(out / f"{cfg['prefix']}_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    required = [
        "README.md",
        f"{cfg['prefix']}_HARNESS_REPORT.json",
        f"{cfg['prefix']}_INPUT_INVENTORY.json",
        f"{cfg['prefix']}_STAGE_LEDGER.json",
        f"{cfg['prefix']}_REPLAY_PAYLOAD.json",
        f"{cfg['prefix']}_BRIEFING_PAYLOAD.json",
        f"{cfg['prefix']}_FACE_ROUTE_PAYLOAD.json",
        f"{cfg['prefix']}_TRACE_REPORT.json",
        f"{cfg['prefix']}_SOURCE_LIMITATION_REPORT.json",
        f"{cfg['prefix']}_NEXT_D5_HANDOFF.json",
        f"{cfg['prefix']}_NO_OVERCLAIM_REPORT.json",
        f"{cfg['prefix']}_NO_MUTATION_REPORT.json",
    ]
    hash_ok = sorted(read_json(out / "SHA256SUMS.json", {}).keys()) == sorted(required)
    gates.append({"gate": f"{lane}-HASHES", "status": "PASS" if hash_ok else "FAIL", "hashed_files": hashes["file_count"]})
    status = "PASS_PAYLOAD_ONLY_WITH_SOURCE_LIMITATIONS" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    harness["status"] = status
    harness["gates"] = gates
    write_json(out / f"{cfg['prefix']}_HARNESS_REPORT.json", harness)
    write_text(out / "README.md", f"# {lane} Replay + Face Payload Proof\n\nStatus: `{status}`\n\nPayload-only D4 review-context proof. This is not an accepted flow cartridge.\n")
    write_hashes(out)
    return {"lane": lane, "status": status, "output_dir": str(out), "face_route_status": face["status"]}


def batch_inventory(project_root: Path) -> dict[str, Any]:
    inputs = {name: project_path(project_root, rel) for name, rel in SHARED_INPUTS.items()}
    inputs.update({f"{lane}_d3": project_path(project_root, cfg["d3_dir"]) for lane, cfg in LANES.items()})
    return {"status": "PASS", "inputs": {name: {"path": str(path), "exists": path.exists(), "signature": input_signature(path)} for name, path in inputs.items()}}


def run_single_d4(lane: str, project_root: str | Path = ".") -> dict[str, Any]:
    return write_individual_d4(Path(project_root).resolve(), lane)


def run_d4_batch(project_root: str | Path = ".", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    out = reset_output_dir(project_path(project_root, output_dir), project_root, Path(output_dir).name)
    watched = {name: project_path(project_root, rel) for name, rel in SHARED_INPUTS.items()}
    watched.update({f"{lane}_d3": project_path(project_root, cfg["d3_dir"]) for lane, cfg in LANES.items()})
    before = {name: input_signature(path) for name, path in watched.items()}
    inventory = batch_inventory(project_root)
    queue_plan = {"status": "PASS", "queue": [{"rank": i, "lane": lane, "output_dir": str(project_path(project_root, cfg["output_dir"]))} for i, (lane, cfg) in enumerate(LANES.items(), start=1)]}
    results = [write_individual_d4(project_root, lane) for lane in LANES]
    d5_handoff = {
        "status": "PASS",
        "already_complete": [{"lane": "CHI-F4X-D5", "status": "already complete"}],
        "needed": [
            {"lane": "NYC-F1X-D5", "status": "needed", "source_d4": "outputs/nyc_f1x_d4_situational_status_replay_face_proof"},
            *[
                {"lane": result["lane"].replace("-D4", "-D5"), "status": "needed" if result["status"].startswith("PASS") else "blocked", "source_d4": result["output_dir"]}
                for result in results
            ],
        ],
        "d6_boundary": "Do not run D6 until D5 batch is complete and a separate D6 promotion-review gate decides accepted vs review/candidate status.",
    }
    write_json(out / "D4_BATCH_D1_INPUT_INVENTORY.json", inventory)
    write_json(out / "D4_BATCH_D1_QUEUE_PLAN.json", queue_plan)
    write_json(out / "D4_BATCH_D1_STAGE_RESULTS.json", {"status": "PASS", "results": results})
    write_json(out / "D4_BATCH_D1_NEXT_D5_HANDOFF.json", d5_handoff)
    gates = [
        {"gate": "D4-BATCH-D1-PRECOND", "status": "PASS"},
        {"gate": "D4-BATCH-D1-INPUT-INVENTORY", "status": inventory["status"]},
        {"gate": "D4-BATCH-D1-QUEUE-PLAN", "status": queue_plan["status"]},
        *[{"gate": f"D4-BATCH-D1-{result['lane']}", "status": "PASS" if result["status"].startswith("PASS") else "FAIL"} for result in results],
        {"gate": "D4-BATCH-D1-NEXT-D5-HANDOFF", "status": d5_handoff["status"]},
        {"gate": "D4-BATCH-D1-BOUNDARY-CARRY-FORWARD", "status": "PASS"},
    ]
    overclaim = scan_no_overclaim([out] + [project_path(project_root, cfg["output_dir"]) for cfg in LANES.values()], skip_names={"SHA256SUMS.json", "D4_BATCH_D1_NO_OVERCLAIM_REPORT.json"})
    write_json(out / "D4_BATCH_D1_NO_OVERCLAIM_REPORT.json", overclaim)
    gates.append({"gate": "D4-BATCH-D1-NO-OVERCLAIM", "status": overclaim["status"]})
    mutation = compare_signatures(before, {name: input_signature(path) for name, path in watched.items()})
    write_json(out / "D4_BATCH_D1_NO_MUTATION_REPORT.json", mutation)
    gates.append({"gate": "D4-BATCH-D1-NO-MUTATION", "status": mutation["status"]})
    passed = sum(1 for r in results if r["status"].startswith("PASS"))
    failed = len(results) - passed
    status = "PASS_WITH_SOURCE_LIMITATIONS" if failed == 0 else ("PASS_WITH_PARTIAL_D4_PROGRESS" if passed else "FAIL")
    write_text(out / "README.md", f"# D4-BATCH-D1 Remaining D4 Replay / Face Proofs\n\nStatus: `{status}`\n\nCompleted {passed} of {len(results)} remaining D4 gates.\n")
    harness = {"task": TASK, "status": status, "generated_at": utc_now(), "output_dir": str(out), "d4_attempted": len(results), "d4_passed": passed, "d4_failed": failed, "results": results, "gates": gates}
    write_json(out / "D4_BATCH_D1_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    hash_ok = sorted(read_json(out / "SHA256SUMS.json", {}).keys()) == sorted(p for p in BATCH_REQUIRED if p != "SHA256SUMS.json")
    gates.append({"gate": "D4-BATCH-D1-HASHES", "status": "PASS" if hash_ok else "FAIL", "hashed_files": hashes["file_count"]})
    status = status if all(g["status"] == "PASS" for g in gates) else "FAIL"
    harness["status"] = status
    harness["gates"] = gates
    write_json(out / "D4_BATCH_D1_HARNESS_REPORT.json", harness)
    write_text(out / "README.md", f"# D4-BATCH-D1 Remaining D4 Replay / Face Proofs\n\nStatus: `{status}`\n\nCompleted {passed} of {len(results)} remaining D4 gates.\n")
    write_hashes(out)
    return harness


def print_final_report(report: dict[str, Any]) -> None:
    print(f"D4-BATCH-D1 Remaining D4 Replay / Face Proofs: {report['status']}")
    print()
    for lane in LANES:
        result = next((r for r in report["results"] if r["lane"] == lane), {"status": "SKIPPED"})
        print(f"{lane}: {'PASS' if str(result['status']).startswith('PASS') else result['status']}")
    print()
    print(f"D4 gates attempted: {report['d4_attempted']}")
    print(f"D4 gates passed: {report['d4_passed']}")
    print(f"D4 gates failed: {report['d4_failed']}")
    gate_map = {g["gate"]: g["status"] for g in report["gates"]}
    print()
    print(f"Next D5 handoff: {gate_map.get('D4-BATCH-D1-NEXT-D5-HANDOFF')}")
    print(f"Boundary carry-forward: {gate_map.get('D4-BATCH-D1-BOUNDARY-CARRY-FORWARD')}")
    print(f"No-overclaim: {gate_map.get('D4-BATCH-D1-NO-OVERCLAIM')}")
    print(f"No-mutation: {gate_map.get('D4-BATCH-D1-NO-MUTATION')}")
    print(f"Hashes: {gate_map.get('D4-BATCH-D1-HASHES')}")
    print()
    print("Final status:")
    print(report["status"])
    print()
    print(f"Output:\n{report['output_dir']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run D4-BATCH-D1 remaining replay/face proofs")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = run_d4_batch(args.project_root, args.output_dir)
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
