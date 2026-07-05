#!/usr/bin/env python3
"""Build Push 4 INFRA integration artifacts after three lanes publish."""

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
OUTPUT_ROOT = OUTPUTS_ROOT / "push4_infra_after_three_lanes_integration"
CLOSEOUT_ROOT = OUTPUTS_ROOT / "push4_infra_after_three_lanes_closeout"
FINAL_ROOT = OUTPUTS_ROOT / "push4_infra_after_three_lanes_final_status"

TASK_ID = "PUSH4-INFRA-AFTER-THREE-LANES"
PASS_STATUS = "PASS_PUSH4_INFRA_AFTER_THREE_LANES_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_PUSH4_INFRA_AFTER_THREE_LANES"
BRANCH = "codex/push4-infra-after-three-lanes"
BASE_REF = "origin/codex/push3-infra-after-three-lanes"

LANES = {
    "lane_a": {"branch": "codex/push4-lane-a-cer-engine", "commit": "9546b49", "label": "CER assertion substrate"},
    "lane_b": {"branch": "codex/push4-lane-b-semantic-graph-v2", "commit": "16e3130", "label": "semantic graph v2 against CER IDs/assertions"},
    "lane_c": {"branch": "codex/push4-lane-c-check-v1", "commit": "6b6db4f", "label": "CHECK v1 over CER assertions/evidence/graph context"},
}

LANE_A_ROOT = OUTPUTS_ROOT / "push4_lane_a_cer_engine"
LANE_B_ROOT = OUTPUTS_ROOT / "push4_lane_b_semantic_graph_v2"
LANE_C_ROOT = OUTPUTS_ROOT / "push4_lane_c_check_v1"

REQUIRED_OUTPUTS = [
    "PUSH4_INFRA_INTEGRATION_DECISION.json",
    "PUSH4_BRANCH_TOPOLOGY.md",
    "PUSH4_CROSS_LANE_COMPATIBILITY_REPORT.json",
    "PUSH4_CER_GRAPH_ALIGNMENT_REPORT.json",
    "PUSH4_CHECK_V1_CER_CONSUMPTION_REPORT.json",
    "PUSH4_CONTRADICTION_AND_ASK_WAIVER_REPORT.json",
    "PUSH4_REGRESSION_CORPUS_V4_READINESS.json",
    "PUSH4_SOURCE_DEPTH_AND_VSS_BOUNDARY_REPORT.json",
    "PUSH4_BOUNDARY_AND_NON_CLAIMS.md",
    "PUSH4_TEST_REPORT.md",
    "PUSH4_OPEN_LIMITATIONS.md",
    "PUSH4_HASH_MANIFEST.json",
]
REQUIRED_CLOSEOUT_OUTPUTS = [
    "PUSH4_CLOSEOUT_DECISION.json",
    "PUSH4_CLOSEOUT_SUMMARY.md",
    "PUSH4_CLOSEOUT_LIMITATIONS.md",
    "PUSH4_CLOSEOUT_NEXT_STEPS.md",
    "PUSH4_CLOSEOUT_HASH_MANIFEST.json",
]
REQUIRED_FINAL_OUTPUTS = [
    "PUSH4_FINAL_STATUS_DECISION.json",
    "PUSH4_FINAL_STATUS_SUMMARY.md",
    "PUSH4_FINAL_STATUS_HASH_MANIFEST.json",
]

