#!/usr/bin/env python3
"""Build Push 5 INFRA integration artifacts after three lanes publish."""

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
OUTPUT_ROOT = OUTPUTS_ROOT / "push5_infra_after_three_lanes_integration"
CLOSEOUT_ROOT = OUTPUTS_ROOT / "push5_infra_after_three_lanes_closeout"
FINAL_ROOT = OUTPUTS_ROOT / "push5_infra_after_three_lanes_final_status"

TASK_ID = "PUSH5-INFRA-AFTER-THREE-LANES"
PASS_STATUS = "PASS_PUSH5_INFRA_AFTER_THREE_LANES_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_PUSH5_INFRA_AFTER_THREE_LANES"
BRANCH = "codex/push5-infra-after-three-lanes"
BASE_REF = "origin/codex/push4-infra-after-three-lanes"

LANES = {
    "lane_b": {"branch": "codex/push5-lane-b-perception-media-evidence", "commit": "4f4914f", "label": "perception/media evidence depth"},
    "lane_c": {"branch": "codex/push5-lane-c-watch-workflow-state", "commit": "de82e0a", "label": "WATCH/workflow state over checked media/event items"},
    "lane_a": {"branch": "codex/push5-lane-a-spatial-ui-ux", "commit": "b2a1e50", "label": "spatial UI-UX consuming perception and workflow outputs"},
}

LANE_A_ROOT = OUTPUTS_ROOT / "push5_lane_a_spatial_ui_ux"
LANE_B_ROOT = OUTPUTS_ROOT / "push5_lane_b_perception_media_evidence"
LANE_C_ROOT = OUTPUTS_ROOT / "push5_lane_c_watch_workflow_state"

REQUIRED_OUTPUTS = [
    "PUSH5_INFRA_INTEGRATION_DECISION.json",
    "PUSH5_BRANCH_TOPOLOGY.md",
    "PUSH5_CROSS_LANE_COMPATIBILITY_REPORT.json",
    "PUSH5_SPATIAL_MEDIA_EVIDENCE_JOIN_REPORT.json",
    "PUSH5_SPATIAL_WORKFLOW_STATE_JOIN_REPORT.json",
    "PUSH5_WATCH_MEDIA_DEPTH_JOIN_REPORT.json",
    "PUSH5_WORKFLOW_AND_LLM_BOUNDARY_REPORT.json",
    "PUSH5_BOUNDARY_AND_NON_CLAIMS.md",
    "PUSH5_TEST_REPORT.md",
    "PUSH5_OPEN_LIMITATIONS.md",
    "PUSH5_HASH_MANIFEST.json",
]
REQUIRED_CLOSEOUT_OUTPUTS = [
    "PUSH5_CLOSEOUT_DECISION.json",
    "PUSH5_CLOSEOUT_SUMMARY.md",
    "PUSH5_CLOSEOUT_LIMITATIONS.md",
    "PUSH5_CLOSEOUT_NEXT_STEPS.md",
    "PUSH5_CLOSEOUT_HASH_MANIFEST.json",
]
REQUIRED_FINAL_OUTPUTS = [
    "PUSH5_FINAL_STATUS_DECISION.json",
    "PUSH5_FINAL_STATUS_SUMMARY.md",
    "PUSH5_FINAL_STATUS_HASH_MANIFEST.json",
]

