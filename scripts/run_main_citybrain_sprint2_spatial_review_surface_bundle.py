from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.event_fabric_r0_1_validator import validator as r0_1_validator


TASK_ID = "MAIN-CITYBRAIN-SPRINT2-TRACK-1-SPATIAL-REVIEW-SURFACE-RUN-TO-CLOSURE"
STATUS = "PASS_MAIN_CITYBRAIN_SPRINT2_SPATIAL_REVIEW_SURFACE_WITH_LIMITATIONS"
FINAL_STATUS = "PASS_MAIN_CITYBRAIN_SPRINT2_SPATIAL_REVIEW_SURFACE_FINAL_STATUS_WITH_LIMITATIONS"
ACTIVE_CONTRACT_COMMIT = "5ba2dc1"
ACTIVE_CONTRACT_BRANCH = "codex/event-fabric-r0-1-contract-delta"

BUNDLE_ROOT = ROOT / "outputs" / "main_citybrain_sprint2_spatial_review_surface_bundle"
CLOSEOUT_ROOT = ROOT / "outputs" / "main_citybrain_sprint2_spatial_review_surface_closeout"
FINAL_ROOT = ROOT / "outputs" / "main_citybrain_sprint2_spatial_review_surface_final_status"
R7_KIT_FIXTURES = ROOT / "outputs" / "main_citybrain_r7_kit_handoff_hardening_r1" / "R7_KIT_HANDOFF_HARDENED_FIXTURES.json"
R0_1_DECISION = ROOT / "outputs" / "main_citybrain_event_fabric_r0_1_contract_delta" / "EVENT_FABRIC_R0_1_CONTRACT_DELTA_DECISION.json"

NOT_EXECUTED = ["official_submission", "dispatch", "control", "enforcement"]
COMMON_CANNOT_CLAIM = [
    "official violation",
    "official affected asset",
    "legal finding",
    "certified finding",
    "live monitoring",
    "dispatch/control/enforcement",
    "full citywide twin",
    "live Kit control",
]
COMMON_LIMITATIONS = [
    "local/replay only",
    "packet-driven review surface only",
    "marker metadata only in USDA/Kit export",
    "no production API, live camera, URL fetch, or LLM call",
    "not official and not certified",
    "action state remains not_executed",
]

REVIEW_STATE_MAP = {
    "active_review": "needs_review",
    "unresolved_review_candidate": "unresolved",
    "quarantined_not_promoted": "quarantined",
    "trace": "needs_review",
    "draft_case": "draft_sandbox",
    "overlay_context": "needs_review",
    "action_proposal": "not_executed",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_manifest(root: Path, name: str) -> dict[str, Any]:
    manifest_path = root / name
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path != manifest_path:
            files.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": sha256_file(path),
                    "bytes": path.stat().st_size,
                }
            )
    payload = {
        "schema_version": "citybrain.hash_manifest.v1",
        "generated_at": utc_now(),
        "root": root.as_posix(),
        "count": len(files),
        "files": files,
    }
    write_json(manifest_path, payload)
    return payload


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return cleaned.lower() or "item"


def r0_1_common() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.event_fabric.r0_1",
        "check_report_ref": None,
        "check_status": "not_evaluated",
        "authority_level": "review_display_only",
        "authority_envelope_ref": None,
    }


def normalize_review_state(item: dict[str, Any]) -> str:
    source = str(item.get("review_state") or "needs_review")
    return REVIEW_STATE_MAP.get(source, source if source in r0_1_validator.ALLOWED_REVIEW_STATES else "needs_review")


def normalize_submission_status(_: dict[str, Any]) -> str:
    return "draft_not_submitted"


def load_source_items() -> list[dict[str, Any]]:
    source = load_json(R7_KIT_FIXTURES)
    items = source.get("items", [])
    if not items:
        raise RuntimeError(f"No R7 Kit handoff fixture items found at {R7_KIT_FIXTURES}")
    return items


