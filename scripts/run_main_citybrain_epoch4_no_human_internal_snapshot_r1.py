#!/usr/bin/env python3
"""Create the Epoch 4 no-human internal snapshot R1.

This freezes the current no-human CityBrain Epoch 4 state for internal
orientation only. It does not create founder/operator session results, fuel,
training rows, live ingestion, forecasts, official actions, or source-truth
mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_no_human_internal_snapshot_r1"
PUBLICATION_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-no-human-internal-snapshot-r1"

STATUS = "PASS_MAIN_CITYBRAIN_EPOCH4_NO_HUMAN_INTERNAL_SNAPSHOT_R1_WITH_LIMITATIONS"

INPUTS = {
    "derived_fix_sequence": ROOT / "outputs" / "main_citybrain_epoch4_derived_fix_and_founder_input_sequence_r1" / "DERIVED_FIX_AND_FOUNDER_INPUT_SEQUENCE_DECISION.json",
    "derived_fix_overlay": ROOT / "outputs" / "main_citybrain_epoch4_derived_fix_promotion_overlay_r1" / "DERIVED_FIX_PROMOTION_OVERLAY_DECISION.json",
    "founder_probe_input_kit": ROOT / "outputs" / "main_citybrain_epoch4_founder_probe_input_kit_r2" / "FOUNDER_PROBE_INPUT_KIT_DECISION.json",
    "no_session_probe_reverify": ROOT / "outputs" / "main_citybrain_epoch4_no_session_probe_readiness_reverify_r1" / "NO_SESSION_PROBE_READINESS_REVERIFY_DECISION.json",
    "eval_expansion_final": ROOT / "outputs" / "main_citybrain_epoch4_eval_expansion_hardening_final_reverify_r1" / "EVAL_EXPANSION_HARDENING_FINAL_REVERIFY_DECISION.json",
    "eval_corpus_r2": ROOT / "outputs" / "main_citybrain_epoch4_eval_corpus_expansion_r2" / "EVAL_CORPUS_R2_INDEX.json",
    "challenge_suite": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_challenge_negative_suite_r1" / "PRODUCT_LOOP_CHALLENGE_NEGATIVE_SUITE_DECISION.json",
    "remediation_eval_sequence": ROOT / "outputs" / "main_citybrain_epoch4_remediation_execution_eval_corpus_sequence_r1" / "REMEDIATION_EXECUTION_EVAL_SEQUENCE_DECISION.json",
    "after_deepening_cross_track": ROOT / "outputs" / "main_citybrain_epoch4_after_deepening_cross_track_reverify_r1" / "DECISION.json",
    "product_loop_final": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_final_reverify_r1" / "PRODUCT_LOOP_FINAL_REVERIFY_DECISION.json",
    "data_maturity_product": ROOT / "outputs" / "main_citybrain_epoch4_data_maturity_diagnostic_product_r2" / "DATA_MATURITY_DIAGNOSTIC_PRODUCT_R2.json",
    "data_maturity_decision": ROOT / "outputs" / "main_citybrain_epoch4_data_maturity_diagnostic_product_r2" / "DECISION.json",
    "data_maturity_remediation": ROOT / "outputs" / "main_citybrain_epoch4_data_maturity_remediation_actions_r1" / "DATA_MATURITY_REMEDIATION_DECISION.json",
}

EXPECTED_FILES = [
    "CURRENT_EPOCH4_NO_HUMAN_STATE.json",
    "PRODUCT_LOOP_CAPABILITY_SUMMARY.json",
    "EVAL_CORPUS_SUMMARY.json",
    "REMEDIATION_OVERLAY_SUMMARY.json",
    "FOUNDER_PROBE_INPUT_KIT_STATUS.json",
    "DATA_MATURITY_CURRENT_STATE.json",
    "PARKED_ITEMS_REGISTER.json",
    "NEXT_DECISION_OPTIONS.json",
    "NO_SESSION_NO_FUEL_GUARD.json",
    "HASH_MANIFEST.json",
    "DECISION.json",
    "EPOCH4_NO_HUMAN_INTERNAL_SNAPSHOT.md",
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
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def status_of(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    return payload.get("status") or payload.get("decision_status") or payload.get("final_status")


def input_audit() -> list[dict[str, Any]]:
    rows = []
    for key, path in INPUTS.items():
        payload = read_json(path, {})
        rows.append({"key": key, "path": rel(path), "exists": path.exists(), "status": status_of(payload)})
    return rows


def publish(filenames: list[str]) -> None:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    for filename in filenames:
        source = SNAPSHOT_ROOT / filename
        if source.exists():
            (PUBLICATION_ROOT / filename).write_bytes(source.read_bytes())


def hash_manifest() -> dict[str, Any]:
    entries = []
    for scan_root in [SNAPSHOT_ROOT, PUBLICATION_ROOT]:
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*")):
            if not path.is_file() or path.name == "HASH_MANIFEST.json":
                continue
            entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "algorithm": "sha256",
        "artifact_id": "HASH_MANIFEST",
        "entries": entries,
        "entry_count": len(entries),
        "generated_at": now_iso(),
        "status": "PASS",
    }
    write_json(SNAPSHOT_ROOT / "HASH_MANIFEST.json", manifest)
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    (PUBLICATION_ROOT / "HASH_MANIFEST.json").write_bytes((SNAPSHOT_ROOT / "HASH_MANIFEST.json").read_bytes())
    return manifest


def verify_manifest(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing:{rel(path)}"]
    errors = []
    for entry in read_json(path, {}).get("entries", []):
        target = ROOT / entry["path"]
        if not target.exists():
            errors.append(f"missing:{entry['path']}")
        elif sha256_file(target) != entry["sha256"]:
            errors.append(f"mismatch:{entry['path']}")
    return errors


def build_snapshot() -> str:
    derived_sequence = read_json(INPUTS["derived_fix_sequence"], {})
    overlay = read_json(INPUTS["derived_fix_overlay"], {})
    kit = read_json(INPUTS["founder_probe_input_kit"], {})
    no_session = read_json(INPUTS["no_session_probe_reverify"], {})
    eval_final = read_json(INPUTS["eval_expansion_final"], {})
    eval_index = read_json(INPUTS["eval_corpus_r2"], {})
    challenge = read_json(INPUTS["challenge_suite"], {})
    product_loop = read_json(INPUTS["product_loop_final"], {})
    maturity = read_json(INPUTS["data_maturity_product"], {})
    maturity_decision = read_json(INPUTS["data_maturity_decision"], {})
    remediation = read_json(INPUTS["data_maturity_remediation"], {})

    write_json(
        SNAPSHOT_ROOT / "CURRENT_EPOCH4_NO_HUMAN_STATE.json",
        {
            "artifact_id": "CURRENT_EPOCH4_NO_HUMAN_STATE",
            "generated_at": now_iso(),
            "input_audit": input_audit(),
            "latest_sequence_status": derived_sequence.get("status"),
            "no_human_snapshot": True,
            "operator_fuel_created": False,
            "session_results_created": False,
            "source_truth_mutated": False,
            "status": "PASS_WITH_LIMITATIONS",
            "training_rows_created": False,
        },
    )
    write_json(
        SNAPSHOT_ROOT / "PRODUCT_LOOP_CAPABILITY_SUMMARY.json",
        {
            "artifact_id": "PRODUCT_LOOP_CAPABILITY_SUMMARY",
            "capability_state": "bounded local/replay product loop with Review Packet 360 and multi-family eval support",
            "limitations": product_loop.get("limitations", []),
            "product_loop_final_status": product_loop.get("status"),
            "review_packet_360_verified": product_loop.get("review_packet_360_verified"),
            "selected_family_count": product_loop.get("selected_family_count"),
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        SNAPSHOT_ROOT / "EVAL_CORPUS_SUMMARY.json",
        {
            "artifact_id": "EVAL_CORPUS_SUMMARY",
            "challenge_case_count": challenge.get("challenge_case_count"),
            "eval_corpus_case_count": eval_index.get("case_count") or eval_final.get("case_count"),
            "family_count": eval_index.get("family_count"),
            "families": eval_index.get("families", []),
            "final_reverify_status": eval_final.get("status"),
            "local_replay_only": True,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        SNAPSHOT_ROOT / "REMEDIATION_OVERLAY_SUMMARY.json",
        {
            "artifact_id": "REMEDIATION_OVERLAY_SUMMARY",
            "derived_overlay_status": overlay.get("status"),
            "maturity_remediation_status": remediation.get("status"),
            "overlay_count": overlay.get("overlay_count"),
            "promoted_to_canonical_truth": False,
            "promoted_to_source_truth": False,
            "source_truth_mutated": overlay.get("source_truth_mutated") is True,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        SNAPSHOT_ROOT / "FOUNDER_PROBE_INPUT_KIT_STATUS.json",
        {
            "artifact_id": "FOUNDER_PROBE_INPUT_KIT_STATUS",
            "card_count": kit.get("card_count"),
            "founder_probe_input_kit_status": kit.get("status"),
            "operator_fuel_created": kit.get("operator_fuel_created") is True,
            "response_template_ready": True,
            "session_results_created": kit.get("session_results_created") is True,
            "status": "PASS_WITH_LIMITATIONS",
            "training_rows_created": kit.get("training_rows_created") is True,
        },
    )
    write_json(
        SNAPSHOT_ROOT / "DATA_MATURITY_CURRENT_STATE.json",
        {
            "artifact_id": "DATA_MATURITY_CURRENT_STATE",
            "data_maturity_status": maturity.get("status"),
            "decision_status": maturity_decision.get("status"),
            "diagnostic_sections": maturity.get("diagnostic_sections", []),
            "overall_maturity_score_ref": maturity.get("overall_maturity_score_ref"),
            "remediation_plan_count": maturity_decision.get("remediation_plan_count"),
            "scorecard_count": maturity.get("scorecard_count"),
            "source_count": maturity.get("source_count"),
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    parked_items = [
        "actual founder probe session results",
        "external operator validation",
        "operator fuel accumulation",
        "training rows or learned labels",
        "learned ranking or model arming",
        "live ingestion or production monitoring",
        "ForecastPacket or product forecast surface",
        "official workflow/action/case/ticket/dispatch/control/enforcement",
        "source-truth or canonical-truth mutation",
        "maturity score inflation as fact",
    ]
    write_json(
        SNAPSHOT_ROOT / "PARKED_ITEMS_REGISTER.json",
        {
            "artifact_id": "PARKED_ITEMS_REGISTER",
            "parked_item_count": len(parked_items),
            "parked_items": parked_items,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        SNAPSHOT_ROOT / "NEXT_DECISION_OPTIONS.json",
        {
            "artifact_id": "NEXT_DECISION_OPTIONS",
            "options": [
                {
                    "option_id": "keep_no_human_path",
                    "description": "Use this snapshot as current internal state and continue non-human hardening.",
                },
                {
                    "option_id": "run_founder_probe_import_later",
                    "description": "Fill the response template with real package-specific founder input, then run response import and reverify.",
                },
                {
                    "option_id": "review_derived_overlays",
                    "description": "Inspect derived overlays and decide which remain candidate-only before any broader review.",
                },
            ],
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        SNAPSHOT_ROOT / "NO_SESSION_NO_FUEL_GUARD.json",
        {
            "artifact_id": "NO_SESSION_NO_FUEL_GUARD",
            "dispositions_created": False,
            "founder_session_results_created": False,
            "operator_fuel_created": False,
            "session_results_created": False,
            "training_rows_created": False,
            "status": "PASS",
        },
    )
    markdown = f"""# Epoch 4 No-Human Internal Snapshot R1

