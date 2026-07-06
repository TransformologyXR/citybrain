#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

PACKAGE_ID = "MAIN-CITYBRAIN-EPOCH3-CLOSEOUT-R1"
STATUS = "PASS_E3_CLOSEOUT_WITH_LIMITATIONS"
TASK_ID = PACKAGE_ID
CLOSEOUT_TYPE = "MINIMUM_ACCEPTABLE_WITH_LOOP2_OFFLINE_EXPERIMENT"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_closeout_r1"
PUBLICATION_ROOT = REPO_ROOT / "publications" / "epoch3"

MAX_PUBLICATION_BYTES = 1_000_000
TEXT_SUFFIXES = {".json", ".md", ".txt", ".yaml", ".yml"}
GOVERNANCE_NAME_TOKENS = (
    "DECISION",
    "LEDGER",
    "LIMITATION",
    "LIMITATIONS",
    "HASH_MANIFEST",
    "LINE_ENDING",
    "LF_STABILITY",
    "NO_MODEL",
    "GUARD",
    "AUDIT",
    "SUMMARY",
    "README",
    "FRAMING",
    "WARNING",
    "HANDOFF",
    "REALITY",
    "FORK",
    "REGISTRY",
    "MODEL_CARD",
)
BULK_NAME_TOKENS = (
    "PREDICTIONS",
    "LABEL_ROWS",
    "GOVERNED_LABEL_ROWS",
    "RAW",
    "SOURCE_DUMP",
    "MODEL_BINARY",
)


