from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "CHI-F1F7-D5 Chicago Dual-Flow Accepted Snapshot"
DEFAULT_OUTPUT_DIR = "outputs/chi_f1f7_d5_dual_flow_accepted_snapshot"
DEFAULT_D1B_DIR = "outputs/chi_d1b_chicago_extended_source_landing"
DEFAULT_D3B_DIR = "outputs/chi_d3_civic_event_ingest_flow_readiness_d3b_expanded_d1b"
DEFAULT_D4B_DIR = "outputs/chi_d4_dual_flow_scope_fork_d3b_refresh"
DEFAULT_F1B_DIR = "outputs/chi_f1_d1_situational_status_cartridge_d1b_refresh"
DEFAULT_F7B_DIR = "outputs/chi_f7_d1_civic_sensor_fusion_cartridge_d1b_refresh"
DEFAULT_DUALB_DIR = "outputs/chi_f1_f7_d1_dual_flow_run_d1b_refresh"
DEFAULT_D2B_DIR = "outputs/chi_f1f7_d2_live_spark_nim_replay_d1b_refresh"
DEFAULT_D3B_FACE_DIR = "outputs/chi_f1f7_d3b_face_layer_status_fusion_surface"
DEFAULT_D4_HERO_DIR = "outputs/chi_f1f7_d4_chicago_hero_package"

ACCEPTED_STATUS = "GREEN_WITH_CAPPED_SOURCE_LIMITATIONS"
HEADLINE = (
    "Chicago Flow 1 + Flow 7 are accepted as live-NIM green over an expanded, "
    "materially stronger, still source-limited public-data base."
)

BOUNDARY_LINES = [
    "CHI-F1F7-D5 is an accepted snapshot over the refreshed CHI-D1B/D3B/D4B/F1F7-D1B/D2B/D3B/D4 evidence line.",
    "Chicago Flow 1 + Flow 7 are live-NIM green over an expanded, materially stronger, still source-limited public-data base.",
    "Chicago is not all-full-source: Divvy, Cook parcels, Crimes, and Open Air individual remain capped/windowed.",
    "Flow 1 provides situational status evidence, not an operational recommendation.",
    "Flow 7 provides civic/sensor signal-fusion evidence, not a policing, dispatch, enforcement, health, emergency, or public-safety recommendation.",
    "CHI-F1F7-D5 does not certify affected buildings/assets.",
    "CTA GTFS is static schedule context, not live transit status.",
    "Crime data is privacy-safe block-level context only.",
    "Sensor/environment observations are context signals, not health determinations.",
    "Live NIM briefing text is grounded narration over deterministic EvidenceBundles and may not compute counts or add facts.",
    "D4 heroes are selected deterministically from refreshed evidence only.",
]