Status: `{STATUS}`

## Current State

- Product loop: local/replay/review-only, Review Packet 360 verified.
- Eval corpus: {eval_index.get('case_count') or eval_final.get('case_count')} cases across {eval_index.get('family_count')} families.
- Challenge suite: {challenge.get('challenge_case_count')} challenge/negative cases.
- Derived overlays: {overlay.get('overlay_count')} derived-only entries.
- Founder input kit: {kit.get('card_count')} task cards with response template/schema/rubric.
- Data maturity: {maturity.get('source_count')} sources, maturity score reference {maturity.get('overall_maturity_score_ref')}.

## Parked

Founder session results, operator fuel, training rows, live ingestion, forecasts, official workflow/action, and source-truth mutation remain parked.
"""
    write_text(SNAPSHOT_ROOT / "EPOCH4_NO_HUMAN_INTERNAL_SNAPSHOT.md", markdown)
    write_json(
        SNAPSHOT_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "forbidden_capabilities_created": [],
            "founder_probe_input_kit_ready": True,
            "generated_at": now_iso(),
            "operator_fuel_created": False,
            "package_id": "MAIN-CITYBRAIN-EPOCH4-NO-HUMAN-INTERNAL-SNAPSHOT-R1",
            "session_results_created": False,
            "source_truth_mutated": False,
            "status": STATUS,
            "training_rows_created": False,
        },
    )
    publish([filename for filename in EXPECTED_FILES if filename != "HASH_MANIFEST.json"])
    hash_manifest()
    return STATUS


def required_paths() -> list[Path]:
    return [SNAPSHOT_ROOT / filename for filename in EXPECTED_FILES]


def validate_all() -> list[str]:
    errors: list[str] = []
    missing = [rel(path) for path in required_paths() if not path.exists()]
    errors.extend(f"missing:{path}" for path in missing)
    if missing:
        return errors
    decision = read_json(SNAPSHOT_ROOT / "DECISION.json", {})
    state = read_json(SNAPSHOT_ROOT / "CURRENT_EPOCH4_NO_HUMAN_STATE.json", {})
    guard = read_json(SNAPSHOT_ROOT / "NO_SESSION_NO_FUEL_GUARD.json", {})
    eval_summary = read_json(SNAPSHOT_ROOT / "EVAL_CORPUS_SUMMARY.json", {})
    overlay = read_json(SNAPSHOT_ROOT / "REMEDIATION_OVERLAY_SUMMARY.json", {})
    kit = read_json(SNAPSHOT_ROOT / "FOUNDER_PROBE_INPUT_KIT_STATUS.json", {})
    if decision.get("status") != STATUS:
        errors.append("decision_status_failed")
    for payload_name, payload in [("decision", decision), ("state", state), ("guard", guard)]:
        for key in ["session_results_created", "operator_fuel_created", "training_rows_created", "source_truth_mutated"]:
            if payload.get(key) is True:
                errors.append(f"{payload_name}:{key}:boundary_failed")
    if eval_summary.get("eval_corpus_case_count") != 48 or eval_summary.get("challenge_case_count") != 32:
        errors.append("eval_summary_counts_failed")
    if overlay.get("overlay_count") != 50 or overlay.get("promoted_to_source_truth") is not False:
        errors.append("overlay_summary_guard_failed")
    if kit.get("card_count") != 16 or kit.get("session_results_created") is not False:
        errors.append("kit_summary_guard_failed")
    errors.extend(verify_manifest(SNAPSHOT_ROOT / "HASH_MANIFEST.json"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if not args.validate_only:
        print(build_snapshot())
    errors = validate_all()
    if errors:
        print("VALIDATION FAILED")
        for error in errors:
            print(error)
        return 1
    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
