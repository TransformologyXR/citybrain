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


TASK_NAME = "F3-NYC-D9 Flow 3 Accepted Snapshot"
DEFAULT_OUTPUT_DIR = "outputs/f3_nyc_d9_flow3_accepted_snapshot"
DEFAULT_D2C_DIR = "outputs/f3_nyc_d2c_capped_working_set_refresh"
DEFAULT_D3_DIR = "outputs/f3_nyc_d3_affected_asset_response_context"
DEFAULT_D4_DIR = "outputs/f3_nyc_d4_candidate_prioritization_review_routing"
DEFAULT_D5_DIR = "outputs/f3_nyc_d5_governed_evidence_briefing"
DEFAULT_D6_DIR = "outputs/f3_nyc_d6_live_spark_nim_replay"
DEFAULT_D7_DIR = "outputs/f3_nyc_d7_live_face_layer_route_map_trace"
DEFAULT_D8_DIR = "outputs/f3_nyc_d8_flow3_hero_package"

HEADLINE = (
    "NYC Flow 3 is green as a governed incident-response / candidate-asset / "
    "operator-review cartridge over the current capped working-set source base."
)

BOUNDARY_LINES = [
    "This is a governed Flow 3 accepted snapshot over the current capped working-set source base.",
    "It is suitable for demo/live replay/hero presentation.",
    "It is not final full-source Flow 3 completion until Fire Dispatch and EMS full downloads are incorporated.",
    "D3 candidate tax-lot context is not certified affected buildings/assets.",
    "D4 route plans are operator-review itineraries, not emergency dispatch or navigable routing.",
    "D5 briefings are deterministic EvidenceBundle briefings.",
    "D6 is live Spark/NIM replay over D5 evidence.",
    "D8 heroes are subject-aligned with D5/D6 evidence.",
    "Fire Dispatch and EMS remain capped until full-source refresh.",
]

D8_SELECTOR_CAVEATS = [
    "3+ stop route preference was not applied because exact D5/D6 route grounding is only available for this route.",
    "Different-borough preference was not applied because exact D5/D6 trace grounding is only available for this route stop.",
]

EXPECTED_HERO_SUBJECTS = {
    "hero_1_top_candidate_incident": "event:us-nyc:flow3:mvc_crash:4463710",
    "hero_2_top_operator_review_route": "review_route:us-nyc:flow3:d4:001:brooklyn:resource_us_nyc_fdny_firehouse_engine_227",
    "hero_3_route_stop_trace_borough_diverse": "review_route:us-nyc:flow3:d4:001:brooklyn:resource_us_nyc_fdny_firehouse_engine_227#1",
    "hero_4_governance_negative_request": "negative_affected_buildings",
}

EXPECTED_SOURCE_COUNTS = {
    "mvc_crashes": {"downloaded_rows": 2269187, "full_rows": 2269187, "source_status": "full_complete"},
    "fdny_firehouses": {"downloaded_rows": 219, "full_rows": 219, "source_status": "full_complete"},
    "fire_incident_dispatch": {"downloaded_rows": 2000000, "full_rows": 11819520, "source_status": "capped"},
    "ems_incident_dispatch": {"downloaded_rows": 3000000, "full_rows": 29572156, "source_status": "capped"},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):
        try:
            return clean_value(value.item())
        except Exception:
            pass
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
    sums = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "F3-NYC-D9-HASHES", "status": "PASS", "file_count": len(sums)}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()):
            raise ValueError(f"refusing to remove path outside workspace: {resolved}")
        if "outputs" not in {part.lower() for part in resolved.parts} or "f3_nyc_d9" not in resolved.name.lower():
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for child in ["snapshot", "reports"]:
        (output_dir / child).mkdir(parents=True, exist_ok=True)


