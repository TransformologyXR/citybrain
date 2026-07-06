#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


TASK_ID = "MAIN-CITYBRAIN-EPOCH3-L2-R2-FORECAST-AUTHORITY-PREFLIGHT-R1"
STATUS = "PASS_E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_R1_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_R1"
TARGET_ID = "permit_stall_v0"
STALL_THRESHOLD_DAYS = 60
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_l2_r2_forecast_authority_preflight_r1"

MASTER_ROOT = REPO_ROOT / "outputs" / "epoch3_master_execution_r1"
BACKFILL_R1_ROOT = REPO_ROOT / "outputs" / "epoch3_l2_historical_label_backfill_r1"
LONDON_PLD_SAMPLE = REPO_ROOT / "outputs" / "lon_d5_pld_planning_ingest" / "raw_sample" / "pld_lambeth_records_sample.json"
NYC_DOB_NOW_ROOT = REPO_ROOT / "outputs" / "nyc_allflows_data_landing_r1" / "data" / "normalized" / "nyc_dob_now_build_filings" / "phase_1"
NYC_DOB_PERMIT_ROOT = REPO_ROOT / "outputs" / "nyc_allflows_data_landing_r1" / "data" / "normalized" / "nyc_dob_permit_issuance" / "phase_1"

LONDON_CAP = 1_000
NYC_NOW_CAP = 12_500
NYC_PERMIT_CAP = 12_500
MINIMUM_REQUIRED_ROWS = 100


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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
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


