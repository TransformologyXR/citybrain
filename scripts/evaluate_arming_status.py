#!/usr/bin/env python3
"""Evaluate CityBrain Epoch 3 arming thresholds.

The evaluator intentionally reads pre-aggregated metric snapshots. Thresholds
come from the manifest as structured `{metric, op, value, filters}` objects;
crossings publish ledger-ready events but never start work.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MISSING = object()
SUPPORTED_OPS = {"==", "!=", ">=", ">", "<=", "<", "contains_all", "exists", "not_exists"}


@dataclass
class RequirementResult:
    id: str
    metric: str
    op: str
    expected: Any
    actual: Any
    passed: bool
    filters: dict[str, Any]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "metric": self.metric,
            "op": self.op,
            "expected": self.expected,
            "actual": None if self.actual is MISSING else self.actual,
            "passed": self.passed,
            "filters": self.filters,
            "error": self.error,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def get_path(obj: dict[str, Any], dotted: str) -> Any:
    cur: Any = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return MISSING
    return cur


def evaluate_op(actual: Any, op: str, expected: Any) -> bool:
    if op not in SUPPORTED_OPS:
        raise ValueError(f"unsupported op: {op}")
    if op == "exists":
        return actual is not MISSING and actual is not None
    if op == "not_exists":
        return actual is MISSING or actual is None
    if actual is MISSING:
        return False
    if op == "==":
        return actual == expected
    if op == "!=":
        return actual != expected
    if op == ">=":
        return actual >= expected
    if op == ">":
        return actual > expected
    if op == "<=":
        return actual <= expected
    if op == "<":
        return actual < expected
    if op == "contains_all":
        return set(expected).issubset(set(actual or []))
    return False


def filter_guard(req: dict[str, Any], metrics: dict[str, Any]) -> tuple[bool, str | None]:
    """Apply CityBrain-specific filter semantics over aggregate snapshots.

    The manifest says primary R3 thresholds require `propensity_status=known`.
    If a snapshot declares propensity-unknown training coverage, fail those
    filtered requirements even if a raw count would otherwise pass.
    """
    filters = req.get("filters") or {}
    if filters.get("propensity_status") != "known":
        return True, None
    coverage = get_path(metrics, "watch.exposure_logging.coverage")
    if coverage in {"propensity_unknown_in_training_candidates", "unknown", "partial"}:
        return False, "propensity_status_known_filter_failed"
    return True, None


def evaluate_requirement(req: dict[str, Any], metrics: dict[str, Any]) -> RequirementResult:
    actual = get_path(metrics, req["metric"])
    guard_passed, guard_error = filter_guard(req, metrics)
    try:
        op_passed = evaluate_op(actual, req["op"], req.get("value"))
        passed = guard_passed and op_passed
        error = guard_error
    except Exception as exc:
        passed = False
        error = str(exc)
    return RequirementResult(
        id=req["id"],
        metric=req["metric"],
        op=req["op"],
        expected=req.get("value"),
        actual=actual,
        passed=passed,
        filters=req.get("filters") or {},
        error=error,
    )


def evaluate_block(block: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    results = [evaluate_requirement(req, metrics) for req in block.get("requires", [])]
    passed = all(result.passed for result in results)
    return {
        "passed": passed,
        "state": "armed" if passed else "not_armed",
        "arming_semantics": block.get("arming_semantics", "MAY_BEGIN_UNDER_CADENCE_AFTER_ARMING_LEDGER_ROW_NOT_STARTED"),
        "operator_surface": block.get("operator_surface"),
        "requirements": [result.to_dict() for result in results],
        "failed_requirement_ids": [result.id for result in results if not result.passed],
    }


def transition_crossings(current: dict[str, Any], previous: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not previous:
        return []
    previous_states: dict[str, str | None] = {}
    for group in ("conditionally_armed", "blocked_until"):
        for increment_id, status in previous.get(group, {}).items():
            previous_states[increment_id] = status.get("state")

    crossings = []
    for group in ("conditionally_armed", "blocked_until"):
        for increment_id, status in current.get(group, {}).items():
            if previous_states.get(increment_id, "not_armed") != "armed" and status.get("state") == "armed":
                crossings.append(
                    {
                        "ledger_event": "EPOCH3_ARMING_THRESHOLD_CROSSED",
                        "increment_id": increment_id,
                        "previous_state": previous_states.get(increment_id, "not_armed"),
                        "new_state": "armed",
                        "arming_semantics": "MAY_BEGIN_UNDER_CADENCE_AFTER_ARMING_LEDGER_ROW_NOT_STARTED",
                        "auto_started_work": False,
                    }
                )
    return crossings


def evaluate(
    manifest: dict[str, Any],
    metrics: dict[str, Any],
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    conditionally_armed = {
        increment_id: evaluate_block(block, metrics)
        for increment_id, block in manifest.get("conditionally_armed", {}).items()
    }
    blocked_until = {
        increment_id: evaluate_block(block, metrics)
        for increment_id, block in manifest.get("blocked_until", {}).items()
    }
    not_armed = [
        increment_id
        for increment_id, status in {**conditionally_armed, **blocked_until}.items()
        if status["state"] != "armed"
    ]
    report = {
        "evaluator_id": manifest["evaluator"]["id"],
        "gate_id": manifest["gate_id"],
        "metrics_snapshot_id": metrics.get("metrics_snapshot_id"),
        "status": "PASS_E3_ENTRY_FOR_DESCRIPTIVE_AND_HARNESS_WORK_WITH_LIMITATIONS",
        "arming_semantics": manifest.get("arming_semantics"),
        "armed_now": manifest.get("armed_now", []),
        "conditionally_armed": conditionally_armed,
        "blocked_until": blocked_until,
        "not_armed": not_armed,
        "threshold_crossings": [],
        "non_claims": manifest.get("non_claims", []),
        "created_at": utc_now(),
    }
    report["threshold_crossings"] = transition_crossings(report, previous)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Epoch 3 arming thresholds")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--metrics", required=True, type=Path)
    parser.add_argument("--previous", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    manifest = load_json(args.manifest)
    metrics = load_json(args.metrics)
    previous = load_json(args.previous) if args.previous else None
    report = evaluate(manifest, metrics, previous)
    if args.out:
        write_json(args.out, report)
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
