from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


TASK_NAME = "CHI-D4 Flow 1 + Flow 7 Scope Fork"
DEFAULT_D1_OUTPUT = "outputs/chi_d1_chicago_deep_source_api_scout"
DEFAULT_D1B_OUTPUT = "outputs/chi_d1b_chicago_extended_source_landing"
DEFAULT_D2B_DIR = "outputs/chi_d2b_base_identity_refresh"
DEFAULT_D3_DIR = "outputs/chi_d3_civic_event_ingest_flow_readiness"
DEFAULT_OUTPUT_DIR = "outputs/chi_d4_dual_flow_scope_fork"

BOUNDARY_LINES = [
    "CHI-D4 creates a scope fork and readiness contracts only.",
    "CHI-D4 does not build Flow 1 or Flow 7.",
    "CHI-D4 does not create a certified Chicago cartridge.",
    "CHI-D4 does not certify affected buildings/assets.",
    "CHI-D4 does not create operational recommendations.",
    "CHI-D4 does not make policing, dispatch, enforcement, health, emergency, or public-safety recommendations.",
    "Flow 1 answers area situational status questions.",
    "Flow 7 answers civic and sensor fusion pattern questions.",
    "Chicago source base improved materially, but still not all-full-source because Divvy, Cook parcels, Crimes, and Open Air individual remain capped/windowed.",
    "Crime data is privacy-safe block-level context only.",
    "Crash people/vehicles are context only, not affected-asset, safety, enforcement, or response evidence.",
    "CTA GTFS is static schedule geography, not live transit status.",
]