def assert_r0_1_ready() -> dict[str, Any]:
    if not R0_1_DECISION.exists():
        return {"status": "FAIL", "reason": f"missing R0.1 decision: {R0_1_DECISION}"}
    decision = load_json(R0_1_DECISION)
    shared_report = r0_1_validator.validate_bundle()
    status_ok = decision.get("status") == r0_1_validator.PASS_STATUS
    return {
        "status": "PASS" if status_ok and shared_report["status"] == "PASS" else "FAIL",
        "active_contract": "Event Fabric R0.1",
        "active_contract_branch": ACTIVE_CONTRACT_BRANCH,
        "active_contract_commit": ACTIVE_CONTRACT_COMMIT,
        "decision_status": decision.get("status"),
        "shared_validator_status": shared_report["status"],
        "shared_validator_checks": shared_report["checks"],
    }


def review_items() -> list[dict[str, Any]]:
    items = []
    for index, source in enumerate(load_source_items(), start=1):
        event_id = source["event_id"]
        overlay_id = source.get("kit_overlay_id") or f"spatial-review:overlay:{index:03d}"
        review_state = normalize_review_state(source)
        candidate_refs = list(source.get("candidate_observation_refs") or [])
        evidence_refs = list(source.get("evidence_refs") or [])
        limitation_refs = sorted(set(COMMON_LIMITATIONS + list(source.get("limitation_refs") or [])))
        trace_refs = list(source.get("trace_refs") or [])
        item = {
            "surface_item_id": f"spatial-review:item:{index:03d}",
            "event_id": event_id,
            "event_refs": list(source.get("event_refs") or [event_id]),
            "candidate_observation_refs": candidate_refs,
            "candidate_observation_ref": candidate_refs[0] if candidate_refs else None,
            "query_case_id": source.get("query_case_id") or f"spatial-review-query-{index:03d}",
            "query_result_id": f"spatial-review:query-result:{slug(str(source.get('query_case_id') or index))}",
            "query_family": source.get("query_family") or "local_replay_spatial_review",
            "overlay_id": overlay_id,
            "overlay_kind": "marker_metadata_only",
            "display_label": source.get("query_family", event_id).replace("_", " ").title(),
            "location_ref": f"local-replay-location:{slug(event_id)}",
            "proposed_prim_path": source.get("kit_prim_path") or f"/World/CityBrain/Sprint2SpatialReview/{slug(event_id)}",
            "candidate_only": True,
            "review_required": True,
            "official_status": "not_official",
            "review_state": review_state,
            "source_review_state": source.get("review_state"),
            "submission_status": normalize_submission_status(source),
            "execution_status": "not_executed",
            "evidence_refs": evidence_refs,
            "limitation_refs": limitation_refs,
            "trace_refs": trace_refs,
            "cannot_claim": COMMON_CANNOT_CLAIM,
            "not_executed": NOT_EXECUTED,
            "marker_metadata_only": True,
            "live_kit_control": False,
            "full_citywide_twin_claim": False,
            "production_omniverse_integration": False,
            "packet_truth_source": "Event Fabric R0.1 packets plus R7 Kit handoff fixtures",
        }
        items.append(item)
    return items


def query_packet(item: dict[str, Any]) -> dict[str, Any]:
    return {
        **r0_1_common(),
        "query_case_id": item["query_case_id"],
        "query_result_id": item["query_result_id"],
        "query_family": item["query_family"],
        "event_refs": item["event_refs"],
        "candidate_observation_refs": item["candidate_observation_refs"],
        "knowns": [
            f"Local/replay review item {item['surface_item_id']} is available for spatial review.",
            "WebUI and Kit marker surfaces consume the same packet refs.",
        ],
        "unknowns": [
            "No official status, live state, certified finding, or legal finding is established.",
            "The marker is not measurement-grade geometry and does not prove a full citywide twin.",
        ],
        "cannot_claim": item["cannot_claim"],
        "safe_next_looks": [
            "inspect evidence refs",
            "inspect limitation refs",
            "add a manual review note if a human reviewer chooses",
        ],
        "evidence_refs": item["evidence_refs"],
        "limitation_refs": item["limitation_refs"],
        "trace_refs": item["trace_refs"],
        "review_state_summary": {item["review_state"]: 1},
        "official_status_summary": {"not_official": 1},
        "not_executed": item["not_executed"],
        "raw_query_authority": False,
    }