def input_snapshot(paths: list[Path]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for root in paths:
        if not root.exists():
            snapshot[str(root)] = {"exists": False}
            continue
        files = [root] if root.is_file() else [p for p in sorted(root.rglob("*")) if p.is_file()]
        for path in files:
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            digest = None
            if stat.st_size <= 100_000_000:
                digest = sha256_file(path)
            snapshot[str(path)] = {"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": digest}
    return snapshot


def stage_ok(status: Any) -> bool:
    return isinstance(status, str) and status.startswith("PASS")


def find_json(root: Path, *names: str) -> Any:
    for name in names:
        direct = root / name
        if direct.exists():
            return read_json(direct, {})
        in_reports = root / "reports" / name
        if in_reports.exists():
            return read_json(in_reports, {})
    return {}


def load_stage_inputs(paths: dict[str, Path]) -> dict[str, Any]:
    return {
        "d2c_harness": read_json(paths["d2c"] / "F3_NYC_D2C_HARNESS_REPORT.json", {}),
        "d2c_counts": read_json(paths["d2c"] / "F3_NYC_D2C_SOURCE_COUNT_REPORT.json", {}),
        "d2c_capped": find_json(paths["d2c"], "capped_vs_full_status.json"),
        "d3_harness": read_json(paths["d3"] / "F3_NYC_D3_HARNESS_REPORT.json", {}),
        "d3_location": read_json(paths["d3"] / "F3_NYC_D3_LOCATION_CONFIDENCE_REPORT.json", {}),
        "d4_harness": read_json(paths["d4"] / "F3_NYC_D4_HARNESS_REPORT.json", {}),
        "d4_route": read_json(paths["d4"] / "F3_NYC_D4_OPERATOR_REVIEW_ROUTE_PLAN_REPORT.json", {}),
        "d5_harness": read_json(paths["d5"] / "F3_NYC_D5_HARNESS_REPORT.json", {}),
        "d5_bundle_report": read_json(paths["d5"] / "F3_NYC_D5_EVIDENCE_BUNDLE_REPORT.json", {}),
        "d6_harness": read_json(paths["d6"] / "F3_NYC_D6_HARNESS_REPORT.json", {}),
        "d6_runtime": read_json(paths["d6"] / "F3_NYC_D6_NIM_RUNTIME_REPORT.json", {}),
        "d7_harness": read_json(paths["d7"] / "F3_NYC_D7_HARNESS_REPORT.json", {}) if paths["d7"].exists() else {},
        "d8_harness": read_json(paths["d8"] / "F3_NYC_D8_HARNESS_REPORT.json", {}),
        "d8_selector": read_json(paths["d8"] / "F3_NYC_D8_SELECTOR_REPORT.json", {}),
        "d8_hero_index": read_json(paths["d8"] / "heroes" / "hero_index.json", {}),
    }


def source_counts(data: dict[str, Any]) -> dict[str, Any]:
    counts = data["d2c_harness"].get("counts") or data["d2c_counts"].get("counts") or data["d2c_counts"]
    return counts if isinstance(counts, dict) else {}


def build_source_status(data: dict[str, Any]) -> dict[str, Any]:
    counts = source_counts(data)
    sources: dict[str, Any] = {}
    for key, expected in EXPECTED_SOURCE_COUNTS.items():
        row = counts.get(key, {})
        sources[key] = {
            "label": row.get("label", key),
            "downloaded_rows": row.get("downloaded_rows"),
            "full_rows": row.get("full_rows"),
            "source_status": row.get("source_status"),
            "expected": expected,
            "matches_expected": all(row.get(k) == v for k, v in expected.items()),
        }
    fire_full = sources["fire_incident_dispatch"]["source_status"] == "full_complete"
    ems_full = sources["ems_incident_dispatch"]["source_status"] == "full_complete"
    snapshot_status = "PASS" if fire_full and ems_full else "PASS_WITH_CAPPED_SOURCE_LIMITATION"
    gate_pass = all(row["matches_expected"] for row in sources.values())
    return {
        "gate": "F3-NYC-D9-SOURCE-STATUS",
        "status": "PASS" if gate_pass else "FAIL",
        "snapshot_status": snapshot_status,
        "sources": sources,
        "required_language": [
            "MVC crashes: full-source complete - 2,269,187 / 2,269,187",
            "FDNY firehouses: full-source complete - 219 / 219",
            "Fire Dispatch: capped - 2,000,000 / 11,819,520",
            "EMS Dispatch: capped - 3,000,000 / 29,572,156",
        ],
        "boundary": BOUNDARY_LINES[:3],
    }


def build_stage_ledger(data: dict[str, Any]) -> dict[str, Any]:
    stages = {
        "F3-NYC-D2C": {
            "status": data["d2c_harness"].get("status"),
            "label": "GREEN_WITH_CAPPED_WORKING_SET",
            "gates": data["d2c_harness"].get("gates", {}),
        },
        "F3-NYC-D3": {
            "status": data["d3_harness"].get("status"),
            "label": "GREEN_WITH_LOCATION_CONFIDENCE_TIERS",
            "gates": data["d3_harness"].get("gates", {}),
        },
        "F3-NYC-D4": {
            "status": data["d4_harness"].get("status"),
            "label": "GREEN_WITH_OPERATOR_REVIEW_ROUTING_LIMITATION",
            "gates": data["d4_harness"].get("gates", {}),
        },
        "F3-NYC-D5": {
            "status": data["d5_harness"].get("status"),
            "label": "GREEN_WITH_GOVERNED_DETERMINISTIC_BRIEFINGS",
            "gates": data["d5_harness"].get("gates", {}),
        },
        "F3-NYC-D6": {
            "status": data["d6_harness"].get("status"),
            "label": "GREEN_LIVE_SPARK_NIM_REPLAY",
            "gates": data["d6_harness"].get("gates", {}),
        },
        "F3-NYC-D7": {
            "status": data["d7_harness"].get("status") or "NOT_FOUND",
            "label": "GREEN_LIVE_FACE_LAYER_ROUTE_MAP_TRACE" if data["d7_harness"] else "PROVEN_THROUGH_D8_LIVE_SURFACE_ONLY",
            "gates": data["d7_harness"].get("gates", {}),
        },
        "F3-NYC-D8": {
            "status": data["d8_harness"].get("status"),
            "label": "GREEN_DETERMINISTIC_THREE_HERO_PACKAGE",
            "gates": data["d8_harness"].get("gates", {}),
        },
    }
    required = ["F3-NYC-D2C", "F3-NYC-D3", "F3-NYC-D4", "F3-NYC-D5", "F3-NYC-D6", "F3-NYC-D8"]
    pass_required = all(stage_ok(stages[name]["status"]) for name in required)
    d7_ok = stage_ok(stages["F3-NYC-D7"]["status"]) or stage_ok(stages["F3-NYC-D8"]["status"])
    return {
        "gate": "F3-NYC-D9-STAGE-LEDGER",
        "status": "PASS" if pass_required and d7_ok else "FAIL",
        "stages": stages,
        "d7_handling": (
            "Separate D7 output included."
            if data["d7_harness"]
            else "Separate D7 output not found; live face proof is carried through D8 4070 publish and 6/6 endpoint smoke."
        ),
    }


def hero_files(d8_dir: Path) -> dict[str, dict[str, Any]]:
    heroes = {}
    for hero_id in EXPECTED_HERO_SUBJECTS:
        heroes[hero_id] = read_json(d8_dir / "heroes" / f"{hero_id}.json", {})
    return heroes


def bundle_subject(bundle: dict[str, Any]) -> str:
    query = bundle.get("query", {})
    if not isinstance(query, dict):
        query = {}
    return str(query.get("subject") or query.get("subject_id") or query.get("route_id") or bundle.get("bundle_id", ""))


def bundle_mentions(bundle: dict[str, Any], subject: str) -> bool:
    return bool(subject) and subject in json.dumps(bundle, ensure_ascii=False)


def build_hero_ledger(data: dict[str, Any], d8_dir: Path) -> dict[str, Any]:
    index = data["d8_hero_index"]
    selected = data["d8_selector"].get("selected_subject_ids") or index.get("selector", {}).get("selected_subject_ids", {})
    heroes = hero_files(d8_dir)
    hero_rows = []
    for hero_id, expected in EXPECTED_HERO_SUBJECTS.items():
        hero = heroes.get(hero_id, {})
        hero_rows.append(
            {
                "hero_id": hero_id,
                "expected_subject_id": expected,
                "selected_subject_id": selected.get(hero_id) or hero.get("selected_subject_id"),
                "hero_type": hero.get("hero_type"),
                "matches_expected": (selected.get(hero_id) or hero.get("selected_subject_id")) == expected,
                "title": hero.get("title"),
            }
        )
    preference_limitations = data["d8_selector"].get("preference_limitations") or index.get("selector", {}).get("preference_limitations", {})
    required_positive = sum(1 for row in hero_rows if row["hero_type"] == "positive_operational")
    optional = sum(1 for row in hero_rows if row["hero_type"] == "optional_governance")
    gate_pass = all(row["matches_expected"] for row in hero_rows) and required_positive >= 3 and optional >= 1
    return {
        "gate": "F3-NYC-D9-HERO-LEDGER",
        "status": "PASS" if gate_pass else "FAIL",
        "heroes": hero_rows,
        "d8_selector_caveats": D8_SELECTOR_CAVEATS,
        "d8_preference_limitations": preference_limitations,
        "acceptance_note": "D8 fixed the selector issue by requiring subject-aligned D5/D6 evidence before accepting a hero.",
    }


def build_subject_alignment_report(d8_dir: Path) -> dict[str, Any]:
    heroes = hero_files(d8_dir)
    h1 = heroes["hero_1_top_candidate_incident"]
    h2 = heroes["hero_2_top_operator_review_route"]
    h3 = heroes["hero_3_route_stop_trace_borough_diverse"]
    h4 = heroes["hero_4_governance_negative_request"]
    checks = {
        "hero_1_subject_in_d5_candidate_bundle": bundle_mentions(h1.get("d5_evidence_bundle", {}), h1.get("selected_subject_id", "")),
        "hero_1_d6_grounding_pass": h1.get("d6_grounding", {}).get("status") == "PASS",
        "hero_2_subject_in_d5_route_bundle": bundle_mentions(h2.get("d5_evidence_bundle", {}), h2.get("selected_subject_id", "")),
        "hero_2_d6_grounding_pass": h2.get("d6_grounding", {}).get("status") == "PASS",
        "hero_3_trace_subject_matches_d5_query": bundle_subject(h3.get("d5_evidence_bundle", {})) == h3.get("selected_subject_id"),
        "hero_3_event_grounded_in_d5_trace_bundle": bundle_mentions(
            h3.get("d5_evidence_bundle", {}),
            h3.get("candidate_record", {}).get("source_id", ""),
        ),
        "hero_3_d6_grounding_pass": h3.get("d6_grounding", {}).get("status") == "PASS",
        "hero_4_negative_request_rejected": h4.get("d6_grounding", {}).get("answer_status") == "rejected",
        "hero_4_not_positive_affected_building_answer": h4.get("hero_type") == "optional_governance",
    }
    return {
        "gate": "F3-NYC-D9-SUBJECT-ALIGNMENT",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "note": "D9 preserves the D8 subject-alignment correction as an acceptance condition.",
    }


def build_live_surface_report(data: dict[str, Any]) -> dict[str, Any]:
    d7_endpoint = data["d7_harness"].get("endpoint_smoke", {})
    d8_endpoint = data["d8_harness"].get("endpoint_smoke", {})
    d7_pass = data["d7_harness"].get("status") == "PASS" and d7_endpoint.get("status") == "PASS"
    d8_pass = data["d8_harness"].get("status") == "PASS" and d8_endpoint.get("status") == "PASS"
    return {
        "gate": "F3-NYC-D9-LIVE-SURFACE",
        "status": "PASS" if d8_pass and (d7_pass or not data["d7_harness"]) else "FAIL",
        "d7": {
            "included": bool(data["d7_harness"]),
            "status": data["d7_harness"].get("status"),
            "endpoint_smoke_status": d7_endpoint.get("status"),
            "live_endpoints_passed": d7_endpoint.get("live_endpoints_passed"),
            "live_endpoints_attempted": d7_endpoint.get("live_endpoints_attempted"),
            "endpoints": d7_endpoint.get("endpoints", []),
        },
        "d8": {
            "status": data["d8_harness"].get("status"),
            "endpoint_smoke_status": d8_endpoint.get("status"),
            "live_endpoints_passed": d8_endpoint.get("live_endpoints_passed"),
            "live_endpoints_attempted": d8_endpoint.get("live_endpoints_attempted"),
            "endpoints": d8_endpoint.get("endpoints", []),
        },
        "note": (
            "D7 live face proof included."
            if data["d7_harness"]
            else "D7 output absent; D8 4070 publish and endpoint smoke carry the live surface proof."
        ),
    }


def build_limitations() -> dict[str, Any]:
    return {
        "gate": "F3-NYC-D9-LIMITATION-CARRY-FORWARD",
        "status": "PASS",
        "headline": HEADLINE,
        "limitations": BOUNDARY_LINES,
        "d8_selector_caveats": D8_SELECTOR_CAVEATS,
    }


def text_for_scan(output_dir: Path) -> str:
    parts = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".json", ".md"}:
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    findings = []
    for line in text_for_scan(output_dir).lower().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if '"request":' in stripped:
            continue
        if re.search(r"fire dispatch[^.\n]*full-source complete", stripped) and "fire dispatch is capped" not in stripped:
            findings.append({"line": stripped, "reason": "fire_dispatch_full_source_claim"})
        if re.search(r"ems(?: dispatch)?[^.\n]*full-source complete", stripped) and "ems is capped" not in stripped and "ems dispatch is capped" not in stripped:
            findings.append({"line": stripped, "reason": "ems_full_source_claim"})
        if "certified affected" in stripped and "not certified affected" not in stripped and "not a certified affected" not in stripped:
            findings.append({"line": stripped, "reason": "certified_affected_positive_claim"})
        if "emergency dispatch" in stripped and not any(
            marker in stripped
            for marker in [
                "not emergency dispatch",
                "no emergency dispatch",
                "does not make emergency",
                "does not perform or claim emergency",
                "rejected",
            ]
        ):
            findings.append({"line": stripped, "reason": "emergency_dispatch_positive_claim"})
        if "navigable rout" in stripped and not any(
            marker in stripped
            for marker in [
                "not emergency dispatch or navigable",
                "not navigable rout",
                "no navigable rout",
                "does not provide navigable",
                "does not claim navigable",
                "not_dispatch_not_navigable",
            ]
        ):
            findings.append({"line": stripped, "reason": "navigable_route_positive_claim"})
    return {"gate": "F3-NYC-D9-NO-OVERCLAIM", "status": "PASS" if not findings else "FAIL", "findings": findings}


