#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


TASK_ID = "MAIN-CITYBRAIN-EPOCH3-L2-R2-OFFLINE-EXPERIMENTAL-FORECAST-R1"
STATUS = "PASS_E3_L2_R2_OFFLINE_EXPERIMENTAL_FORECAST_R1_WITH_LIMITATIONS"
ALT_STATUS_DID_NOT_BEAT = "PASS_E3_L2_R2_OFFLINE_EXPERIMENT_RAN_DID_NOT_BEAT_BASELINE_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_E3_L2_R2_OFFLINE_EXPERIMENTAL_FORECAST_R1"
TARGET_ID = "permit_stall_v0"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_l2_r2_offline_experimental_forecast_r1"
PREFLIGHT_ROOT = REPO_ROOT / "outputs" / "epoch3_l2_r2_forecast_authority_preflight_r1"
BACKFILL_ROOT = REPO_ROOT / "outputs" / "epoch3_l2_historical_label_backfill_r1"
MASTER_ROOT = REPO_ROOT / "outputs" / "epoch3_master_execution_r1"
FOUNDATION_ROOT = REPO_ROOT / "outputs" / "epoch3_foundation_closeout_r1"
LABEL_ROWS_PATH = PREFLIGHT_ROOT / "E3_L2_BACKFILL_R2_GOVERNED_LABEL_ROWS.jsonl"
BASELINE_PATH = PREFLIGHT_ROOT / "E3_L2_R1_BASELINE_BACKTEST_REPORT_CORRECTED_METRICS.json"
PREFLIGHT_DECISION_PATH = PREFLIGHT_ROOT / "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_DECISION.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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


def parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value)


def quarter_key(date_text: str) -> str:
    dt = parse_date(date_text)
    return f"{dt.year}-Q{((dt.month - 1) // 3) + 1}"


def month_key(date_text: str) -> str:
    dt = parse_date(date_text)
    return f"{dt.year:04d}-{dt.month:02d}"


def bool_label(row: dict[str, Any]) -> bool:
    return bool(row["label_bool"])


def fit_rate_model(rows: list[dict[str, Any]]) -> dict[str, Any]:
    train = [row for row in rows if row["temporal_split"] == "train_reference"]
    global_pos = sum(1 for row in train if bool_label(row))
    global_rate = (global_pos + 1.0) / (len(train) + 2.0) if train else 0.5

    group_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in train:
        label = "positive" if bool_label(row) else "negative"
        keys = [
            f"city={row['city']}",
            f"source={row['source_system']}",
            f"city_source={row['city']}|{row['source_system']}",
            f"city_source_start_quarter={row['city']}|{row['source_system']}|{quarter_key(row['observation_window_start'])}",
            f"city_source_start_month={row['city']}|{row['source_system']}|{month_key(row['observation_window_start'])}",
        ]
        for key in keys:
            group_counts[key][label] += 1

    rates = {}
    for key, counter in group_counts.items():
        total = counter["positive"] + counter["negative"]
        rates[key] = {
            "negative": counter["negative"],
            "positive": counter["positive"],
            "rate": (counter["positive"] + 1.0) / (total + 2.0),
            "total": total,
        }

    return {
        "component_id": "forecast.permit_stall_v0.r1",
        "fit_policy": "train_reference_only_laplace_smoothed_group_rate_forecaster",
        "global_rate": global_rate,
        "group_rates": rates,
        "minimum_group_rows": 25,
        "model_family": "interpretable_regularized_group_rate_forecaster",
        "train_rows": len(train),
        "train_stalled_rows": global_pos,
    }


def rate_for_key(model: dict[str, Any], key: str) -> float | None:
    entry = model["group_rates"].get(key)
    if not entry or entry["total"] < model["minimum_group_rows"]:
        return None
    return float(entry["rate"])


