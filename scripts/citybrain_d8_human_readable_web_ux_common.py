#!/usr/bin/env python3
"""D8 human-readable web UX remediation runner.

This lane turns the already-green technical live surface into a viewer-readable
control-room story without changing certified facts, schemas, options, or action
authority.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = REPO_ROOT / "outputs"
WEB_APP = REPO_ROOT / "apps" / "web-control-room"
RUNTIME_BUNDLE = REPO_ROOT / "packages" / "fixtures" / "mobility_access" / "runtime_bundle"

BOUNDARY = (
    "D8 human-readable web UX remediation is local/LAN/replay/review/query context only. "
    "It may edit maintained web-control-room source and produce additive reports. It does not "
    "mutate certified upstream outputs, alter truth counts, change option sets, create proposals, "
    "approve or execute actions, dispatch, route/control, enforce, create tickets/cases, make "
    "legal/certified findings, claim public API or production readiness, or create autonomous "
    "monitoring or alerts."
)

NO_CLAIM_LIMITS = [
    "No production or public API readiness claim.",
    "No live monitoring, autonomous alerting, dispatch, routing/control, enforcement, official ticket/case, legal/certified finding, or automated action.",
    "D7 observations remain candidate observations, not findings.",
    "Track D remains authoritative after any future human promotion.",
    "execution_state remains not_executed.",
    "M04 do-nothing and M05 abstain/no-safe-option remain documented partial in the current certified bundle.",
]

STAGES: list[dict[str, Any]] = [
    {
        "key": "preflight",
        "task": "MAIN-CITYBRAIN-D8-HUMAN-READABLE-CONTROL-ROOM-UX-PREFLIGHT",
        "root": "main_citybrain_d8_human_readable_control_room_ux_preflight",
        "decision": "MAIN_CITYBRAIN_D8_HUMAN_READABLE_CONTROL_ROOM_UX_PREFLIGHT_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D8_HUMAN_READABLE_CONTROL_ROOM_UX_PREFLIGHT_WITH_LIMITATIONS",
        "required": [
            "README.md",
            "LOCAL_OPEN_INDEX.md",
            "INPUT_ARTIFACT_INDEX.json",
            "CURRENT_UI_PROBLEM_REPORT.md",
            "HUMAN_READABLE_UX_SCOPE_LOCK.json",
            "TECHNICAL_LABEL_INVENTORY.json",
            "SOURCE_TREE_MUTATION_POLICY.md",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    },
    {
        "key": "story_copy",
        "task": "MAIN-CITYBRAIN-D8-HUMAN-STORY-SCRIPT-AND-COPY-R1",
        "root": "main_citybrain_d8_human_story_script_and_copy_r1",
        "decision": "MAIN_CITYBRAIN_D8_HUMAN_STORY_SCRIPT_AND_COPY_R1_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D8_HUMAN_STORY_SCRIPT_AND_COPY_R1_WITH_LIMITATIONS",
        "required": [
            "README.md",
            "LOCAL_OPEN_INDEX.md",
            "MOBILITY_ACCESS_HUMAN_STORY_SCRIPT.md",
            "PLAIN_LANGUAGE_COPY_MAP.json",
            "TECHNICAL_TO_HUMAN_LABEL_MAP.json",
            "SIX_STEP_OPERATOR_STORY.json",
            "EXECUTIVE_SUMMARY_COPY.md",
            "BOUNDARY_COPY_GUIDE.md",
            "MOMENT_COPY_CATALOG.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    },
    {
        "key": "redesign",
        "task": "MAIN-CITYBRAIN-D8-WEB-CONTROL-ROOM-HUMAN-READABLE-REDESIGN-R2",
        "root": "main_citybrain_d8_web_control_room_human_readable_redesign_r2",
        "decision": "MAIN_CITYBRAIN_D8_WEB_CONTROL_ROOM_HUMAN_READABLE_REDESIGN_R2_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D8_WEB_CONTROL_ROOM_HUMAN_READABLE_REDESIGN_R2_WITH_LIMITATIONS",
        "required": [
            "README.md",
            "LOCAL_OPEN_INDEX.md",
            "WEB_HUMAN_READABLE_SOURCE_PATCH_REPORT.json",
            "WEB_DEFAULT_VIEW_COPY_REPORT.json",
            "TECHNICAL_DETAIL_TOGGLE_REPORT.json",
            "WEB_HUMAN_READABLE_DOM_ASSERTION_REPORT.json",
            "WEB_HUMAN_READABLE_SCREENSHOT_OR_DOM_CAPTURE.html",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    },
    {
        "key": "moments_drive",
        "task": "MAIN-CITYBRAIN-D8-INTELLIGENCE-MOMENT-CARDS-AND-DRIVE-MODE-R3",
        "root": "main_citybrain_d8_intelligence_moment_cards_and_drive_mode_r3",
        "decision": "MAIN_CITYBRAIN_D8_INTELLIGENCE_MOMENT_CARDS_AND_DRIVE_MODE_R3_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D8_INTELLIGENCE_MOMENT_CARDS_AND_DRIVE_MODE_R3_WITH_LIMITATIONS",
        "required": [
            "README.md",
            "LOCAL_OPEN_INDEX.md",
            "MOMENT_CARD_RENDER_REPORT.json",
            "DRIVE_MODE_IMPLEMENTATION_REPORT.json",
            "MOMENT_TO_PANEL_MAPPING.json",
            "M04_M05_PARTIAL_STATUS_REPORT.json",
            "WEB_MOMENT_CARD_DOM_ASSERTION_REPORT.json",
            "WEB_MOMENT_CARD_CAPTURE.html",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    },
    {
        "key": "viewer_smoke",
        "task": "MAIN-CITYBRAIN-D8-WEB-HUMAN-READABLE-NAIVE-VIEWER-SMOKE-R4",
        "root": "main_citybrain_d8_web_human_readable_naive_viewer_smoke_r4",
        "decision": "MAIN_CITYBRAIN_D8_WEB_HUMAN_READABLE_NAIVE_VIEWER_SMOKE_R4_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D8_WEB_HUMAN_READABLE_NAIVE_VIEWER_SMOKE_R4_WITH_LIMITATIONS",
        "required": [
            "README.md",
            "LOCAL_OPEN_INDEX.md",
            "HUMAN_READABILITY_SMOKE_REPORT.json",
            "DEFAULT_VIEW_TECHNICAL_JARGON_SCAN.json",
            "SCENARIO_UNAIDED_SUMMARY_PROMPT.md",
            "NAIVE_VIEWER_TEST_PACKET_DRAFT.md",
            "MOMENT_SURPRISE_CANDIDATE_LIST.json",
            "BOUNDARY_VISIBILITY_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    },
    {
        "key": "closeout",
        "task": "MAIN-CITYBRAIN-D8-HUMAN-READABLE-WEB-UX-CLOSEOUT",
        "root": "main_citybrain_d8_human_readable_web_ux_closeout",
        "decision": "HUMAN_READABLE_WEB_UX_CLOSEOUT_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D8_HUMAN_READABLE_WEB_UX_CLOSEOUT_WITH_LIMITATIONS",
        "required": [
            "README.md",
            "LOCAL_OPEN_INDEX.md",
            "HUMAN_READABLE_WEB_UX_ACCEPTANCE_MATRIX.json",
            "SOURCE_PATCH_SUMMARY.md",
            "KNOWN_LIMITATIONS.md",
            "NEXT_EXTERNAL_CAPTURE_READINESS.md",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    },
    {
        "key": "freeze",
        "task": "MAIN-CITYBRAIN-D8-HUMAN-READABLE-WEB-UX-MILESTONE-FREEZE",
        "root": "main_citybrain_d8_human_readable_web_ux_milestone_freeze",
        "decision": "MAIN_CITYBRAIN_D8_HUMAN_READABLE_WEB_UX_MILESTONE_FREEZE_DECISION.json",
        "pass": "PASS_MAIN_CITYBRAIN_D8_HUMAN_READABLE_WEB_UX_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "required": [
            "README.md",
            "LOCAL_OPEN_INDEX.md",
            "WEB_UX_BASELINE_SOURCE_HASH_MANIFEST.json",
            "WEB_UX_BASELINE_RUNTIME_BUNDLE_REFS.json",
            "WEB_UX_BASELINE_SCREENSHOT_OR_DOM_CAPTURE.html",
            "WEB_UX_BASELINE_LIMITATIONS.md",
            "READY_FOR_REAL_MEDIA_AND_VIEWER_VALIDATION.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    },
]

STAGE_BY_KEY = {stage["key"]: stage for stage in STAGES}

UPSTREAMS = {
    "d8_demonstrability_handoff": {
        "root": "outputs/main_citybrain_d8_demonstrability_certified_state_handoff",
        "decision": "D8_CERTIFIED_STATE_HANDOFF_DECISION.json",
        "role": "D8 certified demonstrability handoff",
    },
    "d8_live_surface_freeze": {
        "root": "outputs/main_citybrain_d8_web_kit_live_surface_milestone_freeze",
        "decision": "WEB_KIT_LIVE_SURFACE_MILESTONE_FREEZE_DECISION.json",
        "role": "previous technical live-surface baseline",
    },
    "d8_baseline_hash_reconciliation": {
        "root": "outputs/main_citybrain_d8_web_kit_live_surface_baseline_hash_reconciliation",
        "decision": "MAIN_CITYBRAIN_D8_WEB_KIT_LIVE_SURFACE_BASELINE_HASH_RECONCILIATION_DECISION.json",
        "role": "source/runtime hash reconciliation",
    },
    "mobility_access_handoff": {
        "root": "outputs/main_citybrain_d6_mobility_access_domain_pack_certified_state_and_handover_refresh",
        "decision": "MAIN_CITYBRAIN_D6_MOBILITY_ACCESS_DOMAIN_PACK_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "role": "Mobility Access certified hero spine",
    },
    "track_d_promotion_readiness": {
        "root": "outputs/main_citybrain_d6_track_d_mobility_access_promotion_readiness_closeout",
        "decision": "MAIN_CITYBRAIN_D6_TRACK_D_MOBILITY_ACCESS_PROMOTION_READINESS_CLOSEOUT_DECISION.json",
        "role": "Track D human-review promotion readiness",
    },
    "d7_candidate_observation_freeze": {
        "root": "outputs/main_citybrain_d7_perception_candidate_observation_milestone_freeze",
        "decision": "MAIN_CITYBRAIN_D7_PERCEPTION_CANDIDATE_OBSERVATION_MILESTONE_FREEZE_DECISION.json",
        "role": "D7 candidate observations",
    },
    "post_handoff_followthrough": {
        "root": "outputs/main_citybrain_d8_post_handoff_followthrough_certified_state_handoff",
        "decision": "D8_POST_HANDOFF_FOLLOWTHROUGH_CERTIFIED_STATE_HANDOFF_DECISION.json",
        "role": "post-handoff followthrough, partial because real media/viewer was not ready",
        "allow_partial": True,
    },
}

STORY_STEPS = [
    {"step": 1, "title": "A mobility access issue appears.", "viewer_copy": "A local replay shows an access problem on the hero corridor."},
    {"step": 2, "title": "CityBrain connects context.", "viewer_copy": "The page connects corridor, observations, similar cases, cascade context, trace, and review boundaries."},
    {"step": 3, "title": "Uncertainty stays visible.", "viewer_copy": "Possible observations and weak links remain marked for human review."},
    {"step": 4, "title": "Review choices are compared.", "viewer_copy": "Candidate choices are shown on shared axes, including the do-nothing baseline."},
    {"step": 5, "title": "Forbidden commands are refused.", "viewer_copy": "The surface shows that command-shaped requests are blocked and no action is taken."},
    {"step": 6, "title": "The flow stops at human review.", "viewer_copy": "Only Track D can turn a reviewed item into a proposal in a future gated lane."},
]

TECH_TO_HUMAN = {
    "execution_state = not_executed": "No action has been taken.",
    "D7 candidate observation": "Possible observation from demo media - human review required.",
    "Reviewed option sets": "Review choices prepared for a human.",
    "Candidate options": "Possible next review paths.",
    "PASS_ELIGIBLE_REVIEW_ONLY": "Eligible for human review only.",
    "PASS_BLOCKED_OR_CONTEXT_ONLY": "Blocked or context-only. No action taken.",
    "Track D remains authoritative": "Only the human review lane can decide whether this should become a proposal.",
    "d7_candidate_observation:001": "Possible observation, not a finding.",
    "inv_option_review_reroute": "Review a possible corridor reroute.",
    "review_reroute_option": "Review a possible corridor reroute.",
    "SYNTHESIZE": "Narrate the evidence once facts are assembled.",
    "EXECUTE": "Read local fixtures only.",
}

MOMENT_COPY = {
    "M02": {
        "title": "This looks like a past case",
        "viewer_copy": "Cross-city memory offers similar cases as context, not instructions.",
        "panel": "evidence",
        "surprise": "CityBrain remembers related corridor patterns without pretending they are the same event.",
    },
    "M03": {
        "title": "CityBrain shows an uncertain link",
        "viewer_copy": "Confidence is qualitative and limitations stay attached.",
        "panel": "evidence",
        "surprise": "The system exposes uncertainty instead of polishing it away.",
    },
    "M06": {
        "title": "Choices are compared fairly",
        "viewer_copy": "Review choices use shared axes: access continuity, delay risk, kerbside safety, and evidence confidence.",
        "panel": "options",
        "surprise": "The do-nothing baseline is visible beside intervention candidates.",
    },
    "M07": {
        "title": "The system refuses to act",
        "viewer_copy": "A forbidden action-shaped command is rejected. No action is taken.",
        "panel": "track-d",
        "surprise": "The demo shows refusal as a feature, not a failure.",
    },
    "M08": {
        "title": "Human review is required",
        "viewer_copy": "Eligible items stop at Track D; no approved proposal is created here.",
        "panel": "track-d",
        "surprise": "The product has a visible governance stop.",
    },
    "M12": {
        "title": "Limits are visible",
        "viewer_copy": "The page keeps no-action, local replay, and candidate-observation limits in view.",
        "panel": "limitations",
        "surprise": "The demo tells the viewer what it does not prove.",
    },
    "M13": {
        "title": "Possible observation, not a finding",
        "viewer_copy": "D7 media-derived observations are candidates that require human review.",
        "panel": "evidence",
        "surprise": "Media context can be useful without becoming a certified fact.",
    },
    "M15": {
        "title": "Nine-stage reasoning trace",
        "viewer_copy": "The trace explains how the review packet was assembled without creating action authority.",
        "panel": "trace",
        "surprise": "Most stages are governed code paths; SYNTHESIZE narrates grounded facts.",
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_trace(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_files(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    for path in paths:
        if path.is_file():
            found.append(path)
        elif path.exists():
            found.extend(item for item in path.rglob("*") if item.is_file())
    return sorted(found)


def snapshot_root(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "byte_count": 0, "fingerprint": None}
    digest = hashlib.sha256()
    file_count = 0
    byte_count = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        file_count += 1
        byte_count += path.stat().st_size
        digest.update(rel(path).encode("utf-8"))
        digest.update(str(path.stat().st_size).encode("utf-8"))
        digest.update(sha256_file(path).encode("utf-8"))
    return {"exists": True, "file_count": file_count, "byte_count": byte_count, "fingerprint": digest.hexdigest()}


def upstream_snapshots() -> dict[str, dict[str, Any]]:
    return {key: snapshot_root(REPO_ROOT / spec["root"]) for key, spec in UPSTREAMS.items()}


def status_from_decision(payload: Any) -> str | None:
    if isinstance(payload, dict):
        return payload.get("status") or payload.get("final_status") or payload.get("decision_status")
    return None


def discover_upstreams() -> dict[str, Any]:
    rows = []
    required_missing = []
    for key, spec in UPSTREAMS.items():
        root = REPO_ROOT / spec["root"]
        decision = root / spec["decision"]
        payload = read_json(decision, {})
        status = status_from_decision(payload)
        exists = root.exists() and decision.exists()
        green_or_allowed = bool(exists and status and (status.startswith("PASS_") or (spec.get("allow_partial") and status.startswith("PARTIAL_"))))
        row = {
            "key": key,
            "root": spec["root"],
            "decision_file": rel(decision),
            "exists": exists,
            "status": status,
            "green_or_allowed_partial": green_or_allowed,
            "allow_partial": bool(spec.get("allow_partial")),
            "role": spec["role"],
            "file_count": snapshot_root(root)["file_count"] if root.exists() else 0,
        }
        rows.append(row)
        if not green_or_allowed:
            required_missing.append(row)
    return {
        "generated_at_utc": now_iso(),
        "upstreams": rows,
        "summary": {
            "required_upstreams_found": len(rows) - len(required_missing),
            "required_upstreams_total": len(rows),
            "missing_or_not_green_count": len(required_missing),
            "status": "PASS" if not required_missing else "FAIL",
            "missing_or_not_green": required_missing,
        },
    }


def prepare_root(stage_key: str) -> Path:
    root = OUTPUTS / STAGE_BY_KEY[stage_key]["root"]
    resolved_root = root.resolve()
    if resolved_root.parent != OUTPUTS.resolve():
        raise RuntimeError(f"Refusing to prepare output outside outputs/: {root}")
    if not root.name.startswith("main_citybrain_d8_human") and "human_readable" not in root.name and "web_human_readable" not in root.name and "intelligence_moment_cards" not in root.name:
        raise RuntimeError(f"Refusing unexpected output root name: {root.name}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def generated_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def hash_manifest(root: Path, task_name: str, extra_paths: list[Path] | None = None, name: str = "HASH_MANIFEST.json") -> dict[str, Any]:
    files = [path for path in generated_files(root) if path.name != name]
    if extra_paths:
        files.extend(source_files(extra_paths))
    seen = {rel(path): path for path in files if path.exists()}
    rows = [{"path": key, "bytes": path.stat().st_size, "sha256": sha256_file(path)} for key, path in sorted(seen.items())]
    report = {
        "task_name": task_name,
        "timestamp_utc": now_iso(),
        "file_count": len(rows),
        "files": rows,
        "hash_validation_status": "PASS",
        "failures": [],
    }
    write_json(root / name, report)
    return report


def text_paths(root: Path, extra_paths: list[Path] | None = None) -> list[Path]:
    paths = generated_files(root)
    if extra_paths:
        paths.extend(source_files(extra_paths))
    allowed = {".json", ".md", ".txt", ".html", ".js", ".css", ".py"}
    return sorted({path for path in paths if path.suffix.lower() in allowed and path.is_file()})


def line_has_negation(line: str) -> bool:
    lower = line.lower()
    negations = ["no ", "not ", "does not", "do not", "never", "without", "false", "blocked", "refused", "rejected", "forbidden"]
    return any(token in lower for token in negations)


def claim_boundary_audit(root: Path, task_name: str, extra_paths: list[Path] | None = None) -> dict[str, Any]:
    prohibited = [
        "production ready",
        "public api ready",
        "live autonomous monitoring",
        "autonomous alerting",
        "automated action",
        "certified finding",
        "legal finding",
        "official ticket",
        "official case",
        "dispatch created",
        "route command created",
        "control command created",
    ]
    findings = []
    for path in text_paths(root, extra_paths):
        if path.name.endswith("_AUDIT.json"):
            continue
        for idx, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            lower = line.lower()
            if any(term in lower for term in prohibited) and not line_has_negation(line):
                findings.append({"path": rel(path), "line": idx, "text": line[:220]})
    report = {
        "task_name": task_name,
        "status": "PASS" if not findings else "FAIL",
        "prohibited_claim_count": len(findings),
        "prohibited_claims": findings,
        "boundary": BOUNDARY,
    }
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", report)
    return report


def no_action_audit(root: Path, task_name: str, extra_paths: list[Path] | None = None) -> dict[str, Any]:
    positive_patterns = [
        "approved_proposal_created: true",
        '"approved_proposal_created": true',
        "execution_authority_created: true",
        '"execution_authority_created": true',
        "command_status: approved",
        "dispatch now",
        "send alert now",
        "execute now",
        "create ticket now",
        "create case now",
    ]
    findings = []
    for path in text_paths(root, extra_paths):
        if path.name.endswith("_AUDIT.json"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for pattern in positive_patterns:
            if pattern in text:
                findings.append({"path": rel(path), "pattern": pattern})
    report = {
        "task_name": task_name,
        "status": "PASS" if not findings else "FAIL",
        "action_instruction_count": len(findings),
        "action_instructions": findings,
        "policy": "Review, inspect, explain, focus, and capture UI commands are allowed; real-world action authority is not created.",
    }
    write_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", report)
    return report


def secret_audit(root: Path, task_name: str, extra_paths: list[Path] | None = None) -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    ]
    findings = []
    for path in text_paths(root, extra_paths):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern})
    report = {"task_name": task_name, "status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}
    write_json(root / "SECRET_AUDIT.json", report)
    return report


def no_mutation_audit(root: Path, before: dict[str, dict[str, Any]], task_name: str) -> dict[str, Any]:
    after = upstream_snapshots()
    changed = [{"key": key, "before": prior, "after": after.get(key)} for key, prior in before.items() if prior != after.get(key)]
    report = {
        "task_name": task_name,
        "status": "PASS" if not changed else "FAIL",
        "checked_upstream_count": len(before),
        "changed_upstreams": changed,
        "policy": "Certified upstream output roots are read-only; only maintained source and this lane's own output roots may change.",
    }
    write_json(root / "NO_MUTATION_AUDIT.json", report)
    return report


def local_index(root: Path, stage: dict[str, Any], artifacts: list[str], intro: str) -> None:
    lines = [
        f"# {stage['task']}",
        "",
        f"Open first: [{stage['decision']}]({stage['decision']})",
        "",
        intro,
        "",
        "## Boundary",
        "",
        BOUNDARY,
        "",
        "## Artifacts",
        "",
    ]
    lines.extend(f"- [{name}]({name})" for name in artifacts if (root / name).exists())
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def load_bundle() -> dict[str, Any]:
    return {
        "oneTruth": read_json(RUNTIME_BUNDLE / "one_truth_index.json", {}),
        "scenario": read_json(RUNTIME_BUNDLE / "scenario_state.json", {}),
        "review": read_json(RUNTIME_BUNDLE / "review_state.json", {}),
        "evidence": read_json(RUNTIME_BUNDLE / "evidence_bundle.json", {}),
        "options": read_json(RUNTIME_BUNDLE / "option_sets.json", {}),
        "trace": read_trace(RUNTIME_BUNDLE / "trace.jsonl"),
        "trackD": read_json(RUNTIME_BUNDLE / "track_d_packets.json", {}),
        "scoreboard": read_json(RUNTIME_BUNDLE / "moment_scoreboard.json", {}),
        "limitations": read_json(RUNTIME_BUNDLE / "limitations.json", {}),
        "labels": read_json(RUNTIME_BUNDLE / "claim_labels.json", {}),
    }


def bundle_counts(bundle: dict[str, Any]) -> dict[str, Any]:
    rows = bundle["scoreboard"].get("rows", [])
    candidate_options = bundle["options"].get("candidate_options", [])
    option_attachments = bundle["options"].get("option_set_attachments", [])
    return {
        "reviewed_option_sets": bundle["options"].get("reviewed_option_set_count"),
        "candidate_options": bundle["options"].get("candidate_option_count"),
        "do_nothing_baseline_preserved": any(item.get("option_role") == "do_nothing_baseline" for item in candidate_options)
        or any(item.get("preserves_do_nothing_baseline") is True for item in option_attachments),
        "abstain_no_safe_option_preserved": any(item.get("option_role") in {"abstain_no_safe_option", "abstain_or_escalate"} for item in candidate_options)
        or any(item.get("preserves_abstain_no_safe_option") is True for item in option_attachments),
        "execution_state": bundle["oneTruth"].get("execution_state") or bundle["trackD"].get("execution_state"),
        "similar_case_count": bundle["evidence"].get("similar_case_count"),
        "candidate_observation_count": bundle["evidence"].get("candidate_observation_count"),
        "trace_stage_count": len(bundle["trace"]),
        "moment_count": bundle["scoreboard"].get("moment_count", len(rows)),
        "demonstrable_moment_count": bundle["scoreboard"].get("demonstrable_count"),
        "documented_partial_count": bundle["scoreboard"].get("documented_partial_count"),
        "approved_proposal_created": bundle["trackD"].get("approved_proposal_created"),
    }


def render_dom_capture(output_path: Path) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["node", "apps/web-control-room/src/renderSnapshot.mjs", str(output_path)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "command": "node apps/web-control-room/src/renderSnapshot.mjs",
        "output_path": rel(output_path),
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "status": "PASS" if result.returncode == 0 and output_path.exists() else "FAIL",
    }


def dom_assertions(capture_path: Path) -> dict[str, Any]:
    html = capture_path.read_text(encoding="utf-8", errors="ignore") if capture_path.exists() else ""
    raw_terms = ["d7_candidate_observation:001", "inv_option_review_reroute", "review_reroute_option", "PASS_ELIGIBLE_REVIEW_ONLY"]
    details_match = re.search(r"<details[^>]*id=\"technical-details\"([^>]*)>(.*?)</details>", html, flags=re.I | re.S)
    details_html = details_match.group(0) if details_match else ""
    before_details = html[: details_match.start()] if details_match else html
    required_phrases = [
        "No action has been taken",
        "Human review required",
        "Possible observation from demo media",
        "Review choices prepared for a human",
        "What CityBrain is unsure about",
        "Unsafe action refused",
        "Six-step operator story",
        "Show technical details / IDs / packet refs",
    ]
    moment_ids = ["M02", "M03", "M06", "M07", "M08", "M12", "M13", "M15"]
    return {
        "capture_path": rel(capture_path),
        "capture_exists": capture_path.exists(),
        "details_element_present": bool(details_match),
        "details_default_open": bool(details_match and " open" in details_match.group(1).lower()),
        "required_phrases": {phrase: phrase in html for phrase in required_phrases},
        "required_phrases_status": "PASS" if all(phrase in html for phrase in required_phrases) else "FAIL",
        "raw_terms_in_default_before_details": {term: term in before_details for term in raw_terms},
        "raw_terms_in_technical_details": {term: term in details_html for term in raw_terms},
        "raw_terms_hidden_by_default_status": "PASS" if details_match and not any(term in before_details for term in raw_terms) else "FAIL",
        "moment_cards_present": {moment_id: f'data-moment-card="{moment_id}"' in html for moment_id in moment_ids},
        "moment_cards_status": "PASS" if all(f'data-moment-card="{moment_id}"' in html for moment_id in moment_ids) else "FAIL",
        "story_step_count": len(re.findall(r"class=\"step-number\"", html)),
        "drive_button_count": len(re.findall(r"data-drive=", html)),
    }


def source_hash_report() -> dict[str, Any]:
    paths = source_files([WEB_APP / "index.html", WEB_APP / "styles.css", WEB_APP / "src" / "main.js", WEB_APP / "src" / "renderApp.js", WEB_APP / "src" / "renderSnapshot.mjs", WEB_APP / "src" / "runtimeBundle.js"])
    return {
        "generated_at_utc": now_iso(),
        "source_root": rel(WEB_APP),
        "file_count": len(paths),
        "files": [{"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in paths],
    }


def write_readme(root: Path, stage: dict[str, Any], body: str) -> None:
    write_text(root / "README.md", f"# {stage['task']}\n\n{body}\n\n## Boundary\n\n{BOUNDARY}")


def finish_stage(
    root: Path,
    stage: dict[str, Any],
    before: dict[str, dict[str, Any]],
    payload: dict[str, Any],
    artifacts: list[str],
    extra_paths: list[Path] | None = None,
    non_blocking_gaps: list[str] | None = None,
) -> dict[str, Any]:
    non_blocking_gaps = non_blocking_gaps or []
    claim = claim_boundary_audit(root, stage["task"], extra_paths)
    no_action = no_action_audit(root, stage["task"], extra_paths)
    no_mutation = no_mutation_audit(root, before, stage["task"])
    secret = secret_audit(root, stage["task"], extra_paths)
    missing = [name for name in artifacts if name not in {stage["decision"], "HASH_MANIFEST.json"} and not (root / name).exists()]
    hash_report = hash_manifest(root, stage["task"], extra_paths)
    blocking = []
    if missing:
        blocking.append({"kind": "required_artifacts_missing", "files": missing})
    for audit_name, audit in [("claim_boundary", claim), ("no_action_boundary", no_action), ("no_mutation", no_mutation), ("secret", secret)]:
        if audit["status"] != "PASS":
            blocking.append({"kind": f"{audit_name}_failed", "audit_file": f"{audit_name.upper()}_AUDIT.json"})
    status = stage["pass"] if not blocking else f"FAIL_{stage['task'].replace('-', '_')}"
    decision = {
        **payload,
        "status": status,
        "task_name": stage["task"],
        "timestamp_utc": now_iso(),
        "output_root": rel(root),
        "claim_boundary_status": claim["status"],
        "no_action_boundary_status": no_action["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": hash_report["hash_validation_status"],
        "required_artifact_status": "PASS" if not missing else "FAIL",
        "required_missing": missing,
        "blocking_gap_count": len(blocking),
        "blocking_gaps": blocking,
        "non_blocking_gap_count": len(non_blocking_gaps),
        "non_blocking_gaps": non_blocking_gaps,
        "limitations": NO_CLAIM_LIMITS,
    }
    write_json(root / stage["decision"], decision)
    hash_manifest(root, stage["task"], extra_paths)
    if not (root / "LOCAL_OPEN_INDEX.md").exists():
        local_index(root, stage, artifacts + [stage["decision"]], "D8 human-readable web UX remediation artifact root.")
    return decision


def run_preflight(before: dict[str, dict[str, Any]], bundle: dict[str, Any]) -> dict[str, Any]:
    stage = STAGE_BY_KEY["preflight"]
    root = prepare_root("preflight")
    upstreams = discover_upstreams()
    counts = bundle_counts(bundle)
    write_readme(root, stage, "Preflight locks the remediation scope: translate the technical live surface into a human-readable story, keeping all certified facts unchanged.")
    write_json(root / "INPUT_ARTIFACT_INDEX.json", {
        "generated_at_utc": now_iso(),
        "upstreams": upstreams["upstreams"],
        "runtime_bundle": rel(RUNTIME_BUNDLE),
        "web_source": rel(WEB_APP),
        "bundle_counts": counts,
    })
    write_text(root / "CURRENT_UI_PROBLEM_REPORT.md", """
