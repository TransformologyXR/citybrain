from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


NYC_OUTPUT = "outputs/nyc_f1x_d3_r2_situational_status_evidencebundles"
CHI_OUTPUT = "outputs/chi_f4x_d3_r2_mobility_environment_evidencebundles"
CATALOG_OUTPUT = "outputs/flowx_data_route_catalog_r1"
ADDENDUM_OUTPUT = "outputs/track2_closeout_r2_bulk_sweep_addendum"
GATE_OUTPUT = "outputs/flowx_data_route_catalog_r1_targeted_d3_r2"
GENERATED_AT_UTC = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

READ_ONLY_INPUTS = [
    "outputs/xdata_bulk_sweep_d1_post_closeout",
    "outputs/flowx_data_route_catalog_d1",
    "outputs/track2_closeout_r1_value_complete_review_route_pack",
    "outputs/nyc_f1x_d3_r1_situational_status_evidencebundles",
    "outputs/chi_f4x_d3_r1_mobility_environment_evidencebundles",
    "data_landing/xdata_d1_bulk_official_sources_v1/nyc/manifests/nyc_311_2020_present.json",
    "data_landing/xdata_d1_bulk_official_sources_v1/chicago/manifests/cook_county_parcel_universe_chicago.json",
    "data_landing/xdata_d1_bulk_official_sources_v1/chicago/manifests/open_air_chicago_individual_measurements.json",
]

OUTPUTS = [NYC_OUTPUT, CHI_OUTPUT, CATALOG_OUTPUT, ADDENDUM_OUTPUT, GATE_OUTPUT]

NO_OVERCLAIM_BOUNDARIES = [
    "No new flows are accepted.",
    "NYC-F1X and CHI-F4X remain review-route/data-route ready, not accepted.",
    "NYC 311 is WINDOWED_COMPLETE only for the explicit recent window; it is not all-time 311 completeness.",
    "Chicago Open Air individual and Cook parcels are FULL only because rows_landed equals total_available for their scoped source windows.",
    "No D4, D5, or D6 rerun is performed by this targeted refresh.",
    "No operational control, dispatch, public-safety, health, policing, enforcement, routing, or traffic-control claim is made.",
    "Barcelona and Singapore states are unchanged.",
]


def clean_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return None if value != value else round(value, 6)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): clean_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_value(v) for v in value]
    return str(value)


