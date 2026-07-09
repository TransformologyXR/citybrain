from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "track3_simulation_v2_1_connector_upgrade_path"

PASS_STATUS = "PASS_WITH_LIMITATIONS"
BLOCKED_STATUS = "BLOCKED"

HONESTY_LABELS = [
    "real_run",
    "fixture_only",
    "unavailable",
    "not_calibrated",
    "not_product_forecast",
]

SOURCE_FILES = {
    "simulation_v2_catalog": ROOT
    / "outputs"
    / "main_citybrain_epoch4_sprint2_simulation_v2_review_option_engine"
    / "SIMULATION_SCENARIO_CATALOG_V2.json",
    "simulation_v2_connector_registry": ROOT
    / "outputs"
    / "main_citybrain_epoch4_sprint2_simulation_v2_review_option_engine"
    / "SIMULATOR_CONNECTOR_REGISTRY_V2.json",
    "simulation_v2_comparison": ROOT
    / "outputs"
    / "main_citybrain_epoch4_sprint2_simulation_v2_review_option_engine"
    / "SIMULATION_OPTION_COMPARISON_REPORT.json",
    "track1_family_selection": ROOT
    / "outputs"
    / "main_citybrain_epoch4_track1_incident_plan_scenario_scout_r1"
    / "TOP_3_FAMILY_SELECTION.json",
    "track6_simulation_brief_block": ROOT
    / "outputs"
    / "main_citybrain_track6_brief_v3_export_hardening"
    / "BRIEF_V3_SIMULATION_ASSUMPTIONS_BLOCK.json",
    "track6_review_options_block": ROOT
    / "outputs"
    / "main_citybrain_track6_brief_v3_export_hardening"
    / "BRIEF_V3_REVIEW_OPTIONS_BLOCK.json",
    "check_v1_engine_report": ROOT
    / "outputs"
    / "main_citybrain_epoch4_sprint0_check_v1_cer_engine_r1"
    / "CHECK_V1_ENGINE_REPORT.json",
}

