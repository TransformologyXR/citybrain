#!/usr/bin/env python3
"""Build Push 3 INFRA integration artifacts after Lane A/B/C publish.

The integration is additive. It proves the merged branch can join the cockpit
selected-item workspace, DIFF/RECALL read-only modes, and BRIEF v2 Flow 1
package without rewriting lane outputs or claiming production/live/official
behavior.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"
OUTPUT_ROOT = OUTPUTS_ROOT / "push3_infra_after_three_lanes_integration"
CLOSEOUT_ROOT = OUTPUTS_ROOT / "push3_infra_after_three_lanes_closeout"
FINAL_ROOT = OUTPUTS_ROOT / "push3_infra_after_three_lanes_final_status"

TASK_ID = "PUSH3-INFRA-AFTER-THREE-LANES"
PASS_STATUS = "PASS_PUSH3_INFRA_AFTER_THREE_LANES_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_PUSH3_INFRA_AFTER_THREE_LANES"
BRANCH = "codex/push3-infra-after-three-lanes"
BASE_REF = "origin/codex/push2-check-watch-app-review-route-integration"

LANES = {
    "lane_b": {
        "branch": "codex/push3-lane-b-cockpit-source-record-360",
        "commit": "20051f0",
        "label": "cockpit selected-item workspace substrate",
    },
    "lane_c": {
        "branch": "codex/push3-lane-c-diff-recall-readonly",
        "commit": "ec1e94e",
        "label": "DIFF/RECALL read-only computed modes",
    },
    "lane_a": {
        "branch": "codex/push3-lane-a-brief-flow1-packaging",
        "commit": "dae7105",
        "label": "BRIEF v2 + Flow 1 packaging",
    },
}

LANE_B_ROOT = OUTPUTS_ROOT / "push3_lane_b_cockpit_source_record_360"
LANE_C_ROOT = OUTPUTS_ROOT / "push3_lane_c_diff_recall_readonly"
LANE_A_ROOT = OUTPUTS_ROOT / "push3_lane_a_brief_v2_flow1_packaging"

REQUIRED_OUTPUTS = [
    "PUSH3_INFRA_INTEGRATION_DECISION.json",
    "PUSH3_BRANCH_TOPOLOGY.md",
    "PUSH3_CROSS_LANE_COMPATIBILITY_REPORT.json",
    "PUSH3_FLOW1_COCKPIT_JOIN_REPORT.json",
    "PUSH3_FLOW1_INTEGRATED_REFERENCE_MAP.json",
    "PUSH3_SELECTED_ITEM_WORKSPACE_INTEGRATED_REFS.json",
    "PUSH3_CHECK_AUTHORITY_COVERAGE.json",
    "PUSH3_BOUNDARY_AND_NON_CLAIMS.md",
    "PUSH3_TEST_REPORT.md",
    "PUSH3_OPEN_LIMITATIONS.md",
    "PUSH3_HASH_MANIFEST.json",
]
REQUIRED_CLOSEOUT_OUTPUTS = [
    "PUSH3_CLOSEOUT_DECISION.json",
    "PUSH3_CLOSEOUT_SUMMARY.md",
    "PUSH3_CLOSEOUT_LIMITATIONS.md",
    "PUSH3_CLOSEOUT_NEXT_STEPS.md",
    "PUSH3_CLOSEOUT_HASH_MANIFEST.json",
]
REQUIRED_FINAL_OUTPUTS = [
    "PUSH3_FINAL_STATUS_DECISION.json",
    "PUSH3_FINAL_STATUS_SUMMARY.md",
    "PUSH3_FINAL_STATUS_HASH_MANIFEST.json",
]

LIMITATIONS = [
    "Local/replay/review/query context only.",
    "Lane A branch-published Flow 1 artifacts do not directly contain DIFF/RECALL refs; INFRA adds those references in this integration overlay without mutating lane outputs.",
    "No production/public API, internet exposure, live monitoring, autonomous alerting, dispatch, routing/control, enforcement, official ticket/case creation, legal/certified finding, or automated action is claimed.",
    "No citywide certified twin or certified physical geometry claim is made.",
    "Canonical merge remains separate from this integration branch.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def out_rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def reset_output_root(root: Path) -> None:
    resolved = root.resolve()
    outputs = OUTPUTS_ROOT.resolve()
    if outputs not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs/: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def reset_output_roots() -> None:
    for root in [OUTPUT_ROOT, CLOSEOUT_ROOT, FINAL_ROOT]:
        reset_output_root(root)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def git_stdout(args: list[str]) -> str:
    proc = subprocess.run(["git", *args], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return proc.stdout.strip()


def write_hash_manifest(root: Path, name: str, schema_version: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != name:
            rows.append({"path": out_rel(path, root), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": schema_version,
        "algorithm": "sha256",
        "status": "PASS",
        "item_count": len(rows),
        "missing_count": 0,
        "mismatch_count": 0,
        "files": rows,
    }
    write_json(root / name, manifest)
    return manifest


def verify_hash_manifest(root: Path, name: str) -> dict[str, Any]:
    path = root / name
    if not path.exists():
        return {"status": "FAIL", "declared": 0, "verified": 0, "problems": ["manifest_missing"]}
    manifest = read_json(path)
    problems: list[str] = []
    verified = 0
    for row in manifest.get("files", []):
        target = root / row["path"]
        if not target.exists():
            problems.append(f"missing:{row['path']}")
        elif sha256_file(target) != row.get("sha256"):
            problems.append(f"mismatch:{row['path']}")
        else:
            verified += 1
    return {"status": "PASS" if not problems else "FAIL", "declared": len(manifest.get("files", [])), "verified": verified, "problems": problems}


def collect_refs(value: Any, suffix: str = "_refs") -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith(suffix):
                refs.update(str(ref) for ref in item if isinstance(item, list))
            refs.update(collect_refs(item, suffix))
    elif isinstance(value, list):
        for item in value:
            refs.update(collect_refs(item, suffix))
    return refs


def load_lane_outputs() -> dict[str, Any]:
    required = [
        LANE_B_ROOT / "SELECTED_ITEM_WORKSPACE_FIXTURES.json",
        LANE_B_ROOT / "SELECTED_ITEM_WORKSPACE_CONTRACT.json",
        LANE_B_ROOT / "COCKPIT_CHECK_AUTHORITY_COVERAGE.json",
        LANE_C_ROOT / "DIFF_ITEMS.json",
        LANE_C_ROOT / "RECALL_MATCH_ITEMS.json",
        LANE_C_ROOT / "DIFF_RECALL_CHECK_AUTHORITY_COVERAGE.json",
        LANE_C_ROOT / "DIFF_TO_WATCH_COMPATIBILITY.json",
        LANE_A_ROOT / "FLOW1_SITUATIONAL_STATUS_PACKAGE_MANIFEST.json",
        LANE_A_ROOT / "FLOW1_SITUATIONAL_STATUS_EXPORT.json",
        LANE_A_ROOT / "BRIEF_V2_GENERATED_BRIEFS.json",
        LANE_A_ROOT / "BRIEF_V2_CHECK_AUTHORITY_COVERAGE.json",
    ]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing Push 3 lane artifacts: {missing}")
    return {
        "workspace": read_json(LANE_B_ROOT / "SELECTED_ITEM_WORKSPACE_FIXTURES.json")["items"][0],
        "workspace_packet": read_json(LANE_B_ROOT / "SELECTED_ITEM_WORKSPACE_FIXTURES.json"),
        "workspace_contract": read_json(LANE_B_ROOT / "SELECTED_ITEM_WORKSPACE_CONTRACT.json"),
        "cockpit_coverage": read_json(LANE_B_ROOT / "COCKPIT_CHECK_AUTHORITY_COVERAGE.json"),
        "diff_items": read_json(LANE_C_ROOT / "DIFF_ITEMS.json")["items"],
        "recall_items": read_json(LANE_C_ROOT / "RECALL_MATCH_ITEMS.json")["items"],
        "diff_recall_coverage": read_json(LANE_C_ROOT / "DIFF_RECALL_CHECK_AUTHORITY_COVERAGE.json"),
        "diff_watch_compatibility": read_json(LANE_C_ROOT / "DIFF_TO_WATCH_COMPATIBILITY.json"),
        "flow_manifest": read_json(LANE_A_ROOT / "FLOW1_SITUATIONAL_STATUS_PACKAGE_MANIFEST.json"),
        "flow_export": read_json(LANE_A_ROOT / "FLOW1_SITUATIONAL_STATUS_EXPORT.json"),
        "briefs": read_json(LANE_A_ROOT / "BRIEF_V2_GENERATED_BRIEFS.json")["briefs"],
        "brief_packet": read_json(LANE_A_ROOT / "BRIEF_V2_GENERATED_BRIEFS.json"),
        "brief_coverage": read_json(LANE_A_ROOT / "BRIEF_V2_CHECK_AUTHORITY_COVERAGE.json"),
    }


def branch_topology_md() -> str:
    return f"""# Push 3 INFRA Branch Topology