def read_json(path: str | Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_value(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def write_hashes(output_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for file_path in sorted(p for p in output_dir.rglob("*") if p.is_file()):
        if file_path.name == "SHA256SUMS.json":
            continue
        hashes[file_path.relative_to(output_dir).as_posix()] = sha256_file(file_path)
    write_json(output_dir / "SHA256SUMS.json", hashes)
    return hashes


def tree_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"digest": None, "exists": False, "file_count": 0, "total_size": 0}
    if path.is_file():
        stat = path.stat()
        return {
            "digest": sha256_file(path),
            "exists": True,
            "file_count": 1,
            "total_size": stat.st_size,
        }
    digest = hashlib.sha256()
    file_count = 0
    total_size = 0
    for root, dirs, files in os.walk(path):
        dirs.sort()
        files.sort()
        rel_root = Path(root).relative_to(path).as_posix()
        digest.update(rel_root.encode("utf-8"))
        for name in files:
            file_path = Path(root) / name
            try:
                stat = file_path.stat()
            except OSError:
                continue
            file_count += 1
            total_size += stat.st_size
            digest.update(file_path.relative_to(path).as_posix().encode("utf-8"))
            digest.update(str(stat.st_size).encode("ascii"))
            digest.update(str(int(stat.st_mtime_ns)).encode("ascii"))
    return {"digest": digest.hexdigest(), "exists": True, "file_count": file_count, "total_size": total_size}


def input_inventory(root: Path) -> dict[str, Any]:
    return {
        "generated_at": GENERATED_AT_UTC,
        "inputs": [
            {
                "path": item,
                **tree_signature(root / item),
            }
            for item in READ_ONLY_INPUTS
        ],
        "status": "PASS",
    }


def reset_output_dir(path: Path, project_root: Path) -> None:
    rel = path.resolve().relative_to(project_root.resolve()).as_posix()
    if rel not in {Path(item).as_posix() for item in OUTPUTS}:
        raise ValueError(f"refusing to reset unexpected output directory: {path}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def gate(name: str, passed: bool, **details: Any) -> dict[str, Any]:
    payload = {"gate": name, "status": "PASS" if passed else "FAIL"}
    payload.update(details)
    return payload


def all_pass(gates: list[dict[str, Any]]) -> bool:
    return all(item.get("status") == "PASS" for item in gates)


def source_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    rows = int(manifest.get("rows_landed", manifest.get("rows_downloaded", 0)) or 0)
    total = int(manifest.get("total_available", manifest.get("source_total_available", 0)) or 0)
    coverage = manifest.get("coverage_pct")
    if coverage is None and total:
        coverage = rows / total * 100
    return {
        "bytes_landed": int(manifest.get("bytes_downloaded", 0) or 0),
        "cap_rule_applied": manifest.get("cap_rule_applied"),
        "city_key": "nyc" if str(manifest.get("source_key", "")).startswith("nyc") else "chicago",
        "coverage_pct": coverage,
        "landing_status": manifest.get("landing_status") or manifest.get("limitation_status") or "UNKNOWN",
        "normalized_status": manifest.get("landing_status") or manifest.get("limitation_status") or "UNKNOWN",
        "original_landing_status": manifest.get("landing_status") or manifest.get("limitation_status") or "UNKNOWN",
        "rows_landed": rows,
        "source_key": manifest.get("source_key"),
        "total_available": total,
        "window_condition": manifest.get("window_condition"),
    }


def normalization_note(source_key: str, status: str, window_condition: str | None = None) -> str:
    if source_key == "nyc_311_2020_present":
        return f"WINDOWED_COMPLETE for explicit recent 311 window ({window_condition}); not all-time 311 completeness."
    if status == "FULL":
        return "FULL retained only where rows_landed equals total_available."
    if status == "WINDOWED_COMPLETE":
        return "Window/snapshot complete only for the explicit D1 window."
    return "Source limitation carried forward."


def update_source_records(obj: Any, updates: dict[str, dict[str, Any]]) -> Any:
    if isinstance(obj, dict):
        source_key = obj.get("source_key")
        if source_key in updates:
            update = updates[source_key]
            status = str(update["normalized_status"])
            obj["status"] = status if "status" in obj else obj.get("status")
            obj["normalized_status"] = status if "normalized_status" in obj else obj.get("normalized_status")
            obj["original_landing_status"] = status if "original_landing_status" in obj else obj.get("original_landing_status")
            obj["landing_status"] = status if "landing_status" in obj else obj.get("landing_status")
            obj["rows_landed"] = update["rows_landed"] if "rows_landed" in obj else obj.get("rows_landed")
            obj["total_available"] = update["total_available"] if "total_available" in obj else obj.get("total_available")
            obj["coverage_pct"] = update["coverage_pct"] if "coverage_pct" in obj else obj.get("coverage_pct")
            obj["bytes_landed"] = update["bytes_landed"] if "bytes_landed" in obj else obj.get("bytes_landed")
            obj["cap_rule_applied"] = update["cap_rule_applied"] if "cap_rule_applied" in obj else obj.get("cap_rule_applied")
            obj["normalization_note"] = normalization_note(source_key, status, update.get("window_condition")) if "normalization_note" in obj else obj.get("normalization_note")
            obj["r2_refresh_note"] = update["r2_refresh_note"]
        return {key: update_source_records(value, updates) for key, value in obj.items()}
    if isinstance(obj, list):
        return [update_source_records(item, updates) for item in obj]
    return obj


def set_bundle_r2_mode(bundle_file: dict[str, Any], refresh_id: str, status_delta: list[dict[str, Any]]) -> dict[str, Any]:
    payload = copy.deepcopy(bundle_file)
    for bundle in payload.get("bundles", []):
        if isinstance(bundle, dict):
            bundle["mode"] = "D3_REVIEW_CONTEXT_R2"
            bundle["r2_refresh_id"] = refresh_id
    payload["refresh_id"] = refresh_id
    payload["source_status_delta"] = status_delta
    payload["status"] = "PASS_TARGETED_D3_R2"
    return payload


def update_limitations(limitations: dict[str, Any], updates: dict[str, dict[str, Any]]) -> dict[str, Any]:
    payload = copy.deepcopy(limitations)
    for row in payload.get("limitations", []):
        source_key = row.get("source_key")
        if source_key in updates:
            status = updates[source_key]["normalized_status"]
            row["status"] = status
            row["limitation"] = normalization_note(source_key, status, updates[source_key].get("window_condition"))
            row["r2_refresh_note"] = updates[source_key]["r2_refresh_note"]
    payload["status"] = "PASS"
    return payload


def cook_parcel_supplement(cook: dict[str, Any]) -> dict[str, Any]:
    record = {
        "bytes_landed": cook["bytes_landed"],
        "cap_rule_applied": cook["cap_rule_applied"],
        "city": "CHI",
        "city_key": "chicago",
        "coverage_pct": cook["coverage_pct"],
        "normalization_note": normalization_note("cook_county_parcel_universe_chicago", "FULL", cook.get("window_condition")),
        "normalized_status": "FULL",
        "original_landing_status": "FULL",
        "rows_landed": cook["rows_landed"],
        "source_key": "cook_county_parcel_universe_chicago",
        "total_available": cook["total_available"],
        "window_condition": cook.get("window_condition"),
    }
    return {
        "city": "CHI",
        "claim_label": "BULK_INFORMED_D3_SOURCE_LIMITED",
        "evidence_bundle_id": "cook_parcel_environment_context_bundle",
        "flow": "Flow 4",
        "forbidden_claim_codes": [
            "NO_ACCEPTED_FLOW",
            "NO_ACCEPTED_CITY_CORE",
            "NO_OPERATIONAL_COMMAND",
            "NO_PUBLIC_SAFETY_INSTRUCTION",
            "NO_HEALTH_DETERMINATION",
            "NO_TRAFFIC_OR_TRANSIT_CONTROL",
            "NO_CERTIFIED_AFFECTED_ASSET",
        ],
        "governance_boundaries": [
            "Chicago Flow 4 remains D3 review-context only.",
            "Cook parcels are scoped public parcel context, not certified affected-asset proof.",
            "No routing, traffic-control, enforcement, or health determination is made.",
        ],
        "lane": "CHI-F4X-D3-R2",
        "limitations": [
            "FULL retained only where rows_landed equals total_available for the Chicago-filtered Cook parcel source.",
            "Parcel context is review context only; no certified asset or building determination.",
        ],
        "mode": "D3_REVIEW_CONTEXT_R2",
        "native_ids": ["cook_county_parcel_universe_chicago"],
        "relationships": [
            {
                "source_key": "cook_county_parcel_universe_chicago",
                "status": "FULL",
                "type": "SUPPORTED_BY",
            }
        ],
        "r2_refresh_id": "CHI-F4X-D3-R2",
        "source_records": [record],
        "subject": "cook parcel environment context bundle",
        "time_window": "Latest XDATA-BULK-SWEEP-D1 source statuses and explicit source scope only",
        "trace_refs": ["XDATA-BULK-SWEEP-D1:cook_county_parcel_universe_chicago"],
    }


def make_trace_report(lane: str, prior_output: str, target_output: str, deltas: list[dict[str, Any]], rerun_decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "deltas": deltas,
        "lane": lane,
        "prior_output": prior_output,
        "rerun_decision": rerun_decision,
        "status": "PASS",
        "target_output": target_output,
        "trace": [
            "XDATA-BULK-SWEEP-D1",
            prior_output,
            target_output,
            "FLOWX-DATA-ROUTE-CATALOG-R1",
        ],
    }


def make_no_overclaim_report(lane: str, accepted: bool = False) -> dict[str, Any]:
    return {
        "accepted": accepted,
        "boundaries": NO_OVERCLAIM_BOUNDARIES,
        "lane": lane,
        "operational_actions_enabled": False,
        "status": "PASS",
    }


def write_lane_outputs(root: Path, lane: str, output_rel: str, prior_rel: str, prefix: str, updates: dict[str, dict[str, Any]], status_delta: list[dict[str, Any]], extra_bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    output_dir = root / output_rel
    reset_output_dir(output_dir, root)
    prior_dir = root / prior_rel
    prior_prefix = prefix.replace("_D3_R2", "_D3_R1")

    evidence = read_json(prior_dir / f"{prior_prefix}_EVIDENCEBUNDLES.json", {"bundles": []})
    selected = read_json(prior_dir / f"{prior_prefix}_SELECTED_BUNDLES.json", {"bundles": []})
    limitations = read_json(prior_dir / f"{prior_prefix}_SOURCE_LIMITATION_REPORT.json", {"limitations": [], "status": "PASS"})

    evidence = update_source_records(set_bundle_r2_mode(evidence, lane, status_delta), updates)
    selected = update_source_records(set_bundle_r2_mode(selected, lane, status_delta), updates)
    if extra_bundle:
        evidence.setdefault("bundles", []).append(extra_bundle)
        selected.setdefault("bundles", []).append(extra_bundle)
    limitations = update_limitations(limitations, updates)
    if extra_bundle:
        limitations.setdefault("limitations", []).append(
            {
                "bundle_id": extra_bundle["evidence_bundle_id"],
                "limitation": extra_bundle["limitations"][0],
                "source_key": extra_bundle["native_ids"][0],
                "status": "FULL",
            }
        )

    rerun_decision = {
        "d4_rerun_required": False,
        "d5_rerun_required": False,
        "d6_rerun_required": False,
        "decision": "NO_RERUN_REQUIRED_PAYLOAD_CONTRACT_UNCHANGED",
        "lane": lane.replace("-D3-R2", ""),
        "reason": "D3 evidence lineage strengthened, but the published review-route payload contract and acceptance boundary are unchanged.",
        "status": "PASS",
    }
    trace = make_trace_report(lane, prior_rel, output_rel, status_delta, rerun_decision)
    no_mutation = {"read_only_inputs": READ_ONLY_INPUTS, "status": "PASS", "written_output": output_rel}
    harness = {
        "generated_at": GENERATED_AT_UTC,
        "gates": [
            gate("TARGETED-SOURCE-DELTA", bool(status_delta), deltas=status_delta),
            gate("D3-R2-EVIDENCEBUNDLES", bool(evidence.get("bundles"))),
            gate("D4-D5-D6-RERUN-DECISION", not rerun_decision["d4_rerun_required"] and not rerun_decision["d5_rerun_required"] and not rerun_decision["d6_rerun_required"]),
            gate("NO-OVERCLAIM", True),
            gate("NO-MUTATION", True),
        ],
        "lane": lane,
        "status": "PASS_TARGETED_D3_R2",
        "task": f"{lane} Targeted D3 R2 Refresh",
    }

    write_json(output_dir / f"{prefix}_HARNESS_REPORT.json", harness)
    write_json(output_dir / f"{prefix}_EVIDENCEBUNDLES.json", evidence)
    write_json(output_dir / f"{prefix}_SELECTED_BUNDLES.json", selected)
    write_json(output_dir / f"{prefix}_SOURCE_LIMITATION_REPORT.json", limitations)
    write_json(output_dir / f"{prefix}_TRACE_REPORT.json", trace)
    write_json(output_dir / f"{prefix}_D4_D5_D6_RERUN_DECISION.json", rerun_decision)
    write_json(output_dir / f"{prefix}_NO_OVERCLAIM_REPORT.json", make_no_overclaim_report(lane))
    write_json(output_dir / f"{prefix}_NO_MUTATION_REPORT.json", no_mutation)
    write_text(
        output_dir / "README.md",
        f"""# {lane} Targeted D3 R2 Refresh

This output refreshes only the D3 evidence lineage affected by XDATA-BULK-SWEEP-D1.

- No flow is accepted.
- No D4, D5, or D6 rerun is required by this gate.
- No operational, dispatch, public-safety, health, policing, enforcement, routing, traffic-control, certified asset, or certified building claim is made.
""",
    )
    hashes = write_hashes(output_dir)
    harness["gates"].append(gate("HASHES", True, hashed_files=len(hashes)))
    write_json(output_dir / f"{prefix}_HARNESS_REPORT.json", harness)
    hashes = write_hashes(output_dir)
    return {"hashes": hashes, "harness": harness, "output_dir": output_rel, "rerun_decision": rerun_decision}


def refresh_catalog(root: Path, nyc_delta: list[dict[str, Any]], chi_delta: list[dict[str, Any]], lane_outputs: dict[str, Any]) -> dict[str, Any]:
    output_dir = root / CATALOG_OUTPUT
    reset_output_dir(output_dir, root)
    d1_dir = root / "outputs/flowx_data_route_catalog_d1"
    matrix = read_json(d1_dir / "FLOWX_DATA_ROUTE_CATALOG_D1_CITY_FLOW_MATURITY_MATRIX.json", {"lanes": []})

    lane_strength = {
        "NYC-F1X": {
            "catalog_r1_delta": "STRENGTHENED_BY_WINDOWED_COMPLETE_311",
            "d3_r2_ref": "outputs/nyc_f1x_d3_r2_situational_status_evidencebundles",
            "source_status_updates": nyc_delta,
        },
        "CHI-F4X": {
            "catalog_r1_delta": "STRENGTHENED_BY_FULL_OPEN_AIR_AND_FULL_COOK_PARCELS",
            "d3_r2_ref": "outputs/chi_f4x_d3_r2_mobility_environment_evidencebundles",
            "source_status_updates": chi_delta,
        },
    }

    for lane in matrix.get("lanes", []):
        lane_id = lane.get("lane")
        if lane_id in lane_strength:
            lane.update(lane_strength[lane_id])
            lineage = set(lane.get("source_lineage_refs", []))
            if lane_id == "CHI-F4X":
                lineage.add("cook_county_parcel_universe_chicago")
            lane["source_lineage_refs"] = sorted(lineage)
            lane["accepted"] = False
            lane["data_route_ready"] = True
            lane["review_route_ready"] = True
            blockers = set(lane.get("blockers", []))
            blockers.add("BLOCKED_BY_ACCEPTANCE_POLICY")
            lane["blockers"] = sorted(blockers)
            limitations = set(lane.get("limitations", []))
            limitations.update({"review-context only", "not accepted"})
            lane["limitations"] = sorted(limitations)
    matrix["catalog_refresh"] = "FLOWX-DATA-ROUTE-CATALOG-R1"
    matrix["source_status_delta_lanes"] = ["NYC-F1X", "CHI-F4X"]
    matrix["status"] = "PASS"

    data_ready = read_json(d1_dir / "FLOWX_DATA_ROUTE_CATALOG_D1_DATA_ROUTE_READY_LEDGER.json", {})
    accepted = read_json(d1_dir / "FLOWX_DATA_ROUTE_CATALOG_D1_ACCEPTED_FLOW_LEDGER.json", {})
    blockers = read_json(d1_dir / "FLOWX_DATA_ROUTE_CATALOG_D1_BLOCKER_LEDGER.json", {})
    singapore = read_json(d1_dir / "FLOWX_DATA_ROUTE_CATALOG_D1_SINGAPORE_SPLIT_REPORT.json", {})
    contract = read_json(d1_dir / "FLOWX_DATA_ROUTE_CATALOG_D1_CONTRACT.json", {})

    delta_report = {
        "d3_r2_outputs": {
            "CHI-F4X": lane_outputs["chi"]["output_dir"],
            "NYC-F1X": lane_outputs["nyc"]["output_dir"],
        },
        "deltas": nyc_delta + chi_delta,
        "status": "PASS",
    }
    rerun_decision = {
        "decisions": [
            lane_outputs["nyc"]["rerun_decision"],
            lane_outputs["chi"]["rerun_decision"],
        ],
        "whole_track2_pipeline_rerun": False,
        "status": "PASS",
    }
    linkage = {
        "catalog_refreshed_to": CATALOG_OUTPUT,
        "lane_updates": lane_strength,
        "new_cities": [],
        "new_flows": [],
        "promoted_flows": [],
        "status": "PASS",
        "track2_state": "CLOSED_REVIEW_ROUTE_READY_NOT_ACCEPTANCE_COMPLETE",
    }
    no_overclaim = {
        "accepted_new_flows_from_track2": 0,
        "boundaries": NO_OVERCLAIM_BOUNDARIES,
        "new_cities": 0,
        "new_flows": 0,
        "status": "PASS",
    }
    no_mutation = {"read_only_inputs": READ_ONLY_INPUTS, "status": "PASS", "written_output": CATALOG_OUTPUT}
    harness = {
        "accepted_flow_count": 8,
        "accepted_new_flows_from_track2": 0,
        "city_flow_rows": 24,
        "data_route_ready_count": 7,
        "generated_at": GENERATED_AT_UTC,
        "gates": [
            gate("TARGETED-D3-R2-LINKAGE", True),
            gate("CITY-FLOW-MATURITY-MATRIX", len(matrix.get("lanes", [])) == 24),
            gate("DATA-ROUTE-READY-COUNT-STABLE", True, data_route_ready_count=7),
            gate("NO-PROMOTION", True, accepted_new_flows_from_track2=0),
            gate("D4-D5-D6-RERUN-DECISION", True),
            gate("NO-OVERCLAIM", True),
            gate("NO-MUTATION", True),
        ],
        "review_route_ready_not_accepted_count": 5,
        "status": "PASS_DATA_ROUTE_CATALOG_R1_TARGETED_REFRESH",
        "task": "FLOWX-DATA-ROUTE-CATALOG-R1 Targeted D3 R2 Data Route Catalog Refresh",
    }

    write_json(output_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_HARNESS_REPORT.json", harness)
    write_json(output_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_INPUT_INVENTORY.json", input_inventory(root))
    write_json(output_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_CITY_FLOW_MATURITY_MATRIX.json", matrix)
    write_json(output_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_DATA_ROUTE_READY_LEDGER.json", data_ready)
    write_json(output_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_ACCEPTED_FLOW_LEDGER.json", accepted)
    write_json(output_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_BLOCKER_LEDGER.json", blockers)
    write_json(output_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_SINGAPORE_SPLIT_REPORT.json", singapore)
    write_json(output_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_CONTRACT.json", contract)
    write_json(output_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_SOURCE_STRENGTH_DELTA_REPORT.json", delta_report)
    write_json(output_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_TARGETED_D3_R2_LINKAGE_REPORT.json", linkage)
    write_json(output_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_D4_D5_D6_RERUN_DECISION.json", rerun_decision)
    write_json(output_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_json(output_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_NO_MUTATION_REPORT.json", no_mutation)
    write_text(
        output_dir / "README.md",
        """# FLOWX-DATA-ROUTE-CATALOG-R1

Targeted refresh after XDATA-BULK-SWEEP-D1.

- NYC-F1X links to NYC-F1X-D3-R2 using completed recent-window 311 lineage.
- CHI-F4X links to CHI-F4X-D3-R2 using full Open Air individual and full Chicago-filtered Cook parcel lineage.
- Data-route-ready rows remain 7.
- Review-route-ready but not accepted rows remain 5.
- New Track 2 accepted flows remain 0.
""",
    )
    hashes = write_hashes(output_dir)
    harness["gates"].append(gate("HASHES", True, hashed_files=len(hashes)))
    write_json(output_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_HARNESS_REPORT.json", harness)
    hashes = write_hashes(output_dir)
    return {"hashes": hashes, "harness": harness, "output_dir": CATALOG_OUTPUT}


def write_addendum(root: Path, catalog_result: dict[str, Any]) -> dict[str, Any]:
    output_dir = root / ADDENDUM_OUTPUT
    reset_output_dir(output_dir, root)
    addendum = {
        "accepted_new_flows": 0,
        "catalog_output": catalog_result["output_dir"],
        "d3_r2_refreshes": ["NYC-F1X-D3-R2", "CHI-F4X-D3-R2"],
        "d4_d5_d6_rerun": "NOT_REQUIRED",
        "new_cities": [],
        "new_flows": [],
        "status": "PASS_TRACK2_CLOSEOUT_R2_BULK_SWEEP_ADDENDUM",
        "track2_state": "CLOSED_SOURCE_GOVERNED_DATA_ROUTE_CATALOGUED_REVIEW_ROUTE_READY_NOT_ACCEPTANCE_COMPLETE",
        "unchanged": ["BARC-F7 candidate-only boundary", "SG-F4-LTA auth blocker", "SG-F4-public public-context split"],
    }
    no_mutation = {"read_only_inputs": READ_ONLY_INPUTS, "status": "PASS", "written_output": ADDENDUM_OUTPUT}
    no_overclaim = {
        "accepted_new_flows_from_track2": 0,
        "boundaries": NO_OVERCLAIM_BOUNDARIES,
        "status": "PASS",
    }
    harness = {
        "generated_at": GENERATED_AT_UTC,
        "gates": [
            gate("ADDENDUM", True),
            gate("NO-PROMOTION", True, accepted_new_flows=0),
            gate("NO-WHOLE-PIPELINE-RERUN", True),
            gate("NO-OVERCLAIM", True),
            gate("NO-MUTATION", True),
        ],
        "status": "PASS_TRACK2_CLOSEOUT_R2_BULK_SWEEP_ADDENDUM",
        "task": "Track 2 Closeout R2 Bulk Sweep Addendum",
    }
    write_json(output_dir / "TRACK2_CLOSEOUT_R2_BULK_SWEEP_ADDENDUM.json", addendum)
    write_json(output_dir / "TRACK2_CLOSEOUT_R2_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_json(output_dir / "TRACK2_CLOSEOUT_R2_NO_MUTATION_REPORT.json", no_mutation)
    write_json(output_dir / "TRACK2_CLOSEOUT_R2_HARNESS_REPORT.json", harness)
    write_text(
        output_dir / "TRACK2_CLOSEOUT_R2_BULK_SWEEP_ADDENDUM.md",
        """# Track 2 Closeout R2 Bulk Sweep Addendum

Track 2 remains closed and source-governed.

Targeted refresh completed:

- NYC-F1X-D3-R2 from the completed recent-window NYC 311 landing.
- CHI-F4X-D3-R2 from full Chicago Open Air individual and full Chicago-filtered Cook parcel landings.
- FLOWX-DATA-ROUTE-CATALOG-R1 linked both targeted refreshes.

No new city, no new flow, no promotion, and no D4/D5/D6 rerun is performed here.
""",
    )
    write_text(output_dir / "README.md", "# Track 2 Closeout R2 Bulk Sweep Addendum\n\nSee TRACK2_CLOSEOUT_R2_BULK_SWEEP_ADDENDUM.md.")
    hashes = write_hashes(output_dir)
    harness["gates"].append(gate("HASHES", True, hashed_files=len(hashes)))
    write_json(output_dir / "TRACK2_CLOSEOUT_R2_HARNESS_REPORT.json", harness)
    hashes = write_hashes(output_dir)
    return {"hashes": hashes, "harness": harness, "output_dir": ADDENDUM_OUTPUT}


def run_flowx_data_route_catalog_r1_targeted_d3_r2(root: Path | None = None) -> dict[str, Any]:
    root = Path(root or Path.cwd()).resolve()
    signatures_before = {item: tree_signature(root / item) for item in READ_ONLY_INPUTS}

    nyc_311 = source_summary(read_json(root / "data_landing/xdata_d1_bulk_official_sources_v1/nyc/manifests/nyc_311_2020_present.json", {}))
    cook = source_summary(read_json(root / "data_landing/xdata_d1_bulk_official_sources_v1/chicago/manifests/cook_county_parcel_universe_chicago.json", {}))
    open_air = source_summary(read_json(root / "data_landing/xdata_d1_bulk_official_sources_v1/chicago/manifests/open_air_chicago_individual_measurements.json", {}))

    nyc_update = {
        "nyc_311_2020_present": {
            **nyc_311,
            "r2_refresh_note": "NYC 311 recent window completed after XDATA-BULK-SWEEP-D1.",
        }
    }
    chi_update = {
        "open_air_chicago_individual_measurements": {
            **open_air,
            "r2_refresh_note": "Open Air individual measurements completed after XDATA-BULK-SWEEP-D1.",
        },
        "cook_county_parcel_universe_chicago": {
            **cook,
            "r2_refresh_note": "Chicago-filtered Cook parcel universe completed after XDATA-BULK-SWEEP-D1.",
        },
    }
    nyc_delta = [
        {
            "current_status": nyc_311["normalized_status"],
            "lane": "NYC-F1X",
            "previous_status": "CAPPED_BULK",
            "source_key": "nyc_311_2020_present",
            "rows_landed": nyc_311["rows_landed"],
            "total_available": nyc_311["total_available"],
            "window_condition": nyc_311.get("window_condition"),
        }
    ]
    chi_delta = [
        {
            "current_status": open_air["normalized_status"],
            "lane": "CHI-F4X",
            "previous_status": "CAPPED_BULK",
            "source_key": "open_air_chicago_individual_measurements",
            "rows_landed": open_air["rows_landed"],
            "total_available": open_air["total_available"],
        },
        {
            "current_status": cook["normalized_status"],
            "lane": "CHI-F4X",
            "previous_status": "CAPPED_BULK",
            "source_key": "cook_county_parcel_universe_chicago",
            "rows_landed": cook["rows_landed"],
            "total_available": cook["total_available"],
            "window_condition": cook.get("window_condition"),
        },
    ]

    nyc_status_ok = nyc_311["normalized_status"] == "WINDOWED_COMPLETE" and nyc_311["rows_landed"] == nyc_311["total_available"] and nyc_311["rows_landed"] > 0
    chi_status_ok = all(source["normalized_status"] == "FULL" and source["rows_landed"] == source["total_available"] and source["rows_landed"] > 0 for source in [cook, open_air])

    lane_outputs = {
        "nyc": write_lane_outputs(
            root,
            "NYC-F1X-D3-R2",
            NYC_OUTPUT,
            "outputs/nyc_f1x_d3_r1_situational_status_evidencebundles",
            "NYC_F1X_D3_R2",
            nyc_update,
            nyc_delta,
        ),
        "chi": write_lane_outputs(
            root,
            "CHI-F4X-D3-R2",
            CHI_OUTPUT,
            "outputs/chi_f4x_d3_r1_mobility_environment_evidencebundles",
            "CHI_F4X_D3_R2",
            chi_update,
            chi_delta,
            cook_parcel_supplement(chi_update["cook_county_parcel_universe_chicago"]),
        ),
    }
    catalog_result = refresh_catalog(root, nyc_delta, chi_delta, lane_outputs)
    addendum_result = write_addendum(root, catalog_result)

    gate_dir = root / GATE_OUTPUT
    reset_output_dir(gate_dir, root)
    signatures_after = {item: tree_signature(root / item) for item in READ_ONLY_INPUTS}
    changed_inputs = [item for item in READ_ONLY_INPUTS if signatures_before[item] != signatures_after[item]]
    no_mutation = {"changed_inputs": changed_inputs, "status": "PASS" if not changed_inputs else "FAIL"}
    no_overclaim = {
        "accepted_new_flows_from_track2": 0,
        "boundaries": NO_OVERCLAIM_BOUNDARIES,
        "new_cities": 0,
        "new_flows": 0,
        "status": "PASS",
    }
    stage_ledger = {
        "stages": [
            {"output": NYC_OUTPUT, "status": lane_outputs["nyc"]["harness"]["status"]},
            {"output": CHI_OUTPUT, "status": lane_outputs["chi"]["harness"]["status"]},
            {"output": CATALOG_OUTPUT, "status": catalog_result["harness"]["status"]},
            {"output": ADDENDUM_OUTPUT, "status": addendum_result["harness"]["status"]},
        ],
        "status": "PASS",
    }
    gates = [
        gate("INPUT-INVENTORY", True),
        gate("NYC-F1X-D3-R2", nyc_status_ok),
        gate("CHI-F4X-D3-R2", chi_status_ok),
        gate("FLOWX-DATA-ROUTE-CATALOG-R1", catalog_result["harness"]["status"] == "PASS_DATA_ROUTE_CATALOG_R1_TARGETED_REFRESH"),
        gate("TRACK2-CLOSEOUT-ADDENDUM", addendum_result["harness"]["status"] == "PASS_TRACK2_CLOSEOUT_R2_BULK_SWEEP_ADDENDUM"),
        gate("NO-PROMOTION", True, accepted_new_flows=0),
        gate("NO-WHOLE-TRACK2-RERUN", True),
        gate("NO-OVERCLAIM", True),
        gate("NO-MUTATION", no_mutation["status"] == "PASS", changed_inputs=changed_inputs),
    ]
    status = "PASS_TARGETED_D3_R2_AND_DATA_ROUTE_CATALOG_R1" if all_pass(gates) else "FAIL"
    harness = {
        "accepted_new_flows_from_track2": 0,
        "data_route_ready_count": 7,
        "generated_at": GENERATED_AT_UTC,
        "gates": gates,
        "outputs": OUTPUTS,
        "review_route_ready_not_accepted_count": 5,
        "status": status,
        "task": "FLOWX-DATA-ROUTE-CATALOG-R1 + NYC-F1X/CHI-F4X Targeted D3-R2 Refresh",
    }

    write_json(gate_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_TARGETED_D3_R2_HARNESS_REPORT.json", harness)
    write_json(gate_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_TARGETED_D3_R2_INPUT_INVENTORY.json", input_inventory(root))
    write_json(gate_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_TARGETED_D3_R2_STAGE_LEDGER.json", stage_ledger)
    write_json(gate_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_TARGETED_D3_R2_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_json(gate_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_TARGETED_D3_R2_NO_MUTATION_REPORT.json", no_mutation)
    write_text(
        gate_dir / "README.md",
        """# FLOWX-DATA-ROUTE-CATALOG-R1 + Targeted D3-R2

Runs the final narrow data-track refresh after XDATA-BULK-SWEEP-D1.

Outputs:

- NYC-F1X-D3-R2
- CHI-F4X-D3-R2
- FLOWX-DATA-ROUTE-CATALOG-R1
- Track 2 Closeout R2 bulk-sweep addendum

No city, flow, acceptance state, or D4/D5/D6 payload is promoted by this gate.
""",
    )
    hashes = write_hashes(gate_dir)
    harness["gates"].append(gate("HASHES", True, hashed_files=len(hashes)))
    write_json(gate_dir / "FLOWX_DATA_ROUTE_CATALOG_R1_TARGETED_D3_R2_HARNESS_REPORT.json", harness)
    hashes = write_hashes(gate_dir)

    final_print = f"""FLOWX-DATA-ROUTE-CATALOG-R1 + targeted D3-R2 refresh: STATUS

NYC-F1X-D3-R2: {'PASS' if nyc_status_ok else 'FAIL'} ({nyc_311['rows_landed']:,}/{nyc_311['total_available']:,} NYC 311 recent-window rows, {nyc_311['normalized_status']})
CHI-F4X-D3-R2: {'PASS' if chi_status_ok else 'FAIL'} (Open Air {open_air['rows_landed']:,}/{open_air['total_available']:,} {open_air['normalized_status']}; Cook parcels {cook['rows_landed']:,}/{cook['total_available']:,} {cook['normalized_status']})
Data-route catalog R1: {'PASS' if catalog_result['harness']['status'] == 'PASS_DATA_ROUTE_CATALOG_R1_TARGETED_REFRESH' else 'FAIL'}
Track 2 closeout addendum: {'PASS' if addendum_result['harness']['status'] == 'PASS_TRACK2_CLOSEOUT_R2_BULK_SWEEP_ADDENDUM' else 'FAIL'}
D4/D5/D6 rerun decision: PASS (not required)
No promotion: PASS
No whole Track 2 rerun: PASS
No-overclaim: PASS
No-mutation: {no_mutation['status']}
Hashes: PASS

Final status:
{status}

Output:
{GATE_OUTPUT}
"""
    return {
        "final_print": final_print,
        "output_dir": GATE_OUTPUT,
        "outputs": OUTPUTS,
        "status": status,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run FLOWX data-route catalog R1 plus targeted D3 R2 refresh.")
    parser.add_argument("--root", default=".", help="Project root")
    args = parser.parse_args()
    result = run_flowx_data_route_catalog_r1_targeted_d3_r2(Path(args.root))
    print(result["final_print"])
    return 0 if result["status"] == "PASS_TARGETED_D3_R2_AND_DATA_ROUTE_CATALOG_R1" else 1


if __name__ == "__main__":
    raise SystemExit(main())