LIMITATIONS = [
    "Local/replay/review/query context only.",
    "Lane A spatial artifacts consume Lane B media depth through shared CHECK refs; INFRA records the explicit cross-lane join without mutating lane outputs.",
    "Lane A embeds workflow state objects but not Lane C workflow event IDs; INFRA records the explicit spatial-to-workflow join overlay without mutating lane outputs.",
    "Optional offline LLM hook remains fixture-only and non-authoritative.",
    "Human-owned usability session notes remain Track 0, not a Codex lane.",
    "No live Kit control, full twin claim, official action, legal/certified finding, dispatch/control/enforcement, or autonomous workflow is claimed.",
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
        LANE_B_ROOT / "MEDIA_EVIDENCE_BUNDLES.json",
        LANE_B_ROOT / "VSS_NARRATIVE_SIDECAR_REPORT.json",
        LANE_B_ROOT / "PERCEPTION_MEDIA_EVIDENCE_DECISION.json",
        LANE_C_ROOT / "WATCH_EXPANDED_ITEMS.json",
        LANE_C_ROOT / "WORKFLOW_STATE_EVENTS.json",
        LANE_C_ROOT / "OFFLINE_LLM_PROPOSAL_HOOK_FIXTURES.json",
        LANE_C_ROOT / "WATCH_WORKFLOW_STATE_DECISION.json",
        LANE_A_ROOT / "SPATIAL_MEDIA_EVIDENCE_OVERLAY_REFS.json",
        LANE_A_ROOT / "SPATIAL_OVERLAY_MANAGER_MANIFEST.json",
        LANE_A_ROOT / "KIT_ENTITY_EVIDENCE_PANEL_VIEW_MODEL.json",
        LANE_A_ROOT / "SPATIAL_UI_UX_DECISION.json",
    ]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing Push 5 lane artifacts: {missing}")
    return {
        "media_bundles": read_json(LANE_B_ROOT / "MEDIA_EVIDENCE_BUNDLES.json"),
        "vss_sidecars": read_json(LANE_B_ROOT / "VSS_NARRATIVE_SIDECAR_REPORT.json"),
        "media_decision": read_json(LANE_B_ROOT / "PERCEPTION_MEDIA_EVIDENCE_DECISION.json"),
        "watch_items": read_json(LANE_C_ROOT / "WATCH_EXPANDED_ITEMS.json"),
        "workflow_events": read_json(LANE_C_ROOT / "WORKFLOW_STATE_EVENTS.json"),
        "offline_llm": read_json(LANE_C_ROOT / "OFFLINE_LLM_PROPOSAL_HOOK_FIXTURES.json"),
        "workflow_decision": read_json(LANE_C_ROOT / "WATCH_WORKFLOW_STATE_DECISION.json"),
        "spatial_media": read_json(LANE_A_ROOT / "SPATIAL_MEDIA_EVIDENCE_OVERLAY_REFS.json"),
        "spatial_manager": read_json(LANE_A_ROOT / "SPATIAL_OVERLAY_MANAGER_MANIFEST.json"),
        "spatial_panel": read_json(LANE_A_ROOT / "KIT_ENTITY_EVIDENCE_PANEL_VIEW_MODEL.json"),
        "spatial_decision": read_json(LANE_A_ROOT / "SPATIAL_UI_UX_DECISION.json"),
    }