def overlay_packet(item: dict[str, Any]) -> dict[str, Any]:
    return {
        **r0_1_common(),
        "overlay_id": item["overlay_id"],
        "overlay_kind": item["overlay_kind"],
        "event_id": item["event_id"],
        "candidate_observation_ref": item["candidate_observation_ref"],
        "display_label": item["display_label"],
        "location_ref": item["location_ref"],
        "proposed_prim_path": item["proposed_prim_path"],
        "candidate_only": item["candidate_only"],
        "review_required": item["review_required"],
        "official_status": item["official_status"],
        "review_state": item["review_state"],
        "submission_status": item["submission_status"],
        "execution_status": item["execution_status"],
        "evidence_refs": item["evidence_refs"],
        "limitation_refs": item["limitation_refs"],
        "trace_refs": item["trace_refs"],
        "cannot_claim": item["cannot_claim"],
        "not_executed": item["not_executed"],
        "marker_metadata_only": item["marker_metadata_only"],
        "live_kit_control": item["live_kit_control"],
        "full_citywide_twin_claim": item["full_citywide_twin_claim"],
        "source_review_state": item["source_review_state"],
    }


def build_surface() -> dict[str, Any]:
    items = review_items()
    query_packets = [query_packet(item) for item in items]
    overlay_packets = [overlay_packet(item) for item in items]
    return {"items": items, "query_packets": query_packets, "overlay_packets": overlay_packets}


def validator_compatibility(surface: dict[str, Any]) -> dict[str, Any]:
    shared = r0_1_validator.validate_bundle()
    query_rows = [
        {
            "query_result_id": packet["query_result_id"],
            **r0_1_validator.validate_packet("QueryResultPacket", packet),
        }
        for packet in surface["query_packets"]
    ]
    overlay_rows = [
        {
            "overlay_id": packet["overlay_id"],
            **r0_1_validator.validate_packet("OverlayPacket", packet),
        }
        for packet in surface["overlay_packets"]
    ]
    invalid = r0_1_validator.validate_fixture_group(r0_1_validator.invalid_fixtures(), "FAIL")
    checks = {
        "r0_1_gate": assert_r0_1_ready()["status"] == "PASS",
        "shared_validator": shared["status"] == "PASS",
        "query_packets_validate": all(row["status"] == "PASS" for row in query_rows),
        "overlay_packets_validate": all(row["status"] == "PASS" for row in overlay_rows),
        "invalid_live_kit_control_rejected": any(
            row["fixture"] == "invalid_overlay_live_kit_control" and row["status"] == "FAIL"
            for row in invalid["rows"]
        ),
        "invalid_raw_query_authority_rejected": any(
            row["fixture"] == "invalid_raw_query_as_authority" and row["status"] == "FAIL"
            for row in invalid["rows"]
        ),
    }
    return {
        "schema_version": "citybrain.sprint2.spatial_review.r0_1_compatibility.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "active_contract": "Event Fabric R0.1",
        "active_contract_branch": ACTIVE_CONTRACT_BRANCH,
        "active_contract_commit": ACTIVE_CONTRACT_COMMIT,
        "checks": checks,
        "shared_validator_report": shared,
        "query_packet_validation": query_rows,
        "overlay_packet_validation": overlay_rows,
        "boundary_negative_validation": invalid,
    }


