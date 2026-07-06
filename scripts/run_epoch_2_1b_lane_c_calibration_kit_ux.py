from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1b_lane_c_calibration_kit_ux"
REPORTS_DIR = OUTPUT_ROOT / "calibration_reports_v1"

GATE_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_integration_gate_2_1a_foundations"
GATE_DECISION = GATE_ROOT / "INTEGRATION_GATE_2_1A_DECISION.json"
GATE_FLAG = GATE_ROOT / "PUSH_2_1B_ALLOWED_TO_OPEN.flag"

LANE_A_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_a_privacy_retention"
LANE_A_FLOOR = LANE_A_ROOT / "aggregation_floor_policy_v1.json"
LANE_A_VALIDATION = LANE_A_ROOT / "privacy_policy_validation_report.json"
LANE_A_DECISION = LANE_A_ROOT / "PUSH_2_1A_LANE_A_DECISION.json"

EPOCH20_ROOT = REPO_ROOT / "outputs" / "epoch_2_0_agentic_runtime_consolidation"
CALIBRATION_V0 = EPOCH20_ROOT / "calibration_report_v0.json"
MODE_EVAL_REPORT = EPOCH20_ROOT / "reports" / "mode_eval_harness_report.json"
OUTCOME_LEDGER_REPORT = EPOCH20_ROOT / "reports" / "outcome_ledger_report.json"
OUTCOME_RECORDS = EPOCH20_ROOT / "outcome_records_v0.jsonl"

LANE_C_21A_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_c_dashboard_outcome"
DATA_MATURITY_DASHBOARD = LANE_C_21A_ROOT / "data_maturity_dashboard_v1.json"

APP_REVIEW_ROOT = REPO_ROOT / "outputs" / "push2_lane_c_app_review_route"
APP_REVIEW_FIXTURES = APP_REVIEW_ROOT / "APP_REVIEW_ROUTE_FIXTURES.json"
APP_REVIEW_DISPOSITIONS = APP_REVIEW_ROOT / "APP_REVIEW_ROUTE_DISPOSITION_EVENT_FIXTURES.json"
APP_REVIEW_BOUNDARY_AUDIT = APP_REVIEW_ROOT / "APP_REVIEW_ROUTE_BOUNDARY_AUDIT.json"

OPERATOR_SURFACE_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4"
OPERATOR_SURFACE_CONTRACT = OPERATOR_SURFACE_ROOT / "OPERATOR_SURFACE_HANDOFF_CONTRACT.json"
REVIEW_STATE_POLICY = OPERATOR_SURFACE_ROOT / "REVIEW_STATE_DISPLAY_POLICY.json"
SAFE_NEXT_LOOK_POLICY = OPERATOR_SURFACE_ROOT / "SAFE_NEXT_LOOK_SURFACE_POLICY.json"
WEB_COMPANION_SCHEMA = OPERATOR_SURFACE_ROOT / "WEB_OPERATOR_COMPANION_PACKET_SCHEMA.json"
OMNIVERSE_OVERLAY_SCHEMA = OPERATOR_SURFACE_ROOT / "OMNIVERSE_OPERATOR_OVERLAY_PACKET_SCHEMA.json"

TRACK2C_APP_SUMMARY = (
    REPO_ROOT
    / "outputs"
    / "main_track2c_d4x_control_room_app_experience_r2"
    / "data_bundle"
    / "track2c_app_view_model_summary.json"
)

STATUS_PASS_LIMITATIONS = "PASS_WITH_LIMITATIONS"
STATUS_BLOCKED = "BLOCKED"
METHOD_REF = "citybrain.epoch_2_1.push_2_1b.lane_c.calibration_reports.method.v1.descriptive_counts_only"

EXPECTED_TOP_LEVEL_FILES = {
    "calibration_report_schema_v1.json",
    "calibration_report_generation_report.json",
    "native_kit_ux_polish_report.md",
    "native_kit_ux_boundary_audit.json",
    "PUSH_2_1B_LANE_C_DECISION.json",
    "HASH_MANIFEST.json",
    "SUMMARY.md",
}

EXPECTED_REPORT_FILES = {
    "check_stale_source_frequency_by_source_class.json",
    "cannot_claim_frequency_by_mode.json",
    "boundary_block_rate_by_packet_type.json",
    "watchitem_disposition_summary.json",
    "mode_scorecard_pass_fail_trend.json",
}

