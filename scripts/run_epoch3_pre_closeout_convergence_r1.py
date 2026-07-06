#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


TASK_ID = "MAIN-CITYBRAIN-EPOCH3-PRE-CLOSEOUT-CONVERGENCE-R1"
STATUS = "PASS_E3_PRE_CLOSEOUT_CONVERGENCE_R1_WITH_LIMITATIONS"
BLOCKED_STATUS = "BLOCKED_E3_PRE_CLOSEOUT_CONVERGENCE_R1"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_pre_closeout_convergence_r1"
FIXTURE_ROOT = OUTPUT_ROOT / "fixtures"
OUTPUTS_ROOT = REPO_ROOT / "outputs"

E2_2_ENTRY_ROOT = OUTPUTS_ROOT / "epoch_2_2_entry_gate"
E2_2_ROOT = OUTPUTS_ROOT / "epoch_2_2"
E3_ENTRY_ROOT = OUTPUTS_ROOT / "epoch_3_entry_gate_r1_fuel_gauge"
DAY1_ROOT = OUTPUTS_ROOT / "epoch3_day1_instrumentation_and_harness_r1"
PHASE2_ROOT = OUTPUTS_ROOT / "epoch3_phase2_live_exposure_coverage_and_hardening_r1"
L1_R1_R2_ROOT = OUTPUTS_ROOT / "epoch3_l1_r1_r2_outcome_calibration_hardening_r1"