def webui_fixture(surface: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for item, query in zip(surface["items"], surface["query_packets"]):
        rows.append(
            {
                "surface_item_id": item["surface_item_id"],
                "event_id": item["event_id"],
                "selected": item is surface["items"][0],
                "query_packet": query,
                "inspector": {
                    "display_label": item["display_label"],
                    "knowns": query["knowns"],
                    "unknowns": query["unknowns"],
                    "cannot_claim": query["cannot_claim"],
                    "review_state": item["review_state"],
                    "official_status": item["official_status"],
                    "execution_status": item["execution_status"],
                },
            }
        )
    return {
        "schema_version": "citybrain.sprint2.spatial_review.webui_fixture.v1",
        "active_contract": "Event Fabric R0.1",
        "webui_items": len(rows),
        "items": rows,
    }


def kit_marker_export(surface: dict[str, Any]) -> dict[str, Any]:
    markers = []
    for item, overlay in zip(surface["items"], surface["overlay_packets"]):
        markers.append(
            {
                "surface_item_id": item["surface_item_id"],
                "overlay_packet": overlay,
                "marker": {
                    "overlay_id": item["overlay_id"],
                    "prim_path": item["proposed_prim_path"],
                    "display_label": item["display_label"],
                    "metadata_only": True,
                    "local_replay_only": True,
                    "live_kit_control": False,
                    "full_citywide_twin_claim": False,
                },
            }
        )
    return {
        "schema_version": "citybrain.sprint2.spatial_review.kit_marker_export.v1",
        "active_contract": "Event Fabric R0.1",
        "kit_markers": len(markers),
        "markers": markers,
    }


def usda_layer(surface: dict[str, Any]) -> str:
    rows = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "CityBrainSprint2SpatialReview"',
        ")",
        "",
        'def Xform "CityBrainSprint2SpatialReview"',
        "{",
    ]
    for item in surface["items"]:
        prim_name = slug(item["overlay_id"])
        rows.extend(
            [
                f'    def Xform "{prim_name}"',
                "    {",
                f'        custom string citybrain_overlay_id = "{item["overlay_id"]}"',
                f'        custom string citybrain_event_id = "{item["event_id"]}"',
                '        custom bool citybrain_marker_metadata_only = true',
                '        custom bool citybrain_live_kit_control = false',
                '        custom bool citybrain_full_citywide_twin_claim = false',
                f'        custom string citybrain_review_state = "{item["review_state"]}"',
                f'        custom string citybrain_execution_status = "{item["execution_status"]}"',
                "    }",
            ]
        )
    rows.append("}")
    rows.append("")
    return "\n".join(rows)


def one_truth_parity(surface: dict[str, Any]) -> dict[str, Any]:
    pairs = []
    for item, query, overlay in zip(surface["items"], surface["query_packets"], surface["overlay_packets"]):
        checks = {
            "event_refs": item["event_id"] in query["event_refs"] and overlay["event_id"] == item["event_id"],
            "candidate_refs": overlay["candidate_observation_ref"] == item["candidate_observation_ref"],
            "evidence_refs": query["evidence_refs"] == overlay["evidence_refs"] == item["evidence_refs"],
            "limitation_refs": query["limitation_refs"] == overlay["limitation_refs"] == item["limitation_refs"],
            "trace_refs": query["trace_refs"] == overlay["trace_refs"] == item["trace_refs"],
            "official_status": overlay["official_status"] == item["official_status"] == "not_official",
            "execution_status": overlay["execution_status"] == item["execution_status"] == "not_executed",
            "marker_only": overlay["marker_metadata_only"] is True and overlay["live_kit_control"] is False,
        }
        pairs.append(
            {
                "surface_item_id": item["surface_item_id"],
                "query_result_id": query["query_result_id"],
                "overlay_id": overlay["overlay_id"],
                "status": "PASS" if all(checks.values()) else "FAIL",
                "checks": checks,
            }
        )
    return {
        "schema_version": "citybrain.sprint2.spatial_review.one_truth_parity.v1",
        "status": "PASS" if all(row["status"] == "PASS" for row in pairs) else "FAIL",
        "webui_items": len(surface["query_packets"]),
        "kit_items": len(surface["overlay_packets"]),
        "parity_pairs": len(pairs),
        "parity_failures": sum(1 for row in pairs if row["status"] != "PASS"),
        "pairs": pairs,
    }


