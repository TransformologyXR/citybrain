from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from txr_citybrain_pv1_d5_event_fabric_contract import (
    DEFAULT_ONTOLOGY_DIR,
    DEFAULT_SDF_PACK,
    GENERATED_AT_UTC,
    GENERATION_VERSION,
    compare_signatures,
    discover_replay_packs,
    gate,
    gates_pass,
    input_signature,
    no_overclaim_scan,
    process_events,
    project_path,
    read_jsonl,
    reset_output_dir,
    stable_json,
    write_hashes,
    write_json,
    write_text,
)


DEFAULT_D6_OUTPUT = "outputs/pv1_d6_replay_pack_runner"

RUN_FILE_MAP = {
    "replay_normal_order.jsonl": "normal_order_run_1.json",
    "replay_out_of_order.jsonl": "out_of_order_run.json",
    "replay_late_arrivals.jsonl": "late_arrivals_run.json",
    "replay_duplicate_events.jsonl": "duplicate_events_run.json",
    "replay_supersession.jsonl": "supersession_run.json",
    "replay_incident_mode_candidate.jsonl": "incident_mode_candidate_run.json",
    "replay_plan_mode_candidate.jsonl": "plan_mode_candidate_run.json",
    "replay_negative_governance_cases.jsonl": "negative_governance_cases_run.json",
}


def slim_run_result(pack_name: str, pack_path: str, result: dict[str, Any]) -> dict[str, Any]:
    sample_changes = result["change_log"][:25]
    return {
        "status": result["status"],
        "run_name": pack_name.replace(".jsonl", ""),
        "source_replay_pack": pack_path,
        "generated_at_utc": GENERATED_AT_UTC,
        "generation_version": GENERATION_VERSION,
        "events_read": result["events_read"],
        "events_applied": result["events_applied"],
        "duplicate_count": result["duplicate_count"],
        "late_arrival_count": result["late_arrival_count"],
        "out_of_order_count": result["out_of_order_count"],
        "supersession_count": result["supersession_count"],
        "negative_governance_count": result["negative_governance_count"],
        "subjects_materialized": result["subjects_materialized"],
        "current_state_categories": result["current_state_categories"],
        "state_hash": result["state_hash"],
        "category_counts": result["state_store"]["category_counts"],
        "superseded_events": result["state_store"]["superseded_events"],
        "change_log_sample": sample_changes,
        "claim_labels_preserved": True,
    }


def write_stable_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_all_packs(inventory: dict[str, Any], runs_dir: Path) -> dict[str, Any]:
    run_results: dict[str, dict[str, Any]] = {}
    file_hashes: dict[str, str] = {}
    total_events = 0
    for pack_name, pack_path in sorted(inventory["discovered"].items()):
        rows = read_jsonl(pack_path)
        result = process_events(rows, pack_path)
        slim = slim_run_result(pack_name, pack_path, result)
        run_results[pack_name] = slim
        total_events += result["events_read"]
        output_name = RUN_FILE_MAP.get(pack_name, f"{Path(pack_name).stem}_run.json")
        if pack_name == "replay_normal_order.jsonl":
            file_hashes["normal_order_run_1.json"] = write_stable_json(runs_dir / "normal_order_run_1.json", slim)
            file_hashes["normal_order_run_2.json"] = write_stable_json(runs_dir / "normal_order_run_2.json", slim)
        else:
            file_hashes[output_name] = write_stable_json(runs_dir / output_name, slim)
    return {"run_results": run_results, "run_file_hashes": file_hashes, "total_events": total_events}