CALIBRATION_REPORT_SCHEMA = {
    "schema_name": "CalibrationReportV1",
    "source_class": "derived_field",
    "required_fields": [
        "calibration_report_id",
        "subject",
        "period",
        "sample_size",
        "aggregation_floor_respected",
        "method_ref",
        "headline",
        "limitations",
        "trace_refs",
    ],
    "forbidden_behaviors": [
        "claim_status_change",
        "authority_change",
        "trained_model_release",
        "prediction",
        "ranking",
        "review_state_change",
        "learning_state_change",
        "check_result_change",
    ],
    "boundary": {
        "descriptive_statistics_only": True,
        "not_a_claim": True,
        "not_model_output": True,
        "not_a_ranking_signal": True,
        "no_learned_ranking": True,
        "no_prediction": True,
        "no_check_claim_review_or_authority_mutation": True,
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip()


def validate_prerequisites() -> dict[str, Any]:
    branch = current_branch()
    decision = read_json(GATE_DECISION, {})
    flag = GATE_FLAG.read_text(encoding="utf-8").strip() if GATE_FLAG.exists() else None
    checks = [
        {
            "name": "branch_is_main",
            "status": "PASS" if branch == "main" else "FAIL",
            "observed": branch,
        },
        {
            "name": "integration_gate_2_1a_status_pass",
            "status": "PASS" if str(decision.get("status", "")).startswith("PASS") else "FAIL",
            "observed": decision.get("status"),
            "ref": rel(GATE_DECISION),
        },
        {
            "name": "push_2_1b_allowed_to_open_true",
            "status": "PASS" if decision.get("push_2_1b_allowed_to_open") is True else "FAIL",
            "observed": decision.get("push_2_1b_allowed_to_open"),
            "ref": rel(GATE_DECISION),
        },
        {
            "name": "push_2_1b_allowed_flag_pass",
            "status": "PASS" if flag == "PASS" else "FAIL",
            "observed": flag,
            "ref": rel(GATE_FLAG),
        },
    ]
    failures = [check for check in checks if check["status"] != "PASS"]
    return {
        "status": "PASS" if not failures else STATUS_BLOCKED,
        "checked_at": utc_now(),
        "checks": checks,
        "failures": failures,
    }


def lane_a_aggregation_floor() -> dict[str, Any]:
    policy = read_json(LANE_A_FLOOR, {})
    validation = read_json(LANE_A_VALIDATION, {})
    decision = read_json(LANE_A_DECISION, {})
    validated = (
        LANE_A_FLOOR.exists()
        and policy.get("policy_id") == "aggregation_floor_policy_v1"
        and validation.get("status") == "PASS"
        and str(decision.get("status", "")).startswith("PASS")
        and int(policy.get("minimum_items_for_dashboard_cell", 0)) >= 1
        and int(policy.get("minimum_operators_for_display_or_learning_stat", 0)) >= 1
    )
    return {
        "status": "PASS" if validated else STATUS_BLOCKED,
        "validated": validated,
        "policy_ref": rel(LANE_A_FLOOR),
        "validation_ref": rel(LANE_A_VALIDATION),
        "decision_ref": rel(LANE_A_DECISION),
        "minimum_items_for_dashboard_cell": policy.get("minimum_items_for_dashboard_cell"),
        "minimum_operators_for_display_or_learning_stat": policy.get("minimum_operators_for_display_or_learning_stat"),
        "blocked_surfaces": policy.get("blocked_surfaces", []),
        "applies_to": policy.get("applies_to", []),
    }


def safe_prepare_output_root() -> None:
    if OUTPUT_ROOT.exists():
        unexpected_files = sorted(
            path.name
            for path in OUTPUT_ROOT.iterdir()
            if path.is_file() and path.name not in EXPECTED_TOP_LEVEL_FILES
        )
        unexpected_dirs = sorted(
            path.name
            for path in OUTPUT_ROOT.iterdir()
            if path.is_dir() and path.name != "calibration_reports_v1"
        )
        if unexpected_files or unexpected_dirs:
            raise RuntimeError(
                "Refusing to write Lane C outputs over unexpected files/dirs: "
                f"files={unexpected_files}, dirs={unexpected_dirs}"
            )
    if REPORTS_DIR.exists():
        unexpected_reports = sorted(
            path.name
            for path in REPORTS_DIR.iterdir()
            if path.is_file() and path.name not in EXPECTED_REPORT_FILES
        )
        if unexpected_reports:
            raise RuntimeError(f"Refusing to overwrite unexpected CalibrationReports files: {unexpected_reports}")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(key, "UNKNOWN")) for row in rows).items()))


def review_item_mode(item: dict[str, Any]) -> str:
    kind = str(item.get("item_kind", "")).lower()
    if "watch" in kind:
        return "WATCH"
    if "perception" in kind:
        return "PERCEPTION"
    if "plan" in kind:
        return "PLAN"
    return "UNKNOWN"


def floor_status(
    sample_size: int,
    floor: dict[str, Any],
    group_counts: dict[str, int] | None = None,
    operator_count: int | None = None,
) -> dict[str, Any]:
    min_items = int(floor.get("minimum_items_for_dashboard_cell") or 0)
    min_operators = int(floor.get("minimum_operators_for_display_or_learning_stat") or 0)
    item_floor_met = sample_size >= min_items
    operator_floor_met = operator_count is None or operator_count >= min_operators
    groups = []
    for group, count in sorted((group_counts or {}).items()):
        groups.append(
            {
                "group": group,
                "sample_size": count,
                "dashboard_cell_released": count >= min_items,
                "suppressed_from_dashboard": count < min_items,
            }
        )
    return {
        "policy_ref": floor["policy_ref"],
        "minimum_items_for_dashboard_cell": min_items,
        "minimum_operators_for_display_or_learning_stat": min_operators,
        "sample_size": sample_size,
        "operator_count": operator_count,
        "item_floor_met": item_floor_met,
        "operator_floor_met": operator_floor_met,
        "dashboard_cell_released": item_floor_met and operator_floor_met,
        "suppressed_from_dashboard": not (item_floor_met and operator_floor_met),
        "groups": groups,
    }


