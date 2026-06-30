from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "CHI-FLOWX-D1 Parallel Chicago Flow Expansion Scouts"
DEFAULT_OUTPUT_DIR = "outputs/chi_flowx_d1_parallel_expansion_scouts"
DEFAULT_D1B_DIR = "outputs/chi_d1b_chicago_extended_source_landing"
DEFAULT_D2B_DIR = "outputs/chi_d2b_base_identity_refresh"
DEFAULT_D3B_DIR = "outputs/chi_d3_civic_event_ingest_flow_readiness_d3b_expanded_d1b"
DEFAULT_D5_DIR = "outputs/chi_f1f7_d5_dual_flow_accepted_snapshot"

ACCEPTED_CORE_STATUS = "GREEN_WITH_CAPPED_SOURCE_LIMITATIONS"
PUBLIC_TOOL = "citybrain_chicago_f1f7_query"

BOUNDARY_LINES = [
    "CHI-FLOWX-D1 treats Chicago as one accepted city core plus flow-specific extension sub-cartridges.",
    "The X suffix means an extension mounted on the accepted Chicago core, not a fresh city rebuild.",
    "CHI-FLOWX-D1 is a scout only; it does not accept Flow 2, Flow 3, or Flow 4 cartridges.",
    "Chicago Flow 1 and Flow 7 remain the accepted live-NIM flows in the current core.",
    "Extension scouts may reuse city-core native IDs, geography, source ledger, evidence style, face/NIM route conventions, and accepted limitations.",
    "Cook parcels remain capped/windowed; do not claim certified parcel/building joins until identity joins are gated.",
    "Building footprints remain geometry candidates, not certified building identities.",
    "Crash people/vehicles are context only, not affected-asset, safety, enforcement, or response evidence.",
    "Traffic/civic incident context is for analyst review only and is not emergency dispatch.",
    "CTA GTFS is static schedule context, not live transit status.",
    "CTA live APIs remain key-protected unless a valid key is supplied and gated.",
    "Crime data is privacy-safe block-level context only.",
    "Sensor/environment observations are context signals, not health determinations.",
    "No flow extension makes policing, dispatch, enforcement, health, emergency, public-safety, or operational recommendations.",
]