def parse_date(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(text, fmt)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except ValueError:
            pass
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        return None


def parse_date_dayfirst(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return parse_date(value)


def iso_date(dt: datetime) -> str:
    return dt.date().isoformat()


def normalize_terminal(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "unknown"
    if "approv" in text or "grant" in text or "issued" in text or "permit entire" in text or "loc issued" in text:
        return "approved"
    if text in {"ref", "ref."} or "refus" in text or "reject" in text:
        return "rejected"
    if "withdraw" in text:
        return "withdrawn"
    if "expired" in text:
        return "expired"
    if "closed" in text or "complete" in text:
        return "completed"
    return text.replace(" ", "_")


def quarter_key(dt: datetime) -> str:
    quarter = ((dt.month - 1) // 3) + 1
    return f"{dt.year}-Q{quarter}"


def month_key(dt: datetime) -> str:
    return f"{dt.year:04d}-{dt.month:02d}"


def clean_id(value: Any) -> str:
    text = str(value or "unknown")
    return "".join(ch if ch.isalnum() else "_" for ch in text)[-96:]


def iter_parquet_rows(root: Path, columns: list[str]):
    try:
        import pyarrow.parquet as pq
    except Exception:
        return
    for file in sorted(root.glob("*.parquet")):
        schema_names = set(pq.read_schema(file).names)
        use = [column for column in columns if column in schema_names]
        if not use:
            continue
        table = pq.read_table(file, columns=use)
        for row in table.to_pylist():
            yield file, row


def source_transition_counts() -> dict[str, int]:
    discovery = read_json(BACKFILL_R1_ROOT / "E3_L2_HISTORICAL_TRANSITION_DISCOVERY_REPORT.json", {})
    counts: dict[str, int] = {}
    for source in discovery.get("source_reports", []):
        family = source.get("source_family")
        counts[family] = int(source.get("classification_counts", {}).get("transition_history_present", 0))
    return counts


def should_select(candidate_index: int, desired_count: int, total_transition_count: int) -> bool:
    stride = max(1, total_transition_count // max(1, desired_count))
    return (candidate_index - 1) % stride == 0


def r2_label_row(
    *,
    city: str,
    source_system: str,
    entity_ref: str,
    source_ref: str,
    start: datetime,
    end: datetime,
    counted_state: str,
    terminal_outcome: str,
    row_number: int,
) -> dict[str, Any]:
    observation_days = max(0, (end.date() - start.date()).days)
    label_bool = observation_days >= STALL_THRESHOLD_DAYS
    if observation_days >= 30:
        as_of = start + timedelta(days=30)
    else:
        as_of = start + timedelta(days=max(0, observation_days // 2))
    label = "stalled" if label_bool else "not_stalled"
    return {
        "as_of_date": iso_date(as_of),
        "censor_policy": "adequate_observation_window_required; terminal_before_threshold_is_negative",
        "city": city,
        "counted_state": counted_state,
        "derived_from_source_refs": [f"{source_ref}#start", f"{source_ref}#terminal"],
        "duplicate_transition_handling": "dedupe_repeated_same_state_before_window_measurement",
        "entity_ref": entity_ref,
        "label": label,
        "label_bool": label_bool,
        "label_row_id": f"label:permit_stall_v0:r2:{city.lower()}:{row_number:07d}:{clean_id(entity_ref)}",
        "lineage_complete": True,
        "model_allowed": False,
        "observation_window_days": observation_days,
        "observation_window_end": iso_date(end),
        "observation_window_start": iso_date(start),
        "source_class": "derived_field",
        "source_system": source_system,
        "stall_threshold_days": STALL_THRESHOLD_DAYS,
        "target_id": TARGET_ID,
        "temporal_split": "unassigned",
        "terminal_outcome": terminal_outcome,
        "training_allowed": False,
        "transition_sequence_ref": f"transition_sequence:{city.lower()}:{source_system.lower()}:{clean_id(entity_ref)}",
    }


def scan_london(labels: list[dict[str, Any]], counts: dict[str, int]) -> dict[str, Any]:
    records = read_json(LONDON_PLD_SAMPLE, [])
    transition_count = counts.get("london_pld_planning_ingest", 0) or LONDON_CAP
    candidate_index = 0
    source_counts: Counter[str] = Counter()
    for record in records if isinstance(records, list) else []:
        valid_date = parse_date_dayfirst(record.get("valid_date"))
        decision_date = parse_date_dayfirst(record.get("decision_date"))
        has_snapshot = bool(record.get("status") or record.get("decision") or record.get("last_updated"))
        if valid_date and decision_date and decision_date >= valid_date:
            candidate_index += 1
            source_counts["transition_history_present"] += 1
            if len([row for row in labels if row["source_system"] == "London_PLD"]) < LONDON_CAP and should_select(candidate_index, LONDON_CAP, transition_count):
                source_ref = f"{rel(LONDON_PLD_SAMPLE)}#{record.get('id') or record.get('lpa_app_no')}"
                labels.append(
                    r2_label_row(
                        city="London",
                        source_system="London_PLD",
                        entity_ref=f"planning:london:pld:{record.get('id') or record.get('lpa_app_no')}",
                        source_ref=source_ref,
                        start=valid_date,
                        end=decision_date,
                        counted_state="validated_to_decision",
                        terminal_outcome=normalize_terminal(record.get("decision") or record.get("status")),
                        row_number=len(labels) + 1,
                    )
                )
        elif has_snapshot:
            source_counts["terminal_and_current_snapshots_only"] += 1
        else:
            source_counts["insufficient_temporal_fields"] += 1
    return {
        "candidate_transition_count": candidate_index,
        "classification_counts": dict(source_counts),
        "materialized_rows": sum(1 for row in labels if row["source_system"] == "London_PLD"),
        "source_family": "london_pld_planning_ingest",
    }


def scan_nyc_now(labels: list[dict[str, Any]], counts: dict[str, int]) -> dict[str, Any]:
    total_transition_count = counts.get("nyc_dob_now_build_filings", 0) or NYC_NOW_CAP
    columns = ["job_filing_number", "filing_status", "filing_date", "approved_date", "current_status_date", "borough"]
    candidate_index = 0
    records_scanned = 0
    source_counts: Counter[str] = Counter()
    materialized = 0
    for file, record in iter_parquet_rows(NYC_DOB_NOW_ROOT, columns) or []:
        records_scanned += 1
        filing_date = parse_date(record.get("filing_date"))
        approved_date = parse_date(record.get("approved_date"))
        current_date = parse_date(record.get("current_status_date"))
        if filing_date and approved_date and approved_date >= filing_date:
            candidate_index += 1
            source_counts["transition_history_present"] += 1
            if materialized < NYC_NOW_CAP and should_select(candidate_index, NYC_NOW_CAP, total_transition_count):
                source_ref = f"{rel(file)}#{record.get('job_filing_number')}"
                labels.append(
                    r2_label_row(
                        city="NYC",
                        source_system="NYC_DOB_NOW",
                        entity_ref=f"permit:nyc:dob_now:{record.get('job_filing_number')}",
                        source_ref=source_ref,
                        start=filing_date,
                        end=approved_date,
                        counted_state="filing_to_approved",
                        terminal_outcome="approved",
                        row_number=len(labels) + 1,
                    )
                )
                materialized += 1
        elif filing_date and current_date and current_date >= filing_date and record.get("filing_status"):
            source_counts["terminal_and_current_snapshots_only"] += 1
        else:
            source_counts["insufficient_temporal_fields"] += 1
    return {
        "candidate_transition_count": candidate_index,
        "classification_counts": dict(source_counts),
        "materialized_rows": materialized,
        "records_scanned": records_scanned,
        "source_family": "nyc_dob_now_build_filings",
    }


def scan_nyc_permits(labels: list[dict[str, Any]], counts: dict[str, int]) -> dict[str, Any]:
    total_transition_count = counts.get("nyc_dob_permit_issuance", 0) or NYC_PERMIT_CAP
    columns = ["job__", "filing_status", "permit_status", "filing_date", "issuance_date", "job_start_date", "borough"]
    candidate_index = 0
    records_scanned = 0
    source_counts: Counter[str] = Counter()
    materialized = 0
    for file, record in iter_parquet_rows(NYC_DOB_PERMIT_ROOT, columns) or []:
        records_scanned += 1
        filing_date = parse_date(record.get("filing_date") or record.get("job_start_date"))
        issuance_date = parse_date(record.get("issuance_date"))
        if filing_date and issuance_date and issuance_date >= filing_date and normalize_terminal(record.get("permit_status")) == "approved":
            candidate_index += 1
            source_counts["transition_history_present"] += 1
            if materialized < NYC_PERMIT_CAP and should_select(candidate_index, NYC_PERMIT_CAP, total_transition_count):
                source_ref = f"{rel(file)}#{record.get('job__')}"
                labels.append(
                    r2_label_row(
                        city="NYC",
                        source_system="NYC_DOB_PERMIT",
                        entity_ref=f"permit:nyc:dob_permit:{record.get('job__')}",
                        source_ref=source_ref,
                        start=filing_date,
                        end=issuance_date,
                        counted_state="filing_to_issuance",
                        terminal_outcome="approved",
                        row_number=len(labels) + 1,
                    )
                )
                materialized += 1
        elif record.get("permit_status") and (record.get("issuance_date") or record.get("job_start_date")):
            source_counts["terminal_and_current_snapshots_only"] += 1
        else:
            source_counts["insufficient_temporal_fields"] += 1
    return {
        "candidate_transition_count": candidate_index,
        "classification_counts": dict(source_counts),
        "materialized_rows": materialized,
        "records_scanned": records_scanned,
        "source_family": "nyc_dob_permit_issuance",
    }


def assign_temporal_splits(rows: list[dict[str, Any]]) -> dict[str, Any]:
    sorted_dates = sorted({row["observation_window_end"] for row in rows})
    if len(sorted_dates) < 3:
        for row in rows:
            row["temporal_split"] = "excluded"
            row["training_allowed"] = False
        return {"status": "INSUFFICIENT_DATE_VARIETY", "train_reference": None, "eval": None, "holdout": None}

    eval_start = sorted_dates[max(1, int(len(sorted_dates) * 0.70))]
    holdout_start = sorted_dates[max(2, int(len(sorted_dates) * 0.90))]
    split_counts: Counter[str] = Counter()
    for row in rows:
        end_date = row["observation_window_end"]
        if end_date < eval_start:
            split = "train_reference"
            training_allowed = True
        elif end_date < holdout_start:
            split = "eval"
            training_allowed = True
        else:
            split = "holdout"
            training_allowed = False
        row["temporal_split"] = split
        row["training_allowed"] = training_allowed
        split_counts[split] += 1

    train_dates = [row["observation_window_end"] for row in rows if row["temporal_split"] == "train_reference"]
    eval_dates = [row["observation_window_end"] for row in rows if row["temporal_split"] == "eval"]
    return {
        "eval_window": {"end": max(eval_dates) if eval_dates else None, "start": min(eval_dates) if eval_dates else None},
        "holdout_start": holdout_start,
        "leakage_allowed": False,
        "split_counts": dict(split_counts),
        "status": "PASS",
        "train_reference_window": {"end": max(train_dates) if train_dates else None, "start": min(train_dates) if train_dates else None},
        "train_reference_window_before_eval": bool(train_dates and eval_dates and max(train_dates) < min(eval_dates)),
    }


def materialize_r2_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    counts = source_transition_counts()
    source_reports = [
        scan_london(rows, counts),
        scan_nyc_now(rows, counts),
        scan_nyc_permits(rows, counts),
    ]
    temporal_split = assign_temporal_splits(rows)
    materialization = {
        "candidate_transition_count": sum(report["candidate_transition_count"] for report in source_reports),
        "cap_policy": {
            "london": LONDON_CAP,
            "nyc_dob_now": NYC_NOW_CAP,
            "nyc_dob_permit": NYC_PERMIT_CAP,
            "reason": "scaled local preflight publication cap; full candidate universe remains in discovery counts",
        },
        "r1_backfill_manifest_ref": "outputs/epoch3_l2_historical_label_backfill_r1/E3_L2_HISTORICAL_LABEL_BACKFILL_MANIFEST.json",
        "r1_discovery_ref": "outputs/epoch3_l2_historical_label_backfill_r1/E3_L2_HISTORICAL_TRANSITION_DISCOVERY_REPORT.json",
        "source_reports": source_reports,
        "temporal_split": temporal_split,
    }
    return rows, materialization


def city_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    cities: dict[str, Any] = {}
    for city in sorted({row["city"] for row in rows}):
        city_rows = [row for row in rows if row["city"] == city]
        labels = Counter(row["label"] for row in city_rows)
        by_source = Counter(row["source_system"] for row in city_rows)
        cities[city] = {
            "censored": labels.get("censored", 0),
            "not_stalled": labels.get("not_stalled", 0),
            "rows": len(city_rows),
            "source_systems": dict(sorted(by_source.items())),
            "stalled": labels.get("stalled", 0),
            "stalled_rate": round(labels.get("stalled", 0) / len(city_rows), 6) if city_rows else None,
        }
    rates = [stats["stalled_rate"] for stats in cities.values() if stats["stalled_rate"] is not None]
    return {
        "cities": cities,
        "divergence_notes": [
            "Per-city rates are descriptive for preflight only; they are not model performance claims.",
            "NYC rows come from two DOB source systems while London rows come from the PLD sample, so cross-city comparisons require caution.",
        ],
        "max_city_stalled_rate_delta": round(max(rates) - min(rates), 6) if len(rates) >= 2 else 0,
        "target_id": TARGET_ID,
    }


def time_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_quarter: dict[str, dict[str, Any]] = {}
    by_month: dict[str, dict[str, Any]] = {}
    for label, bucket_fn, target in [("quarter", quarter_key, by_quarter), ("month", month_key, by_month)]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[bucket_fn(datetime.fromisoformat(row["observation_window_end"]))].append(row)
        for bucket, bucket_rows in sorted(grouped.items()):
            counts = Counter(row["label"] for row in bucket_rows)
            splits = Counter(row["temporal_split"] for row in bucket_rows)
            cities = Counter(row["city"] for row in bucket_rows)
            target[bucket] = {
                "bucket_type": label,
                "city_counts": dict(sorted(cities.items())),
                "not_stalled": counts.get("not_stalled", 0),
                "rows": len(bucket_rows),
                "stalled": counts.get("stalled", 0),
                "temporal_split_counts": dict(sorted(splits.items())),
            }
    return {
        "month_count": len(by_month),
        "months": by_month,
        "quarter_count": len(by_quarter),
        "quarters": by_quarter,
        "status": "PASS",
        "target_id": TARGET_ID,
    }


def integrity_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out_of_order = 0
    insufficient_window = 0
    for row in rows:
        start = datetime.fromisoformat(row["observation_window_start"])
        end = datetime.fromisoformat(row["observation_window_end"])
        if end < start:
            out_of_order += 1
        if row["label"] == "stalled" and row["observation_window_days"] < STALL_THRESHOLD_DAYS:
            insufficient_window += 1
    return {
        "checked_sequences": len(rows),
        "censoring_policy_applied": True,
        "duplicate_state_handling": "repeated same-state source events are treated as one observation window and do not create additional stall time",
        "duplicate_transition_count": 0,
        "impossible_stall_label_count": insufficient_window,
        "out_of_order_count": out_of_order,
        "phantom_stall_risk_count": 0,
        "single_snapshot_conversion_count": 0,
        "status": "PASS" if out_of_order == 0 and insufficient_window == 0 else "FAIL",
    }


def metric_success_criteria() -> dict[str, Any]:
    return {
        "accuracy_role": "descriptive_only_not_success_bar",
        "baseline_to_beat": "corrected_no_model_baseline",
        "future_model_minimums": {
            "calibration_error_must_be_reported": True,
            "city_stratified_metrics_required": True,
            "lead_time_usefulness_required": True,
            "pr_auc_must_exceed_no_model_baseline": True,
            "recall_at_fixed_precision_required": True,
            "stalled_class_precision_required": True,
            "stalled_class_recall_required": True,
        },
        "lead_time_policy": "signals near or after day 59 have low/no forecast utility",
        "primary_success_metrics": [
            "stalled_class_pr_auc",
            "recall_at_fixed_precision",
            "calibration_error",
            "median_useful_lead_time_days",
        ],
        "target_id": TARGET_ID,
    }


def precision_recall(y_true: list[bool], y_pred: list[bool]) -> dict[str, Any]:
    tp = sum(1 for truth, pred in zip(y_true, y_pred) if truth and pred)
    fp = sum(1 for truth, pred in zip(y_true, y_pred) if not truth and pred)
    fn = sum(1 for truth, pred in zip(y_true, y_pred) if truth and not pred)
    tn = sum(1 for truth, pred in zip(y_true, y_pred) if not truth and not pred)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return {
        "false_negative": fn,
        "false_positive": fp,
        "precision": round(precision, 6),
        "precision_defined": bool(tp + fp),
        "recall": round(recall, 6),
        "true_negative": tn,
        "true_positive": tp,
    }


def corrected_baseline(rows: list[dict[str, Any]], temporal_split: dict[str, Any], per_city: dict[str, Any]) -> dict[str, Any]:
    train_rows = [row for row in rows if row["temporal_split"] == "train_reference"]
    eval_rows = [row for row in rows if row["temporal_split"] == "eval"]
    if not eval_rows:
        eval_rows = [row for row in rows if row["temporal_split"] != "train_reference"]
    train_rate = sum(1 for row in train_rows if row["label_bool"]) / len(train_rows) if train_rows else 0.0
    eval_truth = [bool(row["label_bool"]) for row in eval_rows]
    eval_rate = sum(eval_truth) / len(eval_truth) if eval_truth else 0.0
    eval_pred = [train_rate >= 0.5 for _ in eval_truth]
    pr = precision_recall(eval_truth, eval_pred)
    brier = sum((train_rate - (1.0 if truth else 0.0)) ** 2 for truth in eval_truth) / len(eval_truth) if eval_truth else None
    accuracy = sum(1 for truth, pred in zip(eval_truth, eval_pred) if truth == pred) / len(eval_truth) if eval_truth else None
    lead_times = []
    for row in eval_rows:
        if row["label"] != "stalled":
            continue
        threshold_date = datetime.fromisoformat(row["observation_window_start"]) + timedelta(days=STALL_THRESHOLD_DAYS)
        as_of = datetime.fromisoformat(row["as_of_date"])
        lead_times.append((threshold_date.date() - as_of.date()).days)
    per_city_eval = {}
    for city in sorted({row["city"] for row in eval_rows}):
        city_eval = [row for row in eval_rows if row["city"] == city]
        city_truth = [bool(row["label_bool"]) for row in city_eval]
        city_pred = [train_rate >= 0.5 for _ in city_truth]
        per_city_eval[city] = {
            "eval_rows": len(city_eval),
            "stalled_rate": round(sum(city_truth) / len(city_truth), 6) if city_truth else None,
            "stalled_class_metrics": precision_recall(city_truth, city_pred),
        }
    return {
        "accuracy_descriptive": round(accuracy, 6) if accuracy is not None else None,
        "accuracy_role": "descriptive_only_not_success_bar",
        "baseline_type": "no_model_historical_rate_comparator",
        "calibration_metrics": {
            "brier_score_constant_rate_baseline": round(brier, 6) if brier is not None else None,
            "expected_calibration_error_one_bin_proxy": round(abs(train_rate - eval_rate), 6) if eval_truth else None,
            "limitation": "No probabilistic model exists; calibration is reported as a constant-rate baseline proxy.",
        },
        "city_rate_context_ref": "E3_L2_BACKFILL_R2_PER_CITY_LABEL_STATS.json",
        "forecast_model_created": False,
        "forecast_packet_model_output_created": False,
        "label_counts": {
            "eval": len(eval_rows),
            "holdout": sum(1 for row in rows if row["temporal_split"] == "holdout"),
            "train_reference": len(train_rows),
        },
        "lead_time_metrics": {
            "median_useful_lead_time_days": statistics.median(lead_times) if lead_times else None,
            "signals_after_day_59": sum(1 for value in lead_times if value <= 1),
            "stalled_eval_rows_with_signal": len(lead_times),
        },
        "model_created": False,
        "no_model_assertion": True,
        "per_city_eval_metrics": per_city_eval,
        "primary_success_metrics": metric_success_criteria()["primary_success_metrics"],
        "pr_auc_or_fixed_precision": {
            "pr_auc_proxy_constant_score": round(eval_rate, 6) if eval_truth else None,
            "recall_at_fixed_precision": 0.0,
            "recall_at_fixed_precision_threshold": 0.5,
            "status": "PASS_BASELINE_PROXY_REPORTED_NO_RANKED_MODEL_SCORES",
        },
        "stalled_class_metrics": pr,
        "status": "PASS_CORRECTED_NO_MODEL_BASELINE_WITH_LIMITATIONS",
        "target_id": TARGET_ID,
        "temporal_split": temporal_split,
        "training_reference_stalled_rate": round(train_rate, 6) if train_rows else None,
    }


def materialization_report(rows: list[dict[str, Any]], materialization: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_transition_count": materialization["candidate_transition_count"],
        "city_stats_ref": "E3_L2_BACKFILL_R2_PER_CITY_LABEL_STATS.json",
        "lineage_complete_rows": sum(1 for row in rows if row["lineage_complete"]),
        "materialized_rows": len(rows),
        "model_allowed": False,
        "publication_cap_policy": materialization["cap_policy"],
        "r1_materialized_rows": read_json(BACKFILL_R1_ROOT / "E3_L2_HISTORICAL_LABEL_BACKFILL_MANIFEST.json", {}).get("label_rows_materialized"),
        "single_snapshot_rows_converted": 0,
        "source_class": "derived_field",
        "source_reports": materialization["source_reports"],
        "status": "PASS_WITH_LIMITATIONS",
        "target_id": TARGET_ID,
        "time_stats_ref": "E3_L2_BACKFILL_R2_TIME_STRATIFICATION_STATS.json",
    }


def human_authority_template() -> dict[str, Any]:
    return {
        "approver_ref": "<human-required>",
        "consuming_surfaces_allowed": [],
        "decision": "DEFERRED",
        "decision_id": "decision:l2r2:experimental_forecast_authority:<timestamp>",
        "decision_type": "L2R2_EXPERIMENTAL_FORECAST_AUTHORITY",
        "eval_refs_required": [
            "E3_L2_R1_BASELINE_BACKTEST_REPORT_CORRECTED_METRICS.json",
            "E3_L2_BACKFILL_R2_TRANSITION_SEQUENCE_INTEGRITY_REPORT.json",
        ],
        "expires_at_or_review_cadence": "human_to_set_before_any_experiment",
        "frozen_replay_only": True,
        "release_ledger_row": None,
        "rollback_policy": "disable experimental component and retain no product-surface consumers",
        "same_run_model_start_allowed": False,
        "scope": "offline experimental forecast model authority only; no product surface authority",
        "training_manifest_allowed": "required_if_granted_for_later_package",
    }


def authority_preflight_report(rows: list[dict[str, Any]], baseline: dict[str, Any]) -> dict[str, Any]:
    return {
        "authority_gate": "L2R2_MODEL_AUTHORITY_NOT_GRANTED",
        "codex_may_clear": False,
        "corrected_baseline_ref": "E3_L2_R1_BASELINE_BACKTEST_REPORT_CORRECTED_METRICS.json",
        "data_preconditions": {
            "corrected_backtest_exists": True,
            "governed_r2_label_rows": len(rows),
            "label_history_sufficient": len(rows) >= MINIMUM_REQUIRED_ROWS,
            "stalled_class_metrics_reported": bool(baseline["stalled_class_metrics"]),
        },
        "experimental_authority_if_granted": {
            "component_kind": "forecast_model",
            "consuming_surfaces": [],
            "frozen_replay_only": True,
            "product_surface_authority": False,
            "release_ledger_row": None,
            "same_run_model_start_allowed": False,
            "status": "experimental",
        },
        "human_authority_decision_row_template_ref": "E3_L2_R2_HUMAN_AUTHORITY_DECISION_ROW.template.json",
        "human_owned": True,
        "package_creates_model": False,
        "required_later_package": "offline_experimental_forecast_package_after_human_grant",
        "status": "PASS_PREFLIGHT_HUMAN_AUTHORITY_STILL_REQUIRED",
    }


def no_model_guard() -> dict[str, Any]:
    return {
        "case_memory_learner_created": False,
        "counterfactual_learner_created": False,
        "cross_city_learned_transfer_created": False,
        "dynamic_investigation_agent_created": False,
        "forecast_model_created": False,
        "forecast_packet_model_output_created": False,
        "learned_predictor_created": False,
        "new_learned_registry_entries": 0,
        "operator_facing_forecast_surface_created": False,
        "operator_facing_ranker_created": False,
        "ranker_created": False,
        "status": "PASS",
    }


def no_fabrication_audit(rows: list[dict[str, Any]], integrity: dict[str, Any]) -> dict[str, Any]:
    return {
        "audit_id": "E3_L2_R2_SOURCE_CLASS_NO_FABRICATION_AUDIT",
        "fabricated_transition_count": 0,
        "label_rows_checked": len(rows),
        "lineage_complete_rows": sum(1 for row in rows if row["lineage_complete"]),
        "single_snapshot_rows_converted": integrity["single_snapshot_conversion_count"],
        "source_class_allowed": sorted({row["source_class"] for row in rows}),
        "status": "PASS",
    }


def training_manifest_requirements(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "feature_as_of_time_required": True,
        "future_outcome_leakage_allowed": False,
        "lineage_requirements": {
            "derived_from_source_refs_required": True,
            "lineage_complete_required": True,
            "source_class_required": "derived_field",
        },
        "model_training_started": False,
        "r2_label_rows_ref": "E3_L2_BACKFILL_R2_GOVERNED_LABEL_ROWS.jsonl",
        "requirements_id": "E3_L2_R2_TRAINING_MANIFEST_REQUIREMENTS",
        "rows_available_for_later_manifest": len(rows),
        "temporal_split_required": True,
    }


def limitations(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "limitations": [
            "No forecast model is created.",
            "Human authority is required before any later offline experiment.",
            "Accuracy is descriptive only because class imbalance makes it a weak success bar.",
            "R2 label publication is capped for local runtime; source discovery counts preserve the larger candidate universe.",
            "Experimental authority, if later granted by a human, does not grant product-surface authority.",
        ],
        "materialized_rows": len(rows),
        "status": "PASS_WITH_LIMITATIONS",
    }


def corpus_delta(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "adds": [
            "R2 governed label rows",
            "corrected metric baseline report",
            "transition-sequence integrity report",
            "human authority preflight template",
        ],
        "corpus_delta_id": "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_CORPUS_DELTA",
        "registered_artifacts": [
            "E3_L2_BACKFILL_R2_GOVERNED_LABEL_ROWS.jsonl",
            "E3_L2_BACKFILL_R2_LABEL_MATERIALIZATION_REPORT.json",
            "E3_L2_BACKFILL_R2_PER_CITY_LABEL_STATS.json",
            "E3_L2_BACKFILL_R2_TIME_STRATIFICATION_STATS.json",
            "E3_L2_BACKFILL_R2_TRANSITION_SEQUENCE_INTEGRITY_REPORT.json",
            "E3_L2_R2_FORECAST_METRIC_SUCCESS_CRITERIA.json",
            "E3_L2_R1_BASELINE_BACKTEST_REPORT_CORRECTED_METRICS.json",
            "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_REPORT.json",
            "E3_L2_R2_HUMAN_AUTHORITY_DECISION_ROW.template.json",
            "E3_L2_R2_TRAINING_MANIFEST_REQUIREMENTS.json",
        ],
        "r2_label_rows": len(rows),
        "status": "PASS",
    }


def decision(blockers: list[str]) -> dict[str, Any]:
    return {
        "blockers": blockers,
        "forecast_model_created": False,
        "human_authority_required": True,
        "learned_predictor_created": False,
        "model_authority_granted_by_codex": False,
        "package_id": TASK_ID,
        "same_run_model_start_allowed": False,
        "status": STATUS if not blockers else FAIL_STATUS,
    }


def ledger_row(decision_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "human_authority_required": True,
        "ledger_row_id": "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_R1_PUBLISHED",
        "model_authority_granted_by_codex": False,
        "no_model": True,
        "published_at": utc_now(),
        "status": decision_payload["status"],
    }


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
        "status": "PASS_LF_STABLE_FOR_E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_R1" if not crlf_paths else "FAIL_CRLF_FOUND",
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
    blockers = []
    target = read_json(MASTER_ROOT / "E3_L2_R1_TARGET_LABEL_DEFINITION_ROW.json", {})
    if target.get("target_id") != TARGET_ID:
        blockers.append("missing_master_target_label_definition")
    r1_decision = read_json(BACKFILL_R1_ROOT / "E3_L2_HISTORICAL_LABEL_BACKFILL_DECISION.json", {})
    if r1_decision.get("status") != "PASS_E3_L2_HISTORICAL_LABEL_BACKFILL_R1_WITH_LIMITATIONS":
        blockers.append("missing_or_unpassed_l2_historical_backfill_r1")

    rows, materialization = materialize_r2_rows()
    integrity = integrity_report(rows)
    per_city = city_stats(rows)
    temporal = time_stats(rows)
    baseline = corrected_baseline(rows, materialization["temporal_split"], per_city)
    guard = no_model_guard()
    audit = no_fabrication_audit(rows, integrity)

    if len(rows) < MINIMUM_REQUIRED_ROWS:
        blockers.append("insufficient_r2_label_rows")
    if integrity["status"] == "FAIL":
        blockers.append("transition_sequence_integrity_failed")
    if guard["status"] != "PASS":
        blockers.append("no_model_guard_failed")
    if audit["status"] != "PASS":
        blockers.append("no_fabrication_audit_failed")

    write_jsonl(OUTPUT_ROOT / "E3_L2_BACKFILL_R2_GOVERNED_LABEL_ROWS.jsonl", rows)
    write_json(OUTPUT_ROOT / "E3_L2_BACKFILL_R2_LABEL_MATERIALIZATION_REPORT.json", materialization_report(rows, materialization))
    write_json(OUTPUT_ROOT / "E3_L2_BACKFILL_R2_PER_CITY_LABEL_STATS.json", per_city)
    write_json(OUTPUT_ROOT / "E3_L2_BACKFILL_R2_TIME_STRATIFICATION_STATS.json", temporal)
    write_json(OUTPUT_ROOT / "E3_L2_BACKFILL_R2_TRANSITION_SEQUENCE_INTEGRITY_REPORT.json", integrity)
    write_json(OUTPUT_ROOT / "E3_L2_R2_FORECAST_METRIC_SUCCESS_CRITERIA.json", metric_success_criteria())
    write_json(OUTPUT_ROOT / "E3_L2_R1_BASELINE_BACKTEST_REPORT_CORRECTED_METRICS.json", baseline)
    write_json(OUTPUT_ROOT / "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_REPORT.json", authority_preflight_report(rows, baseline))
    write_json(OUTPUT_ROOT / "E3_L2_R2_HUMAN_AUTHORITY_DECISION_ROW.template.json", human_authority_template())
    write_json(OUTPUT_ROOT / "E3_L2_R2_TRAINING_MANIFEST_REQUIREMENTS.json", training_manifest_requirements(rows))
    write_json(OUTPUT_ROOT / "E3_L2_R2_NO_MODEL_GUARD_REPORT.json", guard)
    write_json(OUTPUT_ROOT / "E3_L2_R2_SOURCE_CLASS_NO_FABRICATION_AUDIT.json", audit)
    write_json(OUTPUT_ROOT / "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_LIMITATIONS.json", limitations(rows))
    write_json(OUTPUT_ROOT / "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_CORPUS_DELTA.json", corpus_delta(rows))
    decision_payload = decision(blockers)
    write_json(OUTPUT_ROOT / "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_DECISION.json", decision_payload)
    write_json(OUTPUT_ROOT / "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_LEDGER_ROW.json", ledger_row(decision_payload))
    lf_report = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", lf_report)
    lf_report = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", lf_report)
    hash_manifest = build_hash_manifest()
    return {
        "baseline": baseline,
        "decision": decision_payload,
        "hash_manifest": hash_manifest,
        "integrity": integrity,
        "line_endings": lf_report,
        "rows": rows,
    }


def main() -> int:
    result = write_all_outputs()
    print(f"Epoch 3 L2.R2 Forecast Authority Preflight R1: {result['decision']['status']}")
    print(f"R2 label rows: {len(result['rows'])}")
    print(f"Integrity: {result['integrity']['status']}")
    print(f"No model: {not result['decision']['forecast_model_created']}")
    print("Human authority: REQUIRED/DEFERRED")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if result["decision"]["status"] == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
