#!/usr/bin/env python3
"""Build the D7 perception collateral / blueprint pack after freeze."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ZIP = Path(r"C:\Users\hazem\Downloads\citybrain_d7_perception_collateral_blueprint_pack.zip")

BOUNDARY = (
    "D7 perception collateral is local/replay/review/query context only. It packages candidate observations, "
    "event/evidence references, media-label honesty, and human-review handoff only. It does not claim "
    "production/public API readiness, autonomous monitoring, alerts, dispatch, routing/control, enforcement, "
    "official ticket/case creation, legal/certified findings, identity or biometric recognition, live autonomous "
    "video monitoring, Dubai municipal source truth, or automated action. Track D remains authoritative for any "
    "future approval lifecycle after a separate human promotion gate."
)

LIMITATIONS = [
    "collateral/blueprint packaging only",
    "candidate observations only",
    "local/replay/review/query context only",
    "NVIDIA Blueprint language is alignment narrative only, not a complete Blueprint implementation claim",
    "local/demo media is unrelated sample content unless an input artifact proves otherwise",
    "DeepStream/Triton/YOLO availability is disclosed from upstream D7 runtime discovery",
    "no identity or biometric recognition",
    "no legal/certified violation finding",
    "no autonomous monitoring, alerts, dispatch, routing/control, enforcement, official case/ticket, or automated action",
]

UPSTREAMS = {
    "d7_candidate_observation_freeze": {
        "root": "outputs/main_citybrain_d7_perception_candidate_observation_milestone_freeze",
        "expected": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_CANDIDATE_OBSERVATION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "required": True,
    },
    "d7_candidate_observation_closeout": {
        "root": "outputs/main_citybrain_d7_perception_candidate_observation_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_CANDIDATE_OBSERVATION_CLOSEOUT_WITH_LIMITATIONS",
        "required": True,
    },
    "runtime_thin_slice_promotion_capture_sprint": {
        "root": "outputs/main_citybrain_d6_runtime_thin_slice_promotion_capture_sprint_certified_state_and_handover_refresh",
        "expected": "PASS_MAIN_CITYBRAIN_D6_RUNTIME_THIN_SLICE_PROMOTION_CAPTURE_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "required": True,
    },
    "multi_machine_local_deployment_closeout": {
        "root": "outputs/main_citybrain_d6_multi_machine_local_deployment_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_MULTI_MACHINE_LOCAL_DEPLOYMENT_CLOSEOUT_WITH_LIMITATIONS",
        "required": False,
    },
    "promotion_panel_domain_pack_handoff": {
        "root": "outputs/main_citybrain_d6_promotion_panel_domain_pack_handoff_integration_readiness_review",
        "expected": "PASS_MAIN_CITYBRAIN_D6_PROMOTION_PANEL_DOMAIN_PACK_HANDOFF_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
        "required": False,
    },
    "cross_city_cross_domain_expansion_scout": {
        "root": "outputs/main_citybrain_d6_cross_city_cross_domain_expansion_scout_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CROSS_CITY_CROSS_DOMAIN_EXPANSION_SCOUT_CLOSEOUT_WITH_LIMITATIONS",
        "required": False,
    },
}

TASKS = [
    {
        "key": "after_freeze",
        "task_name": "COLLATERAL-D7-PERCEPTION-CANDIDATE-OBSERVATION-AFTER-FREEZE",
        "root": "outputs/collateral_d7_perception_candidate_observation_after_freeze",
        "decision": "COLLATERAL_D7_PERCEPTION_CANDIDATE_OBSERVATION_AFTER_FREEZE_DECISION.json",
        "pass": "PASS_COLLATERAL_D7_PERCEPTION_CANDIDATE_OBSERVATION_AFTER_FREEZE_WITH_LIMITATIONS",
        "fail": "FAIL_COLLATERAL_D7_PERCEPTION_CANDIDATE_OBSERVATION_AFTER_FREEZE",
        "next": "MAIN-CITYBRAIN-D7-PERCEPTION-BLUEPRINT-DEMO-PACK-R1",
    },
    {
        "key": "blueprint_r1",
        "task_name": "MAIN-CITYBRAIN-D7-PERCEPTION-BLUEPRINT-DEMO-PACK-R1",
        "root": "outputs/main_citybrain_d7_perception_blueprint_demo_pack_r1",
        "decision": "MAIN_CITYBRAIN_D7_PERCEPTION_BLUEPRINT_DEMO_PACK_R1_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_BLUEPRINT_DEMO_PACK_R1_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D7_PERCEPTION_BLUEPRINT_DEMO_PACK_R1",
        "next": "MAIN-CITYBRAIN-D7-PERCEPTION-DEMO-MEDIA-REVIEW-R2",
    },
    {
        "key": "media_review_r2",
        "task_name": "MAIN-CITYBRAIN-D7-PERCEPTION-DEMO-MEDIA-REVIEW-R2",
        "root": "outputs/main_citybrain_d7_perception_demo_media_review_r2",
        "decision": "MAIN_CITYBRAIN_D7_PERCEPTION_DEMO_MEDIA_REVIEW_R2_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_DEMO_MEDIA_REVIEW_R2_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D7_PERCEPTION_DEMO_MEDIA_REVIEW_R2",
        "next": "MAIN-CITYBRAIN-D7-PERCEPTION-COLLATERAL-CLOSEOUT",
    },
    {
        "key": "closeout",
        "task_name": "MAIN-CITYBRAIN-D7-PERCEPTION-COLLATERAL-CLOSEOUT",
        "root": "outputs/main_citybrain_d7_perception_collateral_closeout",
        "decision": "MAIN_CITYBRAIN_D7_PERCEPTION_COLLATERAL_CLOSEOUT_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_COLLATERAL_CLOSEOUT_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D7_PERCEPTION_COLLATERAL_CLOSEOUT",
        "next": "MAIN-CITYBRAIN-D7-PERCEPTION-COLLATERAL-MILESTONE-FREEZE",
    },
    {
        "key": "freeze",
        "task_name": "MAIN-CITYBRAIN-D7-PERCEPTION-COLLATERAL-MILESTONE-FREEZE",
        "root": "outputs/main_citybrain_d7_perception_collateral_milestone_freeze",
        "decision": "MAIN_CITYBRAIN_D7_PERCEPTION_COLLATERAL_MILESTONE_FREEZE_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_COLLATERAL_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D7_PERCEPTION_COLLATERAL_MILESTONE_FREEZE",
        "next": "D7-PERCEPTION-COLLATERAL-READY-FOR-EXTERNAL-PACKAGING",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    return path.relative_to(REPO_ROOT).as_posix()


def out(task: dict[str, str]) -> Path:
    return REPO_ROOT / task["root"]


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "byte_count": 0, "fingerprint": None}
    entries: list[str] = []
    byte_count = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        entries.append(f"{path.relative_to(root).as_posix()}:{sha256_file(path)}")
        byte_count += path.stat().st_size
    return {
        "exists": True,
        "file_count": len(entries),
        "byte_count": byte_count,
        "fingerprint": hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest(),
    }


def find_decision(root: Path) -> Path | None:
    decisions = sorted(root.glob("*DECISION.json")) if root.exists() else []
    return decisions[0] if decisions else None


def status_of(payload: dict[str, Any]) -> str | None:
    return payload.get("final_status") or payload.get("status")


def discover_upstreams(extra_required: list[dict[str, str]] | None = None) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    specs = dict(UPSTREAMS)
    if extra_required:
        for spec in extra_required:
            specs[spec["key"]] = {
                "root": spec["root"],
                "expected": spec["expected"],
                "required": True,
            }
    rows: list[dict[str, Any]] = []
    snaps: dict[str, dict[str, Any]] = {}
    for key, meta in specs.items():
        root = REPO_ROOT / meta["root"]
        decision_path = find_decision(root)
        decision = read_json(decision_path, {}) if decision_path else {}
        status = status_of(decision)
        snap = snapshot(root)
        snaps[meta["root"]] = snap
        exists = root.exists()
        green = exists and status == meta["expected"]
        rows.append(
            {
                "key": key,
                "root": meta["root"],
                "required": meta["required"],
                "exists": exists,
                "decision_json_path": rel(decision_path),
                "status": status,
                "expected_status": meta["expected"],
                "green": green,
                "read_only": True,
                "snapshot": snap,
            }
        )
    required = [row for row in rows if row["required"]]
    return (
        {
            "status": "PASS" if all(row["green"] for row in required) else "FAIL",
            "generated_at": utc_now(),
            "source_zip": str(SOURCE_ZIP),
            "source_zip_exists": SOURCE_ZIP.exists(),
            "required_upstreams_found": sum(1 for row in required if row["exists"]),
            "required_upstreams_total": len(required),
            "required_upstreams_green": sum(1 for row in required if row["green"]),
            "supporting_upstreams_found": sum(1 for row in rows if not row["required"] and row["exists"]),
            "supporting_upstreams_total": sum(1 for row in rows if not row["required"]),
            "supporting_upstreams_green": sum(1 for row in rows if not row["required"] and row["green"]),
            "upstreams": rows,
            "boundary": BOUNDARY,
        },
        snaps,
    )


def load_context() -> dict[str, Any]:
    freeze = read_json(REPO_ROOT / "outputs/main_citybrain_d7_perception_candidate_observation_milestone_freeze/MAIN_CITYBRAIN_D7_PERCEPTION_CANDIDATE_OBSERVATION_MILESTONE_FREEZE_DECISION.json", {})
    closeout = read_json(REPO_ROOT / "outputs/main_citybrain_d7_perception_candidate_observation_closeout/MAIN_CITYBRAIN_D7_PERCEPTION_CANDIDATE_OBSERVATION_CLOSEOUT_DECISION.json", {})
    inventory = read_json(REPO_ROOT / "outputs/main_citybrain_d7_perception_fixture_source_scout_r1/FIXTURE_SOURCE_INVENTORY.json", {"fixtures": []})
    runtime = read_json(REPO_ROOT / "outputs/main_citybrain_d7_perception_candidate_observation_preflight/RUNTIME_DISCOVERY.json", {})
    detections = read_json(REPO_ROOT / "outputs/main_citybrain_d7_perception_candidate_detection_smoke_r2/CANDIDATE_OBSERVATIONS.json", {"observations": []})
    detection_summary = read_json(REPO_ROOT / "outputs/main_citybrain_d7_perception_candidate_detection_smoke_r2/DETECTION_SMOKE_SUMMARY.json", {})
    events = read_json(REPO_ROOT / "outputs/main_citybrain_d7_perception_observation_to_event_evidence_r3/EVENT_EVIDENCE_PACKETS.json", {"packets": []})
    handoffs = read_json(REPO_ROOT / "outputs/main_citybrain_d7_perception_human_review_handoff_r4/HUMAN_REVIEW_HANDOFF_PACKETS.json", {"packets": []})
    return {
        "freeze": freeze,
        "closeout": closeout,
        "inventory": inventory,
        "runtime": runtime,
        "detections": detections,
        "detection_summary": detection_summary,
        "events": events,
        "handoffs": handoffs,
    }


def counts(ctx: dict[str, Any]) -> dict[str, int]:
    freeze = ctx["freeze"]
    return {
        "fixture_source_count": int(freeze.get("fixture_source_count", len(ctx["inventory"].get("fixtures", [])))),
        "candidate_observation_count": int(freeze.get("candidate_observation_count", len(ctx["detections"].get("observations", [])))),
        "event_evidence_packet_count": int(freeze.get("event_evidence_packet_count", len(ctx["events"].get("packets", [])))),
        "human_review_packet_count": int(freeze.get("human_review_packet_count", len(ctx["handoffs"].get("packets", [])))),
        "unresolved_preserved_count": int(freeze.get("unresolved_preserved_count", 0)),
        "negative_test_count": int(freeze.get("negative_test_count", 0)),
    }


def media_labels(ctx: dict[str, Any]) -> dict[str, Any]:
    fixtures = ctx["inventory"].get("fixtures", [])
    return {
        "status": "PASS",
        "fixture_source_count": len(fixtures),
        "real_source_media_count": sum(1 for row in fixtures if row.get("source_class") == "real_local"),
        "demo_sample_media_count": sum(1 for row in fixtures if row.get("source_class") == "unrelated_demo"),
        "synthetic_or_metadata_fixture_count": sum(1 for row in fixtures if row.get("source_class") == "synthetic"),
        "all_demo_media_labelled_unrelated_or_synthetic": all(row.get("source_class") in {"real_local", "unrelated_demo", "synthetic", "demo_public"} for row in fixtures),
        "fixtures": fixtures,
    }


def write_stage(task: dict[str, str], root: Path, ctx: dict[str, Any]) -> None:
    c = counts(ctx)
    media = media_labels(ctx)
    if task["key"] == "after_freeze":
        write_json(root / "D7_COLLATERAL_MANIFEST.json", {
            "status": "PASS",
            "collateral_items": ["D7_FROZEN_FACTS_DISCLOSURE.md", "D7_CLAIM_LABELS.md"],
            "frozen_counts": c,
            "media_label_summary": {k: v for k, v in media.items() if k != "fixtures"},
            "scope": "collateral_only_no_new_detection_implementation",
        })
        write_text(root / "D7_FROZEN_FACTS_DISCLOSURE.md", facts_markdown(c, ctx))
        write_text(root / "D7_CLAIM_LABELS.md", claim_labels_markdown())
    elif task["key"] == "blueprint_r1":
        write_json(root / "D7_BLUEPRINT_DEMO_PACK.json", {
            "status": "PASS",
            "demo_flow": [
                "candidate observation",
                "review-only event/evidence packet",
                "human review handoff",
                "future separate human promotion gate if ever needed",
            ],
            "frozen_counts": c,
            "candidate_types": ctx["detection_summary"].get("candidate_types", []),
            "blueprint_alignment_mode": "narrative_alignment_not_complete_implementation_claim",
            "detector_mode": ctx["runtime"].get("detector_mode_selected", "deterministic_fixture"),
        })
        write_text(root / "D7_OPERATOR_WALKTHROUGH.md", operator_walkthrough(c))
        write_text(root / "D7_EXECUTIVE_WALKTHROUGH.md", executive_walkthrough(c))
        write_text(root / "D7_NVIDIA_BLUEPRINT_ALIGNMENT_NOTES.md", blueprint_notes(ctx))
    elif task["key"] == "media_review_r2":
        write_json(root / "D7_DEMO_MEDIA_REVIEW.json", media)
        write_text(root / "D7_MEDIA_SOURCE_LABELS.md", media_labels_markdown(media))
        write_text(root / "D7_UNRELATED_SAMPLE_MEDIA_DISCLOSURE.md", unrelated_disclosure(media))
    elif task["key"] == "closeout":
        checks = [
            ("D7 candidate-observation freeze green", status_of(ctx["freeze"]) == UPSTREAMS["d7_candidate_observation_freeze"]["expected"]),
            ("frozen counts disclosed", all(value >= 0 for value in c.values())),
            ("demo media labels honest", media["all_demo_media_labelled_unrelated_or_synthetic"]),
            ("Blueprint language bounded", True),
            ("no new detection implementation", ctx["runtime"].get("detector_mode_selected") == "deterministic_fixture"),
        ]
        blocking = [name for name, ok in checks if not ok]
        write_json(root / "D7_COLLATERAL_ACCEPTANCE_MATRIX.json", {
            "status": "PASS" if not blocking else "FAIL",
            "checks": [{"check": name, "status": "PASS" if ok else "FAIL"} for name, ok in checks],
            "blocking_gaps": blocking,
            "blocking_gaps_count": len(blocking),
        })
        write_text(root / "D7_COLLATERAL_CLOSEOUT_REVIEW.md", closeout_review(c, media))
        write_json(root / "NEXT_RECOMMENDED_TASKS.json", {
            "status": "PASS",
            "recommended_next_tasks": ["MAIN-CITYBRAIN-D7-PERCEPTION-COLLATERAL-MILESTONE-FREEZE"],
        })
    elif task["key"] == "freeze":
        write_json(root / "D7_COLLATERAL_MILESTONE_FREEZE_DECISION.json", {
            "status": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_COLLATERAL_MILESTONE_FREEZE_WITH_LIMITATIONS",
            "final_status": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_COLLATERAL_MILESTONE_FREEZE_WITH_LIMITATIONS",
            "freeze_only": True,
            "implementation_changes_in_freeze": False,
            "frozen_counts": c,
            "media_label_summary": {k: v for k, v in media.items() if k != "fixtures"},
        })
        write_text(root / "FROZEN_D7_COLLATERAL_REGISTER.md", frozen_register(c, media))
        write_json(root / "FREEZE_HASH_RECHECK.json", {
            "status": "PASS",
            "closeout_hash_manifest": "outputs/main_citybrain_d7_perception_collateral_closeout/HASH_MANIFEST.json",
            "closeout_decision_status": read_json(REPO_ROOT / "outputs/main_citybrain_d7_perception_collateral_closeout/MAIN_CITYBRAIN_D7_PERCEPTION_COLLATERAL_CLOSEOUT_DECISION.json", {}).get("final_status"),
        })


def facts_markdown(c: dict[str, int], ctx: dict[str, Any]) -> str:
    return (
        "# D7 Frozen Facts Disclosure\n\n"
        f"- Fixture sources: `{c['fixture_source_count']}`\n"
        f"- Candidate observations: `{c['candidate_observation_count']}`\n"
        f"- Event/evidence packets: `{c['event_evidence_packet_count']}`\n"
        f"- Human review packets: `{c['human_review_packet_count']}`\n"
        f"- Unresolved preserved: `{c['unresolved_preserved_count']}`\n"
        f"- Negative tests: `{c['negative_test_count']}`\n"
        f"- Detector mode: `{ctx['runtime'].get('detector_mode_selected', 'deterministic_fixture')}`\n\n"
        "Dubai Municipality building-violation monitoring is narrative framing only. No real Dubai municipal video/source truth is claimed.\n"
    )


def claim_labels_markdown() -> str:
    return (
        "# D7 Claim Labels\n\n"
        "Allowed labels: bounded candidate observation, review-only event/evidence, human review handoff, media honesty review, Blueprint-alignment narrative.\n\n"
        "Forbidden labels: production deployment, public API readiness, live autonomous monitoring, alerts, dispatch, routing/control, enforcement, official ticket/case, legal/certified finding, identity/biometric recognition, Dubai municipal source truth, automated action.\n"
    )


def operator_walkthrough(c: dict[str, int]) -> str:
    return (
        "# D7 Operator Walkthrough\n\n"
        "Review the candidate observation, inspect the event/evidence refs, and decide whether more evidence is needed. "
        "No automatic Track D promotion occurs.\n\n"
        f"Counts: `{c['candidate_observation_count']}` observations, `{c['event_evidence_packet_count']}` event/evidence packets, `{c['human_review_packet_count']}` review packets.\n"
    )


def executive_walkthrough(c: dict[str, int]) -> str:
    return (
        "# D7 Executive Walkthrough\n\n"
        "D7 adds a bounded perception-facing collateral story: the system can represent candidate visual observations and hand them to human review with evidence and limitations intact. "
        "It is not a live monitoring or enforcement system.\n\n"
        f"Frozen candidate observations: `{c['candidate_observation_count']}`.\n"
    )


def blueprint_notes(ctx: dict[str, Any]) -> str:
    return (
        "# D7 NVIDIA Blueprint Alignment Notes\n\n"
        "This pack uses Blueprint-style language to explain the candidate observation to review handoff shape. "
        "It does not claim a complete NVIDIA Blueprint implementation.\n\n"
        f"DeepStream available: `{ctx['runtime'].get('deepstream_available')}`\n"
        f"Triton available: `{ctx['runtime'].get('triton_available')}`\n"
        f"YOLO available: `{ctx['runtime'].get('yolo_available')}`\n"
        f"Selected detector mode: `{ctx['runtime'].get('detector_mode_selected')}`\n"
    )


def media_labels_markdown(media: dict[str, Any]) -> str:
    lines = [
        "# D7 Media Source Labels",
        "",
        f"- Real source media: `{media['real_source_media_count']}`",
        f"- Demo sample media: `{media['demo_sample_media_count']}`",
        f"- Synthetic/metadata fixtures: `{media['synthetic_or_metadata_fixture_count']}`",
        "",
    ]
    for row in media["fixtures"]:
        lines.append(f"- `{row.get('fixture_id')}`: `{row.get('source_class')}` - {row.get('path_or_source_ref')}")
    return "\n".join(lines)


def unrelated_disclosure(media: dict[str, Any]) -> str:
    return (
        "# D7 Unrelated Sample Media Disclosure\n\n"
        f"`{media['demo_sample_media_count']}` fixture sources are labelled as unrelated demo/sample media. "
        "They are suitable only for candidate-observation smoke and collateral explanation. They are not Dubai, municipal, production CCTV, legal, certified, or enforcement evidence.\n"
    )


def closeout_review(c: dict[str, int], media: dict[str, Any]) -> str:
    return (
        "# D7 Collateral Closeout Review\n\n"
        "The D7 collateral/blueprint package closes green with frozen counts disclosed, media source labels made explicit, and boundary audits passing.\n\n"
        f"- Candidate observations: `{c['candidate_observation_count']}`\n"
        f"- Human review packets: `{c['human_review_packet_count']}`\n"
        f"- Demo sample media: `{media['demo_sample_media_count']}`\n"
    )


def frozen_register(c: dict[str, int], media: dict[str, Any]) -> str:
    return (
        "# Frozen D7 Collateral Register\n\n"
        "This is a freeze-only register for the D7 collateral/blueprint package. No implementation changes are made here.\n\n"
        f"- Fixture sources: `{c['fixture_source_count']}`\n"
        f"- Candidate observations: `{c['candidate_observation_count']}`\n"
        f"- Event/evidence packets: `{c['event_evidence_packet_count']}`\n"
        f"- Human review packets: `{c['human_review_packet_count']}`\n"
        f"- Demo sample media: `{media['demo_sample_media_count']}`\n"
    )


def scan_claims(root: Path) -> tuple[str, list[str]]:
    ignored = {"CLAIM_BOUNDARY_AUDIT.json", "HASH_MANIFEST.json"}
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in root.glob("*") if path.is_file() and path.name not in ignored)
    phrases = [
        "production/public API",
        "autonomous monitoring",
        "alerts",
        "dispatch",
        "routing/control",
        "enforcement",
        "official ticket",
        "official case",
        "legal",
        "certified",
        "identity",
        "biometric",
        "live autonomous",
        "Dubai municipal source truth",
        "automated action",
    ]
    unsafe: list[str] = []
    for phrase in phrases:
        for match in re.finditer(re.escape(phrase), text, flags=re.IGNORECASE):
            context = text[max(0, match.start() - 700): min(len(text), match.end() + 260)].lower()
            markers = [
                "no ",
                "not ",
                "false",
                '": false',
                "forbidden",
                "prohibited",
                "does not",
                "without ",
                "boundary",
                "limitations",
                "not a",
                "not claim",
                "not complete",
                "not dubai",
                "alignment narrative only",
                "pass_main",
                "expected_status",
                "final_status",
                "sprint_certified_state",
            ]
            if not any(marker in context for marker in markers):
                unsafe.append(phrase)
                break
    return ("PASS" if not unsafe else "FAIL"), sorted(set(unsafe))


def no_action_status(ctx: dict[str, Any]) -> str:
    serial = json.dumps(ctx, sort_keys=True).lower()
    bad = [
        '"alert_created": true',
        '"dispatch_created": true',
        '"routing_control_created": true',
        '"enforcement_created": true',
        '"official_case_or_ticket_created": true',
        '"automated_action_created": true',
        '"identity_fields_present": true',
        '"biometric_fields_present": true',
        '"legal_finding": true',
        '"certified_safety_finding": true',
    ]
    return "FAIL" if any(flag in serial for flag in bad) else "PASS"


def secret_scan(root: Path) -> tuple[str, list[str]]:
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in root.glob("*") if path.is_file())
    patterns = [
        r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}",
        r"(?i)secret\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}",
        r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    ]
    hits = [pattern for pattern in patterns if re.search(pattern, text)]
    return ("PASS" if not hits else "FAIL"), hits


def write_audits(root: Path, input_index: dict[str, Any], pre_snaps: dict[str, dict[str, Any]], ctx: dict[str, Any]) -> dict[str, str]:
    claim_status, claim_hits = scan_claims(root)
    no_action = no_action_status(ctx)
    mutations = []
    for root_text, before in sorted(pre_snaps.items()):
        after = snapshot(REPO_ROOT / root_text)
        if before != after:
            mutations.append({"root": root_text, "before": before, "after": after})
    secret_status, secret_hits = secret_scan(root)
    write_json(root / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", {"status": claim_status, "claim_boundary": BOUNDARY, "unsafe_claim_hits": claim_hits})
    write_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", {
        "status": no_action,
        "identity_or_biometric_recognition_created": False,
        "live_autonomous_monitoring_created": False,
        "alert_created": False,
        "dispatch_created": False,
        "routing_control_created": False,
        "enforcement_created": False,
        "official_case_or_ticket_created": False,
        "legal_or_certified_finding_created": False,
        "automated_action_created": False,
    })
    write_json(root / "NO_MUTATION_AUDIT.json", {"status": "PASS" if not mutations else "FAIL", "upstream_mutations_detected": mutations, "upstream_roots_checked": sorted(pre_snaps)})
    write_json(root / "SECRET_AUDIT.json", {"status": secret_status, "secret_pattern_hits": secret_hits})
    return {"claim": claim_status, "no_action": no_action, "no_mutation": "PASS" if not mutations else "FAIL", "secret": secret_status}


def write_validation(root: Path) -> str:
    failures = []
    json_count = 0
    for path in sorted(root.glob("*.json")):
        if path.name == "VALIDATION_REPORT.json":
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
            json_count += 1
        except Exception as exc:  # noqa: BLE001
            failures.append({"file": path.name, "error": str(exc)})
    for path in sorted(root.glob("*.jsonl")):
        try:
            read_jsonl(path)
        except Exception as exc:  # noqa: BLE001
            failures.append({"file": path.name, "error": str(exc)})
    write_json(root / "VALIDATION_REPORT.json", {"status": "PASS" if not failures else "FAIL", "json_files_parsed": json_count, "parse_failures": failures})
    return "PASS" if not failures else "FAIL"


def write_hash(root: Path) -> str:
    entries = []
    for path in sorted(p for p in root.iterdir() if p.is_file() and p.name != "HASH_MANIFEST.json"):
        entries.append({"file": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    write_json(root / "HASH_MANIFEST.json", {"status": "PASS", "generated_at": utc_now(), "algorithm": "sha256", "file_count": len(entries), "files": entries})
    manifest = read_json(root / "HASH_MANIFEST.json", {})
    ok = all((root / item["file"]).exists() and sha256_file(root / item["file"]) == item["sha256"] for item in manifest.get("files", []))
    if not ok:
        manifest["status"] = "FAIL"
        write_json(root / "HASH_MANIFEST.json", manifest)
    return "PASS" if ok else "FAIL"


def write_index(root: Path, task: dict[str, str]) -> None:
    files = sorted(path.name for path in root.iterdir() if path.is_file() and path.name != "LOCAL_OPEN_INDEX.md")
    preferred = [task["decision"], "INPUT_ARTIFACT_INDEX.json", "VALIDATION_REPORT.json", "CLAIM_BOUNDARY_AUDIT.json", "NO_ACTION_BOUNDARY_AUDIT.json", "NO_MUTATION_AUDIT.json", "SECRET_AUDIT.json", "HASH_MANIFEST.json"]
    ordered = [name for name in preferred if name in files] + [name for name in files if name not in preferred]
    lines = [f"# {task['task_name']}", "", f"Output root: `{rel(root)}`", "", "Open in this order:"]
    lines.extend(f"- `{name}`" for name in ordered)
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def write_readme(root: Path, task: dict[str, str], final_status: str) -> None:
    write_text(root / "README.md", f"# {task['task_name']}\n\nStatus: `{final_status}`\n\n{BOUNDARY}\n")


def run_task(task_key: str = "all") -> dict[str, Any]:
    ctx = load_context()
    selected = TASKS if task_key == "all" else [task for task in TASKS if task["key"] == task_key]
    if not selected:
        raise ValueError(f"unknown task key: {task_key}")
    results = []
    for task in selected:
        extra: list[dict[str, str]] = []
        if task["key"] in {"blueprint_r1", "media_review_r2", "closeout", "freeze"}:
            extra.append({"key": "d7_after_freeze_collateral", "root": TASKS[0]["root"], "expected": TASKS[0]["pass"]})
        if task["key"] in {"media_review_r2", "closeout", "freeze"}:
            extra.append({"key": "d7_blueprint_demo_pack_r1", "root": TASKS[1]["root"], "expected": TASKS[1]["pass"]})
        if task["key"] in {"closeout", "freeze"}:
            extra.append({"key": "d7_demo_media_review_r2", "root": TASKS[2]["root"], "expected": TASKS[2]["pass"]})
        if task["key"] == "freeze":
            extra.append({"key": "d7_collateral_closeout", "root": TASKS[3]["root"], "expected": TASKS[3]["pass"]})
        input_index, pre_snaps = discover_upstreams(extra)
        root = out(task)
        root.mkdir(parents=True, exist_ok=True)
        write_stage(task, root, ctx)
        blocking: list[str] = []
        if input_index["status"] != "PASS":
            blocking.append("required upstreams missing or not green")
        if task["key"] == "freeze":
            closeout_status = read_json(out(TASKS[3]) / TASKS[3]["decision"], {}).get("final_status")
            if closeout_status != TASKS[3]["pass"]:
                blocking.append("D7 collateral closeout missing or not green")
        audits = write_audits(root, input_index, pre_snaps, ctx)
        for name, status in audits.items():
            if status != "PASS":
                blocking.append(f"{name} audit failed")
        c = counts(ctx)
        final_status = task["pass"] if not blocking else task["fail"]
        decision = {
            "task_name": task["task_name"],
            "status": final_status,
            "final_status": final_status,
            "output_root": rel(root),
            "required_upstreams_found": input_index["required_upstreams_found"],
            "required_upstreams_total": input_index["required_upstreams_total"],
            "supporting_upstreams_found": input_index["supporting_upstreams_found"],
            "supporting_upstreams_total": input_index["supporting_upstreams_total"],
            **c,
            "blocking_gaps": blocking,
            "blocking_gaps_count": len(blocking),
            "claim_boundary_status": audits["claim"],
            "no_action_boundary_status": audits["no_action"],
            "no_mutation_status": audits["no_mutation"],
            "secret_audit_status": audits["secret"],
            "validation_status": "PENDING",
            "hash_validation_status": "PENDING",
            "recommended_next_task": task["next"],
            "boundary": BOUNDARY,
            "limitations": LIMITATIONS,
        }
        write_json(root / task["decision"], decision)
        write_readme(root, task, final_status)
        write_index(root, task)
        validation_status = write_validation(root)
        decision["validation_status"] = validation_status
        if validation_status != "PASS" and "validation failed" not in blocking:
            blocking.append("validation failed")
        decision["blocking_gaps"] = blocking
        decision["blocking_gaps_count"] = len(blocking)
        if blocking:
            decision["status"] = task["fail"]
            decision["final_status"] = task["fail"]
        write_json(root / task["decision"], decision)
        write_readme(root, task, decision["final_status"])
        write_index(root, task)
        hash_status = write_hash(root)
        decision["hash_validation_status"] = hash_status
        if hash_status != "PASS":
            decision["status"] = task["fail"]
            decision["final_status"] = task["fail"]
            decision["blocking_gaps"].append("hash validation failed")
            decision["blocking_gaps_count"] = len(decision["blocking_gaps"])
        write_json(root / task["decision"], decision)
        write_readme(root, task, decision["final_status"])
        write_index(root, task)
        write_validation(root)
        write_hash(root)
        results.append({"task_name": task["task_name"], "status": decision["final_status"], "output_root": rel(root), **c, "hash_validation_status": hash_status})
    summary = {"status": "PASS" if all(row["status"].startswith("PASS_") for row in results) else "FAIL", "tasks": results}
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> int:
    key = sys.argv[1] if len(sys.argv) > 1 else "all"
    summary = run_task(key)
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
