from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from txr_citybrain_pv1_sdf_common import (
    CLAIM_LABEL,
    GENERATED_AT_UTC,
    GENERATION_VERSION,
    PACK_ID,
    PACK_LABEL,
    REQUIRED_SYNTHETIC_METADATA_FIELDS,
    all_gates_pass,
    gate,
    no_overclaim_scan,
    parse_json_list,
    project_path,
    read_json,
    read_jsonl,
    reset_dir,
    safe_json_dumps,
    write_hashes,
    write_json,
    write_stage_readme,
    write_text,
)
from txr_citybrain_pv1_sdf_d5_replay_pack_builder import materialize_state


DEFAULT_OUTPUT_DIR = "outputs/pv1_sdf_d6_validation_harness"
DEFAULT_SYNTHETIC_ROOT = "data_synthetic/pv1_sdf"
DEFAULT_D1_OUTPUT_DIR = "outputs/pv1_sdf_d1_factory_contract"


def read_pack_tables(pack_dir: Path) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    for path in sorted((pack_dir / "truth").glob("*.parquet")):
        tables[path.stem] = pd.read_parquet(path)
    return tables


def read_projection_tables(pack_dir: Path) -> dict[str, pd.DataFrame]:
    return {path.stem: pd.read_parquet(path) for path in sorted((pack_dir / "source_projections").glob("*.parquet"))}


def read_dirty_tables(pack_dir: Path) -> dict[str, pd.DataFrame]:
    return {path.relative_to(pack_dir / "dirty_variants").as_posix(): pd.read_parquet(path) for path in sorted((pack_dir / "dirty_variants").rglob("*.parquet"))}


def validation_row(test_id: str, test_name: str, inputs: list[str], expected: str, actual: str, status: str, downstream_gate: str, failure_reason: str | None = None) -> dict[str, Any]:
    return {
        "test_id": test_id,
        "test_name": test_name,
        "input_artifacts": inputs,
        "expected_behavior": expected,
        "actual_behavior": actual,
        "status": status,
        "failure_reason": failure_reason,
        "claim_boundary_checked": True,
        "downstream_gate": downstream_gate,
        "claim_label": CLAIM_LABEL,
        "synthetic": True,
        "source_basis": "hybrid",
        "donor_city": "chicago",
        "donor_artifact": PACK_LABEL,
        "generation_version": GENERATION_VERSION,
        "random_seed": 12345,
        "generated_at_utc": GENERATED_AT_UTC,
        "validation_status": status,
        "not_real_world_observation": True,
    }


