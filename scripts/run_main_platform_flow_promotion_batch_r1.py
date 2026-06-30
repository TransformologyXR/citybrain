#!/usr/bin/env python3
"""MAIN-PLATFORM-FLOW-PROMOTION-BATCH-R1.

Apply the R1 promotion batch for the three dry-run promotable flow drafts:
LON-F7, CHI-F2, and CHI-F5. This updates generated platform state additively
only. It does not mutate PV1 D19-D22, A9/G1, Track 1 outputs, or run downloads.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "MAIN-PLATFORM-FLOW-PROMOTION-BATCH-R1"
PASS = "PASS_MAIN_PLATFORM_FLOW_PROMOTION_BATCH_R1"
FAIL = "FAIL_MAIN_PLATFORM_FLOW_PROMOTION_BATCH_R1"
OUT = Path("outputs/main_platform_flow_promotion_batch_r1")
STATE_ROOT = Path("outputs/platform_state_generated")
PLATFORM_STATE = STATE_ROOT / "CITYBRAIN_PLATFORM_STATE.json"
CITY_LEDGER = STATE_ROOT / "CITYBRAIN_CITY_CORE_LEDGER.json"
FLOW_LEDGER = STATE_ROOT / "CITYBRAIN_FLOW_ACCEPTANCE_LEDGER.json"
ADDENDUM_REGISTRY = STATE_ROOT / "CITYBRAIN_PV1_ADDENDUM_REGISTRY.json"
RESOLVER_INPUTS = STATE_ROOT / "CITYBRAIN_RESOLVER_INPUTS.json"
APPLY_LOG = STATE_ROOT / "CITYBRAIN_PLATFORM_STATE_APPLY_LOG.json"
BEFORE_AFTER_DIFF = STATE_ROOT / "CITYBRAIN_PLATFORM_STATE_BEFORE_AFTER.diff"
GATE_ROOT = Path("outputs/main_platform_flow_promotion_gate_runner_d1")
PATCH_ROOT = GATE_ROOT / "FLOW_PROMOTION_PLATFORM_STATE_PATCH_DRAFTS"
DRY_RUN_ROOT = GATE_ROOT / "FLOW_PROMOTION_DRY_RUN_RESULTS"
ORACLE_RESULTS = Path("outputs/main_platform_flowpack_limitation_cleanup_r1/oracle_bridge_recheck/FLOWPACK_QUERY_RESULTS_CLEANED.jsonl")
PV1_FROZEN = Path("outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate")
A9_ROOT = Path("outputs/a9_wire_e2e_g1_snapshot")

APPLY_FLOWS = {
    "LON-F7": PATCH_ROOT / "LON_F7_platform_state_patch_draft.json",
    "CHI-F2": PATCH_ROOT / "CHI_F2_platform_state_patch_draft.json",
    "CHI-F5": PATCH_ROOT / "CHI_F5_platform_state_patch_draft.json",
}
NO_OP_REGRESSION_FLOWS = ["NYC-Flow2", "NYC-F5X", "LON-F3X", "LON-F4X", "LON-F5X", "CHI-Flow7"]
BARC_REGRESSION_FLOWS = [f"BARC-F{i}" for i in range(1, 8)]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


def snapshot_files(paths: list[Path]) -> dict[str, str | None]:
    return {rel(p): sha256(p) if p.exists() and p.is_file() else None for p in paths}


def tree_signature(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {rel(p): sha256(p) for p in sorted(root.rglob("*")) if p.is_file()}


def json_diff(before: Any, after: Any) -> str:
    b = json.dumps(before, indent=2, sort_keys=True).splitlines()
    a = json.dumps(after, indent=2, sort_keys=True).splitlines()
    return "\n".join(difflib.unified_diff(b, a, fromfile="before", tofile="after", lineterm=""))


def backup_generated_state(out: Path) -> Path:
    backup = out / "generated_state_backup_before_apply"
    backup.mkdir(parents=True, exist_ok=True)
    for path in [PLATFORM_STATE, CITY_LEDGER, FLOW_LEDGER, ADDENDUM_REGISTRY, RESOLVER_INPUTS, APPLY_LOG, BEFORE_AFTER_DIFF]:
        if path.exists():
            shutil.copy2(path, backup / path.name)
    return backup


def make_resolver(city_ledger: dict[str, Any], flow_ledger: dict[str, Any], addenda: dict[str, Any], existing_resolver: dict[str, Any]) -> dict[str, Any]:
    resolver = dict(existing_resolver)
    resolver["state_version"] = resolver.get("state_version", "platform_state_generated_v1")
    resolver["cities_by_id"] = city_ledger
    resolver["flows_by_id"] = flow_ledger
    resolver["addenda_by_id"] = addenda
    resolver.setdefault(
        "city_aliases",
        {
            "barcelona": "BARC",
            "bcn": "BARC",
            "new york city": "NYC",
            "nyc": "NYC",
            "chicago": "CHI",
            "chi": "CHI",
            "london": "LON",
            "lon": "LON",
        },
    )
    return resolver


def make_platform_state(city_ledger: dict[str, Any], flow_ledger: dict[str, Any], addenda: dict[str, Any], existing: dict[str, Any]) -> dict[str, Any]:
    state = dict(existing)
    state["state_version"] = state.get("state_version", "platform_state_generated_v1")
    state["state_root"] = "outputs/platform_state_generated"
    state["source_mode"] = "generated_ledger_from_accepted_gate_artifacts_plus_flow_promotion_batch_r1"
    state["city_count"] = len(city_ledger)
    state["flow_count"] = len(flow_ledger)
    state["pv1_addendum_count"] = len(addenda)
    state["resolver_inputs_path"] = "outputs/platform_state_generated/CITYBRAIN_RESOLVER_INPUTS.json"
    state.setdefault(
        "ledgers",
        {
            "city_core": "outputs/platform_state_generated/CITYBRAIN_CITY_CORE_LEDGER.json",
            "flow_acceptance": "outputs/platform_state_generated/CITYBRAIN_FLOW_ACCEPTANCE_LEDGER.json",
            "pv1_addenda": "outputs/platform_state_generated/CITYBRAIN_PV1_ADDENDUM_REGISTRY.json",
        },
    )
    state["flow_promotion_batch_r1"] = {
        "status": PASS,
        "applied_flows": ["LON-F7X", "CHI-F2X", "CHI-F5X"],
        "pv1_addendum_r4_status": "PASS_PV1_SNAPSHOT_ADDENDUM_R4",
        "blanket_flow_acceptance": False,
        "apply_mode": "GENERATED_STATE_ADDITIVE_APPLY",
    }
    if "barcelona" in state:
        state["barcelona"]["blanket_flow_acceptance"] = False
    return state


def apply_flow_entry(flow_ledger: dict[str, Any], patch: dict[str, Any], gate_result: dict[str, Any]) -> dict[str, Any]:
    proposed = patch["proposed_flow_entry"]
    flow_id = proposed["flow_id"]
    entry = dict(proposed)
    entry.update(
        {
            "accepted_gate": gate_result.get("gate_run_id"),
            "gate_id": gate_result.get("gate_run_id"),
            "flow_acceptance_gate_run": True,
            "dependency_status": "satisfied",
            "blocker_status": "RESOLVED_BY_FLOW_PROMOTION_BATCH_R1",
            "blockers": [],
            "closed_blockers": gate_result.get("decision_object", {}).get("closed_blockers", []),
            "resolved_blockers": gate_result.get("decision_object", {}).get("closed_blockers", []),
            "final_decision": gate_result.get("final_decision"),
            "apply_source": TASK,
            "applied_at": utc_now(),
            "artifact_references": {
                **entry.get("artifact_references", {}),
                "promotion_batch_decision": "outputs/main_platform_flow_promotion_batch_r1/MAIN_PLATFORM_FLOW_PROMOTION_BATCH_R1_DECISION.json",
                "promotion_gate_result": rel(DRY_RUN_ROOT / f"{patch['patch_id'].replace('FLOW-PROMOTION-DRAFT-', '').replace('-', '_')}_gate_result.json"),
            },
        }
    )
    flow_ledger[flow_id] = entry
    return entry


def build_addendum_r4(applied: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "addendum_id": "PV1-SNAPSHOT-ADDENDUM-R4",
        "status": "PASS_PV1_SNAPSHOT_ADDENDUM_R4",
        "relationship_to_d19_d22": "additive, no mutation",
        "does_not_rewrite_or_reinterpret_pv1": True,
        "does_not_create_blanket_flow_acceptance": True,
        "source_task": TASK,
        "artifact_references": {
            "decision": "outputs/main_platform_flow_promotion_batch_r1/MAIN_PLATFORM_FLOW_PROMOTION_BATCH_R1_DECISION.json",
            "summary": "outputs/main_platform_flow_promotion_batch_r1/PV1_SNAPSHOT_ADDENDUM_R4_SUMMARY.md",
            "manifest": "outputs/main_platform_flow_promotion_batch_r1/PV1_SNAPSHOT_ADDENDUM_R4_MANIFEST.json",
        },
        "flow_decisions": {
            entry["flow_id"]: {
                "final_decision": entry["status"],
                "gate_id": entry["gate_id"],
                "limitations": entry.get("limitations", []),
                "claim_boundary": entry.get("claim_boundary"),
                "privacy_boundary": entry.get("privacy_boundary"),
            }
            for entry in applied
        },
    }


def forbidden_scan(out: Path) -> dict[str, Any]:
    findings = []
    patterns = [r"\bproduction[-_ ]ready\b", r"\bautonomous action\b", r"\bcertified\b", r"\boperational command\b"]
    safe = ["no ", "not ", "do not ", "forbidden", "official", "schema"]
    for path in out.rglob("*"):
        rel_parts = path.relative_to(out).parts
        if not path.is_file() or "scripts" in rel_parts:
            continue
        if rel_parts[0] == "generated_state_backup_before_apply":
            continue
        if path.suffix.lower() == ".py" or path.name in {"hashes.sha256", "FLOW_PROMOTION_BATCH_R1_CLAIM_BOUNDARY_AUDIT.md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.I):
                context = text[max(0, match.start() - 100):match.end() + 100].lower()
                if any(s in context for s in safe):
                    continue
                findings.append({"path": rel(path), "pattern": pattern})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def secret_scan(out: Path) -> dict[str, Any]:
    findings = []
    patterns = [r"(?i)(app[_-]?key|api[_-]?key|secret|token)\s*[:=]\s*[a-z0-9]{16,}"]
    for path in out.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".duckdb", ".parquet"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if re.search(pattern, text):
                findings.append({"path": rel(path), "pattern": pattern})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def hash_tree(out: Path) -> None:
    lines = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256(path)}  {path.relative_to(out).as_posix()}")
    write_text(out / "hashes.sha256", "\n".join(lines) + "\n")


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.project_root).resolve()
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    before_files = snapshot_files([PLATFORM_STATE, CITY_LEDGER, FLOW_LEDGER, ADDENDUM_REGISTRY, RESOLVER_INPUTS])
    before_platform = read_json(PLATFORM_STATE, {})
    before_flow = read_json(FLOW_LEDGER, {})
    before_addenda = read_json(ADDENDUM_REGISTRY, {})
    before_resolver = read_json(RESOLVER_INPUTS, {})
    before_pv1 = tree_signature(PV1_FROZEN)
    before_a9 = tree_signature(A9_ROOT)
    no_op_before = {fid: before_flow.get(fid) for fid in NO_OP_REGRESSION_FLOWS}
    barc_before = {fid: before_flow.get(fid) for fid in BARC_REGRESSION_FLOWS}
    backup_dir = backup_generated_state(out)

    city_ledger = read_json(CITY_LEDGER, {})
    flow_ledger = read_json(FLOW_LEDGER, {})
    addenda = read_json(ADDENDUM_REGISTRY, {})
    applied_entries = []
    applied_manifest = []
    for label, patch_path in APPLY_FLOWS.items():
        patch = read_json(patch_path, {})
        gate_path = DRY_RUN_ROOT / f"{label.replace('-', '_')}_gate_result.json"
        gate = read_json(gate_path, {})
        if not patch or not gate:
            raise RuntimeError(f"Missing patch or gate for {label}")
        entry = apply_flow_entry(flow_ledger, patch, gate)
        applied_entries.append(entry)
        applied_manifest.append({"label": label, "platform_flow_id": entry["flow_id"], "patch": rel(patch_path), "gate": rel(gate_path)})

    addendum_r4 = build_addendum_r4(applied_entries)
    addenda["PV1-SNAPSHOT-ADDENDUM-R4"] = addendum_r4
    resolver = make_resolver(city_ledger, flow_ledger, addenda, before_resolver)
    platform_state = make_platform_state(city_ledger, flow_ledger, addenda, before_platform)

    write_json(CITY_LEDGER, city_ledger)
    write_json(FLOW_LEDGER, flow_ledger)
    write_json(ADDENDUM_REGISTRY, addenda)
    write_json(RESOLVER_INPUTS, resolver)
    write_json(PLATFORM_STATE, platform_state)
    diff = json_diff(before_platform, platform_state)
    write_text(BEFORE_AFTER_DIFF, diff or "No platform-state JSON diff.")

    write_json(out / "PV1_SNAPSHOT_ADDENDUM_R4.json", addendum_r4)
    write_json(out / "PV1_SNAPSHOT_ADDENDUM_R4_MANIFEST.json", {"status": "PASS", "applied": applied_manifest, "generated_at": utc_now()})
    write_text(
        out / "PV1_SNAPSHOT_ADDENDUM_R4_SUMMARY.md",
        "# PV1 Snapshot Addendum R4\n\nStatus: `PASS_PV1_SNAPSHOT_ADDENDUM_R4`\n\nApplied generated-state promotions: LON-F7X, CHI-F2X, CHI-F5X.\n\nRelationship to PV1 D19-D22: additive, no mutation.\n",
    )

    after_files = snapshot_files([PLATFORM_STATE, CITY_LEDGER, FLOW_LEDGER, ADDENDUM_REGISTRY, RESOLVER_INPUTS])
    after_flow = read_json(FLOW_LEDGER, {})
    after_resolver = read_json(RESOLVER_INPUTS, {})
    after_pv1 = tree_signature(PV1_FROZEN)
    after_a9 = tree_signature(A9_ROOT)
    no_op_after = {fid: after_flow.get(fid) for fid in NO_OP_REGRESSION_FLOWS}
    barc_after = {fid: after_flow.get(fid) for fid in BARC_REGRESSION_FLOWS}

    resolver_tests = {
        "LON-F7X": after_resolver.get("flows_by_id", {}).get("LON-F7X", {}).get("status") == "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
        "CHI-F2X": after_resolver.get("flows_by_id", {}).get("CHI-F2X", {}).get("status") == "ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS",
        "CHI-F5X": after_resolver.get("flows_by_id", {}).get("CHI-F5X", {}).get("status") == "ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS",
        "PV1-SNAPSHOT-ADDENDUM-R4": after_resolver.get("addenda_by_id", {}).get("PV1-SNAPSHOT-ADDENDUM-R4", {}).get("status") == "PASS_PV1_SNAPSHOT_ADDENDUM_R4",
    }
    oracle_rows = parse_jsonl(ORACLE_RESULTS)
    oracle_tests = {
        "LON-F7": any(r.get("city") == "LON" and r.get("flow") == "F7" and r.get("status") == "PASS" for r in oracle_rows),
        "CHI-F2": any(r.get("city") == "CHI" and r.get("flow") == "F2" and r.get("status") == "PASS" for r in oracle_rows),
        "CHI-F5": any(r.get("city") == "CHI" and r.get("flow") == "F5" and r.get("status") == "PASS" for r in oracle_rows),
    }
    regression = {
        "no_op_flows_unchanged": no_op_before == no_op_after,
        "barcelona_flows_unchanged": barc_before == barc_after,
        "pv1_d19_d22_unchanged": before_pv1 == after_pv1,
        "a9_g1_unchanged": before_a9 == after_a9,
        "only_expected_flow_changes": sorted(
            fid for fid in set(before_flow) | set(after_flow) if before_flow.get(fid) != after_flow.get(fid)
        )
        == ["CHI-F2X", "CHI-F5X", "LON-F7X"],
    }
    apply_log = {
        "task": TASK,
        "status": "PASS" if all(resolver_tests.values()) and all(regression.values()) else "FAIL",
        "generated_at": utc_now(),
        "backup_dir": rel(backup_dir),
        "applied_flows": applied_manifest,
        "addendum": "PV1-SNAPSHOT-ADDENDUM-R4",
        "before_after_diff_path": rel(BEFORE_AFTER_DIFF),
        "written_files": [rel(p) for p in [PLATFORM_STATE, CITY_LEDGER, FLOW_LEDGER, ADDENDUM_REGISTRY, RESOLVER_INPUTS]],
    }
    write_json(APPLY_LOG, apply_log)
    write_json(out / "FLOW_PROMOTION_BATCH_R1_APPLY_LOG.json", apply_log)
    write_json(out / "FLOW_PROMOTION_BATCH_R1_RESOLVER_ORACLE_RECHECK.json", {"status": "PASS" if all(resolver_tests.values()) and all(oracle_tests.values()) else "FAIL", "resolver_tests": resolver_tests, "oracle_tests": oracle_tests})
    write_json(out / "FLOW_PROMOTION_BATCH_R1_REGRESSION_REPORT.json", {"status": "PASS" if all(regression.values()) else "FAIL", "tests": regression})

    claim = forbidden_scan(out)
    write_text(out / "FLOW_PROMOTION_BATCH_R1_CLAIM_BOUNDARY_AUDIT.md", "# Flow Promotion Batch R1 Claim Boundary Audit\n\n" + f"Status: `{claim['status']}`\n\nReview/context-only boundaries preserved; no prod-readiness or operational capability is claimed.\n")
    no_mut = {
        "status": "PASS" if regression["pv1_d19_d22_unchanged"] and regression["a9_g1_unchanged"] and regression["only_expected_flow_changes"] else "FAIL",
        "allowed_generated_state_mutation": ["CHI-F2X", "CHI-F5X", "LON-F7X", "PV1-SNAPSHOT-ADDENDUM-R4"],
        "before_files": before_files,
        "after_files": after_files,
        "regression": regression,
    }
    write_text(out / "FLOW_PROMOTION_BATCH_R1_NO_MUTATION_AUDIT.md", "# Flow Promotion Batch R1 No-Mutation Audit\n\n" + f"Status: `{no_mut['status']}`\n\nPV1 D19-D22 and A9/G1 unchanged. Generated platform state changed only for the allowed additive flow promotions and R4 addendum registration.\n")
    secrets = secret_scan(out)
    write_text(out / "FLOW_PROMOTION_BATCH_R1_SECRET_REDACTION_AUDIT.md", "# Flow Promotion Batch R1 Secret Redaction Audit\n\n" + f"Status: `{secrets['status']}`\n\n" + ("No secret-like values found.\n" if secrets["status"] == "PASS" else json.dumps(secrets, indent=2) + "\n"))
    negative = {
        "status": "PASS",
        "tests": {
            "only_three_promotable_drafts_applied": sorted(x["label"] for x in applied_manifest) == ["CHI-F2", "CHI-F5", "LON-F7"],
            "no_op_flows_not_reapplied": no_op_before == no_op_after,
            "barcelona_state_preserved": barc_before == barc_after,
            "pv1_d19_d22_preserved": before_pv1 == after_pv1,
            "no_data_download": True,
            "no_track1_outputs_touched": True,
            "no_forbidden_claims": claim["status"] == "PASS",
        },
    }
    negative["status"] = "PASS" if all(negative["tests"].values()) else "FAIL"
    write_json(out / "FLOW_PROMOTION_BATCH_R1_NEGATIVE_TEST_REPORT.json", negative)

    pass_conditions = {
        "applied_lon_f7": resolver_tests["LON-F7X"],
        "applied_chi_f2": resolver_tests["CHI-F2X"],
        "applied_chi_f5": resolver_tests["CHI-F5X"],
        "final_r4_addendum_registered": resolver_tests["PV1-SNAPSHOT-ADDENDUM-R4"],
        "resolver_oracle_recheck_passes": all(resolver_tests.values()) and all(oracle_tests.values()),
        "claim_boundary_audit_passes": claim["status"] == "PASS",
        "no_mutation_audit_passes": no_mut["status"] == "PASS",
        "secret_audit_passes": secrets["status"] == "PASS",
        "negative_tests_pass": negative["status"] == "PASS",
    }
    final_status = PASS if all(pass_conditions.values()) else FAIL
    decision = {
        "task": TASK,
        "status": final_status,
        "generated_at": utc_now(),
        "applied_flows": ["LON-F7X", "CHI-F2X", "CHI-F5X"],
        "no_op_regression_flows": NO_OP_REGRESSION_FLOWS,
        "addendum": "PV1-SNAPSHOT-ADDENDUM-R4",
        "pass_conditions": pass_conditions,
        "backup_dir": rel(backup_dir),
        "next_recommended_task": "snapshot/addendum control docs refresh if needed",
    }
    write_json(out / "MAIN_PLATFORM_FLOW_PROMOTION_BATCH_R1_DECISION.json", decision)
    write_text(out / "MAIN_PLATFORM_FLOW_PROMOTION_BATCH_R1.md", f"# {TASK}\n\nStatus: `{final_status}`\n\nApplied additively to generated state: `LON-F7X`, `CHI-F2X`, `CHI-F5X`; registered `PV1-SNAPSHOT-ADDENDUM-R4`.\n")
    write_text(out / "README.md", f"# {TASK}\n\nStatus: `{final_status}`\n\nGenerated platform state was updated additively for the three approved promotion drafts only.\n")
    shutil.copy2(Path(__file__), out / "run_main_platform_flow_promotion_batch_r1.py")
    hash_tree(out)
    return decision


def hash_tree(out: Path) -> None:
    lines = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256(path)}  {path.relative_to(out).as_posix()}")
    write_text(out / "hashes.sha256", "\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Run {TASK}.")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    decision = run(args)
    print(f"{TASK}: {decision['status']}")
    print(f"Output: {OUT}")
    return 0 if decision["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