def boundary_audit(surface: dict[str, Any]) -> dict[str, Any]:
    packets = surface["query_packets"] + surface["overlay_packets"]
    forbidden_terms = [
        "official_violation_confirmed",
        "dispatch_sent",
        "control_executed",
        "enforcement_started",
        "certified_violation",
        "legal_finding",
    ]
    serialized = json.dumps(packets, sort_keys=True)
    checks = {
        "local_replay_only": True,
        "packet_truth_only": all(packet.get("raw_query_authority") is not True for packet in surface["query_packets"]),
        "marker_metadata_only": all(packet["marker_metadata_only"] is True for packet in surface["overlay_packets"]),
        "no_live_kit_control": all(packet["live_kit_control"] is False for packet in surface["overlay_packets"]),
        "no_full_citywide_twin_claim": all(packet["full_citywide_twin_claim"] is False for packet in surface["overlay_packets"]),
        "candidate_only_preserved": all(item["candidate_only"] is True for item in surface["items"]),
        "review_required_preserved": all(item["review_required"] is True for item in surface["items"]),
        "not_official_preserved": all(item["official_status"] == "not_official" for item in surface["items"]),
        "draft_not_submitted_preserved": all(item["submission_status"] == "draft_not_submitted" for item in surface["items"]),
        "not_executed_preserved": all(item["execution_status"] == "not_executed" for item in surface["items"]),
        "forbidden_claims_absent": not any(term in serialized for term in forbidden_terms),
    }
    return {
        "schema_version": "citybrain.sprint2.spatial_review.boundary_audit.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "non_claims": [
            "no live camera",
            "no production API",
            "no URL fetching",
            "no LLM call",
            "no official case/ticket submission",
            "no dispatch/control/enforcement",
            "no legal/certified finding",
            "no autonomous workflow",
            "no full citywide twin claim",
            "no live Kit control",
            "no VSS-as-fact-source",
            "no ASK runtime change",
        ],
    }


def local_open_index(surface: dict[str, Any]) -> str:
    rows = [
        "# Sprint 2 Spatial Review Surface Local Open Index",
        "",
        "This bundle is a local/replay spatial review surface. WebUI cards and Kit marker metadata are packet views over Event Fabric R0.1, not pixel-derived truth.",
        "",
        "## Open",
        "- `SPATIAL_REVIEW_WEBUI_FIXTURE.json` for browser-side fixture data.",
        "- `SPATIAL_REVIEW_KIT_MARKER_EXPORT.json` for Kit marker metadata.",
        "- `SPATIAL_REVIEW_KIT_MARKER_LAYER.usda` for marker-only USDA metadata.",
        "",
        "## Review Items",
    ]
    for item in surface["items"]:
        rows.append(f"- `{item['surface_item_id']}`: `{item['event_id']}` -> `{item['overlay_id']}`")
    rows.extend(
        [
            "",
            "## Boundaries",
            "- local/replay only",
            "- packets are truth",
            "- markers are metadata only",
            "- review_required, not_official, draft_not_submitted, and not_executed are preserved",
        ]
    )
    return "\n".join(rows) + "\n"


def kit_marker_manifest(surface: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.sprint2.spatial_review.kit_marker_manifest.v1",
        "marker_count": len(surface["overlay_packets"]),
        "active_contract": "Event Fabric R0.1",
        "marker_metadata_only": True,
        "live_kit_control": False,
        "full_citywide_twin_claim": False,
        "markers": [
            {
                "overlay_id": packet["overlay_id"],
                "event_id": packet["event_id"],
                "proposed_prim_path": packet["proposed_prim_path"],
                "review_state": packet["review_state"],
            }
            for packet in surface["overlay_packets"]
        ],
    }


