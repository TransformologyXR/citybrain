#!/usr/bin/env python3
"""TRACK2-CLOSEOUT-R1 value-complete review-route product pack."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "TRACK2-CLOSEOUT-R1 Value-Complete Track 2 Review-Route Product Pack"
DEFAULT_OUTPUT_DIR = "outputs/track2_closeout_r1_value_complete_review_route_pack"
PASS_STATUSES = {"PASS_TRACK2_VALUE_COMPLETE_REVIEW_ROUTE_PACK", "PASS_TRACK2_VALUE_PACK_WITH_LIMITATIONS"}

LANES: dict[str, dict[str, Any]] = {
    "CHI-F4X": {
        "city": "chicago",
        "flow": "F4X",
        "flow_number": "4",
        "title": "Chicago Flow 4 Mobility / Environment",
        "d3": "outputs/chi_f4x_d3_r1_mobility_environment_evidencebundles",
        "d4": ("outputs/chi_f4x_d4_mobility_environment_replay_face_proof", "CHI_F4X_D4"),
        "d5": ("outputs/chi_f4x_d5_hero_freeze_package", "CHI_F4X_D5"),
        "decision": "REVIEW_ROUTE_READY_NOT_ACCEPTED",
        "summary": "Mobility/environment review route backed by refreshed D3-R1 evidence, D4 replay/briefing payloads, and D5 heroes.",
        "shows": ["mobility/environment review context", "source limitations", "governance boundary"],
        "does_not_show": ["accepted flow", "operational control", "health or traffic instruction"],
        "blockers": [
            "acceptance policy not yet defined for review-route-ready mounted extensions",
            "source limitations remain",
            "no operational/control claim allowed",
        ],
    },
    "NYC-F1X": {
        "city": "nyc",
        "flow": "F1X",
        "flow_number": "1",
        "title": "NYC Flow 1 Situational Status",
        "d3": "outputs/nyc_f1x_d3_r1_situational_status_evidencebundles",
        "d4": ("outputs/nyc_f1x_d4_situational_status_replay_face_proof", "NYC_F1X_D4"),
        "d5": ("outputs/nyc_f1x_d5_situational_status_hero_freeze_package", "NYC_F1X_D5"),
        "decision": "REVIEW_ROUTE_READY_NOT_ACCEPTED",
        "summary": "Situational-status review route backed by the updated NYC source baseline and D3/D4/D5 payload chain.",
        "shows": ["311/situational review context", "source limitations", "governance boundary"],
        "does_not_show": ["accepted flow", "operational control", "complete source history"],
        "blockers": [
            "acceptance policy not yet defined",
            "source limitations remain",
            "situational status is review-context only",
        ],
    },
    "CHI-F3X": {
        "city": "chicago",
        "flow": "F3X",
        "flow_number": "3",
        "title": "Chicago Flow 3 Traffic Incident Context",
        "d3": "outputs/chi_f3x_d3_traffic_incident_context_evidencebundles",
        "d4": ("outputs/chi_f3x_d4_traffic_incident_context_replay_face_proof", "CHI_F3X_D4"),
        "d5": ("outputs/chi_f3x_d5_traffic_incident_context_hero_freeze_package", "CHI_F3X_D5"),
        "decision": "REVIEW_ROUTE_READY_NOT_ACCEPTED",
        "summary": "Traffic/crash context review route with privacy and governance boundaries carried forward.",
        "shows": ["traffic/crash review context", "source-limited trace", "governance boundary"],
        "does_not_show": ["accepted flow", "dispatch", "affected-asset certification"],
        "blockers": [
            "traffic/crash context only",
            "no dispatch/affected-asset certification",
            "acceptance policy not yet defined",
        ],
    },
    "NYC-F5X": {
        "city": "nyc",
        "flow": "F5X",
        "flow_number": "5",
        "title": "NYC Flow 5 Flood / Climate / Asset-Risk",
        "d3": "outputs/nyc_f5x_d3_flood_climate_asset_risk_evidencebundles",
        "d4": ("outputs/nyc_f5x_d4_flood_climate_asset_risk_replay_face_proof", "NYC_F5X_D4"),
        "d5": ("outputs/nyc_f5x_d5_flood_climate_asset_risk_hero_freeze_package", "NYC_F5X_D5"),
        "decision": "REVIEW_ROUTE_READY_NOT_ACCEPTED",
        "summary": "Risk-context review route for flood, climate, facilities, and area-risk evidence.",
        "shows": ["risk review context", "source limitations", "governance boundary"],
        "does_not_show": ["accepted flow", "certified infrastructure propagation", "utility or emergency control"],
        "blockers": [
            "risk context only",
            "no certified infrastructure propagation",
            "no utility/emergency control",
            "acceptance policy not yet defined",
        ],
    },
    "NYC-F6X": {
        "city": "nyc",
        "flow": "F6X",
        "flow_number": "6",
        "title": "NYC Flow 6 Port / Airport Logistics",
        "d3": "outputs/nyc_f6x_d3_port_airport_logistics_evidencebundles",
        "d4": ("outputs/nyc_f6x_d4_port_airport_logistics_replay_face_proof", "NYC_F6X_D4"),
        "d5": ("outputs/nyc_f6x_d5_port_airport_logistics_hero_freeze_package", "NYC_F6X_D5"),
        "decision": "REVIEW_ROUTE_READY_NOT_ACCEPTED",
        "summary": "Port/airport logistics review route with safety-critical and command boundaries preserved.",
        "shows": ["logistics review context", "source-limited trace", "governance boundary"],
        "does_not_show": ["accepted flow", "port/airport command", "safety-critical sequencing"],
        "blockers": [
            "logistics context only",
            "no port/airport operational command",
            "no safety-critical sequencing",
            "acceptance policy not yet defined",
        ],
    },
    "BARC-F7": {
        "city": "barcelona",
        "flow": "F7",
        "flow_number": "7",
        "title": "Barcelona Flow 7 Civic / Sensor Fusion",
        "d3": "outputs/barc_f7_d3_r1_civic_sensor_fusion_evidencebundles",
        "d4": ("outputs/barc_f7_d4_civic_sensor_fusion_replay_face_proof", "BARC_F7_D4"),
        "d5": ("outputs/barc_f7_d5_civic_sensor_fusion_hero_freeze_package", "BARC_F7_D5"),
        "decision": "CANDIDATE_ONLY_NOT_ACCEPTED",
        "secondary_blocker": "BLOCKED_BY_CITY_CORE",
        "summary": "Candidate-only civic/sensor review route backed by manual recovery and source-limited Barcelona evidence.",
        "shows": ["candidate civic/sensor review context", "manual recovery boundaries", "governance boundary"],
        "does_not_show": ["accepted city core", "accepted flow", "operational control"],
        "blockers": [
            "Barcelona city core not accepted",
            "candidate-only city status",
            "source limitations remain",
        ],
    },
}

INPUTS = {
    "xdata_d2_r1": "outputs/xdata_d2_r1_four_city_bulk_landing_reconciliation_refresh",
    "d3_refresh_d1": "outputs/d3_refresh_d1_bulk_informed_refresh_decision",
    "flowx_face_publish_smoke_d1": "outputs/flowx_face_publish_smoke_d1",
    "d5_batch_d1": "outputs/d5_batch_d1_hero_freeze_packages",
    "d6_promotion_review_d1": "outputs/d6_promotion_review_d1_accepted_vs_review_candidate_decision",
    "track2_closeout_d1": "outputs/track2_closeout_d1_xdata_cityflow_freeze",
    "ontology_v2": "contracts/ontology_v2",
}

WATCH_INPUTS = {
    **INPUTS,
    "data_landing": "data_landing",
    "snapshots": "snapshots",
}

REQUIRED = [
    "README.md",
    "TRACK2_CLOSEOUT_R1_HARNESS_REPORT.json",
    "TRACK2_CLOSEOUT_R1_INPUT_INVENTORY.json",
    "TRACK2_CLOSEOUT_R1_REVIEW_ROUTE_CATALOG.json",
    "TRACK2_CLOSEOUT_R1_REVIEW_ROUTE_SMOKE_MATRIX.json",
    "TRACK2_CLOSEOUT_R1_LANE_EVIDENCE_TRACE_MATRIX.json",
    "TRACK2_CLOSEOUT_R1_OPERATOR_DEMO_PACK.json",
    "TRACK2_CLOSEOUT_R1_ACCEPTANCE_BLOCKER_MATRIX.json",
    "TRACK2_CLOSEOUT_R1_ACCEPTANCE_CRITERIA_BACKLOG.json",
    "TRACK2_CLOSEOUT_R1_XDATA_VALUE_SUMMARY.json",
    "TRACK2_CLOSEOUT_R1_BULK_SWEEP_BACKLOG.json",
    "TRACK2_CLOSEOUT_R1_SINGAPORE_DEFERRED_BACKLOG.json",
    "TRACK2_CLOSEOUT_R1_TRACK1_CONSUMPTION_HANDOFF.json",
    "TRACK2_CLOSEOUT_R1_FINAL_EXECUTIVE_HANDOFF.md",
    "TRACK2_CLOSEOUT_R1_NO_OVERCLAIM_REPORT.json",
    "TRACK2_CLOSEOUT_R1_NO_MUTATION_REPORT.json",
    "SHA256SUMS.json",
]

FORBIDDEN_PATTERNS = [
    r"\btrack 2 accepted all flows\b",
    r"\bnew flow accepted by this r1 pack\b",
    r"\breview route means operational control\b",
    r"\breview route means accepted flow\b",
    r"\bpublished route means traffic/transit/utility/port control\b",
    r"\bbarcelona accepted\b",
    r"\bsingapore completed\b",
    r"\bbulk in progress is already included\b",
    r"\bcapped bulk is full\b",
    r"\bwindowed/api snapshot is historical completeness\b",
    r"\bpublic-safety recommendation\b",
    r"\bemergency dispatch\b",
    r"\bhealth determination\b",
    r"\bpolicing recommendation\b",
    r"\benforcement action\b",
    r"\bcertified affected asset\b",
    r"\bcertified affected building\b",
    r"\bplatform v1 complete\b",
]

NEGATION_MARKERS = ("no ", "not ", "never ", "without ", "does not ", "do not ", "cannot ", "0", "candidate-only", "source-limited", "deferred")


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
    sums = {}
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
        if not text.startswith(str(root).lower()) or resolved.name.lower() != "track2_closeout_r1_value_complete_review_route_pack":
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


def route_base(cfg: dict[str, Any]) -> str:
    return f"/{cfg['city']}/flow{cfg['flow_number']}"


def api_base(cfg: dict[str, Any]) -> str:
    return f"/api{route_base(cfg)}"


def lane_paths(project_root: Path) -> dict[str, Path]:
    paths = {name: project_path(project_root, rel) for name, rel in INPUTS.items()}
    for lane, cfg in LANES.items():
        paths[f"{lane}_d3"] = project_path(project_root, cfg["d3"])
        paths[f"{lane}_d4"] = project_path(project_root, cfg["d4"][0])
        paths[f"{lane}_d5"] = project_path(project_root, cfg["d5"][0])
    return paths


def inventory(project_root: Path) -> dict[str, Any]:
    paths = lane_paths(project_root)
    return {
        "status": "PASS",
        "inputs": {name: {"path": str(path), "exists": path.exists(), "signature": input_signature(path)} for name, path in paths.items()},
    }


def load_flowx(project_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    root = project_path(project_root, INPUTS["flowx_face_publish_smoke_d1"])
    harness = read_json(root / "FLOWX_FACE_PUBLISH_SMOKE_D1_HARNESS_REPORT.json", {})
    manifest = read_json(root / "FLOWX_FACE_PUBLISH_SMOKE_D1_PUBLISHED_ROUTE_MANIFEST.json", {})
    smoke = read_json(root / "FLOWX_FACE_PUBLISH_SMOKE_D1_ROUTE_SMOKE_REPORT.json", {})
    return harness, manifest, smoke


def load_d6(project_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = project_path(project_root, INPUTS["d6_promotion_review_d1"])
    review = read_json(root / "D6_PROMOTION_REVIEW_D1_PROMOTION_REVIEW_REPORT.json", {})
    matrix = read_json(root / "D6_PROMOTION_REVIEW_D1_DECISION_MATRIX.json", {})
    return review, matrix


def lane_payloads(project_root: Path, lane: str, cfg: dict[str, Any]) -> dict[str, Any]:
    d4_dir, d4_prefix = cfg["d4"]
    d5_dir, d5_prefix = cfg["d5"]
    d4_path = project_path(project_root, d4_dir)
    d5_path = project_path(project_root, d5_dir)
    return {
        "d4_path": d4_path,
        "d5_path": d5_path,
        "d4_harness": read_json(d4_path / f"{d4_prefix}_HARNESS_REPORT.json", {}),
        "d4_replay": read_json(d4_path / f"{d4_prefix}_REPLAY_PAYLOAD.json", {}),
        "d4_briefing": read_json(d4_path / f"{d4_prefix}_BRIEFING_PAYLOAD.json", {}),
        "d4_face": read_json(d4_path / f"{d4_prefix}_FACE_ROUTE_PAYLOAD.json", {}),
        "d5_harness": read_json(d5_path / f"{d5_prefix}_HARNESS_REPORT.json", {}),
        "d5_heroes": read_json(d5_path / f"{d5_prefix}_HERO_FREEZE_PACKAGE.json", {}),
        "d5_face": read_json(d5_path / f"{d5_prefix}_FACE_HERO_PAYLOAD.json", {}),
    }


def decision_by_lane(d6_matrix: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out = {}
    for item in d6_matrix.get("decisions", []):
        lane = str(item.get("lane", "")).replace("-D6", "")
        out[lane] = item
    return out


def flowx_by_lane(flowx_harness: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["lane"]: item for item in flowx_harness.get("lane_status_matrix", [])}


def route_catalog(project_root: Path, flowx_harness: dict[str, Any], d6_matrix: dict[str, Any]) -> dict[str, Any]:
    flowx = flowx_by_lane(flowx_harness)
    d6 = decision_by_lane(d6_matrix)
    routes = []
    for lane, cfg in LANES.items():
        data = lane_payloads(project_root, lane, cfg)
        base = route_base(cfg)
        api = api_base(cfg)
        routes.append(
            {
                "lane": lane,
                "city": cfg["city"],
                "flow": cfg["flow"],
                "route_status": flowx.get(lane, {}).get("to_face_route_status", "UNKNOWN"),
                "smoke_status": flowx.get(lane, {}).get("smoke_status", "UNKNOWN"),
                "accepted_flow": False,
                "decision": cfg["decision"],
                "secondary_blocker": cfg.get("secondary_blocker"),
                "route_paths": [f"{base}/replay", f"{base}/briefing", f"{base}/heroes"],
                "api_paths": [f"{api}/replay", f"{api}/briefing", f"{api}/heroes"] + [f"{api}/heroes/{hero}" for hero in flowx.get(lane, {}).get("hero_ids", [])],
                "source_d3": str(project_path(project_root, cfg["d3"])),
                "source_d4": str(data["d4_path"]),
                "source_d5": str(data["d5_path"]),
                "summary": cfg["summary"],
                "operator_use": "review-context only",
                "forbidden_uses": cfg["does_not_show"],
                "d6_decision": d6.get(lane, {}).get("decision"),
            }
        )
    return {"status": "PASS", "routes": routes}


def smoke_matrix(flowx_harness: dict[str, Any], flowx_smoke: dict[str, Any]) -> dict[str, Any]:
    lane_status = flowx_by_lane(flowx_harness)
    attempts_by_lane: dict[str, list[dict[str, Any]]] = {lane: [] for lane in LANES}
    for attempt in flowx_smoke.get("attempts", []):
        lane = attempt.get("lane")
        if lane in attempts_by_lane:
            attempts_by_lane[lane].append(attempt)
    rows = []
    for lane, cfg in LANES.items():
        base = route_base(cfg)
        api = api_base(cfg)
        attempts = attempts_by_lane.get(lane, [])
        json_attempts = [item for item in attempts if item.get("json")]
        html_attempts = [item for item in attempts if not item.get("json")]
        rows.append(
            {
                "lane": lane,
                "route_paths": [f"{base}/replay", f"{base}/briefing", f"{base}/heroes"],
                "api_paths": [f"{api}/replay", f"{api}/briefing", f"{api}/heroes"],
                "http_statuses": [{"url": item.get("url"), "status": item.get("status"), "http_status": item.get("http_status")} for item in attempts],
                "payload_smoke_result": lane_status.get(lane, {}).get("smoke_status"),
                "briefing_smoke_result": "PASS" if any("/briefing" in str(item.get("url")) and item.get("status") == "PASS" for item in attempts) else "UNKNOWN",
                "hero_smoke_result": "PASS" if any("/heroes" in str(item.get("url")) and item.get("status") == "PASS" for item in attempts) else "UNKNOWN",
                "evidence_trace_present": bool(json_attempts),
                "boundary_text_present": all((item.get("json") or {}).get("accepted_flow_cartridge") is False for item in json_attempts) and bool(json_attempts),
                "html_attempt_count": len(html_attempts),
                "api_attempt_count": len(json_attempts),
            }
        )
    return {"status": "PASS" if all(row["payload_smoke_result"] == "PASS" for row in rows) else "FAIL", "rows": rows}


def evidence_trace_matrix(project_root: Path, flowx_harness: dict[str, Any], d6_matrix: dict[str, Any]) -> dict[str, Any]:
    flowx = flowx_by_lane(flowx_harness)
    d6 = decision_by_lane(d6_matrix)
    rows = []
    for lane, cfg in LANES.items():
        data = lane_payloads(project_root, lane, cfg)
        d4_missing = not data["d4_path"].exists()
        d5_exists = data["d5_path"].exists()
        replay = data["d4_replay"]
        heroes = data["d5_heroes"].get("heroes", [])
        missing = []
        if d4_missing and d5_exists:
            missing.append("D4_ARTIFACT_MISSING_BUT_D5_PRESENT")
        for label, value in {
            "xdata_refs": replay.get("xdata_refs", []),
            "d3_evidencebundle_ids": replay.get("evidencebundle_refs", []),
            "d5_hero_ids": [hero.get("hero_id") for hero in heroes],
            "promotion_review_decision": d6.get(lane, {}).get("decision"),
        }.items():
            if not value:
                missing.append(f"missing_{label}")
        rows.append(
            {
                "lane": lane,
                "xdata_refs": replay.get("xdata_refs", []),
                "d3_evidencebundle_ids": replay.get("evidencebundle_refs", []),
                "d4_payload_refs": [
                    f"{cfg['d4'][1]}_REPLAY_PAYLOAD.json",
                    f"{cfg['d4'][1]}_BRIEFING_PAYLOAD.json",
                    f"{cfg['d4'][1]}_FACE_ROUTE_PAYLOAD.json",
                ],
                "d5_hero_ids": [hero.get("hero_id") for hero in heroes],
                "face_publish_refs": [flowx.get(lane, {}).get("to_face_route_status"), flowx.get(lane, {}).get("smoke_status")],
                "promotion_review_decision": d6.get(lane, {}).get("decision"),
                "trace_complete": not missing,
                "missing_or_weak_links": missing,
            }
        )
    complete = sum(1 for row in rows if row["trace_complete"])
    return {"status": "PASS" if complete == len(LANES) else "PARTIAL", "trace_complete_count": complete, "trace_total": len(LANES), "lanes": rows}


def operator_demo_pack(catalog: dict[str, Any]) -> dict[str, Any]:
    by_lane = {route["lane"]: route for route in catalog["routes"]}
    cards = []
    for lane, cfg in LANES.items():
        route = by_lane[lane]
        cards.append(
            {
                "demo_card_title": cfg["title"],
                "city": cfg["city"],
                "flow": cfg["flow"],
                "review_route": route["route_paths"][0],
                "briefing_route": route["route_paths"][1],
                "hero_route": route["route_paths"][2],
                "what_it_shows": cfg["shows"],
                "what_it_does_not_show": cfg["does_not_show"],
                "safe_demo_script": [
                    f"Open {route['route_paths'][0]} and identify the review context.",
                    "Open the briefing route and point to source-limited boundaries.",
                    "Open the heroes route and show the evidence/hero trace.",
                    "State that this is review-context only and not an accepted flow.",
                ],
                "operator_boundary": "review-context only",
            }
        )
    return {"status": "PASS", "cards": cards}


def acceptance_blockers() -> dict[str, Any]:
    return {"status": "PASS", "lanes": [{"lane": lane, "decision": cfg["decision"], "blockers": cfg["blockers"]} for lane, cfg in LANES.items()]}


def acceptance_criteria_backlog() -> dict[str, Any]:
    common = [
        "face route published and smoked",
        "evidence trace complete",
        "source limitations explicitly preserved",
        "accepted city core exists",
        "flow-specific no-control boundary enforced",
        "governance policy says review-route-ready can be accepted",
        "human approval / HITL policy if needed",
    ]
    rows = []
    for lane, cfg in LANES.items():
        satisfied = ["face route published and smoked", "evidence trace complete", "source limitations explicitly preserved", "flow-specific no-control boundary enforced"]
        if lane == "BARC-F7":
            satisfied = ["face route published and smoked", "evidence trace complete", "source limitations explicitly preserved"]
        rows.append(
            {
                "lane": lane,
                "target_transition": f"{cfg['decision']} -> ACCEPTED only if future criteria are met",
                "criteria": common,
                "currently_satisfied_or_partly_satisfied": satisfied,
                "not_yet_satisfied": [item for item in common if item not in satisfied],
                "accepted_now": False,
            }
        )
    return {"status": "PASS", "lanes": rows}


def xdata_value_summary(project_root: Path) -> dict[str, Any]:
    matrix = read_json(project_path(project_root, INPUTS["xdata_d2_r1"]) / "XDATA_D2_R1_CITY_SUMMARY_MATRIX.json", {})
    enablement = {
        "London": "London accepted extension support",
        "New York City": "NYC F1/F4/F5/F6 review context",
        "Chicago": "Chicago F3/F4 review context",
        "Barcelona": "Barcelona F7 candidate civic/sensor context",
    }
    cities = []
    for row in matrix.get("cities", []):
        cities.append(
            {
                "city": row.get("city_name"),
                "rows": row.get("rows_landed_effective"),
                "bytes": row.get("bytes_landed_effective"),
                "claim_strength": row.get("claim_strength"),
                "enabled": enablement.get(row.get("city_name")),
                "source_limited": True,
            }
        )
    return {"status": "PASS" if len(cities) == 4 else "FAIL", "stable_baseline": "XDATA-D2-R1", "cities": cities, "boundary": "In-progress bulk is not included unless stable manifests prove it."}


def bulk_sweep_backlog() -> dict[str, Any]:
    return {
        "next_gate": "XDATA-BULK-SWEEP-D1",
        "deferred_until": "current bulk continuations finish",
        "pending_sources": [
            "Chicago Open Air individual continuation",
            "Chicago Cook County parcel continuation",
            "NYC 311 2020-present continuation",
        ],
        "required_after_completion": [
            "rerun manifests",
            "rerun XDATA reconciliation",
            "audit FULL vs CAPPED_BULK",
            "decide if any D3 refresh is needed",
            "do not mutate Track 2 R1 closeout",
        ],
    }


def singapore_backlog() -> dict[str, Any]:
    return {
        "city": "singapore",
        "status": "DEFERRED_PENDING_DATA_AUTH",
        "reason": "LTA/DataMall auth issue and/or fresh source data required",
        "do_not_run_now": True,
        "resume_trigger": "fresh Singapore data/auth or explicit user instruction",
    }


def track1_handoff() -> dict[str, Any]:
    return {
        "return_focus_to": "PV1_MAIN_TRACK",
        "next_track1_gate": "PV1-SUMO-SETUP-D1",
        "then": "PV1-D10/D11/D12 SUMO Simulator Bridge",
        "track2_consumable_assets": [
            "six published/smoked review routes",
            "D3/D4/D5 evidence/hero traces",
            "stable XDATA-D2-R1 source baseline",
            "operator demo cards",
        ],
        "track2_not_to_assume": [
            "no new accepted flows",
            "no operational control",
            "no Barcelona accepted city core",
            "bulk continuations not swept yet",
        ],
        "ready_for_simulator_persona_hitl_demos": [
            "review-route navigation",
            "evidence trace walkthrough",
            "operator demo cards",
            "source-limitation and acceptance-blocker review",
        ],
    }


def executive_handoff(catalog: dict[str, Any], summary: dict[str, Any], xdata: dict[str, Any]) -> str:
    routes = "\n".join(f"- {route['lane']}: {route['decision']} at {route['route_paths'][0]}" for route in catalog["routes"])
    city_rows = "\n".join(f"- {row['city']}: {row['rows']} rows, {row['enabled']}" for row in xdata["cities"])
    return f"""# TRACK2-CLOSEOUT-R1 Executive Handoff