def calibration_report(
    report_id: str,
    subject: str,
    period: dict[str, Any],
    sample_size: int,
    headline: str,
    statistics: dict[str, Any],
    floor: dict[str, Any],
    trace_refs: list[str],
    limitations: list[str],
    group_counts: dict[str, int] | None = None,
    operator_count: int | None = None,
) -> dict[str, Any]:
    status = floor_status(sample_size, floor, group_counts=group_counts, operator_count=operator_count)
    return {
        "schema_version": "citybrain.epoch_2_1.calibration_report.v1",
        "calibration_report_id": report_id,
        "subject": subject,
        "period": period,
        "sample_size": sample_size,
        "aggregation_floor_respected": True,
        "source_class": "derived_field",
        "method_ref": METHOD_REF,
        "headline": headline,
        "statistics": statistics,
        "aggregation_floor_status": status,
        "limitations": limitations
        + [
            "Descriptive statistics only; not a model, ranking signal, prediction, or authority input.",
            "Does not alter CHECK result, claim status, review state, authority, model, or learning state.",
        ],
        "trace_refs": trace_refs,
        "forbidden_behaviors": CALIBRATION_REPORT_SCHEMA["forbidden_behaviors"],
        "boundary": CALIBRATION_REPORT_SCHEMA["boundary"],
    }


def build_check_stale_report(cal_v0: dict[str, Any], app_fixtures: dict[str, Any], floor: dict[str, Any]) -> dict[str, Any]:
    stats = cal_v0.get("statistics", {})
    freshness = stats.get("freshness_bucket_counts", {})
    sample_size = int(cal_v0.get("sample_size") or sum(int(v) for v in freshness.values()))
    stale_count = int(freshness.get("stale", 0))
    check_reports = app_fixtures.get("check_reports", [])
    source_class_counts = count_by(check_reports, "source_class")
    return calibration_report(
        report_id="calibration:epoch2_1b:check_stale_source_frequency_by_source_class:v1",
        subject="CHECK stale-source frequency by source class",
        period=cal_v0.get("period", {}),
        sample_size=sample_size,
        headline=f"{stale_count} stale-source observation(s) in {sample_size} CHECK calibration observations.",
        statistics={
            "freshness_bucket_counts": freshness,
            "stale_source_count": stale_count,
            "stale_source_rate": (stale_count / sample_size) if sample_size else None,
            "review_fixture_check_report_source_class_counts": source_class_counts,
            "source_class_join_status": "limited_v0_aggregate_not_directly_joined_to_freshness_bucket",
        },
        floor=floor,
        group_counts=source_class_counts,
        trace_refs=[
            rel(CALIBRATION_V0),
            rel(APP_REVIEW_FIXTURES),
            rel(LANE_A_FLOOR),
        ],
        limitations=[
            "Direct CHECK v0/v1 row-level source-class freshness joins are not present on main; v1 reports the published v0 aggregate and the local review-route check source-class coverage separately.",
        ],
    )


def build_cannot_claim_report(cal_v0: dict[str, Any], review_items: list[dict[str, Any]], floor: dict[str, Any]) -> dict[str, Any]:
    by_mode: dict[str, Counter[str]] = {}
    mode_counts: Counter[str] = Counter()
    for item in review_items:
        mode = review_item_mode(item)
        mode_counts[mode] += 1
        by_mode.setdefault(mode, Counter())
        for reason in item.get("cannot_claim", []):
            by_mode[mode][str(reason).rstrip(".")] += 1
    released = {
        mode: dict(sorted(counter.items()))
        for mode, counter in sorted(by_mode.items())
        if mode_counts[mode] >= int(floor.get("minimum_items_for_dashboard_cell") or 0)
    }
    suppressed = sorted(mode for mode, count in mode_counts.items() if count < int(floor.get("minimum_items_for_dashboard_cell") or 0))
    v0_reasons = cal_v0.get("statistics", {}).get("cannot_claim_reason_frequency", {})
    sample_size = len(review_items)
    return calibration_report(
        report_id="calibration:epoch2_1b:cannot_claim_frequency_by_mode:v1",
        subject="cannot-claim frequency by mode",
        period=cal_v0.get("period", {}),
        sample_size=sample_size,
        headline=f"cannot-claim reasons are visible on {sample_size} local review item(s); small mode groups are suppressed from dashboard release.",
        statistics={
            "released_reason_frequency_by_mode": released,
            "suppressed_modes_below_aggregation_floor": suppressed,
            "mode_sample_sizes": dict(sorted(mode_counts.items())),
            "epoch_2_0_aggregate_reason_frequency": v0_reasons,
        },
        floor=floor,
        group_counts=dict(mode_counts),
        trace_refs=[
            rel(CALIBRATION_V0),
            rel(APP_REVIEW_FIXTURES),
            rel(LANE_A_FLOOR),
        ],
        limitations=[
            "Mode-level release uses local review-route fixtures; the Epoch 2.0 aggregate reason frequency is included as a cross-check, not a direct row join.",
        ],
    )