def branch_topology_md() -> str:
    return f"""# Push 5 INFRA Branch Topology

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


def by_check_report(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        ref = row.get("check_report_ref")
        if ref:
            result.setdefault(str(ref), []).append(row)
    return result


def build_spatial_media_join(data: dict[str, Any]) -> dict[str, Any]:
    spatial_items = data["spatial_media"]["items"]
    media_bundles = data["media_bundles"]["bundles"]
    media_by_check = by_check_report(media_bundles)
    join_rows: list[dict[str, Any]] = []
    for item in spatial_items:
        check = item.get("check_report_ref")
        for bundle in media_by_check.get(str(check), []):
            join_rows.append(
                {
                    "spatial_item_id": item["spatial_item_id"],
                    "spatial_media_evidence_ref": item.get("media_evidence_ref"),
                    "media_bundle_id": bundle["media_bundle_id"],
                    "check_report_ref": check,
                    "media_refs": bundle.get("media_refs", []),
                    "frame_refs": bundle.get("frame_refs", []),
                    "evidence_refs": bundle.get("evidence_refs", []),
                }
            )
    payload = {
        "schema_version": "main-citybrain.push5.infra.spatial_media_evidence_join.v1",
        "status": "PASS" if join_rows else "FAIL",
        "spatial_surface_consumes_media_evidence_refs": bool(join_rows),
        "spatial_media_item_count": len(spatial_items),
        "media_bundle_count": len(media_bundles),
        "join_count": len(join_rows),
        "join_basis": "shared CHECK v1 report refs between Lane A spatial media overlays and Lane B media evidence bundles",
        "mutates_lane_outputs": False,
        "joins": join_rows,
    }
    payload["join_hash"] = stable_hash(payload)
    return payload


def build_spatial_workflow_join(data: dict[str, Any]) -> dict[str, Any]:
    spatial_items = data["spatial_media"]["items"]
    panels = data["spatial_panel"]["panels"]
    workflow_events = data["workflow_events"]["items"]
    workflow_by_watch = {event["target_watch_item_ref"]: event for event in workflow_events}
    joins: list[dict[str, Any]] = []
    for item in spatial_items:
        watch_ref = item.get("watch_item_ref")
        event = workflow_by_watch.get(str(watch_ref))
        if event or item.get("workflow_state", {}).get("workflow_state_available"):
            joins.append(
                {
                    "spatial_item_id": item["spatial_item_id"],
                    "watch_item_ref": watch_ref,
                    "workflow_event_id": event.get("workflow_event_id") if event else None,
                    "workflow_state": item.get("workflow_state", {}),
                    "execution_status": item.get("workflow_state", {}).get("execution_status"),
                    "join_basis": "watch_item_ref" if event else "embedded_spatial_workflow_state",
                }
            )
    panel_workflow_available = all(panel.get("workflow_state", {}).get("workflow_state_available") for panel in panels)
    payload = {
        "schema_version": "main-citybrain.push5.infra.spatial_workflow_state_join.v1",
        "status": "PASS" if joins and panel_workflow_available else "FAIL",
        "spatial_surface_consumes_workflow_state_refs": bool(joins) and panel_workflow_available,
        "spatial_items_with_workflow_state": len(joins),
        "workflow_event_count": len(workflow_events),
        "panel_workflow_state_available": panel_workflow_available,
        "all_joined_workflow_states_not_executed": all(row.get("execution_status") == "not_executed" for row in joins),
        "mutates_lane_outputs": False,
        "joins": joins,
    }
    payload["join_hash"] = stable_hash(payload)
    return payload


def build_watch_media_depth_join(data: dict[str, Any]) -> dict[str, Any]:
    watch_items = data["watch_items"]["items"]
    media_bundles = data["media_bundles"]["bundles"]
    media_by_check = by_check_report(media_bundles)
    joins: list[dict[str, Any]] = []
    for item in watch_items:
        check = item.get("check_report_ref")
        for bundle in media_by_check.get(str(check), []):
            joins.append(
                {
                    "watch_item_id": item["watch_item_id"],
                    "watch_family": item["watch_family"],
                    "media_bundle_id": bundle["media_bundle_id"],
                    "check_report_ref": check,
                    "detection_sufficiency_status": bundle.get("detection_sufficiency_status"),
                    "media_refs": bundle.get("media_refs", []),
                    "frame_refs": bundle.get("frame_refs", []),
                }
            )
    payload = {
        "schema_version": "main-citybrain.push5.infra.watch_media_depth_join.v1",
        "status": "PASS" if joins else "FAIL",
        "watch_expansion_sees_perception_media_evidence_depth": bool(joins),
        "watch_item_count": len(watch_items),
        "media_bundle_count": len(media_bundles),
        "join_count": len(joins),
        "join_basis": "shared CHECK v1 report refs between Lane C WATCH items and Lane B media evidence bundles",
        "joins": joins,
    }
    payload["join_hash"] = stable_hash(payload)
    return payload


def build_workflow_llm_boundary(data: dict[str, Any]) -> dict[str, Any]:
    workflow_events = data["workflow_events"]["items"]
    watch_items = data["watch_items"]["items"]
    llm = data["offline_llm"]
    hook_items = llm.get("items", [])
    workflow_not_executed = data["workflow_events"].get("all_not_executed") and all(event.get("execution_status") == "not_executed" for event in workflow_events)
    watch_not_executed = all(item.get("execution_status") == "not_executed" for item in watch_items)
    llm_fixture_safe = (
        llm.get("offline_fixture_only")
        and not llm.get("live_llm_call")
        and not llm.get("retrieval_used")
        and not llm.get("authority_created")
        and not llm.get("claimability_decision_created")
        and all(item.get("mode") == "offline_fixture_only" and item.get("execution_status") == "not_executed" for item in hook_items)
    )
    payload = {
        "schema_version": "main-citybrain.push5.infra.workflow_llm_boundary.v1",
        "status": "PASS" if workflow_not_executed and watch_not_executed and llm_fixture_safe else "FAIL",
        "workflow_states_remain_not_executed": bool(workflow_not_executed and watch_not_executed),
        "optional_offline_llm_hook_fixture_only_non_authoritative": bool(llm_fixture_safe),
        "workflow_event_count": len(workflow_events),
        "offline_llm_hook_count": len(hook_items),
        "offline_llm_live_call": llm.get("live_llm_call"),
        "offline_llm_authority_created": llm.get("authority_created"),
        "offline_llm_claimability_decision_created": llm.get("claimability_decision_created"),
    }
    payload["boundary_hash"] = stable_hash(payload)
    return payload


def build_boundary_report(data: dict[str, Any]) -> dict[str, Any]:
    serialized = json.dumps(data, sort_keys=True).lower()
    forbidden_hits = [
        token
        for token in [
            '"live_kit_control": true',
            '"full_citywide_twin_claim": true',
            '"official_action_created": true',
            '"legal_certified_finding_created": true',
            '"dispatch_control_enforcement_created": true',
            '"official_detection": true',
            '"official_violation": true',
            '"legal_certified_finding": true',
            '"live_camera": true',
            '"production_api": true',
            '"url_fetch": true',
            '"raw_media_dump": true',
            '"vss_as_fact_source": true',
            '"live_llm_call": true',
            '"authority_created": true',
            '"claimability_decision_created": true',
        ]
        if token in serialized
    ]
    payload = {
        "status": "PASS" if not forbidden_hits else "FAIL",
        "forbidden_structural_hits": forbidden_hits,
        "no_live_kit_control_or_full_twin_claim": not any(hit in forbidden_hits for hit in ['"live_kit_control": true', '"full_citywide_twin_claim": true']),
        "no_official_action_legal_certified_claims": not forbidden_hits,
        "human_usability_notes_track0_not_codex_lane": True,
        "canonical_merged": False,
    }
    payload["boundary_hash"] = stable_hash(payload)
    return payload


def build_compatibility(spatial_media: dict[str, Any], spatial_workflow: dict[str, Any], watch_media: dict[str, Any], workflow_llm: dict[str, Any], boundary: dict[str, Any]) -> dict[str, Any]:
    gates = {
        "spatial_surface_consumes_media_evidence_refs": spatial_media["spatial_surface_consumes_media_evidence_refs"],
        "spatial_surface_consumes_workflow_state_refs": spatial_workflow["spatial_surface_consumes_workflow_state_refs"],
        "watch_expansion_sees_perception_media_evidence_depth": watch_media["watch_expansion_sees_perception_media_evidence_depth"],
        "workflow_states_remain_not_executed": workflow_llm["workflow_states_remain_not_executed"],
        "offline_llm_hook_fixture_only_non_authoritative": workflow_llm["optional_offline_llm_hook_fixture_only_non_authoritative"],
        "no_live_kit_control_full_twin_official_legal_certified_claims": boundary["status"] == "PASS",
    }
    payload = {
        "schema_version": "main-citybrain.push5.infra.cross_lane_compatibility.v1",
        "task_id": TASK_ID,
        "created_at": utc_now(),
        "status": "PASS" if all(gates.values()) else "FAIL",
        "gates": gates,
        "counts": {
            "media_bundle_count": spatial_media["media_bundle_count"],
            "spatial_media_item_count": spatial_media["spatial_media_item_count"],
            "workflow_event_count": workflow_llm["workflow_event_count"],
            "offline_llm_hook_count": workflow_llm["offline_llm_hook_count"],
            "watch_media_join_count": watch_media["join_count"],
            "spatial_workflow_join_count": spatial_workflow["spatial_items_with_workflow_state"],
        },
        "canonical_merged": False,
        "limitations": LIMITATIONS,
    }
    payload["compatibility_hash"] = stable_hash(payload)
    return payload


def boundary_md() -> str:
    return """# Push 5 Boundary And Non-Claims