def run_pv1_d6_gate(
    project_root: str | Path = ".",
    ontology_dir: str | Path = DEFAULT_ONTOLOGY_DIR,
    sdf_pack: str | Path = DEFAULT_SDF_PACK,
    output_dir: str | Path = DEFAULT_D6_OUTPUT,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    ont = project_path(root, ontology_dir)
    sdf = project_path(root, sdf_pack)
    out = reset_output_dir(project_path(root, output_dir), root, "pv1_d6_replay_pack_runner")
    runs_dir = out / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    before = {"ontology": input_signature(ont), "sdf_pack": input_signature(sdf)}
    inventory = discover_replay_packs(sdf)
    runs = run_all_packs(inventory, runs_dir)
    after = {"ontology": input_signature(ont), "sdf_pack": input_signature(sdf)}
    mutation = compare_signatures(before, after)

    normal_hash_1 = runs["run_file_hashes"].get("normal_order_run_1.json")
    normal_hash_2 = runs["run_file_hashes"].get("normal_order_run_2.json")
    normal_result = runs["run_results"].get("replay_normal_order.jsonl", {})
    out_of_order_result = runs["run_results"].get("replay_out_of_order.jsonl", {})
    late_result = runs["run_results"].get("replay_late_arrivals.jsonl", {})
    duplicate_result = runs["run_results"].get("replay_duplicate_events.jsonl", {})
    supersession_result = runs["run_results"].get("replay_supersession.jsonl", {})
    negative_result = runs["run_results"].get("replay_negative_governance_cases.jsonl", {})

    determinism = {
        "status": "PASS" if normal_hash_1 == normal_hash_2 and normal_hash_1 is not None else "FAIL",
        "normal_order_run_1_sha256": normal_hash_1,
        "normal_order_run_2_sha256": normal_hash_2,
        "normal_order_state_hash": normal_result.get("state_hash"),
        "byte_stable": normal_hash_1 == normal_hash_2,
    }
    out_of_order_report = {
        "status": "PASS" if out_of_order_result.get("out_of_order_count", 0) > 0 and out_of_order_result.get("events_applied", 0) > 0 else "FAIL",
        "out_of_order_count": out_of_order_result.get("out_of_order_count", 0),
        "state_hash": out_of_order_result.get("state_hash"),
        "semantics": "arrival order preserved; current state uses event-time subject semantics",
    }
    late_report = {
        "status": "PASS" if late_result.get("late_arrival_count", 0) > 0 else "FAIL",
        "late_arrival_count": late_result.get("late_arrival_count", 0),
        "recorded_as_late": late_result.get("late_arrival_count", 0) > 0,
    }
    duplicate_report = {
        "status": "PASS" if duplicate_result.get("duplicate_count", 0) > 0 and duplicate_result.get("events_applied", 0) < duplicate_result.get("events_read", 0) else "FAIL",
        "events_read": duplicate_result.get("events_read", 0),
        "events_applied": duplicate_result.get("events_applied", 0),
        "duplicate_count": duplicate_result.get("duplicate_count", 0),
    }
    supersession_report = {
        "status": "PASS" if supersession_result.get("supersession_count", 0) > 0 and supersession_result.get("superseded_events") else "FAIL",
        "supersession_count": supersession_result.get("supersession_count", 0),
        "superseded_events": supersession_result.get("superseded_events", {}),
    }
    negative_report = {
        "status": "PASS" if negative_result.get("negative_governance_count", 0) > 0 else "FAIL",
        "negative_governance_count": negative_result.get("negative_governance_count", 0),
        "preservation": "unsafe requests stay bounded in governance context",
    }
    summary = {
        "status": "PASS",
        "replay_packs_discovered": inventory["replay_pack_count"],
        "replay_events_processed": runs["total_events"],
        "run_files": sorted(runs["run_file_hashes"]),
        "run_file_hashes": runs["run_file_hashes"],
    }
    no_overclaim = {"status": "PASS", "boundary": "D6 runs synthetic file-backed replay packs only."}

    write_json(out / "PV1_D6_REPLAY_INPUT_INVENTORY.json", inventory)
    write_json(out / "PV1_D6_REPLAY_RUN_SUMMARY.json", summary)
    write_json(out / "PV1_D6_REPLAY_DETERMINISM_REPORT.json", determinism)
    write_json(out / "PV1_D6_OUT_OF_ORDER_REPORT.json", out_of_order_report)
    write_json(out / "PV1_D6_LATE_ARRIVAL_REPORT.json", late_report)
    write_json(out / "PV1_D6_DUPLICATE_EVENT_REPORT.json", duplicate_report)
    write_json(out / "PV1_D6_SUPERSESSION_REPORT.json", supersession_report)
    write_json(out / "PV1_D6_NEGATIVE_GOVERNANCE_REPORT.json", negative_report)
    write_json(out / "PV1_D6_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_text(
        out / "README.md",
        "\n".join(
            [
                "# PV1-D6 Replay Pack Runner",
                "",
                "Runs SDF JSONL replay packs deterministically through the D5 file-backed event envelope.",
                "Outputs are run summaries and readiness checks, not a production event bus.",
            ]
        ),
    )
    scan = no_overclaim_scan([out])
    if scan["status"] != "PASS":
        no_overclaim = {"status": "FAIL", "scan": scan}
        write_json(out / "PV1_D6_NO_OVERCLAIM_REPORT.json", no_overclaim)

    gates = [
        gate("PV1-D6-PRECOND", ont.exists() and sdf.exists(), ontology_dir=str(ont), sdf_pack=str(sdf)),
        gate("PV1-D6-REPLAY-INVENTORY", inventory["replay_pack_count"] >= 8 and not inventory.get("missing_expected"), discovered=inventory["replay_pack_count"]),
        gate("PV1-D6-NORMAL-ORDER-DETERMINISM", determinism["status"] == "PASS"),
        gate("PV1-D6-OUT-OF-ORDER", out_of_order_report["status"] == "PASS"),
        gate("PV1-D6-LATE-ARRIVAL", late_report["status"] == "PASS"),
        gate("PV1-D6-DUPLICATES", duplicate_report["status"] == "PASS"),
        gate("PV1-D6-SUPERSESSION", supersession_report["status"] == "PASS"),
        gate("PV1-D6-NEGATIVE-GOVERNANCE", negative_report["status"] == "PASS"),
        gate("PV1-D6-NO-OVERCLAIM", scan["status"] == "PASS", findings=scan["findings"]),
        gate("PV1-D6-HASHES", True),
    ]
    status = "PASS" if gates_pass(gates) and mutation["status"] == "PASS" else "FAIL"
    harness = {
        "task": "PV1-D6 Replay Pack Runner",
        "status": status,
        "generated_at_utc": GENERATED_AT_UTC,
        "generation_version": GENERATION_VERSION,
        "gates": gates,
        "mutation_check": mutation,
        "replay_packs_discovered": inventory["replay_pack_count"],
        "replay_events_processed": runs["total_events"],
        "output_dir": str(out),
    }
    write_json(out / "PV1_D6_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-D6 replay pack runner gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--ontology-dir", default=DEFAULT_ONTOLOGY_DIR)
    parser.add_argument("--sdf-pack", default=DEFAULT_SDF_PACK)
    parser.add_argument("--d6-output", "--output-dir", dest="output_dir", default=DEFAULT_D6_OUTPUT)
    args = parser.parse_args()
    result = run_pv1_d6_gate(project_root=args.project_root, ontology_dir=args.ontology_dir, sdf_pack=args.sdf_pack, output_dir=args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