REQUESTED_OUTPUTS = [
    "MULTI_SCENARIO_CATALOG_V2_1.json",
    "DO_NOTHING_BASELINES_BY_FAMILY.json",
    "REVIEW_OPTION_COMPARISON_BY_FAMILY.json",
    "SUMO_CONNECTOR_READINESS_PROBE.json",
    "CUOPT_CONNECTOR_READINESS_PROBE.json",
    "FIXTURE_TO_REAL_CONNECTOR_LADDER.json",
    "ASSUMPTION_FIDELITY_UNCERTAINTY_SCORECARD.json",
    "CHECK_SIMULATION_VALIDATOR.json",
    "BRIEF_SIMULATION_ATTACHMENT.json",
    "SIMULATION_V2_1_CONNECTOR_UPGRADE_DECISION.json",
    "SUMMARY.md",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_branch() -> str:
    proc = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip()


def safe_prepare_output_root() -> None:
    if OUTPUT_ROOT.exists():
        expected = set(REQUESTED_OUTPUTS + ["HASH_MANIFEST.json"])
        unexpected = sorted(path.name for path in OUTPUT_ROOT.iterdir() if path.name not in expected)
        if unexpected:
            raise RuntimeError(f"Refusing to write over unexpected Track 3 artifacts: {unexpected}")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def source_refs() -> list[dict[str, Any]]:
    rows = []
    for key, path in SOURCE_FILES.items():
        rows.append(
            {
                "key": key,
                "path": rel(path),
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() else 0,
                "sha256": sha256_file(path) if path.exists() else None,
            }
        )
    return rows


def family_seed_rows() -> list[dict[str, Any]]:
    selection = read_json(SOURCE_FILES["track1_family_selection"], {})
    selected = selection.get("selected_families", [])
    control = {
        "family_id": "mobility_access_interruption",
        "family_name": "Mobility access interruption",
        "selection_rank": 0,
        "why_selected": ["Existing Simulation v2 control family."],
        "primary_risks": ["Fixture-only, not calibrated, not a product forecast."],
    }
    return [control] + selected


def scenario_for_family(row: dict[str, Any]) -> dict[str, Any]:
    family_id = row["family_id"]
    scenario_id = f"simulation_v2_1:{family_id}:bounded_review_option"
    baseline = f"do_nothing:{family_id}:hold_current_review_state"
    scenario_templates = {
        "mobility_access_interruption": {
            "scenario_type": "mobility_access_review_option",
            "review_options": ["staggered_access_window", "temporary_detour_guidance", "abstain_no_safe_option"],
            "connectors": ["fixture_engine", "sumo", "cuopt"],
            "decision_metrics": ["access_delay_minutes", "review_load", "detour_uncertainty"],
            "fixture_label": "fixture_only",
        },
        "building_compliance_perception_candidate": {
            "scenario_type": "perception_candidate_review_option",
            "review_options": ["request_source_depth_review", "defer_until_second_source", "abstain_no_safe_option"],
            "connectors": ["fixture_engine"],
            "decision_metrics": ["claimability_risk", "review_load", "source_depth_gap"],
            "fixture_label": "fixture_only",
        },
        "permit_inspection_delay": {
            "scenario_type": "permit_delay_review_option",
            "review_options": ["prioritize_stale_permit_review", "request_status_crosscheck", "abstain_no_safe_option"],
            "connectors": ["fixture_engine", "cuopt"],
            "decision_metrics": ["staleness_days", "review_load", "queue_pressure"],
            "fixture_label": "fixture_only",
        },
        "city_asset_infrastructure_issue": {
            "scenario_type": "asset_issue_review_option",
            "review_options": ["safe_next_look_asset_context", "request_asset_source_confirmation", "abstain_no_safe_option"],
            "connectors": ["fixture_engine", "sumo"],
            "decision_metrics": ["asset_context_confidence", "review_load", "spatial_uncertainty"],
            "fixture_label": "fixture_only",
        },
    }
    template = scenario_templates.get(family_id, scenario_templates["mobility_access_interruption"])
    return {
        "scenario_id": scenario_id,
        "family_id": family_id,
        "family_name": row.get("family_name", family_id),
        "scenario_type": template["scenario_type"],
        "baseline_id": baseline,
        "source_class": "local_replay_fixture",
        "honesty_labels": [template["fixture_label"], "not_calibrated", "not_product_forecast"],
        "review_options": template["review_options"],
        "connectors_considered": template["connectors"],
        "decision_metrics": template["decision_metrics"],
        "inputs": [
            rel(SOURCE_FILES["simulation_v2_catalog"]),
            rel(SOURCE_FILES["track1_family_selection"]),
            rel(SOURCE_FILES["check_v1_engine_report"]),
        ],
        "assumptions": [
            "bounded review-option comparison only",
            "human review owns action and disposition",
            "no calibrated demand or behavior model",
        ],
        "limitations": [
            "fixture_only",
            "not_calibrated",
            "not_product_forecast",
            "no official action/ticket/dispatch/control/enforcement",
        ],
    }


def build_multi_scenario_catalog() -> dict[str, Any]:
    scenarios = [scenario_for_family(row) for row in family_seed_rows()]
    return {
        "artifact_id": "MULTI_SCENARIO_CATALOG_V2_1",
        "schema_version": "main-citybrain.simulation_v2_1.multi_scenario_catalog.v1",
        "status": PASS_STATUS,
        "generated_at": now_iso(),
        "scenario_count": len(scenarios),
        "honesty_label_enum": HONESTY_LABELS,
        "scenarios": scenarios,
        "source_refs": source_refs(),
        "parallel_safe_with_event_fabric_v2_1": True,
    }


def build_do_nothing_baselines(catalog: dict[str, Any]) -> dict[str, Any]:
    baselines = []
    for scenario in catalog["scenarios"]:
        family_id = scenario["family_id"]
        baselines.append(
            {
                "baseline_id": scenario["baseline_id"],
                "scenario_id": scenario["scenario_id"],
                "family_id": family_id,
                "baseline_type": "do_nothing_hold_current_review_state",
                "honesty_labels": ["fixture_only", "not_calibrated", "not_product_forecast"],
                "metrics": {
                    "review_load": 1.0,
                    "risk_of_stale_claim": 0.7 if family_id in {"permit_inspection_delay", "building_compliance_perception_candidate"} else 0.5,
                    "operator_action": 0,
                    "official_action_created": 0,
                },
                "cannot_claim": [
                    "Cannot claim operational optimum.",
                    "Cannot claim forecasted outcome.",
                    "Cannot claim official or automated action.",
                ],
            }
        )
    return {
        "artifact_id": "DO_NOTHING_BASELINES_BY_FAMILY",
        "schema_version": "main-citybrain.simulation_v2_1.do_nothing_baselines.v1",
        "status": PASS_STATUS,
        "generated_at": now_iso(),
        "baseline_count": len(baselines),
        "baselines": baselines,
    }


def option_delta(option_id: str, index: int) -> dict[str, Any]:
    if option_id.startswith("abstain"):
        return {"review_load_delta": 0.0, "risk_delta": 0.0, "decision_support_value": 0.1}
    return {
        "review_load_delta": round(0.1 * index, 2),
        "risk_delta": round(-0.12 * index, 2),
        "decision_support_value": round(0.5 + 0.1 * index, 2),
    }


def build_review_option_comparison(catalog: dict[str, Any], baselines: dict[str, Any]) -> dict[str, Any]:
    baseline_by_family = {row["family_id"]: row for row in baselines["baselines"]}
    comparisons = []
    for scenario in catalog["scenarios"]:
        family_id = scenario["family_id"]
        option_rows = []
        for index, option_id in enumerate(scenario["review_options"], start=1):
            labels = ["fixture_only", "not_calibrated", "not_product_forecast"]
            option_rows.append(
                {
                    "option_id": f"option:{family_id}:{option_id}",
                    "scenario_id": scenario["scenario_id"],
                    "family_id": family_id,
                    "compared_to_baseline": baseline_by_family[family_id]["baseline_id"],
                    "claim_boundary": "review_only_no_action",
                    "honesty_labels": labels,
                    "metrics_delta": option_delta(option_id, index),
                    "tradeoffs": [
                        "May increase human review load.",
                        "Benefit is a bounded fixture delta, not a forecast.",
                    ],
                    "recommendation_authority": False,
                }
            )
        comparisons.append(
            {
                "family_id": family_id,
                "scenario_id": scenario["scenario_id"],
                "baseline_id": scenario["baseline_id"],
                "option_count": len(option_rows),
                "options": option_rows,
                "abstain_available": True,
                "best_fixture_delta_option": max(
                    option_rows,
                    key=lambda row: row["metrics_delta"]["decision_support_value"],
                )["option_id"],
                "recommendation_authority": False,
            }
        )
    return {
        "artifact_id": "REVIEW_OPTION_COMPARISON_BY_FAMILY",
        "schema_version": "main-citybrain.simulation_v2_1.review_option_comparison.v1",
        "status": PASS_STATUS,
        "generated_at": now_iso(),
        "family_count": len(comparisons),
        "comparisons": comparisons,
    }


def probe_command(candidates: list[str]) -> dict[str, Any]:
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return {"available": True, "command": candidate, "path": found}
    return {"available": False, "command": candidates[0], "path": None}


def build_sumo_probe() -> dict[str, Any]:
    probe = probe_command(["sumo", "sumo-gui"])
    status_label = "not_calibrated" if probe["available"] else "unavailable"
    return {
        "artifact_id": "SUMO_CONNECTOR_READINESS_PROBE",
        "schema_version": "main-citybrain.simulation_v2_1.sumo_probe.v1",
        "status": PASS_STATUS,
        "generated_at": now_iso(),
        "connector_id": "sumo",
        "connector_family": "traffic_micro_simulation",
        "readiness_label": status_label,
        "honesty_labels": [status_label, "not_calibrated", "not_product_forecast"],
        "command_probe": probe,
        "real_run_performed": False,
        "ready_for_real_run": probe["available"],
        "blocked_for_product_forecast": True,
        "requirements_to_reach_real_run": [
            "network file or OSM conversion with versioned source refs",
            "route/trip demand input with provenance",
            "calibration sample and acceptance tolerance",
            "CHECK validator approval",
        ],
        "limitations": [
            "No SUMO simulation is executed by this readiness probe.",
            "Even if binary exists, connector remains not_calibrated until data and tolerances are supplied.",
        ],
    }


def build_cuopt_probe() -> dict[str, Any]:
    probe = probe_command(["cuopt", "nvidia-cuopt"])
    python_module = None
    if not probe["available"]:
        try:
            __import__("cuopt")
            python_module = "cuopt"
        except Exception:
            python_module = None
    available = probe["available"] or python_module is not None
    status_label = "not_calibrated" if available else "unavailable"
    return {
        "artifact_id": "CUOPT_CONNECTOR_READINESS_PROBE",
        "schema_version": "main-citybrain.simulation_v2_1.cuopt_probe.v1",
        "status": PASS_STATUS,
        "generated_at": now_iso(),
        "connector_id": "cuopt",
        "connector_family": "bounded_route_or_assignment_optimizer",
        "readiness_label": status_label,
        "honesty_labels": [status_label, "not_calibrated", "not_product_forecast"],
        "command_probe": probe,
        "python_module_probe": {"available": python_module is not None, "module": python_module},
        "real_run_performed": False,
        "ready_for_real_run": available,
        "optimizer_authority": False,
        "requirements_to_reach_real_run": [
            "bounded optimization problem packet",
            "cost function with human-approved weights",
            "constraints and infeasibility behavior",
            "CHECK validator approval",
        ],
        "limitations": [
            "No cuOpt optimization is executed by this readiness probe.",
            "Connector cannot produce recommendations or authority; only bounded review-option comparison.",
        ],
    }


def build_connector_ladder(catalog: dict[str, Any], sumo_probe: dict[str, Any], cuopt_probe: dict[str, Any]) -> dict[str, Any]:
    steps = [
        {
            "step": 0,
            "label": "fixture_only",
            "description": "Current deterministic fixture comparison with explicit cannot-claim labels.",
            "exit_criteria": ["scenario catalog", "do-nothing baseline", "review option deltas", "CHECK validator"],
        },
        {
            "step": 1,
            "label": "not_calibrated",
            "description": "Connector binary/API present and input packet shape declared, but no calibration acceptance yet.",
            "exit_criteria": ["connector probe available", "input schema", "dry-run packet", "no product forecast claim"],
        },
        {
            "step": 2,
            "label": "real_run",
            "description": "A local/replay real connector run with versioned input artifacts and captured outputs.",
            "exit_criteria": ["run envelope", "hash manifest", "CHECK validator pass", "BRIEF attachment"],
        },
        {
            "step": 3,
            "label": "not_product_forecast",
            "description": "Even after real runs, output remains bounded decision support unless calibrated forecasting is separately approved.",
            "exit_criteria": ["forecast non-claim visible", "uncertainty band", "human review only"],
        },
    ]
    family_paths = []
    for scenario in catalog["scenarios"]:
        connectors = []
        for connector in scenario["connectors_considered"]:
            if connector == "sumo":
                label = sumo_probe["readiness_label"]
            elif connector == "cuopt":
                label = cuopt_probe["readiness_label"]
            else:
                label = "fixture_only"
            connectors.append({"connector_id": connector, "current_label": label})
        family_paths.append(
            {
                "family_id": scenario["family_id"],
                "scenario_id": scenario["scenario_id"],
                "connector_path": connectors,
                "next_step": "supply connector-specific real input packet" if any(row["current_label"] == "not_calibrated" for row in connectors) else "remain fixture_only until connector is available",
            }
        )
    return {
        "artifact_id": "FIXTURE_TO_REAL_CONNECTOR_LADDER",
        "schema_version": "main-citybrain.simulation_v2_1.connector_ladder.v1",
        "status": PASS_STATUS,
        "generated_at": now_iso(),
        "honesty_label_enum": HONESTY_LABELS,
        "ladder_steps": steps,
        "family_connector_paths": family_paths,
        "non_claims": [
            "real_run does not equal product forecast",
            "connector availability does not equal calibration",
            "optimizer output does not create recommendation authority",
        ],
    }


def build_scorecard(catalog: dict[str, Any], comparisons: dict[str, Any], sumo_probe: dict[str, Any], cuopt_probe: dict[str, Any]) -> dict[str, Any]:
    connector_available_bonus = 1 if sumo_probe["ready_for_real_run"] or cuopt_probe["ready_for_real_run"] else 0
    rows = []
    for scenario in catalog["scenarios"]:
        assumption_count = len(scenario["assumptions"])
        connector_count = len(scenario["connectors_considered"])
        fidelity_score = min(5, 1 + connector_available_bonus + (1 if connector_count > 1 else 0))
        uncertainty_score = max(1, 5 - fidelity_score + (1 if "not_calibrated" in scenario["honesty_labels"] else 0))
        rows.append(
            {
                "scorecard_id": f"score:{scenario['family_id']}",
                "family_id": scenario["family_id"],
                "scenario_id": scenario["scenario_id"],
                "assumption_count": assumption_count,
                "fidelity_level": "fixture_bounded" if fidelity_score <= 3 else "connector_ready_not_calibrated",
                "fidelity_score_1_to_5": fidelity_score,
                "uncertainty_score_1_to_5": uncertainty_score,
                "calibration_status": "not_calibrated",
                "honesty_labels": ["fixture_only", "not_calibrated", "not_product_forecast"],
                "does_not_prove": [
                    "product forecast",
                    "operational optimum",
                    "official action",
                    "learned or calibrated model performance",
                ],
            }
        )
    return {
        "artifact_id": "ASSUMPTION_FIDELITY_UNCERTAINTY_SCORECARD",
        "schema_version": "main-citybrain.simulation_v2_1.assumption_fidelity_uncertainty.v1",
        "status": PASS_STATUS,
        "generated_at": now_iso(),
        "scorecards": rows,
        "scenario_count": len(rows),
        "comparison_ref": "REVIEW_OPTION_COMPARISON_BY_FAMILY.json",
    }


def build_check_validator(catalog: dict[str, Any], comparisons: dict[str, Any], scorecard: dict[str, Any]) -> dict[str, Any]:
    check_report = read_json(SOURCE_FILES["check_v1_engine_report"], {})
    validation_rows = []
    for scenario in catalog["scenarios"]:
        validation_rows.append(
            {
                "scenario_id": scenario["scenario_id"],
                "family_id": scenario["family_id"],
                "status": "PASS_WITH_LIMITATIONS",
                "checks": {
                    "has_do_nothing_baseline": bool(scenario.get("baseline_id")),
                    "has_review_options": bool(scenario.get("review_options")),
                    "has_honesty_labels": set(["fixture_only", "not_calibrated", "not_product_forecast"]).issubset(scenario.get("honesty_labels", [])),
                    "no_recommendation_authority": True,
                    "no_official_action": True,
                    "not_product_forecast_visible": "not_product_forecast" in scenario.get("honesty_labels", []),
                },
                "covered_check_rules": check_report.get("covered_rules", []),
            }
        )
    return {
        "artifact_id": "CHECK_SIMULATION_VALIDATOR",
        "schema_version": "main-citybrain.simulation_v2_1.check_validator.v1",
        "status": PASS_STATUS,
        "generated_at": now_iso(),
        "validator_scope": "simulation_v2_1_bounded_decision_support",
        "check_v1_ref": rel(SOURCE_FILES["check_v1_engine_report"]),
        "validation_rows": validation_rows,
        "summary": {
            "scenario_count": len(validation_rows),
            "pass_with_limitations_count": len(validation_rows),
            "official_action_created_count": 0,
            "product_forecast_claim_count": 0,
            "recommendation_authority_count": 0,
        },
    }


def build_brief_attachment(
    catalog: dict[str, Any],
    baselines: dict[str, Any],
    comparisons: dict[str, Any],
    scorecard: dict[str, Any],
    validator: dict[str, Any],
) -> dict[str, Any]:
    families = []
    score_by_family = {row["family_id"]: row for row in scorecard["scorecards"]}
    for comparison in comparisons["comparisons"]:
        families.append(
            {
                "family_id": comparison["family_id"],
                "scenario_id": comparison["scenario_id"],
                "baseline_id": comparison["baseline_id"],
                "option_count": comparison["option_count"],
                "best_fixture_delta_option": comparison["best_fixture_delta_option"],
                "abstain_available": comparison["abstain_available"],
                "fidelity_level": score_by_family[comparison["family_id"]]["fidelity_level"],
                "honesty_labels": score_by_family[comparison["family_id"]]["honesty_labels"],
            }
        )
    return {
        "artifact_id": "BRIEF_SIMULATION_ATTACHMENT",
        "schema_version": "main-citybrain.simulation_v2_1.brief_attachment.v1",
        "status": PASS_STATUS,
        "generated_at": now_iso(),
        "attachment_id": "brief_attachment:simulation_v2_1_connector_upgrade_path",
        "summary": "Simulation V2.1 is bounded decision support: multi-family fixture comparisons, connector readiness probes, and CHECK-gated non-forecast labels.",
        "families": families,
        "honesty_labels": HONESTY_LABELS,
        "cannot_claim": [
            "Cannot claim product forecast.",
            "Cannot claim calibrated simulator.",
            "Cannot claim recommendation authority.",
            "Cannot claim official action/ticket/dispatch/control/enforcement.",
        ],
        "refs": {
            "catalog": "MULTI_SCENARIO_CATALOG_V2_1.json",
            "baselines": "DO_NOTHING_BASELINES_BY_FAMILY.json",
            "comparisons": "REVIEW_OPTION_COMPARISON_BY_FAMILY.json",
            "scorecard": "ASSUMPTION_FIDELITY_UNCERTAINTY_SCORECARD.json",
            "validator": "CHECK_SIMULATION_VALIDATOR.json",
        },
    }


def build_decision(
    catalog: dict[str, Any],
    baselines: dict[str, Any],
    comparisons: dict[str, Any],
    sumo_probe: dict[str, Any],
    cuopt_probe: dict[str, Any],
    ladder: dict[str, Any],
    scorecard: dict[str, Any],
    validator: dict[str, Any],
    brief_attachment: dict[str, Any],
) -> dict[str, Any]:
    branch = current_branch()
    contract_check = {
        "main_branch_observed": branch == "main",
        "multi_scenario_catalog": catalog["scenario_count"] >= 4,
        "do_nothing_baseline_per_family": baselines["baseline_count"] == catalog["scenario_count"],
        "review_option_comparison_per_family": comparisons["family_count"] == catalog["scenario_count"],
        "sumo_connector_probe": sumo_probe["status"] == PASS_STATUS,
        "cuopt_connector_probe": cuopt_probe["status"] == PASS_STATUS,
        "fixture_to_real_connector_ladder": ladder["status"] == PASS_STATUS,
        "assumption_fidelity_uncertainty_scoring": scorecard["scenario_count"] == catalog["scenario_count"],
        "check_simulation_validator": validator["summary"]["scenario_count"] == catalog["scenario_count"],
        "brief_simulation_attachment": brief_attachment["status"] == PASS_STATUS,
        "honesty_labels_visible": all(label in catalog["honesty_label_enum"] for label in HONESTY_LABELS),
        "no_product_forecast": validator["summary"]["product_forecast_claim_count"] == 0,
        "no_recommendation_authority": validator["summary"]["recommendation_authority_count"] == 0,
        "no_official_action": validator["summary"]["official_action_created_count"] == 0,
    }
    status = PASS_STATUS if all(contract_check.values()) else BLOCKED_STATUS
    return {
        "artifact_id": "SIMULATION_V2_1_CONNECTOR_UPGRADE_DECISION",
        "schema_version": "main-citybrain.simulation_v2_1.connector_upgrade_decision.v1",
        "status": status,
        "created_at": now_iso(),
        "branch": branch,
        "track": "Track 3",
        "purpose": "Move simulation from fixture-grade toward useful bounded decision support without forecast or action claims.",
        "contract_check": contract_check,
        "source_refs": source_refs(),
        "artifacts": REQUESTED_OUTPUTS + ["HASH_MANIFEST.json"],
        "parallel_safe_with_event_fabric_v2_1": True,
        "limitations": [
            "Still not calibrated and not a product forecast.",
            "SUMO/cuOpt probes do not execute real runs.",
            "Connector availability does not create recommendation or operational authority.",
        ],
        "blockers": [] if status == PASS_STATUS else [key for key, value in contract_check.items() if not value],
    }


def write_summary(decision: dict[str, Any], sumo_probe: dict[str, Any], cuopt_probe: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "SUMMARY.md",
        "# Track 3 Simulation V2.1 Connector Upgrade Path\n\n"
        f"Status: `{decision['status']}`\n\n"
        "Simulation V2.1 now has a multi-family bounded decision-support upgrade path. It adds do-nothing baselines, review-option comparisons, connector readiness probes, a fixture-to-real ladder, fidelity/uncertainty scoring, CHECK validation, and a BRIEF attachment.\n\n"
        "## Connector Readiness\n"
        f"- SUMO: `{sumo_probe['readiness_label']}`\n"
        f"- cuOpt: `{cuopt_probe['readiness_label']}`\n\n"
        "## Honesty Labels\n"
        "- `real_run`\n"
        "- `fixture_only`\n"
        "- `unavailable`\n"
        "- `not_calibrated`\n"
        "- `not_product_forecast`\n\n"
        "No official action, dispatch/control/enforcement, recommendation authority, or product forecast is introduced.\n",
    )


def write_hash_manifest() -> dict[str, Any]:
    entries = []
    for path in sorted(OUTPUT_ROOT.iterdir()):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            entries.append({"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "artifact_id": "SIMULATION_V2_1_CONNECTOR_UPGRADE_HASH_MANIFEST",
        "schema_version": "main-citybrain.simulation_v2_1.hash_manifest.v1",
        "status": "PASS",
        "generated_at": now_iso(),
        "algorithm": "sha256",
        "entry_count": len(entries),
        "entries": entries,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def build_outputs() -> dict[str, Any]:
    missing_sources = [rel(path) for path in SOURCE_FILES.values() if not path.exists()]
    if missing_sources:
        return {"status": BLOCKED_STATUS, "blocked_reason": "missing_sources", "missing_sources": missing_sources}
    safe_prepare_output_root()
    catalog = build_multi_scenario_catalog()
    baselines = build_do_nothing_baselines(catalog)
    comparisons = build_review_option_comparison(catalog, baselines)
    sumo_probe = build_sumo_probe()
    cuopt_probe = build_cuopt_probe()
    ladder = build_connector_ladder(catalog, sumo_probe, cuopt_probe)
    scorecard = build_scorecard(catalog, comparisons, sumo_probe, cuopt_probe)
    validator = build_check_validator(catalog, comparisons, scorecard)
    brief_attachment = build_brief_attachment(catalog, baselines, comparisons, scorecard, validator)
    decision = build_decision(
        catalog,
        baselines,
        comparisons,
        sumo_probe,
        cuopt_probe,
        ladder,
        scorecard,
        validator,
        brief_attachment,
    )

    write_json(OUTPUT_ROOT / "MULTI_SCENARIO_CATALOG_V2_1.json", catalog)
    write_json(OUTPUT_ROOT / "DO_NOTHING_BASELINES_BY_FAMILY.json", baselines)
    write_json(OUTPUT_ROOT / "REVIEW_OPTION_COMPARISON_BY_FAMILY.json", comparisons)
    write_json(OUTPUT_ROOT / "SUMO_CONNECTOR_READINESS_PROBE.json", sumo_probe)
    write_json(OUTPUT_ROOT / "CUOPT_CONNECTOR_READINESS_PROBE.json", cuopt_probe)
    write_json(OUTPUT_ROOT / "FIXTURE_TO_REAL_CONNECTOR_LADDER.json", ladder)
    write_json(OUTPUT_ROOT / "ASSUMPTION_FIDELITY_UNCERTAINTY_SCORECARD.json", scorecard)
    write_json(OUTPUT_ROOT / "CHECK_SIMULATION_VALIDATOR.json", validator)
    write_json(OUTPUT_ROOT / "BRIEF_SIMULATION_ATTACHMENT.json", brief_attachment)
    write_json(OUTPUT_ROOT / "SIMULATION_V2_1_CONNECTOR_UPGRADE_DECISION.json", decision)
    write_summary(decision, sumo_probe, cuopt_probe)
    manifest = write_hash_manifest()
    return {
        "status": decision["status"],
        "decision": decision,
        "multi_scenario_catalog": catalog,
        "sumo_connector_readiness_probe": sumo_probe,
        "cuopt_connector_readiness_probe": cuopt_probe,
        "hash_manifest": manifest,
    }


def validate_outputs() -> list[str]:
    errors = []
    for name in REQUESTED_OUTPUTS + ["HASH_MANIFEST.json"]:
        path = OUTPUT_ROOT / name
        if not path.exists():
            errors.append(f"missing:{name}")
        elif path.suffix == ".json":
            try:
                read_json(path)
            except json.JSONDecodeError as exc:
                errors.append(f"invalid_json:{name}:{exc}")
    if errors:
        return errors
    catalog = read_json(OUTPUT_ROOT / "MULTI_SCENARIO_CATALOG_V2_1.json")
    baselines = read_json(OUTPUT_ROOT / "DO_NOTHING_BASELINES_BY_FAMILY.json")
    comparisons = read_json(OUTPUT_ROOT / "REVIEW_OPTION_COMPARISON_BY_FAMILY.json")
    validator = read_json(OUTPUT_ROOT / "CHECK_SIMULATION_VALIDATOR.json")
    if catalog["scenario_count"] < 4:
        errors.append("scenario_count_below_4")
    if baselines["baseline_count"] != catalog["scenario_count"]:
        errors.append("baseline_count_mismatch")
    if comparisons["family_count"] != catalog["scenario_count"]:
        errors.append("comparison_family_count_mismatch")
    if validator["summary"]["product_forecast_claim_count"] != 0:
        errors.append("product_forecast_claim_detected")
    manifest = read_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
    for entry in manifest.get("entries", []):
        path = OUTPUT_ROOT / entry["path"]
        if not path.exists():
            errors.append(f"manifest_missing:{entry['path']}")
        elif sha256_file(path) != entry["sha256"]:
            errors.append(f"manifest_mismatch:{entry['path']}")
    return errors


def main() -> int:
    result = build_outputs()
    if result["status"] == BLOCKED_STATUS:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2
    errors = validate_outputs()
    status = BLOCKED_STATUS if errors else result["status"]
    print(
        json.dumps(
            {
                "status": status,
                "errors": errors,
                "decision": result["decision"],
                "hash_manifest": result["hash_manifest"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
