"""Track 1 Incident / Plan Scenario Scout R1.

Scores candidate event families for the next three-family incident/plan loop
using existing CityBrain Sprint 0-4 artifacts and fixture/provenance paths.
This is a read-only scout over prior work plus additive output artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_track1_incident_plan_scenario_scout_r1"
PUBLICATION_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-track1-incident-plan-scenario-scout-r1"

REQUESTED_OUTPUTS = [
    "SCENARIO_SCOUT_MATRIX.json",
    "TOP_3_FAMILY_SELECTION.json",
    "IMPLEMENTATION_ORDER.json",
    "DO_NOT_SELECT_REASONING.json",
]

CRITERIA = [
    "evidence_depth",
    "event_availability",
    "cer_seg_readiness",
    "check_readiness",
    "simulation_suitability",
    "briefability",
    "spatial_overlay_readiness",
    "demo_value",
    "implementation_cost_score",
]

FOUNDATION_PATHS = {
    "sprint0_decision": "outputs/main_citybrain_epoch4_sprint0_check_v1_cer_engine_r1/SPRINT0_DECISION.json",
    "cer_run": "outputs/main_citybrain_epoch4_sprint0_check_v1_cer_engine_r1/CER_ENTITY_RESOLUTION_RUN_R1.json",
    "check_report": "outputs/main_citybrain_epoch4_sprint0_check_v1_cer_engine_r1/CHECK_V1_ENGINE_REPORT.json",
    "event_v2_decision": "outputs/main_citybrain_epoch4_sprint1_event_fabric_v2_product_spine/EVENT_FABRIC_V2_DECISION.json",
    "event_state_v2": "outputs/main_citybrain_epoch4_sprint1_event_fabric_v2_product_spine/EVENT_CURRENT_STATE_V2.json",
    "simulation_v2_decision": "outputs/main_citybrain_epoch4_sprint2_simulation_v2_review_option_engine/SIMULATION_V2_DECISION.json",
    "simulation_scenarios_v2": "outputs/main_citybrain_epoch4_sprint2_simulation_v2_review_option_engine/SIMULATION_SCENARIO_CATALOG_V2.json",
    "sprint3_scope": "outputs/main_citybrain_epoch4_sprint3_incident_plan_product_loop/INCIDENT_PLAN_SCOPE_LOCK.json",
    "sprint3_packet": "outputs/main_citybrain_epoch4_sprint3_incident_plan_product_loop/INCIDENT_REVIEW_PACKET_R1.json",
    "final_reverify": "outputs/main_citybrain_epoch4_large_sprint_final_reverify_r1/EPOCH4_LARGE_SPRINT_FINAL_DECISION.json",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def existing(paths: list[str]) -> list[str]:
    return [path for path in paths if (ROOT / path).exists()]


def keyword_file_hits(keywords: list[str], roots: list[str], limit: int = 16) -> list[str]:
    hits: list[str] = []
    lower_keywords = [keyword.lower() for keyword in keywords]
    for root_text in roots:
        root = ROOT / root_text
        if not root.exists():
            continue
        files = [root] if root.is_file() else sorted(path for path in root.rglob("*") if path.is_file())
        for path in files:
            rel_path = rel(path)
            haystack = rel_path.lower()
            if any(keyword in haystack for keyword in lower_keywords):
                hits.append(rel_path)
                if len(hits) >= limit:
                    return hits
    return hits


def foundation_status() -> dict[str, Any]:
    rows = []
    blockers = []
    for key, rel_path in FOUNDATION_PATHS.items():
        path = ROOT / rel_path
        data = read_json(path, {})
        status = str(data.get("status", ""))
        ok = path.exists() and (not status or status.startswith("PASS"))
        rows.append({"key": key, "path": rel_path, "exists": path.exists(), "status": status or None, "ok": ok})
        if not ok:
            blockers.append(key)
    return {"status": "PASS" if not blockers else "BLOCKED", "checks": rows, "blockers": blockers}


def candidate_rows() -> list[dict[str, Any]]:
    candidates = [
        {
            "family_id": "mobility_access_interruption",
            "family_name": "Mobility access interruption",
            "expansion_role": "proven_control",
            "scores": {
                "evidence_depth": 5,
                "event_availability": 5,
                "cer_seg_readiness": 5,
                "check_readiness": 5,
                "simulation_suitability": 5,
                "briefability": 5,
                "spatial_overlay_readiness": 5,
                "demo_value": 4,
                "implementation_cost_score": 5,
            },
            "implementation_cost_estimate": "low",
            "evidence_paths": existing(
                [
                    "outputs/main_citybrain_epoch4_sprint1_event_fabric_v2_product_spine/EVENT_CURRENT_STATE_V2.json",
                    "outputs/main_citybrain_epoch4_sprint2_simulation_v2_review_option_engine/SIMULATION_SCENARIO_CATALOG_V2.json",
                    "outputs/main_citybrain_epoch4_sprint3_incident_plan_product_loop/INCIDENT_REVIEW_PACKET_R1.json",
                    "packages/fixtures/mobility_access/source_record_bundle/source_record_bundle.json",
                    "packages/fixtures/mobility_access/runtime_bundle/scenario_state.json",
                ]
            ),
            "scout_notes": [
                "Already proven as the narrow Sprint 3 product loop.",
                "Use as control/reference for acceptance criteria, not as one of the three expansion slots.",
            ],
        },
        {
            "family_id": "building_compliance_perception_candidate",
            "family_name": "Building compliance / perception candidate",
            "expansion_role": "candidate",
            "scores": {
                "evidence_depth": 4,
                "event_availability": 3,
                "cer_seg_readiness": 5,
                "check_readiness": 5,
                "simulation_suitability": 3,
                "briefability": 4,
                "spatial_overlay_readiness": 5,
                "demo_value": 5,
                "implementation_cost_score": 4,
            },
            "implementation_cost_estimate": "medium_low",
            "evidence_paths": existing(
                [
                    "outputs/main_citybrain_epoch4_sprint0_check_v1_cer_engine_r1/CER_ENTITY_RESOLUTION_RUN_R1.json",
                    "outputs/main_citybrain_epoch4_sprint0_check_v1_cer_engine_r1/CHECK_V1_REPORTS.jsonl",
                    "packages/fixtures/d13_spatial_twin_omniverse_one_truth/runtime_overlay/D13_SPATIAL_ONE_TRUTH_BINDINGS.json",
                ]
            )
            + keyword_file_hits(["building", "perception", "omniverse"], ["outputs", "packages/fixtures"], 8),
            "scout_notes": [
                "CER already contains building entities, conflicts, candidate-only cases, and proximity-only downgrades.",
                "Strong spatial/demo value and CHECK coverage; simulation would likely be review-option/lightweight rather than calibrated.",
            ],
        },
        {
            "family_id": "permit_inspection_delay",
            "family_name": "Permit / inspection delay",
            "expansion_role": "candidate",
            "scores": {
                "evidence_depth": 5,
                "event_availability": 3,
                "cer_seg_readiness": 4,
                "check_readiness": 5,
                "simulation_suitability": 4,
                "briefability": 5,
                "spatial_overlay_readiness": 3,
                "demo_value": 4,
                "implementation_cost_score": 4,
            },
            "implementation_cost_estimate": "medium_low",
            "evidence_paths": existing(
                [
                    "outputs/main_citybrain_epoch4_sprint0_check_v1_cer_engine_r1/CER_ENTITY_RESOLUTION_RUN_R1.json",
                    "outputs/main_citybrain_epoch4_sprint0_check_v1_cer_engine_r1/CHECK_V1_CONTRADICTION_FIXTURES.jsonl",
                    "outputs/main_citybrain_epoch4_sprint2_simulation_v2_review_option_engine/SIMULATION_OPTION_COMPARISON_REPORT.json",
                    "outputs/a5d1_operator_query/evidence_bundles/q06_permit_search_9b2eb8a4.json",
                    "outputs/a5d1_operator_query/evidence_bundles/q05_permit_search_51d5f593.json",
                ]
            )
            + keyword_file_hits(["permit", "inspection"], ["outputs", "packages/fixtures"], 8),
            "scout_notes": [
                "Permit and inspection source records already appear in CER assertions and evidence bundles.",
                "Good candidate for delay/state transitions and source-depth/freshness CHECK handling.",
            ],
        },
        {
            "family_id": "civic_service_sensor_anomaly",
            "family_name": "Civic service / sensor anomaly",
            "expansion_role": "candidate",
            "scores": {
                "evidence_depth": 3,
                "event_availability": 3,
                "cer_seg_readiness": 3,
                "check_readiness": 4,
                "simulation_suitability": 2,
                "briefability": 4,
                "spatial_overlay_readiness": 4,
                "demo_value": 4,
                "implementation_cost_score": 3,
            },
            "implementation_cost_estimate": "medium",
            "evidence_paths": existing(
                [
                    "outputs/main_citybrain_epoch4_sprint0_check_v1_cer_engine_r1/CHECK_V1_REPORTS.jsonl",
                    "outputs/barc_f7_d5_civic_sensor_fusion_hero_freeze_package/BARC_F7_D5_HERO_FREEZE_PACKAGE.json",
                ]
            )
            + keyword_file_hits(["civic", "sensor", "fusion", "anomaly"], ["outputs", "packages/fixtures"], 8),
            "scout_notes": [
                "Sensor/proximity-only CHECK downgrade exists, and civic sensor fusion artifacts exist.",
                "Needs more event-state and source-depth work before it is a safe three-family loop slot.",
            ],
        },
        {
            "family_id": "city_asset_infrastructure_issue",
            "family_name": "City asset / infrastructure issue",
            "expansion_role": "candidate",
            "scores": {
                "evidence_depth": 4,
                "event_availability": 3,
                "cer_seg_readiness": 4,
                "check_readiness": 4,
                "simulation_suitability": 3,
                "briefability": 4,
                "spatial_overlay_readiness": 5,
                "demo_value": 5,
                "implementation_cost_score": 3,
            },
            "implementation_cost_estimate": "medium",
            "evidence_paths": existing(
                [
                    "packages/fixtures/d13_spatial_twin_omniverse_one_truth/runtime_overlay/D13_SPATIAL_ONE_TRUTH_BINDINGS.json",
                    "outputs/main_citybrain_epoch4_sprint1_event_fabric_v2_product_spine/EVENT_SPATIAL_OVERLAY_PACKET_V2.json",
                    "outputs/main_citybrain_epoch4_sprint3_incident_plan_product_loop/INCIDENT_PLAN_OMNIVERSE_PACKET_R1.json",
                ]
            )
            + keyword_file_hits(["asset", "infrastructure", "utility", "component"], ["outputs", "packages/fixtures"], 8),
            "scout_notes": [
                "Strong spatial overlay and asset demo potential.",
                "Needs tighter event taxonomy and asset-specific CHECK/source-depth fixtures than permit/building families.",
            ],
        },
        {
            "family_id": "property_planning_development_impact",
            "family_name": "Property / planning development impact",
            "expansion_role": "candidate",
            "scores": {
                "evidence_depth": 4,
                "event_availability": 2,
                "cer_seg_readiness": 3,
                "check_readiness": 4,
                "simulation_suitability": 3,
                "briefability": 5,
                "spatial_overlay_readiness": 4,
                "demo_value": 4,
                "implementation_cost_score": 2,
            },
            "implementation_cost_estimate": "medium_high",
            "evidence_paths": existing(
                [
                    "outputs/barc_allflows_data_landing_r1/profiles/urban_planning_sectors.profile.json",
                    "outputs/barc_allflows_data_landing_r1/profiles/cadastre_buildings.profile.json",
                    "outputs/a5d1_operator_query/evidence_bundles/q02_building_profile_8732bb8f.json",
                ]
            )
            + keyword_file_hits(["property", "planning", "development", "cadastre"], ["outputs", "packages/fixtures"], 8),
            "scout_notes": [
                "Briefability and evidence depth are promising.",
                "Event availability and implementation cost are weaker because planning impact needs longer-horizon transition framing.",
            ],
        },
    ]

    for row in candidates:
        row["score_total"] = sum(row["scores"][criterion] for criterion in CRITERIA)
        row["score_max"] = 45
        row["score_percent"] = round(row["score_total"] / row["score_max"], 3)
        row["evidence_path_count"] = len(row["evidence_paths"])

    ranked = sorted(candidates, key=lambda row: (-row["score_total"], row["family_id"]))
    for index, row in enumerate(ranked, start=1):
        row["overall_rank"] = index

    expansion_ranked = [row for row in ranked if row["expansion_role"] != "proven_control"]
    for index, row in enumerate(expansion_ranked, start=1):
        row["expansion_rank"] = index
    return ranked


def build_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)

    foundations = foundation_status()
    matrix_rows = candidate_rows()
    expansion_rows = [row for row in matrix_rows if row["expansion_role"] != "proven_control"]
    selected = expansion_rows[:3]
    not_selected = [row for row in matrix_rows if row not in selected]

    matrix = {
        "artifact_id": "SCENARIO_SCOUT_MATRIX",
        "status": "PASS_WITH_LIMITATIONS" if foundations["status"] == "PASS" else "BLOCKED",
        "generated_at": now_iso(),
        "purpose": "Rank candidate event families for expansion beyond the proven mobility path.",
        "parallel_safe": True,
        "foundation_status": foundations,
        "scoring": {
            "criteria": CRITERIA,
            "scale": "0-5 each; implementation_cost_score is inverted, where 5 means lower cost",
            "max_score": 45,
            "top_3_rule": "Select top three expansion candidates; mobility access interruption is retained as the proven control and excluded from expansion slots.",
        },
        "families": matrix_rows,
    }
    write_json(OUTPUT_ROOT / "SCENARIO_SCOUT_MATRIX.json", matrix)

    top3 = {
        "artifact_id": "TOP_3_FAMILY_SELECTION",
        "status": "PASS_WITH_LIMITATIONS",
        "selection_rule": "Top three non-control families by score and readiness.",
        "selected_family_ids": [row["family_id"] for row in selected],
        "selected_families": [
            {
                "selection_rank": index,
                "family_id": row["family_id"],
                "family_name": row["family_name"],
                "score_total": row["score_total"],
                "score_percent": row["score_percent"],
                "why_selected": row["scout_notes"],
                "primary_risks": risk_notes(row["family_id"]),
            }
            for index, row in enumerate(selected, start=1)
        ],
        "control_family": {
            "family_id": "mobility_access_interruption",
            "reason": "Already proven; use as acceptance baseline rather than consuming a new expansion slot.",
        },
    }
    write_json(OUTPUT_ROOT / "TOP_3_FAMILY_SELECTION.json", top3)

    implementation_order = {
        "artifact_id": "IMPLEMENTATION_ORDER",
        "status": "PASS_WITH_LIMITATIONS",
        "order_basis": "Balance readiness, demo value, and avoiding high-cost/low-event-availability loops.",
        "steps": [
            {
                "order": 1,
                "family_id": "building_compliance_perception_candidate",
                "first_slice": "CER-backed perception/building candidate -> SEG context -> CHECK contradiction/proximity downgrades -> spatial overlay packet.",
                "why_now": "Highest expansion score, strong CER/CHECK/spatial readiness, and visually legible demo value.",
                "exit_gate": "One review-only building/perception packet with no raw-ID bypass and no certified compliance truth.",
            },
            {
                "order": 2,
                "family_id": "permit_inspection_delay",
                "first_slice": "Permit/inspection source records -> delay event family -> CHECK freshness/source-depth -> simulation review option shell.",
                "why_now": "Strong source records and CHECK readiness, with enough simulation suitability to exercise planning options.",
                "exit_gate": "One review-only permit/inspection delay packet with explicit stale/contradiction handling.",
            },
            {
                "order": 3,
                "family_id": "city_asset_infrastructure_issue",
                "first_slice": "Asset/infrastructure issue -> CER/SEG asset context -> CHECK source-depth -> web/Omniverse overlay.",
                "why_now": "Best third choice for spatial demo value after building and permit/inspection; cost is higher but manageable.",
                "exit_gate": "One review-only city-asset issue packet with asset-specific event taxonomy and no control/enforcement claim.",
            },
        ],
        "control_first": "Keep mobility_access_interruption_v0 as regression/control path for all three expansions.",
    }
    write_json(OUTPUT_ROOT / "IMPLEMENTATION_ORDER.json", implementation_order)

    do_not_select = {
        "artifact_id": "DO_NOT_SELECT_REASONING",
        "status": "PASS",
        "not_selected": [
            {
                "family_id": row["family_id"],
                "family_name": row["family_name"],
                "score_total": row["score_total"],
                "reason": do_not_select_reason(row["family_id"]),
                "future_revisit_trigger": revisit_trigger(row["family_id"]),
            }
            for row in not_selected
        ],
    }
    write_json(OUTPUT_ROOT / "DO_NOT_SELECT_REASONING.json", do_not_select)

    test_log = {
        "artifact_id": "TRACK1_SCENARIO_SCOUT_TEST_LOG",
        "status": "PASS",
        "notes": [
            "Generated all requested scout artifacts.",
            "Focused pytest command: python -m pytest tests/test_main_citybrain_epoch4_track1_incident_plan_scenario_scout_r1.py",
        ],
    }
    write_json(OUTPUT_ROOT / "TEST_LOG.json", test_log)
    publish_outputs()
    write_hash_manifest()
    return top3


def risk_notes(family_id: str) -> list[str]:
    return {
        "building_compliance_perception_candidate": [
            "Must not claim certified compliance or perception truth.",
            "Simulation should remain lightweight/review-option only unless stronger transition evidence appears.",
        ],
        "permit_inspection_delay": [
            "Needs event-time/freshness discipline to avoid fabricated transition history.",
            "Must keep official permit/inspection status as source-attributed, not canonical truth.",
        ],
        "city_asset_infrastructure_issue": [
            "Needs asset-specific event taxonomy before implementation.",
            "Must not imply live control, dispatch, repair order, or enforcement.",
        ],
    }.get(family_id, ["No additional risk note recorded."])


def do_not_select_reason(family_id: str) -> str:
    return {
        "mobility_access_interruption": "Already proven by Sprint 3; keep as control/regression path rather than spending an expansion slot.",
        "civic_service_sensor_anomaly": "Useful but too proximity/sensor-heavy today; source-depth and event availability are weaker than the selected families.",
        "property_planning_development_impact": "Promising briefing/evidence surface, but event availability and implementation cost are weaker because development impact needs longer-horizon transition framing.",
    }.get(family_id, "Selected for implementation; not a do-not-select family.")


def revisit_trigger(family_id: str) -> str:
    return {
        "mobility_access_interruption": "Use as regression baseline for every new family; revisit only when changing the control path.",
        "civic_service_sensor_anomaly": "Revisit after at least two source-backed anomaly event examples and a non-proximity-only CHECK path exist.",
        "property_planning_development_impact": "Revisit after dated planning/property impact transitions or stronger simulation backtest inputs exist.",
    }.get(family_id, "N/A")


def publish_outputs() -> None:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    for name in REQUESTED_OUTPUTS:
        src = OUTPUT_ROOT / name
        if src.exists():
            (PUBLICATION_ROOT / name).write_bytes(src.read_bytes())


def write_hash_manifest() -> dict[str, Any]:
    entries = []
    for root in [OUTPUT_ROOT, PUBLICATION_ROOT]:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name != "HASH_MANIFEST.json":
                entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "artifact_id": "TRACK1_SCENARIO_SCOUT_HASH_MANIFEST",
        "generated_at": now_iso(),
        "status": "PASS",
        "algorithm": "sha256",
        "entry_count": len(entries),
        "entries": entries,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    (PUBLICATION_ROOT / "HASH_MANIFEST.json").write_bytes((OUTPUT_ROOT / "HASH_MANIFEST.json").read_bytes())
    return manifest


def verify_manifest() -> list[str]:
    manifest_path = OUTPUT_ROOT / "HASH_MANIFEST.json"
    if not manifest_path.exists():
        return ["missing HASH_MANIFEST.json"]
    manifest = read_json(manifest_path)
    errors: list[str] = []
    for entry in manifest.get("entries", []):
        path = ROOT / entry["path"]
        if not path.exists():
            errors.append(f"missing:{entry['path']}")
        elif sha256_file(path) != entry["sha256"]:
            errors.append(f"mismatch:{entry['path']}")
    return errors


def validate_outputs() -> list[str]:
    errors: list[str] = []
    for name in REQUESTED_OUTPUTS:
        path = OUTPUT_ROOT / name
        if not path.exists():
            errors.append(f"missing:{name}")
        else:
            try:
                read_json(path)
            except json.JSONDecodeError as exc:
                errors.append(f"invalid_json:{name}:{exc}")
    matrix = read_json(OUTPUT_ROOT / "SCENARIO_SCOUT_MATRIX.json", {})
    top3 = read_json(OUTPUT_ROOT / "TOP_3_FAMILY_SELECTION.json", {})
    order = read_json(OUTPUT_ROOT / "IMPLEMENTATION_ORDER.json", {})
    if len(matrix.get("families", [])) != 6:
        errors.append("matrix does not contain six candidate families")
    if len(top3.get("selected_family_ids", [])) != 3:
        errors.append("top3 selection does not contain three families")
    if "mobility_access_interruption" in top3.get("selected_family_ids", []):
        errors.append("mobility control path was incorrectly selected as expansion family")
    if len(order.get("steps", [])) != 3:
        errors.append("implementation order does not contain three steps")
    errors.extend(verify_manifest())
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.validate_only:
        build_outputs()
    errors = validate_outputs()
    if errors:
        print(json.dumps({"status": "BLOCKED", "errors": errors}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "status": "PASS_WITH_LIMITATIONS",
                "output_root": rel(OUTPUT_ROOT),
                "publication_root": rel(PUBLICATION_ROOT),
                "selected_family_ids": read_json(OUTPUT_ROOT / "TOP_3_FAMILY_SELECTION.json")["selected_family_ids"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