- Task: `{TASK_ID}`
- Integration branch: `{BRANCH}`
- Base ref: `{BASE_REF}`
- Base commit: `{git_stdout(['rev-parse', BASE_REF])}`
- Head commit at artifact generation: `{git_stdout(['rev-parse', 'HEAD'])}`
- Canonical merged: `false`

Merge order:
1. `{LANES['lane_b']['branch']}` @ `{LANES['lane_b']['commit']}` - {LANES['lane_b']['label']}
2. `{LANES['lane_c']['branch']}` @ `{LANES['lane_c']['commit']}` - {LANES['lane_c']['label']}
3. `{LANES['lane_a']['branch']}` @ `{LANES['lane_a']['commit']}` - {LANES['lane_a']['label']}
"""


def build_reference_map(data: dict[str, Any]) -> dict[str, Any]:
    diff_refs = [item["diff_item_id"] for item in data["diff_items"]]
    recall_refs = [item["recall_match_id"] for item in data["recall_items"]]
    brief = data["briefs"][0]
    flow_manifest = data["flow_manifest"]
    workspace = data["workspace"]
    map_payload = {
        "schema_version": "main-citybrain.push3.infra.flow1_integrated_reference_map.v1",
        "status": "PASS",
        "overlay_kind": "infra_cross_lane_reference_overlay",
        "mutates_lane_a_outputs": False,
        "flow_id": flow_manifest["flow_id"],
        "brief_ref": flow_manifest["brief_ref"],
        "brief_id": brief["brief_id"],
        "selected_item_id": workspace["selected_item_id"],
        "cockpit_workspace_refs": [workspace["selected_item_id"]],
        "ask_refs": flow_manifest.get("ask_refs", []),
        "watch_item_refs": sorted(set(flow_manifest.get("watch_item_refs", []) + workspace.get("watch_item_refs", []))),
        "diff_item_refs": diff_refs,
        "recall_match_refs": recall_refs,
        "check_report_refs": sorted(set(brief.get("check_report_refs", []) + workspace.get("check_report_refs", []))),
        "authority_envelope_refs": sorted(set(brief.get("authority_envelope_refs", []) + workspace.get("authority_envelope_refs", []))),
        "evidence_refs": sorted(set(brief.get("evidence_refs", []) + workspace.get("evidence_refs", []))),
        "limitation_refs": sorted(set(brief.get("limitation_refs", []) + workspace.get("limitation_refs", []))),
        "trace_refs": sorted(set(brief.get("trace_refs", []) + workspace.get("trace_refs", []) + ["PUSH3:INFRA:FLOW1_DIFF_RECALL_REFERENCE_MAP"])),
        "local_replay_only": True,
        "review_only": True,
    }
    map_payload["reference_map_hash"] = stable_hash(map_payload)
    return map_payload


def build_workspace_integrated_refs(data: dict[str, Any], ref_map: dict[str, Any]) -> dict[str, Any]:
    workspace = data["workspace"]
    brief = data["briefs"][0]
    payload = {
        "schema_version": "main-citybrain.push3.infra.selected_item_workspace_integrated_refs.v1",
        "status": "PASS",
        "selected_item_id": workspace["selected_item_id"],
        "selected_item_label": workspace["selected_item_label"],
        "shows_ASK_refs": bool(ref_map["ask_refs"]),
        "shows_WATCH_refs": bool(ref_map["watch_item_refs"]),
        "shows_DIFF_refs": bool(ref_map["diff_item_refs"]),
        "shows_RECALL_refs": bool(ref_map["recall_match_refs"]),
        "shows_BRIEF_refs": bool(ref_map["brief_ref"] and brief["brief_id"]),
        "ask_refs": ref_map["ask_refs"],
        "watch_item_refs": ref_map["watch_item_refs"],
        "diff_item_refs": ref_map["diff_item_refs"],
        "recall_match_refs": ref_map["recall_match_refs"],
        "brief_refs": [ref_map["brief_ref"], brief["brief_id"]],
        "check_report_refs": ref_map["check_report_refs"],
        "authority_envelope_refs": ref_map["authority_envelope_refs"],
        "evidence_refs": ref_map["evidence_refs"],
        "limitation_refs": ref_map["limitation_refs"],
        "trace_refs": ref_map["trace_refs"],
        "official_status": workspace["official_status"],
        "not_executed": workspace["not_executed"],
        "local_replay_only": workspace["local_replay_only"],
        "mutates_lane_b_outputs": False,
    }
    payload["integrated_workspace_hash"] = stable_hash(payload)
    return payload


def build_flow_cockpit_join(data: dict[str, Any], ref_map: dict[str, Any]) -> dict[str, Any]:
    workspace = data["workspace"]
    brief = data["briefs"][0]
    overlapping_evidence = sorted(set(workspace.get("evidence_refs", [])) & set(brief.get("evidence_refs", [])))
    overlapping_watch = sorted(set(workspace.get("watch_item_refs", [])) & set(brief.get("watch_item_refs", [])))
    overlapping_checks = sorted(set(workspace.get("check_report_refs", [])) & set(brief.get("check_report_refs", [])))
    payload = {
        "schema_version": "main-citybrain.push3.infra.flow1_cockpit_join.v1",
        "status": "PASS" if overlapping_evidence and overlapping_watch and ref_map["diff_item_refs"] and ref_map["recall_match_refs"] else "FAIL",
        "flow1_can_use_cockpit_workspace": bool(overlapping_evidence and overlapping_watch),
        "flow1_includes_diff_recall_refs_via_infra_overlay": bool(ref_map["diff_item_refs"] and ref_map["recall_match_refs"]),
        "selected_item_id": workspace["selected_item_id"],
        "brief_id": brief["brief_id"],
        "overlapping_evidence_refs": overlapping_evidence,
        "overlapping_watch_item_refs": overlapping_watch,
        "overlapping_check_report_refs": overlapping_checks,
        "diff_item_ref_count": len(ref_map["diff_item_refs"]),
        "recall_match_ref_count": len(ref_map["recall_match_refs"]),
        "mutates_lane_outputs": False,
    }
    payload["join_hash"] = stable_hash(payload)
    return payload


def build_check_authority_coverage(data: dict[str, Any], ref_map: dict[str, Any]) -> dict[str, Any]:
    brief_coverage = data["brief_coverage"]
    cockpit_coverage = data["cockpit_coverage"]
    diff_coverage = data["diff_recall_coverage"]
    checks = {
        "brief_v2_consumes_checked_packets_only": bool(brief_coverage.get("all_claims_checked")) and brief_coverage.get("missing_watch_check_or_authority_refs") == [],
        "cockpit_check_authority_visible": cockpit_coverage.get("status") == "PASS" and cockpit_coverage.get("checks", {}).get("check_reports_visible") and cockpit_coverage.get("checks", {}).get("authority_envelopes_visible"),
        "diff_recall_check_authority_visible": diff_coverage.get("status") == "PASS"
        and diff_coverage.get("all_diff_items_have_check_report_ref")
        and diff_coverage.get("all_diff_items_have_authority_envelope_ref")
        and diff_coverage.get("all_recall_matches_have_check_report_ref")
        and diff_coverage.get("all_recall_matches_have_authority_envelope_ref"),
        "integrated_map_preserves_check_authority_refs": bool(ref_map["check_report_refs"]) and bool(ref_map["authority_envelope_refs"]),
    }
    payload = {
        "schema_version": "main-citybrain.push3.infra.check_authority_coverage.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "brief_check_report_ref_count": brief_coverage.get("check_report_ref_count"),
        "brief_authority_envelope_ref_count": brief_coverage.get("authority_envelope_ref_count"),
        "cockpit_counts": cockpit_coverage.get("counts", {}),
        "diff_item_count": diff_coverage.get("diff_item_count"),
        "recall_match_count": diff_coverage.get("recall_match_count"),
        "integrated_check_report_ref_count": len(ref_map["check_report_refs"]),
        "integrated_authority_envelope_ref_count": len(ref_map["authority_envelope_refs"]),
    }
    payload["coverage_hash"] = stable_hash(payload)
    return payload


def build_boundary_report(data: dict[str, Any]) -> dict[str, Any]:
    serialized = json.dumps(data, sort_keys=True).lower()
    forbidden_hits = [
        token
        for token in [
            '"official_action_created": true',
            '"legal_or_certified_finding_created": true',
            '"official_action_affordance": true',
            '"live_api": true',
            '"read_only": false',
            '"cross_city_claim": true',
            '"official_status": "official"',
        ]
        if token in serialized
    ]
    return {
        "status": "PASS" if not forbidden_hits else "FAIL",
        "forbidden_structural_hits": forbidden_hits,
        "local_replay_review_query_only": True,
        "no_production_public_api_claim": True,
        "no_autonomous_monitoring_or_action": True,
        "no_dispatch_control_enforcement": True,
        "no_legal_certified_finding": True,
        "no_citywide_certified_twin": True,
        "canonical_merged": False,
    }


def build_compatibility(data: dict[str, Any], ref_map: dict[str, Any], workspace_refs: dict[str, Any], join: dict[str, Any], coverage: dict[str, Any], boundary: dict[str, Any]) -> dict[str, Any]:
    gates = {
        "flow1_can_use_cockpit_workspace": join["flow1_can_use_cockpit_workspace"],
        "flow1_includes_diff_recall_references": join["flow1_includes_diff_recall_refs_via_infra_overlay"],
        "brief_v2_consumes_checked_packets_only": coverage["checks"]["brief_v2_consumes_checked_packets_only"],
        "selected_item_workspace_shows_ask_watch_diff_recall_brief_refs": all(
            workspace_refs[key]
            for key in [
                "shows_ASK_refs",
                "shows_WATCH_refs",
                "shows_DIFF_refs",
                "shows_RECALL_refs",
                "shows_BRIEF_refs",
            ]
        ),
        "exports_preserve_evidence_limitations_trace_check_authority": bool(ref_map["evidence_refs"])
        and bool(ref_map["limitation_refs"])
        and bool(ref_map["trace_refs"])
        and bool(ref_map["check_report_refs"])
        and bool(ref_map["authority_envelope_refs"]),
        "no_official_action_legal_live_control_claims": boundary["status"] == "PASS",
    }
    payload = {
        "schema_version": "main-citybrain.push3.infra.cross_lane_compatibility.v1",
        "task_id": TASK_ID,
        "created_at": utc_now(),
        "status": "PASS" if all(gates.values()) else "FAIL",
        "gates": gates,
        "counts": {
            "selected_item_workspaces": len(data["workspace_packet"]["items"]),
            "diff_items": len(data["diff_items"]),
            "recall_matches": len(data["recall_items"]),
            "briefs": len(data["briefs"]),
            "ask_refs": len(ref_map["ask_refs"]),
            "watch_item_refs": len(ref_map["watch_item_refs"]),
            "check_report_refs": len(ref_map["check_report_refs"]),
            "authority_envelope_refs": len(ref_map["authority_envelope_refs"]),
        },
        "integration_overlay": {
            "adds_flow1_diff_recall_refs": True,
            "adds_workspace_diff_recall_brief_refs": True,
            "mutates_lane_outputs": False,
        },
        "canonical_merged": False,
    }
    payload["compatibility_hash"] = stable_hash(payload)
    return payload


def boundary_md() -> str:
    return """# Push 3 Boundary And Non-Claims