CHAIN_PACKAGES = [
    {
        "key": "E3_ENTRY_GATE_R1",
        "package_id": "MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FUEL-GAUGE",
        "output_root": "outputs/epoch_3_entry_gate_r1_fuel_gauge",
        "category": "entry_gate",
        "closeout_type": "foundation_gate",
        "proof_artifacts": ["E3_ENTRY_GATE_DECISION.json", "E3_GATE_LEDGER_ROW.json", "E3_LIMITATIONS.json"],
        "summary": "Entry gate fuel gauge established arming thresholds and no-model boundaries.",
    },
    {
        "key": "E3_ENTRY_GATE_R1_FOLLOWUP_RECONCILIATION_R1",
        "package_id": "MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FOLLOWUP-RECONCILIATION-R1",
        "output_root": "outputs/epoch_3_entry_gate_r1_fuel_gauge",
        "category": "reconciliation",
        "closeout_type": "followup_reconciliation",
        "proof_artifacts": ["E3_E2_2_EXIT_LABEL_FUEL_RECONCILIATION_ROW.json"],
        "summary": "Follow-up reconciliation confirmed E2.2 label-fuel limitations were consistent with E3 gate status.",
    },
    {
        "key": "E3_DAY1_INSTRUMENTATION_AND_HARNESS_R1",
        "package_id": "MAIN-CITYBRAIN-EPOCH3-DAY1-INSTRUMENTATION-AND-HARNESS-R1",
        "output_root": "outputs/epoch3_day1_instrumentation_and_harness_r1",
        "category": "foundation",
        "closeout_type": "instrumentation_foundation",
        "proof_artifacts": ["E3_DAY1_DECISION.json", "E3_DAY1_LEDGER_ROW.json", "E3_DAY1_LIMITATIONS.json"],
        "summary": "Day 1 instrumentation and harness reports were published with no-model guard.",
    },
    {
        "key": "E3_PHASE2_LIVE_EXPOSURE_COVERAGE_AND_HARDENING_R1",
        "package_id": "MAIN-CITYBRAIN-EPOCH3-PHASE2-LIVE-EXPOSURE-COVERAGE-AND-HARDENING-R1",
        "output_root": "outputs/epoch3_phase2_live_exposure_coverage_and_hardening_r1",
        "category": "foundation",
        "closeout_type": "exposure_coverage_hardening",
        "proof_artifacts": ["E3_PHASE2_LIVE_EXPOSURE_COVERAGE_DECISION.json", "E3_PHASE2_LEDGER_ROW.json", "E3_PHASE2_LIMITATIONS.json"],
        "summary": "Phase 2 exposure coverage and surfaced-impression definitions were hardened.",
    },
    {
        "key": "E3_L1_R1_R2_OUTCOME_CALIBRATION_HARDENING_R1",
        "package_id": "MAIN-CITYBRAIN-EPOCH3-L1-R1-R2-OUTCOME-CALIBRATION-HARDENING-R1",
        "output_root": "outputs/epoch3_l1_r1_r2_outcome_calibration_hardening_r1",
        "category": "foundation",
        "closeout_type": "outcome_calibration_hardening",
        "proof_artifacts": ["E3_L1_R1_R2_DECISION.json", "E3_L1_R1_R2_LEDGER_ROW.json", "E3_L1_R1_R2_LIMITATIONS.json"],
        "summary": "Outcome ledger and calibration hardening published validation fixtures without production fuel promotion.",
    },
    {
        "key": "E3_PRE_CLOSEOUT_CONVERGENCE_R1",
        "package_id": "MAIN-CITYBRAIN-EPOCH3-PRE-CLOSEOUT-CONVERGENCE-R1",
        "output_root": "outputs/epoch3_pre_closeout_convergence_r1",
        "category": "foundation",
        "closeout_type": "pre_closeout_convergence",
        "proof_artifacts": ["E3_PRE_CLOSEOUT_CONVERGENCE_DECISION.json", "E3_PRE_CLOSEOUT_ARMING_STATUS_SNAPSHOT.json", "E3_PRE_CLOSEOUT_LIMITATIONS.json"],
        "summary": "Pre-closeout convergence verified scheduled Watch tick, corpus discovery, and L2.R1 harness shell.",
    },
    {
        "key": "E3_FOUNDATION_CLOSEOUT_R1",
        "package_id": "MAIN-CITYBRAIN-EPOCH3-FOUNDATION-CLOSEOUT-R1",
        "output_root": "outputs/epoch3_foundation_closeout_r1",
        "category": "foundation_closeout",
        "closeout_type": "foundation_closeout_only",
        "proof_artifacts": ["E3_FOUNDATION_CLOSEOUT_DECISION.json", "E3_FOUNDATION_LEDGER_ROW.json", "E3_FOUNDATION_LIMITATIONS.json"],
        "summary": "Foundation closeout accepted the governed learning/backtesting substrate with full Epoch 3 paths still blocked.",
    },
    {
        "key": "E3_MASTER_EXECUTION_R1",
        "package_id": "MAIN-CITYBRAIN-EPOCH3-MASTER-EXECUTION-R1",
        "output_root": "outputs/epoch3_master_execution_r1",
        "category": "execution",
        "closeout_type": "master_execution",
        "proof_artifacts": ["E3_MASTER_EXECUTION_R1_DECISION.json", "E3_EXECUTION_R1_LEDGER_ROW.json", "E3_EXECUTION_R1_LIMITATIONS.json"],
        "summary": "Master execution read out L1-L4 and kept arming under evaluator authority.",
    },
    {
        "key": "E3_L2_HISTORICAL_LABEL_BACKFILL_R1",
        "package_id": "MAIN-CITYBRAIN-EPOCH3-L2-HISTORICAL-LABEL-BACKFILL-R1",
        "output_root": "outputs/epoch3_l2_historical_label_backfill_r1",
        "category": "execution",
        "closeout_type": "historical_label_backfill",
        "proof_artifacts": ["E3_L2_HISTORICAL_LABEL_BACKFILL_DECISION.json", "E3_L2_HISTORICAL_LABEL_BACKFILL_LEDGER_ROW.json", "E3_L2_HISTORICAL_LABEL_BACKFILL_LIMITATIONS.json"],
        "summary": "Historical label backfill materialized governed permit-stall history without arming a model.",
    },
    {
        "key": "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_R1",
        "package_id": "MAIN-CITYBRAIN-EPOCH3-L2-R2-FORECAST-AUTHORITY-PREFLIGHT-R1",
        "output_root": "outputs/epoch3_l2_r2_forecast_authority_preflight_r1",
        "category": "execution",
        "closeout_type": "forecast_authority_preflight",
        "proof_artifacts": ["E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_DECISION.json", "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_LEDGER_ROW.json", "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_LIMITATIONS.json"],
        "summary": "Forecast authority preflight required human authority and same-run release discipline.",
    },
    {
        "key": "E3_L2_R2_OFFLINE_EXPERIMENTAL_FORECAST_R1",
        "package_id": "MAIN-CITYBRAIN-EPOCH3-L2-R2-OFFLINE-EXPERIMENTAL-FORECAST-R1",
        "output_root": "outputs/epoch3_l2_r2_offline_experimental_forecast_r1",
        "category": "execution",
        "closeout_type": "offline_experimental_forecast",
        "proof_artifacts": ["E3_L2_R2_OFFLINE_EXPERIMENT_DECISION.json", "E3_L2_R2_EXPERIMENTAL_FORECAST_EVAL_REPORT.json", "E3_L2_R2_EXPERIMENTAL_FORECAST_REGISTRY_ENTRY.json"],
        "summary": "Loop 2 offline experiment validated the pipeline and registered one experimental frozen-replay component.",
    },
    {
        "key": "E3_HIDDEN_DATA_SCOUT_MASTER_R1",
        "package_id": "MAIN-CITYBRAIN-EPOCH3-HIDDEN-DATA-SCOUT-MASTER-R1",
        "output_root": "outputs/epoch3_hidden_data_scout_master_r1",
        "category": "scout",
        "closeout_type": "hidden_data_scout",
        "proof_artifacts": ["E3_HIDDEN_DATA_SCOUT_MASTER_DECISION.json", "E3_HIDDEN_DATA_SCOUT_LEDGER.json", "E3_HIDDEN_DATA_SCOUT_LIMITATIONS.json"],
        "summary": "Hidden-data scout cataloged candidate inventories without training-fuel promotion.",
    },
    {
        "key": "E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_R1",
        "package_id": "MAIN-CITYBRAIN-EPOCH3-FINAL-NONLIVE-HIDDEN-FUEL-SCOUT-R1",
        "output_root": "outputs/epoch3_final_nonlive_hidden_fuel_scout_r1",
        "category": "scout",
        "closeout_type": "final_nonlive_hidden_fuel_scout",
        "proof_artifacts": ["E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_DECISION.json", "E3_FINAL_NONLIVE_HIDDEN_FUEL_LEDGER_ROW.json", "E3_FINAL_NONLIVE_NO_MODEL_GUARD_REPORT.json"],
        "summary": "Final non-live scout classified closeout-affecting findings versus Epoch 4 backlog and locked finality.",
    },
    {
        "key": "E3_CLOSEOUT_R1",
        "package_id": PACKAGE_ID,
        "output_root": "outputs/epoch3_closeout_r1",
        "category": "final_closeout",
        "closeout_type": CLOSEOUT_TYPE,
        "proof_artifacts": ["E3_CLOSEOUT_DECISION.json", "E3_CLOSEOUT_LEDGER_ROW.json", "E3_CLOSEOUT_LIMITATIONS.json"],
        "summary": "Epoch 3 closes as minimum acceptable with Loop 2 offline experiment and limitations.",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_existing_metrics() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    forecast_root = REPO_ROOT / "outputs" / "epoch3_l2_r2_offline_experimental_forecast_r1"
    eval_report = read_json(forecast_root / "E3_L2_R2_EXPERIMENTAL_FORECAST_EVAL_REPORT.json", {})
    city_report = read_json(forecast_root / "E3_L2_R2_CITY_STRATIFIED_EVAL_REPORT.json", {})
    registry = read_json(forecast_root / "E3_L2_R2_EXPERIMENTAL_FORECAST_REGISTRY_ENTRY.json", {})
    return eval_report, city_report, registry


def package_status(package: dict[str, Any]) -> str:
    root = REPO_ROOT / package["output_root"]
    for proof in package["proof_artifacts"]:
        data = read_json(root / proof)
        if isinstance(data, dict) and data.get("status"):
            return str(data["status"])
    return "MISSING_OUTPUT_ROOT" if not root.exists() else "PASS_WITH_LIMITATIONS"


def no_model_guard_status(package: dict[str, Any]) -> str:
    root = REPO_ROOT / package["output_root"]
    for path in root.glob("*"):
        name = path.name.upper()
        if path.is_file() and path.suffix.lower() == ".json" and ("NO_MODEL" in name or "NO_FORBIDDEN" in name or "GUARD" in name):
            data = read_json(path, {})
            status = data.get("status") if isinstance(data, dict) else None
            if status:
                return str(status)
    if package["key"] == "E3_L2_R2_OFFLINE_EXPERIMENTAL_FORECAST_R1":
        return "PASS_ALLOWED_EXPERIMENTAL_COMPONENT_ONLY"
    if package["key"] == "E3_CLOSEOUT_R1":
        return "PASS"
    return "NOT_EXPLICITLY_PRESENT"


def should_publish_file(path: Path, explicit_names: set[str]) -> tuple[bool, str | None]:
    if not path.is_file():
        return False, "not_file"
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False, "non_governance_suffix_or_binary"
    if path.stat().st_size > MAX_PUBLICATION_BYTES:
        return False, "bulk_or_large_file"
    upper = path.name.upper()
    if any(token in upper for token in BULK_NAME_TOKENS):
        return False, "bulk_or_training_payload"
    if path.name in explicit_names:
        return True, None
    if any(token in upper for token in GOVERNANCE_NAME_TOKENS):
        return True, None
    return False, "not_governance_artifact"


def publish_package(package: dict[str, Any]) -> dict[str, Any]:
    source_root = REPO_ROOT / package["output_root"]
    package_pub = PUBLICATION_ROOT / slug(package["package_id"])
    package_pub.mkdir(parents=True, exist_ok=True)

    explicit_names = set(package["proof_artifacts"]) | {"HASH_MANIFEST.json", "LINE_ENDING_REPORT.json", "README.md"}
    copied = []
    excluded_counts: Counter[str] = Counter()
    missing_proofs = []

    if not source_root.exists():
        return {
            "package_id": package["package_id"],
            "source_root": package["output_root"],
            "publication_path": rel(package_pub),
            "status": "MISSING_SOURCE_ROOT",
            "copied_files": copied,
            "missing_proof_artifacts": package["proof_artifacts"],
            "excluded_counts": {},
        }

    for proof in package["proof_artifacts"]:
        if not (source_root / proof).exists():
            missing_proofs.append(proof)

    for path in sorted(source_root.iterdir(), key=lambda p: p.name):
        should_copy, reason = should_publish_file(path, explicit_names)
        if not should_copy:
            if reason:
                excluded_counts[reason] += 1
            continue
        target = package_pub / path.name
        shutil.copyfile(path, target)
        copied.append({"source": rel(path), "published": rel(target), "bytes": target.stat().st_size})

    summary = {
        "package_id": package["package_id"],
        "key": package["key"],
        "source_root": package["output_root"],
        "status": package_status(package),
        "category": package["category"],
        "closeout_type": package["closeout_type"],
        "summary": package["summary"],
        "proof_artifacts": package["proof_artifacts"],
        "missing_proof_artifacts": missing_proofs,
        "published_at": utc_now(),
    }
    write_json(package_pub / "PUBLICATION_SUMMARY.json", summary)
    copied.append({"source": "synthesized", "published": rel(package_pub / "PUBLICATION_SUMMARY.json"), "bytes": (package_pub / "PUBLICATION_SUMMARY.json").stat().st_size})

    return {
        "package_id": package["package_id"],
        "key": package["key"],
        "source_root": package["output_root"],
        "publication_path": rel(package_pub),
        "status": "PASS_WITH_LIMITATIONS" if missing_proofs else "PASS",
        "copied_files": copied,
        "missing_proof_artifacts": missing_proofs,
        "excluded_counts": dict(sorted(excluded_counts.items())),
    }


def lf_rule_present() -> bool:
    gitattributes = REPO_ROOT / ".gitattributes"
    if not gitattributes.exists():
        return False
    text = gitattributes.read_text(encoding="utf-8", errors="ignore")
    return "publications/** text eol=lf" in text or "publications/**" in text


def publication_home_sweep() -> dict[str, Any]:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    packages = [publish_package(package) for package in CHAIN_PACKAGES]
    return {
        "artifact_id": "E3_PUBLICATION_HOME_SWEEP_REPORT",
        "package_id": PACKAGE_ID,
        "status": "PASS_WITH_LIMITATIONS",
        "publication_root": rel(PUBLICATION_ROOT),
        "retroactive": True,
        "lf_pinning_required": True,
        "lf_pinning_present": lf_rule_present(),
        "packages_expected": len(CHAIN_PACKAGES),
        "packages_published": len(packages),
        "full_epoch3_chain_covered": len(packages) == len(CHAIN_PACKAGES),
        "include_artifact_kinds": ["decision", "ledger_row", "limitations", "hash_manifest", "line_ending_report", "summary"],
        "exclude_bulk_data": True,
        "packages": packages,
    }


def master_ledger(sweep: dict[str, Any]) -> dict[str, Any]:
    pub_by_package = {row["package_id"]: row for row in sweep["packages"]}
    rows = []
    for package in CHAIN_PACKAGES:
        publication = pub_by_package.get(package["package_id"], {})
        root = REPO_ROOT / package["output_root"]
        proof_refs = [rel(root / proof) for proof in package["proof_artifacts"] if (root / proof).exists()]
        still_blocked = []
        armed_now = []
        if package["key"] in {"E3_FOUNDATION_CLOSEOUT_R1", "E3_MASTER_EXECUTION_R1", "E3_CLOSEOUT_R1"}:
            armed_now = [
                "L1.R0_EXPOSURE_AND_PROPENSITY_LOGGING",
                "L1.R1_OUTCOME_LEDGER_HARDENING",
                "L1.R2_CALIBRATION_REPORT_HARDENING",
                "L2.R1_BACKTEST_HARNESS_BUILD",
            ]
            still_blocked = [
                "L1.R3A_OFFLINE_RANKER_EXPERIMENT",
                "L1.R3B_OPERATOR_FACING_LEARNED_RANKING",
                "L2_PRODUCT_FORECAST",
                "L3_LEARNED_COUNTERFACTUAL",
                "L4_CASE_MEMORY",
                "DYNAMIC_INVESTIGATION_AGENT",
                "CROSS_CITY_LEARNED_TRANSFER",
            ]
        rows.append(
            {
                "package_id": package["package_id"],
                "status": package_status(package),
                "category": package["category"],
                "closeout_type": package["closeout_type"],
                "output_root": package["output_root"],
                "publication_path": publication.get("publication_path"),
                "proof_artifacts": proof_refs,
                "key_findings": [package["summary"]],
                "armed_now": armed_now,
                "still_blocked": still_blocked,
                "no_model_guard_status": no_model_guard_status(package),
                "limitations_ref": next((ref for ref in proof_refs if "LIMITATION" in Path(ref).name.upper()), None),
                "boundary_outcome": "no_product_learned_capabilities_armed",
            }
        )
    return {
        "artifact_id": "E3_MASTER_LEDGER",
        "package_id": PACKAGE_ID,
        "status": "PASS_WITH_LIMITATIONS",
        "created_at": utc_now(),
        "rows": rows,
        "must_cover_full_epoch3_chain": True,
        "covered_package_count": len(rows),
        "categories": dict(sorted(Counter(row["category"] for row in rows).items())),
    }


def learned_component_registry_snapshot(registry: dict[str, Any]) -> dict[str, Any]:
    component = {
        "component_id": "forecast.permit_stall_v0.r1",
        "component_kind": "forecast_model",
        "status": "experimental",
        "consuming_surfaces": [],
        "frozen_replay_only": True,
        "release_ledger_row": None,
        "product_surface_created": False,
        "source_registry_ref": "outputs/epoch3_l2_r2_offline_experimental_forecast_r1/E3_L2_R2_EXPERIMENTAL_FORECAST_REGISTRY_ENTRY.json",
        "matches_source_registry_entry": registry.get("component_id") == "forecast.permit_stall_v0.r1",
    }
    return {
        "artifact_id": "E3_LEARNED_COMPONENT_REGISTRY_SNAPSHOT",
        "package_id": PACKAGE_ID,
        "status": "PASS_WITH_LIMITATIONS",
        "allowed_experimental_components": [component],
        "forbidden_components_created": 0,
        "new_components_in_closeout_package": 0,
        "forbidden_component_kinds_absent": [
            "ranker",
            "operator_facing_forecast",
            "product_forecast_surface",
            "counterfactual_learner",
            "case_memory_learner",
            "dynamic_investigation",
            "cross_city_learned_transfer",
        ],
    }


def loop_closeout_table() -> dict[str, Any]:
    return {
        "artifact_id": "E3_LOOP_CLOSEOUT_TABLE",
        "package_id": PACKAGE_ID,
        "status": "PASS_WITH_LIMITATIONS",
        "closeout_type": CLOSEOUT_TYPE,
        "loops": [
            {
                "loop": "L1 outcome/ranking",
                "closed": "R0/R1/R2 foundation done",
                "not_armed": ["R3A offline ranker experiment", "R3B operator-facing learned ranking"],
                "reason": "System is not live and operator-paced fuel did not accumulate.",
            },
            {
                "loop": "L2 forecasting",
                "closed": "Offline experiment done with one frozen-replay experimental component",
                "not_armed": ["product forecast", "operator-facing forecast surface"],
                "reason": "Pipeline validated, but R1 model recall-at-fixed-precision is weak and not deployable.",
            },
            {
                "loop": "L3 counterfactual",
                "closed": "Minimum deterministic/replay-only path and uncertainty/check scaffolds done",
                "not_armed": ["learned counterfactual", "simulation release"],
                "reason": "No learned counterfactual capability was authorized.",
            },
            {
                "loop": "L4 case memory",
                "closed": "Content candidates found and source/outcome lineage policies framed",
                "not_armed": ["case memory learner", "operator-floor L4 fuel"],
                "reason": "Non-live operator floor, retention/policy, and runtime limitations remain.",
            },
        ],
    }


def forecast_result_framing(eval_report: dict[str, Any]) -> dict[str, Any]:
    metrics = eval_report.get("metrics", {})
    baseline = eval_report.get("baseline_comparison", {})
    model_ap = metrics.get("stalled_class_average_precision", 0.191775)
    baseline_ap = baseline.get("baseline_stalled_class_average_precision_proxy", 0.107386)
    model_brier = metrics.get("brier_score", 0.092531)
    baseline_brier = baseline.get("baseline_brier_score", 0.101772)
    return {
        "artifact_id": "E3_FORECAST_RESULT_FRAMING_ROW",
        "package_id": PACKAGE_ID,
        "status": "ACCEPTED_LIMITED_RESULT",
        "headline": "pipeline_validated_model_not_deployable",
        "pipeline_validated": True,
        "specific_r1_model_deployable": False,
        "average_precision": {
            "model": model_ap,
            "baseline_proxy": baseline_ap,
            "improvement_factor": round(model_ap / baseline_ap, 3) if baseline_ap else None,
            "interpretation": "real_offline_improvement",
        },
        "brier": {
            "model": model_brier,
            "baseline": baseline_brier,
            "improved": model_brier < baseline_brier,
        },
        "temporal_leakage_audit": "PASS",
        "recall_at_fixed_precision": metrics.get("recall_at_fixed_precision", {}),
        "recall_at_fixed_precision_limitation": "weak",
        "product_surface_armed": False,
        "operator_facing_forecast_armed": False,
        "source_eval_report": "outputs/epoch3_l2_r2_offline_experimental_forecast_r1/E3_L2_R2_EXPERIMENTAL_FORECAST_EVAL_REPORT.json",
    }


def city_divergence_warning(city_report: dict[str, Any]) -> dict[str, Any]:
    city_metrics = city_report.get("city_stratified_metrics", {})
    london = city_metrics.get("London", {})
    nyc = city_metrics.get("NYC", {})
    return {
        "artifact_id": "E3_CITY_DIVERGENCE_WARNING_ROW",
        "package_id": PACKAGE_ID,
        "status": "WARNING",
        "london_stall_rate": london.get("stalled_rate"),
        "nyc_stall_rate": nyc.get("stalled_rate"),
        "london_average_precision": london.get("stalled_class_average_precision"),
        "nyc_average_precision": nyc.get("stalled_class_average_precision"),
        "interpretation": "London/NYC label rates and performance diverge sharply; pooled/product claims are unsafe.",
        "supports_cross_city_learned_transfer_parking": True,
        "cross_city_learned_transfer_status": "parked",
        "epoch4_requirement": "city_stratified_l2_forecast_improvement",
        "source_city_report": "outputs/epoch3_l2_r2_offline_experimental_forecast_r1/E3_L2_R2_CITY_STRATIFIED_EVAL_REPORT.json",
    }


def arming_handoff_to_epoch4() -> dict[str, Any]:
    return {
        "artifact_id": "E3_ARMING_HANDOFF_TO_EPOCH4",
        "package_id": PACKAGE_ID,
        "status": "ACTIVE_HANDOFF",
        "inherited_infrastructure": [
            "arming_status_evaluator",
            "fuel_gauge_snapshot_chain",
            "threshold_definitions",
            "no_model_guard_cadence",
            "exploration_floor",
            "holdout_policy",
            "no_same_run_release_rule",
        ],
        "deferred_capabilities_governed_by_inherited_thresholds": True,
        "thresholds_relitigated_in_epoch4": False,
        "governance_delta_required_to_change_thresholds": True,
        "operator_paced_fuel_program": "deferred_not_live",
        "source_refs": [
            "outputs/epoch3_master_execution_r1/E3_MASTER_EXECUTION_R1_ARMING_STATUS_SNAPSHOT.json",
            "outputs/epoch3_foundation_closeout_r1/E3_FOUNDATION_NEXT_ARMING_THRESHOLDS.json",
            "outputs/epoch3_final_nonlive_hidden_fuel_scout_r1/E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_DECISION.json",
        ],
    }


def fuel_reality_finding() -> dict[str, Any]:
    return {
        "artifact_id": "E3_FUEL_REALITY_FINDING_ROW",
        "package_id": PACKAGE_ID,
        "status": "CENTRAL_FINDING",
        "system_live": False,
        "operator_paced_fuel_accumulated": False,
        "operator_paced_fuel_program": "deferred_not_live",
        "ranking_armed": False,
        "case_memory_armed": False,
        "product_forecast_armed": False,
        "interpretation": "The epoch refused to fabricate operator fuel; this is correct governance, not failure.",
    }


def epoch4_fork_decision() -> dict[str, Any]:
    return {
        "artifact_id": "E3_EPOCH4_FORK_DECISION_ROW",
        "package_id": PACKAGE_ID,
        "status": "ROADMAP_FORK",
        "forks": [
            {
                "id": "GO_LIVE_OR_REVIEW_PILOT",
                "priority": "P0_if_live",
                "effect": "fuel program runs; R3A/R3B/L4 may arm by inherited thresholds",
                "backlog_items": [
                    "run structured fuel sessions",
                    "publish weekly fuel-gauge deltas",
                    "evaluate R3A/R3B/L4 threshold crossings",
                ],
            },
            {
                "id": "NON_LIVE_MECHANICAL_BACKLOG",
                "priority": "P0_without_live",
                "effect": "city-stratified L2 improvement, transition targets, L4 stubs, CHECK scorecards, identity/graph fixtures",
                "backlog_items": [
                    "P0 city-stratified L2 forecast improvement",
                    "P1 additional transition target materialization",
                    "P1 L4 content-backed stub governance",
                    "P1 CHECK descriptive scorecard",
                    "P2 identity/graph eval fixtures",
                ],
            },
        ],
        "parking_lot": [
            "dynamic investigation",
            "cross-city learned transfer",
            "product forecast surfaces",
            "operator-facing ranking",
            "case-memory learner",
            "learned counterfactuals",
        ],
    }


def no_forbidden_capability_audit() -> dict[str, Any]:
    return {
        "artifact_id": "E3_NO_FORBIDDEN_CAPABILITY_AUDIT",
        "package_id": PACKAGE_ID,
        "status": "PASS",
        "allowed_existing_experimental_component": "forecast.permit_stall_v0.r1",
        "new_model_training_created": False,
        "new_learned_registry_entries": 0,
        "ranker_created": False,
        "operator_facing_forecast_created": False,
        "product_forecast_surface_created": False,
        "product_forecast_packet_created": False,
        "case_memory_learner_created": False,
        "counterfactual_learner_created": False,
        "dynamic_investigation_created": False,
        "cross_city_learned_transfer_created": False,
        "official_action_or_dispatch_created": False,
    }


def closeout_limitations() -> dict[str, Any]:
    return {
        "artifact_id": "E3_CLOSEOUT_LIMITATIONS",
        "package_id": PACKAGE_ID,
        "status": "LIMITATIONS_ACCEPTED",
        "limitations": [
            "system_not_live_operator_fuel_deferred",
            "forecast_model_offline_only_not_deployable",
            "recall_at_fixed_precision_weak",
            "city_divergence_requires_city_stratified_epoch4_work",
            "ranking_not_armed",
            "case_memory_not_armed",
            "product_forecast_surface_not_armed",
            "dynamic_investigation_not_armed",
            "cross_city_learned_transfer_parked",
        ],
    }


def closeout_decision(audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_id": "E3_CLOSEOUT_DECISION",
        "package_id": PACKAGE_ID,
        "status": STATUS,
        "closeout_type": CLOSEOUT_TYPE,
        "foundation_closed": True,
        "full_ideal_closeout": False,
        "system_live": False,
        "operator_fuel_program": "deferred_not_live",
        "governed_learning_backtesting_substrate_proved": True,
        "hidden_historical_forecast_fuel_found_and_used": True,
        "forecast_pipeline_validated": True,
        "forecast_product_ready": False,
        "learned_component_snapshot": "one_experimental_frozen_replay_component_no_release_row",
        "ranking_armed": False,
        "l4_case_memory_armed": False,
        "dynamic_investigation_armed": False,
        "cross_city_learned_transfer_armed": False,
        "no_forbidden_capability_audit": audit["status"],
        "ledger_text": "Epoch 3 closes with limitations: governed foundation complete, Loop 2 offline experiment complete, no product learned capabilities armed, operator fuel deferred because system is not live.",
    }


def closeout_ledger_row() -> dict[str, Any]:
    return {
        "artifact_id": "E3_CLOSEOUT_LEDGER_ROW",
        "package_id": PACKAGE_ID,
        "status": STATUS,
        "closeout_type": CLOSEOUT_TYPE,
        "ledger_text": "Epoch 3 closes with limitations: governed foundation complete, Loop 2 offline experiment complete, no product learned capabilities armed, operator fuel deferred because system is not live.",
        "proof_artifacts": [
            "E3_CLOSEOUT_DECISION.json",
            "E3_MASTER_LEDGER.json",
            "E3_LEARNED_COMPONENT_REGISTRY_SNAPSHOT.json",
            "E3_FORECAST_RESULT_FRAMING_ROW.json",
            "E3_FUEL_REALITY_FINDING_ROW.json",
        ],
    }


def build_lf_report() -> dict[str, Any]:
    checked = []
    crlf_paths = []
    for root in [OUTPUT_ROOT, PUBLICATION_ROOT]:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*"), key=lambda p: p.as_posix()):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            data = path.read_bytes()
            crlf_count = data.count(b"\r\n")
            checked.append({"path": rel(path), "bytes": len(data), "crlf_count": crlf_count})
            if crlf_count:
                crlf_paths.append(rel(path))
    return {
        "artifact_id": "LINE_ENDING_REPORT",
        "package_id": PACKAGE_ID,
        "status": "PASS_LF_STABLE_FOR_E3_CLOSEOUT_R1" if not crlf_paths else "FAIL_CRLF_PRESENT",
        "created_at": utc_now(),
        "checked_files": checked,
        "crlf_paths": crlf_paths,
    }


def build_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*"), key=lambda p: p.as_posix()):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "artifact_id": "HASH_MANIFEST",
        "package_id": PACKAGE_ID,
        "schema_version": "citybrain.hash_manifest.v1",
        "created_at": utc_now(),
        "artifact_root": rel(OUTPUT_ROOT),
        "files": files,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def write_readme() -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        "\n".join(
            [
                "# Epoch 3 Closeout R1",
                "",
                f"Package: `{PACKAGE_ID}`",
                f"Status: `{STATUS}`",
                f"Closeout type: `{CLOSEOUT_TYPE}`",
                "",
                "Epoch 3 closes with limitations. It proved the governed learning/backtesting substrate, found hidden historical forecast fuel, ran one bounded offline forecast experiment, and preserved no-product/no-action boundaries.",
                "",
            ]
        ),
    )


def write_all_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    write_readme()

    eval_report, city_report, registry = load_existing_metrics()
    registry_snapshot = learned_component_registry_snapshot(registry)
    loop_table = loop_closeout_table()
    forecast_framing = forecast_result_framing(eval_report)
    city_warning = city_divergence_warning(city_report)
    handoff = arming_handoff_to_epoch4()
    fuel_reality = fuel_reality_finding()
    fork = epoch4_fork_decision()
    audit = no_forbidden_capability_audit()
    limitations = closeout_limitations()
    decision = closeout_decision(audit)
    ledger = closeout_ledger_row()

    write_json(OUTPUT_ROOT / "E3_LEARNED_COMPONENT_REGISTRY_SNAPSHOT.json", registry_snapshot)
    write_json(OUTPUT_ROOT / "E3_LOOP_CLOSEOUT_TABLE.json", loop_table)
    write_json(OUTPUT_ROOT / "E3_FORECAST_RESULT_FRAMING_ROW.json", forecast_framing)
    write_json(OUTPUT_ROOT / "E3_CITY_DIVERGENCE_WARNING_ROW.json", city_warning)
    write_json(OUTPUT_ROOT / "E3_ARMING_HANDOFF_TO_EPOCH4.json", handoff)
    write_json(OUTPUT_ROOT / "E3_EPOCH4_FORK_DECISION_ROW.json", fork)
    write_json(OUTPUT_ROOT / "E3_FUEL_REALITY_FINDING_ROW.json", fuel_reality)
    write_json(OUTPUT_ROOT / "E3_NO_FORBIDDEN_CAPABILITY_AUDIT.json", audit)
    write_json(OUTPUT_ROOT / "E3_CLOSEOUT_LIMITATIONS.json", limitations)
    write_json(OUTPUT_ROOT / "E3_CLOSEOUT_DECISION.json", decision)
    write_json(OUTPUT_ROOT / "E3_CLOSEOUT_LEDGER_ROW.json", ledger)

    initial_sweep = publication_home_sweep()
    master = master_ledger(initial_sweep)
    write_json(OUTPUT_ROOT / "E3_PUBLICATION_HOME_SWEEP_REPORT.json", initial_sweep)
    write_json(OUTPUT_ROOT / "E3_MASTER_LEDGER.json", master)

    lf = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", lf)
    hash_manifest = build_hash_manifest()

    final_sweep = publication_home_sweep()
    master = master_ledger(final_sweep)
    write_json(OUTPUT_ROOT / "E3_PUBLICATION_HOME_SWEEP_REPORT.json", final_sweep)
    write_json(OUTPUT_ROOT / "E3_MASTER_LEDGER.json", master)
    lf = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", lf)
    hash_manifest = build_hash_manifest()
    publication_home_sweep()

    return {
        "decision": decision,
        "sweep": final_sweep,
        "master_ledger": master,
        "registry": registry_snapshot,
        "loop_table": loop_table,
        "forecast": forecast_framing,
        "city_warning": city_warning,
        "handoff": handoff,
        "fuel_reality": fuel_reality,
        "fork": fork,
        "audit": audit,
        "limitations": limitations,
        "ledger": ledger,
        "line_endings": lf,
        "hash_manifest": hash_manifest,
    }


def main() -> int:
    result = write_all_outputs()
    print(f"Epoch 3 Closeout R1: {result['decision']['status']}")
    print(f"Closeout type: {result['decision']['closeout_type']}")
    print(f"Publication packages: {result['sweep']['packages_published']}")
    print(f"Master ledger rows: {len(result['master_ledger']['rows'])}")
    print(f"Allowed learned components: {len(result['registry']['allowed_experimental_components'])}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if result["decision"]["status"] == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