def make_reports(data: dict[str, Any], source_status: dict[str, Any]) -> dict[str, Any]:
    d3 = data["d3_harness"]
    d4 = data["d4_harness"]
    d5 = data["d5_harness"]
    d6 = data["d6_harness"]
    d8 = data["d8_harness"]
    return {
        "d2c_source_lineage": {
            "status": data["d2c_harness"].get("status"),
            "sources": source_status["sources"],
            "d5_handoff": data["d2c_harness"].get("d5_handoff", {}),
        },
        "d3_location_confidence_summary": {
            "status": d3.get("status"),
            "location_tier_counts": d3.get("location_tier_counts"),
            "mvc_tier_counts": d3.get("mvc_tier_counts"),
            "fdny_tier_counts": d3.get("fdny_tier_counts"),
            "asset_candidate_edges": d3.get("asset_candidate_edges"),
            "asset_candidates": d3.get("asset_candidates"),
            "fdny_asset_edges": d3.get("fdny_asset_edges"),
            "response_context_edges": d3.get("response_context_edges"),
        },
        "d4_review_routing_summary": {
            "status": d4.get("status"),
            "candidate_pool_rows": d4.get("candidate_pool_rows"),
            "prioritized_candidate_rows": d4.get("prioritized_candidate_rows"),
            "operator_review_routes": d4.get("operator_review_routes"),
            "operator_review_stops": d4.get("operator_review_stops"),
            "review_plan_edges": d4.get("review_plan_edges"),
            "optimization_backend": d4.get("optimization_backend"),
            "cuopt_backend_called": d4.get("cuopt_backend_called"),
        },
        "d5_evidence_briefing_summary": {
            "status": d5.get("status"),
            "evidence_bundles": d5.get("evidence_bundles"),
            "deterministic_briefings": d5.get("deterministic_briefings"),
            "briefing_grounding": d5.get("briefing_grounding", {}),
        },
        "d6_live_nim_summary": {
            "status": d6.get("status"),
            "d2c_source_status": d6.get("d2c_source_status", {}),
            "nim_runtime": data["d6_runtime"],
            "grounding_status": d6.get("grounding", {}).get("status"),
            "negative_requests": d6.get("negative_requests", {}),
        },
        "d8_hero_summary": {
            "status": d8.get("status"),
            "selector": data["d8_selector"],
            "hero_package": d8.get("hero_package", {}),
            "endpoint_smoke": {
                "status": d8.get("endpoint_smoke", {}).get("status"),
                "live_endpoints_passed": d8.get("endpoint_smoke", {}).get("live_endpoints_passed"),
                "live_endpoints_attempted": d8.get("endpoint_smoke", {}).get("live_endpoints_attempted"),
                "endpoints": d8.get("endpoint_smoke", {}).get("endpoints", []),
                "checks": d8.get("endpoint_smoke", {}).get("checks", {}),
            },
        },
        "current_vs_full_source_status": source_status,
    }