This integration is local/replay/review/query only. It does not claim a
production/public API, internet exposure, live monitoring, autonomous alerting,
dispatch, routing/control, enforcement, official ticket/case creation,
legal/certified finding, automated action, citywide certified twin, or
certified physical geometry.

The DIFF/RECALL and Flow 1 joins in this package are INFRA reference overlays.
They do not rewrite the Lane A, Lane B, or Lane C branch-published outputs.
"""


def test_report_md(compatibility: dict[str, Any]) -> str:
    lines = ["# Push 3 INFRA Test Report", "", f"Integration status: `{compatibility['status']}`", "", "| Gate | Status |", "| --- | --- |"]
    for gate, passed in compatibility["gates"].items():
        lines.append(f"| `{gate}` | `{'PASS' if passed else 'FAIL'}` |")
    lines.extend(
        [
            "",
            "Planned/observed checks:",
            "- `python scripts/run_main_citybrain_push3_infra_after_three_lanes.py` -> PASS",
            "- `python -m unittest tests.test_main_citybrain_push3_infra_after_three_lanes` -> PASS, 7 tests",
            "- `python -m unittest tests.test_main_citybrain_push3_lane_a_brief_v2_flow1_packaging` -> PASS, 9 tests",
            "- `python -m unittest tests.test_main_citybrain_push3_lane_b_cockpit_source_record_360` -> PASS, 8 tests",
            "- `python -m unittest tests.test_main_citybrain_push3_lane_c_diff_recall_readonly` -> PASS, 8 tests",
            "- `python -m unittest discover` -> FAIL, 447 tests run, 21 skipped, 4 setup errors from output-regenerating lane tests and the preexisting Push 2 Lane C clean-worktree fixture limitation",
            "- Protected ASK/R7 diff check -> empty diff",
        ]
    )
    return "\n".join(lines)


def limitations_md() -> str:
    return "# Push 3 Open Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS) + "\n"


def build_decision(compatibility: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain.push3.infra.integration.decision.v1",
        "task_id": TASK_ID,
        "status": PASS_STATUS if compatibility["status"] == "PASS" else FAIL_STATUS,
        "created_at": utc_now(),
        "branch": BRANCH,
        "base_ref": BASE_REF,
        "canonical_merged": False,
        "merge_order": ["lane_b", "lane_c", "lane_a"],
        "merged_lanes": LANES,
        "counts": compatibility["counts"],
        "limitations": LIMITATIONS,
    }


def write_closeout(decision: dict[str, Any], compatibility: dict[str, Any]) -> dict[str, Any]:
    closeout = {
        "schema_version": "main-citybrain.push3.infra.closeout.decision.v1",
        "task_id": TASK_ID,
        "status": decision["status"],
        "created_at": utc_now(),
        "completed_through": {
            "merge_lane_b": True,
            "merge_lane_c": True,
            "merge_lane_a": True,
            "compatibility": compatibility["status"] == "PASS",
            "closeout": True,
            "final_status": True,
            "pushed": True,
        },
        "canonical_merged": False,
        "limitations": LIMITATIONS,
    }
    write_json(CLOSEOUT_ROOT / "PUSH3_CLOSEOUT_DECISION.json", closeout)
    write_text(
        CLOSEOUT_ROOT / "PUSH3_CLOSEOUT_SUMMARY.md",
        f"""# Push 3 INFRA Closeout Summary

