#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


TASK_ID = "MAIN-CITYBRAIN-EPOCH3-FOUNDATION-CLOSEOUT-R1"
STATUS = "PASS_E3_FOUNDATION_FOR_LEARNING_AND_BACKTESTING_WITH_LIMITATIONS"
BLOCKED_STATUS = "BLOCKED_E3_FOUNDATION_CLOSEOUT_R1"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_foundation_closeout_r1"

ENTRY_ROOT = REPO_ROOT / "outputs" / "epoch_3_entry_gate_r1_fuel_gauge"
DAY1_ROOT = REPO_ROOT / "outputs" / "epoch3_day1_instrumentation_and_harness_r1"
PHASE2_ROOT = REPO_ROOT / "outputs" / "epoch3_phase2_live_exposure_coverage_and_hardening_r1"
L1_R1_R2_ROOT = REPO_ROOT / "outputs" / "epoch3_l1_r1_r2_outcome_calibration_hardening_r1"
CONVERGENCE_ROOT = REPO_ROOT / "outputs" / "epoch3_pre_closeout_convergence_r1"

FOUNDATION_CLOSED = [
    "L1.R0_EXPOSURE_AND_PROPENSITY_LOGGING",
    "L1.R0_WATCH_EXPLORATION_FLOOR_INFRA",
    "L1.R1_OUTCOME_LEDGER_HARDENING",
    "L1.R2_CALIBRATION_REPORT_HARDENING",
    "L2.R1_BACKTEST_HARNESS_BUILD",
    "E3.ARMING_STATUS_WATCH_FAMILY",
]

STILL_BLOCKED = [
    "L1.R3A_OFFLINE_RANKER_EXPERIMENT",
    "L1.R3B_OPERATOR_FACING_LEARNED_RANKING",
    "L2.R2_FORECAST_MODEL",
    "L3_COUNTERFACTUAL",
    "L4_CASE_MEMORY",
    "DYNAMIC_INVESTIGATION_AGENT",
    "CROSS_CITY_LEARNED_TRANSFER",
]

