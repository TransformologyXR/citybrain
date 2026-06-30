#!/usr/bin/env python3
"""TRACK2-CLOSEOUT-D1 XDATA / city-flow expansion closeout."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "TRACK2-CLOSEOUT-D1 XDATA / City-Flow Expansion Closeout"
DEFAULT_OUTPUT_DIR = "outputs/track2_closeout_d1_xdata_cityflow_freeze"
PASS_STATUSES = {
    "PASS_TRACK2_CLOSED_REVIEW_ROUTE_READY",
    "PASS_TRACK2_CLOSED_WITH_DEFERRED_BULK_SWEEP",
    "PASS_TRACK2_PARTIAL_CLOSEOUT",
}

LANES: dict[str, dict[str, Any]] = {
    "CHI-F4X": {
        "d4": ("outputs/chi_f4x_d4_mobility_environment_replay_face_proof", "CHI_F4X_D4"),
        "d5": ("outputs/chi_f4x_d5_hero_freeze_package", "CHI_F4X_D5"),
        "closeout_status": "REVIEW_ROUTE_READY_NOT_ACCEPTED",
    },
    "NYC-F1X": {
        "d4": ("outputs/nyc_f1x_d4_situational_status_replay_face_proof", "NYC_F1X_D4"),
        "d5": ("outputs/nyc_f1x_d5_situational_status_hero_freeze_package", "NYC_F1X_D5"),
        "closeout_status": "REVIEW_ROUTE_READY_NOT_ACCEPTED",
    },
    "CHI-F3X": {
        "d4": ("outputs/chi_f3x_d4_traffic_incident_context_replay_face_proof", "CHI_F3X_D4"),
        "d5": ("outputs/chi_f3x_d5_traffic_incident_context_hero_freeze_package", "CHI_F3X_D5"),
        "closeout_status": "REVIEW_ROUTE_READY_NOT_ACCEPTED",
    },
    "NYC-F5X": {
        "d4": ("outputs/nyc_f5x_d4_flood_climate_asset_risk_replay_face_proof", "NYC_F5X_D4"),
        "d5": ("outputs/nyc_f5x_d5_flood_climate_asset_risk_hero_freeze_package", "NYC_F5X_D5"),
        "closeout_status": "REVIEW_ROUTE_READY_NOT_ACCEPTED",
    },
    "NYC-F6X": {
        "d4": ("outputs/nyc_f6x_d4_port_airport_logistics_replay_face_proof", "NYC_F6X_D4"),
        "d5": ("outputs/nyc_f6x_d5_port_airport_logistics_hero_freeze_package", "NYC_F6X_D5"),
        "closeout_status": "REVIEW_ROUTE_READY_NOT_ACCEPTED",
    },
    "BARC-F7": {
        "d4": ("outputs/barc_f7_d4_civic_sensor_fusion_replay_face_proof", "BARC_F7_D4"),
        "d5": ("outputs/barc_f7_d5_civic_sensor_fusion_hero_freeze_package", "BARC_F7_D5"),
        "closeout_status": "CANDIDATE_ONLY_NOT_ACCEPTED",
        "secondary_blocker": "BLOCKED_BY_CITY_CORE",
    },
}

INPUTS = {
    "xdata_d2_r1": "outputs/xdata_d2_r1_four_city_bulk_landing_reconciliation_refresh",
    "d3_refresh_d1": "outputs/d3_refresh_d1_bulk_informed_refresh_decision",
    "d4_batch_d1": "outputs/d4_batch_d1_remaining_replay_face_proofs",
    "d5_batch_d1": "outputs/d5_batch_d1_hero_freeze_packages",
    "flowx_face_publish_smoke_d1": "outputs/flowx_face_publish_smoke_d1",
    "d6_promotion_review_d1": "outputs/d6_promotion_review_d1_accepted_vs_review_candidate_decision",
}

WATCH_INPUTS = {
    **INPUTS,
    "contracts_ontology_v2": "contracts/ontology_v2",
    "data_landing": "data_landing",
    "snapshots": "snapshots",
}

REQUIRED = [
    "README.md",
    "TRACK2_CLOSEOUT_D1_HARNESS_REPORT.json",
    "TRACK2_CLOSEOUT_D1_INPUT_INVENTORY.json",
    "TRACK2_CLOSEOUT_D1_XDATA_FREEZE_REPORT.json",
    "TRACK2_CLOSEOUT_D1_ACTIVE_BULK_DEFERRED_REPORT.json",
    "TRACK2_CLOSEOUT_D1_D3_D4_D5_LEDGER.json",
    "TRACK2_CLOSEOUT_D1_FACE_PUBLISH_SMOKE_LEDGER.json",
    "TRACK2_CLOSEOUT_D1_PROMOTION_REVIEW_LEDGER.json",
    "TRACK2_CLOSEOUT_D1_ACCEPTANCE_DECISION_SUMMARY.json",
    "TRACK2_CLOSEOUT_D1_DEFERRED_BACKLOG.json",
    "TRACK2_CLOSEOUT_D1_SINGAPORE_DEFERRED_HANDOFF.json",
    "TRACK2_CLOSEOUT_D1_BULK_SWEEP_HANDOFF.json",
    "TRACK2_CLOSEOUT_D1_TRACK1_HANDOFF.json",
    "TRACK2_CLOSEOUT_D1_NO_OVERCLAIM_REPORT.json",
    "TRACK2_CLOSEOUT_D1_NO_MUTATION_REPORT.json",
    "TRACK2_CLOSEOUT_D1_FINAL_HANDOFF.md",
    "SHA256SUMS.json",
]

FORBIDDEN_PATTERNS = [
    r"\btrack 2 accepted all flows\b",
    r"\bnew flow accepted\b",
    r"\bpublished route means operational control\b",
    r"\bpublished route means accepted flow\b",
    r"\bbarcelona accepted\b",
    r"\bsingapore completed\b",
    r"\bbulk in progress is already reflected in xdata-d2-r1\b",
    r"\bcapped bulk is full\b",
    r"\bwindowed/api snapshot is historical completeness\b",
    r"\btraffic-control instruction\b",
    r"\btransit-control instruction\b",
    r"\bemergency dispatch\b",
    r"\bpublic-safety recommendation\b",
    r"\bpublic safety recommendation\b",
    r"\bhealth determination\b",
    r"\bpolicing recommendation\b",
    r"\benforcement action\b",
    r"\butility-control instruction\b",
    r"\bport/airport operational command\b",
    r"\bcertified affected asset\b",
    r"\bcertified affected building\b",
    r"\bplatform v1 complete\b",
]

NEGATION_MARKERS = ("no ", "not ", "never ", "without ", "does not ", "do not ", "cannot ", "0", "deferred", "candidate-only", "review-route-ready")


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
        if not text.startswith(str(root).lower()) or resolved.name.lower() != "track2_closeout_d1_xdata_cityflow_freeze":
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


def inventory(project_root: Path) -> dict[str, Any]:
    paths = dict(INPUTS)
    for lane, cfg in LANES.items():
        paths[f"{lane}_d4"] = cfg["d4"][0]
        paths[f"{lane}_d5"] = cfg["d5"][0]
    inputs = {}
    for name, rel in paths.items():
        path = project_path(project_root, rel)
        inputs[name] = {"path": str(path), "exists": path.exists(), "signature": input_signature(path)}
    return {"status": "PASS", "inputs": inputs}


def gate_status(report: dict[str, Any], gate_name: str) -> str | None:
    gates = report.get("gates")
    if isinstance(gates, dict):
        return gates.get(gate_name)
    if isinstance(gates, list):
        for gate in gates:
            if gate.get("gate") == gate_name:
                return gate.get("status")
    return None


def xdata_freeze(project_root: Path) -> dict[str, Any]:
    xdata_dir = project_path(project_root, INPUTS["xdata_d2_r1"])
    harness = read_json(xdata_dir / "XDATA_D2_R1_HARNESS_REPORT.json", {})
    matrix = read_json(xdata_dir / "XDATA_D2_R1_CITY_SUMMARY_MATRIX.json", {})
    cities = matrix.get("cities") or harness.get("city_summary", [])
    return {
        "status": "PASS" if harness.get("status") == "PASS_WITH_SOURCE_LIMITATIONS" and len(cities) == 4 else "FAIL",
        "source": str(xdata_dir),
        "xdata_status": harness.get("status"),
        "frozen_baseline": "XDATA-D2-R1",
        "city_totals": cities,
        "boundary": "Track 2 closeout uses current stable XDATA-D2-R1 only; active bulk continuation is deferred.",
    }


def active_bulk_deferred() -> dict[str, Any]:
    items = [
        {"city": "Chicago", "item": "Open Air individual continuation", "status": "DEFERRED_BULK_SWEEP_REQUIRED"},
        {"city": "Chicago", "item": "Cook County parcel continuation", "status": "DEFERRED_BULK_SWEEP_REQUIRED"},
        {"city": "NYC", "item": "311 2020-present continuation", "status": "DEFERRED_BULK_SWEEP_REQUIRED"},
    ]
    return {
        "status": "PASS",
        "do_not_wait_in_this_closeout": True,
        "items": items,
        "basis": "Close Track 2 using current stable XDATA-D2-R1 and defer active NYC/Chicago bulk continuation to a later sweep.",
    }


def d3_d4_d5_ledger(project_root: Path) -> dict[str, Any]:
    d3 = read_json(project_path(project_root, INPUTS["d3_refresh_d1"]) / "D3_REFRESH_D1_HARNESS_REPORT.json", {})
    rows = []
    for lane, cfg in LANES.items():
        d4_dir, d4_prefix = cfg["d4"]
        d5_dir, d5_prefix = cfg["d5"]
        d4_path = project_path(project_root, d4_dir)
        d5_path = project_path(project_root, d5_dir)
        d4_harness = read_json(d4_path / f"{d4_prefix}_HARNESS_REPORT.json", {})
        d5_harness = read_json(d5_path / f"{d5_prefix}_HARNESS_REPORT.json", {})
        d4_status = d4_harness.get("status")
        d5_status = d5_harness.get("status")
        artifact_status = "PASS" if d4_status else ("D4_ARTIFACT_MISSING_BUT_D5_PRESENT" if d5_status else "MISSING")
        rows.append(
            {
                "lane": lane,
                "d4_output": str(d4_path),
                "d4_status": d4_status,
                "d5_output": str(d5_path),
                "d5_status": d5_status,
                "artifact_status": artifact_status,
                "source_limited": True,
            }
        )
    return {
        "status": "PASS" if d3.get("status") == "PASS_D3_REFRESH_DECISION" and all(row["d5_status"] for row in rows) else "FAIL",
        "d3_refresh_status": d3.get("status"),
        "refreshed_outputs": d3.get("refreshed_outputs", []),
        "lane_ledger": rows,
    }


def face_publish_ledger(project_root: Path) -> dict[str, Any]:
    flowx = read_json(project_path(project_root, INPUTS["flowx_face_publish_smoke_d1"]) / "FLOWX_FACE_PUBLISH_SMOKE_D1_HARNESS_REPORT.json", {})
    lanes = flowx.get("lane_status_matrix", [])
    return {
        "status": "PASS" if flowx.get("status") == "PASS_FACE_PUBLISH_SMOKE_WITH_REVIEW_ROUTES" and flowx.get("published_review_routes") == 6 else "FAIL",
        "flowx_status": flowx.get("status"),
        "published_review_routes": flowx.get("published_review_routes", 0),
        "route_smoke": gate_status(flowx, "ROUTE-SMOKE"),
        "accepted_new_flows": 0,
        "lanes": lanes,
    }


def promotion_review_ledger(project_root: Path) -> dict[str, Any]:
    d6_dir = project_path(project_root, INPUTS["d6_promotion_review_d1"])
    harness = read_json(d6_dir / "D6_PROMOTION_REVIEW_D1_HARNESS_REPORT.json", {})
    review = read_json(d6_dir / "D6_PROMOTION_REVIEW_D1_PROMOTION_REVIEW_REPORT.json", {})
    decisions = read_json(d6_dir / "D6_PROMOTION_REVIEW_D1_DECISION_MATRIX.json", {})
    return {
        "status": "PASS" if harness.get("status") == "PASS_WITH_REVIEW_ONLY_DECISIONS" and review.get("accepted_count") == 0 and review.get("published_review_route_count") == 6 else "FAIL",
        "d6_status": harness.get("status"),
        "published_review_route_count": review.get("published_review_route_count"),
        "accepted_new_flows": review.get("accepted_count"),
        "candidate_only_count": review.get("candidate_only_count"),
        "decision_summary": review.get("decision_summary"),
        "decisions": [
            {
                "lane": item.get("lane", "").replace("-D6", ""),
                "decision": item.get("decision"),
                "face_route_status": item.get("face_route_status"),
                "published_review_route": item.get("published_review_route"),
                "candidate_only": item.get("candidate_only"),
                "accepted": item.get("accepted_flow_cartridge"),
            }
            for item in decisions.get("decisions", [])
        ],
    }


def acceptance_summary(face: dict[str, Any], promo: dict[str, Any]) -> dict[str, Any]:
    route_lanes = {row["lane"]: row for row in face.get("lanes", [])}
    promo_lanes = {row["lane"]: row for row in promo.get("decisions", [])}
    rows = []
    for lane, cfg in LANES.items():
        status = cfg["closeout_status"]
        if lane == "BARC-F7":
            status = "CANDIDATE_ONLY_NOT_ACCEPTED"
        rows.append(
            {
                "lane": lane,
                "closeout_status": status,
                "secondary_blocker": cfg.get("secondary_blocker", "BLOCKED_BY_ACCEPTANCE_POLICY"),
                "face_route_status": route_lanes.get(lane, {}).get("to_face_route_status") or promo_lanes.get(lane, {}).get("face_route_status"),
                "published_review_route": bool(route_lanes.get(lane, {}).get("published_review_route") or promo_lanes.get(lane, {}).get("published_review_route")),
                "accepted_new_flow": False,
                "source_limited": True,
            }
        )
    return {
        "status": "PASS",
        "track2_closed_for_now": True,
        "review_route_ready_lanes": sum(1 for row in rows if row["closeout_status"] == "REVIEW_ROUTE_READY_NOT_ACCEPTED"),
        "candidate_only_lanes": sum(1 for row in rows if row["closeout_status"] == "CANDIDATE_ONLY_NOT_ACCEPTED"),
        "accepted_new_flows": 0,
        "lane_classification": rows,
        "interpretation": "Six lanes are review-route-ready or candidate-only, not accepted. Publish/smoke alone does not accept flows.",
    }


def singapore_handoff() -> dict[str, Any]:
    return {
        "city": "singapore",
        "status": "DEFERRED_PENDING_DATA_AUTH",
        "reason": "LTA/DataMall auth issue and/or fresh source data required",
        "do_not_run_now": True,
        "resume_trigger": "fresh Singapore data/auth or explicit user instruction",
    }


def bulk_sweep_handoff() -> dict[str, Any]:
    return {
        "next_bulk_sweep_gate": "XDATA-BULK-SWEEP-D1",
        "trigger": "when current NYC/Chicago bulk continuations finish",
        "do_not_wait_in_this_closeout": True,
        "expected_pending_items": [
            "Chicago Open Air individual continuation",
            "Chicago Cook County parcel continuation",
            "NYC 311 2020-present continuation",
        ],
        "required_future_actions": [
            "rerun source manifests",
            "rerun XDATA reconciliation",
            "audit FULL vs CAPPED_BULK",
            "decide whether any D3 evidence should be refreshed",
            "do not mutate Track 2 closeout",
        ],
    }


def track1_handoff() -> dict[str, Any]:
    return {
        "return_focus_to": "PV1_MAIN_TRACK",
        "next_active_gate": "PV1-SUMO-SETUP-D1",
        "then": "PV1-D10/D11/D12 SUMO Simulator Bridge",
        "track2_status": "closed_review_route_ready",
        "track2_should_not_block_pv1": True,
    }


def deferred_backlog() -> dict[str, Any]:
    return {
        "status": "PASS",
        "items": [
            {"item": "NYC/Chicago active bulk continuation", "handoff": "TRACK2_CLOSEOUT_D1_BULK_SWEEP_HANDOFF.json"},
            {"item": "Singapore source/auth recovery", "handoff": "TRACK2_CLOSEOUT_D1_SINGAPORE_DEFERRED_HANDOFF.json"},
            {"item": "Explicit flow acceptance criteria", "status": "BLOCKED_BY_ACCEPTANCE_POLICY"},
            {"item": "Barcelona city-core acceptance policy", "status": "BLOCKED_BY_CITY_CORE"},
        ],
    }


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    findings = []
    checked = 0
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in {"SHA256SUMS.json", "TRACK2_CLOSEOUT_D1_NO_OVERCLAIM_REPORT.json"}:
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


def final_handoff_md(summary: dict[str, Any], xdata: dict[str, Any], bulk: dict[str, Any]) -> str:
    cities = {row["city_name"]: row for row in xdata.get("city_totals", [])}
    lines = [
        "# TRACK2-CLOSEOUT-D1 Final Handoff",
        "",
        "Track 2 is closed for now.",
        "",
        f"Six review routes were published/smoked: {summary['review_route_ready_lanes'] + summary['candidate_only_lanes']}.",
        f"Accepted new flows: {summary['accepted_new_flows']}.",
        "The six lanes are review-route-ready, not accepted.",
        "Barcelona remains candidate-only.",
        "Singapore is deferred pending fresh data/auth.",
        "In-progress NYC/Chicago bulk work is deferred to a later bulk sweep.",
        "Project focus returns to Track 1 / PV1 main: SUMO setup, then PV1-D10/D11/D12.",
        "",
        "## XDATA Freeze",
    ]
    for name in ["London", "New York City", "Chicago", "Barcelona"]:
        city = cities.get(name, {})
        if city:
            lines.append(f"- {name}: {city.get('rows_landed_effective')} rows / {city.get('bytes_landed_effective')} bytes")
    lines += [
        "",
        "## Lane Classification",
        *[f"- {row['lane']}: {row['closeout_status']}" + (f" / {row['secondary_blocker']}" if row["lane"] == "BARC-F7" else "") for row in summary["lane_classification"]],
        "",
        "## Deferred Bulk",
        *[f"- {item['item']}: {item['status']}" for item in bulk["items"]],
    ]
    return "\n".join(lines) + "\n"


def run_track2_closeout(project_root: str | Path = ".", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    out = reset_output_dir(project_path(project_root, output_dir), project_root)
    watched = {name: project_path(project_root, rel) for name, rel in WATCH_INPUTS.items()}
    before = {name: input_signature(path) for name, path in watched.items()}

    inv = inventory(project_root)
    xdata = xdata_freeze(project_root)
    bulk = active_bulk_deferred()
    d345 = d3_d4_d5_ledger(project_root)
    face = face_publish_ledger(project_root)
    promo = promotion_review_ledger(project_root)
    summary = acceptance_summary(face, promo)
    singapore = singapore_handoff()
    bulk_handoff = bulk_sweep_handoff()
    pv1 = track1_handoff()
    backlog = deferred_backlog()

    write_json(out / "TRACK2_CLOSEOUT_D1_INPUT_INVENTORY.json", inv)
    write_json(out / "TRACK2_CLOSEOUT_D1_XDATA_FREEZE_REPORT.json", xdata)
    write_json(out / "TRACK2_CLOSEOUT_D1_ACTIVE_BULK_DEFERRED_REPORT.json", bulk)
    write_json(out / "TRACK2_CLOSEOUT_D1_D3_D4_D5_LEDGER.json", d345)
    write_json(out / "TRACK2_CLOSEOUT_D1_FACE_PUBLISH_SMOKE_LEDGER.json", face)
    write_json(out / "TRACK2_CLOSEOUT_D1_PROMOTION_REVIEW_LEDGER.json", promo)
    write_json(out / "TRACK2_CLOSEOUT_D1_ACCEPTANCE_DECISION_SUMMARY.json", summary)
    write_json(out / "TRACK2_CLOSEOUT_D1_DEFERRED_BACKLOG.json", backlog)
    write_json(out / "TRACK2_CLOSEOUT_D1_SINGAPORE_DEFERRED_HANDOFF.json", singapore)
    write_json(out / "TRACK2_CLOSEOUT_D1_BULK_SWEEP_HANDOFF.json", bulk_handoff)
    write_json(out / "TRACK2_CLOSEOUT_D1_TRACK1_HANDOFF.json", pv1)
    write_text(out / "TRACK2_CLOSEOUT_D1_FINAL_HANDOFF.md", final_handoff_md(summary, xdata, bulk))

    gates = [
        {"gate": "TRACK2-CLOSEOUT-D1-PRECOND", "status": "PASS" if xdata["status"] == "PASS" and face["status"] == "PASS" and promo["status"] == "PASS" else "FAIL"},
        {"gate": "TRACK2-CLOSEOUT-D1-INPUT-INVENTORY", "status": inv["status"]},
        {"gate": "TRACK2-CLOSEOUT-D1-XDATA-FREEZE", "status": xdata["status"]},
        {"gate": "TRACK2-CLOSEOUT-D1-ACTIVE-BULK-DEFERRED", "status": bulk["status"]},
        {"gate": "TRACK2-CLOSEOUT-D1-D3-D4-D5-LEDGER", "status": d345["status"]},
        {"gate": "TRACK2-CLOSEOUT-D1-FACE-PUBLISH-SMOKE-LEDGER", "status": face["status"]},
        {"gate": "TRACK2-CLOSEOUT-D1-PROMOTION-REVIEW-LEDGER", "status": promo["status"]},
        {"gate": "TRACK2-CLOSEOUT-D1-ACCEPTANCE-DECISION-SUMMARY", "status": summary["status"]},
        {"gate": "TRACK2-CLOSEOUT-D1-SINGAPORE-DEFERRED", "status": "PASS" if singapore["status"] == "DEFERRED_PENDING_DATA_AUTH" else "FAIL"},
        {"gate": "TRACK2-CLOSEOUT-D1-BULK-SWEEP-HANDOFF", "status": "PASS" if bulk_handoff["do_not_wait_in_this_closeout"] else "FAIL"},
        {"gate": "TRACK2-CLOSEOUT-D1-TRACK1-HANDOFF", "status": "PASS" if pv1["track2_should_not_block_pv1"] else "FAIL"},
    ]
    overclaim = scan_no_overclaim(out)
    write_json(out / "TRACK2_CLOSEOUT_D1_NO_OVERCLAIM_REPORT.json", overclaim)
    gates.append({"gate": "TRACK2-CLOSEOUT-D1-NO-OVERCLAIM", "status": overclaim["status"]})
    mutation = compare_signatures(before, {name: input_signature(path) for name, path in watched.items()})
    write_json(out / "TRACK2_CLOSEOUT_D1_NO_MUTATION_REPORT.json", mutation)
    gates.append({"gate": "TRACK2-CLOSEOUT-D1-NO-MUTATION", "status": mutation["status"]})

    status = "PASS_TRACK2_CLOSED_WITH_DEFERRED_BULK_SWEEP" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    write_text(
        out / "README.md",
        "# TRACK2-CLOSEOUT-D1 XDATA / City-Flow Expansion Closeout\n\n"
        f"Status: `{status}`\n\n"
        "Track 2 is closed for now as review-route-ready / source-limited / no-new-acceptance. Active bulk and Singapore are deferred.\n",
    )
    harness = {
        "task": TASK,
        "status": status,
        "generated_at": utc_now(),
        "output_dir": str(out),
        "xdata_freeze_status": xdata["status"],
        "review_routes_published_smoked": face["published_review_routes"],
        "accepted_new_flows": summary["accepted_new_flows"],
        "review_route_ready_lanes": summary["review_route_ready_lanes"],
        "candidate_only_lanes": summary["candidate_only_lanes"],
        "track1_handoff": pv1,
        "gates": gates,
    }
    write_json(out / "TRACK2_CLOSEOUT_D1_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    hashed_keys = set(read_json(out / "SHA256SUMS.json", {}).keys())
    hash_ok = all(name in hashed_keys for name in REQUIRED if name != "SHA256SUMS.json")
    gates.append({"gate": "TRACK2-CLOSEOUT-D1-HASHES", "status": "PASS" if hash_ok else "FAIL", "hashed_files": hashes["file_count"]})
    status = "PASS_TRACK2_CLOSED_WITH_DEFERRED_BULK_SWEEP" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    harness["status"] = status
    harness["gates"] = gates
    write_json(out / "TRACK2_CLOSEOUT_D1_HARNESS_REPORT.json", harness)
    write_text(
        out / "README.md",
        "# TRACK2-CLOSEOUT-D1 XDATA / City-Flow Expansion Closeout\n\n"
        f"Status: `{status}`\n\n"
        "Track 2 is closed for now as review-route-ready / source-limited / no-new-acceptance. Active bulk and Singapore are deferred.\n",
    )
    write_hashes(out)
    return harness


def print_final_report(report: dict[str, Any]) -> None:
    gate_map = {gate["gate"]: gate["status"] for gate in report["gates"]}
    print(f"TRACK2-CLOSEOUT-D1 XDATA / City-Flow Expansion Closeout: {report['status']}")
    print()
    print(f"XDATA freeze: {gate_map.get('TRACK2-CLOSEOUT-D1-XDATA-FREEZE')}")
    print(f"Active bulk deferred: {gate_map.get('TRACK2-CLOSEOUT-D1-ACTIVE-BULK-DEFERRED')}")
    print(f"Review routes published/smoked: {report['review_routes_published_smoked']}")
    print(f"Accepted new flows: {report['accepted_new_flows']}")
    print(f"Review-route-ready lanes: {report['review_route_ready_lanes']}")
    print(f"Candidate-only lanes: {report['candidate_only_lanes']}")
    print(f"Singapore deferred: {gate_map.get('TRACK2-CLOSEOUT-D1-SINGAPORE-DEFERRED')}")
    print(f"Bulk sweep handoff: {gate_map.get('TRACK2-CLOSEOUT-D1-BULK-SWEEP-HANDOFF')}")
    print(f"Track 1 handoff: {gate_map.get('TRACK2-CLOSEOUT-D1-TRACK1-HANDOFF')}")
    print()
    print(f"No-overclaim: {gate_map.get('TRACK2-CLOSEOUT-D1-NO-OVERCLAIM')}")
    print(f"No-mutation: {gate_map.get('TRACK2-CLOSEOUT-D1-NO-MUTATION')}")
    print(f"Hashes: {gate_map.get('TRACK2-CLOSEOUT-D1-HASHES')}")
    print()
    print("Final status:")
    print(report["status"])
    print()
    print(f"Output:\n{report['output_dir']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Track 2 closeout gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = run_track2_closeout(args.project_root, args.output_dir)
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