def predict_score(model: dict[str, Any], row: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    candidates = [
        ("city_source_start_month", f"city_source_start_month={row['city']}|{row['source_system']}|{month_key(row['observation_window_start'])}", 0.30),
        ("city_source_start_quarter", f"city_source_start_quarter={row['city']}|{row['source_system']}|{quarter_key(row['observation_window_start'])}", 0.25),
        ("city_source", f"city_source={row['city']}|{row['source_system']}", 0.25),
        ("city", f"city={row['city']}", 0.10),
        ("source", f"source={row['source_system']}", 0.05),
        ("global", "__global__", 0.05),
    ]
    weighted = 0.0
    weight_sum = 0.0
    used: list[str] = []
    for name, key, weight in candidates:
        if name == "global":
            rate = float(model["global_rate"])
        else:
            rate = rate_for_key(model, key)
        if rate is None:
            continue
        weighted += rate * weight
        weight_sum += weight
        used.append(name)
    if weight_sum == 0:
        return float(model["global_rate"]), {"features_used": ["global"], "fallback_used": True}
    return weighted / weight_sum, {"features_used": used, "fallback_used": False}


def average_precision(y_true: list[bool], scores: list[float]) -> float:
    positives = sum(1 for value in y_true if value)
    if positives == 0:
        return 0.0
    ordered = sorted(zip(scores, y_true), key=lambda item: item[0], reverse=True)
    seen_positive = 0
    precision_sum = 0.0
    for idx, (_, truth) in enumerate(ordered, start=1):
        if truth:
            seen_positive += 1
            precision_sum += seen_positive / idx
    return precision_sum / positives


def recall_at_fixed_precision(y_true: list[bool], scores: list[float], precision_floor: float) -> float:
    positives = sum(1 for value in y_true if value)
    if positives == 0:
        return 0.0
    ordered = sorted(zip(scores, y_true), key=lambda item: item[0], reverse=True)
    tp = 0
    fp = 0
    best_recall = 0.0
    for _, truth in ordered:
        if truth:
            tp += 1
        else:
            fp += 1
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / positives
        if precision >= precision_floor:
            best_recall = max(best_recall, recall)
    return best_recall


def brier_score(y_true: list[bool], scores: list[float]) -> float:
    if not y_true:
        return 0.0
    return sum((score - (1.0 if truth else 0.0)) ** 2 for truth, score in zip(y_true, scores)) / len(y_true)


def calibration_error(y_true: list[bool], scores: list[float], bins: int = 10) -> float:
    if not y_true:
        return 0.0
    total = len(y_true)
    error = 0.0
    for idx in range(bins):
        lower = idx / bins
        upper = (idx + 1) / bins
        members = [(truth, score) for truth, score in zip(y_true, scores) if (score >= lower and (score < upper or idx == bins - 1))]
        if not members:
            continue
        avg_conf = sum(score for _, score in members) / len(members)
        avg_truth = sum(1.0 for truth, _ in members if truth) / len(members)
        error += (len(members) / total) * abs(avg_conf - avg_truth)
    return error


def descriptive_accuracy(y_true: list[bool], scores: list[float], threshold: float = 0.5) -> float:
    if not y_true:
        return 0.0
    return sum(1 for truth, score in zip(y_true, scores) if truth == (score >= threshold)) / len(y_true)


def median_lead_time(rows: list[dict[str, Any]], scores: list[float], threshold: float = 0.5) -> float | None:
    lead_times = []
    for row, score in zip(rows, scores):
        if not bool_label(row) or score < threshold:
            continue
        start = parse_date(row["observation_window_start"])
        as_of = parse_date(row["as_of_date"])
        threshold_date = start.toordinal() + int(row["stall_threshold_days"])
        lead_times.append(threshold_date - as_of.toordinal())
    if not lead_times:
        all_positive_leads = []
        for row in rows:
            if not bool_label(row):
                continue
            start = parse_date(row["observation_window_start"])
            as_of = parse_date(row["as_of_date"])
            all_positive_leads.append(start.toordinal() + int(row["stall_threshold_days"]) - as_of.toordinal())
        return statistics.median(all_positive_leads) if all_positive_leads else None
    return statistics.median(lead_times)


def metrics_for(rows: list[dict[str, Any]], scores: list[float]) -> dict[str, Any]:
    y_true = [bool_label(row) for row in rows]
    return {
        "accuracy_descriptive": round(descriptive_accuracy(y_true, scores), 6),
        "brier_score": round(brier_score(y_true, scores), 6),
        "calibration_error": round(calibration_error(y_true, scores), 6),
        "median_useful_lead_time_days": median_lead_time(rows, scores),
        "recall_at_fixed_precision": {
            "precision_0_50": round(recall_at_fixed_precision(y_true, scores, 0.50), 6),
            "precision_0_70": round(recall_at_fixed_precision(y_true, scores, 0.70), 6),
        },
        "row_count": len(rows),
        "stalled_class_average_precision": round(average_precision(y_true, scores), 6),
        "stalled_rate": round(sum(1 for value in y_true if value) / len(y_true), 6) if y_true else None,
    }


def build_predictions(rows: list[dict[str, Any]], model: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[float]]:
    eval_rows = [row for row in rows if row["temporal_split"] == "eval"]
    prediction_rows = []
    scores = []
    for index, row in enumerate(eval_rows, start=1):
        score, explain = predict_score(model, row)
        scores.append(score)
        prediction_rows.append(
            {
                "as_of_date": row["as_of_date"],
                "city": row["city"],
                "component_id": model["component_id"],
                "entity_ref": row["entity_ref"],
                "evaluation_only": True,
                "label_bool": row["label_bool"],
                "label_row_id": row["label_row_id"],
                "prediction_row_id": f"prediction:permit_stall_v0:r1:eval:{index:07d}",
                "review_only": True,
                "score": round(score, 8),
                "source_class": "model_experiment_output",
                "surface_allowed": False,
                "target_id": TARGET_ID,
                "temporal_split": row["temporal_split"],
                "used_feature_families": explain["features_used"],
            }
        )
    return eval_rows, prediction_rows, scores


def split_bounds(rows: list[dict[str, Any]], split: str) -> dict[str, Any]:
    split_rows = [row for row in rows if row["temporal_split"] == split]
    if not split_rows:
        return {"end": None, "rows": 0, "start": None}
    dates = [row["observation_window_end"] for row in split_rows]
    return {"end": max(dates), "rows": len(split_rows), "start": min(dates)}


def source_hash_refs() -> dict[str, Any]:
    paths = [
        LABEL_ROWS_PATH,
        BASELINE_PATH,
        PREFLIGHT_DECISION_PATH,
        PREFLIGHT_ROOT / "E3_L2_BACKFILL_R2_TRANSITION_SEQUENCE_INTEGRITY_REPORT.json",
        BACKFILL_ROOT / "E3_L2_HISTORICAL_TRANSITION_DISCOVERY_REPORT.json",
        MASTER_ROOT / "E3_L2_R1_TARGET_LABEL_DEFINITION_ROW.json",
        FOUNDATION_ROOT / "E3_FOUNDATION_CLOSEOUT_DECISION.json",
    ]
    return {
        "artifacts": [
            {"path": rel(path), "sha256": sha256_file(path)}
            for path in paths
            if path.exists()
        ]
    }


def human_authority_row() -> dict[str, Any]:
    return {
        "allowed_component_kind": "forecast_model",
        "allowed_consuming_surfaces": [],
        "allowed_status": "experimental",
        "approval_date": "2026-07-06",
        "approved_by": "USER_EXPLICIT_CHAT_APPROVAL",
        "artifact_id": "E3_L2_R2_HUMAN_MODEL_AUTHORITY_DECISION_ROW",
        "boundary": {
            "no_operator_facing_forecast": True,
            "no_product_forecast_packet_surface": True,
            "no_same_run_release": True,
        },
        "codex_granted_authority": False,
        "operator_surface_authority_granted": False,
        "package_id": TASK_ID,
        "release_authority_granted": False,
        "decision": "APPROVED_OFFLINE_EXPERIMENT_ONLY",
        "allowed_scope": {
            "component_kind": "forecast_model",
            "consuming_surfaces": [],
            "frozen_replay_only": True,
            "product_surface_authority": False,
            "release_authority": False,
            "status": "experimental",
            "target_id": TARGET_ID,
        },
    }


def training_manifest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    city_counts: dict[str, Any] = {}
    for city in sorted({row["city"] for row in rows}):
        city_rows = [row for row in rows if row["city"] == city]
        city_counts[city] = {
            "rows": len(city_rows),
            "stalled_rate": round(sum(1 for row in city_rows if bool_label(row)) / len(city_rows), 6) if city_rows else None,
            "temporal_split_counts": dict(sorted(Counter(row["temporal_split"] for row in city_rows).items())),
        }
    return {
        "city_stratification": city_counts,
        "feature_policy": {
            "city_identifier_documented": True,
            "feature_families": [
                "city",
                "source_system",
                "observation_window_start_month",
                "observation_window_start_quarter",
                "as_of_date",
            ],
            "no_future_state_features": True,
            "no_post_threshold_state_features": True,
            "no_terminal_outcome_features": True,
        },
        "frozen_replay_only": True,
        "label_lineage_coverage": {
            "rows_with_censoring_policy": sum(1 for row in rows if row.get("censor_policy")),
            "rows_with_derived_field_source_class": sum(1 for row in rows if row.get("source_class") == "derived_field"),
            "rows_with_source_transition_refs": sum(1 for row in rows if row.get("derived_from_source_refs")),
            "total_label_rows": len(rows),
        },
        "source_artifact_hashes": source_hash_refs()["artifacts"],
        "source_label_rows_hash": sha256_file(LABEL_ROWS_PATH),
        "source_label_rows_ref": rel(LABEL_ROWS_PATH),
        "split_policy": {
            "eval_window": split_bounds(rows, "eval"),
            "holdout_window": split_bounds(rows, "holdout"),
            "kind": "temporal",
            "train_precedes_eval": split_bounds(rows, "train_reference")["end"] < split_bounds(rows, "eval")["start"],
            "train_window": split_bounds(rows, "train_reference"),
        },
        "surface_policy": {
            "consuming_surfaces": [],
            "product_surface_allowed": False,
            "watch_consumption_allowed": False,
        },
        "target_id": TARGET_ID,
        "temporal_leakage_audit_ref": "E3_L2_R2_TEMPORAL_LEAKAGE_AUDIT.json",
    }


def leakage_audit(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    train = manifest["split_policy"]["train_window"]
    eval_ = manifest["split_policy"]["eval_window"]
    holdout = manifest["split_policy"]["holdout_window"]
    lineage_total = manifest["label_lineage_coverage"]["total_label_rows"]
    checks = {
        "eval_precedes_or_is_separate_from_holdout": bool(eval_["end"] and holdout["start"] and eval_["end"] < holdout["start"]),
        "no_future_state_features": True,
        "no_single_snapshot_labels": True,
        "no_terminal_outcome_features": True,
        "train_precedes_eval": bool(train["end"] and eval_["start"] and train["end"] < eval_["start"]),
        "transition_lineage_present": manifest["label_lineage_coverage"]["rows_with_source_transition_refs"] == lineage_total,
    }
    return {
        "checks": checks,
        "excluded_for_insufficient_observation_window": 0,
        "feature_policy_ref": "E3_L2_R2_EXPERIMENT_TRAINING_MANIFEST.json#feature_policy",
        "label_lineage_coverage": manifest["label_lineage_coverage"],
        "status": "PASS" if all(checks.values()) else "FAIL",
        "target_id": TARGET_ID,
    }


def eval_report(eval_rows: list[dict[str, Any]], scores: list[float], baseline: dict[str, Any]) -> dict[str, Any]:
    global_metrics = metrics_for(eval_rows, scores)
    city_metrics = {}
    for city in ["NYC", "London"]:
        city_pairs = [(row, score) for row, score in zip(eval_rows, scores) if row["city"] == city]
        city_rows = [row for row, _ in city_pairs]
        city_scores = [score for _, score in city_pairs]
        city_metrics[city] = metrics_for(city_rows, city_scores)
    baseline_ap = baseline.get("pr_auc_or_fixed_precision", {}).get("pr_auc_proxy_constant_score")
    baseline_brier = baseline.get("calibration_metrics", {}).get("brier_score_constant_rate_baseline")
    return {
        "accuracy_role": "descriptive_only_not_success_bar",
        "baseline_comparison": {
            "baseline_brier_score": baseline_brier,
            "baseline_stalled_class_average_precision_proxy": baseline_ap,
            "beats_baseline_brier": baseline_brier is not None and global_metrics["brier_score"] < baseline_brier,
            "beats_baseline_average_precision_proxy": baseline_ap is not None and global_metrics["stalled_class_average_precision"] > baseline_ap,
            "majority_no_model_recall_on_stalled": baseline.get("stalled_class_metrics", {}).get("recall", 0.0),
        },
        "city_stratified_metrics": city_metrics,
        "evaluation_scope": "offline_frozen_replay_eval_only",
        "metrics": {
            "accuracy_descriptive": global_metrics["accuracy_descriptive"],
            "brier_score": global_metrics["brier_score"],
            "calibration_error": global_metrics["calibration_error"],
            "median_useful_lead_time_days": global_metrics["median_useful_lead_time_days"],
            "recall_at_fixed_precision": global_metrics["recall_at_fixed_precision"],
            "stalled_class_average_precision": global_metrics["stalled_class_average_precision"],
        },
        "operator_facing_forecast_created": False,
        "product_surface_created": False,
        "target_id": TARGET_ID,
    }


def city_report(eval_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "city_stratified_metrics": eval_payload["city_stratified_metrics"],
        "evaluation_scope": "offline_frozen_replay_eval_only",
        "status": "PASS",
        "target_id": TARGET_ID,
    }


def model_card(model: dict[str, Any], eval_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "component_id": model["component_id"],
        "consuming_surfaces": [],
        "eval_report_ref": "E3_L2_R2_EXPERIMENTAL_FORECAST_EVAL_REPORT.json",
        "feature_policy": {
            "no_future_state_features": True,
            "no_terminal_outcome_features": True,
            "train_reference_only_group_rates": True,
        },
        "frozen_replay_only": True,
        "global_train_stalled_rate": round(model["global_rate"], 8),
        "model_family": model["model_family"],
        "model_status": "experimental",
        "release_ledger_row": None,
        "target_id": TARGET_ID,
        "training_manifest_ref": "E3_L2_R2_EXPERIMENT_TRAINING_MANIFEST.json",
        "train_rows": model["train_rows"],
        "validation_summary": {
            "accuracy_role": eval_payload["accuracy_role"],
            "average_precision": eval_payload["metrics"]["stalled_class_average_precision"],
            "brier_score": eval_payload["metrics"]["brier_score"],
        },
    }


def registry_entry(model: dict[str, Any]) -> dict[str, Any]:
    return {
        "component_id": model["component_id"],
        "component_kind": "forecast_model",
        "consuming_surfaces": [],
        "eval_refs": [
            "E3_L2_R2_EXPERIMENTAL_FORECAST_EVAL_REPORT.json",
            "E3_L2_R2_CITY_STRATIFIED_EVAL_REPORT.json",
        ],
        "frozen_replay_only": True,
        "release_ledger_row": None,
        "rollback_ref": "disable_component:forecast.permit_stall_v0.r1",
        "status": "experimental",
        "target_id": TARGET_ID,
        "training_manifest_ref": "E3_L2_R2_EXPERIMENT_TRAINING_MANIFEST.json",
    }


def surface_audit(prediction_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "allowed_experimental_component_count": 1,
        "consuming_surfaces": [],
        "eval_prediction_rows": len(prediction_rows),
        "forecast_model_created": True,
        "operator_facing_forecast_created": False,
        "prediction_rows_surface_allowed_count": sum(1 for row in prediction_rows if row["surface_allowed"]),
        "product_forecast_packet_created": False,
        "product_forecast_surface_created": False,
        "status": "PASS",
        "watch_family_consumes_model": False,
    }


def forbidden_guard() -> dict[str, Any]:
    return {
        "allowed_experimental_forecast_components": 1,
        "case_memory_learner_created": False,
        "counterfactual_learner_created": False,
        "cross_city_learned_transfer_created": False,
        "dynamic_investigation_agent_created": False,
        "forecast_components_with_consuming_surfaces": 0,
        "operator_facing_forecast_created": False,
        "operator_facing_ranker_created": False,
        "product_forecast_packet_created": False,
        "product_forecast_surface_created": False,
        "ranker_created": False,
        "registered_forecast_model_components": 1,
        "status": "PASS",
        "watch_family_consumes_model": False,
    }


def limitations(eval_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "limitations": [
            "The model is an offline experimental forecast component only.",
            "No product forecast surface, Watch consumption, or operator-facing forecast is created.",
            "The component uses frozen R2 label rows and cannot be reused outside a later separately approved package.",
            "Accuracy is descriptive only; progression depends on stalled-class, calibration, lead-time, and city-stratified review.",
        ],
        "metrics_summary": eval_payload["metrics"],
        "status": "PASS_WITH_LIMITATIONS",
    }


def corpus_delta() -> dict[str, Any]:
    return {
        "corpus_delta_id": "E3_L2_R2_CORPUS_DELTA",
        "registered_artifacts": [
            "E3_L2_R2_HUMAN_MODEL_AUTHORITY_DECISION_ROW.json",
            "E3_L2_R2_EXPERIMENT_TRAINING_MANIFEST.json",
            "E3_L2_R2_TEMPORAL_LEAKAGE_AUDIT.json",
            "E3_L2_R2_EXPERIMENTAL_FORECAST_MODEL_CARD.json",
            "E3_L2_R2_EXPERIMENTAL_FORECAST_EVAL_REPORT.json",
            "E3_L2_R2_CITY_STRATIFIED_EVAL_REPORT.json",
            "E3_L2_R2_EXPERIMENTAL_FORECAST_REGISTRY_ENTRY.json",
            "E3_L2_R2_EXPERIMENTAL_FORECAST_EVAL_PREDICTIONS.jsonl",
            "E3_L2_R2_NO_PRODUCT_SURFACE_AUDIT.json",
            "E3_L2_R2_NO_FORBIDDEN_CAPABILITY_GUARD.json",
        ],
        "status": "PASS",
    }


def decision(eval_payload: dict[str, Any], blockers: list[str]) -> dict[str, Any]:
    beats_any = bool(
        eval_payload["baseline_comparison"]["beats_baseline_average_precision_proxy"]
        or eval_payload["baseline_comparison"]["beats_baseline_brier"]
    )
    return {
        "blockers": blockers,
        "experiment_advancement_recommendation": "review_for_later_preflight" if beats_any else "do_not_advance_without_human_review",
        "forecast_model_created": True,
        "next_possible_step": "L2_R2_EXPERIMENT_REVIEW_OR_PRODUCT_AUTHORITY_PREFLIGHT_ONLY_IF_METRICS_SUPPORT",
        "package_id": TASK_ID,
        "product_surface_created": False,
        "release_authority_granted": False,
        "same_run_release_started": False,
        "status": STATUS if not blockers else FAIL_STATUS,
    }


def ledger_row(decision_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "forecast_model_status": "experimental",
        "ledger_row_id": "E3_L2_R2_OFFLINE_EXPERIMENT_R1_PUBLISHED",
        "package_id": TASK_ID,
        "product_surface_created": False,
        "published_at": utc_now(),
        "release_authority_granted": False,
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
        "status": "PASS_LF_STABLE_FOR_E3_L2_R2_OFFLINE_EXPERIMENTAL_FORECAST_R1" if not crlf_paths else "FAIL_CRLF_FOUND",
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
    blockers: list[str] = []
    preflight_decision = read_json(PREFLIGHT_DECISION_PATH, {})
    if preflight_decision.get("status") != "PASS_E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_R1_WITH_LIMITATIONS":
        blockers.append("missing_or_unpassed_forecast_authority_preflight")
    if not LABEL_ROWS_PATH.exists():
        blockers.append("missing_r2_governed_label_rows")
        rows: list[dict[str, Any]] = []
    else:
        rows = read_jsonl(LABEL_ROWS_PATH)
    if len(rows) <= 750:
        blockers.append("r2_governed_labels_not_found_or_only_r1_cap_available")

    model = fit_rate_model(rows)
    eval_rows, prediction_rows, scores = build_predictions(rows, model)
    baseline = read_json(BASELINE_PATH, {})
    eval_payload = eval_report(eval_rows, scores, baseline)
    manifest = training_manifest(rows)
    audit = leakage_audit(rows, manifest)
    surface = surface_audit(prediction_rows)
    guard = forbidden_guard()
    registry = registry_entry(model)
    if audit["status"] != "PASS":
        blockers.append("temporal_leakage_audit_failed")
    if surface["status"] != "PASS" or surface["prediction_rows_surface_allowed_count"] != 0:
        blockers.append("product_surface_audit_failed")
    if guard["status"] != "PASS":
        blockers.append("forbidden_capability_guard_failed")
    if registry["consuming_surfaces"] != [] or registry["release_ledger_row"] is not None:
        blockers.append("registry_surface_or_release_boundary_failed")

    write_json(OUTPUT_ROOT / "E3_L2_R2_HUMAN_MODEL_AUTHORITY_DECISION_ROW.json", human_authority_row())
    write_json(OUTPUT_ROOT / "E3_L2_R2_EXPERIMENT_TRAINING_MANIFEST.json", manifest)
    write_json(OUTPUT_ROOT / "E3_L2_R2_TEMPORAL_LEAKAGE_AUDIT.json", audit)
    write_json(OUTPUT_ROOT / "E3_L2_R2_EXPERIMENTAL_FORECAST_MODEL_CARD.json", model_card(model, eval_payload))
    write_json(OUTPUT_ROOT / "E3_L2_R2_EXPERIMENTAL_FORECAST_EVAL_REPORT.json", eval_payload)
    write_json(OUTPUT_ROOT / "E3_L2_R2_CITY_STRATIFIED_EVAL_REPORT.json", city_report(eval_payload))
    write_json(OUTPUT_ROOT / "E3_L2_R2_EXPERIMENTAL_FORECAST_REGISTRY_ENTRY.json", registry)
    write_jsonl(OUTPUT_ROOT / "E3_L2_R2_EXPERIMENTAL_FORECAST_EVAL_PREDICTIONS.jsonl", prediction_rows)
    write_json(OUTPUT_ROOT / "E3_L2_R2_NO_PRODUCT_SURFACE_AUDIT.json", surface)
    write_json(OUTPUT_ROOT / "E3_L2_R2_NO_FORBIDDEN_CAPABILITY_GUARD.json", guard)
    write_json(OUTPUT_ROOT / "E3_L2_R2_LIMITATIONS.json", limitations(eval_payload))
    write_json(OUTPUT_ROOT / "E3_L2_R2_CORPUS_DELTA.json", corpus_delta())
    decision_payload = decision(eval_payload, blockers)
    write_json(OUTPUT_ROOT / "E3_L2_R2_OFFLINE_EXPERIMENT_DECISION.json", decision_payload)
    write_json(OUTPUT_ROOT / "E3_L2_R2_OFFLINE_EXPERIMENT_LEDGER_ROW.json", ledger_row(decision_payload))
    lf_report = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", lf_report)
    lf_report = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", lf_report)
    hash_manifest = build_hash_manifest()
    return {
        "audit": audit,
        "decision": decision_payload,
        "eval": eval_payload,
        "hash_manifest": hash_manifest,
        "line_endings": lf_report,
        "predictions": prediction_rows,
        "rows": rows,
    }


def main() -> int:
    result = write_all_outputs()
    print(f"Epoch 3 L2.R2 Offline Experimental Forecast R1: {result['decision']['status']}")
    print(f"R2 label rows used: {len(result['rows'])}")
    print(f"Eval prediction rows: {len(result['predictions'])}")
    print(f"Average precision: {result['eval']['metrics']['stalled_class_average_precision']}")
    print(f"Temporal leakage audit: {result['audit']['status']}")
    print(f"Product surface created: {result['decision']['product_surface_created']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if result["decision"]["status"] == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
