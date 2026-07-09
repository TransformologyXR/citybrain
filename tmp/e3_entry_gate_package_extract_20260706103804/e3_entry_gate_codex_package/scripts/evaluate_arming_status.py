#!/usr/bin/env python3
"""Reference evaluator for the CityBrain Epoch 3 arming manifest.

This script is intentionally dependency-free. It evaluates pre-aggregated metric
snapshots against structured requirements in epoch3_arming_manifest.json.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


MISSING = object()


@dataclass
class RequirementResult:
    id: str
    metric: str
    op: str
    expected: Any
    actual: Any
    passed: bool
    filters: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "metric": self.metric,
            "op": self.op,
            "expected": self.expected,
            "actual": None if self.actual is MISSING else self.actual,
            "passed": self.passed,
            "filters": self.filters or {},
            "error": self.error,
        }


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_path(obj: Dict[str, Any], dotted: str) -> Any:
    cur: Any = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return MISSING
    return cur


def evaluate_op(actual: Any, op: str, expected: Any) -> bool:
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
    raise ValueError(f"unsupported op: {op}")


def evaluate_requirement(req: Dict[str, Any], metrics: Dict[str, Any]) -> RequirementResult:
    actual = get_path(metrics, req["metric"])
    try:
        passed = evaluate_op(actual, req["op"], req.get("value"))
        error = None
    except Exception as exc:  # keep reportable rather than crashing gate
        passed = False
        error = str(exc)
    return RequirementResult(
        id=req["id"],
        metric=req["metric"],
        op=req["op"],
        expected=req.get("value"),
        actual=actual,
        passed=passed,
        filters=req.get("filters"),
        error=error,
    )


def evaluate_block(block: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
    results = [evaluate_requirement(req, metrics) for req in block.get("requires", [])]
    passed = all(r.passed for r in results)
    return {
        "passed": passed,
        "state": "armed" if passed else "not_armed",
        "requirements": [r.to_dict() for r in results],
        "failed_requirement_ids": [r.id for r in results if not r.passed],
    }


def transition_crossings(current: Dict[str, Any], previous: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not previous:
        return []
    crossings: List[Dict[str, Any]] = []
    prev_states = {}
    for group in ("conditionally_armed", "blocked_until"):
        for inc, status in previous.get(group, {}).items():
            prev_states[inc] = status.get("state")
    for group in ("conditionally_armed", "blocked_until"):
        for inc, status in current.get(group, {}).items():
            if prev_states.get(inc) != "armed" and status.get("state") == "armed":
                crossings.append({
                    "ledger_event": "EPOCH3_ARMING_THRESHOLD_CROSSED",
                    "increment_id": inc,
                    "previous_state": prev_states.get(inc, "not_armed"),
                    "new_state": "armed",
                    "arming_semantics": "MAY_BEGIN_UNDER_CADENCE_AFTER_ARMING_LEDGER_ROW_NOT_STARTED",
                })
    return crossings


def evaluate(manifest: Dict[str, Any], metrics: Dict[str, Any], previous: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cond = {inc: evaluate_block(block, metrics) for inc, block in manifest.get("conditionally_armed", {}).items()}
    blocked = {inc: evaluate_block(block, metrics) for inc, block in manifest.get("blocked_until", {}).items()}

    not_armed = []
    for inc, status in {**cond, **blocked}.items():
        if status["state"] != "armed":
            not_armed.append(inc)

    report = {
        "evaluator_id": manifest["evaluator"]["id"],
        "gate_id": manifest["gate_id"],
        "metrics_snapshot_id": metrics.get("metrics_snapshot_id"),
        "status": "PASS_E3_ENTRY_FOR_DESCRIPTIVE_AND_HARNESS_WORK_WITH_LIMITATIONS",
        "arming_semantics": manifest.get("arming_semantics"),
        "armed_now": manifest.get("armed_now", []),
        "conditionally_armed": cond,
        "blocked_until": blocked,
        "not_armed": not_armed,
        "threshold_crossings": [],
        "non_claims": manifest.get("non_claims", []),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    report["threshold_crossings"] = transition_crossings(report, previous)
    return report


def main() -> None:
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

    text = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