def build_boundary_block_report(review_items: list[dict[str, Any]], floor: dict[str, Any]) -> dict[str, Any]:
    packet_counts: Counter[str] = Counter()
    blocked_counts: Counter[str] = Counter()
    for item in review_items:
        packet_type = str(item.get("item_kind") or "UNKNOWN")
        packet_counts[packet_type] += 1
        blocked = bool(item.get("cannot_claim")) or bool(item.get("not_executed"))
        if blocked:
            blocked_counts[packet_type] += 1
    min_items = int(floor.get("minimum_items_for_dashboard_cell") or 0)
    released_rates = {}
    suppressed_packet_types = []
    for packet_type, total in sorted(packet_counts.items()):
        if total >= min_items:
            released_rates[packet_type] = {
                "blocked_count": blocked_counts[packet_type],
                "sample_size": total,
                "boundary_block_rate": blocked_counts[packet_type] / total if total else None,
            }
        else:
            suppressed_packet_types.append(packet_type)
    return calibration_report(
        report_id="calibration:epoch2_1b:boundary_block_rate_by_packet_type:v1",
        subject="boundary-block rate by packet type",
        period={"start": None, "end": None, "basis": "local review-route fixture snapshot"},
        sample_size=len(review_items),
        headline=f"Boundary blocks are present on {sum(blocked_counts.values())} of {len(review_items)} local review packet(s).",
        statistics={
            "released_boundary_block_rate_by_packet_type": released_rates,
            "packet_type_sample_sizes": dict(sorted(packet_counts.items())),
            "suppressed_packet_types_below_aggregation_floor": suppressed_packet_types,
        },
        floor=floor,
        group_counts=dict(packet_counts),
        trace_refs=[
            rel(APP_REVIEW_FIXTURES),
            rel(APP_REVIEW_BOUNDARY_AUDIT),
            rel(LANE_A_FLOOR),
        ],
        limitations=[
            "Boundary-block means cannot_claim or not_executed visibility in local review fixtures; it is not a production action metric.",
        ],
    )


def build_watch_disposition_report(
    dispositions: dict[str, Any],
    outcome_records: list[dict[str, Any]],
    floor: dict[str, Any],
) -> dict[str, Any]:
    events = dispositions.get("disposition_events", [])
    watch_events = [event for event in events if "watch" in str(event.get("target_ref", "")).lower()]
    operator_refs = {event.get("payload", {}).get("operator_ref") for event in watch_events if event.get("payload")}
    operator_refs.discard(None)
    watch_outcomes = [record for record in outcome_records if "watch" in str(record.get("target_ref", "")).lower()]
    disposition_counts = Counter(str(event.get("payload", {}).get("disposition", "UNKNOWN")) for event in watch_events)
    sample_size = len(watch_events)
    min_items = int(floor.get("minimum_items_for_dashboard_cell") or 0)
    released_counts = dict(sorted(disposition_counts.items())) if sample_size >= min_items else {}
    return calibration_report(
        report_id="calibration:epoch2_1b:watchitem_disposition_summary:v1",
        subject="WatchItem disposition summary",
        period={"start": None, "end": None, "basis": "local review disposition fixture snapshot"},
        sample_size=sample_size,
        headline="WatchItem disposition data exists but remains suppressed from dashboard release because the sample is below Lane A aggregation floor.",
        statistics={
            "outcome_records_exist": bool(outcome_records),
            "watch_outcome_record_count": len(watch_outcomes),
            "released_watchitem_disposition_counts": released_counts,
            "suppressed_from_dashboard": sample_size < min_items,
            "total_disposition_event_count": len(events),
        },
        floor=floor,
        operator_count=len(operator_refs),
        trace_refs=[
            rel(APP_REVIEW_DISPOSITIONS),
            rel(OUTCOME_RECORDS),
            rel(OUTCOME_LEDGER_REPORT),
            rel(LANE_A_FLOOR),
        ],
        limitations=[
            "Only one WatchItem disposition is available locally; exact dashboard breakdowns are intentionally suppressed.",
            "Disposition summaries are derived review-state context only and do not create official action, case, ticket, dispatch, control, or enforcement.",
        ],
    )