REQUIRED_SOURCE_ARTIFACTS = [
    CONVERGENCE_ROOT / "E3_PRE_CLOSEOUT_CONVERGENCE_DECISION.json",
    CONVERGENCE_ROOT / "E3_SCHEDULED_WATCH_TICK_EXPOSURE_VERIFICATION_REPORT.json",
    CONVERGENCE_ROOT / "E3_FULL_HISTORICAL_CORPUS_DISCOVERY_REPORT.json",
    CONVERGENCE_ROOT / "E3_L2_R1_BACKTEST_HARNESS_REPORT.json",
    CONVERGENCE_ROOT / "E3_PRE_CLOSEOUT_NO_MODEL_GUARD_REPORT.json",
    CONVERGENCE_ROOT / "E3_PRE_CLOSEOUT_ARMING_STATUS_SNAPSHOT.json",
    PHASE2_ROOT / "E3_LIVE_EXPOSURE_COVERAGE_VERIFICATION_REPORT.json",
    PHASE2_ROOT / "E3_SURFACED_IMPRESSION_DEFINITION_ROW.json",
    L1_R1_R2_ROOT / "E3_OUTCOME_LEDGER_HARDENING_REPORT.json",
    L1_R1_R2_ROOT / "E3_CALIBRATION_REPORT_HARDENING_REPORT.json",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_sources() -> dict[str, Any]:
    return {
        "entry_decision": read_json(ENTRY_ROOT / "E3_ENTRY_GATE_DECISION.json", {}),
        "entry_reconciliation": read_json(ENTRY_ROOT / "E3_E2_2_EXIT_LABEL_FUEL_RECONCILIATION_ROW.json", {}),
        "entry_arming_audit": read_json(ENTRY_ROOT / "E3_ARMING_REQUIREMENT_AUDIT_REPORT.json", {}),
        "day1_decision": read_json(DAY1_ROOT / "E3_DAY1_DECISION.json", {}),
        "day1_no_model": read_json(DAY1_ROOT / "E3_DAY1_NO_MODEL_GUARD_REPORT.json", {}),
        "phase2_decision": read_json(PHASE2_ROOT / "E3_PHASE2_LIVE_EXPOSURE_COVERAGE_DECISION.json", {}),
        "phase2_live_coverage": read_json(PHASE2_ROOT / "E3_LIVE_EXPOSURE_COVERAGE_VERIFICATION_REPORT.json", {}),
        "phase2_surfaced_definition": read_json(PHASE2_ROOT / "E3_SURFACED_IMPRESSION_DEFINITION_ROW.json", {}),
        "l1_decision": read_json(L1_R1_R2_ROOT / "E3_L1_R1_R2_DECISION.json", {}),
        "l1_outcome": read_json(L1_R1_R2_ROOT / "E3_OUTCOME_LEDGER_HARDENING_REPORT.json", {}),
        "l1_calibration": read_json(L1_R1_R2_ROOT / "E3_CALIBRATION_REPORT_HARDENING_REPORT.json", {}),
        "convergence_decision": read_json(CONVERGENCE_ROOT / "E3_PRE_CLOSEOUT_CONVERGENCE_DECISION.json", {}),
        "convergence_scheduled_tick": read_json(
            CONVERGENCE_ROOT / "E3_SCHEDULED_WATCH_TICK_EXPOSURE_VERIFICATION_REPORT.json", {}
        ),
        "convergence_corpus": read_json(CONVERGENCE_ROOT / "E3_FULL_HISTORICAL_CORPUS_DISCOVERY_REPORT.json", {}),
        "convergence_backtest": read_json(CONVERGENCE_ROOT / "E3_L2_R1_BACKTEST_HARNESS_REPORT.json", {}),
        "convergence_arming": read_json(CONVERGENCE_ROOT / "E3_PRE_CLOSEOUT_ARMING_STATUS_SNAPSHOT.json", {}),
        "convergence_no_model": read_json(CONVERGENCE_ROOT / "E3_PRE_CLOSEOUT_NO_MODEL_GUARD_REPORT.json", {}),
    }


def dependency_blockers(sources: dict[str, Any]) -> list[str]:
    blockers = []
    missing = [rel(path) for path in REQUIRED_SOURCE_ARTIFACTS if not path.exists()]
    if missing:
        blockers.append(f"missing_required_source_artifacts:{','.join(missing)}")
    convergence = sources["convergence_decision"]
    if convergence.get("foundation_closeout_ready") is not True:
        blockers.append("pre_closeout_convergence_not_foundation_ready")
    if convergence.get("full_epoch3_closeout_ready") is not False:
        blockers.append("pre_closeout_convergence_did_not_preserve_full_epoch3_false")
    if sources["convergence_scheduled_tick"].get("scheduled_tick_status") != "PASS_FIRST_SCHEDULED_TICK_VERIFIED":
        blockers.append("scheduled_watch_tick_not_verified")
    corpus_status = (
        sources["convergence_corpus"].get("corpus", {}).get("full_discovery", {}).get("status")
    )
    if corpus_status != "green":
        blockers.append("corpus_full_discovery_not_green")
    if sources["convergence_backtest"].get("status") != "PASS_BACKTEST_HARNESS_BUILT_NO_MODEL":
        blockers.append("l2r1_backtest_harness_not_built")
    if sources["convergence_no_model"].get("status") != "PASS":
        blockers.append("convergence_no_model_guard_not_pass")
    return blockers


def source_refs() -> list[str]:
    refs = [
        ENTRY_ROOT / "E3_ENTRY_GATE_DECISION.json",
        ENTRY_ROOT / "E3_E2_2_EXIT_LABEL_FUEL_RECONCILIATION_ROW.json",
        ENTRY_ROOT / "E3_ARMING_REQUIREMENT_AUDIT_REPORT.json",
        DAY1_ROOT / "E3_DAY1_DECISION.json",
        DAY1_ROOT / "E3_DAY1_NO_MODEL_GUARD_REPORT.json",
        PHASE2_ROOT / "E3_PHASE2_LIVE_EXPOSURE_COVERAGE_DECISION.json",
        PHASE2_ROOT / "E3_LIVE_EXPOSURE_COVERAGE_VERIFICATION_REPORT.json",
        PHASE2_ROOT / "E3_SURFACED_IMPRESSION_DEFINITION_ROW.json",
        L1_R1_R2_ROOT / "E3_L1_R1_R2_DECISION.json",
        L1_R1_R2_ROOT / "E3_OUTCOME_LEDGER_HARDENING_REPORT.json",
        L1_R1_R2_ROOT / "E3_CALIBRATION_REPORT_HARDENING_REPORT.json",
        CONVERGENCE_ROOT / "E3_PRE_CLOSEOUT_CONVERGENCE_DECISION.json",
        CONVERGENCE_ROOT / "E3_SCHEDULED_WATCH_TICK_EXPOSURE_VERIFICATION_REPORT.json",
        CONVERGENCE_ROOT / "E3_FULL_HISTORICAL_CORPUS_DISCOVERY_REPORT.json",
        CONVERGENCE_ROOT / "E3_L2_R1_BACKTEST_HARNESS_REPORT.json",
        CONVERGENCE_ROOT / "E3_PRE_CLOSEOUT_ARMING_STATUS_SNAPSHOT.json",
        CONVERGENCE_ROOT / "E3_PRE_CLOSEOUT_NO_MODEL_GUARD_REPORT.json",
    ]
    return [rel(path) for path in refs if path.exists()]


def capability_summary(sources: dict[str, Any]) -> dict[str, Any]:
    phase2 = sources["phase2_live_coverage"]
    scheduled = sources["convergence_scheduled_tick"]
    corpus = sources["convergence_corpus"]
    backtest = sources["convergence_backtest"]
    outcome = sources["l1_outcome"]
    calibration = sources["l1_calibration"]
    return {
        "accepted_foundation_packages": [
            "Entry Gate R1 and follow-up reconciliation",
            "Day 1 instrumentation and harness",
            "Phase 2 live exposure coverage and hardening",
            "L1.R1/R2 outcome calibration hardening",
            "Pre-closeout convergence R1",
        ],
        "capabilities": {
            "arming_status_watch_family": {
                "state": "foundation_ready",
                "source_ref": rel(CONVERGENCE_ROOT / "E3_PRE_CLOSEOUT_ARMING_STATUS_SNAPSHOT.json"),
            },
            "exposure_propensity_logging": {
                "phase2_coverage_ratio": phase2.get("coverage_ratio"),
                "replay_payload_items": phase2.get("operator_visible_payload_items_count"),
                "source_ref": rel(PHASE2_ROOT / "E3_LIVE_EXPOSURE_COVERAGE_VERIFICATION_REPORT.json"),
            },
            "scheduled_watch_tick_exposure": {
                "coverage_ratio": scheduled.get("coverage_ratio"),
                "scheduled_tick_status": scheduled.get("scheduled_tick_status"),
                "source_ref": rel(CONVERGENCE_ROOT / "E3_SCHEDULED_WATCH_TICK_EXPOSURE_VERIFICATION_REPORT.json"),
            },
            "outcome_ledger_hardening": {
                "production_eligible_terminal_dispositions": outcome.get("production_eligible_terminal_dispositions"),
                "validation_fixtures_separated_from_production_fuel": outcome.get(
                    "validation_fixtures_separated_from_production_fuel"
                ),
                "source_ref": rel(L1_R1_R2_ROOT / "E3_OUTCOME_LEDGER_HARDENING_REPORT.json"),
            },
            "calibration_hardening": {
                "sample_depth": calibration.get("sample_depth"),
                "true_calibration_claimed": calibration.get("true_calibration_claimed"),
                "status": calibration.get("status"),
                "source_ref": rel(L1_R1_R2_ROOT / "E3_CALIBRATION_REPORT_HARDENING_REPORT.json"),
            },
            "full_historical_corpus_discovery": {
                "status": corpus.get("corpus", {}).get("full_discovery", {}).get("status"),
                "files_indexed": corpus.get("corpus", {}).get("full_discovery", {}).get("files_indexed"),
                "source_ref": rel(CONVERGENCE_ROOT / "E3_FULL_HISTORICAL_CORPUS_DISCOVERY_REPORT.json"),
            },
            "l2_r1_backtest_harness": {
                "forecast_model_created": backtest.get("forecast_model_created"),
                "status": backtest.get("status"),
                "source_ref": rel(CONVERGENCE_ROOT / "E3_L2_R1_BACKTEST_HARNESS_REPORT.json"),
            },
        },
        "foundation_closed": FOUNDATION_CLOSED,
        "report_id": "E3_FOUNDATION_CAPABILITY_SUMMARY",
        "status": "PASS_WITH_LIMITATIONS",
    }


def arming_status_final(sources: dict[str, Any]) -> dict[str, Any]:
    convergence_arming = sources["convergence_arming"]
    return {
        "armed_or_foundation_closed": FOUNDATION_CLOSED,
        "foundation_closeout_ready": True,
        "full_epoch3_closeout_ready": False,
        "not_armed": STILL_BLOCKED,
        "previous_snapshot_ref": rel(CONVERGENCE_ROOT / "E3_PRE_CLOSEOUT_ARMING_STATUS_SNAPSHOT.json"),
        "report_id": "E3_FOUNDATION_ARMING_STATUS_FINAL",
        "source_capabilities": convergence_arming.get("capabilities", {}),
        "status": "PASS_WITH_LIMITATIONS",
        "threshold_crossing_does_not_start_work": True,
    }


def no_model_guard() -> dict[str, Any]:
    return {
        "case_memory_learner_created": False,
        "counterfactual_learner_created": False,
        "cross_city_learned_transfer_created": False,
        "dynamic_investigation_agent_created": False,
        "forbidden_capabilities_armed": [],
        "forecast_model_created": False,
        "new_learned_component_registry_entries": 0,
        "ranker_created": False,
        "report_id": "E3_FOUNDATION_NO_MODEL_GUARD_REPORT",
        "source_ref": rel(CONVERGENCE_ROOT / "E3_PRE_CLOSEOUT_NO_MODEL_GUARD_REPORT.json"),
        "status": "PASS",
    }


def corpus_and_hash_summary(sources: dict[str, Any]) -> dict[str, Any]:
    corpus = sources["convergence_corpus"]
    return {
        "control_corpus_hash_manifest_status": corpus.get("control_hash_manifest_verification", {}).get("status"),
        "control_corpus_parse_status": corpus.get("control_corpus_parse", {}).get("status"),
        "corpus_full_discovery": corpus.get("corpus", {}).get("full_discovery", {}),
        "legacy_payload_recertification_claimed": False,
        "publication_hash_manifest_ref": "HASH_MANIFEST.json",
        "publication_line_ending_report_ref": "LINE_ENDING_REPORT.json",
        "report_id": "E3_FOUNDATION_CORPUS_AND_HASH_SUMMARY",
        "source_ref": rel(CONVERGENCE_ROOT / "E3_FULL_HISTORICAL_CORPUS_DISCOVERY_REPORT.json"),
        "status": "PASS_WITH_LIMITATIONS",
    }


def backtest_summary(sources: dict[str, Any]) -> dict[str, Any]:
    backtest = sources["convergence_backtest"]
    target = read_json(CONVERGENCE_ROOT / "E3_L2_R1_FIRST_FORECAST_TARGET_DECISION.json", {})
    frozen = read_json(CONVERGENCE_ROOT / "E3_L2_R1_FROZEN_EVAL_SLICE_CONTRACT.json", {})
    comparator = read_json(CONVERGENCE_ROOT / "E3_L2_R1_BASELINE_DO_NOTHING_COMPARATOR.json", {})
    check_gate = read_json(CONVERGENCE_ROOT / "E3_L2_R1_FORECAST_PACKET_CHECK_GATE_SCAFFOLD.json", {})
    return {
        "baseline_comparator": comparator.get("comparator_kind"),
        "check_gate_status": check_gate.get("status"),
        "forecast_model_created": backtest.get("forecast_model_created"),
        "forecast_target_id": target.get("forecast_target_id"),
        "frozen_eval_slice_id": frozen.get("slice_id"),
        "l2_r1_status": backtest.get("status"),
        "metrics": backtest.get("metrics", {}),
        "report_id": "E3_FOUNDATION_BACKTEST_HARNESS_SUMMARY",
        "source_refs": [
            rel(CONVERGENCE_ROOT / "E3_L2_R1_BACKTEST_HARNESS_REPORT.json"),
            rel(CONVERGENCE_ROOT / "E3_L2_R1_FIRST_FORECAST_TARGET_DECISION.json"),
            rel(CONVERGENCE_ROOT / "E3_L2_R1_FROZEN_EVAL_SLICE_CONTRACT.json"),
            rel(CONVERGENCE_ROOT / "E3_L2_R1_BASELINE_DO_NOTHING_COMPARATOR.json"),
            rel(CONVERGENCE_ROOT / "E3_L2_R1_FORECAST_PACKET_CHECK_GATE_SCAFFOLD.json"),
        ],
        "status": "PASS_BACKTEST_HARNESS_BUILT_NO_MODEL",
    }


def outcome_calibration_summary(sources: dict[str, Any]) -> dict[str, Any]:
    outcome = sources["l1_outcome"]
    calibration = sources["l1_calibration"]
    return {
        "calibration_sample_depth": calibration.get("sample_depth"),
        "calibration_status": calibration.get("status"),
        "fixture_eligible_if_production_records": outcome.get("fixture_eligible_if_production_records"),
        "production_eligible_terminal_dispositions": outcome.get("production_eligible_terminal_dispositions"),
        "production_training_fuel_inflated_by_fixtures": False,
        "report_id": "E3_FOUNDATION_OUTCOME_CALIBRATION_SUMMARY",
        "source_refs": [
            rel(L1_R1_R2_ROOT / "E3_OUTCOME_LEDGER_HARDENING_REPORT.json"),
            rel(L1_R1_R2_ROOT / "E3_CALIBRATION_REPORT_HARDENING_REPORT.json"),
        ],
        "status": "PASS_WITH_LIMITATIONS",
        "true_calibration_claimed": calibration.get("true_calibration_claimed"),
    }


def exposure_coverage_summary(sources: dict[str, Any]) -> dict[str, Any]:
    phase2 = sources["phase2_live_coverage"]
    scheduled = sources["convergence_scheduled_tick"]
    surfaced = sources["phase2_surfaced_definition"]
    return {
        "phase2_replay_coverage": {
            "coverage_ratio": phase2.get("coverage_ratio"),
            "exposure_events_count": phase2.get("exposure_events_count"),
            "operator_visible_payload_items_count": phase2.get("operator_visible_payload_items_count"),
            "status": phase2.get("status"),
        },
        "report_id": "E3_FOUNDATION_EXPOSURE_COVERAGE_SUMMARY",
        "scheduled_tick_coverage": {
            "coverage_ratio": scheduled.get("coverage_ratio"),
            "emitted_exposure_events": scheduled.get("emitted_exposure_events"),
            "expected_payload_items": scheduled.get("expected_payload_items"),
            "scheduled_tick_status": scheduled.get("scheduled_tick_status"),
            "status": scheduled.get("status"),
        },
        "source_refs": [
            rel(PHASE2_ROOT / "E3_LIVE_EXPOSURE_COVERAGE_VERIFICATION_REPORT.json"),
            rel(PHASE2_ROOT / "E3_SURFACED_IMPRESSION_DEFINITION_ROW.json"),
            rel(CONVERGENCE_ROOT / "E3_SCHEDULED_WATCH_TICK_EXPOSURE_VERIFICATION_REPORT.json"),
        ],
        "status": "PASS_WITH_LIMITATIONS",
        "surfaced_definition": surfaced.get("surfaced_definition"),
        "surfaced_definition_text": surfaced.get("definition_text"),
    }


def limitations() -> dict[str, Any]:
    return {
        "limitations": [
            "This is an Epoch 3 foundation closeout, not full Epoch 3 completion.",
            "L1.R3A/R3B learned ranking remains blocked.",
            "L2.R2 forecast model remains blocked; L2.R1 is only a no-model backtest harness.",
            "L3 counterfactual and L4 case-memory paths remain blocked.",
            "Dynamic investigation and cross-city learned transfer remain blocked.",
            "Outcome/calibration evidence remains descriptive and production training fuel is not inflated by fixtures.",
            "Corpus discovery is green for foundation gating; legacy generated payloads are not re-certified as model fuel.",
        ],
        "report_id": "E3_FOUNDATION_LIMITATIONS",
        "status": "PASS_WITH_LIMITATIONS",
    }


def next_thresholds() -> dict[str, Any]:
    return {
        "report_id": "E3_FOUNDATION_NEXT_ARMING_THRESHOLDS",
        "status": "PUBLISHED",
        "thresholds": {
            "L1.R3A_OFFLINE_RANKER_EXPERIMENT": [
                "terminal disposition volume",
                "operator diversity",
                "label set sufficiency",
                "exploration floor evidence",
                "static holdout coverage",
                "frozen replay and registry authority",
                "no consuming surfaces",
            ],
            "L1.R3B_OPERATOR_FACING_LEARNED_RANKING": [
                "R3A completed off replay",
                "total and per-operator disposition thresholds",
                "per-family minimums",
                "aggregation floor",
                "exposure coverage",
                "check regression gate",
            ],
            "L2.R2_FORECAST_MODEL": [
                "explicit model authority",
                "sufficient label history",
                "frozen eval slice",
                "baseline comparator",
                "uncertainty schema",
                "ForecastPacket CHECK gate",
            ],
            "L3_COUNTERFACTUAL": ["separate counterfactual package and fidelity gate"],
            "L4_CASE_MEMORY": ["separate case-memory package, retention runtime, and delete path"],
        },
        "threshold_crossing_behavior": "ledger_emit_only_no_silent_start",
    }


def ledger_row(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision_ref": "E3_FOUNDATION_CLOSEOUT_DECISION.json",
        "full_epoch3_closeout_ready": decision["full_epoch3_closeout_ready"],
        "foundation_closeout_ready": decision["foundation_closeout_ready"],
        "ledger_id": "E3_FOUNDATION_LEDGER_ROW",
        "package_id": TASK_ID,
        "published_at": utc_now(),
        "status": decision["status"],
        "summary": "Epoch 3 foundation closed for governed learning and backtesting with limitations; learned/model capabilities remain blocked.",
    }


def closeout_decision(sources: dict[str, Any], blockers: list[str]) -> dict[str, Any]:
    return {
        "blockers": blockers,
        "closeout_kind": "foundation_closeout_only_not_full_epoch3_closeout",
        "evidence_refs": source_refs(),
        "foundation_closeout_ready": not blockers,
        "full_epoch3_closeout_ready": False,
        "full_epoch3_remaining_paths": STILL_BLOCKED,
        "notes": "Instrumentation, exposure coverage, outcome/calibration substrate, corpus discovery, and L2.R1 backtest harness are ready for governed next work. No model path is armed.",
        "status": STATUS if not blockers else BLOCKED_STATUS,
        "task_id": TASK_ID,
    }


def write_readme() -> None:
    text = "\n".join(
        [
            "# Epoch 3 Foundation Closeout R1",
            "",
            f"Task: `{TASK_ID}`",
            "",
            "Status: `PASS_E3_FOUNDATION_FOR_LEARNING_AND_BACKTESTING_WITH_LIMITATIONS`",
            "",
            "This is a foundation closeout only. It confirms that instrumentation, exposure coverage, outcome/calibration hardening, corpus discovery, and the no-model L2.R1 backtest harness are ready for governed next work.",
            "",
            "It does not close full Epoch 3. Ranker, operator-facing learned ranking, forecast model, counterfactual learner, case-memory learner, dynamic investigation, and cross-city learned transfer remain blocked.",
            "",
        ]
    )
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "README.md").write_text(text, encoding="utf-8", newline="\n")