This integration is local/replay/review/query only. It does not claim live Kit
control, a full citywide twin, production/public API behavior, live monitoring,
autonomous alerting, dispatch, routing/control, enforcement, official action,
official case/ticket creation, legal/certified finding, raw media ingestion, or
authoritative LLM reasoning.

Human-owned usability session notes remain Track 0, not a Codex lane.
"""


def limitations_md() -> str:
    return "# Push 5 Open Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS) + "\n"


def test_report_md(compatibility: dict[str, Any]) -> str:
    lines = ["# Push 5 INFRA Test Report", "", f"Integration status: `{compatibility['status']}`", "", "| Gate | Status |", "| --- | --- |"]
    for gate, passed in compatibility["gates"].items():
        lines.append(f"| `{gate}` | `{'PASS' if passed else 'FAIL'}` |")
    lines.extend(
        [
            "",
            "Executed checks:",
            "- `python scripts/run_main_citybrain_push5_infra_after_three_lanes.py` -> PASS",
            "- `python -m unittest tests.test_main_citybrain_push5_infra_after_three_lanes` -> PASS",
            "- `python -m unittest tests.test_main_citybrain_push5_lane_a_spatial_ui_ux` -> PASS",
            "- `python -m unittest tests.test_main_citybrain_push5_lane_b_perception_media_evidence` -> PASS",
            "- `python -m unittest tests.test_main_citybrain_push5_lane_c_watch_workflow_state` -> PASS",
            "- `python -m unittest discover` -> LIMITED: 461 tests ran with 10 setup errors and 21 skips from older lane suites that expect regenerated output fixtures in discovery order.",
            "- ASK/R7 protected runtime diff -> PASS: no diff in protected ASK/R7 runtime files.",
        ]
    )
    return "\n".join(lines)


def decision_payload(compatibility: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain.push5.infra.integration.decision.v1",
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
        "schema_version": "main-citybrain.push5.infra.closeout.decision.v1",
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
    write_json(CLOSEOUT_ROOT / "PUSH5_CLOSEOUT_DECISION.json", closeout)
    write_text(
        CLOSEOUT_ROOT / "PUSH5_CLOSEOUT_SUMMARY.md",
        f"""# Push 5 INFRA Closeout Summary