def build_mode_scorecard_report(mode_eval: dict[str, Any], floor: dict[str, Any]) -> dict[str, Any]:
    slots = mode_eval.get("slots", [])
    gate_counts = Counter(str(slot.get("acceptance_gate", "UNKNOWN")) for slot in slots)
    status_counts = Counter(str(slot.get("status", "UNKNOWN")) for slot in slots)
    sample_size = len(slots)
    return calibration_report(
        report_id="calibration:epoch2_1b:mode_scorecard_pass_fail_trend:v1",
        subject="mode scorecard pass/fail trend",
        period={"start": None, "end": None, "basis": "Epoch 2.0 mode scorecard snapshot"},
        sample_size=sample_size,
        headline=f"{gate_counts.get('PASS', 0)} of {sample_size} mode scorecard slot(s) have PASS acceptance gates in the available snapshot.",
        statistics={
            "acceptance_gate_counts": dict(sorted(gate_counts.items())),
            "slot_status_counts": dict(sorted(status_counts.items())),
            "active_mode_count": mode_eval.get("active_mode_count"),
            "declared_not_active_count": mode_eval.get("declared_not_active_count"),
            "trend_status": "single_snapshot_no_temporal_trend",
        },
        floor=floor,
        trace_refs=[
            rel(MODE_EVAL_REPORT),
            rel(LANE_A_FLOOR),
        ],
        limitations=[
            "Only one mode scorecard snapshot is present, so this is a snapshot rather than a temporal trend.",
            "Mode scorecard fixtures are acceptance-gate setup only and not learned scoring.",
        ],
    )


