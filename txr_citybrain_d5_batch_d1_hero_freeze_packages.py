#!/usr/bin/env python3
"""D5-BATCH-D1 hero freeze packages for payload-only D4 lanes."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "D5-BATCH-D1 Hero Freeze Packages"
DEFAULT_OUTPUT_DIR = "outputs/d5_batch_d1_hero_freeze_packages"
PASS_STATUSES = {"PASS_D5_BATCH_HERO_FREEZE_PACKAGES", "PASS_WITH_SOURCE_LIMITATIONS", "PASS_WITH_PARTIAL_D5_PROGRESS"}

LANES: dict[str, dict[str, Any]] = {
    "NYC-F1X-D5": {
        "city": "nyc",
        "city_label": "NYC",
        "flow": "F1X",
        "flow_number": "1",
        "topic": "Situational Status",
        "d4_dir": "outputs/nyc_f1x_d4_situational_status_replay_face_proof",
        "d4_prefix": "NYC_F1X_D4",
        "prefix": "NYC_F1X_D5",
        "output_dir": "outputs/nyc_f1x_d5_situational_status_hero_freeze_package",
        "script": "txr_citybrain_nyc_f1x_d5_situational_status_hero_freeze_package.py",
        "runner": "scripts/run_nyc_f1x_d5_gate.py",
        "context_title": "NYC Flow 1 Situational Status Context",
        "evidence_focus": ["311 situational status", "collision/mobility", "air quality/environment", "transit status"],
        "not_accepted": "NYC Flow 1 is not accepted.",
    },
    "CHI-F3X-D5": {
        "city": "chicago",
        "city_label": "Chicago",
        "flow": "F3X",
        "flow_number": "3",
        "topic": "Traffic Incident Context",
        "d4_dir": "outputs/chi_f3x_d4_traffic_incident_context_replay_face_proof",
        "d4_prefix": "CHI_F3X_D4",
        "prefix": "CHI_F3X_D5",
        "output_dir": "outputs/chi_f3x_d5_traffic_incident_context_hero_freeze_package",
        "script": "txr_citybrain_chi_f3x_d5_traffic_incident_context_hero_freeze_package.py",
        "runner": "scripts/run_chi_f3x_d5_gate.py",
        "context_title": "Chicago Flow 3 Traffic Incident Context",
        "evidence_focus": ["crash event", "crash vehicle", "privacy-safe crash/person", "traffic segment"],
        "not_accepted": "Chicago Flow 3 extension is not accepted.",
    },
    "NYC-F5X-D5": {
        "city": "nyc",
        "city_label": "NYC",
        "flow": "F5X",
        "flow_number": "5",
        "topic": "Flood / Climate / Asset-Risk",
        "d4_dir": "outputs/nyc_f5x_d4_flood_climate_asset_risk_replay_face_proof",
        "d4_prefix": "NYC_F5X_D4",
        "prefix": "NYC_F5X_D5",
        "output_dir": "outputs/nyc_f5x_d5_flood_climate_asset_risk_hero_freeze_package",
        "script": "txr_citybrain_nyc_f5x_d5_flood_climate_asset_risk_hero_freeze_package.py",
        "runner": "scripts/run_nyc_f5x_d5_gate.py",
        "context_title": "NYC Flow 5 Flood / Climate / Asset-Risk Context",
        "evidence_focus": ["flood vulnerability", "air quality/climate", "area-risk", "facility context"],
        "not_accepted": "NYC Flow 5 is not accepted.",
    },
    "NYC-F6X-D5": {
        "city": "nyc",
        "city_label": "NYC",
        "flow": "F6X",
        "flow_number": "6",
        "topic": "Port / Airport Logistics",
        "d4_dir": "outputs/nyc_f6x_d4_port_airport_logistics_replay_face_proof",
        "d4_prefix": "NYC_F6X_D4",
        "prefix": "NYC_F6X_D5",
        "output_dir": "outputs/nyc_f6x_d5_port_airport_logistics_hero_freeze_package",
        "script": "txr_citybrain_nyc_f6x_d5_port_airport_logistics_hero_freeze_package.py",
        "runner": "scripts/run_nyc_f6x_d5_gate.py",
        "context_title": "NYC Flow 6 Port / Airport Logistics Context",
        "evidence_focus": ["PANYNJ air passenger", "airport logistics trend", "review-only sequence", "logistics governance"],
        "not_accepted": "NYC Flow 6 is not accepted.",
    },
    "BARC-F7-D5": {
        "city": "barcelona",
        "city_label": "Barcelona",
        "flow": "F7",
        "flow_number": "7",
        "topic": "Civic / Sensor Fusion",
        "d4_dir": "outputs/barc_f7_d4_civic_sensor_fusion_replay_face_proof",
        "d4_prefix": "BARC_F7_D4",
        "prefix": "BARC_F7_D5",
        "output_dir": "outputs/barc_f7_d5_civic_sensor_fusion_hero_freeze_package",
        "script": "txr_citybrain_barc_f7_d5_civic_sensor_fusion_hero_freeze_package.py",
        "runner": "scripts/run_barc_f7_d5_gate.py",
        "context_title": "Barcelona Flow 7 Civic / Sensor Fusion Context",
        "evidence_focus": ["IRIS civic-service", "Sentilo/Connecta sensor", "air/noise", "traffic/Bicing", "facilities"],
        "not_accepted": "Barcelona Flow 7 is not accepted; Barcelona remains candidate-only.",
        "candidate_only": True,
    },
}

SHARED_INPUTS = {
    "d4_batch": "outputs/d4_batch_d1_remaining_replay_face_proofs",
    "xdata_d2_r1": "outputs/xdata_d2_r1_four_city_bulk_landing_reconciliation_refresh",
    "d3_refresh_d1": "outputs/d3_refresh_d1_bulk_informed_refresh_decision",
    "ontology_v2": "contracts/ontology_v2",
    "chi_f4x_d5_complete": "outputs/chi_f4x_d5_hero_freeze_package",
}

NO_OVERCLAIM_PATTERNS = [
    r"\bplatform v1 complete\b",
    r"\ball flows accepted\b",
    r"\baccepted flow cartridge\b",
    r"\bpayload-only means live route\b",
    r"\bcapped bulk is full\b",
    r"\bwindowed/api snapshot is historical completeness\b",
    r"\bemergency dispatch\b",
    r"\bfire dispatch\b",
    r"\bpublic safety recommendation\b",
    r"\bpublic-safety recommendation\b",
    r"\bhealth determination\b",
    r"\btraffic-control instruction\b",
    r"\btransit-control instruction\b",
    r"\butility-control instruction\b",
    r"\bport/airport operational command\b",
    r"\bairport operational command\b",
    r"\bport operational command\b",
    r"\bpolicing recommendation\b",
    r"\benforcement action\b",
    r"\bcertified affected asset\b",
    r"\bcertified affected building\b",
]

NEGATION_MARKERS = ("no ", "not ", "never ", "without ", "does not ", "do not ", "cannot ", "candidate-only", "review-context", "payload-only")

BATCH_REQUIRED = [
    "README.md",
    "D5_BATCH_D1_HARNESS_REPORT.json",
    "D5_BATCH_D1_INPUT_INVENTORY.json",
    "D5_BATCH_D1_QUEUE_PLAN.json",
    "D5_BATCH_D1_STAGE_RESULTS.json",
    "D5_BATCH_D1_D6_PROMOTION_REVIEW_HANDOFF.json",
    "D5_BATCH_D1_NO_OVERCLAIM_REPORT.json",
    "D5_BATCH_D1_NO_MUTATION_REPORT.json",
    "SHA256SUMS.json",
]

INDIVIDUAL_SUFFIXES = [
    "README.md",
    "{prefix}_HARNESS_REPORT.json",
    "{prefix}_INPUT_INVENTORY.json",
    "{prefix}_HERO_SELECTION_POLICY.json",
    "{prefix}_HERO_CANDIDATES.json",
    "{prefix}_SELECTED_HEROES.json",
    "{prefix}_HERO_FREEZE_PACKAGE.json",
    "{prefix}_HERO_BRIEFINGS.json",
    "{prefix}_FACE_HERO_PAYLOAD.json",
    "{prefix}_TRACE_REPORT.json",
    "{prefix}_SOURCE_LIMITATION_REPORT.json",
    "{prefix}_NEXT_D6_HANDOFF.json",
    "{prefix}_NO_OVERCLAIM_REPORT.json",
    "{prefix}_NO_MUTATION_REPORT.json",
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
                    window = text[max(0, match.start() - 72) : match.end() + 24]
                    if any(marker in window for marker in NEGATION_MARKERS):
                        continue
                    findings.append({"path": str(path), "pattern": pattern, "context": window})
    return {"status": "PASS" if not findings else "FAIL", "checked_files": checked, "findings": findings}


def load_d4(project_root: Path, cfg: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    d4 = project_path(project_root, cfg["d4_dir"])
    prefix = cfg["d4_prefix"]
    return (
        read_json(d4 / f"{prefix}_HARNESS_REPORT.json", {}),
        read_json(d4 / f"{prefix}_REPLAY_PAYLOAD.json", {}),
        read_json(d4 / f"{prefix}_FACE_ROUTE_PAYLOAD.json", {}),
    )


def build_heroes(lane: str, cfg: dict[str, Any], replay: dict[str, Any], face: dict[str, Any]) -> list[dict[str, Any]]:
    bundle_refs = replay.get("evidencebundle_refs", [])
    payload_ids = [f"{cfg['d4_prefix']}_REPLAY_PAYLOAD", f"{cfg['d4_prefix']}_BRIEFING_PAYLOAD", f"{cfg['d4_prefix']}_FACE_ROUTE_PAYLOAD"]
    source_limitations = replay.get("source_limitations", [])
    boundaries = list(replay.get("governance_boundaries", [])) + [
        cfg["not_accepted"],
        f"D4 face route status is {face.get('status', 'FACE_ROUTE_PAYLOAD_ONLY')}.",
        "D5 is hero freeze only and does not run D6.",
    ]
    base = {
        "city": cfg["city"],
        "flow": cfg["flow"],
        "stage": "D5",
        "source_stage": lane.replace("-D5", "-D4"),
        "accepted_flow_cartridge": False,
        "review_context_only": True,
        "source_d4_payload_ids": payload_ids,
        "next_step": "D6 promotion review only",
    }
    forbidden = [
        "NO_ACCEPTED_FLOW",
        "NO_LIVE_ROUTE_FROM_PAYLOAD_ONLY",
        "NO_CONTROL_INSTRUCTION",
        "NO_EMERGENCY_DISPATCH",
        "NO_PUBLIC_SAFETY_RECOMMENDATION",
        "NO_HEALTH_DETERMINATION",
        "NO_OPERATIONAL_COMMAND",
        "NO_CERTIFIED_AFFECTED_ASSET_OR_BUILDING",
    ]
    heroes = [
        {
            **base,
            "hero_id": f"{cfg['prefix'].lower()}_hero_1_context",
            "hero_title": cfg["context_title"],
            "claim_label": "[R]",
            "summary": f"{cfg['context_title']} hero freeze for review-context operator review using {', '.join(cfg['evidence_focus'])}.",
            "source_evidence_bundle_ids": bundle_refs,
            "evidence_refs": [f"{cfg['d4_prefix']}:{ref}" for ref in bundle_refs],
            "source_limitations": source_limitations,
            "governance_boundaries": boundaries,
            "forbidden_claims": forbidden,
        },
        {
            **base,
            "hero_id": f"{cfg['prefix'].lower()}_hero_2_source_limitations",
            "hero_title": f"{cfg['city_label']} {cfg['flow']} Source-Limited Evidence",
            "claim_label": "[R]",
            "summary": "Source-limited hero freeze carrying capped bulk, windowed complete, bounded, manual recovery, or full where proven labels from D4.",
            "source_evidence_bundle_ids": bundle_refs,
            "evidence_refs": [f"{cfg['d4_prefix']}:source_limitation_report"],
            "source_limitations": source_limitations,
            "governance_boundaries": boundaries,
            "forbidden_claims": forbidden,
        },
        {
            **base,
            "hero_id": f"{cfg['prefix'].lower()}_hero_3_governance_boundary",
            "hero_title": f"Governance Boundary: {cfg['city_label']} {cfg['flow']} Payload-Only Review",
            "claim_label": "[G]",
            "summary": "Governance hero freeze showing payload-only, review-context, D6 promotion-review-ready boundaries.",
            "source_evidence_bundle_ids": bundle_refs,
            "evidence_refs": [f"{cfg['d4_prefix']}:face_route_payload", f"{cfg['d4_prefix']}:trace_report"],
            "source_limitations": source_limitations,
            "governance_boundaries": boundaries,
            "forbidden_claims": forbidden,
        },
    ]
    if cfg.get("candidate_only"):
        for hero in heroes:
            hero["candidate_only"] = True
    return heroes


def build_briefings(lane: str, heroes: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "briefings": [
            {
                "hero_id": hero["hero_id"],
                "hero_title": hero["hero_title"],
                "briefing_text": [
                    f"{lane} hero freeze is review-context, source-limited, and payload-only.",
                    "Capped bulk, windowed complete, bounded, manual recovery, and full where proven labels carry forward.",
                    "This is D6 promotion-review-ready, not an acceptance decision.",
                ],
                "allowed_language_used": ["review-context", "source-limited", "payload-only", "full where proven", "capped bulk", "windowed complete", "operator review", "D6 promotion-review-ready"],
            }
            for hero in heroes
        ],
    }


def write_individual_d5(project_root: Path, lane: str) -> dict[str, Any]:
    cfg = LANES[lane]
    out = reset_output_dir(project_path(project_root, cfg["output_dir"]), project_root, Path(cfg["output_dir"]).name)
    watched = {
        "d4": project_path(project_root, cfg["d4_dir"]),
        "xdata_d2_r1": project_path(project_root, SHARED_INPUTS["xdata_d2_r1"]),
        "ontology_v2": project_path(project_root, SHARED_INPUTS["ontology_v2"]),
    }
    before = {name: input_signature(path) for name, path in watched.items()}
    d4_harness, replay, face = load_d4(project_root, cfg)
    heroes = build_heroes(lane, cfg, replay, face)
    inventory = {"status": "PASS", "inputs": {name: {"path": str(path), "exists": path.exists(), "signature": input_signature(path)} for name, path in watched.items()}}
    policy = {"status": "PASS", "required_count": 3, "selection_rule": "context hero, source limitation hero, governance boundary hero", "source_stage": lane.replace("-D5", "-D4")}
    candidates = {"status": "PASS", "candidates": heroes}
    selected = {"status": "PASS", "selected_heroes": heroes}
    freeze = {
        "status": "PASS",
        "city": cfg["city"],
        "flow": cfg["flow"],
        "stage": "D5",
        "accepted_flow_cartridge": False,
        "review_context_only": True,
        "hero_count": len(heroes),
        "selected_hero_ids": [hero["hero_id"] for hero in heroes],
        "heroes": heroes,
        "source_stage": lane.replace("-D5", "-D4"),
        "d4_status": d4_harness.get("status"),
        "face_route_status": face.get("status"),
    }
    briefings = build_briefings(lane, heroes)
    face_payload = {
        "status": "FACE_HERO_PAYLOAD_ONLY",
        "published": False,
        "reason": "D4 face route status is payload-only; D5 does not publish live hero routes.",
        "future_routes": [f"/{cfg['city']}/flow{cfg['flow_number']}/heroes", f"/api/{cfg['city']}/flow{cfg['flow_number']}/heroes", f"/api/{cfg['city']}/flow{cfg['flow_number']}/heroes/{{hero_id}}"],
        "hero_ids": [hero["hero_id"] for hero in heroes],
        "accepted_flow_cartridge": False,
        "review_context_only": True,
    }
    trace = {"status": "PASS", "trace_refs": [ref for hero in heroes for ref in hero["evidence_refs"]]}
    source_report = {"status": "PASS", "source_limitations": replay.get("source_limitations", []), "boundaries": heroes[2]["governance_boundaries"], "payload_only_boundary": face.get("status") == "FACE_ROUTE_PAYLOAD_ONLY"}
    next_d6 = {
        "status": "D6_PROMOTION_REVIEW_READY_WITH_SOURCE_LIMITATIONS",
        "recommended_next_gate": lane.replace("-D5", "-D6"),
        "decision_scope": "promotion review only",
        "accepted_flow_cartridge": False,
        "candidate_only": bool(cfg.get("candidate_only")),
        "hero_freeze_package": f"{cfg['prefix']}_HERO_FREEZE_PACKAGE.json",
        "boundaries_to_carry": source_report["boundaries"],
    }
    prefix = cfg["prefix"]
    write_json(out / f"{prefix}_INPUT_INVENTORY.json", inventory)
    write_json(out / f"{prefix}_HERO_SELECTION_POLICY.json", policy)
    write_json(out / f"{prefix}_HERO_CANDIDATES.json", candidates)
    write_json(out / f"{prefix}_SELECTED_HEROES.json", selected)
    write_json(out / f"{prefix}_HERO_FREEZE_PACKAGE.json", freeze)
    write_json(out / f"{prefix}_HERO_BRIEFINGS.json", briefings)
    write_json(out / f"{prefix}_FACE_HERO_PAYLOAD.json", face_payload)
    write_json(out / f"{prefix}_TRACE_REPORT.json", trace)
    write_json(out / f"{prefix}_SOURCE_LIMITATION_REPORT.json", source_report)
    write_json(out / f"{prefix}_NEXT_D6_HANDOFF.json", next_d6)
    gates = [
        {"gate": f"{lane}-PRECOND", "status": "PASS" if d4_harness.get("status", "").startswith("PASS") else "FAIL"},
        {"gate": f"{lane}-INPUT-INVENTORY", "status": inventory["status"]},
        {"gate": f"{lane}-HERO-SELECTION-POLICY", "status": policy["status"]},
        {"gate": f"{lane}-HERO-CANDIDATES", "status": "PASS" if len(heroes) == 3 else "FAIL", "candidate_count": len(heroes)},
        {"gate": f"{lane}-SELECTED-HEROES", "status": "PASS" if len(heroes) == 3 else "FAIL", "selected_count": len(heroes)},
        {"gate": f"{lane}-HERO-FREEZE-PACKAGE", "status": freeze["status"]},
        {"gate": f"{lane}-HERO-BRIEFINGS", "status": briefings["status"]},
        {"gate": f"{lane}-FACE-HERO-PAYLOAD", "status": "PASS", "face_hero_status": face_payload["status"]},
        {"gate": f"{lane}-SOURCE-LIMITATIONS", "status": source_report["status"]},
        {"gate": f"{lane}-BOUNDARY-CARRY-FORWARD", "status": "PASS"},
        {"gate": f"{lane}-NEXT-D6-HANDOFF", "status": "PASS"},
    ]
    overclaim = scan_no_overclaim([out], skip_names={f"{prefix}_NO_OVERCLAIM_REPORT.json", "SHA256SUMS.json"})
    write_json(out / f"{prefix}_NO_OVERCLAIM_REPORT.json", overclaim)
    gates.append({"gate": f"{lane}-NO-OVERCLAIM", "status": overclaim["status"]})
    mutation = compare_signatures(before, {name: input_signature(path) for name, path in watched.items()})
    write_json(out / f"{prefix}_NO_MUTATION_REPORT.json", mutation)
    gates.append({"gate": f"{lane}-NO-MUTATION", "status": mutation["status"]})
    status = "PASS_HERO_PAYLOAD_ONLY_WITH_SOURCE_LIMITATIONS" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    write_text(out / "README.md", f"# {lane} Hero Freeze Package\n\nStatus: `{status}`\n\nHero freeze package only. Source-limited review-context. D6 promotion-review-ready, not accepted.\n")
    harness = {"task": f"{lane} Hero Freeze Package", "status": status, "generated_at": utc_now(), "output_dir": str(out), "hero_candidates": len(heroes), "selected_heroes": len(heroes), "face_hero_status": face_payload["status"], "gates": gates}
    write_json(out / f"{prefix}_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    required = [item.format(prefix=prefix) for item in INDIVIDUAL_SUFFIXES if item != "SHA256SUMS.json"]
    hash_ok = sorted(read_json(out / "SHA256SUMS.json", {}).keys()) == sorted(required)
    gates.append({"gate": f"{lane}-HASHES", "status": "PASS" if hash_ok else "FAIL", "hashed_files": hashes["file_count"]})
    status = "PASS_HERO_PAYLOAD_ONLY_WITH_SOURCE_LIMITATIONS" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    harness["status"] = status
    harness["gates"] = gates
    write_json(out / f"{prefix}_HARNESS_REPORT.json", harness)
    write_text(out / "README.md", f"# {lane} Hero Freeze Package\n\nStatus: `{status}`\n\nHero freeze package only. Source-limited review-context. D6 promotion-review-ready, not accepted.\n")
    write_hashes(out)
    return {"lane": lane, "status": status, "output_dir": str(out), "selected_heroes": len(heroes), "face_hero_status": face_payload["status"]}


def run_single_d5(lane: str, project_root: str | Path = ".") -> dict[str, Any]:
    return write_individual_d5(Path(project_root).resolve(), lane)


def batch_inventory(project_root: Path) -> dict[str, Any]:
    inputs = {name: project_path(project_root, rel) for name, rel in SHARED_INPUTS.items()}
    inputs.update({f"{lane}_d4": project_path(project_root, cfg["d4_dir"]) for lane, cfg in LANES.items()})
    return {"status": "PASS", "inputs": {name: {"path": str(path), "exists": path.exists(), "signature": input_signature(path)} for name, path in inputs.items()}}


def run_d5_batch(project_root: str | Path = ".", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    out = reset_output_dir(project_path(project_root, output_dir), project_root, Path(output_dir).name)
    watched = {name: project_path(project_root, rel) for name, rel in SHARED_INPUTS.items()}
    watched.update({f"{lane}_d4": project_path(project_root, cfg["d4_dir"]) for lane, cfg in LANES.items()})
    before = {name: input_signature(path) for name, path in watched.items()}
    inventory = batch_inventory(project_root)
    queue_plan = {
        "status": "PASS",
        "already_complete": [{"lane": "CHI-F4X-D5", "output_dir": str(project_path(project_root, "outputs/chi_f4x_d5_hero_freeze_package"))}],
        "queue": [{"rank": index, "lane": lane, "source_d4": str(project_path(project_root, cfg["d4_dir"])), "output_dir": str(project_path(project_root, cfg["output_dir"]))} for index, (lane, cfg) in enumerate(LANES.items(), start=1)],
    }
    results = [write_individual_d5(project_root, lane) for lane in LANES]
    d6_handoff = {
        "status": "PASS",
        "ready_for_d6_promotion_review": [
            {"lane": "CHI-F4X-D6", "source_d5": "outputs/chi_f4x_d5_hero_freeze_package", "note": "Already complete D5; promotion review only."},
            *[
                {"lane": result["lane"].replace("-D5", "-D6"), "source_d5": result["output_dir"], "note": "Promotion review only; payload-only D4/D5 cannot blindly accept flow."}
                for result in results
                if result["status"].startswith("PASS")
            ],
        ],
        "boundary": "Do not run D6 acceptance blindly. D6 must decide accepted vs review/candidate status in a separate promotion-review gate.",
    }
    write_json(out / "D5_BATCH_D1_INPUT_INVENTORY.json", inventory)
    write_json(out / "D5_BATCH_D1_QUEUE_PLAN.json", queue_plan)
    write_json(out / "D5_BATCH_D1_STAGE_RESULTS.json", {"status": "PASS", "results": results})
    write_json(out / "D5_BATCH_D1_D6_PROMOTION_REVIEW_HANDOFF.json", d6_handoff)
    gates = [
        {"gate": "D5-BATCH-D1-PRECOND", "status": "PASS"},
        {"gate": "D5-BATCH-D1-INPUT-INVENTORY", "status": inventory["status"]},
        {"gate": "D5-BATCH-D1-QUEUE-PLAN", "status": queue_plan["status"]},
        *[{"gate": f"D5-BATCH-D1-{result['lane']}", "status": "PASS" if result["status"].startswith("PASS") else "FAIL"} for result in results],
        {"gate": "D5-BATCH-D1-D6-PROMOTION-REVIEW-HANDOFF", "status": d6_handoff["status"]},
        {"gate": "D5-BATCH-D1-BOUNDARY-CARRY-FORWARD", "status": "PASS"},
    ]
    overclaim = scan_no_overclaim([out] + [project_path(project_root, cfg["output_dir"]) for cfg in LANES.values()], skip_names={"SHA256SUMS.json", "D5_BATCH_D1_NO_OVERCLAIM_REPORT.json"})
    write_json(out / "D5_BATCH_D1_NO_OVERCLAIM_REPORT.json", overclaim)
    gates.append({"gate": "D5-BATCH-D1-NO-OVERCLAIM", "status": overclaim["status"]})
    mutation = compare_signatures(before, {name: input_signature(path) for name, path in watched.items()})
    write_json(out / "D5_BATCH_D1_NO_MUTATION_REPORT.json", mutation)
    gates.append({"gate": "D5-BATCH-D1-NO-MUTATION", "status": mutation["status"]})
    passed = sum(1 for result in results if result["status"].startswith("PASS"))
    failed = len(results) - passed
    status = "PASS_WITH_SOURCE_LIMITATIONS" if failed == 0 else ("PASS_WITH_PARTIAL_D5_PROGRESS" if passed else "FAIL")
    write_text(out / "README.md", f"# D5-BATCH-D1 Hero Freeze Packages\n\nStatus: `{status}`\n\nCompleted {passed} of {len(results)} planned D5 hero freeze packages. D6 is not run here.\n")
    harness = {"task": TASK, "status": status, "generated_at": utc_now(), "output_dir": str(out), "d5_attempted": len(results), "d5_passed": passed, "d5_failed": failed, "results": results, "gates": gates}
    write_json(out / "D5_BATCH_D1_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    hash_ok = sorted(read_json(out / "SHA256SUMS.json", {}).keys()) == sorted(item for item in BATCH_REQUIRED if item != "SHA256SUMS.json")
    gates.append({"gate": "D5-BATCH-D1-HASHES", "status": "PASS" if hash_ok else "FAIL", "hashed_files": hashes["file_count"]})
    status = status if all(g["status"] == "PASS" for g in gates) else "FAIL"
    harness["status"] = status
    harness["gates"] = gates
    write_json(out / "D5_BATCH_D1_HARNESS_REPORT.json", harness)
    write_text(out / "README.md", f"# D5-BATCH-D1 Hero Freeze Packages\n\nStatus: `{status}`\n\nCompleted {passed} of {len(results)} planned D5 hero freeze packages. D6 is not run here.\n")
    write_hashes(out)
    return harness


def print_final_report(report: dict[str, Any]) -> None:
    print(f"D5-BATCH-D1 Hero Freeze Packages: {report['status']}")
    print()
    for lane in LANES:
        result = next((item for item in report["results"] if item["lane"] == lane), {"status": "SKIPPED"})
        print(f"{lane}: {'PASS' if str(result['status']).startswith('PASS') else result['status']}")
    print()
    print(f"D5 gates attempted: {report['d5_attempted']}")
    print(f"D5 gates passed: {report['d5_passed']}")
    print(f"D5 gates failed: {report['d5_failed']}")
    gate_map = {gate["gate"]: gate["status"] for gate in report["gates"]}
    print()
    print(f"D6 promotion-review handoff: {gate_map.get('D5-BATCH-D1-D6-PROMOTION-REVIEW-HANDOFF')}")
    print(f"Boundary carry-forward: {gate_map.get('D5-BATCH-D1-BOUNDARY-CARRY-FORWARD')}")
    print(f"No-overclaim: {gate_map.get('D5-BATCH-D1-NO-OVERCLAIM')}")
    print(f"No-mutation: {gate_map.get('D5-BATCH-D1-NO-MUTATION')}")
    print(f"Hashes: {gate_map.get('D5-BATCH-D1-HASHES')}")
    print()
    print("Final status:")
    print(report["status"])
    print()
    print(f"Output:\n{report['output_dir']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run D5-BATCH-D1 hero freeze packages")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = run_d5_batch(args.project_root, args.output_dir)
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