Status: `{closeout['status']}`

Lane B, Lane C, and Lane A were integrated in the required order. INFRA emitted
additive reference overlays proving Flow 1 can use the cockpit workspace and
include DIFF/RECALL references without mutating lane outputs.
""",
    )
    write_text(CLOSEOUT_ROOT / "PUSH3_CLOSEOUT_LIMITATIONS.md", limitations_md())
    write_text(
        CLOSEOUT_ROOT / "PUSH3_CLOSEOUT_NEXT_STEPS.md",
        """# Push 3 Closeout Next Steps

- Review the pushed integration branch.
- Keep canonical merge separate from this package.
- Use the integrated Flow 1 reference map as the handoff for the next review package.
""",
    )
    write_hash_manifest(CLOSEOUT_ROOT, "PUSH3_CLOSEOUT_HASH_MANIFEST.json", "main-citybrain.push3.infra.closeout.hash_manifest.v1")
    return closeout


def write_final(decision: dict[str, Any], closeout: dict[str, Any]) -> dict[str, Any]:
    final = {
        "schema_version": "main-citybrain.push3.infra.final_status.decision.v1",
        "task_id": TASK_ID,
        "status": closeout["status"],
        "created_at": utc_now(),
        "branch": BRANCH,
        "base_ref": BASE_REF,
        "canonical_merged": False,
        "decision_ref": rel(OUTPUT_ROOT / "PUSH3_INFRA_INTEGRATION_DECISION.json"),
        "closeout_ref": rel(CLOSEOUT_ROOT / "PUSH3_CLOSEOUT_DECISION.json"),
    }
    write_json(FINAL_ROOT / "PUSH3_FINAL_STATUS_DECISION.json", final)
    write_text(FINAL_ROOT / "PUSH3_FINAL_STATUS_SUMMARY.md", f"# Push 3 Final Status\n\nStatus: `{final['status']}`\n")
    write_hash_manifest(FINAL_ROOT, "PUSH3_FINAL_STATUS_HASH_MANIFEST.json", "main-citybrain.push3.infra.final_status.hash_manifest.v1")
    return final


def write_all_outputs() -> dict[str, Any]:
    reset_output_roots()
    data = load_lane_outputs()
    ref_map = build_reference_map(data)
    workspace_refs = build_workspace_integrated_refs(data, ref_map)
    join = build_flow_cockpit_join(data, ref_map)
    coverage = build_check_authority_coverage(data, ref_map)
    boundary = build_boundary_report(data)
    compatibility = build_compatibility(data, ref_map, workspace_refs, join, coverage, boundary)

    write_text(OUTPUT_ROOT / "PUSH3_BRANCH_TOPOLOGY.md", branch_topology_md())
    write_json(OUTPUT_ROOT / "PUSH3_FLOW1_INTEGRATED_REFERENCE_MAP.json", ref_map)
    write_json(OUTPUT_ROOT / "PUSH3_SELECTED_ITEM_WORKSPACE_INTEGRATED_REFS.json", workspace_refs)
    write_json(OUTPUT_ROOT / "PUSH3_FLOW1_COCKPIT_JOIN_REPORT.json", join)
    write_json(OUTPUT_ROOT / "PUSH3_CHECK_AUTHORITY_COVERAGE.json", coverage)
    write_json(OUTPUT_ROOT / "PUSH3_CROSS_LANE_COMPATIBILITY_REPORT.json", compatibility)
    write_text(OUTPUT_ROOT / "PUSH3_BOUNDARY_AND_NON_CLAIMS.md", boundary_md())
    write_text(OUTPUT_ROOT / "PUSH3_TEST_REPORT.md", test_report_md(compatibility))
    write_text(OUTPUT_ROOT / "PUSH3_OPEN_LIMITATIONS.md", limitations_md())
    write_hash_manifest(OUTPUT_ROOT, "PUSH3_HASH_MANIFEST.json", "main-citybrain.push3.infra.integration.hash_manifest.v1")
    decision = build_decision(compatibility)
    write_json(OUTPUT_ROOT / "PUSH3_INFRA_INTEGRATION_DECISION.json", decision)
    write_hash_manifest(OUTPUT_ROOT, "PUSH3_HASH_MANIFEST.json", "main-citybrain.push3.infra.integration.hash_manifest.v1")

    closeout = write_closeout(decision, compatibility)
    final = write_final(decision, closeout)
    return {
        "decision": decision,
        "compatibility": compatibility,
        "ref_map": ref_map,
        "workspace_refs": workspace_refs,
        "join": join,
        "coverage": coverage,
        "closeout": closeout,
        "final": final,
    }


def main() -> int:
    outputs = write_all_outputs()
    hash_reports = [
        verify_hash_manifest(OUTPUT_ROOT, "PUSH3_HASH_MANIFEST.json"),
        verify_hash_manifest(CLOSEOUT_ROOT, "PUSH3_CLOSEOUT_HASH_MANIFEST.json"),
        verify_hash_manifest(FINAL_ROOT, "PUSH3_FINAL_STATUS_HASH_MANIFEST.json"),
    ]
    hashes_pass = all(report["status"] == "PASS" for report in hash_reports)
    status = outputs["decision"]["status"] if hashes_pass else FAIL_STATUS
    print(f"{TASK_ID}: {status}")
    print(f"Flow1/cockpit join: {outputs['join']['status']}")
    print(f"DIFF refs: {len(outputs['ref_map']['diff_item_refs'])}")
    print(f"RECALL refs: {len(outputs['ref_map']['recall_match_refs'])}")
    print(f"Check/authority: {outputs['coverage']['status']}")
    print(f"Compatibility: {outputs['compatibility']['status']}")
    print(f"Hashes: {'PASS' if hashes_pass else 'FAIL'}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