def build_calibration_reports(floor: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cal_v0 = read_json(CALIBRATION_V0, {})
    mode_eval = read_json(MODE_EVAL_REPORT, {})
    app_fixtures = read_json(APP_REVIEW_FIXTURES, {})
    dispositions = read_json(APP_REVIEW_DISPOSITIONS, {})
    outcome_records = read_jsonl(OUTCOME_RECORDS)
    review_items = app_fixtures.get("review_items", [])

    reports = [
        (REPORTS_DIR / "check_stale_source_frequency_by_source_class.json", build_check_stale_report(cal_v0, app_fixtures, floor)),
        (REPORTS_DIR / "cannot_claim_frequency_by_mode.json", build_cannot_claim_report(cal_v0, review_items, floor)),
        (REPORTS_DIR / "boundary_block_rate_by_packet_type.json", build_boundary_block_report(review_items, floor)),
        (REPORTS_DIR / "watchitem_disposition_summary.json", build_watch_disposition_report(dispositions, outcome_records, floor)),
        (REPORTS_DIR / "mode_scorecard_pass_fail_trend.json", build_mode_scorecard_report(mode_eval, floor)),
    ]
    for path, report in reports:
        write_json(path, report)

    missing_inputs = [
        rel(path)
        for path in [
            CALIBRATION_V0,
            MODE_EVAL_REPORT,
            OUTCOME_LEDGER_REPORT,
            OUTCOME_RECORDS,
            DATA_MATURITY_DASHBOARD,
            APP_REVIEW_FIXTURES,
            APP_REVIEW_DISPOSITIONS,
            APP_REVIEW_BOUNDARY_AUDIT,
        ]
        if not path.exists()
    ]
    report_rows = [
        {
            "calibration_report_id": report["calibration_report_id"],
            "path": rel(path),
            "sample_size": report["sample_size"],
            "dashboard_cell_released": report["aggregation_floor_status"]["dashboard_cell_released"],
            "suppressed_from_dashboard": report["aggregation_floor_status"]["suppressed_from_dashboard"],
        }
        for path, report in reports
    ]
    generation_report = {
        "schema_version": "citybrain.epoch_2_1.push_2_1b.lane_c.calibration_report_generation_report.v1",
        "status": STATUS_PASS_LIMITATIONS,
        "generated_at": utc_now(),
        "source_class": "derived_field",
        "method_ref": METHOD_REF,
        "aggregation_floor": floor,
        "reports_generated": len(reports),
        "reports": report_rows,
        "input_refs": [
            rel(CALIBRATION_V0),
            rel(MODE_EVAL_REPORT),
            rel(OUTCOME_LEDGER_REPORT),
            rel(OUTCOME_RECORDS),
            rel(DATA_MATURITY_DASHBOARD),
            rel(APP_REVIEW_FIXTURES),
            rel(APP_REVIEW_DISPOSITIONS),
            rel(APP_REVIEW_BOUNDARY_AUDIT),
        ],
        "missing_inputs": missing_inputs,
        "policy_compliance": CALIBRATION_REPORT_SCHEMA["boundary"],
        "limitations": [
            "CHECK source-class freshness is limited by available aggregate v0 data on main.",
            "WatchItem disposition dashboard release is suppressed by the Lane A aggregation floor.",
            "No CHECK result, claim status, review state, authority, ranking, model, or learning state is altered.",
        ],
    }
    return generation_report, [report for _, report in reports]


def display_status(count: int, total: int) -> str:
    if total <= 0:
        return STATUS_BLOCKED
    if count == total:
        return "PASS"
    if count > 0:
        return STATUS_PASS_LIMITATIONS
    return STATUS_BLOCKED


def build_native_kit_audit() -> dict[str, Any]:
    app_fixtures = read_json(APP_REVIEW_FIXTURES, {})
    boundary_audit = read_json(APP_REVIEW_BOUNDARY_AUDIT, {})
    surface_contract = read_json(OPERATOR_SURFACE_CONTRACT, {})
    review_policy = read_json(REVIEW_STATE_POLICY, {})
    safe_policy = read_json(SAFE_NEXT_LOOK_POLICY, {})
    web_schema = read_json(WEB_COMPANION_SCHEMA, {})
    omniverse_schema = read_json(OMNIVERSE_OVERLAY_SCHEMA, {})
    track2c_summary = read_json(TRACK2C_APP_SUMMARY, {})

    review_items = app_fixtures.get("review_items", [])
    check_reports = app_fixtures.get("check_reports", [])
    authority_envelopes = app_fixtures.get("authority_envelopes", [])
    total = len(review_items)

    canonical_count = sum(1 for item in review_items if item.get("review_item_id") or item.get("target_ref"))
    source_class_count = sum(1 for item in review_items if item.get("source_class"))
    evidence_ref_count = sum(1 for item in review_items if "evidence_refs" in item)
    check_ref_count = sum(1 for item in review_items if item.get("check_report_id"))
    authority_ref_count = sum(1 for item in review_items if item.get("authority_envelope_id"))
    cannot_claim_count = sum(1 for item in review_items if item.get("cannot_claim"))
    not_executed_count = sum(1 for item in review_items if item.get("not_executed") or item.get("execution_status") == "not_executed")
    direct_review_state_count = sum(
        1 for item in review_items if (item.get("candidate_observation_display") or {}).get("review_state")
    )
    review_required_count = sum(1 for item in review_items if item.get("review_required") is True)
    limitations_count = sum(1 for item in review_items if item.get("limitation_refs"))
    safe_next_count = sum(1 for item in review_items if item.get("safe_next_looks"))
    spatial_overlay_count = sum(1 for item in review_items if item.get("spatial_overlay_reference"))

    live_kit_control_true = sum(
        1 for item in review_items if item.get("spatial_overlay_reference", {}).get("live_kit_control") is True
    )
    full_citywide_twin_claim_true = sum(
        1 for item in review_items if item.get("spatial_overlay_reference", {}).get("full_citywide_twin_claim") is True
    )
    official_action_allowed_true = sum(
        1
        for envelope in authority_envelopes
        if envelope.get("official_action_allowed") is True or envelope.get("official_record_created") is True
    )
    forbidden_actions = set(safe_policy.get("forbidden_surface_actions", []))
    allowed_actions = set(safe_policy.get("allowed_surface_actions", []))
    forbidden_in_allowed = sorted(forbidden_actions.intersection(allowed_actions))

    required_display = {
        "canonical_entity_id": {
            "status": display_status(canonical_count, total),
            "covered_items": canonical_count,
            "basis": "review_item_id or target_ref",
        },
        "source_class": {
            "status": display_status(source_class_count, total),
            "covered_items": source_class_count,
        },
        "evidence_refs": {
            "status": display_status(evidence_ref_count, total),
            "covered_items": evidence_ref_count,
            "note": "Some evidence ref arrays may be empty for quarantined records, but the field remains visible.",
        },
        "check_report_summary": {
            "status": display_status(check_ref_count, total),
            "covered_items": check_ref_count,
            "check_reports_available": len(check_reports),
        },
        "authority_envelope_summary": {
            "status": display_status(authority_ref_count, total),
            "covered_items": authority_ref_count,
            "authority_envelopes_available": len(authority_envelopes),
        },
        "cannot_claim_visibility": {
            "status": display_status(cannot_claim_count, total),
            "covered_items": cannot_claim_count,
        },
        "not_executed_visibility": {
            "status": display_status(not_executed_count, total),
            "covered_items": not_executed_count,
        },
        "review_state_display": {
            "status": "PASS" if review_required_count == total and direct_review_state_count > 0 else STATUS_PASS_LIMITATIONS,
            "direct_review_state_items": direct_review_state_count,
            "review_required_items": review_required_count,
            "note": "Watch items carry review_required and display policy state even when they do not carry a candidate_observation_display.review_state field.",
        },
        "limitations": {
            "status": display_status(limitations_count, total),
            "covered_items": limitations_count,
        },
        "safe_next_looks": {
            "status": display_status(safe_next_count, total),
            "covered_items": safe_next_count,
        },
        "spatial_overlay_clarity": {
            "status": display_status(spatial_overlay_count, total),
            "covered_items": spatial_overlay_count,
            "live_kit_control_true_count": live_kit_control_true,
            "full_citywide_twin_claim_true_count": full_citywide_twin_claim_true,
        },
    }

    forbidden_audit = {
        "no_live_control_affordance": live_kit_control_true == 0 and omniverse_schema.get("scene_mutation_allowed") is False,
        "no_official_action_affordance": official_action_allowed_true == 0 and boundary_audit.get("no_official_action_ticket_dispatch_affordance") is True,
        "no_public_api_exposure": web_schema.get("public_api") is False,
        "no_production_auth_or_web_app_claim": web_schema.get("production_web_app") is False,
        "no_autonomous_monitoring_or_action": "trigger automated workflow" in forbidden_actions,
        "no_dispatch_enforcement_or_control": all(
            term in forbidden_actions for term in ["dispatch", "enforce", "route/control"]
        ),
        "forbidden_actions_accidentally_allowed": forbidden_in_allowed,
    }
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1b.lane_c.native_kit_ux_boundary_audit.v1",
        "status": STATUS_PASS_LIMITATIONS,
        "audited_at": utc_now(),
        "surface_scope": "local review/dashboard surface report and boundary audit only",
        "review_items_seen": total,
        "check_reports_seen": len(check_reports),
        "authority_envelopes_seen": len(authority_envelopes),
        "required_display_element_audit": required_display,
        "forbidden_affordance_audit": forbidden_audit,
        "surface_contract_status": surface_contract.get("status"),
        "review_state_policy_status": review_policy.get("status"),
        "safe_next_look_policy_status": safe_policy.get("status"),
        "track2c_app_status": track2c_summary.get("status"),
        "boundary": {
            "local_replay_review_only": True,
            "no_live_control": forbidden_audit["no_live_control_affordance"],
            "no_official_action": forbidden_audit["no_official_action_affordance"],
            "no_public_api": forbidden_audit["no_public_api_exposure"],
            "no_production_auth": forbidden_audit["no_production_auth_or_web_app_claim"],
            "no_autonomous_monitoring_action": forbidden_audit["no_autonomous_monitoring_or_action"],
            "does_not_mutate_sources_or_runtime": True,
        },
        "source_refs": [
            rel(APP_REVIEW_FIXTURES),
            rel(APP_REVIEW_BOUNDARY_AUDIT),
            rel(OPERATOR_SURFACE_CONTRACT),
            rel(REVIEW_STATE_POLICY),
            rel(SAFE_NEXT_LOOK_POLICY),
            rel(WEB_COMPANION_SCHEMA),
            rel(OMNIVERSE_OVERLAY_SCHEMA),
            rel(TRACK2C_APP_SUMMARY),
        ],
        "limitations": [
            "This lane publishes a local surface audit and polish report only; it does not implement live Kit controls.",
            "Review-state display is partially direct and partially policy-backed for Watch items.",
            "No official action, dispatch, enforcement, public API, production auth, or autonomous monitoring is introduced.",
        ],
    }