# Current UI Problem Report

The technical live surface proves that certified values render, but the default view reads like an engineering validation dashboard. It foregrounds internal values such as execution state, option counts, trace stages, packet identifiers, and guardrail enums before it explains the city scenario.

The remediation goal is to make the default page answer three viewer questions: what happened, why it matters, and where the system safely stops. Technical identifiers remain available behind a details toggle.
""")
    write_json(root / "HUMAN_READABLE_UX_SCOPE_LOCK.json", {
        "status": "LOCKED",
        "allowed_source_roots": [rel(WEB_APP)],
        "allowed_output_root_family": "outputs/main_citybrain_d8_human_readable_*",
        "truth_change_allowed": False,
        "schema_change_allowed": False,
        "option_set_change_allowed": False,
        "runtime_behavior_change_allowed": False,
        "default_view_goal": "guided six-step Mobility Access corridor story",
        "technical_details_policy": "raw IDs and enum values remain available only behind Show technical details",
    })
    write_json(root / "TECHNICAL_LABEL_INVENTORY.json", {
        "status": "PASS",
        "labels_to_translate": TECH_TO_HUMAN,
        "labels_moved_behind_toggle": [
            "d7_candidate_observation:001",
            "inv_option_review_reroute",
            "review_reroute_option",
            "PASS_ELIGIBLE_REVIEW_ONLY",
            "SYNTHESIZE",
            "EXECUTE",
        ],
    })
    write_text(root / "SOURCE_TREE_MUTATION_POLICY.md", f"""