def artifact_manifest(output_dir: Path, status: str) -> dict[str, Any]:
    files = sorted(path.relative_to(output_dir).as_posix() for path in output_dir.rglob("*") if path.is_file())
    return {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "output_dir": str(output_dir),
        "files": files,
    }


def write_readme(output_dir: Path, status: str) -> None:
    lines = [
        "# F3-NYC-D9 Flow 3 Accepted Snapshot",
        "",
        f"Status: `{status}`",
        "",
        HEADLINE,
        "",
        "## Accepted Boundary",
        "",
        *[f"- {line}" for line in BOUNDARY_LINES],
        "",
        "## D8 Selector Caveat",
        "",
        *[f"- {line}" for line in D8_SELECTOR_CAVEATS],
        "",
        "D8 selector caveats are not failures. They preserve evidence discipline: D9 accepts only heroes aligned to the D5/D6 evidence currently available.",
        "",
    ]
    write_text(output_dir / "README.md", "\n".join(lines))


def write_handover(output_dir: Path, status: str) -> None:
    lines = [
        "# F3-NYC-D9 Adapter Handover",
        "",
        f"Accepted status: `{status}`",
        "",
        "Use `snapshot/flow3_current_status.json`, `snapshot/flow3_hero_index.json`, and `snapshot/flow3_live_endpoints.json` as lightweight accepted-state inputs for face/API surfaces.",
        "",
        "Do not present this as final full-source Flow 3 completion until Fire Dispatch and EMS full downloads are incorporated and D3-D8 are refreshed.",
        "",
        "Boundary:",
        *[f"- {line}" for line in BOUNDARY_LINES],
        "",
        "D8 subject-alignment note:",
        "- D8 heroes are accepted only when the selected subject is grounded in the attached D5/D6 evidence.",
        *[f"- {line}" for line in D8_SELECTOR_CAVEATS],
        "",
    ]
    write_text(output_dir / "F3_NYC_D9_ADAPTER_HANDOVER.md", "\n".join(lines))