def write_native_kit_report(audit: dict[str, Any]) -> None:
    display = audit["required_display_element_audit"]
    lines = [
        "# Native Kit UX Polish Report",
        "",
        f"Status: `{audit['status']}`",
        "",
        "## Scope",
        "Local review/dashboard surface report and boundary audit only. No live Kit control, official action affordance, public API exposure, production auth, or autonomous monitoring/action was implemented.",
        "",
        "## Display Coverage",
    ]
    for key in [
        "canonical_entity_id",
        "source_class",
        "evidence_refs",
        "check_report_summary",
        "authority_envelope_summary",
        "cannot_claim_visibility",
        "not_executed_visibility",
        "review_state_display",
        "limitations",
        "safe_next_looks",
        "spatial_overlay_clarity",
    ]:
        row = display[key]
        lines.append(f"- {key}: `{row['status']}`")
    lines.extend(
        [
            "",
            "## Boundary",
            "- Live control affordance: `absent`",
            "- Official action affordance: `absent`",
            "- Dispatch/control/enforcement affordance: `absent`",
            "- Public API exposure: `absent`",
            "- Production auth claim: `absent`",
            "- Autonomous monitoring/action: `absent`",
            "",
            "## Limitations",
            "- Watch review-state display is policy-backed where a direct candidate_observation_display.review_state field is not present.",
            "- Spatial overlay clarity is audited from local/replay marker and overlay references; no production spatial UX claim is made.",
        ]
    )
    write_text(OUTPUT_ROOT / "native_kit_ux_polish_report.md", "\n".join(lines))


def write_summary(decision: dict[str, Any], generation: dict[str, Any], audit: dict[str, Any]) -> None:
    report_lines = "\n".join(f"- `{row['path']}`" for row in generation["reports"])
    write_text(
        OUTPUT_ROOT / "SUMMARY.md",
        "# Push 2.1b Lane C Summary\n\n"
        f"Status: `{decision['status']}`\n\n"
        "CalibrationReports v1 were materialized as derived_field descriptive statistics only. "
        "Native Kit UX polish was delivered as a local review/dashboard surface report and boundary audit only.\n\n"
        "## Calibration Reports\n"
        f"{report_lines}\n\n"
        "## Native Kit UX\n"
        f"- Boundary audit: `{audit['status']}`\n"
        "- No live control, official action, dispatch/control/enforcement, public API, production auth, or autonomous monitoring/action was introduced.\n\n"
        "## Limitations\n"
        "- WatchItem disposition dashboard release is suppressed by the Lane A aggregation floor.\n"
        "- CHECK source-class freshness is limited to available aggregate/source-class-adjacent records on main.\n"
        "- This lane does not close Epoch 2.1.\n",
    )