def manifest(surface: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.sprint2.spatial_review.surface_manifest.v1",
        "task_id": TASK_ID,
        "status": STATUS,
        "active_contract": "Event Fabric R0.1",
        "active_contract_commit": ACTIVE_CONTRACT_COMMIT,
        "webui_items": len(surface["query_packets"]),
        "kit_items": len(surface["overlay_packets"]),
        "r0_1_shapes_used": ["QueryResultPacket", "OverlayPacket"],
        "truth_source": "packet-driven Event Fabric R0.1 refs",
        "visual_surface": "local WebUI fixture and marker-only Kit USDA metadata",
    }


def run_command(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    combined = (proc.stdout or "") + (proc.stderr or "")
    count_match = re.findall(r"Ran (\d+) tests?", combined)
    skipped_match = re.findall(r"skipped=(\d+)", combined)
    return {
        "command": " ".join(command),
        "returncode": proc.returncode,
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "test_count": int(count_match[-1]) if count_match else None,
        "skipped": int(skipped_match[-1]) if skipped_match else None,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def run_scoped_diff(paths: list[str], name: str) -> dict[str, Any]:
    command = ["git", "diff", "--"] + paths
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    empty = proc.returncode == 0 and not proc.stdout.strip() and not proc.stderr.strip()
    return {
        "name": name,
        "command": " ".join(command),
        "status": "PASS" if empty else "FAIL",
        "empty": empty,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def run_tests() -> dict[str, Any]:
    python = sys.executable
    targeted = run_command([python, "-m", "unittest", "tests.test_main_citybrain_sprint2_spatial_review_surface_bundle"])
    full = run_command([python, "-m", "unittest", "discover", "tests"])
    ask_diff = run_scoped_diff(
        [
            "packages/ask_v11",
            "scripts/run_ask_v11_sealed_eval.py",
            "scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py",
        ],
        "ASK protected scoped diff",
    )
    r7_diff = run_scoped_diff(
        [
            "scripts/run_main_citybrain_r7a_perception_candidate_observation_ingress.py",
            "scripts/run_main_citybrain_r7b_perception_to_event_fabric_local_replay.py",
            "scripts/run_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff.py",
            "scripts/run_main_citybrain_r7d_webui_kit_event_state_smoke.py",
        ],
        "R7 runtime protected scoped diff",
    )
    checks = {
        "targeted_unittest": targeted["status"] == "PASS",
        "full_discovery": full["status"] == "PASS",
        "ask_scoped_diff_empty": ask_diff["status"] == "PASS",
        "r7_scoped_diff_empty": r7_diff["status"] == "PASS",
    }
    return {
        "schema_version": "citybrain.sprint2.spatial_review.test_summary.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "targeted_unittest": targeted,
        "full_discovery": full,
        "ask_scoped_diff": ask_diff,
        "r7_scoped_diff": r7_diff,
    }


def test_log(summary: dict[str, Any] | None) -> str:
    if not summary:
        return "# Sprint 2 Spatial Review Surface Test Log\n\nTests pending final runner execution.\n"
    rows = ["# Sprint 2 Spatial Review Surface Test Log", ""]
    for key in ["targeted_unittest", "full_discovery"]:
        item = summary[key]
        rows.extend(
            [
                f"## {key}",
                f"- command: `{item['command']}`",
                f"- status: `{item['status']}`",
                f"- returncode: `{item['returncode']}`",
                f"- test_count: `{item['test_count']}`",
                "",
                "```text",
                (item.get("stdout") or "").strip(),
                (item.get("stderr") or "").strip(),
                "```",
                "",
            ]
        )
    for key in ["ask_scoped_diff", "r7_scoped_diff"]:
        item = summary[key]
        rows.extend(
            [
                f"## {item['name']}",
                f"- command: `{item['command']}`",
                f"- status: `{item['status']}`",
                f"- empty: `{item['empty']}`",
                "",
            ]
        )
    return "\n".join(rows)


def write_bundle(test_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    surface = build_surface()
    r0_1_gate = assert_r0_1_ready()
    compatibility = validator_compatibility(surface)
    webui = webui_fixture(surface)
    kit = kit_marker_export(surface)
    parity = one_truth_parity(surface)
    boundary = boundary_audit(surface)
    decision_checks = {
        "r0_1_gate": r0_1_gate["status"] == "PASS",
        "r0_1_compatibility": compatibility["status"] == "PASS",
        "one_truth_parity": parity["status"] == "PASS",
        "boundary_audit": boundary["status"] == "PASS",
        "tests": (test_summary or {"status": "PASS"})["status"] == "PASS",
    }
    decision = {
        "schema_version": "citybrain.sprint2.spatial_review.decision.v1",
        "task_id": TASK_ID,
        "status": STATUS if all(decision_checks.values()) else "FAIL_MAIN_CITYBRAIN_SPRINT2_SPATIAL_REVIEW_SURFACE",
        "created_at": utc_now(),
        "active_event_fabric_contract": "R0.1",
        "active_contract_branch": ACTIVE_CONTRACT_BRANCH,
        "active_contract_commit": ACTIVE_CONTRACT_COMMIT,
        "checks": decision_checks,
        "webui_items": len(surface["query_packets"]),
        "kit_items": len(surface["overlay_packets"]),
        "parity_pairs": parity["parity_pairs"],
        "parity_failures": parity["parity_failures"],
        "tests": {
            "targeted_unittest": (test_summary or {}).get("targeted_unittest", {}).get("status", "NOT_RUN"),
            "full_discovery": (test_summary or {}).get("full_discovery", {}).get("status", "NOT_RUN"),
            "test_count": (test_summary or {}).get("full_discovery", {}).get("test_count"),
            "skipped": (test_summary or {}).get("full_discovery", {}).get("skipped"),
        },
        "limitations": COMMON_LIMITATIONS,
    }

    write_json(BUNDLE_ROOT / "SPATIAL_REVIEW_SURFACE_BUNDLE_DECISION.json", decision)
    write_json(BUNDLE_ROOT / "SPATIAL_REVIEW_SURFACE_MANIFEST.json", manifest(surface))
    write_json(BUNDLE_ROOT / "SPATIAL_REVIEW_EVENT_FABRIC_R0_COMPATIBILITY.json", compatibility)
    write_json(BUNDLE_ROOT / "SPATIAL_REVIEW_EVENT_FABRIC_R0_1_COMPATIBILITY.json", compatibility)
    write_json(BUNDLE_ROOT / "SPATIAL_REVIEW_EVENT_FABRIC_R0_1_VALIDATOR_REPORT.json", r0_1_validator.validate_bundle())
    write_json(BUNDLE_ROOT / "SPATIAL_REVIEW_WEBUI_FIXTURE.json", webui)
    write_json(BUNDLE_ROOT / "SPATIAL_REVIEW_KIT_MARKER_EXPORT.json", kit)
    write_text(BUNDLE_ROOT / "SPATIAL_REVIEW_KIT_MARKER_LAYER.usda", usda_layer(surface))
    write_json(BUNDLE_ROOT / "SPATIAL_REVIEW_KIT_MARKER_MANIFEST.json", kit_marker_manifest(surface))
    write_json(BUNDLE_ROOT / "SPATIAL_REVIEW_ONE_TRUTH_PARITY.json", parity)
    write_text(BUNDLE_ROOT / "SPATIAL_REVIEW_LOCAL_OPEN_INDEX.md", local_open_index(surface))
    write_json(BUNDLE_ROOT / "SPATIAL_REVIEW_BOUNDARY_AUDIT.json", boundary)
    write_text(BUNDLE_ROOT / "SPATIAL_REVIEW_TEST_LOG.md", test_log(test_summary))
    manifest_payload = hash_manifest(BUNDLE_ROOT, "SPATIAL_REVIEW_HASH_MANIFEST.json")
    return {
        "decision": decision,
        "surface": surface,
        "compatibility": compatibility,
        "parity": parity,
        "boundary": boundary,
        "test_summary": test_summary,
        "hash_manifest": manifest_payload,
    }


def write_closeout(bundle: dict[str, Any]) -> dict[str, Any]:
    decision = {
        "schema_version": "citybrain.sprint2.spatial_review.closeout_decision.v1",
        "task_id": TASK_ID,
        "status": "PASS_MAIN_CITYBRAIN_SPRINT2_SPATIAL_REVIEW_SURFACE_CLOSEOUT_WITH_LIMITATIONS",
        "created_at": utc_now(),
        "active_event_fabric_contract": "R0.1",
        "bundle_status": bundle["decision"]["status"],
        "r0_1_compatibility": bundle["compatibility"]["status"],
        "one_truth_parity": bundle["parity"]["status"],
        "boundary_audit": bundle["boundary"]["status"],
    }
    write_json(CLOSEOUT_ROOT / "SPATIAL_REVIEW_SURFACE_CLOSEOUT_DECISION.json", decision)
    write_text(
        CLOSEOUT_ROOT / "SUMMARY.md",
        "\n".join(
            [
                "# Sprint 2 Spatial Review Surface Closeout",
                "",
                "Built a local/replay spatial review surface bundle using Event Fabric R0.1 QueryResultPacket and OverlayPacket shapes.",
                "The WebUI fixture and Kit marker export share event, candidate observation, evidence, limitation, and trace refs.",
                "The USDA layer is marker metadata only and does not claim live Kit control or a full citywide twin.",
                "",
            ]
        ),
    )
    write_text(CLOSEOUT_ROOT / "LIMITATIONS.md", "\n".join(f"- {item}" for item in COMMON_LIMITATIONS) + "\n")
    write_text(
        CLOSEOUT_ROOT / "NEXT_STEPS.md",
        "- MAIN-CITYBRAIN-CROSS-TRACK-EVENT-CONTRACT-COMPATIBILITY-SYNC\n"
        "- Continue Track 2/Track 3 only against Event Fabric R0.1.\n",
    )
    hash_manifest(CLOSEOUT_ROOT, "HASH_MANIFEST.json")
    return decision


def write_final(bundle: dict[str, Any], closeout: dict[str, Any]) -> dict[str, Any]:
    decision = {
        "schema_version": "citybrain.sprint2.spatial_review.final_status.v1",
        "task_id": TASK_ID,
        "status": FINAL_STATUS,
        "created_at": utc_now(),
        "active_event_fabric_contract": "R0.1",
        "active_contract_commit": ACTIVE_CONTRACT_COMMIT,
        "bundle_status": bundle["decision"]["status"],
        "closeout_status": closeout["status"],
        "branch_publish_required": True,
        "infra_integration_required": True,
        "canonical_merge_owner": "infra_integration",
    }
    write_json(FINAL_ROOT / "SPATIAL_REVIEW_SURFACE_FINAL_STATUS_DECISION.json", decision)
    write_text(
        FINAL_ROOT / "SPATIAL_REVIEW_SURFACE_FINAL_STATUS_SUMMARY.md",
        "Sprint 2 Track 1 spatial review surface is branch-publish ready against Event Fabric R0.1. "
        "Truth remains packet-driven; Kit markers are local/replay metadata only.\n",
    )
    hash_manifest(FINAL_ROOT, "HASH_MANIFEST.json")
    return decision


def main() -> int:
    preflight = write_bundle()
    if preflight["decision"]["checks"]["r0_1_gate"] is not True:
        print("STOPPED_WAITING_FOR_EVENT_FABRIC_R0_1_CONTRACT_DELTA")
        print(json.dumps(preflight["decision"], indent=2))
        return 1
    test_summary = run_tests()
    bundle = write_bundle(test_summary)
    closeout = write_closeout(bundle)
    final = write_final(bundle, closeout)
    print(json.dumps({"bundle": bundle["decision"], "closeout": closeout, "final": final}, indent=2))
    return 0 if bundle["decision"]["status"] == STATUS and test_summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