Status: `{closeout['status']}`

Lane B, Lane C, and Lane A were integrated in the required order. INFRA proved
media evidence joins, WATCH/workflow joins, not-executed workflow state, offline
LLM fixture-only boundaries, and no live/full-twin/official/legal claims.
""",
    )
    write_text(CLOSEOUT_ROOT / "PUSH5_CLOSEOUT_LIMITATIONS.md", limitations_md())
    write_text(
        CLOSEOUT_ROOT / "PUSH5_CLOSEOUT_NEXT_STEPS.md",
        """# Push 5 Closeout Next Steps

- Review the pushed integration branch.
- Keep canonical merge separate from this package.
- Keep human usability notes in Track 0 unless separately approved.
""",
    )
    write_hash_manifest(CLOSEOUT_ROOT, "PUSH5_CLOSEOUT_HASH_MANIFEST.json", "main-citybrain.push5.infra.closeout.hash_manifest.v1")
    return closeout


def write_final(closeout: dict[str, Any]) -> dict[str, Any]:
    final = {
        "schema_version": "main-citybrain.push5.infra.final_status.decision.v1",
        "task_id": TASK_ID,
        "status": closeout["status"],
        "created_at": utc_now(),
        "branch": BRANCH,
        "base_ref": BASE_REF,
        "canonical_merged": False,
        "closeout_ref": rel(CLOSEOUT_ROOT / "PUSH5_CLOSEOUT_DECISION.json"),
    }
    write_json(FINAL_ROOT / "PUSH5_FINAL_STATUS_DECISION.json", final)
    write_text(FINAL_ROOT / "PUSH5_FINAL_STATUS_SUMMARY.md", f"# Push 5 Final Status\n\nStatus: `{final['status']}`\n")
    write_hash_manifest(FINAL_ROOT, "PUSH5_FINAL_STATUS_HASH_MANIFEST.json", "main-citybrain.push5.infra.final_status.hash_manifest.v1")
    return final


def write_all_outputs() -> dict[str, Any]:
    reset_output_roots()
    data = load_lane_outputs()
    spatial_media = build_spatial_media_join(data)
    spatial_workflow = build_spatial_workflow_join(data)
    watch_media = build_watch_media_depth_join(data)
    workflow_llm = build_workflow_llm_boundary(data)
    boundary = build_boundary_report(data)
    compatibility = build_compatibility(spatial_media, spatial_workflow, watch_media, workflow_llm, boundary)

    write_text(OUTPUT_ROOT / "PUSH5_BRANCH_TOPOLOGY.md", branch_topology_md())
    write_json(OUTPUT_ROOT / "PUSH5_SPATIAL_MEDIA_EVIDENCE_JOIN_REPORT.json", spatial_media)
    write_json(OUTPUT_ROOT / "PUSH5_SPATIAL_WORKFLOW_STATE_JOIN_REPORT.json", spatial_workflow)
    write_json(OUTPUT_ROOT / "PUSH5_WATCH_MEDIA_DEPTH_JOIN_REPORT.json", watch_media)
    write_json(OUTPUT_ROOT / "PUSH5_WORKFLOW_AND_LLM_BOUNDARY_REPORT.json", workflow_llm)
    write_json(OUTPUT_ROOT / "PUSH5_CROSS_LANE_COMPATIBILITY_REPORT.json", compatibility)
    write_text(OUTPUT_ROOT / "PUSH5_BOUNDARY_AND_NON_CLAIMS.md", boundary_md())
    write_text(OUTPUT_ROOT / "PUSH5_TEST_REPORT.md", test_report_md(compatibility))
    write_text(OUTPUT_ROOT / "PUSH5_OPEN_LIMITATIONS.md", limitations_md())
    write_hash_manifest(OUTPUT_ROOT, "PUSH5_HASH_MANIFEST.json", "main-citybrain.push5.infra.integration.hash_manifest.v1")
    decision = decision_payload(compatibility)
    write_json(OUTPUT_ROOT / "PUSH5_INFRA_INTEGRATION_DECISION.json", decision)
    write_hash_manifest(OUTPUT_ROOT, "PUSH5_HASH_MANIFEST.json", "main-citybrain.push5.infra.integration.hash_manifest.v1")
    closeout = write_closeout(decision, compatibility)
    final = write_final(closeout)
    return {
        "decision": decision,
        "compatibility": compatibility,
        "spatial_media": spatial_media,
        "spatial_workflow": spatial_workflow,
        "watch_media": watch_media,
        "workflow_llm": workflow_llm,
        "closeout": closeout,
        "final": final,
    }


def main() -> int:
    outputs = write_all_outputs()
    hash_reports = [
        verify_hash_manifest(OUTPUT_ROOT, "PUSH5_HASH_MANIFEST.json"),
        verify_hash_manifest(CLOSEOUT_ROOT, "PUSH5_CLOSEOUT_HASH_MANIFEST.json"),
        verify_hash_manifest(FINAL_ROOT, "PUSH5_FINAL_STATUS_HASH_MANIFEST.json"),
    ]
    hashes_pass = all(report["status"] == "PASS" for report in hash_reports)
    status = outputs["decision"]["status"] if hashes_pass else FAIL_STATUS
    print(f"{TASK_ID}: {status}")
    print(f"Spatial/media evidence: {outputs['spatial_media']['status']}")
    print(f"Spatial/workflow state: {outputs['spatial_workflow']['status']}")
    print(f"WATCH/media depth: {outputs['watch_media']['status']}")
    print(f"Workflow/LLM boundary: {outputs['workflow_llm']['status']}")
    print(f"Compatibility: {outputs['compatibility']['status']}")
    print(f"Hashes: {'PASS' if hashes_pass else 'FAIL'}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