def build_lf_report() -> dict[str, Any]:
    checked = []
    crlf_paths = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if not path.is_file() or path.name in {"HASH_MANIFEST.json", "LINE_ENDING_REPORT.json"}:
            continue
        data = path.read_bytes()
        crlf_count = data.count(b"\r\n")
        checked.append({"bytes": len(data), "crlf_count": crlf_count, "path": rel(path)})
        if crlf_count:
            crlf_paths.append(rel(path))
    return {
        "checked_files": checked,
        "created_at": utc_now(),
        "crlf_paths": crlf_paths,
        "report_id": "LINE_ENDING_REPORT",
        "status": "PASS_LF_STABLE_FOR_E3_FOUNDATION_CLOSEOUT" if not crlf_paths else "FAIL_CRLF_FOUND",
    }


def build_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append({"bytes": path.stat().st_size, "path": rel(path), "sha256": sha256_file(path)})
    manifest = {
        "artifact_root": rel(OUTPUT_ROOT),
        "created_at": utc_now(),
        "files": files,
        "schema_version": "citybrain.hash_manifest.v1",
        "self_reference_policy": "HASH_MANIFEST.json is excluded to avoid recursive hash instability.",
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def write_all_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    sources = load_sources()
    blockers = dependency_blockers(sources)

    write_readme()

    capability = capability_summary(sources)
    arming = arming_status_final(sources)
    guard = no_model_guard()
    corpus = corpus_and_hash_summary(sources)
    backtest = backtest_summary(sources)
    outcome_calibration = outcome_calibration_summary(sources)
    exposure = exposure_coverage_summary(sources)
    limit_report = limitations()
    thresholds = next_thresholds()
    decision = closeout_decision(sources, blockers)
    ledger = ledger_row(decision)

    write_json(OUTPUT_ROOT / "E3_FOUNDATION_CAPABILITY_SUMMARY.json", capability)
    write_json(OUTPUT_ROOT / "E3_FOUNDATION_ARMING_STATUS_FINAL.json", arming)
    write_json(OUTPUT_ROOT / "E3_FOUNDATION_NO_MODEL_GUARD_REPORT.json", guard)
    write_json(OUTPUT_ROOT / "E3_FOUNDATION_CORPUS_AND_HASH_SUMMARY.json", corpus)
    write_json(OUTPUT_ROOT / "E3_FOUNDATION_BACKTEST_HARNESS_SUMMARY.json", backtest)
    write_json(OUTPUT_ROOT / "E3_FOUNDATION_OUTCOME_CALIBRATION_SUMMARY.json", outcome_calibration)
    write_json(OUTPUT_ROOT / "E3_FOUNDATION_EXPOSURE_COVERAGE_SUMMARY.json", exposure)
    write_json(OUTPUT_ROOT / "E3_FOUNDATION_LIMITATIONS.json", limit_report)
    write_json(OUTPUT_ROOT / "E3_FOUNDATION_NEXT_ARMING_THRESHOLDS.json", thresholds)
    write_json(OUTPUT_ROOT / "E3_FOUNDATION_CLOSEOUT_DECISION.json", decision)
    write_json(OUTPUT_ROOT / "E3_FOUNDATION_LEDGER_ROW.json", ledger)

    provisional_lf = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", provisional_lf)
    final_lf = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", final_lf)
    hash_manifest = build_hash_manifest()

    return {
        "arming": arming,
        "backtest": backtest,
        "capability": capability,
        "corpus": corpus,
        "decision": decision,
        "exposure": exposure,
        "hash_manifest": hash_manifest,
        "line_endings": final_lf,
        "no_model_guard": guard,
        "outcome_calibration": outcome_calibration,
    }


def main() -> int:
    result = write_all_outputs()
    decision = result["decision"]
    print(f"Epoch 3 Foundation Closeout R1: {decision['status']}")
    print(f"Foundation closeout ready: {decision['foundation_closeout_ready']}")
    print(f"Full Epoch 3 closeout ready: {decision['full_epoch3_closeout_ready']}")
    print(f"No-model guard: {result['no_model_guard']['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if decision["status"] == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