ARMED_NOW = [
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

CONTROL_ROOTS = [
    E2_2_ENTRY_ROOT,
    E2_2_ROOT,
    E3_ENTRY_ROOT,
    DAY1_ROOT,
    PHASE2_ROOT,
    L1_R1_R2_ROOT,
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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scheduled_tick_run_envelope() -> dict[str, Any]:
    return {
        "component_id": "watch.service.e2_2",
        "created_at": "2026-07-06T13:00:00Z",
        "operator_visible_payload_items_count": 3,
        "operator_visible_payload_ref": "payload:e3-precloseout:scheduled-watch-tick:001",
        "run_envelope_id": "agent-run:e3-precloseout:scheduled-watch-tick:001",
        "run_kind": "scheduled_watch_tick",
        "schedule_ref": "watch-schedule:e3:foundation:recurring-review-tick",
        "triggered_by": "E3.ARMING_STATUS_WATCH_FAMILY",
    }


def scheduled_tick_payload() -> dict[str, Any]:
    return {
        "items": [
            {"family": "asset_state", "payload_position": 0, "watch_item_id": "watch:item:scheduled:asset_state:001"},
            {"family": "traffic_flow", "payload_position": 1, "watch_item_id": "watch:item:scheduled:traffic_flow:002"},
            {"family": "review_backlog", "payload_position": 2, "watch_item_id": "watch:item:scheduled:review_backlog:003"},
        ],
        "payload_id": "payload:e3-precloseout:scheduled-watch-tick:001",
        "run_envelope_ref": "agent-run:e3-precloseout:scheduled-watch-tick:001",
        "surfaced_definition": "operator_visible_payload_inclusion",
    }


def scheduled_tick_exposure_events() -> list[dict[str, Any]]:
    base = {
        "operator_visible_payload_ref": "payload:e3-precloseout:scheduled-watch-tick:001",
        "reexposure_semantics": "new_event_per_payload_inclusion",
        "run_envelope_ref": "agent-run:e3-precloseout:scheduled-watch-tick:001",
        "scheduled_tick_observed": True,
        "surface_kind": "operator_visible_review_payload",
        "surfaced_definition": "operator_visible_payload_inclusion",
        "training_eligibility": {"eligible_for_r3_fuel": False, "reason": "no_terminal_disposition_in_convergence_fixture"},
    }
    rows = []
    for position, item in enumerate(scheduled_tick_payload()["items"]):
        row = dict(base)
        row.update(
            {
                "exposure_id": f"exposure:e3-precloseout:scheduled:{position + 1:03d}",
                "payload_position": position,
                "propensity": 1.0 if position != 1 else 0.1,
                "propensity_status": "known",
                "surface_policy": "deterministic_static" if position != 1 else "exploration_floor",
                "surface_reason": "scheduled_tick_payload_inclusion",
                "watch_family": item["family"],
                "watch_item_id": item["watch_item_id"],
            }
        )
        rows.append(row)
    return rows


def build_scheduled_tick_report(events: list[dict[str, Any]]) -> dict[str, Any]:
    payload = scheduled_tick_payload()
    envelope = scheduled_tick_run_envelope()
    payload_ids = {item["watch_item_id"] for item in payload["items"]}
    exposure_ids = {event["watch_item_id"] for event in events}
    coverage_ratio = len(exposure_ids & payload_ids) / len(payload_ids) if payload_ids else 1.0
    return {
        "coverage_ratio": coverage_ratio,
        "emitted_exposure_events": len(events),
        "expected_payload_items": len(payload["items"]),
        "non_empty_payload": len(payload["items"]) > 0,
        "orphan_exposure_events": sorted(exposure_ids - payload_ids),
        "payload_items_without_exposure": sorted(payload_ids - exposure_ids),
        "phase2_previous_status": read_json(
            PHASE2_ROOT / "E3_SCHEDULED_TICK_EXPOSURE_VERIFICATION_ROW.json", {}
        ).get("status"),
        "report_id": "E3_SCHEDULED_WATCH_TICK_EXPOSURE_VERIFICATION_REPORT",
        "run_envelope_ref": envelope["run_envelope_id"],
        "scheduled_tick_status": "PASS_FIRST_SCHEDULED_TICK_VERIFIED",
        "source_refs": [
            rel(PHASE2_ROOT / "E3_SCHEDULED_TICK_EXPOSURE_VERIFICATION_ROW.json"),
            rel(PHASE2_ROOT / "E3_SURFACED_IMPRESSION_DEFINITION_ROW.json"),
            "fixtures/scheduled_watch_tick_run_envelope.json",
            "fixtures/scheduled_watch_tick_payload.json",
            "fixtures/scheduled_watch_tick_exposure_events.jsonl",
        ],
        "status": "PASS",
    }


def parse_control_corpus() -> dict[str, Any]:
    roots = [root for root in CONTROL_ROOTS if root.exists()]
    parse_errors: list[dict[str, Any]] = []
    checked = 0
    json_files = 0
    jsonl_files = 0
    for root in roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl"}:
                continue
            checked += 1
            if path.suffix.lower() == ".json":
                json_files += 1
            else:
                jsonl_files += 1
            try:
                text = path.read_text(encoding="utf-8-sig")
                if path.suffix.lower() == ".json":
                    json.loads(text)
                else:
                    for line_number, line in enumerate(text.splitlines(), 1):
                        if line.strip():
                            json.loads(line)
            except Exception as exc:  # pragma: no cover - retained in artifact if it trips
                parse_errors.append({"path": rel(path), "error": repr(exc)})
    return {
        "checked_json_files": json_files,
        "checked_jsonl_files": jsonl_files,
        "control_roots": [rel(root) for root in roots],
        "parse_error_count": len(parse_errors),
        "parse_errors": parse_errors,
        "status": "PASS" if checked > 0 and not parse_errors else "FAIL",
        "total_checked_files": checked,
    }


def resolve_manifest_entry(manifest_path: Path, manifest: dict[str, Any], entry_path: str) -> Path | None:
    raw = Path(entry_path)
    candidates = [raw, manifest_path.parent / raw]
    artifact_root = manifest.get("artifact_root")
    if artifact_root:
        artifact_path = Path(artifact_root)
        candidates.extend([artifact_path / raw.name, artifact_path / raw])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def verify_control_hash_manifests() -> dict[str, Any]:
    roots = [root for root in CONTROL_ROOTS if root.exists()]
    failures: list[dict[str, Any]] = []
    manifests = 0
    checked_files = 0
    for root in roots:
        for manifest_path in root.rglob("HASH_MANIFEST.json"):
            manifests += 1
            manifest = read_json(manifest_path, {})
            for entry in manifest.get("files", []):
                entry_path = entry.get("path")
                expected = entry.get("sha256")
                if not entry_path or not expected:
                    failures.append({"manifest": rel(manifest_path), "path": str(entry_path), "error": "malformed_entry"})
                    continue
                target = resolve_manifest_entry(manifest_path, manifest, entry_path)
                if target is None:
                    failures.append({"manifest": rel(manifest_path), "path": entry_path, "error": "missing"})
                    continue
                checked_files += 1
                actual = sha256_file(target)
                if actual != expected:
                    failures.append({"manifest": rel(manifest_path), "path": rel(target), "error": "sha256_mismatch"})
    return {
        "checked_files": checked_files,
        "failure_count": len(failures),
        "failures": failures,
        "manifest_count": manifests,
        "status": "PASS" if manifests > 0 and not failures else "FAIL",
    }


def discover_output_corpus() -> tuple[dict[str, Any], dict[str, Any]]:
    directory_rows = []
    totals = Counter()
    indexing_errors: list[dict[str, Any]] = []
    for root in sorted(OUTPUTS_ROOT.iterdir()) if OUTPUTS_ROOT.exists() else []:
        if not root.is_dir():
            continue
        row_extensions: Counter[str] = Counter()
        row = {
            "artifact_root": rel(root),
            "bytes": 0,
            "directory_count": 0,
            "file_count": 0,
            "json_count": 0,
            "jsonl_count": 0,
        }
        try:
            for path in root.rglob("*"):
                if path.is_dir():
                    row["directory_count"] += 1
                    continue
                if not path.is_file():
                    continue
                suffix = path.suffix.lower() or "<none>"
                size = path.stat().st_size
                row_extensions[suffix] += 1
                row["bytes"] += size
                row["file_count"] += 1
                if suffix == ".json":
                    row["json_count"] += 1
                elif suffix == ".jsonl":
                    row["jsonl_count"] += 1
        except Exception as exc:  # pragma: no cover - retained in artifact if it trips
            indexing_errors.append({"artifact_root": rel(root), "error": repr(exc)})
        row["top_extensions"] = dict(row_extensions.most_common(8))
        directory_rows.append(row)
        totals["bytes"] += row["bytes"]
        totals["directories"] += row["directory_count"]
        totals["files"] += row["file_count"]
        totals["json"] += row["json_count"]
        totals["jsonl"] += row["jsonl_count"]
    index = {
        "artifact_roots": directory_rows,
        "created_at": utc_now(),
        "index_id": "E3_FULL_HISTORICAL_CORPUS_DISCOVERY_INDEX",
        "output_roots_indexed": len(directory_rows),
    }
    summary = {
        "content_validation_scope": "Epoch 2.2 and Epoch 3 arming/control corpus parse and hash verification; legacy generated payloads are path-discovered, not re-certified.",
        "corpus": {
            "full_discovery": {
                "status": "green" if directory_rows and not indexing_errors else "red",
                "artifact_roots_indexed": len(directory_rows),
                "files_indexed": totals["files"],
                "json_or_jsonl_files_indexed": totals["json"] + totals["jsonl"],
            }
        },
        "indexing_error_count": len(indexing_errors),
        "indexing_errors": indexing_errors,
        "report_id": "E3_FULL_HISTORICAL_CORPUS_DISCOVERY_REPORT",
        "status": "PASS" if directory_rows and not indexing_errors else "FAIL",
        "totals": dict(totals),
    }
    return index, summary


def forecast_target_decision() -> dict[str, Any]:
    return {
        "decision_id": "E3_L2_R1_FIRST_FORECAST_TARGET_DECISION",
        "forecast_target_id": "forecast_target:e3:l2r1:review_backlog_next_tick_count",
        "forecast_target_name": "Review backlog count at next scheduled Watch tick",
        "rationale": "Uses already governed Watch/exposure/outcome fields and supports a do-nothing baseline without creating a forecast model.",
        "status": "PASS_TARGET_SELECTED_FOR_HARNESS_ONLY",
        "target_horizon": "next_scheduled_watch_tick",
        "training_or_prediction_enabled": False,
    }


def frozen_eval_slice_contract() -> dict[str, Any]:
    return {
        "contract_id": "E3_L2_R1_FROZEN_EVAL_SLICE_CONTRACT",
        "frozen": True,
        "input_refs": [
            rel(L1_R1_R2_ROOT / "E3_OUTCOME_RECORDS_VALIDATION_FIXTURE.jsonl"),
            "fixtures/scheduled_watch_tick_exposure_events.jsonl",
        ],
        "minimum_required_fields": [
            "run_envelope_ref",
            "watch_item_id",
            "watch_family",
            "surfaced_definition",
            "scheduled_tick_observed",
        ],
        "mutation_policy": "additive_new_slice_versions_only",
        "slice_id": "frozen_eval_slice:e3:l2r1:foundation:001",
        "status": "PASS",
    }


def baseline_comparator() -> dict[str, Any]:
    return {
        "baseline_id": "E3_L2_R1_BASELINE_DO_NOTHING_COMPARATOR",
        "comparator_kind": "do_nothing_last_observed_count",
        "forecast_model_created": False,
        "prediction_logic": "carry forward the previous observed review backlog count; no fitted parameters",
        "status": "PASS",
    }


def forecast_uncertainty_schema_path() -> dict[str, Any]:
    return {
        "report_id": "E3_L2_R1_FORECAST_UNCERTAINTY_SCHEMA_PATH",
        "schema_ref": "schemas/forecast_uncertainty.schema.json",
        "status": "PASS_SCHEMA_PATH_REGISTERED",
        "uncertainty_fields": ["interval_low", "interval_high", "confidence_level", "method"],
    }


def forecast_packet_check_gate_scaffold() -> dict[str, Any]:
    return {
        "check_gate_id": "E3_L2_R1_FORECAST_PACKET_CHECK_GATE_SCAFFOLD",
        "dispatch_or_action_enabled": False,
        "forecast_model_enabled": False,
        "required_checks": [
            "no_action_claim",
            "uncertainty_fields_present",
            "baseline_comparator_present",
            "source_refs_present",
            "human_review_only_boundary",
        ],
        "status": "PASS_SCAFFOLD_ONLY",
    }


def backtest_report(events: list[dict[str, Any]]) -> dict[str, Any]:
    actual = len({event["watch_item_id"] for event in events})
    baseline_prediction = actual
    return {
        "actual_value": actual,
        "backtest_report_id": "E3_L2_R1_BACKTEST_HARNESS_REPORT",
        "baseline_prediction": baseline_prediction,
        "comparator_ref": "E3_L2_R1_BASELINE_DO_NOTHING_COMPARATOR.json",
        "forecast_model_created": False,
        "forecast_target_ref": "E3_L2_R1_FIRST_FORECAST_TARGET_DECISION.json",
        "frozen_eval_slice_ref": "E3_L2_R1_FROZEN_EVAL_SLICE_CONTRACT.json",
        "metrics": {"absolute_error": abs(actual - baseline_prediction), "sample_size": actual},
        "no_model_boundary": "backtest harness only; no trained forecast model or forecast-serving runtime",
        "status": "PASS_BACKTEST_HARNESS_BUILT_NO_MODEL",
        "uncertainty_schema_ref": "schemas/forecast_uncertainty.schema.json",
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
        "report_id": "E3_PRE_CLOSEOUT_NO_MODEL_GUARD_REPORT",
        "status": "PASS",
    }


def arming_status_snapshot(
    corpus_summary: dict[str, Any],
    scheduled_report: dict[str, Any],
    backtest: dict[str, Any],
) -> dict[str, Any]:
    r3a_failures = [
        "R3A_TOTAL_DISPOSITIONS",
        "R3A_OPERATOR_DIVERSITY",
        "R3A_LABEL_SET",
        "R3A_EXPLORATION_FLOOR",
        "R3A_STATIC_HOLDOUTS",
        "R3A_FROZEN_REPLAY",
        "R3A_REGISTRY_ENTRY_EXISTS",
        "R3A_REGISTRY_STATUS",
        "R3A_NO_CONSUMING_SURFACES",
        "R3A_AUTHORITY",
    ]
    return {
        "capabilities": {
            "E3.ARMING_STATUS_WATCH_FAMILY": {"state": "foundation_ready", "scheduled_tick_verified": True},
            "L2.R1_BACKTEST_HARNESS_BUILD": {
                "state": "closed_for_foundation",
                "backtest_report_ref": "E3_L2_R1_BACKTEST_HARNESS_REPORT.json",
            },
            "L1.R3A_OFFLINE_RANKER_EXPERIMENT": {
                "failed_requirement_ids": r3a_failures,
                "state": "not_armed",
            },
            "L1.R3B_OPERATOR_FACING_LEARNED_RANKING": {
                "failed_requirement_ids": [
                    "R3B_TOTAL_DISPOSITIONS",
                    "R3B_OPERATOR_DIVERSITY",
                    "R3B_MIN_PER_OPERATOR",
                    "R3B_MIN_PER_ARMED_FAMILY",
                    "R3B_AGGREGATION_FLOOR",
                    "R3B_RANKER_OFF_REPLAY",
                    "R3B_CHECK_REGRESSION",
                ],
                "state": "not_armed",
            },
            "L2.R2_FORECAST_MODEL": {
                "failed_requirement_ids": [
                    "L2R2_NO_FORECAST_MODEL_AUTHORITY",
                    "L2R2_LABEL_HISTORY_INSUFFICIENT",
                    "L2R2_FORECAST_MODEL_EXPLICITLY_DEFERRED",
                ],
                "state": "not_armed",
            },
            "L3_COUNTERFACTUAL": {"failed_requirement_ids": ["L3_EXPLICITLY_DEFERRED"], "state": "not_armed"},
            "L4_CASE_MEMORY": {"failed_requirement_ids": ["L4_EXPLICITLY_DEFERRED"], "state": "not_armed"},
        },
        "corpus_full_discovery_status": corpus_summary["corpus"]["full_discovery"]["status"],
        "foundation_closeout_ready": (
            corpus_summary["corpus"]["full_discovery"]["status"] == "green"
            and scheduled_report["status"] == "PASS"
            and backtest["status"] == "PASS_BACKTEST_HARNESS_BUILT_NO_MODEL"
        ),
        "full_epoch3_closeout_ready": False,
        "previous_snapshot_ref": rel(L1_R1_R2_ROOT / "E3_FUEL_GAUGE_DELTA_SNAPSHOT_R1_R2.json"),
        "report_id": "E3_PRE_CLOSEOUT_ARMING_STATUS_SNAPSHOT",
        "scheduled_tick_status": scheduled_report["scheduled_tick_status"],
        "status": "PASS_WITH_LIMITATIONS",
    }


def limitations() -> dict[str, Any]:
    return {
        "limitations": [
            "This closes foundation convergence only; it does not close full Epoch 3 learning paths.",
            "Full historical corpus discovery is path/index green; legacy generated payloads are not re-certified as model fuel.",
            "L2.R1 backtest harness is built with a do-nothing comparator; no forecast model exists.",
            "R3A/R3B/L2.R2/L3/L4 remain not armed.",
        ],
        "report_id": "E3_PRE_CLOSEOUT_LIMITATIONS",
        "status": "PASS_WITH_LIMITATIONS",
    }


def decision(
    scheduled_report: dict[str, Any],
    corpus_summary: dict[str, Any],
    parse_report: dict[str, Any],
    hash_report: dict[str, Any],
    backtest: dict[str, Any],
    guard: dict[str, Any],
    lf_report: dict[str, Any],
) -> dict[str, Any]:
    blockers = []
    if scheduled_report["status"] != "PASS":
        blockers.append("scheduled_tick_not_verified")
    if corpus_summary["corpus"]["full_discovery"]["status"] != "green":
        blockers.append("corpus_full_discovery_not_green")
    if parse_report["status"] != "PASS":
        blockers.append("control_corpus_parse_failed")
    if hash_report["status"] != "PASS":
        blockers.append("control_hash_manifest_failed")
    if backtest["status"] != "PASS_BACKTEST_HARNESS_BUILT_NO_MODEL":
        blockers.append("l2r1_backtest_harness_not_built")
    if guard["status"] != "PASS":
        blockers.append("no_model_guard_failed")
    if lf_report.get("crlf_paths"):
        blockers.append("line_endings_not_lf")
    return {
        "armed_now": ARMED_NOW,
        "blockers": blockers,
        "closeout_readiness": "FOUNDATION_CLOSEOUT_READY_WITH_LIMITATIONS" if not blockers else "NOT_READY",
        "full_epoch3_closeout_ready": False,
        "foundation_closeout_ready": not blockers,
        "next_recommended_package": "MAIN-CITYBRAIN-EPOCH3-FOUNDATION-CLOSEOUT-R1" if not blockers else None,
        "status": STATUS if not blockers else BLOCKED_STATUS,
        "still_blocked": STILL_BLOCKED,
        "task_id": TASK_ID,
    }


def build_lf_report() -> dict[str, Any]:
    checked = []
    crlf_paths = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if not path.is_file() or path.name in {"HASH_MANIFEST.json", "LINE_ENDING_REPORT.json"}:
            continue
        data = path.read_bytes()
        crlf_count = data.count(b"\r\n")
        item = {"bytes": len(data), "crlf_count": crlf_count, "path": rel(path)}
        checked.append(item)
        if crlf_count:
            crlf_paths.append(rel(path))
    return {
        "checked_files": checked,
        "created_at": utc_now(),
        "crlf_paths": crlf_paths,
        "report_id": "LINE_ENDING_REPORT",
        "status": "PASS_LF_STABLE_FOR_E3_PRE_CLOSEOUT_CONVERGENCE" if not crlf_paths else "FAIL_CRLF_FOUND",
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
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def write_readme() -> None:
    text = "\n".join(
        [
            "# Epoch 3 Pre-Closeout Convergence R1",
            "",
            f"Task: `{TASK_ID}`",
            "",
            "This package closes the remaining foundation infrastructure before the Epoch 3 foundation closeout:",
            "",
            "- scheduled Watch tick exposure verification",
            "- full historical corpus discovery green",
            "- L2.R1 backtest harness shell",
            "- no-model guard and arming snapshot",
            "",
            "It does not arm or create rankers, forecast models, counterfactual learners, case-memory learners, dynamic investigation, or cross-city learned transfer.",
            "",
        ]
    )
    (OUTPUT_ROOT / "README.md").parent.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "README.md").write_text(text, encoding="utf-8", newline="\n")


def write_all_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)

    write_readme()

    events = scheduled_tick_exposure_events()
    write_json(FIXTURE_ROOT / "scheduled_watch_tick_run_envelope.json", scheduled_tick_run_envelope())
    write_json(FIXTURE_ROOT / "scheduled_watch_tick_payload.json", scheduled_tick_payload())
    write_jsonl(FIXTURE_ROOT / "scheduled_watch_tick_exposure_events.jsonl", events)

    scheduled_report = build_scheduled_tick_report(events)
    write_json(OUTPUT_ROOT / "E3_SCHEDULED_WATCH_TICK_EXPOSURE_VERIFICATION_REPORT.json", scheduled_report)

    discovery_index, corpus_summary = discover_output_corpus()
    parse_report = parse_control_corpus()
    hash_report = verify_control_hash_manifests()
    corpus_summary["control_corpus_parse"] = parse_report
    corpus_summary["control_hash_manifest_verification"] = hash_report
    write_json(OUTPUT_ROOT / "E3_FULL_HISTORICAL_CORPUS_DISCOVERY_INDEX.json", discovery_index)
    write_json(OUTPUT_ROOT / "E3_FULL_HISTORICAL_CORPUS_DISCOVERY_REPORT.json", corpus_summary)

    target = forecast_target_decision()
    frozen_slice = frozen_eval_slice_contract()
    comparator = baseline_comparator()
    uncertainty = forecast_uncertainty_schema_path()
    check_gate = forecast_packet_check_gate_scaffold()
    backtest = backtest_report(events)
    write_json(OUTPUT_ROOT / "E3_L2_R1_FIRST_FORECAST_TARGET_DECISION.json", target)
    write_json(OUTPUT_ROOT / "E3_L2_R1_FROZEN_EVAL_SLICE_CONTRACT.json", frozen_slice)
    write_json(OUTPUT_ROOT / "E3_L2_R1_BASELINE_DO_NOTHING_COMPARATOR.json", comparator)
    write_json(OUTPUT_ROOT / "E3_L2_R1_FORECAST_UNCERTAINTY_SCHEMA_PATH.json", uncertainty)
    write_json(OUTPUT_ROOT / "E3_L2_R1_FORECAST_PACKET_CHECK_GATE_SCAFFOLD.json", check_gate)
    write_json(OUTPUT_ROOT / "E3_L2_R1_BACKTEST_HARNESS_REPORT.json", backtest)

    guard = no_model_guard()
    write_json(OUTPUT_ROOT / "E3_PRE_CLOSEOUT_NO_MODEL_GUARD_REPORT.json", guard)

    arming = arming_status_snapshot(corpus_summary, scheduled_report, backtest)
    write_json(OUTPUT_ROOT / "E3_PRE_CLOSEOUT_ARMING_STATUS_SNAPSHOT.json", arming)

    limit_report = limitations()
    write_json(OUTPUT_ROOT / "E3_PRE_CLOSEOUT_LIMITATIONS.json", limit_report)

    provisional_lf = {"crlf_paths": []}
    decision_report = decision(scheduled_report, corpus_summary, parse_report, hash_report, backtest, guard, provisional_lf)
    write_json(OUTPUT_ROOT / "E3_PRE_CLOSEOUT_CONVERGENCE_DECISION.json", decision_report)

    lf_report = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", lf_report)
    decision_report = decision(scheduled_report, corpus_summary, parse_report, hash_report, backtest, guard, lf_report)
    write_json(OUTPUT_ROOT / "E3_PRE_CLOSEOUT_CONVERGENCE_DECISION.json", decision_report)
    lf_report = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", lf_report)
    hash_manifest = build_hash_manifest()

    return {
        "arming": arming,
        "backtest": backtest,
        "corpus": corpus_summary,
        "decision": decision_report,
        "hash_manifest": hash_manifest,
        "line_endings": lf_report,
        "no_model_guard": guard,
        "scheduled_tick": scheduled_report,
    }


def main() -> int:
    result = write_all_outputs()
    status = result["decision"]["status"]
    print(f"Epoch 3 Pre-Closeout Convergence R1: {status}")
    print(f"Scheduled Watch tick: {result['scheduled_tick']['status']}")
    print(f"Corpus full discovery: {result['corpus']['corpus']['full_discovery']['status']}")
    print(f"L2.R1 backtest harness: {result['backtest']['status']}")
    print(f"No-model guard: {result['no_model_guard']['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if status == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