def run_f3_nyc_d9_gate(
    d2c_dir: str = DEFAULT_D2C_DIR,
    d3_dir: str = DEFAULT_D3_DIR,
    d4_dir: str = DEFAULT_D4_DIR,
    d5_dir: str = DEFAULT_D5_DIR,
    d6_dir: str = DEFAULT_D6_DIR,
    d7_dir: str | None = DEFAULT_D7_DIR,
    d8_dir: str = DEFAULT_D8_DIR,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> dict:
    paths = {
        "d2c": Path(d2c_dir),
        "d3": Path(d3_dir),
        "d4": Path(d4_dir),
        "d5": Path(d5_dir),
        "d6": Path(d6_dir),
        "d7": Path(d7_dir) if d7_dir else Path("__missing_d7__"),
        "d8": Path(d8_dir),
    }
    output_path = Path(output_dir)
    reset_output_dir(output_path)
    watched = [paths[k] for k in ["d2c", "d3", "d4", "d5", "d6", "d8"]] + ([paths["d7"]] if paths["d7"].exists() else [])
    before = input_snapshot(watched)

    data = load_stage_inputs(paths)
    precond_checks = {
        "d2c_exists": paths["d2c"].exists(),
        "d3_exists": paths["d3"].exists(),
        "d4_exists": paths["d4"].exists(),
        "d5_exists": paths["d5"].exists(),
        "d6_exists": paths["d6"].exists(),
        "d8_exists": paths["d8"].exists(),
        "d2c_status_pass": stage_ok(data["d2c_harness"].get("status")),
        "d3_status_pass": stage_ok(data["d3_harness"].get("status")),
        "d4_status_pass": stage_ok(data["d4_harness"].get("status")),
        "d5_status_pass": stage_ok(data["d5_harness"].get("status")),
        "d6_status_pass": stage_ok(data["d6_harness"].get("status")),
        "d8_status_pass": stage_ok(data["d8_harness"].get("status")),
    }
    precond = {"gate": "F3-NYC-D9-PRECOND", "status": "PASS" if all(precond_checks.values()) else "FAIL", "checks": precond_checks}
    stage_ledger = build_stage_ledger(data)
    source_status = build_source_status(data)
    snapshot_status = source_status["snapshot_status"]
    hero_ledger = build_hero_ledger(data, paths["d8"])
    alignment = build_subject_alignment_report(paths["d8"])
    live_surface = build_live_surface_report(data)
    limitations = build_limitations()
    reports = make_reports(data, source_status)

    accepted_state = {
        "task": TASK_NAME,
        "status": snapshot_status,
        "headline": HEADLINE,
        "created_utc": utc_now(),
        "accepted_stage_range": "F3-NYC-D2C through F3-NYC-D8",
        "stage_ledger_status": stage_ledger["status"],
        "source_status": source_status,
        "hero_ledger_status": hero_ledger["status"],
        "subject_alignment_status": alignment["status"],
        "live_surface_status": live_surface["status"],
        "limitations": BOUNDARY_LINES,
        "d8_selector_caveats": D8_SELECTOR_CAVEATS,
    }

    write_readme(output_path, snapshot_status)
    write_handover(output_path, snapshot_status)
    write_json(output_path / "F3_NYC_D9_ACCEPTED_STATE.json", accepted_state)
    write_json(output_path / "F3_NYC_D9_STAGE_LEDGER.json", stage_ledger)
    write_json(output_path / "F3_NYC_D9_SOURCE_STATUS.json", source_status)
    write_json(output_path / "F3_NYC_D9_HERO_LEDGER.json", hero_ledger)
    write_json(output_path / "F3_NYC_D9_LIVE_SURFACE_REPORT.json", live_surface)
    write_json(output_path / "F3_NYC_D9_SUBJECT_ALIGNMENT_REPORT.json", alignment)
    write_json(output_path / "F3_NYC_D9_LIMITATION_REGISTER.json", limitations)

    write_json(output_path / "snapshot" / "flow3_current_status.json", accepted_state)
    write_json(output_path / "snapshot" / "flow3_hero_index.json", data["d8_hero_index"])
    write_json(output_path / "snapshot" / "flow3_source_limitations.json", limitations)
    write_json(output_path / "snapshot" / "flow3_live_endpoints.json", live_surface)

    for name, payload in reports.items():
        write_json(output_path / "reports" / f"{name}.json", payload)

    write_json(output_path / "snapshot" / "flow3_accepted_snapshot_manifest.json", artifact_manifest(output_path, snapshot_status))
    overclaim = no_overclaim_report(output_path)
    write_json(output_path / "F3_NYC_D9_NO_OVERCLAIM_REPORT.json", overclaim)

    after = input_snapshot(watched)
    no_mutation = {
        "gate": "F3-NYC-D9-NO-MUTATION",
        "status": "PASS" if before == after else "FAIL",
        "watched_paths": [str(path) for path in watched],
        "changed_inputs": [key for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)],
    }
    write_json(output_path / "F3_NYC_D9_NO_MUTATION_REPORT.json", no_mutation)

    gates = {
        precond["gate"]: precond["status"],
        stage_ledger["gate"]: stage_ledger["status"],
        source_status["gate"]: source_status["status"],
        hero_ledger["gate"]: hero_ledger["status"],
        alignment["gate"]: alignment["status"],
        live_surface["gate"]: live_surface["status"],
        limitations["gate"]: limitations["status"],
        overclaim["gate"]: overclaim["status"],
        no_mutation["gate"]: no_mutation["status"],
        "F3-NYC-D9-HASHES": "PENDING",
    }
    interim_status = snapshot_status if all(value in {"PASS", "PENDING"} for value in gates.values()) else "FAIL"
    harness = {
        "task": TASK_NAME,
        "created_utc": utc_now(),
        "status": interim_status,
        "gates": gates,
        "precond": precond,
        "source_status": source_status,
        "stage_ledger": stage_ledger,
        "hero_ledger": hero_ledger,
        "subject_alignment": alignment,
        "live_surface": live_surface,
        "limitations": limitations,
        "no_overclaim": overclaim,
        "no_mutation": no_mutation,
        "output": str(output_path),
    }
    write_json(output_path / "F3_NYC_D9_HARNESS_REPORT.json", harness)

    hash_report = write_hashes(output_path)
    gates["F3-NYC-D9-HASHES"] = hash_report["status"]
    final_status = snapshot_status if all(value == "PASS" for value in gates.values()) else "FAIL"
    harness["status"] = final_status
    harness["gates"] = gates
    harness["hashes"] = hash_report
    write_json(output_path / "F3_NYC_D9_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    write_json(output_path / "snapshot" / "flow3_accepted_snapshot_manifest.json", artifact_manifest(output_path, final_status))
    write_hashes(output_path)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Build F3-NYC-D9 Flow 3 accepted snapshot")
    parser.add_argument("--d2c-dir", default=DEFAULT_D2C_DIR)
    parser.add_argument("--d3-dir", default=DEFAULT_D3_DIR)
    parser.add_argument("--d4-dir", default=DEFAULT_D4_DIR)
    parser.add_argument("--d5-dir", default=DEFAULT_D5_DIR)
    parser.add_argument("--d6-dir", default=DEFAULT_D6_DIR)
    parser.add_argument("--d7-dir", default=DEFAULT_D7_DIR)
    parser.add_argument("--d8-dir", default=DEFAULT_D8_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_f3_nyc_d9_gate(
        d2c_dir=args.d2c_dir,
        d3_dir=args.d3_dir,
        d4_dir=args.d4_dir,
        d5_dir=args.d5_dir,
        d6_dir=args.d6_dir,
        d7_dir=args.d7_dir,
        d8_dir=args.d8_dir,
        output_dir=args.output_dir,
    )
    print(f"F3-NYC-D9 Flow 3 Accepted Snapshot: {report['status']}")
    print(f"D2C source status: {report['gates'].get('F3-NYC-D9-SOURCE-STATUS')}")
    print(f"D3 location confidence: {report['stage_ledger']['stages']['F3-NYC-D3']['gates'].get('F3-NYC-D3-LOCATION-CONFIDENCE-TIERS')}")
    print(f"D4 operator-review routing: {report['stage_ledger']['stages']['F3-NYC-D4']['gates'].get('F3-NYC-D4-OPERATOR-REVIEW-ROUTE-PLAN')}")
    print(f"D5 governed briefings: {report['stage_ledger']['stages']['F3-NYC-D5']['gates'].get('F3-NYC-D5-BRIEFING-GROUNDING')}")
    print(f"D6 live Spark/NIM replay: {report['stage_ledger']['stages']['F3-NYC-D6']['gates'].get('F3-NYC-D6-LIVE-OR-FALLBACK-REPLAY')}")
    print(f"D8 heroes: {report['gates'].get('F3-NYC-D9-HERO-LEDGER')}")
    print(f"Subject alignment: {report['gates'].get('F3-NYC-D9-SUBJECT-ALIGNMENT')}")
    print(f"Live surface: {report['gates'].get('F3-NYC-D9-LIVE-SURFACE')}")
    print(f"No-overclaim: {report['gates'].get('F3-NYC-D9-NO-OVERCLAIM')}")
    print(f"No-mutation: {report['gates'].get('F3-NYC-D9-NO-MUTATION')}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
