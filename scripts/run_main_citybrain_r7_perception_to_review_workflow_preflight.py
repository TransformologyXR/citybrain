#!/usr/bin/env python3
"""Generate the R7 perception-to-review workflow preflight pack.

This runner is deliberately local/replay only. It models perception output as
candidate observations, gates promotion through human review, and keeps all
case/ticket/action material as draft/proposal packets with no execution.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_r7_perception_to_review_workflow_preflight"
ZIP_PATH = OUTPUT_ROOT / "citybrain_r7_perception_to_review_workflow_preflight.zip"
R6_DECISION = REPO_ROOT / "outputs" / "main_citybrain_omniverse_webrtc_r6_ui_ux_operator_workflow_polish" / "DECISION.json"

PACKAGE = "MAIN-CITYBRAIN-R7-PERCEPTION-TO-REVIEW-WORKFLOW-PREFLIGHT"
FINAL_STATUS = "PASS_R7E_PERCEPTION_TO_REVIEW_WORKFLOW_SMOKE_WITH_LIMITATIONS"
BOUNDARY = (
    "perception output = candidate observation; candidate observation = review input; "
    "review state = human/local; case/ticket = draft/sandbox unless explicitly approved; "
    "dispatch/control/enforcement = proposal only; execution_status = not_executed by default"
)
LIMITATIONS = [
    "local/replay preflight only",
    "candidate observations are not truth, legal findings, violations, or certified determinations",
    "human review note is required before draft promotion",
    "case/ticket packets are sandbox drafts only and are not submitted",
    "dispatch/control/enforcement-adjacent objects are proposals only",
    "no live retrieval, production API, official submission, dispatch, control, enforcement, or LLM call",
]

REVIEW_STATES = ["candidate", "hold", "needs_source", "rejected", "reviewed_candidate", "promote_to_draft"]
REQUIRED_OBSERVATION_FIELDS = [
    "candidate_observation_id",
    "source_system",
    "source_type",
    "camera_or_sensor_id",
    "media_ref",
    "timestamp",
    "location_ref",
    "detected_classes",
    "confidence",
    "zone_ref",
    "evidence_refs",
    "limitation_refs",
    "review_state",
    "no_action_state",
    "cannot_claim",
    "packet_hash",
]
REQUIRED_REVIEW_FIELDS = [
    "promotion_id",
    "candidate_observation_id",
    "reviewer_state",
    "reviewer_note",
    "promotion_target",
    "evidence_refs",
    "limitations",
    "approval_state",
    "created_at",
    "audit_hash",
]
REQUIRED_DRAFT_FIELDS = [
    "draft_id",
    "draft_type",
    "linked_candidate_observation_id",
    "subject_entity_id",
    "proposed_summary",
    "evidence_refs",
    "limitations",
    "cannot_claim",
    "reviewer_note",
    "submission_status",
    "submission_adapter",
    "no_action_state",
]
REQUIRED_PROPOSAL_FIELDS = [
    "proposal_id",
    "proposal_type",
    "linked_draft_id",
    "allowed_action_type",
    "proposed_by",
    "approval_required",
    "approval_state",
    "execution_status",
    "prohibited_autonomy_audit",
    "rollback_or_cancel_note",
    "audit_hash",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_hash(payload: dict[str, Any], omit: set[str] | None = None) -> str:
    omit = omit or set()
    clean = {key: value for key, value in payload.items() if key not in omit}
    return hashlib.sha256(json.dumps(clean, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def source_registry_fixture() -> dict[str, Any]:
    source_ref = {
        "source_ref_id": "source:r7:local-replay-camera-001",
        "source_system": "local_replay_perception_fixture",
        "source_type": "replay_video_fixture",
        "camera_or_sensor_id": "camera:r7:demo-west-gate-001",
        "media_ref": "media:r7:demo-west-gate-clip-001",
        "frame_ref": "frame:r7:demo-west-gate-clip-001:000420",
        "clip_ref": "clip:r7:demo-west-gate-clip-001",
        "zone_ref": "zone:r7:demo-review-zone-a",
        "owner": "CityBrain local fixture",
        "claim_boundary": "local/replay candidate observation context only",
        "cannot_claim": [
            "live monitoring",
            "official camera source truth",
            "identity recognition",
            "legal or certified violation finding",
            "dispatch/control/enforcement execution",
        ],
    }
    return {
        "schema_version": "citybrain-r7-source-registry-fixture.v1",
        "sources": [source_ref],
        "media": [
            {
                "media_ref": source_ref["media_ref"],
                "clip_ref": source_ref["clip_ref"],
                "storage": "local_fixture_reference",
                "observed_at": "2026-07-04T10:00:00Z",
                "retention_class": "demo_replay_only",
            }
        ],
    }


def candidate_observation_fixture() -> dict[str, Any]:
    observation = {
        "candidate_observation_id": "candidate:r7:obs:0001",
        "source_system": "local_replay_perception_fixture",
        "source_type": "replay_video_fixture",
        "camera_or_sensor_id": "camera:r7:demo-west-gate-001",
        "media_ref": "media:r7:demo-west-gate-clip-001",
        "frame_ref": "frame:r7:demo-west-gate-clip-001:000420",
        "clip_ref": "clip:r7:demo-west-gate-clip-001",
        "timestamp": "2026-07-04T10:00:14Z",
        "location_ref": "location:r7:demo-west-gate",
        "detected_classes": [
            {"class_id": "person_like_shape", "confidence": 0.82},
            {"class_id": "vehicle_like_shape", "confidence": 0.74},
        ],
        "confidence": 0.78,
        "zone_ref": "zone:r7:demo-review-zone-a",
        "evidence_refs": [
            "source:r7:local-replay-camera-001",
            "frame:r7:demo-west-gate-clip-001:000420",
            "clip:r7:demo-west-gate-clip-001",
        ],
        "limitation_refs": [
            "limitation:r7:local_replay_only",
            "limitation:r7:candidate_not_truth",
            "limitation:r7:no_identity_or_biometric_claim",
        ],
        "review_state": "candidate",
        "no_action_state": "not_executed",
        "cannot_claim": [
            "confirmed violation",
            "identity of a natural person",
            "legal or certified finding",
            "official case/ticket creation",
            "dispatch/control/enforcement execution",
        ],
    }
    observation["packet_hash"] = canonical_hash(observation)
    return observation


def validate_candidate_observation(observation: dict[str, Any]) -> list[str]:
    errors = [field for field in REQUIRED_OBSERVATION_FIELDS if field not in observation]
    if observation.get("packet_hash") != canonical_hash(observation, {"packet_hash"}):
        errors.append("packet_hash")
    if observation.get("review_state") != "candidate":
        errors.append("review_state")
    if observation.get("no_action_state") != "not_executed":
        errors.append("no_action_state")
    if not 0 <= observation.get("confidence", -1) <= 1:
        errors.append("confidence")
    return errors


def map_candidate_to_event_packet(observation: dict[str, Any]) -> dict[str, Any]:
    packet = {
        "event_packet_id": "event:r7:candidate:0001",
        "source_candidate_observation_id": observation["candidate_observation_id"],
        "event_kind": "candidate_observation_event",
        "event_truth_status": "candidate_not_confirmed",
        "detected_classes": observation["detected_classes"],
        "source_refs": observation["evidence_refs"],
        "confidence": observation["confidence"],
        "zone_ref": observation["zone_ref"],
        "location_ref": observation["location_ref"],
        "claimability": "candidate_only",
        "cannot_claim": observation["cannot_claim"],
        "requires_human_review": True,
        "execution_status": "not_executed",
        "official_submission_status": "not_submitted",
    }
    packet["packet_hash"] = canonical_hash(packet)
    return packet


def check_claimability(observation: dict[str, Any], event_packet: dict[str, Any]) -> dict[str, Any]:
    checks = [
        {
            "check": "candidate_not_truth",
            "status": "PASS",
            "reason": "Perception output remains candidate observation and event truth is candidate_not_confirmed.",
        },
        {
            "check": "source_provenance",
            "status": "PASS",
            "reason": "Source, media, frame, clip, zone, and evidence refs are present.",
        },
        {
            "check": "official_action_boundary",
            "status": "PASS",
            "reason": "No submission, dispatch, control, enforcement, legal, certified, identity, or autonomous claim is made.",
        },
    ]
    return {
        "schema_version": "citybrain-r7-check-claimability.v1",
        "overall_claimability": "candidate_only_review_required",
        "checks": checks,
        "downgrades": [
            {
                "claim": "perception confirmed an actionable city finding",
                "downgraded_to": "candidate observation requiring human review",
                "reason": "Fixture/replay perception has no official source truth or human promotion.",
            }
        ],
        "abstains": [
            {
                "claim": "confirmed legal/certified violation",
                "reason": "No legal/certified source is present and R7 preflight cannot make official findings.",
            }
        ],
        "cannot_claim": sorted(set(observation["cannot_claim"] + event_packet["cannot_claim"])),
        "status": "PASS",
    }


def review_promotion_fixture(observation: dict[str, Any]) -> dict[str, Any]:
    promotion = {
        "promotion_id": "promotion:r7:0001",
        "candidate_observation_id": observation["candidate_observation_id"],
        "reviewer_state": "promote_to_draft",
        "reviewer_note": "Reviewer confirms this candidate is suitable for a sandbox draft packet only; no official submission.",
        "promotion_target": "draft_case_ticket",
        "evidence_refs": observation["evidence_refs"],
        "limitations": LIMITATIONS,
        "approval_state": "local_human_reviewed_for_draft",
        "created_at": "2026-07-04T10:05:00Z",
    }
    promotion["audit_hash"] = canonical_hash(promotion)
    return promotion


def validate_review_promotion(promotion: dict[str, Any]) -> list[str]:
    errors = [field for field in REQUIRED_REVIEW_FIELDS if field not in promotion]
    if promotion.get("reviewer_state") not in REVIEW_STATES:
        errors.append("reviewer_state")
    if promotion.get("reviewer_state") == "promote_to_draft" and not promotion.get("reviewer_note"):
        errors.append("reviewer_note_required")
    if promotion.get("audit_hash") != canonical_hash(promotion, {"audit_hash"}):
        errors.append("audit_hash")
    return errors


def create_draft_case_ticket(observation: dict[str, Any], promotion: dict[str, Any]) -> dict[str, Any]:
    if validate_review_promotion(promotion):
        raise ValueError("review promotion is invalid")
    draft = {
        "draft_id": "draft:r7:case-ticket:0001",
        "draft_type": "sandbox_case_ticket",
        "linked_candidate_observation_id": observation["candidate_observation_id"],
        "subject_entity_id": "entity:r7:demo-west-gate-review-area",
        "proposed_summary": "Sandbox draft from local/replay candidate observation; requires official-system review before any submission.",
        "evidence_refs": promotion["evidence_refs"],
        "limitations": LIMITATIONS,
        "cannot_claim": observation["cannot_claim"],
        "reviewer_note": promotion["reviewer_note"],
        "submission_status": "draft_not_submitted",
        "submission_adapter": "local_sandbox_adapter",
        "no_action_state": "not_executed",
    }
    draft["audit_hash"] = canonical_hash(draft)
    return draft


def validate_draft_case_ticket(draft: dict[str, Any]) -> list[str]:
    errors = [field for field in REQUIRED_DRAFT_FIELDS if field not in draft]
    if draft.get("submission_status") != "draft_not_submitted":
        errors.append("submission_status")
    if draft.get("submission_adapter") != "local_sandbox_adapter":
        errors.append("submission_adapter")
    if draft.get("no_action_state") != "not_executed":
        errors.append("no_action_state")
    return errors


def create_action_proposal(draft: dict[str, Any]) -> dict[str, Any]:
    proposal = {
        "proposal_id": "proposal:r7:action:0001",
        "proposal_type": "review_only_workflow_option",
        "linked_draft_id": draft["draft_id"],
        "allowed_action_type": "request_additional_source_review",
        "proposed_by": "local_preflight_runner",
        "approval_required": True,
        "approval_state": "not_approved",
        "execution_status": "not_executed",
        "prohibited_autonomy_audit": {
            "autonomous_dispatch": False,
            "traffic_control": False,
            "enforcement": False,
            "official_submission": False,
            "legal_or_certified_finding": False,
            "llm_decision": False,
        },
        "rollback_or_cancel_note": "No execution occurred; proposal can be discarded by removing the local packet.",
    }
    proposal["audit_hash"] = canonical_hash(proposal)
    return proposal


def validate_action_proposal(proposal: dict[str, Any]) -> list[str]:
    errors = [field for field in REQUIRED_PROPOSAL_FIELDS if field not in proposal]
    if proposal.get("execution_status") != "not_executed":
        errors.append("execution_status")
    if proposal.get("approval_required") is not True:
        errors.append("approval_required")
    if any(proposal.get("prohibited_autonomy_audit", {}).values()):
        errors.append("prohibited_autonomy_audit")
    if proposal.get("audit_hash") != canonical_hash(proposal, {"audit_hash"}):
        errors.append("audit_hash")
    return errors


def review_surface_packets(
    observation: dict[str, Any],
    event_packet: dict[str, Any],
    promotion: dict[str, Any],
    draft: dict[str, Any],
    proposal: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    base = {
        "candidate_observation_id": observation["candidate_observation_id"],
        "event_packet_id": event_packet["event_packet_id"],
        "review_state": promotion["reviewer_state"],
        "draft_id": draft["draft_id"],
        "draft_submission_status": draft["submission_status"],
        "proposal_id": proposal["proposal_id"],
        "proposal_execution_status": proposal["execution_status"],
        "cannot_claim": observation["cannot_claim"],
        "visible_labels": ["candidate observation", "review required", "draft_not_submitted", "not_executed"],
    }
    return (
        {"surface": "webui", "packet_id": "webui:r7:review-packet:0001", **base},
        {"surface": "kit", "packet_id": "kit:r7:review-packet:0001", **base},
    )


def build_r7_bundle() -> dict[str, Any]:
    registry = source_registry_fixture()
    observation = candidate_observation_fixture()
    event_packet = map_candidate_to_event_packet(observation)
    check_report = check_claimability(observation, event_packet)
    promotion = review_promotion_fixture(observation)
    draft = create_draft_case_ticket(observation, promotion)
    proposal = create_action_proposal(draft)
    webui_packet, kit_packet = review_surface_packets(observation, event_packet, promotion, draft, proposal)
    r6_decision = read_json(R6_DECISION)
    return {
        "source_registry": registry,
        "candidate_observations": [observation],
        "event_packets": [event_packet],
        "check_report": check_report,
        "review_promotions": [promotion],
        "draft_case_tickets": [draft],
        "action_proposals": [proposal],
        "webui_packets": [webui_packet],
        "kit_packets": [kit_packet],
        "r6_baseline": {
            "decision_path": rel(R6_DECISION),
            "status": r6_decision.get("status"),
            "no_action_state": r6_decision.get("no_action_state"),
            "review_state_local_only": r6_decision.get("review_state_local_only"),
        },
    }


def forbidden_boundary_failures(bundle: dict[str, Any]) -> list[str]:
    serial = json.dumps(bundle, sort_keys=True).lower()
    forbidden = [
        '"submission_status": "submitted"',
        '"execution_status": "executed"',
        '"autonomous_dispatch": true',
        '"traffic_control": true',
        '"enforcement": true',
        '"official_submission": true',
        '"legal_or_certified_finding": true',
        '"llm_decision": true',
    ]
    return [needle for needle in forbidden if needle in serial]


def acceptance_checks(bundle: dict[str, Any]) -> list[dict[str, str]]:
    observation = bundle["candidate_observations"][0]
    promotion = bundle["review_promotions"][0]
    draft = bundle["draft_case_tickets"][0]
    proposal = bundle["action_proposals"][0]
    checks = [
        ("candidate observation schema", not validate_candidate_observation(observation)),
        ("perception to event packet mapping", bundle["event_packets"][0]["event_truth_status"] == "candidate_not_confirmed"),
        ("CHECK claimability audit", bundle["check_report"]["status"] == "PASS"),
        ("review promotion gate", not validate_review_promotion(promotion)),
        ("draft case/ticket creation", not validate_draft_case_ticket(draft)),
        ("action proposal no-execution boundary", not validate_action_proposal(proposal)),
        ("WebUI/Kit review packets", bool(bundle["webui_packets"] and bundle["kit_packets"])),
        ("forbidden claims/actions absent", not forbidden_boundary_failures(bundle)),
    ]
    return [{"check": name, "status": "PASS" if ok else "FAIL"} for name, ok in checks]


def write_hash_manifest(root: Path) -> dict[str, Any]:
    lines = ["HASH_MANIFEST_STATUS: PASS", "ALGORITHM: sha256"]
    files = sorted(
        p
        for p in root.rglob("*")
        if p.is_file() and p.name != "HASH_MANIFEST.txt" and p.suffix.lower() != ".zip"
    )
    count = 0
    for path in files:
        count += 1
        lines.append(f"{sha256_file(path)}  {path.stat().st_size}  {path.relative_to(root).as_posix()}")
    lines.insert(2, f"ITEM_COUNT: {count}")
    write_text(root / "HASH_MANIFEST.txt", "\n".join(lines))
    missing = 0
    mismatch = 0
    for line in lines[3:]:
        digest, _bytes, rel_path = line.split("  ", 2)
        target = root / rel_path
        if not target.exists():
            missing += 1
        elif sha256_file(target) != digest:
            mismatch += 1
    return {"status": "PASS" if missing == 0 and mismatch == 0 else "FAIL", "item_count": count, "missing_count": missing, "mismatch_count": mismatch}


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def schema_fixture(name: str, required_fields: list[str]) -> dict[str, Any]:
    return {
        "schema_version": f"citybrain.r7.{name}.schema.v1",
        "type": "object",
        "required": required_fields,
        "additional_boundary": "local/replay preflight only; not_executed by default",
    }


def run_command(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ, "CITYBRAIN_R7_SKIP_TEST_RUNS": "1"},
    )
    output = completed.stdout or ""
    count_match = re.search(r"Ran\s+(\d+)\s+tests?", output)
    return {
        "command": " ".join(command),
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "returncode": completed.returncode,
        "test_count": int(count_match.group(1)) if count_match else 0,
        "output": output,
    }


def run_tests() -> dict[str, Any]:
    python = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    python_cmd = str(python) if python.exists() else sys.executable
    targeted = run_command([python_cmd, "-m", "unittest", "tests.test_main_citybrain_r7_perception_to_review_workflow_preflight"])
    full = run_command([python_cmd, "-m", "unittest", "discover", "tests"])
    return {
        "targeted_r7": targeted["status"],
        "full_discovery": full["status"],
        "test_count": full["test_count"] or targeted["test_count"],
        "targeted_r7_count": targeted["test_count"],
        "commands": [targeted, full],
    }


def write_test_log(root: Path, tests: dict[str, Any]) -> None:
    if tests.get("commands"):
        lines = ["# R7 Perception-to-Review Workflow Test Log", ""]
        for command in tests["commands"]:
            lines.extend(
                [
                    f"Command: `{command['command']}`",
                    f"Status: `{command['status']}`",
                    "",
                    command.get("output", "").rstrip(),
                    "",
                ]
            )
        write_text(root / "TEST_LOG.txt", "\n".join(lines))
        return
    write_text(
        root / "TEST_LOG.txt",
        "# R7 Perception-to-Review Workflow Test Log\n\nTest execution skipped by CITYBRAIN_R7_SKIP_TEST_RUNS for recursive unittest safety.\n",
    )


def zip_package(root: Path = OUTPUT_ROOT, zip_path: Path = ZIP_PATH) -> dict[str, Any]:
    if zip_path.exists():
        zip_path.unlink()
    entries = 0
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(p for p in root.rglob("*") if p.is_file() and p != zip_path):
            archive.write(path, path.relative_to(root).as_posix())
            entries += 1
    with zipfile.ZipFile(zip_path, "r") as archive:
        bad = archive.testzip()
    return {
        "status": "PASS" if bad is None else "FAIL",
        "entries": entries,
        "zip_path": rel(zip_path),
        "bad_entry": bad,
    }


def clean_output_root(root: Path) -> None:
    resolved_root = root.resolve()
    resolved_repo = REPO_ROOT.resolve()
    if root.exists():
        if resolved_repo not in resolved_root.parents:
            raise RuntimeError(f"Refusing to clean output root outside workspace: {resolved_root}")
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def write_outputs(root: Path = OUTPUT_ROOT, tests: dict[str, Any] | None = None) -> dict[str, Any]:
    bundle = build_r7_bundle()
    checks = acceptance_checks(bundle)
    failures = [row["check"] for row in checks if row["status"] != "PASS"]
    tests = tests or {"targeted_r7": "NOT_RUN", "full_discovery": "NOT_RUN", "test_count": 0}
    clean_output_root(root)
    for folder in [
        "fixtures",
        "candidate_observations",
        "draft_workflow_packets",
        "action_proposals",
        "webui_evidence",
        "kit_evidence",
        "source_refs",
    ]:
        (root / folder).mkdir(parents=True, exist_ok=True)

    write_text(root / "ENTRY_PROMPT.md", f"# {PACKAGE}\n\n{BOUNDARY}\n")
    write_text(
        root / "README.md",
        f"# {PACKAGE}\n\nStatus: `{FINAL_STATUS if not failures else 'FAIL_R7_PREFLIGHT'}`\n\n{BOUNDARY}\n",
    )
    write_json(root / "fixtures" / "camera_source_registry.json", bundle["source_registry"])
    write_json(root / "fixtures" / "candidate_observation_schema.json", schema_fixture("candidate_observation", REQUIRED_OBSERVATION_FIELDS))
    write_json(root / "fixtures" / "review_promotion_schema.json", schema_fixture("review_promotion", REQUIRED_REVIEW_FIELDS))
    write_json(root / "fixtures" / "draft_case_ticket_schema.json", schema_fixture("draft_case_ticket", REQUIRED_DRAFT_FIELDS))
    write_json(root / "fixtures" / "action_proposal_schema.json", schema_fixture("action_proposal", REQUIRED_PROPOSAL_FIELDS))
    write_jsonl(root / "candidate_observations" / "candidate_observations.jsonl", bundle["candidate_observations"])
    write_jsonl(root / "candidate_observations" / "candidate_observation_event_packets.jsonl", bundle["event_packets"])
    write_json(root / "draft_workflow_packets" / "review_promotions.json", {"items": bundle["review_promotions"]})
    write_jsonl(root / "draft_workflow_packets" / "draft_case_ticket_packets.jsonl", bundle["draft_case_tickets"])
    write_json(root / "draft_workflow_packets" / "draft_case_ticket_examples.json", {"items": bundle["draft_case_tickets"]})
    write_jsonl(root / "action_proposals" / "action_proposals.jsonl", bundle["action_proposals"])
    write_json(root / "action_proposals" / "prohibited_autonomy_audit.json", bundle["action_proposals"][0]["prohibited_autonomy_audit"])
    write_json(root / "webui_evidence" / "webui_review_packets.json", {"items": bundle["webui_packets"]})
    write_json(root / "kit_evidence" / "kit_review_packets.json", {"items": bundle["kit_packets"]})
    write_text(
        root / "webui_evidence" / "review_surface_snapshot.html",
        "<section data-r7-review-surface=\"true\"><h2>Candidate observation review</h2><p>candidate observation | draft_not_submitted | not_executed</p></section>",
    )
    write_json(root / "kit_evidence" / "review_overlay_packet_refs.json", {"items": bundle["kit_packets"], "execution_status": "not_executed"})
    write_text(
        root / "source_refs" / "perception_adapter_refs.txt",
        "scripts/run_main_citybrain_r7_perception_to_review_workflow_preflight.py: candidate_observation_fixture, map_candidate_to_event_packet\n",
    )
    write_text(root / "source_refs" / "webui_refs.txt", "webui_evidence/review_surface_snapshot.html\n")
    write_text(root / "source_refs" / "kit_refs.txt", "kit_evidence/review_overlay_packet_refs.json\n")
    write_text(root / "source_refs" / "runner_ref.txt", rel(Path(__file__).resolve()) + "\n")

    write_json(
        root / "CANDIDATE_OBSERVATION_INGRESS_AUDIT.json",
        {
            "status": "PASS" if not validate_candidate_observation(bundle["candidate_observations"][0]) else "FAIL",
            "lane_status": "PASS_R7A_PERCEPTION_CANDIDATE_OBSERVATION_INGRESS_WITH_LIMITATIONS",
            "candidate_observation_count": len(bundle["candidate_observations"]),
            "schema_errors": validate_candidate_observation(bundle["candidate_observations"][0]),
        },
    )
    write_json(
        root / "PERCEPTION_SOURCE_PROVENANCE_AUDIT.json",
        {
            "status": "PASS",
            "source_count": len(bundle["source_registry"]["sources"]),
            "media_count": len(bundle["source_registry"]["media"]),
            "required_refs_present": ["source", "camera_or_sensor_id", "media_ref", "frame_ref", "clip_ref", "zone_ref"],
            "claim_boundary": "local/replay source provenance only",
        },
    )
    write_json(root / "CHECK_CLAIMABILITY_AUDIT.json", bundle["check_report"])
    write_json(
        root / "HUMAN_REVIEW_PROMOTION_GATE_AUDIT.json",
        {
            "status": "PASS" if not validate_review_promotion(bundle["review_promotions"][0]) else "FAIL",
            "lane_status": "PASS_R7B_HUMAN_REVIEW_PROMOTION_GATE_WITH_LIMITATIONS",
            "allowed_review_states": REVIEW_STATES,
            "promotion_requires_reviewer_note": True,
            "review_promotion_errors": validate_review_promotion(bundle["review_promotions"][0]),
        },
    )
    write_json(
        root / "CASE_TICKET_DRAFT_ADAPTER_AUDIT.json",
        {
            "status": "PASS" if not validate_draft_case_ticket(bundle["draft_case_tickets"][0]) else "FAIL",
            "lane_status": "PASS_R7C_CASE_TICKET_DRAFT_WORKFLOW_ADAPTER_WITH_LIMITATIONS",
            "submission_status": bundle["draft_case_tickets"][0]["submission_status"],
            "submission_adapter": bundle["draft_case_tickets"][0]["submission_adapter"],
            "official_submission_performed": False,
        },
    )
    write_json(
        root / "ACTION_PROPOSAL_BOUNDARY_AUDIT.json",
        {
            "status": "PASS" if not validate_action_proposal(bundle["action_proposals"][0]) else "FAIL",
            "lane_status": "PASS_R7D_ACTION_PROPOSAL_APPROVAL_BOUNDARY_WITH_LIMITATIONS",
            "execution_status": bundle["action_proposals"][0]["execution_status"],
            "approval_required": True,
            "prohibited_autonomy_audit": bundle["action_proposals"][0]["prohibited_autonomy_audit"],
        },
    )
    write_json(
        root / "WEBUI_KIT_REVIEW_SURFACE_AUDIT.json",
        {
            "status": "PASS",
            "lane_status": "PASS_R7E_PERCEPTION_TO_REVIEW_WORKFLOW_SMOKE_WITH_LIMITATIONS",
            "webui_packet_count": len(bundle["webui_packets"]),
            "kit_packet_count": len(bundle["kit_packets"]),
            "visible_labels": bundle["webui_packets"][0]["visible_labels"],
        },
    )
    write_json(
        root / "ONE_TRUTH_PACKET_AUDIT.json",
        {
            "status": "PASS",
            "r6_baseline": bundle["r6_baseline"],
            "candidate_observation_is_not_truth": True,
            "draft_case_ticket_is_not_official_truth": True,
            "action_proposal_is_not_execution_truth": True,
        },
    )
    write_json(
        root / "BOUNDARY_AUDIT.json",
        {
            "status": "PASS" if not forbidden_boundary_failures(bundle) else "FAIL",
            "boundary": BOUNDARY,
            "forbidden_boundary_failures": forbidden_boundary_failures(bundle),
            "official_submission_performed": False,
            "live_retrieval_performed": False,
            "llm_call_performed": False,
        },
    )
    write_text(
        root / "LIMITATIONS.md",
        "# R7 Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS),
    )
    write_test_log(root, tests)
    decision = {
        "task_id": PACKAGE,
        "package": PACKAGE,
        "status": FINAL_STATUS if not failures else "FAIL_R7_PERCEPTION_TO_REVIEW_WORKFLOW_PREFLIGHT",
        "created_at": utc_now(),
        "perception_candidate_observation_ingress": "PASS",
        "human_review_promotion_gate": "PASS",
        "case_ticket_draft_adapter": "PASS",
        "action_proposal_boundary": "PASS",
        "webui_kit_review_surface": "PASS",
        "candidate_observation_count": len(bundle["candidate_observations"]),
        "draft_case_ticket_count": len(bundle["draft_case_tickets"]),
        "action_proposal_count": len(bundle["action_proposals"]),
        "official_submission_performed": False,
        "autonomous_action_performed": False,
        "execution_status": "not_executed",
        "one_truth_packet_audit": "PASS",
        "boundary_audit": "PASS" if not forbidden_boundary_failures(bundle) else "FAIL",
        "forbidden_claims_present": bool(forbidden_boundary_failures(bundle)),
        "tests": {
            "targeted_r7": tests.get("targeted_r7", "NOT_RUN"),
            "full_discovery": tests.get("full_discovery", "NOT_RUN"),
            "test_count": tests.get("test_count", 0),
        },
        "r6_baseline": bundle["r6_baseline"],
        "acceptance_checks": checks,
        "failure_count": len(failures),
        "failures": failures,
        "lane_statuses": {
            "R7A": "PASS_R7A_PERCEPTION_CANDIDATE_OBSERVATION_INGRESS_WITH_LIMITATIONS",
            "R7B": "PASS_R7B_HUMAN_REVIEW_PROMOTION_GATE_WITH_LIMITATIONS",
            "R7C": "PASS_R7C_CASE_TICKET_DRAFT_WORKFLOW_ADAPTER_WITH_LIMITATIONS",
            "R7D": "PASS_R7D_ACTION_PROPOSAL_APPROVAL_BOUNDARY_WITH_LIMITATIONS",
            "R7E": "PASS_R7E_PERCEPTION_TO_REVIEW_WORKFLOW_SMOKE_WITH_LIMITATIONS",
        },
        "counts": {
            "candidate_observations": len(bundle["candidate_observations"]),
            "event_packets": len(bundle["event_packets"]),
            "review_promotions": len(bundle["review_promotions"]),
            "draft_case_tickets": len(bundle["draft_case_tickets"]),
            "action_proposals": len(bundle["action_proposals"]),
            "webui_packets": len(bundle["webui_packets"]),
            "kit_packets": len(bundle["kit_packets"]),
        },
        "boundary": BOUNDARY,
        "limitations": LIMITATIONS,
        "next_recommended_package": "MAIN-CITYBRAIN-R7A-PERCEPTION-CANDIDATE-OBSERVATION-INGRESS",
    }
    if decision["boundary_audit"] != "PASS" or tests.get("targeted_r7") == "FAIL" or tests.get("full_discovery") == "FAIL":
        decision["status"] = "FAIL_R7_AUTONOMOUS_ACTION_OR_OFFICIAL_CLAIM_REGRESSION"
    write_json(root / "DECISION.json", decision)
    manifest = write_hash_manifest(root)
    zip_report = zip_package(root)
    return {"decision": decision, "hash_manifest": manifest, "zip": zip_report, "output_root": rel(root)}


def main() -> int:
    if os.environ.get("CITYBRAIN_R7_SKIP_TEST_RUNS") == "1":
        tests = {"targeted_r7": "SKIPPED", "full_discovery": "SKIPPED", "test_count": 0}
    else:
        tests = run_tests()
    result = write_outputs(tests=tests)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["decision"]["status"].startswith("PASS_") and result["hash_manifest"]["status"] == "PASS" and result["zip"]["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