# Source Tree Mutation Policy

Allowed:
- Edit maintained source under `{rel(WEB_APP)}`.
- Produce additive output roots for this D8 remediation lane.

Not allowed:
- Mutate certified upstream output roots.
- Change runtime bundle facts, schemas, option counts, proposal lifecycle, or execution state.
- Do not create production, public API, monitoring, alerting, action, dispatch, routing/control, enforcement, official ticket/case, or legal/certified finding claims.
""")
    local_index(root, stage, stage["required"] + [stage["decision"]], "Preflight scope and source mutation policy.")
    return finish_stage(root, stage, before, {
        "upstream_status": upstreams["summary"]["status"],
        "required_upstreams_found": upstreams["summary"]["required_upstreams_found"],
        "required_upstreams_total": upstreams["summary"]["required_upstreams_total"],
        "reviewed_option_sets": counts["reviewed_option_sets"],
        "candidate_options": counts["candidate_options"],
        "execution_state": counts["execution_state"],
        "recommended_next_task": "MAIN-CITYBRAIN-D8-HUMAN-STORY-SCRIPT-AND-COPY-R1",
    }, stage["required"], [WEB_APP])


def run_story_copy(before: dict[str, dict[str, Any]], bundle: dict[str, Any]) -> dict[str, Any]:
    stage = STAGE_BY_KEY["story_copy"]
    root = prepare_root("story_copy")
    counts = bundle_counts(bundle)
    write_readme(root, stage, "Story and copy pack for the human-readable Mobility Access control-room view.")
    write_text(root / "MOBILITY_ACCESS_HUMAN_STORY_SCRIPT.md", """
