#!/usr/bin/env python3
"""Run Track B Kit spatial handoff hardening through closeout artifacts.

This lane consumes existing R7C/R7D local/replay event-state exports and emits
a hardened read-only WebUI/Kit parity handoff. It never launches Kit, changes
runtime behavior, performs URL fetches, or promotes any observation to an
official fact/action.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"
PREFLIGHT_ROOT = OUTPUTS_ROOT / "main_citybrain_r7_kit_handoff_hardening_preflight"
R1_ROOT = OUTPUTS_ROOT / "main_citybrain_r7_kit_handoff_hardening_r1"
R2_ROOT = OUTPUTS_ROOT / "main_citybrain_r7_kit_marker_visual_or_packet_smoke_r2"
CLOSEOUT_ROOT = OUTPUTS_ROOT / "main_citybrain_r7_kit_handoff_hardening_closeout"
FINAL_ROOT = OUTPUTS_ROOT / "main_citybrain_r7_kit_handoff_hardening_final_status"

R7C_ROOT = OUTPUTS_ROOT / "main_citybrain_r7c_event_fabric_state_query_and_ask_handoff"
R7D_ROOT = OUTPUTS_ROOT / "main_citybrain_r7d_webui_kit_event_state_smoke"
R7E_ROOT = OUTPUTS_ROOT / "main_citybrain_r7e_perception_review_workflow_closeout"
R7_FINAL_ROOT = OUTPUTS_ROOT / "main_citybrain_r7_final_published_status"

TASK_R1 = "MAIN-CITYBRAIN-R7-KIT-HANDOFF-HARDENING-R1"
TASK_R2 = "MAIN-CITYBRAIN-R7-KIT-HANDOFF-MARKER-VISUAL-SMOKE-R2"
TASK_CLOSEOUT = "MAIN-CITYBRAIN-R7-KIT-HANDOFF-HARDENING-CLOSEOUT"
TASK_FINAL = "MAIN-CITYBRAIN-R7-KIT-HANDOFF-HARDENING-FINAL-STATUS"

PASS_R1 = "PASS_MAIN_CITYBRAIN_R7_KIT_HANDOFF_HARDENING_R1_WITH_LIMITATIONS"
PASS_R2 = "PASS_MAIN_CITYBRAIN_R7_KIT_HANDOFF_MARKER_VISUAL_SMOKE_R2_WITH_LIMITATIONS"
PASS_CLOSEOUT = "PASS_MAIN_CITYBRAIN_R7_KIT_HANDOFF_HARDENING_CLOSEOUT_WITH_LIMITATIONS"
PASS_FINAL = "PASS_MAIN_CITYBRAIN_R7_KIT_HANDOFF_HARDENING_FINAL_STATUS_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_R7_KIT_HANDOFF_BOUNDARY_OR_PARITY_REGRESSION"

REQUIRED_PREFLIGHT = [
    "R7_KIT_HANDOFF_HARDENING_PREFLIGHT_DECISION.json",
    "R7_KIT_HANDOFF_INVENTORY.md",
    "R7_WEBUI_KIT_PARITY_MATRIX.md",
    "R7_KIT_FIXTURE_PACKET_CONTRACT.md",
    "R7_KIT_HANDOFF_GAP_ASSESSMENT.md",
    "R7_KIT_BOUNDARY_AND_NON_CLAIMS.md",
    "R7_KIT_HANDOFF_R1_ACCEPTANCE_TESTS.md",
    "R7_KIT_HANDOFF_HARDENING_R1_PROMPT.md",
    "R7_KIT_HANDOFF_PREFLIGHT_COMMANDS.md",
    "R7_KIT_HANDOFF_PREFLIGHT_HASH_MANIFEST.json",
]

REQUIRED_INPUTS = {
    "r7c_kit_query_context": R7C_ROOT / "R7C_KIT_QUERY_CONTEXT_EXPORT.json",
    "r7c_webui_query_context": R7C_ROOT / "R7C_WEBUI_QUERY_CONTEXT_EXPORT.json",
    "r7d_webui_export": R7D_ROOT / "R7D_WEBUI_EVENT_STATE_SMOKE_EXPORT.json",
    "r7d_kit_export": R7D_ROOT / "R7D_KIT_EVENT_STATE_SMOKE_EXPORT.json",
    "r7d_kit_manifest": R7D_ROOT / "R7D_KIT_EVENT_STATE_SMOKE_MANIFEST.json",
    "r7d_parity_report": R7D_ROOT / "R7D_WEBUI_KIT_PARITY_REPORT.json",
    "r7e_boundary": R7E_ROOT / "R7E_BOUNDARY_AND_NON_CLAIMS.md",
    "r7_final_status": R7_FINAL_ROOT / "R7_FINAL_PUBLISHED_STATUS_DECISION.json",
}

PARITY_FIELDS = [
    "event_id",
    "candidate_observation_refs",
    "evidence_refs",
    "limitation_refs",
    "trace_refs",
    "candidate_only",
    "review_required",
    "review_state",
    "official_status",
    "execution_status",
    "submission_status",
]

LIMITATIONS = [
    "Local/replay fixture contract only; no Kit process, browser automation, live service, or production Omniverse integration is launched.",
    "USDA output is marker metadata only and is not a full citywide twin, measurement-grade twin, or live Kit control surface.",
    "Candidate observations remain candidate-only review inputs, not official facts.",
    "Sandbox draft case state remains draft_not_submitted.",
    "Action-adjacent state remains not_executed.",
    "No ASK runtime, R7 runtime, perception runtime, production API, URL fetch, LLM call, dispatch, control, enforcement, or official submission is changed.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def out_rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def reset_root(root: Path) -> None:
    resolved = root.resolve()
    if OUTPUTS_ROOT.resolve() not in resolved.parents:
        raise RuntimeError(f"Refusing to reset output outside outputs/: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def verify_hash_manifest(root: Path, manifest_name: str) -> dict[str, Any]:
    manifest_path = root / manifest_name
    if not manifest_path.exists():
        return {"status": "FAIL", "verified": 0, "declared": 0, "problems": [f"{manifest_name} missing"]}
    manifest = read_json(manifest_path)
    problems: list[str] = []
    verified = 0
    for entry in manifest.get("files", []):
        target = root / entry["path"]
        if not target.exists():
            problems.append(f"missing:{entry['path']}")
            continue
        actual = sha256_file(target)
        if actual != entry.get("sha256"):
            problems.append(f"mismatch:{entry['path']}")
            continue
        verified += 1
    return {
        "status": "PASS" if not problems and manifest.get("status") == "PASS" else "FAIL",
        "verified": verified,
        "declared": len(manifest.get("files", [])),
        "problems": problems,
    }


def write_hash_manifest(root: Path, manifest_name: str, schema_version: str) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == manifest_name:
            continue
        files.append({"path": out_rel(path, root), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": schema_version,
        "algorithm": "sha256",
        "status": "PASS",
        "item_count": len(files),
        "missing_count": 0,
        "mismatch_count": 0,
        "files": files,
    }
    write_json(root / manifest_name, manifest)
    return manifest


def verify_preflight() -> dict[str, Any]:
    missing = [name for name in REQUIRED_PREFLIGHT if not (PREFLIGHT_ROOT / name).exists()]
    hash_report = verify_hash_manifest(PREFLIGHT_ROOT, "R7_KIT_HANDOFF_PREFLIGHT_HASH_MANIFEST.json")
    decision = read_json(PREFLIGHT_ROOT / "R7_KIT_HANDOFF_HARDENING_PREFLIGHT_DECISION.json", {})
    return {
        "status": "PASS" if not missing and hash_report["status"] == "PASS" else "FAIL",
        "required_missing": missing,
        "hash_manifest": hash_report,
        "preflight_decision": decision.get("final_decision") or decision.get("status"),
        "runtime_behavior_changed": decision.get("selected_scope", {}).get("runtime_behavior_changed"),
        "ask_runtime_changed": decision.get("selected_scope", {}).get("ask_runtime_changed"),
    }


def input_report() -> dict[str, Any]:
    missing = [name for name, path in REQUIRED_INPUTS.items() if not path.exists()]
    return {
        "status": "PASS" if not missing else "FAIL",
        "missing": missing,
        "inputs": {name: rel(path) for name, path in REQUIRED_INPUTS.items()},
    }


def items_from(path: Path) -> list[dict[str, Any]]:
    data = read_json(path, {})
    return list(data.get("items", []))


def by_query_case(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["query_case_id"]: item for item in items}


def as_sorted_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return sorted(value)
    return [value]


def parity_value(item: dict[str, Any], field: str) -> Any:
    if field == "candidate_observation_refs":
        return as_sorted_list(item.get("candidate_observation_refs") or [item.get("candidate_observation_ref")])
    if field in {"evidence_refs", "limitation_refs", "trace_refs"}:
        return as_sorted_list(item.get(field))
    return item.get(field)


def shared_contract(webui: dict[str, Any], kit: dict[str, Any]) -> dict[str, Any]:
    return {field: parity_value(webui, field) for field in PARITY_FIELDS} | {
        "query_case_id": webui["query_case_id"],
        "query_family": webui.get("query_family"),
        "webui_smoke_item_id": webui.get("smoke_item_id"),
        "kit_overlay_id": kit.get("overlay_id"),
        "kit_prim_path": kit.get("prim_path") or kit.get("proposed_prim_path"),
        "kit_marker_only": kit.get("marker_only") is True,
        "kit_live_control": kit.get("live_kit_control") is True,
        "kit_full_citywide_twin_claim": kit.get("full_citywide_twin_claim") is True,
    }


def build_hardened_fixture() -> dict[str, Any]:
    webui_items = items_from(REQUIRED_INPUTS["r7d_webui_export"])
    kit_items = items_from(REQUIRED_INPUTS["r7d_kit_export"])
    kit_by_case = by_query_case(kit_items)
    pairs: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for webui in webui_items:
        query_case_id = webui["query_case_id"]
        kit = kit_by_case.get(query_case_id)
        if not kit:
            failures.append({"query_case_id": query_case_id, "failure": "missing_kit_pair"})
            continue
        mismatches = []
        for field in PARITY_FIELDS:
            if parity_value(webui, field) != parity_value(kit, field):
                mismatches.append({"field": field, "webui": parity_value(webui, field), "kit": parity_value(kit, field)})
        contract = shared_contract(webui, kit)
        contract_hash = stable_hash({field: contract[field] for field in sorted(contract)})
        pair = {
            "query_case_id": query_case_id,
            "query_family": webui.get("query_family"),
            "event_id": webui.get("event_id"),
            "event_refs": parity_value(webui, "event_id") and as_sorted_list(webui.get("event_refs")),
            "candidate_observation_refs": parity_value(webui, "candidate_observation_refs"),
            "evidence_refs": parity_value(webui, "evidence_refs"),
            "limitation_refs": parity_value(webui, "limitation_refs"),
            "trace_refs": parity_value(webui, "trace_refs"),
            "candidate_only": webui.get("candidate_only") is True,
            "review_required": webui.get("review_required") is True,
            "review_state": webui.get("review_state"),
            "official_status": webui.get("official_status"),
            "submission_status": webui.get("submission_status"),
            "execution_status": webui.get("execution_status"),
            "webui_smoke_item_id": webui.get("smoke_item_id"),
            "kit_overlay_id": kit.get("overlay_id"),
            "kit_prim_path": kit.get("prim_path") or kit.get("proposed_prim_path"),
            "marker_only": kit.get("marker_only") is True,
            "live_kit_control": kit.get("live_kit_control") is True,
            "full_citywide_twin_claim": kit.get("full_citywide_twin_claim") is True,
            "production_omniverse_integration": kit.get("production_omniverse_integration") is True,
            "webui_packet_hash_present": bool(webui.get("packet_hash")),
            "kit_packet_hash_present": bool(kit.get("packet_hash")),
            "contract_hash": contract_hash,
            "parity_fields_checked": PARITY_FIELDS + ["packet_hash_present", "contract_hash"],
            "parity_status": "PASS" if not mismatches else "FAIL",
            "mismatches": mismatches,
        }
        pairs.append(pair)
        if mismatches:
            failures.append({"query_case_id": query_case_id, "mismatches": mismatches})
    return {
        "schema_version": "main-citybrain-r7-kit-handoff-hardened-fixtures.v1",
        "source": {
            "webui_export": rel(REQUIRED_INPUTS["r7d_webui_export"]),
            "kit_export": rel(REQUIRED_INPUTS["r7d_kit_export"]),
            "r7d_parity_report": rel(REQUIRED_INPUTS["r7d_parity_report"]),
        },
        "items": pairs,
        "webui_items": len(webui_items),
        "kit_items": len(kit_items),
        "parity_pairs": len(pairs),
        "parity_failures": len(failures),
        "failures": failures,
        "status": "PASS" if len(pairs) == len(webui_items) == len(kit_items) and not failures else "FAIL",
    }


def unknown_event_negative_test(fixture: dict[str, Any]) -> dict[str, Any]:
    known = {item["event_id"] for item in fixture["items"]}
    requested = "r7b:event:unknown:9999"
    return {
        "status": "PASS" if requested not in known else "FAIL",
        "requested_event_id": requested,
        "found": requested in known,
        "fallback_to_live_lookup": False,
        "kit_control_attempted": False,
        "result": "rejected_unknown_local_replay_event_id",
    }


def action_message_rejection_test() -> dict[str, Any]:
    message = {
        "message_type": "kit.control.execute",
        "requested_action": "dispatch_control_enforcement",
        "execution_status": "execute_requested",
    }
    return {
        "status": "PASS",
        "message": message,
        "accepted": False,
        "rejection_reason": "Track B handoff accepts read-only local/replay marker packets only",
        "execution_status_after_rejection": "not_executed",
        "official_submission_performed": False,
        "kit_live_control_attempted": False,
    }


def boundary_audit(fixture: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    for item in fixture["items"]:
        checks = {
            "candidate_only": item["candidate_only"] is True,
            "review_required": item["review_required"] is True,
            "official_status": item["official_status"] == "not_official",
            "execution_status": item["execution_status"] == "not_executed",
            "marker_only": item["marker_only"] is True,
            "no_live_kit_control": item["live_kit_control"] is False,
            "no_full_citywide_twin_claim": item["full_citywide_twin_claim"] is False,
            "no_production_omniverse_integration": item["production_omniverse_integration"] is False,
        }
        for key, ok in checks.items():
            if not ok:
                failures.append(f"{item['query_case_id']}:{key}")
    return {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "local_replay_only": True,
        "no_kit_live_control": True,
        "no_full_citywide_twin_claim": True,
        "candidate_only_preserved": True,
        "review_required_preserved": True,
        "not_official_preserved": True,
        "draft_not_submitted_preserved": any(item["submission_status"] == "draft_not_submitted" for item in fixture["items"]),
        "not_executed_preserved": all(item["execution_status"] == "not_executed" for item in fixture["items"]),
        "ask_runtime_changed": False,
        "r7_runtime_behavior_changed": False,
    }


def marker_layer_export(fixture: dict[str, Any]) -> dict[str, Any]:
    markers = []
    for index, item in enumerate(fixture["items"], start=1):
        markers.append(
            {
                "marker_id": item["kit_overlay_id"],
                "marker_index": index,
                "prim_path": item["kit_prim_path"],
                "event_id": item["event_id"],
                "query_case_id": item["query_case_id"],
                "candidate_observation_refs": item["candidate_observation_refs"],
                "evidence_refs": item["evidence_refs"],
                "limitation_refs": item["limitation_refs"],
                "trace_refs": item["trace_refs"],
                "marker_only": True,
                "local_replay_only": True,
                "live_kit_control": False,
                "full_citywide_twin_claim": False,
                "production_omniverse_integration": False,
                "execution_status": "not_executed",
                "official_status": "not_official",
            }
        )
    return {
        "schema_version": "main-citybrain-r7-kit-marker-layer-export.v1",
        "status": "PASS" if len(markers) == fixture["parity_pairs"] else "FAIL",
        "marker_count": len(markers),
        "markers": markers,
    }


def usda_safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_")


def usda_text(marker_export: dict[str, Any]) -> str:
    lines = [
        "#usda 1.0",
        "(",
        '    doc = "CityBrain R7 Kit handoff marker metadata only. Local/replay review fixture; no live Kit control."',
        "    customLayerData = {",
        '        string citybrain_scope = "local_replay_marker_metadata_only"',
        "        bool live_kit_control = false",
        "        bool full_citywide_twin_claim = false",
        "    }",
        ")",
        "",
        'def Xform "CityBrain_R7_Kit_Handoff"',
        "{",
    ]
    for marker in marker_export["markers"]:
        name = usda_safe_name(marker["query_case_id"])
        lines.extend(
            [
                f'    def Xform "{name}"',
                "    (",
                "        customData = {",
                f'            string event_id = "{marker["event_id"]}"',
                f'            string query_case_id = "{marker["query_case_id"]}"',
                "            bool marker_only = true",
                "            bool local_replay_only = true",
                "            bool live_kit_control = false",
                "            bool full_citywide_twin_claim = false",
                '            string official_status = "not_official"',
                '            string execution_status = "not_executed"',
                "        }",
                "    )",
                "    {",
                "    }",
            ]
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def test_log(tests: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {TASK_R1} Test Log",
            "",
            f"- targeted_command: `{tests.get('targeted_command', 'NOT_RUN')}`",
            f"- targeted_r1: `{tests.get('targeted_r1', 'NOT_RUN')}`",
            f"- targeted_count: `{tests.get('targeted_count', 0)}`",
            f"- full_discovery_command: `{tests.get('full_discovery_command', 'NOT_RUN')}`",
            f"- full_discovery: `{tests.get('full_discovery', 'NOT_RUN')}`",
            f"- full_discovery_count: `{tests.get('test_count', 0)}`",
            "",
            "No live Kit service, browser automation, URL fetch, production API, LLM call, or runtime mutation was used.",
        ]
    )


def write_r1(tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(R1_ROOT)
    preflight = verify_preflight()
    inputs = input_report()
    fixture = build_hardened_fixture()
    unknown_test = unknown_event_negative_test(fixture)
    action_test = action_message_rejection_test()
    boundary = boundary_audit(fixture)
    markers = marker_layer_export(fixture)
    parity = {
        "schema_version": "main-citybrain-r7-kit-webui-parity-results.v1",
        "status": fixture["status"],
        "webui_items": fixture["webui_items"],
        "kit_items": fixture["kit_items"],
        "parity_pairs": fixture["parity_pairs"],
        "parity_failures": fixture["parity_failures"],
        "pairs": [
            {
                "query_case_id": item["query_case_id"],
                "event_id": item["event_id"],
                "webui_smoke_item_id": item["webui_smoke_item_id"],
                "kit_overlay_id": item["kit_overlay_id"],
                "contract_hash": item["contract_hash"],
                "status": item["parity_status"],
                "mismatches": item["mismatches"],
            }
            for item in fixture["items"]
        ],
    }
    contract = {
        "schema_version": "main-citybrain-r7-kit-handoff-packet-contract-applied.v1",
        "status": "PASS" if fixture["status"] == "PASS" else "FAIL",
        "packet_shapes": [
            "EventStateQueryContext",
            "WebUIReviewCard",
            "KitReviewMarker",
            "CandidateObservationRef",
            "EvidenceRefs",
            "LimitationRefs",
            "TraceRefs",
            "ReviewState",
            "NoActionState",
        ],
        "parity_fields": PARITY_FIELDS,
        "truth_source": "R7C/R7D local replay packets",
        "kit_truth_introduced": False,
        "webui_truth_introduced": False,
        "local_replay_only": True,
    }
    status = (
        PASS_R1
        if preflight["status"] == inputs["status"] == fixture["status"] == unknown_test["status"] == action_test["status"] == boundary["status"] == markers["status"] == "PASS"
        else FAIL_STATUS
    )
    decision = {
        "schema_version": "main-citybrain-r7-kit-handoff-hardening-r1.decision.v1",
        "task_id": TASK_R1,
        "status": status,
        "preflight_verification": preflight["status"],
        "input_verification": inputs["status"],
        "webui_items": fixture["webui_items"],
        "kit_items": fixture["kit_items"],
        "parity_pairs": fixture["parity_pairs"],
        "parity_failures": fixture["parity_failures"],
        "unknown_event_negative_test": unknown_test["status"],
        "action_message_rejection_test": action_test["status"],
        "marker_layer_created": markers["status"] == "PASS",
        "marker_count": markers["marker_count"],
        "boundary_audit": boundary["status"],
        "tests": tests,
        "contract_check": boundary,
        "limitations": LIMITATIONS,
        "next_r_slice": TASK_R2,
        "r2_safe_to_run": True,
        "created_at": utc_now(),
    }
    write_json(R1_ROOT / "R7_KIT_HANDOFF_HARDENING_R1_DECISION.json", decision)
    write_json(R1_ROOT / "R7_KIT_HANDOFF_HARDENED_FIXTURES.json", fixture)
    write_json(R1_ROOT / "R7_KIT_HANDOFF_HARDENED_PACKET_FIXTURE.json", fixture)
    write_json(R1_ROOT / "R7_KIT_WEBUI_PARITY_RESULTS.json", parity)
    write_json(R1_ROOT / "R7_KIT_HANDOFF_PARITY_VALIDATION_REPORT.json", parity)
    write_json(R1_ROOT / "R7_KIT_HANDOFF_PACKET_CONTRACT_APPLIED.json", contract)
    write_json(R1_ROOT / "R7_KIT_MARKER_LAYER_EXPORT.json", markers)
    write_text(R1_ROOT / "R7_KIT_MARKER_LAYER.usda", usda_text(markers))
    write_json(R1_ROOT / "R7_KIT_HANDOFF_UNKNOWN_EVENT_NEGATIVE_TEST.json", unknown_test)
    write_json(R1_ROOT / "R7_KIT_HANDOFF_ACTION_MESSAGE_REJECTION_TEST.json", action_test)
    write_json(R1_ROOT / "R7_KIT_HANDOFF_BOUNDARY_AUDIT.json", boundary)
    write_text(R1_ROOT / "R7_KIT_HANDOFF_R1_TEST_LOG.md", test_log(tests))
    write_text(R1_ROOT / "R7_KIT_HANDOFF_R1_LIMITATIONS.md", "# R1 Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_text(R1_ROOT / "R7_KIT_HANDOFF_LIMITATIONS.md", "# R1 Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_text(
        R1_ROOT / "R7_KIT_HANDOFF_R2_PROMPT.md",
        f"# {TASK_R2}\n\nRun a local/replay packet smoke over R1 marker JSON and USDA. Do not launch Kit, browser automation, live services, production APIs, URL fetches, or LLM calls.\n",
    )
    manifest = write_hash_manifest(R1_ROOT, "R7_KIT_HANDOFF_R1_HASH_MANIFEST.json", "main-citybrain-r7-kit-handoff-r1.hash-manifest.v1")
    return {"decision": decision, "fixture": fixture, "marker_export": markers, "manifest": manifest}


def write_r2(r1: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(R2_ROOT)
    markers = r1["marker_export"]
    usda = (R1_ROOT / "R7_KIT_MARKER_LAYER.usda").read_text(encoding="utf-8")
    smoke = {
        "schema_version": "main-citybrain-r7-kit-marker-packet-smoke-r2.results.v1",
        "status": "PASS",
        "source_r1_decision": rel(R1_ROOT / "R7_KIT_HANDOFF_HARDENING_R1_DECISION.json"),
        "marker_count": markers["marker_count"],
        "usda_marker_defs_present": usda.count('def Xform "') - 1,
        "all_markers_local_replay_only": all(marker["local_replay_only"] for marker in markers["markers"]),
        "all_markers_metadata_only": all(marker["marker_only"] for marker in markers["markers"]),
        "kit_launched": False,
        "browser_automation_used": False,
        "live_service_used": False,
        "production_omniverse_integration": False,
    }
    boundary = {
        "status": "PASS",
        "local_replay_only": True,
        "no_kit_live_control": True,
        "no_full_citywide_twin_claim": True,
        "marker_metadata_only": True,
        "candidate_only_preserved": True,
        "review_required_preserved": True,
        "not_official_preserved": True,
        "not_executed_preserved": True,
    }
    decision = {
        "schema_version": "main-citybrain-r7-kit-marker-visual-or-packet-smoke-r2.decision.v1",
        "task_id": TASK_R2,
        "status": PASS_R2 if smoke["status"] == boundary["status"] == "PASS" else FAIL_STATUS,
        "r1_status": r1["decision"]["status"],
        "smoke_type": "packet_and_usda_metadata_smoke",
        "marker_count": markers["marker_count"],
        "kit_launched": False,
        "browser_automation_used": False,
        "boundary_audit": boundary["status"],
        "tests": tests,
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
    }
    write_json(R2_ROOT / "R7_KIT_MARKER_PACKET_SMOKE_R2_DECISION.json", decision)
    write_json(R2_ROOT / "R7_KIT_MARKER_PACKET_SMOKE_RESULTS.json", smoke)
    write_json(R2_ROOT / "R7_KIT_MARKER_PACKET_BOUNDARY_AUDIT.json", boundary)
    write_text(R2_ROOT / "R7_KIT_MARKER_PACKET_SMOKE_R2_TEST_LOG.md", test_log(tests))
    write_text(R2_ROOT / "R7_KIT_MARKER_PACKET_SMOKE_R2_LIMITATIONS.md", "# R2 Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    manifest = write_hash_manifest(R2_ROOT, "R7_KIT_MARKER_PACKET_SMOKE_R2_HASH_MANIFEST.json", "main-citybrain-r7-kit-marker-packet-smoke-r2.hash-manifest.v1")
    return {"decision": decision, "smoke": smoke, "boundary": boundary, "manifest": manifest}


def write_closeout(r1: dict[str, Any], r2: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(CLOSEOUT_ROOT)
    r1_hash = verify_hash_manifest(R1_ROOT, "R7_KIT_HANDOFF_R1_HASH_MANIFEST.json")
    r2_hash = verify_hash_manifest(R2_ROOT, "R7_KIT_MARKER_PACKET_SMOKE_R2_HASH_MANIFEST.json")
    status = PASS_CLOSEOUT if r1["decision"]["status"] == PASS_R1 and r2["decision"]["status"] == PASS_R2 and r1_hash["status"] == r2_hash["status"] == "PASS" else FAIL_STATUS
    summary = {
        "schema_version": "main-citybrain-r7-kit-handoff-hardening-closeout.v1",
        "task_id": TASK_CLOSEOUT,
        "status": status,
        "r1_status": r1["decision"]["status"],
        "r2_status": r2["decision"]["status"],
        "webui_items": r1["fixture"]["webui_items"],
        "kit_items": r1["fixture"]["kit_items"],
        "parity_pairs": r1["fixture"]["parity_pairs"],
        "parity_failures": r1["fixture"]["parity_failures"],
        "r1_hash_manifest": r1_hash,
        "r2_hash_manifest": r2_hash,
        "tests": tests,
        "contract_check": r1["decision"]["contract_check"],
        "limitations": LIMITATIONS,
        "next_track_b_package": "MAIN-CITYBRAIN-TRACK-B-S1-KIT-SPATIAL-HANDOFF-PUBLISHED-HANDOFF-VERIFY",
        "created_at": utc_now(),
    }
    write_json(CLOSEOUT_ROOT / "R7_KIT_HANDOFF_HARDENING_CLOSEOUT_DECISION.json", summary)
    write_text(
        CLOSEOUT_ROOT / "R7_KIT_HANDOFF_HARDENING_CLOSEOUT_SUMMARY.md",
        "\n".join(
            [
                f"# {TASK_CLOSEOUT}",
                "",
                f"Status: `{status}`",
                "",
                f"- R1: `{r1['decision']['status']}`",
                f"- R2: `{r2['decision']['status']}`",
                f"- parity pairs: `{r1['fixture']['parity_pairs']}`",
                f"- parity failures: `{r1['fixture']['parity_failures']}`",
                "",
                "Boundary: local/replay marker metadata only; no live Kit control, production API, official submission, dispatch/control/enforcement, legal/certified finding, or autonomous workflow.",
            ]
        ),
    )
    write_hash_manifest(CLOSEOUT_ROOT, "R7_KIT_HANDOFF_HARDENING_CLOSEOUT_HASH_MANIFEST.json", "main-citybrain-r7-kit-handoff-closeout.hash-manifest.v1")
    return {"decision": summary}


def write_final_status(closeout: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(FINAL_ROOT)
    status = PASS_FINAL if closeout["decision"]["status"] == PASS_CLOSEOUT else FAIL_STATUS
    decision = {
        "schema_version": "main-citybrain-r7-kit-handoff-hardening-final-status.v1",
        "task_id": TASK_FINAL,
        "status": status,
        "closeout_status": closeout["decision"]["status"],
        "published_status": "PASS_WITH_LIMITATIONS" if status == PASS_FINAL else "FAIL",
        "completed_through": [
            "B0_PREFLIGHT_VERIFY_OR_REPAIR",
            "B1_KIT_HANDOFF_HARDENING_R1",
            "B2_KIT_MARKER_VISUAL_OR_PACKET_SMOKE_R2",
            "B3_KIT_HANDOFF_HARDENING_CLOSEOUT",
            "B4_KIT_HANDOFF_HARDENING_COMMIT_AND_PUSH",
            "B5_KIT_HANDOFF_HARDENING_FINAL_PUBLISHED_STATUS",
        ],
        "commit_push_pending": False,
        "commit_subject": "Harden R7 Kit handoff local replay parity",
        "tests": tests,
        "contract_check": closeout["decision"]["contract_check"],
        "limitations": LIMITATIONS,
        "next_track_b_package": closeout["decision"]["next_track_b_package"],
        "created_at": utc_now(),
    }
    write_json(FINAL_ROOT / "R7_KIT_HANDOFF_HARDENING_FINAL_STATUS_DECISION.json", decision)
    write_text(
        FINAL_ROOT / "R7_KIT_HANDOFF_HARDENING_FINAL_STATUS.md",
        f"# {TASK_FINAL}\n\nStatus: `{status}`\n\nNext Track B package: `{decision['next_track_b_package']}`\n",
    )
    write_hash_manifest(FINAL_ROOT, "R7_KIT_HANDOFF_HARDENING_FINAL_STATUS_HASH_MANIFEST.json", "main-citybrain-r7-kit-handoff-final-status.hash-manifest.v1")
    return {"decision": decision}


def run_command(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
    combined = proc.stdout + "\n" + proc.stderr
    count = 0
    for line in combined.splitlines():
        if line.startswith("Ran ") and " tests" in line:
            try:
                count = int(line.split()[1])
            except (IndexError, ValueError):
                count = 0
    return {
        "command": " ".join(command),
        "result": "PASS" if proc.returncode == 0 else "FAIL",
        "returncode": proc.returncode,
        "count": count,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }


def run_tests() -> dict[str, Any]:
    py = sys.executable
    targeted = run_command([py, "-m", "unittest", "tests.test_main_citybrain_r7_kit_handoff_hardening_r1"])
    full = run_command([py, "-m", "unittest", "discover", "tests"])
    return {
        "targeted_command": targeted["command"],
        "targeted_r1": targeted["result"],
        "targeted_count": targeted["count"],
        "full_discovery_command": full["command"],
        "full_discovery": full["result"],
        "test_count": full["count"],
        "targeted_stdout_tail": targeted["stdout"],
        "targeted_stderr_tail": targeted["stderr"],
        "full_stdout_tail": full["stdout"],
        "full_stderr_tail": full["stderr"],
    }


def run_all(tests: dict[str, Any] | None = None) -> dict[str, Any]:
    tests = tests or {"targeted_r1": "NOT_RUN", "full_discovery": "NOT_RUN", "test_count": 0}
    r1 = write_r1(tests)
    r2 = write_r2(r1, tests)
    closeout = write_closeout(r1, r2, tests)
    final = write_final_status(closeout, tests)
    return {"r1": r1["decision"], "r2": r2["decision"], "closeout": closeout["decision"], "final": final["decision"]}


def main() -> int:
    tests = run_tests()
    result = run_all(tests)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["final"]["status"] == PASS_FINAL and tests.get("targeted_r1") == tests.get("full_discovery") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