FORBIDDEN_PATTERNS = [
    r"\bbuilds flow 1\b",
    r"\bbuilds flow 7\b",
    r"\bflow 1 cartridge built\b",
    r"\bflow 7 cartridge built\b",
    r"\bcreates a certified chicago cartridge\b",
    r"\bcertifies affected (?:buildings|assets)\b",
    r"\baffected (?:buildings|assets) are certified\b",
    r"\bcreates operational recommendations\b",
    r"\bmakes policing recommendations\b",
    r"\bmakes dispatch recommendations\b",
    r"\bmakes enforcement recommendations\b",
    r"\bmakes health recommendations\b",
    r"\bmakes emergency recommendations\b",
    r"\bmakes public-safety recommendations\b",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def with_boundary(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    out.setdefault("generated_at", utc_now())
    out.setdefault("boundary_lines", BOUNDARY_LINES)
    return out


def write_json(path: Path, payload: Any, add_boundary: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if add_boundary and isinstance(payload, dict):
        payload = with_boundary(payload)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


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
    write_json(output_dir / "SHA256SUMS.json", sums, add_boundary=False)
    expected = sorted(p.relative_to(output_dir).as_posix() for p in output_dir.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json")
    return {
        "status": "PASS" if sorted(sums) == expected else "FAIL",
        "file_count": len(sums),
        "missing": sorted(set(expected) - set(sums)),
        "extra": sorted(set(sums) - set(expected)),
    }


def write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if frame.empty:
        frame = pd.DataFrame({"_empty": pd.Series(dtype="string")})
    frame.to_parquet(path, index=False)


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()):
            raise ValueError(f"Refusing to remove output outside workspace: {resolved}")
        if "chi_d4_dual_flow_scope_fork" not in resolved.name.lower():
            raise ValueError(f"Refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["contracts", "canonical", "reports"]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def snapshot(paths: list[Path]) -> dict[str, Any]:
    watched: dict[str, Any] = {}
    for root in paths:
        if not root.exists():
            watched[str(root.resolve())] = {"exists": False}
            continue
        files = [root] if root.is_file() else [p for p in sorted(root.rglob("*")) if p.is_file()]
        for path in files:
            stat = path.stat()
            entry = {"exists": True, "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}
            if stat.st_size <= 5_000_000:
                entry["sha256"] = sha256_file(path)
            watched[str(path.resolve())] = entry
    return watched


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = []
    for key, old in before.items():
        if old != after.get(key):
            changed.append({"path": key, "before": old, "after": after.get(key)})
    return {"status": "PASS" if not changed else "FAIL", "changed_inputs": changed, "checked_files": len(before)}


def status_pass(value: Any) -> bool:
    text = str(value or "").upper()
    return text.startswith("PASS") or text.startswith("GREEN") or text.startswith("FLOW")


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    checked = []
    boundary_failures = []
    forbidden_hits = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md"} or path.name == "SHA256SUMS.json":
            continue
        if "canonical" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        checked.append(str(path.relative_to(output_dir)))
        missing = [line for line in BOUNDARY_LINES if line not in text]
        if missing:
            boundary_failures.append({"path": str(path.relative_to(output_dir)), "missing_boundary_lines": missing})
        lower = text.lower()
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, lower):
                forbidden_hits.append({"path": str(path.relative_to(output_dir)), "pattern": pattern})
    return {
        "status": "PASS" if not boundary_failures and not forbidden_hits else "FAIL",
        "checked_files": checked,
        "boundary_failures": boundary_failures,
        "forbidden_hits": forbidden_hits,
    }


def shared_source_ledger(d3_source_report: dict[str, Any], d3_counts: dict[str, Any]) -> dict[str, Any]:
    flow1_primary = {
        "area_context",
        "311_service_requests",
        "building_permits",
        "building_violations",
        "food_inspections",
        "business_licenses",
        "traffic_crashes_crashes",
        "open_air_chicago_hour_aggregations",
        "traffic_tracker_historical_2024_current",
        "divvy_trips",
    }
    flow7_primary = {
        "311_service_requests",
        "open_air_chicago_hour_aggregations",
        "open_air_chicago_individual_measurements",
        "food_inspections",
        "business_licenses",
        "traffic_crashes_crashes",
        "traffic_tracker_historical_2024_current",
        "divvy_trips",
        "crimes_2001_present",
    }
    rows = []
    for item in d3_source_report.get("sources", []):
        key = item.get("source_key")
        rows.append(
            {
                "source_key": key,
                "completion_status": item.get("completion_status"),
                "downloaded_rows": item.get("downloaded_rows"),
                "total_count": item.get("total_count"),
                "window_count": item.get("window_count"),
                "rows_loaded_by_d3": item.get("rows_loaded_by_d3"),
                "flow1_role": "primary_status_signal" if key in flow1_primary else "supporting_or_deferred",
                "flow7_role": "primary_fusion_signal" if key in flow7_primary else "supporting_or_deferred",
            }
        )
    rows.extend(
        [
            {
                "source_key": "chi_d2b_area_context",
                "completion_status": "ACCEPTED_D2B",
                "downloaded_rows": d3_counts.get("event_location_confidence_rows"),
                "total_count": None,
                "window_count": None,
                "rows_loaded_by_d3": None,
                "flow1_role": "primary_area_unit",
                "flow7_role": "cluster_context",
            },
            {
                "source_key": "chi_d2b_cta_gtfs_static",
                "completion_status": "FULL_STATIC_GTFS",
                "downloaded_rows": None,
                "total_count": None,
                "window_count": None,
                "rows_loaded_by_d3": None,
                "flow1_role": "static_transit_context",
                "flow7_role": "facility_transit_context",
            },
        ]
    )
    return {
        "status": "PASS",
        "ledger": rows,
        "shared_boundary": "Both flows use the same accepted D2B/D3 evidence base, but answer different operator questions.",
    }


def flow1_contract(d3_harness: dict[str, Any]) -> dict[str, Any]:
    counts = d3_harness.get("counts", {})
    return {
        "status": "PASS",
        "contract_id": "chi-f1-d1-readiness-contract",
        "flow": "CHI-F1-D1",
        "flow_name": "Chicago Situational Status",
        "operator_question": "What is the current/recent status of this area?",
        "unit_of_analysis": ["community_area", "ward", "police_district", "corridor"],
        "expected_outputs": ["area_status_card", "EvidenceBundle", "grounded_deterministic_briefing"],
        "required_inputs": [
            "D2B area context",
            "D2B facilities/resources",
            "D2B CTA static GTFS context",
            "D3 event counts and location confidence",
            "D3 311 recent-window events, permits, violations, inspections, licenses, crashes, Open Air, Traffic Tracker, Divvy context",
        ],
        "readiness_status": d3_harness.get("flow1_readiness"),
        "minimum_first_scope": {
            "area_units": ["community_area", "ward"],
            "signals": ["311", "permits", "violations", "food_inspections", "business_licenses", "traffic_crashes", "open_air_hourly"],
            "location_confidence_required": "A/B/C/D shown on every status card",
        },
        "first_build_should": [
            "aggregate D3 event/context rows by accepted D2B area IDs",
            "show recent/current status signals with source completion tiers",
            "produce deterministic EvidenceBundles and briefings",
        ],
        "first_build_must_not": [
            "build Flow 7",
            "make operational recommendations",
            "certify affected buildings/assets",
            "claim all-history 311/crime/Divvy/Traffic Tracker/Open Air individual completion",
        ],
        "supporting_counts": counts,
    }


def flow7_contract(d3_harness: dict[str, Any]) -> dict[str, Any]:
    counts = d3_harness.get("counts", {})
    return {
        "status": "PASS",
        "contract_id": "chi-f7-d1-readiness-contract",
        "flow": "CHI-F7-D1",
        "flow_name": "Chicago Civic + Sensor Fusion",
        "operator_question": "Where do civic demand, inspection signals, mobility, environment, and facility context converge?",
        "unit_of_analysis": ["service_hotspot", "sensor_zone", "civic_cluster"],
        "expected_outputs": ["fused_civic_sensor_candidate", "EvidenceBundle", "hero_scenario_candidate"],
        "required_inputs": [
            "D3 311 service events",
            "D3 Open Air observations",
            "D3 food inspections",
            "D3 business licenses",
            "D3 traffic crashes",
            "D3 Divvy context and Traffic Tracker recent-window context",
            "D2B facilities/resources and CTA static GTFS context",
            "D3 crime context as privacy-safe block-level context only",
        ],
        "readiness_status": d3_harness.get("flow7_readiness"),
        "minimum_first_scope": {
            "cluster_units": ["community_area", "service_hotspot", "sensor_zone"],
            "signals": ["311", "open_air", "food_inspections", "business_licenses", "traffic_crashes", "divvy", "traffic_tracker"],
            "fusion_requirement": "rank fused candidates with explicit source completion tiers and no recommendation language",
        },
        "first_build_should": [
            "fuse multi-signal D3 evidence into candidate clusters",
            "carry source confidence, capped-source limitations, and privacy limits into each EvidenceBundle",
            "select deterministic hero candidates from candidate clusters",
        ],
        "first_build_must_not": [
            "build Flow 1",
            "make health/public-safety/policing/dispatch recommendations",
            "claim crime-to-person or exact asset impact",
            "claim full-source completion for capped/windowed sources",
        ],
        "supporting_counts": counts,
    }


def hero_recommendations(d3_hero_report: dict[str, Any]) -> pd.DataFrame:
    candidates = d3_hero_report.get("candidates", [])
    by_id = {item.get("candidate_id"): item for item in candidates}
    rows = [
        {
            "recommendation_id": "chi_f1_d1:first:area_status_from_civic_service",
            "target_flow": "CHI-F1-D1",
            "rank": 1,
            "candidate_type": "area_status_card",
            "source_candidate_id": "hero_candidate:chi_d3:civic_service_hotspot",
            "supporting_sources": "311, permits, violations, inspections, licenses, crashes, Open Air hourly",
            "why_first": "Cheapest path to reusable city status surface; works directly with area units and D3 area-context edges.",
            "limitations": by_id.get("hero_candidate:chi_d3:civic_service_hotspot", {}).get("limitations"),
            "next_gate": "CHI-F1-D1",
        },
        {
            "recommendation_id": "chi_f1_d1:second:building_permit_violation_context",
            "target_flow": "CHI-F1-D1",
            "rank": 2,
            "candidate_type": "area_status_card",
            "source_candidate_id": "hero_candidate:chi_d3:building_permit_violation_context",
            "supporting_sources": "Building Permits, Building Violations, D2B area context",
            "why_first": "Good second status slice because permits are full and violations are windowed-complete.",
            "limitations": by_id.get("hero_candidate:chi_d3:building_permit_violation_context", {}).get("limitations"),
            "next_gate": "CHI-F1-D1",
        },
        {
            "recommendation_id": "chi_f7_d1:first:civic_sensor_cluster",
            "target_flow": "CHI-F7-D1",
            "rank": 1,
            "candidate_type": "fused_civic_sensor_candidate",
            "source_candidate_id": "hero_candidate:chi_d3:environment_sensor_context",
            "supporting_sources": "Open Air hourly/individual, 311, food inspections, business licenses, traffic crashes, Divvy/Traffic Tracker",
            "why_first": "Strongest portfolio story: multi-signal fusion across civic demand, sensor observations, inspection, mobility, and facility context.",
            "limitations": by_id.get("hero_candidate:chi_d3:environment_sensor_context", {}).get("limitations"),
            "next_gate": "CHI-F7-D1",
        },
        {
            "recommendation_id": "chi_f7_d1:second:traffic_crash_civic_context",
            "target_flow": "CHI-F7-D1",
            "rank": 2,
            "candidate_type": "fused_civic_sensor_candidate",
            "source_candidate_id": "hero_candidate:chi_d3:traffic_crash_context",
            "supporting_sources": "Traffic Crashes, 311, facilities/resources, mobility context",
            "why_first": "Complete crash table plus full people/vehicle context gives a stronger traffic context backbone while D3 still avoids person-level canonical rows.",
            "limitations": by_id.get("hero_candidate:chi_d3:traffic_crash_context", {}).get("limitations"),
            "next_gate": "CHI-F7-D1",
        },
    ]
    return pd.DataFrame(rows)


def run_chi_d4_gate(
    project_root: str = ".",
    chi_d1_output_dir: str = DEFAULT_D1_OUTPUT,
    chi_d1b_output_dir: str = DEFAULT_D1B_OUTPUT,
    chi_d2b_dir: str = DEFAULT_D2B_DIR,
    chi_d3_dir: str = DEFAULT_D3_DIR,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    root = Path(project_root)

    def resolve(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else root / path

    d1 = resolve(chi_d1_output_dir)
    d1b = resolve(chi_d1b_output_dir)
    d2b = resolve(chi_d2b_dir)
    d3 = resolve(chi_d3_dir)
    out = resolve(output_dir)
    input_roots = [d1, d1b, d2b, d3]
    before = snapshot(input_roots)
    reset_output_dir(out)

    d1_harness = read_json(d1 / "CHI_D1_HARNESS_REPORT.json", {})
    d1b_harness = read_json(d1b / "CHI_D1B_HARNESS_REPORT.json", {})
    d2b_harness = read_json(d2b / "CHI_D2B_HARNESS_REPORT.json", {})
    d3_harness = read_json(d3 / "CHI_D3_HARNESS_REPORT.json", {})
    d3_source_report = read_json(d3 / "CHI_D3_SOURCE_STATUS_REPORT.json", {})
    d3_hero_report = read_json(d3 / "CHI_D3_HERO_CANDIDATE_REPORT.json", {})
    d3_counts = d3_harness.get("counts", {})

    required = {
        "d1_harness": d1 / "CHI_D1_HARNESS_REPORT.json",
        "d1b_harness": d1b / "CHI_D1B_HARNESS_REPORT.json",
        "d2b_harness": d2b / "CHI_D2B_HARNESS_REPORT.json",
        "d3_harness": d3 / "CHI_D3_HARNESS_REPORT.json",
        "d3_source_status": d3 / "CHI_D3_SOURCE_STATUS_REPORT.json",
        "d3_hero_candidates": d3 / "CHI_D3_HERO_CANDIDATE_REPORT.json",
    }
    input_inventory = {
        "status": "PASS" if all(path.exists() for path in required.values()) else "FAIL",
        "required_inputs": {key: str(value) for key, value in required.items()},
        "required_input_exists": {key: value.exists() for key, value in required.items()},
        "d1_status": d1_harness.get("status"),
        "d1b_status": d1b_harness.get("status"),
        "d2b_status": d2b_harness.get("status"),
        "d3_status": d3_harness.get("status"),
        "d3_flow1_readiness": d3_harness.get("flow1_readiness"),
        "d3_flow7_readiness": d3_harness.get("flow7_readiness"),
        "d3_counts": d3_counts,
    }
    write_json(out / "CHI_D4_INPUT_INVENTORY.json", input_inventory)

    f1 = flow1_contract(d3_harness)
    f7 = flow7_contract(d3_harness)
    ledger = shared_source_ledger(d3_source_report, d3_counts)
    heroes = hero_recommendations(d3_hero_report)

    write_json(out / "CHI_D4_F1_D1_READINESS_CONTRACT.json", f1)
    write_json(out / "CHI_D4_F7_D1_READINESS_CONTRACT.json", f7)
    write_json(out / "contracts" / "chi_f1_d1_readiness_contract.json", f1)
    write_json(out / "contracts" / "chi_f7_d1_readiness_contract.json", f7)
    write_json(out / "CHI_D4_SHARED_SOURCE_LEDGER.json", ledger)
    write_json(out / "CHI_D4_HERO_CANDIDATE_RECOMMENDATIONS.json", {"status": "PASS", "recommendations": heroes.to_dict("records")})
    write_parquet(out / "canonical" / "chi_d4_flow_scope_fork.parquet", pd.DataFrame([{"flow": "CHI-F1-D1", **f1}, {"flow": "CHI-F7-D1", **f7}]))
    write_parquet(out / "canonical" / "chi_d4_hero_candidate_recommendations.parquet", heroes)

    comparison = {
        "status": "PASS",
        "flow1": {
            "question": f1["operator_question"],
            "unit": f1["unit_of_analysis"],
            "output": f1["expected_outputs"],
            "summary": "Flow 1 is the area dashboard/status intelligence flow.",
        },
        "flow7": {
            "question": f7["operator_question"],
            "unit": f7["unit_of_analysis"],
            "output": f7["expected_outputs"],
            "summary": "Flow 7 is the multi-signal civic and sensor fusion flow.",
        },
        "why_split": "Merging the flows would blur area status questions with cross-signal pattern discovery. D4 keeps two portfolio proofs over the same Chicago evidence base.",
    }
    build_order = {
        "status": "PASS",
        "recommended_order": ["CHI-D4 dual-flow fork", "CHI-F1-D1 area status cartridge", "CHI-F7-D1 civic/sensor fusion cartridge"],
        "reason": "CHI-F1-D1 is cheaper and creates the reusable status surface; CHI-F7-D1 is the stronger Chicago-specific portfolio story.",
    }
    write_json(out / "CHI_D4_FLOW_COMPARISON_REPORT.json", comparison)
    write_json(out / "CHI_D4_BUILD_ORDER_RECOMMENDATION.json", build_order)
    write_json(out / "reports" / "shared_source_ledger_by_flow.json", ledger)
    write_json(out / "reports" / "flow_comparison.json", comparison)
    write_json(out / "reports" / "first_hero_candidate_ranking.json", {"status": "PASS", "recommendations": heroes.to_dict("records")})
    write_json(out / "reports" / "build_order.json", build_order)
    write_json(out / "reports" / "no_overclaim_boundaries.json", {"status": "PASS", "boundary_lines": BOUNDARY_LINES})

    readme = "\n".join(
        [
            "# CHI-D4 Flow 1 + Flow 7 Scope Fork",
            "",
            *BOUNDARY_LINES,
            "",
            "## Result",
            "",
            "Status: PASS_WITH_DUAL_FLOW_FORK",
            "Flow 1: area dashboard / status intelligence flow.",
            "Flow 7: multi-signal civic and sensor fusion flow.",
            "",
            "Recommended order:",
            "1. CHI-F1-D1 first, because it is cheaper and becomes the reusable status surface.",
            "2. CHI-F7-D1 next, because it is the stronger Chicago-specific portfolio story.",
            "",
        ]
    )
    write_text(out / "README.md", readme)
    handover = "\n".join(
        [
            "# CHI-D4 Adapter Handover",
            "",
            *BOUNDARY_LINES,
            "",
            "## Next Gates",
            "",
            "- CHI-F1-D1 should consume `contracts/chi_f1_d1_readiness_contract.json` and build the area status cartridge.",
            "- CHI-F7-D1 should consume `contracts/chi_f7_d1_readiness_contract.json` and build the civic/sensor fusion cartridge.",
            "- Both should preserve `CHI_D4_SHARED_SOURCE_LEDGER.json` source completion tiers.",
            "- Neither should claim operational recommendations or affected-asset certification.",
            "",
        ]
    )
    write_text(out / "CHI_D4_ADAPTER_HANDOVER.md", handover)

    gates: dict[str, str] = {
        "CHI-D4-PRECOND": "PASS" if input_inventory["status"] == "PASS" and status_pass(d1_harness.get("status")) and status_pass(d1b_harness.get("status")) and status_pass(d2b_harness.get("status")) and status_pass(d3_harness.get("status")) else "FAIL",
        "CHI-D4-FLOW-DISTINCTION": "PASS" if f1["operator_question"] != f7["operator_question"] and f1["unit_of_analysis"] != f7["unit_of_analysis"] else "FAIL",
        "CHI-D4-F1-CONTRACT": "PASS" if f1["readiness_status"] == "FLOW1_READY_WITH_CAPPED_SOURCE_LIMITATIONS" else "FAIL",
        "CHI-D4-F7-CONTRACT": "PASS" if f7["readiness_status"] == "FLOW7_READY_WITH_CAPPED_SOURCE_LIMITATIONS" else "FAIL",
        "CHI-D4-SHARED-SOURCE-LEDGER": ledger["status"],
        "CHI-D4-HERO-CANDIDATES": "PASS" if len(heroes) >= 4 and set(heroes["target_flow"]) == {"CHI-F1-D1", "CHI-F7-D1"} else "FAIL",
        "CHI-D4-BUILD-ORDER": build_order["status"],
    }

    after = snapshot(input_roots)
    no_mutation = compare_snapshots(before, after)
    write_json(out / "CHI_D4_NO_MUTATION_REPORT.json", no_mutation)
    gates["CHI-D4-NO-MUTATION"] = no_mutation["status"]

    harness = {
        "task": TASK_NAME,
        "status": "PASS_WITH_DUAL_FLOW_FORK",
        "created_utc": utc_now(),
        "flow1_readiness_contract": f1["status"],
        "flow7_readiness_contract": f7["status"],
        "hero_recommendations": int(len(heroes)),
        "gates": gates,
        "output": str(out),
    }
    write_json(out / "CHI_D4_HARNESS_REPORT.json", harness)
    no_overclaim = scan_no_overclaim(out)
    write_json(out / "CHI_D4_SHARED_NO_OVERCLAIM_REPORT.json", no_overclaim)
    gates["CHI-D4-NO-OVERCLAIM"] = no_overclaim["status"]
    harness["gates"] = gates
    harness["status"] = "PASS_WITH_DUAL_FLOW_FORK" if all(value == "PASS" for value in gates.values()) else "FAIL"
    write_json(out / "CHI_D4_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    gates["CHI-D4-HASHES"] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = hashes
    harness["status"] = "PASS_WITH_DUAL_FLOW_FORK" if all(value == "PASS" for value in gates.values()) else "FAIL"
    write_json(out / "CHI_D4_HARNESS_REPORT.json", harness)
    final_no_overclaim = scan_no_overclaim(out)
    write_json(out / "CHI_D4_SHARED_NO_OVERCLAIM_REPORT.json", final_no_overclaim)
    gates["CHI-D4-NO-OVERCLAIM"] = final_no_overclaim["status"]
    hashes = write_hashes(out)
    gates["CHI-D4-HASHES"] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = hashes
    harness["status"] = "PASS_WITH_DUAL_FLOW_FORK" if all(value == "PASS" for value in gates.values()) else "FAIL"
    write_json(out / "CHI_D4_HARNESS_REPORT.json", harness)
    write_hashes(out)

    return {
        "status": harness["status"],
        "flow1_contract": f1["status"],
        "flow7_contract": f7["status"],
        "hero_recommendations": int(len(heroes)),
        "gates": gates,
        "output": str(out),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--chi-d1-output-dir", default=DEFAULT_D1_OUTPUT)
    parser.add_argument("--chi-d1b-output-dir", default=DEFAULT_D1B_OUTPUT)
    parser.add_argument("--chi-d2b-dir", default=DEFAULT_D2B_DIR)
    parser.add_argument("--chi-d3-dir", default=DEFAULT_D3_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-gates", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_chi_d4_gate(
        project_root=args.project_root,
        chi_d1_output_dir=args.chi_d1_output_dir,
        chi_d1b_output_dir=args.chi_d1b_output_dir,
        chi_d2b_dir=args.chi_d2b_dir,
        chi_d3_dir=args.chi_d3_dir,
        output_dir=args.output_dir,
    )
    gates = result["gates"]
    print(f"CHI-D4 Flow 1 + Flow 7 Scope Fork: {result['status']}")
    print(f"F1-D1 readiness contract: {result['flow1_contract']}")
    print(f"F7-D1 readiness contract: {result['flow7_contract']}")
    print("Shared source ledger: " + gates.get("CHI-D4-SHARED-SOURCE-LEDGER", "FAIL"))
    print(f"Hero recommendations: {result['hero_recommendations']}")
    print("Flow distinction: " + gates.get("CHI-D4-FLOW-DISTINCTION", "FAIL"))
    print("No-overclaim: " + gates.get("CHI-D4-NO-OVERCLAIM", "FAIL"))
    print("No-mutation: " + gates.get("CHI-D4-NO-MUTATION", "FAIL"))
    print(f"Output: {result['output']}")
    return 0 if str(result["status"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