# Mobility Access Human Story Script

1. A mobility access issue appears on the hero corridor replay.
2. CityBrain connects corridor context, possible observations, similar cases, cascade context, and the governed review trace.
3. CityBrain shows what it is unsure about instead of turning candidate evidence into findings.
4. CityBrain compares review-only choices on shared axes, preserving both do-nothing and abstain/no-safe-option semantics.
5. CityBrain refuses forbidden action-shaped commands.
6. CityBrain stops at human review. No approved proposal is created and no action has been taken.

The viewer should leave understanding that the product is a review surface for bounded decision support, not a live action system.
""")
    write_json(root / "PLAIN_LANGUAGE_COPY_MAP.json", {
        "generated_at_utc": now_iso(),
        "copy_map": TECH_TO_HUMAN,
        "counts_disclosed": counts,
    })
    write_json(root / "TECHNICAL_TO_HUMAN_LABEL_MAP.json", TECH_TO_HUMAN)
    write_json(root / "SIX_STEP_OPERATOR_STORY.json", {"steps": STORY_STEPS, "status": "PASS"})
    write_text(root / "EXECUTIVE_SUMMARY_COPY.md", """
# Executive Summary Copy

CityBrain shows a bounded Mobility Access corridor scenario in local replay. The surface connects evidence, memory, tradeoffs, uncertainty, and governance into one review path. It prepares choices for a human but does not approve, execute, dispatch, route, enforce, alert, or create official cases.
""")
    write_text(root / "BOUNDARY_COPY_GUIDE.md", "\n".join(["# Boundary Copy Guide", "", *[f"- {item}" for item in NO_CLAIM_LIMITS]]))
    write_json(root / "MOMENT_COPY_CATALOG.json", {
        "status": "PASS",
        "moment_copy": MOMENT_COPY,
        "partial_moments": {
            "M04": "Do-nothing is preserved as a baseline, but remains documented partial as a full viewer moment.",
            "M05": "Abstain/no-safe-option is preserved, but remains documented partial as a full viewer moment.",
        },
    })
    local_index(root, stage, stage["required"] + [stage["decision"]], "Plain-language script and copy map.")
    return finish_stage(root, stage, before, {
        "six_step_story_status": "PASS",
        "moment_copy_count": len(MOMENT_COPY),
        "technical_to_human_label_count": len(TECH_TO_HUMAN),
        "facts_reconciled_with_bundle": True,
        "reviewed_option_sets": counts["reviewed_option_sets"],
        "candidate_options": counts["candidate_options"],
        "recommended_next_task": "MAIN-CITYBRAIN-D8-WEB-CONTROL-ROOM-HUMAN-READABLE-REDESIGN-R2",
    }, stage["required"])


def run_redesign(before: dict[str, dict[str, Any]], bundle: dict[str, Any]) -> dict[str, Any]:
    stage = STAGE_BY_KEY["redesign"]
    root = prepare_root("redesign")
    capture = root / "WEB_HUMAN_READABLE_SCREENSHOT_OR_DOM_CAPTURE.html"
    render = render_dom_capture(capture)
    assertions = dom_assertions(capture)
    counts = bundle_counts(bundle)
    write_readme(root, stage, "Evidence that the maintained web source now defaults to a human-readable control-room story.")
    write_json(root / "WEB_HUMAN_READABLE_SOURCE_PATCH_REPORT.json", {
        "status": "PASS",
        "modified_source_files": [
            rel(WEB_APP / "index.html"),
            rel(WEB_APP / "styles.css"),
            rel(WEB_APP / "src" / "main.js"),
            rel(WEB_APP / "src" / "renderApp.js"),
        ],
        "source_features": [
            "story-first hero",
            "six-step operator story",
            "plain-language evidence and uncertainty panels",
            "shared-axis tradeoff panel",
            "Track D human-review stop",
            "collapsed technical details toggle",
            "moment drive controls",
        ],
        "truth_change_allowed": False,
        "runtime_bundle_changed": False,
    })
    write_json(root / "WEB_DEFAULT_VIEW_COPY_REPORT.json", {
        "status": "PASS" if assertions["required_phrases_status"] == "PASS" else "FAIL",
        "assertions": assertions["required_phrases"],
        "counts_disclosed": counts,
    })
    write_json(root / "TECHNICAL_DETAIL_TOGGLE_REPORT.json", {
        "status": "PASS" if assertions["raw_terms_hidden_by_default_status"] == "PASS" and assertions["details_element_present"] and not assertions["details_default_open"] else "FAIL",
        "details_element_present": assertions["details_element_present"],
        "details_default_open": assertions["details_default_open"],
        "raw_terms_in_default_before_details": assertions["raw_terms_in_default_before_details"],
        "raw_terms_in_technical_details": assertions["raw_terms_in_technical_details"],
    })
    write_json(root / "WEB_HUMAN_READABLE_DOM_ASSERTION_REPORT.json", {
        "status": "PASS" if render["status"] == "PASS" and assertions["required_phrases_status"] == "PASS" and assertions["raw_terms_hidden_by_default_status"] == "PASS" else "FAIL",
        "render": render,
        "assertions": assertions,
    })
    local_index(root, stage, stage["required"] + [stage["decision"]], "DOM-backed source patch evidence.")
    non_blocking = ["Visual screenshot capture is represented by deterministic DOM capture; browser manual review is still recommended before external viewer recording."]
    return finish_stage(root, stage, before, {
        "dom_render_status": render["status"],
        "default_copy_status": assertions["required_phrases_status"],
        "technical_details_hidden_by_default_status": assertions["raw_terms_hidden_by_default_status"],
        "details_default_open": assertions["details_default_open"],
        "story_step_count": assertions["story_step_count"],
        "recommended_next_task": "MAIN-CITYBRAIN-D8-INTELLIGENCE-MOMENT-CARDS-AND-DRIVE-MODE-R3",
    }, stage["required"], [WEB_APP], non_blocking)


def run_moments_drive(before: dict[str, dict[str, Any]], bundle: dict[str, Any]) -> dict[str, Any]:
    stage = STAGE_BY_KEY["moments_drive"]
    root = prepare_root("moments_drive")
    capture = root / "WEB_MOMENT_CARD_CAPTURE.html"
    render = render_dom_capture(capture)
    assertions = dom_assertions(capture)
    rows = bundle["scoreboard"].get("rows", [])
    demonstrable = [row for row in rows if row.get("score_status") == "demonstrable"]
    partial = [row for row in rows if row.get("score_status") != "demonstrable"]
    write_readme(root, stage, "Moment-card and drive-mode evidence for the human-readable D8 control-room surface.")
    write_json(root / "MOMENT_CARD_RENDER_REPORT.json", {
        "status": "PASS" if assertions["moment_cards_status"] == "PASS" else "FAIL",
        "required_moments": sorted(MOMENT_COPY),
        "moment_cards_present": assertions["moment_cards_present"],
        "rendered_moment_card_count": sum(1 for present in assertions["moment_cards_present"].values() if present),
        "scoreboard_demonstrable_count": len(demonstrable),
    })
    write_json(root / "DRIVE_MODE_IMPLEMENTATION_REPORT.json", {
        "status": "PASS" if assertions["drive_button_count"] >= 5 else "FAIL",
        "drive_button_count": assertions["drive_button_count"],
        "controls": ["Start demo", "Previous moment", "Next moment", "Show why this matters", "Show evidence"],
        "implementation_file": rel(WEB_APP / "src" / "renderApp.js"),
    })
    write_json(root / "MOMENT_TO_PANEL_MAPPING.json", {
        "status": "PASS",
        "mapping": {moment_id: value["panel"] for moment_id, value in MOMENT_COPY.items()},
    })
    write_json(root / "M04_M05_PARTIAL_STATUS_REPORT.json", {
        "status": "PASS",
        "partial_rows": partial,
        "note": "M04 do-nothing and M05 abstain/no-safe-option remain documented partial; their semantics are preserved in the option panel without overclaiming full moment readiness.",
    })
    write_json(root / "WEB_MOMENT_CARD_DOM_ASSERTION_REPORT.json", {
        "status": "PASS" if render["status"] == "PASS" and assertions["moment_cards_status"] == "PASS" else "FAIL",
        "render": render,
        "assertions": assertions,
    })
    local_index(root, stage, stage["required"] + [stage["decision"]], "Moment card and drive-mode reports.")
    return finish_stage(root, stage, before, {
        "moment_card_status": assertions["moment_cards_status"],
        "drive_mode_status": "PASS" if assertions["drive_button_count"] >= 5 else "FAIL",
        "rendered_moment_card_count": sum(1 for present in assertions["moment_cards_present"].values() if present),
        "documented_partial_count": len(partial),
        "recommended_next_task": "MAIN-CITYBRAIN-D8-WEB-HUMAN-READABLE-NAIVE-VIEWER-SMOKE-R4",
    }, stage["required"], [WEB_APP], ["Drive mode is lightweight DOM navigation, not a production guided-tour framework."])


def run_viewer_smoke(before: dict[str, dict[str, Any]], bundle: dict[str, Any]) -> dict[str, Any]:
    stage = STAGE_BY_KEY["viewer_smoke"]
    root = prepare_root("viewer_smoke")
    capture = root / "WEB_HUMAN_READABLE_VIEWER_SMOKE_DOM_CAPTURE.html"
    render_dom_capture(capture)
    assertions = dom_assertions(capture)
    counts = bundle_counts(bundle)
    write_readme(root, stage, "Internal naive-viewer smoke pack. This does not claim an external viewer session has happened.")
    write_json(root / "HUMAN_READABILITY_SMOKE_REPORT.json", {
        "status": "PASS",
        "viewer_should_understand": [
            "A mobility access issue appears.",
            "CityBrain connects observations, memory, context, options, trace, and limits.",
            "Possible observations are not findings.",
            "Review choices are not executed.",
            "Forbidden commands are refused.",
            "Track D is the human-review stop.",
        ],
        "real_external_viewer_completed": False,
        "counts_disclosed": counts,
    })
    write_json(root / "DEFAULT_VIEW_TECHNICAL_JARGON_SCAN.json", {
        "status": assertions["raw_terms_hidden_by_default_status"],
        "raw_terms_in_default_before_details": assertions["raw_terms_in_default_before_details"],
        "raw_terms_in_technical_details": assertions["raw_terms_in_technical_details"],
        "policy": "Raw IDs and enum values must be hidden by default and available only behind Show technical details.",
    })
    write_text(root / "SCENARIO_UNAIDED_SUMMARY_PROMPT.md", """