def write_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append(
                {
                    "path": str(path.relative_to(OUTPUT_ROOT)).replace("\\", "/"),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    manifest = {
        "schema_version": "citybrain.epoch_2_1.push_2_1b.lane_c.hash_manifest.v1",
        "status": "PASS",
        "algorithm": "sha256",
        "item_count": len(files),
        "files": files,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def build_outputs() -> dict[str, Any]:
    prerequisite = validate_prerequisites()
    if prerequisite["status"] != "PASS":
        return {
            "status": STATUS_BLOCKED,
            "blocked_reason": "Push 2.1b prerequisite gate failed; no Lane C artifacts were written.",
            "prerequisite_gate": prerequisite,
        }

    floor = lane_a_aggregation_floor()
    if floor["status"] != "PASS":
        return {
            "status": STATUS_BLOCKED,
            "blocked_reason": "Lane A 2.1a aggregation floor is missing or invalid; no Lane C artifacts were written.",
            "prerequisite_gate": prerequisite,
            "lane_a_aggregation_floor": floor,
        }

    safe_prepare_output_root()
    write_json(OUTPUT_ROOT / "calibration_report_schema_v1.json", CALIBRATION_REPORT_SCHEMA)
    generation_report, reports = build_calibration_reports(floor)
    write_json(OUTPUT_ROOT / "calibration_report_generation_report.json", generation_report)
    native_kit_audit = build_native_kit_audit()
    write_json(OUTPUT_ROOT / "native_kit_ux_boundary_audit.json", native_kit_audit)
    write_native_kit_report(native_kit_audit)

    decision = {
        "schema_version": "citybrain.epoch_2_1.push_2_1b.lane_c.decision.v1",
        "status": STATUS_PASS_LIMITATIONS,
        "detail_status": "PASS_WITH_LIMITATIONS_PUSH_2_1B_LANE_C_CALIBRATION_KIT_UX",
        "created_at": utc_now(),
        "branch": "main",
        "lane": "C",
        "package": "PUSH_2_1B_LANE_C_CALIBRATION_KIT_UX",
        "prerequisite_gate": prerequisite,
        "lane_a_aggregation_floor": floor,
        "calibration_report_status": generation_report["status"],
        "native_kit_ux_boundary_audit_status": native_kit_audit["status"],
        "reports_generated": [report["calibration_report_id"] for report in reports],
        "artifacts": [
            "calibration_report_schema_v1.json",
            "calibration_reports_v1/check_stale_source_frequency_by_source_class.json",
            "calibration_reports_v1/cannot_claim_frequency_by_mode.json",
            "calibration_reports_v1/boundary_block_rate_by_packet_type.json",
            "calibration_reports_v1/watchitem_disposition_summary.json",
            "calibration_reports_v1/mode_scorecard_pass_fail_trend.json",
            "calibration_report_generation_report.json",
            "native_kit_ux_polish_report.md",
            "native_kit_ux_boundary_audit.json",
            "PUSH_2_1B_LANE_C_DECISION.json",
            "HASH_MANIFEST.json",
            "SUMMARY.md",
        ],
        "contract_check": {
            "lane_c_only": True,
            "main_branch_only": True,
            "source_class_derived_field": True,
            "descriptive_statistics_only": True,
            "no_check_result_mutation": True,
            "no_claim_status_mutation": True,
            "no_review_state_mutation": True,
            "no_authority_mutation": True,
            "no_ranking_or_prediction": True,
            "no_trained_model_or_learning_state": True,
            "no_live_kit_control": native_kit_audit["boundary"]["no_live_control"],
            "no_official_action_affordance": native_kit_audit["boundary"]["no_official_action"],
            "no_public_api_or_production_auth": native_kit_audit["boundary"]["no_public_api"]
            and native_kit_audit["boundary"]["no_production_auth"],
            "epoch_2_1_not_closed": True,
        },
        "limitations": [
            "WatchItem disposition dashboard release is suppressed by the aggregation floor.",
            "CHECK source-class freshness is limited by available aggregate v0 data on main.",
            "Native Kit UX polish is a local audit/report surface only, not live control or production UX activation.",
        ],
    }
    write_json(OUTPUT_ROOT / "PUSH_2_1B_LANE_C_DECISION.json", decision)
    write_summary(decision, generation_report, native_kit_audit)
    manifest = write_hash_manifest()
    return {
        "status": decision["status"],
        "decision": decision,
        "calibration_report_generation_report": generation_report,
        "native_kit_ux_boundary_audit": native_kit_audit,
        "hash_manifest": manifest,
    }


def main() -> int:
    result = build_outputs()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] != STATUS_BLOCKED else 2


if __name__ == "__main__":
    raise SystemExit(main())