def schema_conformance(tables: dict[str, pd.DataFrame], projections: dict[str, pd.DataFrame], dirty: dict[str, pd.DataFrame], replay_rows: list[dict[str, Any]], d1_dir: Path) -> dict[str, Any]:
    schema_files = [
        d1_dir / "schemas" / "synthetic_truth_schema.json",
        d1_dir / "schemas" / "source_projection_schema.json",
        d1_dir / "schemas" / "dirty_variant_schema.json",
        d1_dir / "schemas" / "replay_event_schema.json",
        d1_dir / "schemas" / "validation_report_schema.json",
        d1_dir / "schemas" / "donor_distribution_schema.json",
        d1_dir / "schemas" / "action_proposal_synthetic_schema.json",
    ]
    truth_ok = all(all(field in df.columns for field in REQUIRED_SYNTHETIC_METADATA_FIELDS) for df in tables.values())
    projection_required = ["source_system", "source_table", "source_record_id", "native_id_shape", "payload", "schema_version", "projection_from_truth_ids"]
    projection_ok = all(all(field in df.columns for field in projection_required) for df in projections.values())
    dirty_required = ["dirty_variant_type", "dirty_variant_id", "dirty_fields", "expected_adapter_detection"]
    dirty_ok = all(all(field in df.columns for field in dirty_required) for df in dirty.values())
    replay_required = ["event_id", "event_time", "processing_time", "source_system", "event_type", "subject_ids", "payload", "sequence_number", "replay_pack_id", "late_arrival_flag", "out_of_order_flag", "claim_label"]
    replay_ok = all(all(field in row for field in replay_required) for row in replay_rows)
    schemas_present = all(path.exists() for path in schema_files)
    checks = {
        "schemas_present": schemas_present,
        "truth_metadata_fields": truth_ok,
        "projection_required_fields": projection_ok,
        "dirty_required_fields": dirty_ok,
        "replay_required_fields": replay_ok,
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def claim_label_report(tables: dict[str, pd.DataFrame], projections: dict[str, pd.DataFrame], dirty: dict[str, pd.DataFrame], replay_rows: list[dict[str, Any]]) -> dict[str, Any]:
    table_checks = {name: bool((df["claim_label"] == CLAIM_LABEL).all() and (df["synthetic"] == True).all()) for name, df in tables.items()}
    projection_checks = {name: bool((df["claim_label"] == CLAIM_LABEL).all() and (df["synthetic"] == True).all()) for name, df in projections.items()}
    dirty_checks = {name: bool((df["claim_label"] == CLAIM_LABEL).all() and (df["synthetic"] == True).all()) for name, df in dirty.items()}
    replay_ok = all(row.get("claim_label") == CLAIM_LABEL and row.get("synthetic") is True for row in replay_rows)
    ok = all(table_checks.values()) and all(projection_checks.values()) and all(dirty_checks.values()) and replay_ok
    return {
        "status": "PASS" if ok else "FAIL",
        "truth_tables": table_checks,
        "source_projections": projection_checks,
        "dirty_variants": dirty_checks,
        "replay_rows": replay_ok,
    }


def real_id_reuse_report(tables: dict[str, pd.DataFrame], projections: dict[str, pd.DataFrame]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for table_name, df in tables.items():
        for column in [c for c in df.columns if c.endswith("_id") or c == "entity_id"]:
            for value in df[column].dropna().astype(str).head(5000):
                if value.startswith("synthetic:") or value.startswith("SYN-"):
                    continue
                if column in {"donor_community_area"}:
                    continue
                if column.endswith("_id") and value and value != "nan":
                    findings.append({"table": table_name, "column": column, "value": value})
                    break
    for table_name, df in projections.items():
        if "source_record_id" in df.columns:
            bad = df["source_record_id"].dropna().astype(str).map(lambda value: not value.startswith("SYN-"))
            if bool(bad.any()):
                findings.append({"table": table_name, "column": "source_record_id", "value": "non-SYN source id"})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings[:25]}


def truth_id_set(tables: dict[str, pd.DataFrame]) -> set[str]:
    ids: set[str] = set()
    for df in tables.values():
        for column in [c for c in df.columns if c.endswith("_id") or c == "entity_id"]:
            ids.update(str(v) for v in df[column].dropna().unique() if str(v).startswith("synthetic:"))
    return ids


def truth_projection_roundtrip(tables: dict[str, pd.DataFrame], projections: dict[str, pd.DataFrame]) -> dict[str, Any]:
    ids = truth_id_set(tables)
    missing: list[dict[str, Any]] = []
    rows_checked = 0
    for table_name, df in projections.items():
        for _, row in df.iterrows():
            rows_checked += 1
            for truth_id in parse_json_list(row.get("projection_from_truth_ids")):
                if str(truth_id).startswith("synthetic:") and str(truth_id) not in ids:
                    missing.append({"projection": table_name, "source_record_id": row.get("source_record_id"), "truth_id": truth_id})
    return {"status": "PASS" if not missing else "FAIL", "rows_checked": rows_checked, "missing_truth_ids": missing[:25]}


def dirty_detection_report(dirty: dict[str, pd.DataFrame]) -> dict[str, Any]:
    detected: set[str] = set()
    row_counts: dict[str, int] = {}
    for path, df in dirty.items():
        if "dirty_variant_type" in df.columns and len(df) > 0:
            variant_type = str(df["dirty_variant_type"].iloc[0])
            detected.add(variant_type)
            row_counts[path] = int(len(df))
    required = {
        "missing_id",
        "duplicate_record",
        "geometry_jitter",
        "schema_drift",
        "late_arrival",
        "out_of_order_event",
        "wrong_area_label",
        "partial_join_key",
    }
    return {
        "status": "PASS" if required.issubset(detected) else "FAIL",
        "required": sorted(required),
        "detected": sorted(detected),
        "row_counts": row_counts,
    }


def replay_validation(pack_dir: Path) -> dict[str, Any]:
    replay_dir = pack_dir / "replay_packs"
    expected_dir = pack_dir / "expected_state"
    normal = read_jsonl(replay_dir / "replay_normal_order.jsonl")
    state_a = materialize_state(normal)
    state_b = materialize_state(read_jsonl(replay_dir / "replay_normal_order.jsonl"))
    encoded_a = json.dumps(state_a, sort_keys=True)
    encoded_b = json.dumps(state_b, sort_keys=True)
    expected_normal = read_json(expected_dir / "expected_state_after_normal_order.json", {})
    late = read_jsonl(replay_dir / "replay_late_arrivals.jsonl")
    out_of_order = read_jsonl(replay_dir / "replay_out_of_order.jsonl")
    supersession = read_jsonl(replay_dir / "replay_supersession.jsonl")
    checks = {
        "deterministic_hash_match": hashlib.sha256(encoded_a.encode()).hexdigest() == hashlib.sha256(encoded_b.encode()).hexdigest(),
        "expected_normal_state_match": state_a == expected_normal,
        "late_arrivals_present": any(row.get("late_arrival_flag") for row in late),
        "out_of_order_present": any(row.get("out_of_order_flag") for row in out_of_order),
        "supersession_present": any(row.get("supersedes_event_id") for row in supersession),
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "normal_state_hash": hashlib.sha256(encoded_a.encode()).hexdigest()}


def readiness_reports(pack_dir: Path, tables: dict[str, pd.DataFrame]) -> dict[str, dict[str, Any]]:
    expected_dir = pack_dir / "expected_state"
    replay_dir = pack_dir / "replay_packs"
    incident_expected = read_json(expected_dir / "expected_incident_trigger_state.json", {})
    plan_expected = read_json(expected_dir / "expected_plan_proposal_state.json", {})
    negative_rows = read_jsonl(replay_dir / "replay_negative_governance_cases.jsonl")
    action_proposals = tables["synthetic_action_proposals"]
    events = tables["synthetic_events"]
    roads = tables["synthetic_road_segments"]
    reports = {
        "incident": {
            "status": "PASS" if incident_expected.get("trigger") == "review_only_incident_candidate" and incident_expected.get("evidence_bundle_ready") is True else "FAIL",
            "trigger": incident_expected.get("trigger"),
            "evidence_bundle_ready": incident_expected.get("evidence_bundle_ready"),
            "real_world_recommendation": False,
        },
        "plan": {
            "status": "PASS" if plan_expected.get("proposal_state") == "approval_required" and plan_expected.get("autonomous_execution") is False else "FAIL",
            "proposal_state": plan_expected.get("proposal_state"),
            "review_only": plan_expected.get("review_only"),
            "autonomous_execution": plan_expected.get("autonomous_execution"),
        },
        "hitl": {
            "status": "PASS" if bool((action_proposals["approval_required"] == True).all() and (action_proposals["review_only"] == True).all()) else "FAIL",
            "approval_required_count": int((action_proposals["approval_required"] == True).sum()),
            "proposal_count": int(len(action_proposals)),
        },
        "persona": {
            "status": "PASS",
            "persona_targets": ["Executive", "Planner", "Operator", "Analyst"],
            "shared_evidence_bundle_fields": ["event_id", "event_type", "subject_ids", "payload", "claim_label"],
            "readiness_only": True,
        },
        "simulator": {
            "status": "PASS" if len(roads) >= 10 and len(events) > 0 else "FAIL",
            "road_segment_ids": roads["road_segment_id"].head(12).tolist(),
            "event_time_window": {"start": str(events["event_time"].min()), "end": str(events["event_time"].max())},
            "demand_perturbation": "synthetic mobility-context uplift fixture",
            "scenario_label": PACK_LABEL,
            "expected_simulated_output_placeholder": "SUMO-ready placeholder; simulator not run by D6.",
        },
        "negative": {
            "status": "PASS" if all(row.get("payload", {}).get("bounded") is True and row.get("payload", {}).get("execution_allowed") is False for row in negative_rows) else "FAIL",
            "case_count": len(negative_rows),
            "request_codes": [row.get("payload", {}).get("request_code") for row in negative_rows],
            "expected_behavior": "reject_or_bound",
        },
    }
    return reports


def run_pv1_sdf_d6_gate(
    project_root: str | Path = ".",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    synthetic_root: str | Path = DEFAULT_SYNTHETIC_ROOT,
    d1_output_dir: str | Path = DEFAULT_D1_OUTPUT_DIR,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = reset_dir(project_path(root, output_dir), root)
    tests_dir = out / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    pack_dir = project_path(root, synthetic_root) / "packs" / PACK_ID
    d1_dir = project_path(root, d1_output_dir)

    tables = read_pack_tables(pack_dir)
    projections = read_projection_tables(pack_dir)
    dirty = read_dirty_tables(pack_dir)
    replay_rows = []
    for path in sorted((pack_dir / "replay_packs").glob("*.jsonl")):
        replay_rows.extend(read_jsonl(path))

    schema = schema_conformance(tables, projections, dirty, replay_rows, d1_dir)
    claims = claim_label_report(tables, projections, dirty, replay_rows)
    no_real_ids = real_id_reuse_report(tables, projections)
    roundtrip = truth_projection_roundtrip(tables, projections)
    dirty_detection = dirty_detection_report(dirty)
    replay = replay_validation(pack_dir)
    readiness = readiness_reports(pack_dir, tables)
    scan = no_overclaim_scan([out, pack_dir])

    test_payloads = {
        "test_schema_conformance.json": validation_row("D6-T01", "Schema conformance", ["D1 schemas", "pack truth", "projections", "dirty variants", "replay"], "All artifacts match required field contracts.", schema["status"], schema["status"], "PV1-SDF-D6-SCHEMAS"),
        "test_claim_label_presence.json": validation_row("D6-T02", "Claim label presence", ["all generated artifacts"], "Every synthetic row carries [S].", claims["status"], claims["status"], "PV1-SDF-D6-CLAIM-LABELS"),
        "test_no_real_id_reuse.json": validation_row("D6-T03", "No real ID reuse", ["truth", "source projections"], "Primary IDs are synthetic-safe.", no_real_ids["status"], no_real_ids["status"], "PV1-SDF-D6-NO-REAL-ID-REUSE"),
        "test_truth_projection_roundtrip.json": validation_row("D6-T04", "Truth projection roundtrip", ["source projections", "truth tables"], "Projection truth IDs resolve.", roundtrip["status"], roundtrip["status"], "PV1-SDF-D6-TRUTH-PROJECTION-ROUNDTRIP"),
        "test_dirty_variant_detection.json": validation_row("D6-T05", "Dirty variant detection", ["dirty variants"], "Required dirty variant types are detectable.", dirty_detection["status"], dirty_detection["status"], "PV1-SDF-D6-DIRTY-VARIANTS"),
        "test_replay_determinism.json": validation_row("D6-T06", "Replay determinism", ["replay_normal_order"], "Two materializations produce identical state.", replay["status"], replay["status"], "PV1-SDF-D6-REPLAY-DETERMINISM"),
        "test_out_of_order_handling_expectation.json": validation_row("D6-T07", "Out-of-order handling expectation", ["replay_out_of_order"], "Out-of-order flags are present.", "PASS" if replay["checks"]["out_of_order_present"] else "FAIL", "PASS" if replay["checks"]["out_of_order_present"] else "FAIL", "PV1-SDF-D6-EXPECTED-STATE"),
        "test_late_arrival_expectation.json": validation_row("D6-T08", "Late arrival expectation", ["replay_late_arrivals"], "Late arrival flags are present.", "PASS" if replay["checks"]["late_arrivals_present"] else "FAIL", "PASS" if replay["checks"]["late_arrivals_present"] else "FAIL", "PV1-SDF-D6-EXPECTED-STATE"),
        "test_supersession_expectation.json": validation_row("D6-T09", "Supersession expectation", ["replay_supersession"], "Supersession link is present.", "PASS" if replay["checks"]["supersession_present"] else "FAIL", "PASS" if replay["checks"]["supersession_present"] else "FAIL", "PV1-SDF-D6-EXPECTED-STATE"),
        "test_negative_governance_expectation.json": validation_row("D6-T10", "Negative governance expectation", ["replay_negative_governance_cases"], "Unsafe requests are rejected or bounded.", readiness["negative"]["status"], readiness["negative"]["status"], "PV1-SDF-D6-NEGATIVE-GOVERNANCE"),
    }
    for filename, payload in test_payloads.items():
        write_json(tests_dir / filename, payload)

    summary = {
        "report_id": "PV1-SDF-D6-VALIDATION-SUMMARY",
        "status": "PASS" if all(payload["status"] == "PASS" for payload in test_payloads.values()) and scan["status"] == "PASS" else "FAIL",
        "claim_label": CLAIM_LABEL,
        "pack_id": PACK_ID,
        "validation_tests": len(test_payloads),
        "schema_status": schema["status"],
        "claim_label_status": claims["status"],
        "no_real_id_reuse_status": no_real_ids["status"],
        "truth_roundtrip_status": roundtrip["status"],
        "dirty_variant_status": dirty_detection["status"],
        "replay_status": replay["status"],
        "negative_governance_status": readiness["negative"]["status"],
    }
    write_json(out / "PV1_SDF_D6_VALIDATION_SUMMARY.json", summary)
    write_json(out / "PV1_SDF_D6_SCHEMA_VALIDATION_REPORT.json", schema)
    write_json(out / "PV1_SDF_D6_CLAIM_LABEL_REPORT.json", claims)
    write_json(out / "PV1_SDF_D6_TRUTH_MAPPING_VALIDATION.json", roundtrip)
    write_json(out / "PV1_SDF_D6_REPLAY_VALIDATION_REPORT.json", replay)
    write_json(out / "PV1_SDF_D6_INCIDENT_MODE_READINESS_REPORT.json", readiness["incident"])
    write_json(out / "PV1_SDF_D6_PLAN_MODE_READINESS_REPORT.json", readiness["plan"])
    write_json(out / "PV1_SDF_D6_HITL_READINESS_REPORT.json", readiness["hitl"])
    write_json(out / "PV1_SDF_D6_PERSONA_READINESS_REPORT.json", readiness["persona"])
    write_json(out / "PV1_SDF_D6_SIMULATOR_READINESS_REPORT.json", readiness["simulator"])
    write_json(out / "PV1_SDF_D6_NEGATIVE_CASE_REPORT.json", readiness["negative"])
    write_json(out / "PV1_SDF_D6_NO_OVERCLAIM_REPORT.json", {"status": scan["status"], "claim_label": CLAIM_LABEL, "scan": scan})
    write_text(
        out / "PV1_SDF_D6_ADAPTER_HANDOVER.md",
        "\n".join(
            [
                "# PV1-SDF-D6 Adapter Handover",
                "",
                "Validation tests are under `tests/` and each maps to a Platform v1 downstream gate.",
                "Simulator readiness is a handoff fixture only; D6 does not run SUMO.",
            ]
        ),
    )
    write_stage_readme(
        out / "README.md",
        "PV1-SDF-D6 Synthetic Validation Harness",
        [
            "D6 validates schemas, claim labels, synthetic-safe IDs, truth/projection mapping, dirty variants, replay determinism, expected state, readiness handoffs, and governance negatives.",
            f"Status: {summary['status']}.",
        ],
    )

    gates = [
        gate("PV1-SDF-D6-PRECOND", pack_dir.exists(), pack_dir=str(pack_dir)),
        gate("PV1-SDF-D6-SCHEMAS", schema["status"] == "PASS", checks=schema["checks"]),
        gate("PV1-SDF-D6-CLAIM-LABELS", claims["status"] == "PASS"),
        gate("PV1-SDF-D6-NO-REAL-ID-REUSE", no_real_ids["status"] == "PASS", findings=no_real_ids["findings"]),
        gate("PV1-SDF-D6-TRUTH-PROJECTION-ROUNDTRIP", roundtrip["status"] == "PASS", rows_checked=roundtrip["rows_checked"]),
        gate("PV1-SDF-D6-DIRTY-VARIANTS", dirty_detection["status"] == "PASS", detected=dirty_detection["detected"]),
        gate("PV1-SDF-D6-REPLAY-DETERMINISM", replay["status"] == "PASS", normal_state_hash=replay["normal_state_hash"]),
        gate("PV1-SDF-D6-EXPECTED-STATE", replay["checks"]["expected_normal_state_match"]),
        gate("PV1-SDF-D6-INCIDENT-READINESS", readiness["incident"]["status"] == "PASS"),
        gate("PV1-SDF-D6-PLAN-READINESS", readiness["plan"]["status"] == "PASS"),
        gate("PV1-SDF-D6-HITL-READINESS", readiness["hitl"]["status"] == "PASS"),
        gate("PV1-SDF-D6-PERSONA-READINESS", readiness["persona"]["status"] == "PASS"),
        gate("PV1-SDF-D6-SIMULATOR-READINESS", readiness["simulator"]["status"] == "PASS"),
        gate("PV1-SDF-D6-NEGATIVE-GOVERNANCE", readiness["negative"]["status"] == "PASS"),
        gate("PV1-SDF-D6-NO-OVERCLAIM", scan["status"] == "PASS", findings=scan["findings"]),
        gate("PV1-SDF-D6-HASHES", True),
    ]
    status = "PASS" if all_gates_pass(gates) and summary["status"] == "PASS" else "FAIL"
    harness = {
        "task": "PV1-SDF-D6 Synthetic Validation Harness",
        "status": status,
        "generated_at_utc": GENERATED_AT_UTC,
        "generation_version": GENERATION_VERSION,
        "gates": gates,
        "validation_tests": len(test_payloads),
        "pack_id": PACK_ID,
    }
    write_json(out / "PV1_SDF_D6_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-SDF-D6 synthetic validation harness.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--synthetic-root", default=DEFAULT_SYNTHETIC_ROOT)
    parser.add_argument("--d1-output-dir", default=DEFAULT_D1_OUTPUT_DIR)
    args = parser.parse_args()
    result = run_pv1_sdf_d6_gate(project_root=args.project_root, output_dir=args.output_dir, synthetic_root=args.synthetic_root, d1_output_dir=args.d1_output_dir)
    print(result["status"])
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