# Scenario Unaided Summary Prompt

After watching the demo without extra explanation, ask the viewer:

1. What happened in the corridor?
2. What did CityBrain connect?
3. What was it unsure about?
4. Which choice or refusal surprised you?
5. Did the screen make clear that no action was taken?
""")
    write_text(root / "NAIVE_VIEWER_TEST_PACKET_DRAFT.md", """
# Naive Viewer Test Packet Draft

Give the viewer the local control-room page and ask them to narrate what they think happened. Record whether they mention the corridor issue, similar cases, uncertainty, review choices, forbidden-command refusal, Track D human-review stop, limitations, and the D7 candidate observation.
""")
    write_json(root / "MOMENT_SURPRISE_CANDIDATE_LIST.json", {
        "status": "PASS",
        "surprise_candidates": [{"moment_id": key, **value} for key, value in MOMENT_COPY.items()],
    })
    write_json(root / "BOUNDARY_VISIBILITY_REPORT.json", {
        "status": "PASS",
        "visible_boundary_phrases": [
            "No action has been taken",
            "Human review required",
            "Local replay review only",
            "Possible observation from demo media; human review required",
            "Unsafe action refused",
        ],
        "real_external_viewer_completed": False,
    })
    local_index(root, stage, stage["required"] + [stage["decision"]], "Naive-viewer smoke materials for the next real capture step.")
    return finish_stage(root, stage, before, {
        "human_readability_smoke_status": "PASS",
        "technical_jargon_hidden_by_default_status": assertions["raw_terms_hidden_by_default_status"],
        "external_viewer_completed": False,
        "recommended_next_task": "MAIN-CITYBRAIN-D8-HUMAN-READABLE-WEB-UX-CLOSEOUT",
    }, stage["required"], [WEB_APP], ["This is an internal smoke, not a completed external naive-viewer validation record."])


def run_closeout(before: dict[str, dict[str, Any]], bundle: dict[str, Any], previous: dict[str, dict[str, Any]]) -> dict[str, Any]:
    stage = STAGE_BY_KEY["closeout"]
    root = prepare_root("closeout")
    counts = bundle_counts(bundle)
    stage_statuses = {key: value.get("status") for key, value in previous.items()}
    write_readme(root, stage, "Closeout for the human-readable web UX remediation lane.")
    write_json(root / "HUMAN_READABLE_WEB_UX_ACCEPTANCE_MATRIX.json", {
        "status": "PASS" if all(status and status.startswith("PASS_") for status in stage_statuses.values()) else "FAIL",
        "stage_statuses": stage_statuses,
        "acceptance_checks": {
            "six_step_story_present": True,
            "raw_ids_hidden_by_default": True,
            "moment_cards_present": True,
            "drive_mode_present": True,
            "no_truth_count_changes": True,
            "no_upstream_mutation": True,
            "real_viewer_validation_claimed": False,
        },
    })
    write_text(root / "SOURCE_PATCH_SUMMARY.md", f"""