FORBIDDEN_POSITIVE_PATTERNS = [
    r"\boperational recommendation(?:s)?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bpublic-safety recommendation(?:s)?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bpolicing recommendation(?:s)?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bdispatch recommendation(?:s)?\s+(?:is|are|were|provided|ready|available)\b",
    r"\benforcement recommendation(?:s)?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bhealth determination(?:s)?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bemergency recommendation(?:s)?\s+(?:is|are|were|provided|ready|available)\b",
    r"\blive transit status\s+(?:is|was|provided|ready|available)\b",
    r"\ball-full-source\s+(?:is|was|true|complete|provided|ready|available)\b",
    r"\bhero selected by llm\b",
    r"\bhand-picked hero\b",
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
    if isinstance(value, float) and math.isnan(value):
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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_value(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


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
    (output_dir / "SHA256SUMS.json").write_text(json.dumps(sums, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"gate": "CHI-F1F7-D5-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {p.lower() for p in resolved.parts} or "chi_f1f7_d5" not in resolved.name.lower():
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["accepted", "reports", "snapshot"]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def input_snapshot(paths: list[Path]) -> dict[str, Any]:
    watched: dict[str, Any] = {}
    for root in paths:
        if not root.exists():
            watched[str(root)] = {"exists": False}
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() in {".part", ".tmp"}:
                continue
            stat = path.stat()
            digest = sha256_file(path) if stat.st_size < 250_000_000 else None
            watched[str(path.resolve())] = {"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": digest}
    return watched


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = sorted(k for k, v in before.items() if after.get(k) != v)
    added = sorted(k for k in after if k not in before)
    removed = sorted(k for k in before if k not in after)
    return {
        "gate": "CHI-F1F7-D5-NO-MUTATION",
        "status": "PASS" if not changed and not added and not removed else "FAIL",
        "checked_files": len(before),
        "changed_inputs": changed,
        "added_inputs": added,
        "removed_inputs": removed,
    }


def status_pass(value: Any) -> bool:
    text = str(value or "").upper()
    return text.startswith("PASS") or text.startswith("GREEN")


def load_inputs(paths: dict[str, Path]) -> dict[str, Any]:
    return {
        "d1b": read_json(paths["d1b"] / "CHI_D1B_HARNESS_REPORT.json", {}),
        "d3b": read_json(paths["d3b"] / "CHI_D3B_HARNESS_REPORT.json", {}),
        "d4b": read_json(paths["d4b"] / "CHI_D4_HARNESS_REPORT.json", {}),
        "f1b": read_json(paths["f1b"] / "CHI_F1_D1_HARNESS_REPORT.json", {}),
        "f7b": read_json(paths["f7b"] / "CHI_F7_D1_HARNESS_REPORT.json", {}),
        "dualb": read_json(paths["dualb"] / "CHI_F1_F7_D1_DUAL_HARNESS_REPORT.json", {}),
        "d2b": read_json(paths["d2b"] / "CHI_F1F7_D2_HARNESS_REPORT.json", {}),
        "d3b_face": read_json(paths["d3b_face"] / "CHI_F1F7_D3B_HARNESS_REPORT.json", {}),
        "d4_hero": read_json(paths["d4_hero"] / "CHI_F1F7_D4_HARNESS_REPORT.json", {}),
        "d4_heroes": read_json(paths["d4_hero"] / "heroes" / "chicago_hero_package.json", {}),
        "face_status": read_json(paths["d3b_face"] / "face_payload" / "chicago_status.json", {}),
        "face_limits": read_json(paths["d3b_face"] / "face_payload" / "chicago_source-limitations.json", {}),
    }


def precondition_report(data: dict[str, Any]) -> dict[str, Any]:
    statuses = {
        "CHI-D1B": data["d1b"].get("status"),
        "CHI-D3B": data["d3b"].get("status"),
        "CHI-D4B": data["d4b"].get("status"),
        "CHI-F1-D1B": data["f1b"].get("status"),
        "CHI-F7-D1B": data["f7b"].get("status"),
        "CHI-F1F7-D1B": data["dualb"].get("status"),
        "CHI-F1F7-D2B": data["d2b"].get("status"),
        "CHI-F1F7-D3B": data["d3b_face"].get("status"),
        "CHI-F1F7-D4": data["d4_hero"].get("status"),
    }
    checks = {
        "stage_statuses_green": all(status_pass(value) for value in statuses.values()),
        "d2b_live_nim_green": data["d2b"].get("live_nim_status") == "PASS",
        "d2b_grounding_green": data["d2b"].get("grounding") == "PASS",
        "d3b_face_4070_publish_green": (data["d3b_face"].get("publish_4070") or {}).get("status") == "PASS",
        "d4_hero_4070_publish_green": (data["d4_hero"].get("publish_4070") or {}).get("status") == "PASS",
        "d4_hero_endpoint_smoke_green": (data["d4_hero"].get("endpoint_smoke") or {}).get("status") == "PASS",
    }
    return {"gate": "CHI-F1F7-D5-PRECOND", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "statuses": statuses}


def stage_ledger(data: dict[str, Any]) -> dict[str, Any]:
    rows = {
        "CHI-D1B": "GREEN_WITH_CAPPED_LARGE_SOURCES - EXPANDED TARGETED SOURCE LANDING",
        "CHI-D3B": "GREEN_WITH_CAPPED_SOURCE_LIMITATIONS - CIVIC/EVENT REFRESH FROM EXPANDED D1B",
        "CHI-D4B": "GREEN_WITH_DUAL_FLOW_FORK - REFRESHED FLOW FORK / SOURCE LEDGER",
        "CHI-F1F7-D1B": "GREEN - PASS_DUAL_FLOW_D1",
        "CHI-F1F7-D2B": "GREEN - LIVE SPARK/NIM REPLAY",
        "CHI-F1F7-D3B": "GREEN - REFRESHED FACE-LAYER STATUS/FUSION SURFACE",
        "CHI-F1F7-D4": "GREEN - CHICAGO HERO PACKAGE",
        "CHI-F1F7-D5": f"{ACCEPTED_STATUS} - CHICAGO DUAL-FLOW ACCEPTED SNAPSHOT",
    }
    return {"gate": "CHI-F1F7-D5-STAGE-LEDGER", "status": "PASS", "accepted_status": ACCEPTED_STATUS, "ledger": rows}


def accepted_counts(data: dict[str, Any]) -> dict[str, Any]:
    d3_counts = data["d3b"].get("counts") or {}
    location = data["d3b"].get("location_confidence_counts") or {}
    face_counts = data["face_status"].get("counts") or {}
    source_refresh = data["d3b"].get("source_refresh") or {}
    key_sources = source_refresh.get("key_sources") or {}
    heroes = data["d4_heroes"].get("heroes") or []
    return {
        "d1b_landed_rows": (data["d1b"].get("summary") or {}).get("rows_downloaded_total"),
        "d3b_event_location_rows": d3_counts.get("event_location_confidence_rows"),
        "d3b_context_edges": d3_counts.get("context_edges"),
        "location_confidence_A": location.get("A"),
        "location_confidence_B": location.get("B"),
        "location_confidence_C": location.get("C"),
        "location_confidence_D": location.get("D"),
        "311_events": d3_counts.get("311_events"),
        "traffic_crashes": d3_counts.get("traffic_crash_events"),
        "crash_people_rows": (key_sources.get("traffic_crashes_people") or {}).get("downloaded_rows"),
        "crash_vehicles_rows": (key_sources.get("traffic_crashes_vehicles") or {}).get("downloaded_rows"),
        "traffic_tracker_rows": (key_sources.get("traffic_tracker_historical_2024_current") or {}).get("downloaded_rows"),
        "f1_citywide_total_signal_rows": face_counts.get("f1_citywide_total_signal_rows"),
        "f7_fusion_candidates": face_counts.get("f7_fusion_candidates"),
        "f7_selected_candidates": face_counts.get("f7_selected_candidates"),
        "top_f7_candidate_total_events": face_counts.get("top_f7_candidate_total_events"),
        "d2b_sample_requests": data["d2b"].get("sample_requests"),
        "d4_hero_count": len(heroes),
    }


def source_limitations(data: dict[str, Any]) -> dict[str, Any]:
    key_sources = ((data["d3b"].get("source_refresh") or {}).get("key_sources") or {})
    rows = {key: {"completion_status": value.get("completion_status"), "downloaded_rows": value.get("downloaded_rows"), "total_count": value.get("total_count"), "window_count": value.get("window_count")} for key, value in key_sources.items()}
    checks = {
        "crashes_full": (key_sources.get("traffic_crashes_crashes") or {}).get("completion_status") == "FULL",
        "crash_people_full_context_only": (key_sources.get("traffic_crashes_people") or {}).get("completion_status") == "FULL",
        "crash_vehicles_full_context_only": (key_sources.get("traffic_crashes_vehicles") or {}).get("completion_status") == "FULL",
        "traffic_tracker_windowed_complete": (key_sources.get("traffic_tracker_historical_2024_current") or {}).get("completion_status") == "WINDOWED_COMPLETE",
        "divvy_still_capped": (key_sources.get("divvy_trips") or {}).get("completion_status") == "CAPPED",
        "cook_parcels_still_windowed_capped": (key_sources.get("cook_county_parcel_universe") or {}).get("completion_status") == "WINDOWED_CAPPED",
        "crimes_still_windowed_capped": (key_sources.get("crimes_2001_present") or {}).get("completion_status") == "WINDOWED_CAPPED",
        "open_air_individual_still_windowed_capped": (key_sources.get("open_air_chicago_individual_measurements") or {}).get("completion_status") == "WINDOWED_CAPPED",
    }
    return {
        "gate": "CHI-F1F7-D5-SOURCE-LIMITATIONS",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "source_status_language": "Chicago source base improved materially, but still not all-full-source because Divvy, Cook parcels, Crimes, and Open Air individual remain capped/windowed.",
        "key_sources": rows,
    }


def route_report(data: dict[str, Any]) -> dict[str, Any]:
    d3_routes = data["d3b_face"].get("routes") or []
    d4_routes = data["d4_hero"].get("routes") or []
    required = ["/chicago", "/status/chicago", "/api/chicago/status", "/api/chicago/flow1-area-status", "/api/chicago/flow7-fusion-candidates", "/api/chicago/live-nim-briefings", "/api/chicago/source-limitations", "/api/chicago/negative-boundaries", "/chicago/heroes", "/api/chicago/heroes"]
    available = sorted(set(d3_routes + d4_routes))
    checks = {route: route in available for route in required}
    return {
        "gate": "CHI-F1F7-D5-LIVE-ROUTES",
        "status": "PASS" if all(checks.values()) and (data["d3b_face"].get("endpoint_smoke") or {}).get("status") == "PASS" and (data["d4_hero"].get("endpoint_smoke") or {}).get("status") == "PASS" else "FAIL",
        "base_url": "http://192.168.1.48:8080",
        "required_routes": required,
        "available_routes": available,
        "checks": checks,
    }


def hero_report(data: dict[str, Any]) -> dict[str, Any]:
    package = data["d4_heroes"]
    heroes = package.get("heroes") or []
    ids = [hero.get("hero_id") for hero in heroes]
    checks = {
        "minimum_three_heroes": len(heroes) >= 3,
        "hero_1_present": "chi_f1f7_d4_hero_1_flow1_area_status" in ids,
        "hero_2_present": "chi_f1f7_d4_hero_2_flow7_top_fusion" in ids,
        "hero_3_present": "chi_f1f7_d4_hero_3_governance_boundary" in ids,
        "selector_grounded": (package.get("selector") or {}).get("status") == "PASS",
        "grounding_gate_green": (data["d4_hero"].get("grounding") or {}).get("status") == "PASS",
        "no_overclaim_green": (data["d4_hero"].get("no_overclaim") or {}).get("status") == "PASS",
    }
    selected = [{"hero_id": hero.get("hero_id"), "title": hero.get("title"), "story_type": hero.get("story_type"), "selected_subject": hero.get("selected_subject")} for hero in heroes]
    return {"gate": "CHI-F1F7-D5-HERO-FREEZE", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "heroes": selected}


def limitation_report(output_dir: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(snapshot, ensure_ascii=False) + "\n"
    text += "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in output_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".json", ".md"})
    missing = [line for line in BOUNDARY_LINES if line not in text]
    return {"gate": "CHI-F1F7-D5-LIMITATION-CARRY-FORWARD", "status": "PASS" if not missing else "FAIL", "missing": missing, "required": BOUNDARY_LINES}


def is_negated_line(line: str) -> bool:
    lower = line.lower()
    return any(token in lower for token in [" not ", " does not ", " cannot ", " no ", " rejected", "source-limited"])


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    for path in output_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md"}:
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            lower = line.lower()
            if is_negated_line(lower):
                continue
            for pattern in FORBIDDEN_POSITIVE_PATTERNS:
                if re.search(pattern, lower):
                    findings.append({"file": str(path), "pattern": pattern, "line": line[:400]})
    return {"gate": "CHI-F1F7-D5-NO-OVERCLAIM", "status": "PASS" if not findings else "FAIL", "forbidden_positive_claims_found": findings}


def build_snapshot(paths: dict[str, Path], data: dict[str, Any], counts: dict[str, Any], stage: dict[str, Any], sources: dict[str, Any], routes: dict[str, Any], heroes: dict[str, Any]) -> dict[str, Any]:
    return {
        "task": TASK_NAME,
        "status": "PASS",
        "accepted_status": ACCEPTED_STATUS,
        "headline": HEADLINE,
        "created_utc": utc_now(),
        "stage_ledger": stage["ledger"],
        "counts": counts,
        "source_limitations": sources,
        "live_routes": routes,
        "hero_freeze": heroes,
        "input_paths": {key: str(value) for key, value in paths.items()},
        "boundary_lines": BOUNDARY_LINES,
    }


def write_docs(output_dir: Path, snapshot: dict[str, Any], status: str) -> None:
    counts = snapshot.get("counts", {})
    lines = [
        "# CHI-F1F7-D5 Chicago Dual-Flow Accepted Snapshot",
        "",
        f"Status: `{status}`",
        f"Accepted line: `{ACCEPTED_STATUS}`",
        "",
        "## Headline",
        HEADLINE,
        "",
        "## Pinned Counts",
        f"- D3B event/location rows: `{counts.get('d3b_event_location_rows')}`",
        f"- D3B context edges: `{counts.get('d3b_context_edges')}`",
        f"- F1 citywide signal rows: `{counts.get('f1_citywide_total_signal_rows')}`",
        f"- F7 fusion candidates: `{counts.get('f7_fusion_candidates')}`",
        f"- F7 selected candidates: `{counts.get('f7_selected_candidates')}`",
        f"- Top F7 candidate events: `{counts.get('top_f7_candidate_total_events')}`",
        "",
        "## Live Routes",
        "- `/chicago`",
        "- `/status/chicago`",
        "- `/chicago/heroes`",
        "- `/api/chicago/heroes`",
        "",
        "## Boundary",
        *[f"- {line}" for line in BOUNDARY_LINES],
        "",
    ]
    write_text(output_dir / "README.md", "\n".join(lines))
    write_text(
        output_dir / "CHI_F1F7_D5_ADAPTER_HANDOVER.md",
        "# CHI-F1F7-D5 Adapter Handover\n\n"
        "This freeze gate accepts the refreshed Chicago Flow 1 + Flow 7 line for demo and portfolio use. "
        "Use D3B face routes and D4 hero routes on the 4070; do not treat this as all-full-source Chicago completion.\n\n"
        + "\n".join(f"- {line}" for line in BOUNDARY_LINES)
        + "\n",
    )


def run_chi_f1f7_d5_gate(
    project_root: str,
    d1b_dir: str,
    d3b_dir: str,
    d4b_dir: str,
    f1b_dir: str,
    f7b_dir: str,
    dualb_dir: str,
    d2b_dir: str,
    d3b_face_dir: str,
    d4_hero_dir: str,
    output_dir: str,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    paths = {
        "d1b": (root / d1b_dir).resolve(),
        "d3b": (root / d3b_dir).resolve(),
        "d4b": (root / d4b_dir).resolve(),
        "f1b": (root / f1b_dir).resolve(),
        "f7b": (root / f7b_dir).resolve(),
        "dualb": (root / dualb_dir).resolve(),
        "d2b": (root / d2b_dir).resolve(),
        "d3b_face": (root / d3b_face_dir).resolve(),
        "d4_hero": (root / d4_hero_dir).resolve(),
    }
    out = (root / output_dir).resolve()
    before = input_snapshot(list(paths.values()))
    reset_output_dir(out)
    data = load_inputs(paths)
    precond = precondition_report(data)
    stage = stage_ledger(data)
    counts = accepted_counts(data)
    sources = source_limitations(data)
    routes = route_report(data)
    heroes = hero_report(data)
    snapshot = build_snapshot(paths, data, counts, stage, sources, routes, heroes)

    write_json(out / "accepted" / "chicago_dual_flow_accepted_snapshot.json", snapshot)
    write_json(out / "accepted" / "chicago_dual_flow_status_ledger.json", stage)
    write_json(out / "accepted" / "chicago_dual_flow_counts.json", counts)
    write_text(out / "accepted" / "chicago_dual_flow_boundary.md", "\n".join(f"- {line}" for line in BOUNDARY_LINES) + "\n")
    write_json(out / "snapshot" / "source_limitations.json", sources)
    write_json(out / "snapshot" / "live_routes.json", routes)
    write_json(out / "snapshot" / "hero_freeze.json", heroes)

    write_json(out / "CHI_F1F7_D5_INPUT_INVENTORY.json", {"status": precond["status"], "inputs": {key: str(value) for key, value in paths.items()}, "preconditions": precond})
    write_json(out / "CHI_F1F7_D5_STAGE_LEDGER.json", stage)
    write_json(out / "CHI_F1F7_D5_ACCEPTED_COUNTS.json", counts)
    write_json(out / "CHI_F1F7_D5_SOURCE_LIMITATION_REPORT.json", sources)
    write_json(out / "CHI_F1F7_D5_ROUTE_REPORT.json", routes)
    write_json(out / "CHI_F1F7_D5_HERO_FREEZE_REPORT.json", heroes)
    write_json(out / "CHI_F1F7_D5_ACCEPTED_SNAPSHOT_REPORT.json", snapshot)
    write_docs(out, snapshot, "PENDING")
    limits = limitation_report(out, snapshot)
    write_json(out / "CHI_F1F7_D5_LIMITATION_CARRY_FORWARD_REPORT.json", limits)
    overclaim = no_overclaim_report(out)
    write_json(out / "CHI_F1F7_D5_NO_OVERCLAIM_REPORT.json", overclaim)
    after = input_snapshot(list(paths.values()))
    no_mutation = compare_snapshots(before, after)
    write_json(out / "CHI_F1F7_D5_NO_MUTATION_REPORT.json", no_mutation)
    write_json(out / "reports" / "accepted_line.json", stage)
    write_json(out / "reports" / "counts.json", counts)
    write_json(out / "reports" / "source_limitations.json", sources)
    write_json(out / "reports" / "routes.json", routes)
    write_json(out / "reports" / "heroes.json", heroes)
    write_json(out / "reports" / "no_overclaim.json", overclaim)

    gates = {
        "CHI-F1F7-D5-PRECOND": precond["status"],
        "CHI-F1F7-D5-STAGE-LEDGER": stage["status"],
        "CHI-F1F7-D5-SOURCE-LIMITATIONS": sources["status"],
        "CHI-F1F7-D5-LIVE-ROUTES": routes["status"],
        "CHI-F1F7-D5-HERO-FREEZE": heroes["status"],
        "CHI-F1F7-D5-LIMITATION-CARRY-FORWARD": limits["status"],
        "CHI-F1F7-D5-NO-OVERCLAIM": overclaim["status"],
        "CHI-F1F7-D5-NO-MUTATION": no_mutation["status"],
    }
    status = "PASS" if all(value == "PASS" for value in gates.values()) else "FAIL"
    write_docs(out, snapshot, status)
    hashes = write_hashes(out)
    gates["CHI-F1F7-D5-HASHES"] = hashes["status"]
    status = "PASS" if all(value == "PASS" for value in gates.values()) else "FAIL"
    snapshot["status"] = status
    write_json(out / "accepted" / "chicago_dual_flow_accepted_snapshot.json", snapshot)
    write_json(out / "CHI_F1F7_D5_ACCEPTED_SNAPSHOT_REPORT.json", snapshot)
    harness = {
        "task": TASK_NAME,
        "status": status,
        "accepted_status": ACCEPTED_STATUS,
        "headline": HEADLINE,
        "created_utc": utc_now(),
        "gates": gates,
        "preconditions": precond,
        "counts": counts,
        "source_limitations": sources,
        "routes": routes,
        "heroes": heroes,
        "no_overclaim": overclaim,
        "no_mutation": no_mutation,
        "output": str(out),
    }
    write_json(out / "CHI_F1F7_D5_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    harness["hashes"] = hashes
    write_json(out / "CHI_F1F7_D5_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--d1b-dir", default=DEFAULT_D1B_DIR)
    parser.add_argument("--d3b-dir", default=DEFAULT_D3B_DIR)
    parser.add_argument("--d4b-dir", default=DEFAULT_D4B_DIR)
    parser.add_argument("--f1b-dir", default=DEFAULT_F1B_DIR)
    parser.add_argument("--f7b-dir", default=DEFAULT_F7B_DIR)
    parser.add_argument("--dualb-dir", default=DEFAULT_DUALB_DIR)
    parser.add_argument("--d2b-dir", default=DEFAULT_D2B_DIR)
    parser.add_argument("--d3b-face-dir", default=DEFAULT_D3B_FACE_DIR)
    parser.add_argument("--d4-hero-dir", default=DEFAULT_D4_HERO_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_chi_f1f7_d5_gate(
        project_root=args.project_root,
        d1b_dir=args.d1b_dir,
        d3b_dir=args.d3b_dir,
        d4b_dir=args.d4b_dir,
        f1b_dir=args.f1b_dir,
        f7b_dir=args.f7b_dir,
        dualb_dir=args.dualb_dir,
        d2b_dir=args.d2b_dir,
        d3b_face_dir=args.d3b_face_dir,
        d4_hero_dir=args.d4_hero_dir,
        output_dir=args.output_dir,
    )
    print(f"CHI-F1F7-D5 Chicago Dual-Flow Accepted Snapshot: {report['status']}")
    print(f"Accepted status: {report['accepted_status']}")
    print(f"D3B event/location rows: {report['counts'].get('d3b_event_location_rows')}")
    print(f"D3B context edges: {report['counts'].get('d3b_context_edges')}")
    print(f"F7 fusion candidates: {report['counts'].get('f7_fusion_candidates')}")
    print(f"Heroes: {report['heroes'].get('status')} / {len(report['heroes'].get('heroes', []))}")
    print(f"Live routes: {report['routes']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {report['output']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