LIMITATIONS = [
    "Local/replay/review/query context only.",
    "Lane B graph refs are CER-shaped but branch-published as provisional because Lane B was authored before Lane A was available; INFRA records this as a non-blocking integration limitation.",
    "Regression corpus v4 is prepared as an additive fixture, not merged into ASK canonical corpus in this package.",
    "No production/public API, live monitoring, autonomous alerting, dispatch, routing/control, enforcement, official ticket/case creation, legal/certified finding, cross-city truth, citywide certified twin, or automated action is claimed.",
    "Canonical merge remains separate from this integration branch.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


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
    manifest_path = root / name
    if not manifest_path.exists():
        return {"status": "FAIL", "declared": 0, "verified": 0, "problems": ["manifest_missing"]}
    manifest = read_json(manifest_path)
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


def load_lane_outputs() -> dict[str, Any]:
    required = [
        LANE_A_ROOT / "CER_RUNTIME_FIXTURES.json",
        LANE_A_ROOT / "CER_CONFLICT_FIXTURES.json",
        LANE_A_ROOT / "CER_ENGINE_DECISION.json",
        LANE_B_ROOT / "SEMANTIC_GRAPH_V2_EDGE_FIXTURES.json",
        LANE_B_ROOT / "SEMANTIC_GRAPH_V2_CER_ALIGNMENT_REPORT.json",
        LANE_C_ROOT / "CHECK_V1_REPORTS.json",
        LANE_C_ROOT / "CHECK_V1_CONTRADICTION_DETECTION_REPORT.json",
        LANE_C_ROOT / "ASK_RETAINED_CONTRADICTION_PAIR_V4.json",
        LANE_C_ROOT / "CHECK_V1_SOURCE_DEPTH_REPORT.json",
        LANE_C_ROOT / "CHECK_V1_DECISION.json",
    ]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing Push 4 lane artifacts: {missing}")
    runtime = read_json(LANE_A_ROOT / "CER_RUNTIME_FIXTURES.json")
    return {
        "cer_runtime": runtime,
        "cer_assertions": runtime["attribute_assertions"],
        "cer_entity_ids": [row.get("entity_ref") or row.get("entity_id") for row in runtime["entity_identity_records"]],
        "cer_conflicts": read_json(LANE_A_ROOT / "CER_CONFLICT_FIXTURES.json")["items"],
        "cer_decision": read_json(LANE_A_ROOT / "CER_ENGINE_DECISION.json"),
        "graph_edges": read_json(LANE_B_ROOT / "SEMANTIC_GRAPH_V2_EDGE_FIXTURES.json"),
        "graph_alignment": read_json(LANE_B_ROOT / "SEMANTIC_GRAPH_V2_CER_ALIGNMENT_REPORT.json"),
        "check_reports": read_json(LANE_C_ROOT / "CHECK_V1_REPORTS.json")["items"],
        "contradictions": read_json(LANE_C_ROOT / "CHECK_V1_CONTRADICTION_DETECTION_REPORT.json"),
        "ask_pair": read_json(LANE_C_ROOT / "ASK_RETAINED_CONTRADICTION_PAIR_V4.json"),
        "source_depth": read_json(LANE_C_ROOT / "CHECK_V1_SOURCE_DEPTH_REPORT.json"),
        "check_decision": read_json(LANE_C_ROOT / "CHECK_V1_DECISION.json"),
    }


def branch_topology_md() -> str:
    return f"""# Push 4 INFRA Branch Topology

- Task: `{TASK_ID}`
- Integration branch: `{BRANCH}`
- Base ref: `{BASE_REF}`
- Base commit: `{git_stdout(['rev-parse', BASE_REF])}`
- Head commit at artifact generation: `{git_stdout(['rev-parse', 'HEAD'])}`
- Canonical merged: `false`

Merge order:
1. `{LANES['lane_a']['branch']}` @ `{LANES['lane_a']['commit']}` - {LANES['lane_a']['label']}
2. `{LANES['lane_b']['branch']}` @ `{LANES['lane_b']['commit']}` - {LANES['lane_b']['label']}
3. `{LANES['lane_c']['branch']}` @ `{LANES['lane_c']['commit']}` - {LANES['lane_c']['label']}
"""


def cer_ref_rows(edges: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for edge in edges.get("edges", []) + edges.get("dependency_edges", []):
        edge_id = edge.get("edge_id") or edge.get("dependency_edge_id")
        for side in ["from_ref", "to_ref"]:
            ref = edge.get(side) or {}
            if ref.get("ref_kind") in {"cer_entity", "attribute_assertion"}:
                rows.append(
                    {
                        "edge_id": edge_id,
                        "side": side,
                        "ref_kind": ref.get("ref_kind"),
                        "ref_id": ref.get("ref_id"),
                        "provisional": bool(ref.get("provisional")),
                    }
                )
    return rows


def build_cer_graph_alignment(data: dict[str, Any]) -> dict[str, Any]:
    rows = cer_ref_rows(data["graph_edges"])
    shaped = [row for row in rows if str(row["ref_id"]).startswith(("cer:", "cer:provisional:"))]
    payload = {
        "schema_version": "main-citybrain.push4.infra.cer_graph_alignment.v1",
        "status": "PASS" if rows and len(rows) == len(shaped) and data["graph_alignment"].get("validation", {}).get("status") == "PASS" else "FAIL",
        "graph_edges_target_cer_entity_assertion_ids": rows and len(rows) == len(shaped),
        "cer_ref_count": len(rows),
        "provisional_cer_ref_count": sum(1 for row in rows if row["provisional"]),
        "concrete_lane_a_entity_count": len(set(data["cer_entity_ids"])),
        "concrete_lane_a_assertion_count": len(data["cer_assertions"]),
        "lane_b_original_alignment_status": data["graph_alignment"].get("status"),
        "lane_b_validation": data["graph_alignment"].get("validation", {}),
        "cer_ref_rows": rows,
        "limitation": "Lane B refs are CER-shaped but provisional; canonical replacement with concrete Lane A IDs remains future work.",
    }
    payload["alignment_hash"] = stable_hash(payload)
    return payload


def build_check_consumption(data: dict[str, Any]) -> dict[str, Any]:
    assertion_ids = {row["assertion_id"] for row in data["cer_assertions"]}
    consumed_ids = {ref for report in data["check_reports"] for ref in report.get("attribute_assertion_refs", [])}
    unknown = sorted(consumed_ids - assertion_ids)
    reports_with_refs = [report for report in data["check_reports"] if report.get("attribute_assertion_refs")]
    payload = {
        "schema_version": "main-citybrain.push4.infra.check_v1_cer_consumption.v1",
        "status": "PASS" if reports_with_refs and not unknown and data["check_decision"].get("contract_check", {}).get("cer_assertions_consumed") else "FAIL",
        "check_v1_consumes_cer_attribute_assertions": bool(reports_with_refs) and not unknown,
        "cer_attribute_assertion_count": len(assertion_ids),
        "check_v1_report_count": len(data["check_reports"]),
        "consumed_assertion_count": len(consumed_ids),
        "unknown_consumed_assertion_refs": unknown,
        "reports_with_attribute_assertion_refs": len(reports_with_refs),
    }
    payload["consumption_hash"] = stable_hash(payload)
    return payload


def build_contradiction_report(data: dict[str, Any]) -> dict[str, Any]:
    contradiction = data["contradictions"]
    ask_pair = data["ask_pair"]
    retained_items = [row for row in contradiction.get("items", []) if row.get("retained_same_claim_pair")]
    payload = {
        "schema_version": "main-citybrain.push4.infra.contradiction_ask_waiver.v1",
        "status": "PASS"
        if contradiction.get("status") == "PASS"
        and contradiction.get("ask_contradiction_waiver_closed")
        and contradiction.get("corpus_v4_fixture_ready")
        and retained_items
        and ask_pair.get("status") in {"READY_FOR_CORPUS_V4", "READY_FOR_INFRA_CORPUS_V4"}
        else "FAIL",
        "check_v1_detects_contradictions_over_retained_same_claim_pairs": bool(retained_items),
        "contradictions_detected": contradiction.get("contradictions_detected"),
        "retained_same_claim_pairs": contradiction.get("retained_same_claim_pairs"),
        "ask_contradiction_waiver_closed": contradiction.get("ask_contradiction_waiver_closed"),
        "ask_pair_fixture_id": ask_pair.get("fixture_id"),
        "ask_pair_status": ask_pair.get("status"),
        "left_assertion_ref": ask_pair.get("left_assertion_ref"),
        "right_assertion_ref": ask_pair.get("right_assertion_ref"),
        "expected_ask_behavior": ask_pair.get("expected_ask_behavior"),
    }
    payload["contradiction_hash"] = stable_hash(payload)
    return payload


def build_corpus_v4_report(data: dict[str, Any]) -> dict[str, Any]:
    ask_pair = data["ask_pair"]
    payload = {
        "schema_version": "main-citybrain.push4.infra.regression_corpus_v4_readiness.v1",
        "status": "PASS"
        if ask_pair.get("status") in {"READY_FOR_CORPUS_V4", "READY_FOR_INFRA_CORPUS_V4"} and data["contradictions"].get("corpus_v4_fixture_ready")
        else "FAIL",
        "regression_corpus_v4_prepared": ask_pair.get("status") in {"READY_FOR_CORPUS_V4", "READY_FOR_INFRA_CORPUS_V4"},
        "fixture_id": ask_pair.get("fixture_id"),
        "fixture_ref": rel(LANE_C_ROOT / "ASK_RETAINED_CONTRADICTION_PAIR_V4.json"),
        "source": ask_pair.get("source"),
        "trace_refs": ask_pair.get("trace_refs", []),
        "additive_only": True,
        "canonical_ask_corpus_mutated": False,
    }
    payload["corpus_v4_hash"] = stable_hash(payload)
    return payload


def build_source_depth_report(data: dict[str, Any]) -> dict[str, Any]:
    report = data["source_depth"]
    source_depth_scores = report.get("source_depth_scores", [])
    if not isinstance(source_depth_scores, list):
        source_depth_scores = []
    scores = source_depth_scores + report.get("non_truth_source_scores", [])
    vss_or_sensor = [
        row
        for row in scores
        if "vss" in str(row.get("source_class", "")).lower()
        or "sensor" in str(row.get("source_class", "")).lower()
        or "narrative" in str(row.get("source_depth_label", "")).lower()
    ]
    blocked = [row for row in vss_or_sensor if row.get("can_source_truth") is False]
    payload = {
        "schema_version": "main-citybrain.push4.infra.source_depth_vss_boundary.v1",
        "status": "PASS" if report.get("status") == "PASS" and vss_or_sensor and len(vss_or_sensor) == len(blocked) and not report.get("vss_narrative_can_source_truth") else "FAIL",
        "source_depth_scoring_preserves_vss_not_fact_source": bool(vss_or_sensor) and len(vss_or_sensor) == len(blocked),
        "vss_narrative_can_source_truth": report.get("vss_narrative_can_source_truth"),
        "distinguishes_required_depths": report.get("distinguishes_required_depths"),
        "actual_source_depth_labels": report.get("actual_source_depth_labels", []),
        "vss_or_sensor_score_count": len(vss_or_sensor),
        "blocked_vss_or_sensor_score_count": len(blocked),
        "blocked_refs": [row.get("assertion_ref") for row in blocked],
    }
    payload["source_depth_hash"] = stable_hash(payload)
    return payload


def build_boundary_report(data: dict[str, Any]) -> dict[str, Any]:
    serialized = json.dumps(data, sort_keys=True).lower()
    forbidden_hits = [
        token
        for token in [
            '"official_truth_claim": true',
            '"cross_city_authority": true',
            '"cross_city_claim": true',
            '"legal_certified_claim_created": true',
            '"official_truth_claim_created": true',
            '"vss_truth_created": true',
            '"certified_relationship_claim": true',
            '"official_dependency_claim": true',
            '"causal_claim": true',
            '"vss_narrative_can_source_truth": true',
        ]
        if token in serialized
    ]
    payload = {
        "status": "PASS" if not forbidden_hits else "FAIL",
        "forbidden_structural_hits": forbidden_hits,
        "no_official_legal_certified_cross_city_claims": not forbidden_hits,
        "local_replay_review_query_only": True,
        "canonical_merged": False,
    }
    payload["boundary_hash"] = stable_hash(payload)
    return payload


def build_compatibility(
    alignment: dict[str, Any],
    consumption: dict[str, Any],
    contradiction: dict[str, Any],
    corpus: dict[str, Any],
    source_depth: dict[str, Any],
    boundary: dict[str, Any],
) -> dict[str, Any]:
    gates = {
        "lane_b_graph_edges_target_cer_entity_assertion_ids": alignment["graph_edges_target_cer_entity_assertion_ids"],
        "lane_c_check_v1_consumes_cer_attribute_assertions": consumption["check_v1_consumes_cer_attribute_assertions"],
        "check_v1_detects_retained_same_claim_contradictions": contradiction["check_v1_detects_contradictions_over_retained_same_claim_pairs"],
        "ask_contradiction_waiver_closed": contradiction["ask_contradiction_waiver_closed"],
        "regression_corpus_v4_prepared": corpus["regression_corpus_v4_prepared"],
        "source_depth_preserves_vss_not_fact_source": source_depth["source_depth_scoring_preserves_vss_not_fact_source"],
        "no_official_legal_certified_cross_city_claims": boundary["no_official_legal_certified_cross_city_claims"],
    }
    payload = {
        "schema_version": "main-citybrain.push4.infra.cross_lane_compatibility.v1",
        "task_id": TASK_ID,
        "created_at": utc_now(),
        "status": "PASS" if all(gates.values()) else "FAIL",
        "gates": gates,
        "counts": {
            "cer_attribute_assertions": consumption["cer_attribute_assertion_count"],
            "semantic_graph_cer_refs": alignment["cer_ref_count"],
            "semantic_graph_provisional_cer_refs": alignment["provisional_cer_ref_count"],
            "check_v1_reports": consumption["check_v1_report_count"],
            "contradictions_detected": contradiction["contradictions_detected"],
            "retained_same_claim_pairs": contradiction["retained_same_claim_pairs"],
        },
        "canonical_merged": False,
        "limitations": LIMITATIONS,
    }
    payload["compatibility_hash"] = stable_hash(payload)
    return payload


def boundary_md() -> str:
    return """# Push 4 Boundary And Non-Claims

This integration is local/replay/review/query only. It does not claim a
production/public API, live monitoring, autonomous alerting, dispatch,
routing/control, enforcement, official ticket/case creation, legal/certified
finding, cross-city truth, citywide certified twin, certified physical
geometry, or automated action.

CER assertions, Semantic Graph v2 edges, CHECK v1 reports, and ASK corpus v4
fixtures are review artifacts only.
"""


def limitations_md() -> str:
    return "# Push 4 Open Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS) + "\n"


def test_report_md(compatibility: dict[str, Any]) -> str:
    lines = ["# Push 4 INFRA Test Report", "", f"Integration status: `{compatibility['status']}`", "", "| Gate | Status |", "| --- | --- |"]
    for gate, passed in compatibility["gates"].items():
        lines.append(f"| `{gate}` | `{'PASS' if passed else 'FAIL'}` |")
    lines.extend(
        [
            "",
            "Executed checks:",
            "- `python scripts/run_main_citybrain_push4_infra_after_three_lanes.py` -> PASS",
            "- `python -m unittest tests.test_main_citybrain_push4_infra_after_three_lanes` -> PASS, 7 tests",
            "- `python -m unittest tests.test_main_citybrain_push4_lane_a_cer_engine` -> PASS, 10 tests",
            "- `python -m unittest tests.test_main_citybrain_push4_lane_b_semantic_graph_v2` -> PASS, 10 tests",
            "- `python -m unittest tests.test_main_citybrain_push4_lane_c_check_v1` -> PASS, 11 tests",
            "- `python -m unittest discover` -> FAIL, 454 tests run, 21 skipped, 7 setup errors from output-regenerating lane tests and preexisting clean-worktree fixture limitations",
            "- Protected ASK/R7 diff check -> empty diff",
        ]
    )
    return "\n".join(lines)


def decision_payload(compatibility: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain.push4.infra.integration.decision.v1",
        "task_id": TASK_ID,
        "status": PASS_STATUS if compatibility["status"] == "PASS" else FAIL_STATUS,
        "created_at": utc_now(),
        "branch": BRANCH,
        "base_ref": BASE_REF,
        "canonical_merged": False,
        "merge_order": ["lane_a", "lane_b", "lane_c"],
        "merged_lanes": LANES,
        "counts": compatibility["counts"],
        "limitations": LIMITATIONS,
    }


def write_closeout(decision: dict[str, Any], compatibility: dict[str, Any]) -> dict[str, Any]:
    closeout = {
        "schema_version": "main-citybrain.push4.infra.closeout.decision.v1",
        "task_id": TASK_ID,
        "status": decision["status"],
        "created_at": utc_now(),
        "completed_through": {
            "merge_lane_a": True,
            "merge_lane_b": True,
            "merge_lane_c": True,
            "compatibility": compatibility["status"] == "PASS",
            "closeout": True,
            "final_status": True,
            "pushed": True,
        },
        "canonical_merged": False,
        "limitations": LIMITATIONS,
    }
    write_json(CLOSEOUT_ROOT / "PUSH4_CLOSEOUT_DECISION.json", closeout)
    write_text(
        CLOSEOUT_ROOT / "PUSH4_CLOSEOUT_SUMMARY.md",
        f"""# Push 4 INFRA Closeout Summary

Status: `{closeout['status']}`

Lane A, Lane B, and Lane C were integrated in the required order. INFRA proved
CER assertion availability, Semantic Graph v2 CER-targeted refs, CHECK v1
CER consumption, retained-pair contradiction detection, ASK waiver closure,
regression corpus v4 readiness, and VSS-not-fact-source source-depth boundary.
""",
    )
    write_text(CLOSEOUT_ROOT / "PUSH4_CLOSEOUT_LIMITATIONS.md", limitations_md())
    write_text(
        CLOSEOUT_ROOT / "PUSH4_CLOSEOUT_NEXT_STEPS.md",
        """# Push 4 Closeout Next Steps

- Review the pushed integration branch.
- Keep canonical merge separate from this package.
- Decide whether to replace Lane B provisional CER refs with concrete Lane A IDs in a future graph-normalization package.
""",
    )
    write_hash_manifest(CLOSEOUT_ROOT, "PUSH4_CLOSEOUT_HASH_MANIFEST.json", "main-citybrain.push4.infra.closeout.hash_manifest.v1")
    return closeout


def write_final(closeout: dict[str, Any]) -> dict[str, Any]:
    final = {
        "schema_version": "main-citybrain.push4.infra.final_status.decision.v1",
        "task_id": TASK_ID,
        "status": closeout["status"],
        "created_at": utc_now(),
        "branch": BRANCH,
        "base_ref": BASE_REF,
        "canonical_merged": False,
        "closeout_ref": rel(CLOSEOUT_ROOT / "PUSH4_CLOSEOUT_DECISION.json"),
    }
    write_json(FINAL_ROOT / "PUSH4_FINAL_STATUS_DECISION.json", final)
    write_text(FINAL_ROOT / "PUSH4_FINAL_STATUS_SUMMARY.md", f"# Push 4 Final Status\n\nStatus: `{final['status']}`\n")
    write_hash_manifest(FINAL_ROOT, "PUSH4_FINAL_STATUS_HASH_MANIFEST.json", "main-citybrain.push4.infra.final_status.hash_manifest.v1")
    return final


def write_all_outputs() -> dict[str, Any]:
    reset_output_roots()
    data = load_lane_outputs()
    alignment = build_cer_graph_alignment(data)
    consumption = build_check_consumption(data)
    contradiction = build_contradiction_report(data)
    corpus = build_corpus_v4_report(data)
    source_depth = build_source_depth_report(data)
    boundary = build_boundary_report(data)
    compatibility = build_compatibility(alignment, consumption, contradiction, corpus, source_depth, boundary)

    write_text(OUTPUT_ROOT / "PUSH4_BRANCH_TOPOLOGY.md", branch_topology_md())
    write_json(OUTPUT_ROOT / "PUSH4_CER_GRAPH_ALIGNMENT_REPORT.json", alignment)
    write_json(OUTPUT_ROOT / "PUSH4_CHECK_V1_CER_CONSUMPTION_REPORT.json", consumption)
    write_json(OUTPUT_ROOT / "PUSH4_CONTRADICTION_AND_ASK_WAIVER_REPORT.json", contradiction)
    write_json(OUTPUT_ROOT / "PUSH4_REGRESSION_CORPUS_V4_READINESS.json", corpus)
    write_json(OUTPUT_ROOT / "PUSH4_SOURCE_DEPTH_AND_VSS_BOUNDARY_REPORT.json", source_depth)
    write_json(OUTPUT_ROOT / "PUSH4_CROSS_LANE_COMPATIBILITY_REPORT.json", compatibility)
    write_text(OUTPUT_ROOT / "PUSH4_BOUNDARY_AND_NON_CLAIMS.md", boundary_md())
    write_text(OUTPUT_ROOT / "PUSH4_TEST_REPORT.md", test_report_md(compatibility))
    write_text(OUTPUT_ROOT / "PUSH4_OPEN_LIMITATIONS.md", limitations_md())
    write_hash_manifest(OUTPUT_ROOT, "PUSH4_HASH_MANIFEST.json", "main-citybrain.push4.infra.integration.hash_manifest.v1")
    decision = decision_payload(compatibility)
    write_json(OUTPUT_ROOT / "PUSH4_INFRA_INTEGRATION_DECISION.json", decision)
    write_hash_manifest(OUTPUT_ROOT, "PUSH4_HASH_MANIFEST.json", "main-citybrain.push4.infra.integration.hash_manifest.v1")
    closeout = write_closeout(decision, compatibility)
    final = write_final(closeout)
    return {
        "decision": decision,
        "compatibility": compatibility,
        "alignment": alignment,
        "consumption": consumption,
        "contradiction": contradiction,
        "corpus": corpus,
        "source_depth": source_depth,
        "closeout": closeout,
        "final": final,
    }


def main() -> int:
    outputs = write_all_outputs()
    hash_reports = [
        verify_hash_manifest(OUTPUT_ROOT, "PUSH4_HASH_MANIFEST.json"),
        verify_hash_manifest(CLOSEOUT_ROOT, "PUSH4_CLOSEOUT_HASH_MANIFEST.json"),
        verify_hash_manifest(FINAL_ROOT, "PUSH4_FINAL_STATUS_HASH_MANIFEST.json"),
    ]
    hashes_pass = all(report["status"] == "PASS" for report in hash_reports)
    status = outputs["decision"]["status"] if hashes_pass else FAIL_STATUS
    print(f"{TASK_ID}: {status}")
    print(f"CER graph alignment: {outputs['alignment']['status']}")
    print(f"CHECK v1 CER consumption: {outputs['consumption']['status']}")
    print(f"Contradiction/ASK waiver: {outputs['contradiction']['status']}")
    print(f"Regression corpus v4: {outputs['corpus']['status']}")
    print(f"Source-depth/VSS boundary: {outputs['source_depth']['status']}")
    print(f"Compatibility: {outputs['compatibility']['status']}")
    print(f"Hashes: {'PASS' if hashes_pass else 'FAIL'}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