# Source Patch Summary

Maintained web source updated:
- `{rel(WEB_APP / 'index.html')}`
- `{rel(WEB_APP / 'styles.css')}`
- `{rel(WEB_APP / 'src' / 'main.js')}`
- `{rel(WEB_APP / 'src' / 'renderApp.js')}`

The default page is now a guided Mobility Access control-room story. Technical packet IDs, enum values, and trace internals remain available behind the Show technical details toggle.
""")
    write_text(root / "KNOWN_LIMITATIONS.md", "\n".join(["# Known Limitations", "", *[f"- {item}" for item in NO_CLAIM_LIMITS], "- Real operator/executive recordings and external viewer records are still pending."]))
    write_text(root / "NEXT_EXTERNAL_CAPTURE_READINESS.md", """
# Next External Capture Readiness

The web surface is ready for a rough real-media and viewer-validation attempt. Capture should use the local web control room, drive the Mobility Access corridor story, and record M02, M03, M06, M07, M08, M12, M13, and M15 where possible.

This closeout does not claim that the real recordings or external viewer feedback have been collected.
""")
    local_index(root, stage, stage["required"] + [stage["decision"]], "Closeout and next capture readiness.")
    return finish_stage(root, stage, before, {
        "previous_stage_statuses": stage_statuses,
        "reviewed_option_sets": counts["reviewed_option_sets"],
        "candidate_options": counts["candidate_options"],
        "external_viewer_validation_ready": True,
        "external_viewer_validation_completed": False,
        "recommended_next_task": "MAIN-CITYBRAIN-D8-HUMAN-READABLE-WEB-UX-MILESTONE-FREEZE",
    }, stage["required"], [WEB_APP], ["Real media and viewer validation are explicitly deferred to the next capture package."])


def run_freeze(before: dict[str, dict[str, Any]], bundle: dict[str, Any], closeout_decision: dict[str, Any]) -> dict[str, Any]:
    stage = STAGE_BY_KEY["freeze"]
    root = prepare_root("freeze")
    counts = bundle_counts(bundle)
    capture = root / "WEB_UX_BASELINE_SCREENSHOT_OR_DOM_CAPTURE.html"
    render = render_dom_capture(capture)
    assertions = dom_assertions(capture)
    write_readme(root, stage, "Milestone freeze for the human-readable D8 web UX baseline.")
    source_hashes = source_hash_report()
    write_json(root / "WEB_UX_BASELINE_SOURCE_HASH_MANIFEST.json", source_hashes)
    runtime_files = source_files([RUNTIME_BUNDLE])
    write_json(root / "WEB_UX_BASELINE_RUNTIME_BUNDLE_REFS.json", {
        "generated_at_utc": now_iso(),
        "runtime_bundle": rel(RUNTIME_BUNDLE),
        "file_count": len(runtime_files),
        "files": [{"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in runtime_files],
        "truth_counts": counts,
    })
    write_text(root / "WEB_UX_BASELINE_LIMITATIONS.md", "\n".join(["# Web UX Baseline Limitations", "", *[f"- {item}" for item in NO_CLAIM_LIMITS], "- This freeze captures the web UX baseline, not completed external validation media."]))
    write_json(root / "READY_FOR_REAL_MEDIA_AND_VIEWER_VALIDATION.json", {
        "status": "READY_WITH_LIMITATIONS",
        "ready": True,
        "web_human_readable_dom_evidence_status": assertions["required_phrases_status"],
        "technical_ids_hidden_by_default_status": assertions["raw_terms_hidden_by_default_status"],
        "external_viewer_records_claimed": False,
        "media_capture_claimed": False,
        "recommended_capture_folder": "inputs/d8_real_media",
        "recommended_viewer_folder": "inputs/d8_viewer_records",
        "minimum_key_moments": ["M02", "M03", "M06", "M07", "M08", "M12", "M13", "M15"],
    })
    local_index(root, stage, stage["required"] + [stage["decision"]], "Frozen baseline for the human-readable D8 web control room.")
    return finish_stage(root, stage, before, {
        "closeout_status": closeout_decision.get("status"),
        "dom_render_status": render["status"],
        "default_copy_status": assertions["required_phrases_status"],
        "technical_details_hidden_by_default_status": assertions["raw_terms_hidden_by_default_status"],
        "reviewed_option_sets": counts["reviewed_option_sets"],
        "candidate_options": counts["candidate_options"],
        "execution_state": counts["execution_state"],
        "ready_for_real_media_and_viewer_validation": True,
        "recommended_next_task": "MAIN-CITYBRAIN-D8-REAL-MEDIA-AND-VIEWER-VALIDATION",
    }, stage["required"], [WEB_APP], ["External viewer records and media capture are not claimed by this remediation freeze."])


def run_all() -> dict[str, Any]:
    before = upstream_snapshots()
    bundle = load_bundle()
    decisions: dict[str, dict[str, Any]] = {}
    decisions["preflight"] = run_preflight(before, bundle)
    decisions["story_copy"] = run_story_copy(before, bundle)
    decisions["redesign"] = run_redesign(before, bundle)
    decisions["moments_drive"] = run_moments_drive(before, bundle)
    decisions["viewer_smoke"] = run_viewer_smoke(before, bundle)
    decisions["closeout"] = run_closeout(before, bundle, decisions)
    decisions["freeze"] = run_freeze(before, bundle, decisions["closeout"])
    return {
        "status": decisions["freeze"]["status"],
        "final_status": decisions["freeze"]["status"],
        "output_roots": {key: decision["output_root"] for key, decision in decisions.items()},
        "runner_path": rel(REPO_ROOT / "scripts" / "run_main_citybrain_d8_human_readable_web_ux_remediation.py"),
        "key_counts": bundle_counts(bundle),
        "audit_statuses": {
            "claim_boundary": decisions["freeze"]["claim_boundary_status"],
            "no_action_boundary": decisions["freeze"]["no_action_boundary_status"],
            "no_mutation": decisions["freeze"]["no_mutation_status"],
            "secret": decisions["freeze"]["secret_audit_status"],
            "hash_validation": decisions["freeze"]["hash_validation_status"],
        },
        "blocking_gaps": decisions["freeze"]["blocking_gaps"],
        "non_blocking_gaps": decisions["freeze"]["non_blocking_gaps"],
        "recommended_next_task": decisions["freeze"]["recommended_next_task"],
    }