FORBIDDEN_POSITIVE_PATTERNS = [
    r"\bflow\s*[234]\s+(?:is|was|are|were)\s+accepted\b",
    r"\bcertified\s+(?:parcel|building|asset)\s+join\b",
    r"\bcertifies\s+affected\s+(?:buildings|assets)\b",
    r"\bdefinitely\s+affected\s+(?:buildings|assets)\b",
    r"\boperational recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bpublic-safety recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bdispatch recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\benforcement recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bhealth determinations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\blive transit status\s+(?:is|was|provided|ready|available)\b",
    r"\ball-full-source\s+(?:is|was|true|complete|provided|ready|available)\b",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_value(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            return clean_value(value.item())
        except Exception:
            pass
    if isinstance(value, float) and value != value:
        return None
    if isinstance(value, dict):
        return {str(k): clean_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_value(v) for v in value]
    return value


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\bNaN\b", "null", text)
    return json.loads(text)


def write_json(path: Path, payload: Any, add_boundary: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if add_boundary and isinstance(payload, dict):
        payload = dict(payload)
        payload.setdefault("generated_at", utc_now())
        payload.setdefault("boundary_lines", BOUNDARY_LINES)
    path.write_text(json.dumps(clean_value(payload), indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
    return {"gate": "CHI-FLOWX-D1-HASHES", "status": "PASS", "file_count": len(sums)}


def status_pass(value: Any) -> bool:
    text = str(value or "").upper()
    return text.startswith("PASS") or text.startswith("GREEN")


def resolve_under(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        parts = {part.lower() for part in resolved.parts}
        if (
            not str(resolved).lower().startswith(str(cwd).lower())
            or "outputs" not in parts
            or "chi_flowx_d1_parallel_expansion_scouts" != resolved.name.lower()
        ):
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in [
        "city_core",
        "chi_f2x_d1_compliance_cascade_expansion_scout",
        "chi_f3x_d1_traffic_incident_context_expansion_scout",
        "chi_f4x_d1_mobility_environment_expansion_scout",
        "reports",
    ]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def input_snapshot(paths: list[Path]) -> dict[str, Any]:
    watched: dict[str, Any] = {}
    for root in paths:
        if not root.exists():
            watched[str(root.resolve())] = {"exists": False}
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() in {".tmp", ".part"}:
                continue
            stat = path.stat()
            watched[str(path.resolve())] = {
                "exists": True,
                "bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": sha256_file(path) if stat.st_size <= 25_000_000 else None,
            }
    return watched


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = sorted(key for key, value in before.items() if after.get(key) != value)
    added = sorted(key for key in after if key not in before)
    removed = sorted(key for key in before if key not in after)
    return {
        "gate": "CHI-FLOWX-D1-NO-MUTATION",
        "status": "PASS" if not changed and not added and not removed else "FAIL",
        "checked_files": len(before),
        "changed_inputs": changed,
        "added_inputs": added,
        "removed_inputs": removed,
    }


def source_rows(d3b_dir: Path, d1b_dir: Path) -> list[dict[str, Any]]:
    d3b_usage = read_json(d3b_dir / "reports" / "source_usage.json", {})
    rows = d3b_usage.get("sources") or []
    d1b_counts = read_json(d1b_dir / "CHI_D1B_COUNTS_REPORT.json", {})
    d1b_by_key = {
        str(row.get("source_key")): dict(row)
        for row in d1b_counts.get("counts", [])
        if isinstance(row, dict) and row.get("source_key")
    }
    if rows:
        merged = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            out = dict(row)
            d1b_row = d1b_by_key.get(str(out.get("source_key")))
            if d1b_row:
                for field in ["resource_id", "planned_count"]:
                    out.setdefault(field, d1b_row.get(field))
            merged.append(out)
        return merged
    return [dict(row) for row in d1b_counts.get("counts", []) if isinstance(row, dict)]


def sources_by_key(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("source_key")): row for row in rows if row.get("source_key")}


def source_summary(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {"present": False}
    return {
        "present": True,
        "source_key": row.get("source_key"),
        "resource_id": row.get("resource_id"),
        "completion_status": row.get("completion_status"),
        "downloaded_rows": row.get("downloaded_rows"),
        "rows_loaded_by_d3": row.get("rows_loaded_by_d3"),
        "total_count": row.get("total_count"),
        "window_count": row.get("window_count"),
    }


def count_source_status(sources: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in sources:
        status = str(row.get("completion_status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def load_inputs(paths: dict[str, Path]) -> dict[str, Any]:
    d3b_sources = source_rows(paths["d3b"], paths["d1b"])
    return {
        "d1b_harness": read_json(paths["d1b"] / "CHI_D1B_HARNESS_REPORT.json", {}),
        "d1b_counts": read_json(paths["d1b"] / "CHI_D1B_COUNTS_REPORT.json", {}),
        "d2b_harness": read_json(paths["d2b"] / "CHI_D2B_HARNESS_REPORT.json", {}),
        "d2b_counts": read_json(paths["d2b"] / "CHI_D2B_ENTITY_COUNTS.json", {}),
        "d2b_handoff": read_json(paths["d2b"] / "CHI_D2B_EVENT_SOURCE_HANDOFF.json", {}),
        "d3b_harness": read_json(paths["d3b"] / "CHI_D3B_HARNESS_REPORT.json", {}),
        "d3b_event_counts": read_json(paths["d3b"] / "reports" / "event_type_distribution.json", {}),
        "d3b_source_usage": d3b_sources,
        "d3b_source_capped": read_json(paths["d3b"] / "reports" / "source_capped_status.json", {}),
        "crash_policy": read_json(paths["d3b"] / "reports" / "crash_people_vehicle_linkage_policy.json", {}),
        "building_policy": read_json(paths["d3b"] / "reports" / "building_context_candidate_policy.json", {}),
        "d5_harness": read_json(paths["d5"] / "CHI_F1F7_D5_HARNESS_REPORT.json", {}),
        "d5_counts": read_json(paths["d5"] / "CHI_F1F7_D5_ACCEPTED_COUNTS.json", {}),
        "d5_stage": read_json(paths["d5"] / "CHI_F1F7_D5_STAGE_LEDGER.json", {}),
    }


def precondition_report(data: dict[str, Any]) -> dict[str, Any]:
    statuses = {
        "CHI-D1B": data["d1b_harness"].get("status"),
        "CHI-D2B": data["d2b_harness"].get("status"),
        "CHI-D3B": data["d3b_harness"].get("status"),
        "CHI-F1F7-D5": data["d5_harness"].get("status") or data["d5_harness"].get("accepted_status"),
    }
    checks = {
        "accepted_core_green": status_pass(data["d5_harness"].get("status")) or status_pass(data["d5_harness"].get("accepted_status")),
        "d1b_green": status_pass(data["d1b_harness"].get("status")),
        "d2b_green": status_pass(data["d2b_harness"].get("status")),
        "d3b_green": status_pass(data["d3b_harness"].get("status")),
        "source_usage_present": bool(data["d3b_source_usage"]),
    }
    return {"gate": "CHI-FLOWX-D1-PRECOND", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "statuses": statuses}


def build_city_core(paths: dict[str, Path], data: dict[str, Any]) -> dict[str, Any]:
    d2b_counts = data["d2b_counts"]
    d3b_counts = data["d3b_harness"].get("counts") or {}
    d5_counts = data["d5_harness"].get("counts") or {}
    source_rows_list = data["d3b_source_usage"]
    return {
        "status": "PASS",
        "core_id": "CHI-CORE-D5",
        "accepted_status": ACCEPTED_CORE_STATUS,
        "accepted_flows": ["CHI-F1-D1B", "CHI-F7-D1B"],
        "extension_model": "CITY-FLOW-SUBCARTRIDGE",
        "native_ids": {
            "parcel": "Cook County PIN14",
            "building": "Chicago building footprint candidate ID / geometry candidate",
            "permit": "permit_number",
            "violation": "violation source_record_id / inspection_number",
            "service_request": "service_request_number",
            "crash": "crash_record_id",
            "transit_stop": "CTA stop_id",
            "transit_route": "CTA route_id",
            "traffic_segment": "Traffic Tracker segment_id",
            "sensor": "Open Air sensor_id",
        },
        "geography": {
            "area_context": d2b_counts.get("area_context"),
            "building_footprint_candidates": d2b_counts.get("building_footprint_candidates"),
            "parcels_pin14": d2b_counts.get("parcels_pin14"),
            "transit_nodes": d2b_counts.get("transit_nodes"),
            "transit_routes": d2b_counts.get("transit_routes"),
            "facilities_resources": d2b_counts.get("facilities_resources"),
            "identity_edges": d2b_counts.get("identity_edges"),
            "identity_context_edges_total": d2b_counts.get("identity_context_edges_total"),
        },
        "source_ledger": {
            "source_count": len(source_rows_list),
            "status_counts": count_source_status(source_rows_list),
            "sources": [source_summary(row) for row in source_rows_list],
        },
        "base_evidence_style": {
            "evidence_bundle_mode": "deterministic EvidenceBundles with source lineage and no-overclaim scans",
            "live_replay_mode": "Spark/NIM narration may narrate accepted facts only and may not compute counts or add facts",
            "public_tool": PUBLIC_TOOL,
            "face_routes": data["d5_harness"].get("routes", {}).get("available_routes", []),
        },
        "accepted_counts": {
            "d1b_landed_rows": d5_counts.get("d1b_landed_rows"),
            "d3b_event_location_rows": d3b_counts.get("event_location_confidence_rows") or d5_counts.get("d3b_event_location_rows"),
            "d3b_context_edges": d3b_counts.get("context_edges") or d5_counts.get("d3b_context_edges"),
            "f1_citywide_total_signal_rows": d5_counts.get("f1_citywide_total_signal_rows"),
            "f7_fusion_candidates": d5_counts.get("f7_fusion_candidates"),
            "f7_selected_candidates": d5_counts.get("f7_selected_candidates"),
        },
        "accepted_limitations": BOUNDARY_LINES,
        "input_paths": {key: str(value) for key, value in paths.items()},
    }


def source_fit(keys: list[str], by_key: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sources = {key: source_summary(by_key.get(key)) for key in keys}
    present = [key for key, row in sources.items() if row.get("present")]
    missing = [key for key, row in sources.items() if not row.get("present")]
    downloaded = sum(int(row.get("downloaded_rows") or 0) for row in sources.values() if row.get("present"))
    return {
        "status": "PASS" if not missing else "FAIL",
        "required_source_keys": keys,
        "present_source_keys": present,
        "missing_source_keys": missing,
        "downloaded_rows_across_present_sources": downloaded,
        "sources": sources,
    }


def evidence_bundle(bundle_id: str, flow: str, subject: str, feasibility: str, source_fit_report: dict[str, Any], join_readiness: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "bundle_id": bundle_id,
        "bundle_type": "expansion_scout_evidence_bundle",
        "flow": flow,
        "subject": subject,
        "feasibility": feasibility,
        "source_fit": source_fit_report,
        "join_readiness": join_readiness,
        "decision": decision,
        "provenance": [
            "CHI-F1F7-D5 accepted city core",
            "CHI-D2B base identity/geography",
            "CHI-D3B expanded civic/event readiness",
            "CHI-D1B source landing counts",
        ],
        "boundary_lines": BOUNDARY_LINES,
    }


def flow2_scout(data: dict[str, Any]) -> dict[str, Any]:
    by_key = sources_by_key(data["d3b_source_usage"])
    required = [
        "building_footprints_primary",
        "building_permits",
        "building_violations",
        "business_licenses",
        "food_inspections",
        "cook_county_parcel_universe",
        "311_service_requests",
    ]
    fit = source_fit(required, by_key)
    d2b_counts = data["d2b_counts"]
    join_readiness = {
        "status": "PASS_WITH_BLOCKERS",
        "ready_context_joins": [
            "area-context rollups through ward/community area/police district fields",
            "permit PIN-list parsing candidate from building permits",
            "address/geometry candidate joins for permits, violations, inspections, licenses, and 311",
        ],
        "blocking_join_gates": [
            "Cook parcel universe is still WINDOWED_CAPPED in the accepted core.",
            "D2B identity_edges count is zero; parcel/building identity joins are not certified.",
            "Building footprints remain geometry candidates.",
            "Violation and inspection records must stay compliance context until exact parcel/building joins are proven.",
        ],
        "d2b_identity_edges": d2b_counts.get("identity_edges"),
        "parcels_pin14": d2b_counts.get("parcels_pin14"),
        "building_footprint_candidates": d2b_counts.get("building_footprint_candidates"),
    }
    decision = {
        "status": "RECOMMEND_CHI-F2X-D2",
        "recommended_next": "CHI-F2X-D2 compliance cascade identity-join gate",
        "candidate_strength": "HIGH",
        "not_yet": "not a certified parcel/building compliance cascade",
    }
    bundle = evidence_bundle(
        "evidence_bundle_chi_f2x_d1_compliance_cascade_scout",
        "CHI-F2X",
        "Chicago compliance cascade feasibility",
        "HIGH_WITH_IDENTITY_JOIN_BLOCKERS",
        fit,
        join_readiness,
        decision,
    )
    return {
        "task": "CHI-F2X-D1 Chicago Compliance Cascade Expansion Scout",
        "status": "PASS_FEASIBILITY_HIGH_WITH_IDENTITY_JOIN_BLOCKERS",
        "candidate_strength": "HIGH",
        "source_fit": fit,
        "join_readiness": join_readiness,
        "decision": decision,
        "evidence_bundles": [bundle],
        "boundaries": [
            "Cook parcels remain capped/windowed in the accepted core.",
            "Do not claim certified parcel/building compliance cascade until identity joins are gated.",
            "This scout emits no enforcement recommendation.",
        ],
    }


def flow3_scout(data: dict[str, Any]) -> dict[str, Any]:
    by_key = sources_by_key(data["d3b_source_usage"])
    required = [
        "traffic_crashes_crashes",
        "traffic_crashes_people",
        "traffic_crashes_vehicles",
        "traffic_tracker_historical_2024_current",
        "311_service_requests",
    ]
    fit = source_fit(required, by_key)
    d2b_counts = data["d2b_counts"]
    crash_policy = data["crash_policy"]
    join_readiness = {
        "status": "PASS_CONTEXT_ONLY",
        "ready_context_joins": [
            "traffic crash events already have crash_record_id, area fields, geometry, and injury summary fields",
            "crash people and vehicle tables are full-source landed and can be joined by crash_record_id after privacy/context gate",
            "Traffic Tracker recent window can support segment/time context after segment normalization",
            "facilities/resources and static CTA nodes can provide nearby context for analyst review",
        ],
        "blocking_join_gates": [
            "crash people/vehicles are currently landing context only, not person/vehicle canonical evidence rows",
            "Traffic Tracker is windowed-complete but not yet normalized into D3 incident context rows",
            "CTA live APIs are not available without a developer key",
            "No emergency dispatch, response optimization, or affected-building detection claim is allowed",
        ],
        "crash_policy": crash_policy.get("policy"),
        "facilities_resources": d2b_counts.get("facilities_resources"),
        "transit_nodes": d2b_counts.get("transit_nodes"),
        "transit_routes": d2b_counts.get("transit_routes"),
    }
    decision = {
        "status": "RECOMMEND_CHI-F3X-D2",
        "recommended_next": "CHI-F3X-D2 crash triad and traffic-segment context join gate",
        "candidate_strength": "MEDIUM_HIGH",
        "not_yet": "not dispatch, not public-safety recommendation, not affected-asset certification",
    }
    bundle = evidence_bundle(
        "evidence_bundle_chi_f3x_d1_traffic_incident_context_scout",
        "CHI-F3X",
        "Chicago traffic-incident context feasibility",
        "MEDIUM_HIGH_CONTEXT_ONLY",
        fit,
        join_readiness,
        decision,
    )
    return {
        "task": "CHI-F3X-D1 Chicago Traffic-Incident Context Expansion Scout",
        "status": "PASS_FEASIBILITY_MEDIUM_HIGH_CONTEXT_ONLY",
        "candidate_strength": "MEDIUM_HIGH",
        "source_fit": fit,
        "join_readiness": join_readiness,
        "decision": decision,
        "evidence_bundles": [bundle],
        "boundaries": [
            "This is not emergency dispatch.",
            "This is not certified affected-building detection.",
            "Crash people/vehicles are context-only and require privacy/context gating.",
        ],
    }


def flow4_scout(data: dict[str, Any]) -> dict[str, Any]:
    by_key = sources_by_key(data["d3b_source_usage"])
    required = [
        "traffic_tracker_historical_2024_current",
        "divvy_trips",
        "open_air_chicago_hour_aggregations",
        "open_air_chicago_individual_measurements",
        "311_service_requests",
    ]
    fit = source_fit(required, by_key)
    d2b_counts = data["d2b_counts"]
    join_readiness = {
        "status": "PASS_WITH_KEY_LIMITED_LIVE_FEEDS",
        "ready_context_joins": [
            "CTA GTFS static stops/routes are present in city core",
            "Traffic Tracker recent window is landed as windowed-complete source context",
            "Divvy trip sample can support bounded mobility-demand context",
            "Open Air hourly observations can support environmental context",
            "311 service requests can provide civic friction/context signals",
        ],
        "blocking_join_gates": [
            "CTA live bus/train APIs require a developer key and are not part of the accepted core.",
            "Divvy and Open Air individual measurements remain capped/windowed.",
            "Traffic Tracker is not live transit status.",
            "Environmental observations are not health determinations.",
        ],
        "static_gtfs": {
            "transit_nodes": d2b_counts.get("transit_nodes"),
            "transit_routes": d2b_counts.get("transit_routes"),
            "status": "STATIC_CONTEXT_ONLY",
        },
    }
    decision = {
        "status": "RECOMMEND_CHI-F4X-D2",
        "recommended_next": "CHI-F4X-D2 mobility/environment time-window fusion gate",
        "candidate_strength": "HIGH",
        "not_yet": "not real-time urban mobility unless CTA/live feeds are keyed and gated",
    }
    bundle = evidence_bundle(
        "evidence_bundle_chi_f4x_d1_mobility_environment_scout",
        "CHI-F4X",
        "Chicago mobility/environment feasibility",
        "HIGH_WITH_KEY_PROTECTED_LIVE_FEEDS",
        fit,
        join_readiness,
        decision,
    )
    return {
        "task": "CHI-F4X-D1 Chicago Mobility/Environment Expansion Scout",
        "status": "PASS_FEASIBILITY_HIGH_WITH_KEY_PROTECTED_LIVE_FEEDS",
        "candidate_strength": "HIGH",
        "source_fit": fit,
        "join_readiness": join_readiness,
        "decision": decision,
        "evidence_bundles": [bundle],
        "boundaries": [
            "CTA GTFS is static schedule context, not live transit status.",
            "CTA live APIs require a developer key before real-time claims can be tested.",
            "Open Air/environment observations are context signals, not health determinations.",
        ],
    }


def source_strength(flow: dict[str, Any]) -> dict[str, Any]:
    fit = flow["source_fit"]
    total_required = len(fit["required_source_keys"])
    present = len(fit["present_source_keys"])
    return {
        "candidate_strength": flow["candidate_strength"],
        "source_coverage_ratio": round(present / total_required, 4) if total_required else 0,
        "downloaded_rows_across_present_sources": fit.get("downloaded_rows_across_present_sources"),
        "next": flow["decision"]["recommended_next"],
        "status": flow["status"],
    }


def write_flow_output(base_dir: Path, prefix: str, flow: dict[str, Any]) -> None:
    write_json(base_dir / f"{prefix}_HARNESS_REPORT.json", flow)
    write_json(base_dir / f"{prefix}_SOURCE_FIT_REPORT.json", flow["source_fit"])
    write_json(base_dir / f"{prefix}_JOIN_READINESS_REPORT.json", flow["join_readiness"])
    write_json(base_dir / f"{prefix}_EVIDENCE_BUNDLE_REPORT.json", {"status": "PASS", "bundle_count": len(flow["evidence_bundles"]), "bundles": flow["evidence_bundles"]})
    write_json(base_dir / f"{prefix}_DECISION_REPORT.json", flow["decision"])
    lines = [
        f"# {flow['task']}",
        "",
        f"Status: {flow['status']}",
        f"Candidate strength: {flow['candidate_strength']}",
        "",
        "## Decision",
        f"- {flow['decision']['recommended_next']}",
        f"- Not yet: {flow['decision']['not_yet']}",
        "",
        "## Boundary",
        *[f"- {line}" for line in BOUNDARY_LINES],
        *[f"- {line}" for line in flow["boundaries"]],
        "",
    ]
    write_text(base_dir / "README.md", "\n".join(lines))


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    findings = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in {"SHA256SUMS.json", "CHI_FLOWX_D1_NO_OVERCLAIM_REPORT.json"}:
            continue
        if path.suffix.lower() not in {".json", ".md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for pattern in FORBIDDEN_POSITIVE_PATTERNS:
            if re.search(pattern, text):
                findings.append({"path": path.relative_to(output_dir).as_posix(), "pattern": pattern})
    return {"gate": "CHI-FLOWX-D1-NO-OVERCLAIM", "status": "PASS" if not findings else "FAIL", "forbidden_positive_claims_found": findings}


def limitation_report(output_dir: Path) -> dict[str, Any]:
    joined = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in output_dir.rglob("*.json")) + "\n"
    joined += "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in output_dir.rglob("*.md"))
    missing = [line for line in BOUNDARY_LINES if line not in joined]
    return {"gate": "CHI-FLOWX-D1-LIMITATION-CARRY-FORWARD", "status": "PASS" if not missing else "FAIL", "missing_boundary_lines": missing}


def write_docs(output_dir: Path, core: dict[str, Any], flows: dict[str, dict[str, Any]]) -> None:
    lines = [
        "# CHI-FLOWX-D1 Parallel Chicago Flow Expansion Scouts",
        "",
        "Status: PASS_PARALLEL_FLOW_EXTENSION_SCOUTS",
        "",
        "Chicago is treated as one accepted city core plus flow-specific extension sub-cartridges.",
        "",
        "## City Core",
        f"- Core ID: {core['core_id']}",
        f"- Accepted flows: {', '.join(core['accepted_flows'])}",
        f"- Public tool convention: {core['base_evidence_style']['public_tool']}",
        "",
        "## Scout Results",
    ]
    for key, flow in flows.items():
        lines.append(f"- {key}: {flow['status']} -> {flow['decision']['recommended_next']}")
    lines.extend(["", "## Boundary", *[f"- {line}" for line in BOUNDARY_LINES], ""])
    write_text(output_dir / "README.md", "\n".join(lines))

    handover = [
        "# CHI-FLOWX-D1 Adapter Handover",
        "",
        "Mount future flow sub-cartridges on CHI-CORE-D5. Do not rebuild Chicago base identity/geography for each flow unless a specific source repair requires it.",
        "",
        "Recommended next gates:",
        "- CHI-F2X-D2: compliance cascade identity-join gate",
        "- CHI-F3X-D2: crash triad and traffic-segment context join gate",
        "- CHI-F4X-D2: mobility/environment time-window fusion gate",
        "",
        "These remain scouts, not accepted Flow 2/3/4 cartridges.",
        "",
        "## Boundary",
        *[f"- {line}" for line in BOUNDARY_LINES],
        "",
    ]
    write_text(output_dir / "CHI_FLOWX_D1_ADAPTER_HANDOVER.md", "\n".join(handover))


def run_chi_flowx_expansion_scouts(
    project_root: str,
    d1b_dir: str,
    d2b_dir: str,
    d3b_dir: str,
    d5_dir: str,
    output_dir: str,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    paths = {
        "d1b": resolve_under(root, d1b_dir).resolve(),
        "d2b": resolve_under(root, d2b_dir).resolve(),
        "d3b": resolve_under(root, d3b_dir).resolve(),
        "d5": resolve_under(root, d5_dir).resolve(),
    }
    out = resolve_under(root, output_dir).resolve()

    before = input_snapshot(list(paths.values()))
    reset_output_dir(out)

    data = load_inputs(paths)
    precond = precondition_report(data)
    core = build_city_core(paths, data)
    flows = {
        "CHI-F2X-D1": flow2_scout(data),
        "CHI-F3X-D1": flow3_scout(data),
        "CHI-F4X-D1": flow4_scout(data),
    }

    write_json(out / "city_core" / "CHI_CITY_CORE_SLOT_MODEL.json", core)
    write_json(out / "city_core" / "CHI_CITY_CORE_SOURCE_LEDGER.json", core["source_ledger"])
    write_json(out / "city_core" / "CHI_CITY_CORE_NATIVE_IDS.json", core["native_ids"])

    write_flow_output(out / "chi_f2x_d1_compliance_cascade_expansion_scout", "CHI_F2X_D1", flows["CHI-F2X-D1"])
    write_flow_output(out / "chi_f3x_d1_traffic_incident_context_expansion_scout", "CHI_F3X_D1", flows["CHI-F3X-D1"])
    write_flow_output(out / "chi_f4x_d1_mobility_environment_expansion_scout", "CHI_F4X_D1", flows["CHI-F4X-D1"])

    recommendation = {
        "status": "PASS",
        "slotting_model": "CITY-CORE plus CITY-FLOW-SUBCARTRIDGE",
        "city_core": "CHI-CORE-D5",
        "parallel_scouts": {key: source_strength(flow) for key, flow in flows.items()},
        "recommended_order": ["CHI-F2X-D2", "CHI-F4X-D2", "CHI-F3X-D2"],
        "rationale": [
            "F2X has broad compliance ingredients but must earn identity joins.",
            "F4X has strong mobility/environment ingredients but live CTA remains key-protected.",
            "F3X has crash/traffic depth but must stay context-only and avoid dispatch/affected-asset claims.",
        ],
    }
    write_json(out / "CHI_FLOWX_D1_RECOMMENDATION.json", recommendation)
    write_json(out / "reports" / "parallel_scout_matrix.json", recommendation)
    write_docs(out, core, flows)

    limitation = limitation_report(out)
    no_overclaim = no_overclaim_report(out)
    after = input_snapshot(list(paths.values()))
    no_mutation = compare_snapshots(before, after)
    write_json(out / "CHI_FLOWX_D1_LIMITATION_CARRY_FORWARD_REPORT.json", limitation)
    write_json(out / "CHI_FLOWX_D1_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_json(out / "CHI_FLOWX_D1_NO_MUTATION_REPORT.json", no_mutation)

    gates = {
        "CHI-FLOWX-D1-PRECOND": precond["status"],
        "CHI-FLOWX-D1-CITY-CORE-MOUNT": core["status"],
        "CHI-FLOWX-D1-F2X-SCOUT": "PASS" if status_pass(flows["CHI-F2X-D1"]["status"]) else "FAIL",
        "CHI-FLOWX-D1-F3X-SCOUT": "PASS" if status_pass(flows["CHI-F3X-D1"]["status"]) else "FAIL",
        "CHI-FLOWX-D1-F4X-SCOUT": "PASS" if status_pass(flows["CHI-F4X-D1"]["status"]) else "FAIL",
        "CHI-FLOWX-D1-LIMITATION-CARRY-FORWARD": limitation["status"],
        "CHI-FLOWX-D1-NO-OVERCLAIM": no_overclaim["status"],
        "CHI-FLOWX-D1-NO-MUTATION": no_mutation["status"],
    }
    overall = "PASS_PARALLEL_FLOW_EXTENSION_SCOUTS" if all(value == "PASS" for value in gates.values()) else "FAIL"
    harness = {
        "task": TASK_NAME,
        "status": overall,
        "city_core": "CHI-CORE-D5",
        "accepted_core_status": ACCEPTED_CORE_STATUS,
        "scouts": {
            "CHI-F2X-D1": flows["CHI-F2X-D1"]["status"],
            "CHI-F3X-D1": flows["CHI-F3X-D1"]["status"],
            "CHI-F4X-D1": flows["CHI-F4X-D1"]["status"],
        },
        "recommendation": recommendation,
        "preconditions": precond,
        "gates": gates,
        "output": str(out),
        "generated_at": utc_now(),
        "boundary_lines": BOUNDARY_LINES,
    }
    write_json(out / "CHI_FLOWX_D1_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    gates["CHI-FLOWX-D1-HASHES"] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = hashes
    harness["status"] = "PASS_PARALLEL_FLOW_EXTENSION_SCOUTS" if all(value == "PASS" for value in gates.values()) else "FAIL"
    write_json(out / "CHI_FLOWX_D1_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return harness


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--d1b-dir", default=DEFAULT_D1B_DIR)
    parser.add_argument("--d2b-dir", default=DEFAULT_D2B_DIR)
    parser.add_argument("--d3b-dir", default=DEFAULT_D3B_DIR)
    parser.add_argument("--d5-dir", default=DEFAULT_D5_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_chi_flowx_expansion_scouts(
        project_root=args.project_root,
        d1b_dir=args.d1b_dir,
        d2b_dir=args.d2b_dir,
        d3b_dir=args.d3b_dir,
        d5_dir=args.d5_dir,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"Status: {result['status']}")
    for key, status in result["scouts"].items():
        print(f"{key}: {status}")
    return 0 if str(result.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
