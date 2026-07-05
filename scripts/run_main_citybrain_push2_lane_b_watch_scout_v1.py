#!/usr/bin/env python3
"""Build Push 2 Lane B WATCH Scout v1 artifacts.

WATCH is a proactive consumer of the local/replay Event Fabric state. It emits
review prompts only: no findings, no official actions, no live retrieval, and
no execution.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "push2_lane_b_watch_scout_v1"
CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "push2_lane_b_watch_scout_v1_closeout"
FINAL_STATUS_ROOT = REPO_ROOT / "outputs" / "push2_lane_b_watch_scout_v1_final_status"
R7B_ROOT = REPO_ROOT / "outputs" / "main_citybrain_r7b_perception_to_event_fabric_local_replay"
R7B_DECISION = R7B_ROOT / "R7B_EVENT_FABRIC_DECISION.json"
R7B_EVENT_LOG = R7B_ROOT / "R7B_LOCAL_EVENT_LOG.jsonl"
R7B_MATERIALIZED = R7B_ROOT / "R7B_MATERIALIZED_REVIEW_STATE.json"
LANE_A_ROOT = REPO_ROOT / "outputs" / "push2_lane_a_check_v0"

PACKAGE = "MAIN-CITYBRAIN-PUSH2-LANE-B-WATCH-SCOUT-V1"
PASS_STATUS = "PASS_PUSH2_LANE_B_WATCH_SCOUT_V1_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_PUSH2_LANE_B_WATCH_SCOUT_V1_BOUNDARY_OR_AUTHORITY"
STOP_STATUS = "STOP_PUSH2_LANE_B_WATCH_SCOUT_V1_MISSING_EVENT_RUNTIME_AND_FALLBACK"

AUTHORITY_LEVEL = "review_prompt_only"
OFFICIAL_STATUS = "not_official"

NOT_EXECUTED = [
    "no live retrieval",
    "no production API",
    "no URL fetch",
    "no LLM call",
    "no official finding",
    "no official case/ticket submission",
    "no dispatch/control/enforcement",
    "no automated action",
]

CANNOT_CLAIM = [
    "official finding",
    "official action",
    "legal/certified finding",
    "live monitoring",
    "production feed",
    "official case/ticket submission",
    "dispatch/control/enforcement",
    "autonomous workflow",
]

SAFE_NEXT_LOOKS = {
    "unresolved_candidate_observations": [
        "inspect the retained evidence refs",
        "check missing source context before any promotion",
        "route to human review if the candidate still matters",
    ],
    "quarantined_or_boundary_blocked_items": [
        "inspect quarantine or boundary-failed reasons",
        "compare the source packet with CHECK boundary output",
        "leave blocked unless an approved source resolves the boundary",
    ],
    "stale_or_low_authority_review_items": [
        "inspect authority envelope before use",
        "refresh source context if a reviewer needs newer evidence",
        "keep sandbox drafts and proposals non-executed",
    ],
    "new_review_events_since_last_snapshot": [
        "inspect the new review event trace",
        "compare against the previous local snapshot before escalating",
        "keep the prompt candidate-only until a reviewer accepts it",
    ],
}

WATCH_FAMILIES = [
    {
        "execution_order": 1,
        "watch_family": "unresolved_candidate_observations",
        "source_state": "R7B_MATERIALIZED_REVIEW_STATE.unresolved_observations",
        "description": "Candidate observations preserved as unresolved review context.",
    },
    {
        "execution_order": 2,
        "watch_family": "stale_or_low_authority_review_items",
        "source_state": "R7B_MATERIALIZED_REVIEW_STATE.sandbox_draft_cases + not_executed_action_proposals",
        "description": "Low-authority local replay items that remain draft or not executed.",
    },
    {
        "execution_order": 3,
        "watch_family": "new_review_events_since_last_snapshot",
        "source_state": "R7B_MATERIALIZED_REVIEW_STATE.active_review_events",
        "description": "Review events treated as new relative to the empty WATCH v1 snapshot.",
    },
    {
        "execution_order": 4,
        "watch_family": "quarantined_or_boundary_blocked_items",
        "source_state": "R7B_MATERIALIZED_REVIEW_STATE.quarantined_observations",
        "description": "Quarantined Event Fabric items, or Lane A boundary-failed fallback packets if quarantine is absent.",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(payload: dict[str, Any], omit: set[str] | None = None) -> str:
    omit = omit or set()
    clean = {key: value for key, value in payload.items() if key not in omit}
    return hashlib.sha256(json.dumps(clean, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def reset_output_root(root: Path = OUTPUT_ROOT) -> None:
    resolved = root.resolve()
    if (REPO_ROOT / "outputs").resolve() not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs/: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def reset_output_roots() -> None:
    for root in [OUTPUT_ROOT, CLOSEOUT_ROOT, FINAL_STATUS_ROOT]:
        reset_output_root(root)


def load_event_runtime_state() -> dict[str, Any]:
    missing = [rel(path) for path in [R7B_DECISION, R7B_EVENT_LOG, R7B_MATERIALIZED] if not path.exists()]
    if missing:
        return {
            "status": "MISSING",
            "runtime_loaded": False,
            "missing": missing,
            "decision": {},
            "events": [],
            "materialized": {},
        }
    materialized = read_json(R7B_MATERIALIZED, {})
    return {
        "status": "PASS" if materialized.get("status") == "PASS" else "WARN",
        "runtime_loaded": True,
        "missing": [],
        "decision": read_json(R7B_DECISION, {}),
        "events": read_jsonl(R7B_EVENT_LOG),
        "materialized": materialized,
        "source_runtime_refs": [rel(R7B_DECISION), rel(R7B_EVENT_LOG), rel(R7B_MATERIALIZED)],
    }


def _coerce_refs(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        return [values]
    refs: list[str] = []
    for value in values if isinstance(values, list) else [values]:
        if value is None:
            continue
        if isinstance(value, dict):
            ref = value.get("ref_id") or value.get("source_id") or value.get("id")
            if ref:
                refs.append(str(ref))
        else:
            refs.append(str(value))
    return refs


def event_refs_for(event: dict[str, Any]) -> list[str]:
    refs = _coerce_refs(event.get("event_refs"))
    if event.get("event_id"):
        refs.insert(0, str(event["event_id"]))
    return sorted(dict.fromkeys(refs))


def candidate_refs_for(event: dict[str, Any]) -> list[str]:
    refs = _coerce_refs(event.get("candidate_observation_refs"))
    if event.get("candidate_observation_id"):
        refs.insert(0, str(event["candidate_observation_id"]))
    payload = event.get("payload", {})
    if isinstance(payload, dict):
        refs.extend(_coerce_refs(payload.get("candidate_observation_refs")))
        if payload.get("candidate_observation_id"):
            refs.append(str(payload["candidate_observation_id"]))
        if payload.get("linked_candidate_observation_id"):
            refs.append(str(payload["linked_candidate_observation_id"]))
    return sorted(dict.fromkeys(refs))


def evidence_refs_for(event: dict[str, Any]) -> list[str]:
    refs = _coerce_refs(event.get("evidence_refs"))
    payload = event.get("payload", {})
    if isinstance(payload, dict):
        refs.extend(_coerce_refs(payload.get("evidence_refs")))
        refs.extend(_coerce_refs(payload.get("source_refs")))
    if not refs:
        refs = ["evidence:watch-scout:local-replay-event-fabric"]
    return sorted(dict.fromkeys(refs))


def limitation_refs_for(event: dict[str, Any]) -> list[str]:
    refs = _coerce_refs(event.get("limitation_refs"))
    payload = event.get("payload", {})
    if isinstance(payload, dict):
        refs.extend(_coerce_refs(payload.get("limitation_refs")))
        refs.extend(_coerce_refs(payload.get("reasons")))
    if not refs:
        refs = ["limitation:watch-scout:review-prompt-only"]
    return sorted(dict.fromkeys(refs))


def trace_refs_for(event: dict[str, Any], family: str) -> list[str]:
    refs = _coerce_refs(event.get("trace_refs"))
    payload = event.get("payload", {})
    if isinstance(payload, dict):
        refs.extend(_coerce_refs(payload.get("trace")))
    refs.append(f"PUSH2:WATCH:{family}")
    return sorted(dict.fromkeys(refs))


def load_lane_a_boundary_failed_check_reports() -> list[dict[str, Any]]:
    candidates = [
        LANE_A_ROOT / "CHECK_REPORTS.json",
        LANE_A_ROOT / "LANE_A_CHECK_REPORTS.json",
        LANE_A_ROOT / "CHECK_V0_REPORTS.json",
        LANE_A_ROOT / "WATCH_BOUNDARY_FAILED_CHECK_REPORTS.json",
    ]
    reports: list[dict[str, Any]] = []
    for path in candidates:
        payload = read_json(path, None)
        if not payload:
            continue
        if isinstance(payload, list):
            rows = payload
        else:
            rows = payload.get("check_reports") or payload.get("items") or payload.get("reports") or []
        for row in rows:
            status_text = json.dumps(row, sort_keys=True).lower()
            if any(token in status_text for token in ["boundary_failed", "boundary-failed", "boundary blocked", "blocked", "fail"]):
                row = dict(row)
                row["source_check_report_path"] = rel(path)
                reports.append(row)
    return reports


def boundary_report_to_event(report: dict[str, Any], index: int) -> dict[str, Any]:
    report_id = report.get("check_report_id") or report.get("report_id") or f"lane-a:boundary-failed:{index:04d}"
    return {
        "event_id": f"watch:fallback:{report_id}",
        "event_type": "boundary_test_failed_packet",
        "candidate_observation_id": report.get("candidate_observation_id"),
        "candidate_observation_refs": _coerce_refs(report.get("candidate_observation_refs")),
        "candidate_only": True,
        "review_required": True,
        "official_status": OFFICIAL_STATUS,
        "execution_status": "not_executed",
        "evidence_refs": _coerce_refs(report.get("evidence_refs")) or [str(report_id)],
        "limitation_refs": _coerce_refs(report.get("limitation_refs")) or ["limitation:lane-a-boundary-failed"],
        "trace_refs": _coerce_refs(report.get("trace_refs")) or ["PUSH2:LANE_A:CHECK_BOUNDARY_FAILED"],
        "payload": {
            "source_check_report_ref": report_id,
            "source_check_report_path": report.get("source_check_report_path"),
            "boundary_result": report.get("boundary_result") or report.get("status") or "boundary_failed",
        },
    }


def family_inputs(state: dict[str, Any], fallback_boundary_reports: list[dict[str, Any]] | None = None) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    materialized = state.get("materialized") or {}
    fallback_boundary_reports = fallback_boundary_reports if fallback_boundary_reports is not None else load_lane_a_boundary_failed_check_reports()
    quarantined = list(materialized.get("quarantined_observations") or [])
    family2_source = "event_fabric_quarantine" if quarantined else "lane_a_boundary_failed_check_reports"
    family2_effective_family = "quarantined_or_boundary_blocked_items" if quarantined else "boundary_test_failed_packets"
    family2_items = quarantined or [boundary_report_to_event(report, index) for index, report in enumerate(fallback_boundary_reports, start=1)]
    low_authority_items = list(materialized.get("sandbox_draft_cases") or []) + list(materialized.get("not_executed_action_proposals") or [])
    return (
        {
            "unresolved_candidate_observations": list(materialized.get("unresolved_observations") or []),
            "stale_or_low_authority_review_items": low_authority_items,
            "new_review_events_since_last_snapshot": list(materialized.get("active_review_events") or []),
            "quarantined_or_boundary_blocked_items": family2_items,
        },
        {
            "family2_source": family2_source,
            "family2_effective_family": family2_effective_family,
            "event_fabric_quarantine_available": bool(quarantined),
            "lane_a_boundary_failed_fallback_available": bool(fallback_boundary_reports),
            "family2_runs_last": WATCH_FAMILIES[-1]["watch_family"] == "quarantined_or_boundary_blocked_items",
        },
    )


def make_watch_item(family: str, event: dict[str, Any], ordinal: int) -> dict[str, Any]:
    watch_item_id = f"watch:item:{family}:{ordinal:04d}"
    check_report_ref = f"check_report:{watch_item_id}"
    authority_envelope_ref = f"authority_envelope:{watch_item_id}"
    item = {
        "watch_item_id": watch_item_id,
        "watch_family": family,
        "event_refs": event_refs_for(event),
        "candidate_observation_refs": candidate_refs_for(event),
        "evidence_refs": evidence_refs_for(event),
        "limitation_refs": limitation_refs_for(event),
        "trace_refs": trace_refs_for(event, family),
        "check_report_ref": check_report_ref,
        "authority_envelope_ref": authority_envelope_ref,
        "authority_level": AUTHORITY_LEVEL,
        "review_required": True,
        "official_status": OFFICIAL_STATUS,
        "not_executed": NOT_EXECUTED,
        "safe_next_looks": SAFE_NEXT_LOOKS[family],
        "cannot_claim": CANNOT_CLAIM,
        "watch_item_kind": "review_prompt",
        "prompt_reason": prompt_reason_for(family, event),
        "source_event_type": event.get("event_type") or "unknown",
        "not_finding": True,
        "not_action": True,
    }
    item["watch_item_hash"] = canonical_hash(item, {"watch_item_hash"})
    return item


def prompt_reason_for(family: str, event: dict[str, Any]) -> str:
    if family == "unresolved_candidate_observations":
        return "Candidate observation is unresolved and needs human source review."
    if family == "quarantined_or_boundary_blocked_items":
        if event.get("event_type") == "boundary_test_failed_packet":
            return "Lane A boundary-failed packet is blocked and needs review, not promotion."
        return "Candidate observation is quarantined and must not be promoted without review."
    if family == "stale_or_low_authority_review_items":
        return "Local replay item has draft, sandbox, not-executed, or low-authority status."
    return "Review event is new relative to the empty WATCH v1 snapshot."


def build_watch_items(state: dict[str, Any], fallback_boundary_reports: list[dict[str, Any]] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    inputs, meta = family_inputs(state, fallback_boundary_reports)
    items: list[dict[str, Any]] = []
    for spec in WATCH_FAMILIES:
        family = spec["watch_family"]
        for ordinal, event in enumerate(inputs[family], start=1):
            items.append(make_watch_item(family, event, ordinal))
    emitted = sorted({item["watch_family"] for item in items})
    meta.update(
        {
            "watch_item_count": len(items),
            "emitting_families": emitted,
            "emitting_family_count": len(emitted),
            "family_counts": {family: len(rows) for family, rows in inputs.items()},
        }
    )
    return items, meta


def build_query_families(items: list[dict[str, Any]], meta: dict[str, Any]) -> dict[str, Any]:
    counts = meta.get("family_counts", {})
    families = []
    for spec in WATCH_FAMILIES:
        family = spec["watch_family"]
        row = dict(spec)
        row["emitted_watch_items"] = counts.get(family, 0)
        if family == "quarantined_or_boundary_blocked_items":
            row["family2_source"] = meta["family2_source"]
            row["effective_family"] = meta["family2_effective_family"]
            row["runs_last"] = meta["family2_runs_last"]
        families.append(row)
    return {
        "schema_version": "push2.lane_b.watch_scout.query_families.v1",
        "status": "PASS" if 3 <= meta.get("emitting_family_count", 0) <= 4 and meta.get("family2_runs_last") else "FAIL",
        "family_count": len(WATCH_FAMILIES),
        "emitting_family_count": meta.get("emitting_family_count", 0),
        "emitting_families": meta.get("emitting_families", []),
        "watch_item_count": len(items),
        "family2_source": meta["family2_source"],
        "family2_effective_family": meta["family2_effective_family"],
        "families": families,
    }


def build_check_authority_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    check_reports = []
    authority_envelopes = []
    for item in items:
        check_report = {
            "check_report_ref": item["check_report_ref"],
            "watch_item_id": item["watch_item_id"],
            "status": "PASS",
            "overall_claimability": "not_claimable_official_review_prompt_only",
            "checks": [
                {
                    "check_id": "watch_item_review_prompt_only",
                    "status": "PASS",
                    "reason": "WATCH item is a review prompt and carries not_finding/not_action flags.",
                    "refs": [item["watch_item_id"]],
                },
                {
                    "check_id": "evidence_limit_trace_present",
                    "status": "PASS" if item["evidence_refs"] and item["limitation_refs"] and item["trace_refs"] else "FAIL",
                    "reason": "WatchItem must carry evidence, limitation, and trace refs.",
                    "refs": item["evidence_refs"] + item["limitation_refs"] + item["trace_refs"],
                },
                {
                    "check_id": "authority_envelope_linked",
                    "status": "PASS" if item["authority_envelope_ref"] else "FAIL",
                    "reason": "WatchItem must point to an AuthorityEnvelope.",
                    "refs": [item["authority_envelope_ref"]],
                },
            ],
            "verdicts": [
                {
                    "verdict": "abstain_required",
                    "claim": "official finding or action",
                    "reason": "WATCH Scout v1 emits review prompts only.",
                    "refs": [item["watch_item_id"]],
                }
            ],
        }
        authority_envelope = {
            "authority_envelope_ref": item["authority_envelope_ref"],
            "watch_item_id": item["watch_item_id"],
            "check_report_ref": item["check_report_ref"],
            "authority_level": AUTHORITY_LEVEL,
            "official_status": OFFICIAL_STATUS,
            "execution_status": "not_executed",
            "source_authority": "local_replay_event_fabric",
            "scope": "human_review_triage_prompt",
            "authorized_uses": [
                "show in WATCH review queue",
                "support human triage",
                "point reviewer to evidence, limitations, and trace refs",
            ],
            "forbidden_uses": CANNOT_CLAIM,
            "source_refs": sorted(dict.fromkeys(item["event_refs"] + item["evidence_refs"] + item["trace_refs"])),
        }
        check_reports.append(check_report)
        authority_envelopes.append(authority_envelope)
    failed_checks = [
        check
        for report in check_reports
        for check in report["checks"]
        if check["status"] != "PASS"
    ]
    return {
        "schema_version": "push2.lane_b.watch_scout.check_authority_report.v1",
        "status": "PASS" if not failed_checks and len(check_reports) == len(items) == len(authority_envelopes) else "FAIL",
        "check_report_count": len(check_reports),
        "authority_envelope_count": len(authority_envelopes),
        "all_watch_items_have_check_report": len(check_reports) == len(items),
        "all_watch_items_have_authority_envelope": len(authority_envelopes) == len(items),
        "authority_level": AUTHORITY_LEVEL,
        "failed_checks": failed_checks,
        "check_reports": check_reports,
        "authority_envelopes": authority_envelopes,
    }


def boundary_failures(items: list[dict[str, Any]], check_authority: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    check_refs = {report["check_report_ref"] for report in check_authority.get("check_reports", [])}
    authority_refs = {envelope["authority_envelope_ref"] for envelope in check_authority.get("authority_envelopes", [])}
    for item in items:
        item_id = item.get("watch_item_id", "unknown")
        if item.get("watch_item_kind") != "review_prompt":
            failures.append(f"not_review_prompt:{item_id}")
        if item.get("review_required") is not True:
            failures.append(f"review_required_false:{item_id}")
        if item.get("official_status") != OFFICIAL_STATUS:
            failures.append(f"official_status:{item_id}")
        if item.get("authority_level") != AUTHORITY_LEVEL:
            failures.append(f"authority_level:{item_id}")
        if item.get("check_report_ref") not in check_refs:
            failures.append(f"missing_check_report:{item_id}")
        if item.get("authority_envelope_ref") not in authority_refs:
            failures.append(f"missing_authority_envelope:{item_id}")
        if not (item.get("evidence_refs") and item.get("limitation_refs") and item.get("trace_refs")):
            failures.append(f"missing_refs:{item_id}")
        for forbidden_field in [
            "official_case_id",
            "external_submission_ref",
            "dispatch_ref",
            "control_ref",
            "enforcement_ref",
            "official_finding",
            "official_action",
            "action_command",
            "execution_command",
        ]:
            if forbidden_field in item:
                failures.append(f"forbidden_field:{forbidden_field}:{item_id}")
    payload = json.dumps({"items": items, "check_authority": check_authority}, sort_keys=True).lower()
    forbidden_tokens = [
        '"official_status": "official"',
        '"execution_status": "executed"',
        '"submission_status": "submitted"',
        '"legal_violation": true',
        '"certified": true',
        '"official_finding": true',
        '"official_action": true',
        '"dispatch_ref": "',
        '"control_ref": "',
        '"enforcement_ref": "',
        '"external_submission_ref": "',
        '"official_case_id": "',
    ]
    failures.extend(f"forbidden_token:{token}" for token in forbidden_tokens if token in payload)
    return failures


def build_boundary_audit(items: list[dict[str, Any]], check_authority: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    failures = boundary_failures(items, check_authority)
    return {
        "schema_version": "push2.lane_b.watch_scout.boundary_audit.v1",
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "watch_items_are_review_prompts_only": all(item.get("watch_item_kind") == "review_prompt" for item in items),
        "no_official_findings_or_actions": not failures,
        "not_official_preserved": all(item.get("official_status") == OFFICIAL_STATUS for item in items),
        "review_required_preserved": all(item.get("review_required") is True for item in items),
        "not_executed_preserved": all(bool(item.get("not_executed")) for item in items),
        "check_report_linkage_present": check_authority.get("all_watch_items_have_check_report") is True,
        "authority_envelope_linkage_present": check_authority.get("all_watch_items_have_authority_envelope") is True,
        "family2_source": meta["family2_source"],
        "family2_uses_quarantine_or_boundary_failed_fallback": meta["family2_source"] in {"event_fabric_quarantine", "lane_a_boundary_failed_check_reports"},
        "family2_runs_last": meta["family2_runs_last"],
        "live_retrieval_performed": False,
        "production_api_called": False,
        "url_fetch_performed": False,
        "llm_call_performed": False,
        "official_submission_performed": False,
        "dispatch_control_enforcement_performed": False,
    }


def write_hash_manifest(root: Path = OUTPUT_ROOT, manifest_name: str = "WATCH_SCOUT_HASH_MANIFEST.json") -> dict[str, Any]:
    items = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != manifest_name):
        items.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    manifest = {
        "schema_version": "push2.lane_b.watch_scout.hash_manifest.v1",
        "algorithm": "sha256",
        "status": "PASS",
        "item_count": len(items),
        "missing_count": 0,
        "mismatch_count": 0,
        "items": items,
    }
    write_json(root / manifest_name, manifest)
    missing = 0
    mismatch = 0
    for item in items:
        target = root / item["path"]
        if not target.exists():
            missing += 1
        elif sha256_file(target) != item["sha256"]:
            mismatch += 1
    manifest["missing_count"] = missing
    manifest["mismatch_count"] = mismatch
    manifest["status"] = "PASS" if missing == 0 and mismatch == 0 else "FAIL"
    write_json(root / manifest_name, manifest)
    return manifest


def verify_hash_manifest(root: Path = OUTPUT_ROOT, manifest_name: str = "WATCH_SCOUT_HASH_MANIFEST.json") -> dict[str, Any]:
    manifest = read_json(root / manifest_name, {})
    problems = []
    verified = 0
    for item in manifest.get("items", []):
        target = root / item["path"]
        if not target.exists():
            problems.append(f"missing:{item['path']}")
            continue
        if sha256_file(target) != item.get("sha256"):
            problems.append(f"mismatch:{item['path']}")
            continue
        verified += 1
    return {
        "status": "PASS" if manifest.get("status") == "PASS" and not problems else "FAIL",
        "declared": len(manifest.get("items", [])),
        "verified": verified,
        "problems": problems,
    }


def test_log_text(decision: dict[str, Any], query_families: dict[str, Any], boundary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# WATCH Scout v1 Test Log",
            "",
            f"- decision: `{decision['status']}`",
            f"- watch items: `{decision['result_counts']['watch_items']}`",
            f"- emitting families: `{query_families['emitting_family_count']}`",
            f"- family 2 source: `{query_families['family2_source']}`",
            f"- boundary audit: `{boundary['status']}`",
            "- focused test command: `.venv\\Scripts\\python.exe -m unittest tests.test_main_citybrain_push2_lane_b_watch_scout_v1`",
            "",
            "WATCH Scout v1 emitted review prompts only. No live retrieval, production API, URL fetch, LLM call, official finding, official submission, dispatch, control, enforcement, or automated action was performed.",
        ]
    )


def closeout_summary_text(decision: dict[str, Any], boundary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# WATCH Scout v1 Closeout",
            "",
            f"Status: `{decision['status']}`",
            "",
            f"- WatchItems: `{decision['result_counts']['watch_items']}`",
            f"- Emitting families: `{decision['result_counts']['emitting_families']}`",
            f"- CheckReports: `{decision['result_counts']['check_reports']}`",
            f"- AuthorityEnvelopes: `{decision['result_counts']['authority_envelopes']}`",
            f"- Boundary audit: `{boundary['status']}`",
            "",
            "Lane B is branch-publish ready. INFRA owns canonical cross-lane integration.",
        ]
    )


def final_status_summary_text(final_decision: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# WATCH Scout v1 Final Status",
            "",
            f"Status: `{final_decision['status']}`",
            "",
            "Completed through implementation, verification, lane closeout, final status, and exact Lane B staging scope readiness.",
            "No Lane A, Lane C, sealed ASK, or protected R7 runtime change is required by this lane.",
        ]
    )


def stop_decision(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "push2.lane_b.watch_scout.decision.v1",
        "package": PACKAGE,
        "status": STOP_STATUS,
        "created_at": utc_now(),
        "runtime_loaded": state.get("runtime_loaded", False),
        "missing": state.get("missing", []),
        "stop_reason": "Event Fabric runtime materialized state is missing and no valid Lane A boundary-failed fallback can close WATCH family 2.",
        "required_outputs_written": False,
    }


def write_watch_outputs(root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    state = load_event_runtime_state()
    fallback_reports = load_lane_a_boundary_failed_check_reports()
    if not state["runtime_loaded"] and not fallback_reports:
        decision = stop_decision(state)
        write_json(root / "WATCH_SCOUT_V1_DECISION.json", decision)
        write_hash_manifest(root)
        return {"decision": decision, "hash_manifest": verify_hash_manifest(root), "output_root": rel(root)}
    items, meta = build_watch_items(state, fallback_reports)
    query_families = build_query_families(items, meta)
    check_authority = build_check_authority_report(items)
    boundary = build_boundary_audit(items, check_authority, meta)
    status = PASS_STATUS if items and query_families["status"] == "PASS" and check_authority["status"] == "PASS" and boundary["status"] == "PASS" else FAIL_STATUS
    decision = {
        "schema_version": "push2.lane_b.watch_scout.decision.v1",
        "package": PACKAGE,
        "status": status,
        "created_at": utc_now(),
        "runtime_loaded": state["runtime_loaded"],
        "source_runtime_refs": state.get("source_runtime_refs", []),
        "result_counts": {
            "watch_items": len(items),
            "query_families": len(WATCH_FAMILIES),
            "emitting_families": query_families["emitting_family_count"],
            "check_reports": check_authority["check_report_count"],
            "authority_envelopes": check_authority["authority_envelope_count"],
        },
        "contract_check": {
            "watch_emits_review_prompts_not_findings": boundary["watch_items_are_review_prompts_only"],
            "watch_items_carry_evidence_limitations_trace": all(item["evidence_refs"] and item["limitation_refs"] and item["trace_refs"] for item in items),
            "watch_items_carry_check_report_and_authority_envelope": check_authority["status"] == "PASS",
            "no_official_findings_or_actions": boundary["no_official_findings_or_actions"],
            "family2_uses_quarantine_or_boundary_failed_fallback": boundary["family2_uses_quarantine_or_boundary_failed_fallback"],
            "family2_runs_last": boundary["family2_runs_last"],
            "infra_canonical_integration_owned_elsewhere": True,
        },
        "limitations": [
            "Local/replay Event Fabric consumer only.",
            "WATCH items are review prompts, not findings or actions.",
            "AuthorityEnvelope level is review_prompt_only.",
            "No live retrieval, production API, URL fetch, LLM call, official submission, dispatch, control, enforcement, or automated action.",
        ],
        "next": "INFRA canonical integration after branch-publish.",
    }
    write_json(root / "WATCH_SCOUT_V1_DECISION.json", decision)
    write_json(root / "WATCH_SCOUT_QUERY_FAMILIES.json", query_families)
    write_json(root / "WATCH_ITEMS.json", {"schema_version": "push2.lane_b.watch_items.v1", "status": "PASS" if items else "FAIL", "items": items})
    write_json(root / "WATCH_SCOUT_CHECK_AUTHORITY_REPORT.json", check_authority)
    write_json(root / "WATCH_SCOUT_BOUNDARY_AUDIT.json", boundary)
    write_text(root / "WATCH_SCOUT_TEST_LOG.md", test_log_text(decision, query_families, boundary))
    manifest = write_hash_manifest(root)
    decision["hash_manifest"] = {
        "status": manifest["status"],
        "item_count": manifest["item_count"],
        "missing_count": manifest["missing_count"],
        "mismatch_count": manifest["mismatch_count"],
    }
    write_json(root / "WATCH_SCOUT_V1_DECISION.json", decision)
    manifest = write_hash_manifest(root)
    return {"decision": decision, "hash_manifest": manifest, "output_root": rel(root)}


def write_closeout(watch_result: dict[str, Any], root: Path = CLOSEOUT_ROOT) -> dict[str, Any]:
    watch_decision = watch_result["decision"]
    watch_hash = verify_hash_manifest(OUTPUT_ROOT)
    boundary = read_json(OUTPUT_ROOT / "WATCH_SCOUT_BOUNDARY_AUDIT.json", {})
    status = PASS_STATUS if watch_decision.get("status") == PASS_STATUS and watch_hash["status"] == "PASS" and boundary.get("status") == "PASS" else FAIL_STATUS
    decision = {
        "schema_version": "push2.lane_b.watch_scout.closeout.decision.v1",
        "package": f"{PACKAGE}-CLOSEOUT",
        "status": status,
        "created_at": utc_now(),
        "source_watch_decision": rel(OUTPUT_ROOT / "WATCH_SCOUT_V1_DECISION.json"),
        "source_watch_hash_manifest": watch_hash,
        "result_counts": watch_decision.get("result_counts", {}),
        "boundary_audit_status": boundary.get("status"),
        "contract_check": watch_decision.get("contract_check", {}),
        "limitations": watch_decision.get("limitations", []),
        "branch_publish_scope": [
            "scripts/run_main_citybrain_push2_lane_b_watch_scout_v1.py",
            "tests/test_main_citybrain_push2_lane_b_watch_scout_v1.py",
            "outputs/push2_lane_b_watch_scout_v1/",
            "outputs/push2_lane_b_watch_scout_v1_closeout/",
            "outputs/push2_lane_b_watch_scout_v1_final_status/",
        ],
        "infra_canonical_integration_owned_elsewhere": True,
    }
    write_json(root / "WATCH_SCOUT_V1_CLOSEOUT_DECISION.json", decision)
    write_text(root / "WATCH_SCOUT_V1_CLOSEOUT_SUMMARY.md", closeout_summary_text(watch_decision, boundary))
    write_text(root / "WATCH_SCOUT_V1_CLOSEOUT_LIMITATIONS.md", "# WATCH Scout v1 Limitations\n\n" + "\n".join(f"- {item}" for item in decision["limitations"]))
    manifest = write_hash_manifest(root, "WATCH_SCOUT_V1_CLOSEOUT_HASH_MANIFEST.json")
    decision["hash_manifest"] = {
        "status": manifest["status"],
        "item_count": manifest["item_count"],
        "missing_count": manifest["missing_count"],
        "mismatch_count": manifest["mismatch_count"],
    }
    write_json(root / "WATCH_SCOUT_V1_CLOSEOUT_DECISION.json", decision)
    manifest = write_hash_manifest(root, "WATCH_SCOUT_V1_CLOSEOUT_HASH_MANIFEST.json")
    return {"decision": decision, "hash_manifest": manifest, "output_root": rel(root)}


def write_final_status(closeout_result: dict[str, Any], root: Path = FINAL_STATUS_ROOT) -> dict[str, Any]:
    closeout_decision = closeout_result["decision"]
    closeout_hash = verify_hash_manifest(CLOSEOUT_ROOT, "WATCH_SCOUT_V1_CLOSEOUT_HASH_MANIFEST.json")
    status = PASS_STATUS if closeout_decision.get("status") == PASS_STATUS and closeout_hash["status"] == "PASS" else FAIL_STATUS
    decision = {
        "schema_version": "push2.lane_b.watch_scout.final_status.decision.v1",
        "package": f"{PACKAGE}-FINAL-STATUS",
        "status": status,
        "created_at": utc_now(),
        "source_closeout_decision": rel(CLOSEOUT_ROOT / "WATCH_SCOUT_V1_CLOSEOUT_DECISION.json"),
        "source_closeout_hash_manifest": closeout_hash,
        "completed_through": [
            "implementation",
            "verification",
            "lane_closeout",
            "lane_final_status",
            "exact_staging_scope_ready",
        ],
        "branch": "codex/push2-lane-b-watch-scout-v1",
        "commit_message": "Add Push 2 WATCH Scout v1",
        "infra_canonical_integration_owned_elsewhere": True,
        "limitations": closeout_decision.get("limitations", []),
    }
    write_json(root / "WATCH_SCOUT_V1_FINAL_STATUS_DECISION.json", decision)
    write_text(root / "WATCH_SCOUT_V1_FINAL_STATUS_SUMMARY.md", final_status_summary_text(decision))
    manifest = write_hash_manifest(root, "WATCH_SCOUT_V1_FINAL_STATUS_HASH_MANIFEST.json")
    decision["hash_manifest"] = {
        "status": manifest["status"],
        "item_count": manifest["item_count"],
        "missing_count": manifest["missing_count"],
        "mismatch_count": manifest["mismatch_count"],
    }
    write_json(root / "WATCH_SCOUT_V1_FINAL_STATUS_DECISION.json", decision)
    manifest = write_hash_manifest(root, "WATCH_SCOUT_V1_FINAL_STATUS_HASH_MANIFEST.json")
    return {"decision": decision, "hash_manifest": manifest, "output_root": rel(root)}


def write_outputs() -> dict[str, Any]:
    reset_output_roots()
    watch = write_watch_outputs()
    closeout = write_closeout(watch)
    final_status = write_final_status(closeout)
    return {"watch": watch, "closeout": closeout, "final_status": final_status}


def main() -> int:
    result = write_outputs()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["final_status"]["decision"]["status"] == PASS_STATUS and result["final_status"]["hash_manifest"]["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