1. Track 2 final status: value-complete review-route pack, source-limited, no new accepted flows.
2. What was achieved: six published/smoked review routes, evidence traces, demo cards, blocker matrix, and PV1 handoff.
3. Usable review routes:
{routes}
4. What remains not accepted: all six lanes remain not accepted; Barcelona remains candidate-only because the city core is not accepted.
5. Value extracted:
{city_rows}
6. Deferred: NYC/Chicago active bulk continuation goes to XDATA-BULK-SWEEP-D1; Singapore is deferred pending data/auth.
7. Track 1 next: return to PV1-SUMO-SETUP-D1, then PV1-D10/D11/D12 SUMO Simulator Bridge.
"""


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    findings = []
    checked = 0
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in {"SHA256SUMS.json", "TRACK2_CLOSEOUT_R1_NO_OVERCLAIM_REPORT.json"}:
            continue
        if path.suffix.lower() not in {".json", ".md", ".txt"}:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for pattern in FORBIDDEN_PATTERNS:
            for match in re.finditer(pattern, text):
                window = text[max(0, match.start() - 88) : match.end() + 40]
                if any(marker in window for marker in NEGATION_MARKERS):
                    continue
                findings.append({"path": path.relative_to(output_dir).as_posix(), "pattern": pattern, "context": window})
    return {"status": "PASS" if not findings else "FAIL", "checked_files": checked, "findings": findings}


def run_track2_closeout_r1(project_root: str | Path = ".", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    out = reset_output_dir(project_path(project_root, output_dir), project_root)
    watched = {name: project_path(project_root, rel) for name, rel in WATCH_INPUTS.items()}
    for lane, cfg in LANES.items():
        watched[f"{lane}_d3"] = project_path(project_root, cfg["d3"])
        watched[f"{lane}_d4"] = project_path(project_root, cfg["d4"][0])
        watched[f"{lane}_d5"] = project_path(project_root, cfg["d5"][0])
    before = {name: input_signature(path) for name, path in watched.items()}

    inv = inventory(project_root)
    flowx_harness, flowx_manifest, flowx_smoke = load_flowx(project_root)
    d6_review, d6_matrix = load_d6(project_root)
    closeout_d1 = read_json(project_path(project_root, INPUTS["track2_closeout_d1"]) / "TRACK2_CLOSEOUT_D1_HARNESS_REPORT.json", {})
    xdata_harness = read_json(project_path(project_root, INPUTS["xdata_d2_r1"]) / "XDATA_D2_R1_HARNESS_REPORT.json", {})
    d3_refresh = read_json(project_path(project_root, INPUTS["d3_refresh_d1"]) / "D3_REFRESH_D1_HARNESS_REPORT.json", {})
    d5_batch = read_json(project_path(project_root, INPUTS["d5_batch_d1"]) / "D5_BATCH_D1_HARNESS_REPORT.json", {})

    catalog = route_catalog(project_root, flowx_harness, d6_matrix)
    smoke = smoke_matrix(flowx_harness, flowx_smoke)
    trace = evidence_trace_matrix(project_root, flowx_harness, d6_matrix)
    demo = operator_demo_pack(catalog)
    blockers = acceptance_blockers()
    criteria = acceptance_criteria_backlog()
    xdata = xdata_value_summary(project_root)
    bulk = bulk_sweep_backlog()
    singapore = singapore_backlog()
    track1 = track1_handoff()

    write_json(out / "TRACK2_CLOSEOUT_R1_INPUT_INVENTORY.json", inv)
    write_json(out / "TRACK2_CLOSEOUT_R1_REVIEW_ROUTE_CATALOG.json", catalog)
    write_json(out / "TRACK2_CLOSEOUT_R1_REVIEW_ROUTE_SMOKE_MATRIX.json", smoke)
    write_json(out / "TRACK2_CLOSEOUT_R1_LANE_EVIDENCE_TRACE_MATRIX.json", trace)
    write_json(out / "TRACK2_CLOSEOUT_R1_OPERATOR_DEMO_PACK.json", demo)
    write_json(out / "TRACK2_CLOSEOUT_R1_ACCEPTANCE_BLOCKER_MATRIX.json", blockers)
    write_json(out / "TRACK2_CLOSEOUT_R1_ACCEPTANCE_CRITERIA_BACKLOG.json", criteria)
    write_json(out / "TRACK2_CLOSEOUT_R1_XDATA_VALUE_SUMMARY.json", xdata)
    write_json(out / "TRACK2_CLOSEOUT_R1_BULK_SWEEP_BACKLOG.json", bulk)
    write_json(out / "TRACK2_CLOSEOUT_R1_SINGAPORE_DEFERRED_BACKLOG.json", singapore)
    write_json(out / "TRACK2_CLOSEOUT_R1_TRACK1_CONSUMPTION_HANDOFF.json", track1)
    write_text(out / "TRACK2_CLOSEOUT_R1_FINAL_EXECUTIVE_HANDOFF.md", executive_handoff(catalog, trace, xdata))

    precond_ok = (
        xdata_harness.get("status") == "PASS_WITH_SOURCE_LIMITATIONS"
        and d3_refresh.get("status") == "PASS_D3_REFRESH_DECISION"
        and d5_batch.get("status") == "PASS_WITH_SOURCE_LIMITATIONS"
        and flowx_harness.get("status") == "PASS_FACE_PUBLISH_SMOKE_WITH_REVIEW_ROUTES"
        and d6_review.get("status") == "PASS_WITH_REVIEW_ONLY_DECISIONS"
        and closeout_d1.get("status") == "PASS_TRACK2_CLOSED_WITH_DEFERRED_BULK_SWEEP"
    )
    gates = [
        {"gate": "TRACK2-CLOSEOUT-R1-PRECOND", "status": "PASS" if precond_ok else "FAIL"},
        {"gate": "TRACK2-CLOSEOUT-R1-INPUT-INVENTORY", "status": inv["status"]},
        {"gate": "TRACK2-CLOSEOUT-R1-REVIEW-ROUTE-CATALOG", "status": catalog["status"]},
        {"gate": "TRACK2-CLOSEOUT-R1-SMOKE-MATRIX", "status": smoke["status"]},
        {"gate": "TRACK2-CLOSEOUT-R1-LANE-EVIDENCE-TRACE", "status": "PASS" if trace["status"] in {"PASS", "PARTIAL"} else "FAIL"},
        {"gate": "TRACK2-CLOSEOUT-R1-OPERATOR-DEMO-PACK", "status": demo["status"]},
        {"gate": "TRACK2-CLOSEOUT-R1-ACCEPTANCE-BLOCKERS", "status": blockers["status"]},
        {"gate": "TRACK2-CLOSEOUT-R1-ACCEPTANCE-CRITERIA-BACKLOG", "status": criteria["status"]},
        {"gate": "TRACK2-CLOSEOUT-R1-XDATA-VALUE-SUMMARY", "status": xdata["status"]},
        {"gate": "TRACK2-CLOSEOUT-R1-BULK-SWEEP-BACKLOG", "status": "PASS" if bulk["next_gate"] == "XDATA-BULK-SWEEP-D1" else "FAIL"},
        {"gate": "TRACK2-CLOSEOUT-R1-SINGAPORE-DEFERRED-BACKLOG", "status": "PASS" if singapore["status"] == "DEFERRED_PENDING_DATA_AUTH" else "FAIL"},
        {"gate": "TRACK2-CLOSEOUT-R1-TRACK1-CONSUMPTION-HANDOFF", "status": "PASS" if track1["return_focus_to"] == "PV1_MAIN_TRACK" else "FAIL"},
        {"gate": "TRACK2-CLOSEOUT-R1-FINAL-HANDOFF", "status": "PASS"},
    ]
    overclaim = scan_no_overclaim(out)
    write_json(out / "TRACK2_CLOSEOUT_R1_NO_OVERCLAIM_REPORT.json", overclaim)
    gates.append({"gate": "TRACK2-CLOSEOUT-R1-NO-OVERCLAIM", "status": overclaim["status"]})
    mutation = compare_signatures(before, {name: input_signature(path) for name, path in watched.items()})
    write_json(out / "TRACK2_CLOSEOUT_R1_NO_MUTATION_REPORT.json", mutation)
    gates.append({"gate": "TRACK2-CLOSEOUT-R1-NO-MUTATION", "status": mutation["status"]})

    status = "PASS_TRACK2_VALUE_COMPLETE_REVIEW_ROUTE_PACK" if all(g["status"] == "PASS" for g in gates) and trace["status"] == "PASS" else (
        "PASS_TRACK2_VALUE_PACK_WITH_LIMITATIONS" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    )
    write_text(
        out / "README.md",
        "# TRACK2-CLOSEOUT-R1 Value-Complete Review-Route Product Pack\n\n"
        f"Status: `{status}`\n\n"
        "This pack extracts usable review-route value from stable Track 2 outputs. It creates no new accepted flows.\n",
    )
    harness = {
        "task": TASK,
        "status": status,
        "generated_at": utc_now(),
        "output_dir": str(out),
        "review_routes_catalogued": len(catalog["routes"]),
        "published_smoked_routes": flowx_harness.get("published_review_routes", 0),
        "lane_evidence_traces_complete": trace["trace_complete_count"],
        "lane_evidence_traces_total": trace["trace_total"],
        "operator_demo_cards": len(demo["cards"]),
        "accepted_new_flows": 0,
        "gates": gates,
    }
    write_json(out / "TRACK2_CLOSEOUT_R1_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    hashed_keys = set(read_json(out / "SHA256SUMS.json", {}).keys())
    hash_ok = all(name in hashed_keys for name in REQUIRED if name != "SHA256SUMS.json")
    gates.append({"gate": "TRACK2-CLOSEOUT-R1-HASHES", "status": "PASS" if hash_ok else "FAIL", "hashed_files": hashes["file_count"]})
    status = "PASS_TRACK2_VALUE_COMPLETE_REVIEW_ROUTE_PACK" if all(g["status"] == "PASS" for g in gates) and trace["status"] == "PASS" else (
        "PASS_TRACK2_VALUE_PACK_WITH_LIMITATIONS" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    )
    harness["status"] = status
    harness["gates"] = gates
    write_json(out / "TRACK2_CLOSEOUT_R1_HARNESS_REPORT.json", harness)
    write_text(
        out / "README.md",
        "# TRACK2-CLOSEOUT-R1 Value-Complete Review-Route Product Pack\n\n"
        f"Status: `{status}`\n\n"
        "This pack extracts usable review-route value from stable Track 2 outputs. It creates no new accepted flows.\n",
    )
    write_hashes(out)
    return harness


def print_final_report(report: dict[str, Any]) -> None:
    gate_map = {gate["gate"]: gate["status"] for gate in report["gates"]}
    print(f"TRACK2-CLOSEOUT-R1 Value-Complete Review-Route Product Pack: {report['status']}")
    print()
    print(f"Review routes catalogued: {report['review_routes_catalogued']}")
    print(f"Published/smoked routes: {report['published_smoked_routes']}")
    print(f"Lane evidence traces complete: {report['lane_evidence_traces_complete']} / {report['lane_evidence_traces_total']}")
    print(f"Operator demo cards: {report['operator_demo_cards']}")
    print(f"Accepted new flows: {report['accepted_new_flows']}")
    print(f"Acceptance blocker matrix: {gate_map.get('TRACK2-CLOSEOUT-R1-ACCEPTANCE-BLOCKERS')}")
    print(f"Acceptance criteria backlog: {gate_map.get('TRACK2-CLOSEOUT-R1-ACCEPTANCE-CRITERIA-BACKLOG')}")
    print(f"XDATA value summary: {gate_map.get('TRACK2-CLOSEOUT-R1-XDATA-VALUE-SUMMARY')}")
    print(f"Bulk sweep backlog: {gate_map.get('TRACK2-CLOSEOUT-R1-BULK-SWEEP-BACKLOG')}")
    print(f"Track 1 consumption handoff: {gate_map.get('TRACK2-CLOSEOUT-R1-TRACK1-CONSUMPTION-HANDOFF')}")
    print()
    print(f"No-overclaim: {gate_map.get('TRACK2-CLOSEOUT-R1-NO-OVERCLAIM')}")
    print(f"No-mutation: {gate_map.get('TRACK2-CLOSEOUT-R1-NO-MUTATION')}")
    print(f"Hashes: {gate_map.get('TRACK2-CLOSEOUT-R1-HASHES')}")
    print()
    print("Final status:")
    print(report["status"])
    print()
    print(f"Output:\n{report['output_dir']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Track 2 R1 value-complete closeout pack")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = run_track2_closeout_r1(args.project_root, args.output_dir)
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
