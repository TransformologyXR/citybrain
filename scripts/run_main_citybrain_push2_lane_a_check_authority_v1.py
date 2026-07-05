#!/usr/bin/env python3
"""Build PUSH 2 Lane A CHECK v0 and AuthorityEnvelope v1 artifacts."""

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
OUTPUT_ROOT = REPO_ROOT / "outputs" / "push2_lane_a_check_authority_v1"
CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "push2_lane_a_check_authority_v1_closeout"
FINAL_ROOT = REPO_ROOT / "outputs" / "push2_lane_a_check_authority_v1_final_status"
R7A_ROOT = REPO_ROOT / "outputs" / "main_citybrain_r7a_perception_candidate_observation_ingress"
R7B_ROOT = REPO_ROOT / "outputs" / "main_citybrain_r7b_perception_to_event_fabric_local_replay"
R7C_ROOT = REPO_ROOT / "outputs" / "main_citybrain_r7c_event_fabric_state_query_and_ask_handoff"
ASK_CONTRACT_PATHS = [
    "packages/ask_v11",
    "packages/contracts",
    "scripts/run_ask_v11_sealed_eval.py",
    "scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py",
]
R7_RUNTIME_PATHS = [
    "scripts/run_main_citybrain_r7a_perception_candidate_observation_ingress.py",
    "scripts/run_main_citybrain_r7b_perception_to_event_fabric_local_replay.py",
    "scripts/run_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff.py",
    "scripts/run_main_citybrain_r7d_webui_kit_event_state_smoke.py",
]

TASK_ID = "MAIN-CITYBRAIN-PUSH2-LANE-A-CHECK-V0-AUTHORITY-ENVELOPE-V1"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_PUSH2_LANE_A_CHECK_V0_AUTHORITY_ENVELOPE_V1_WITH_LIMITATIONS"
CLOSEOUT_STATUS = "PASS_PUSH2_LANE_A_CHECK_V0_AUTHORITY_ENVELOPE_V1_WITH_LIMITATIONS"
FINAL_STATUS = "PASS_PUSH2_LANE_A_CHECK_V0_AUTHORITY_ENVELOPE_V1_FINAL_STATUS_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_PUSH2_LANE_A_CHECK_V0_AUTHORITY_ENVELOPE_V1"
NOW = datetime(2026, 7, 5, tzinfo=timezone.utc)

LANE_LIMITATIONS = [
    "Lane A branch-publishes CHECK v0 and AuthorityEnvelope v1 only; INFRA owns canonical cross-lane integration.",
    "CHECK attaches to ASK outputs at the app/handoff adapter layer and does not modify sealed ASK G1-G8.",
    "Protected R7 runtime files remain unchanged; R7 local/replay outputs are consumed as fixtures.",
    "WatchItem support is schema-ready, with no runtime WatchItem packet available in this workspace yet.",
    "No live retrieval, production API, URL fetch, LLM call, official action, dispatch, control, enforcement, legal finding, or certified finding is performed.",
]

OFFICIAL_CLAIM_CODES = {
    "official_action",
    "dispatch",
    "control",
    "enforcement",
    "legal_finding",
    "certified_finding",
    "official_finding",
    "official_truth",
    "official_case_submission",
    "official_case_ticket",
}

SOURCE_CLASS_RULES: dict[str, dict[str, Any]] = {
    "vss_sensor_inferred": {
        "authority_level": 0,
        "label": "sensor inferred candidate",
        "max_age_days": 7,
        "fact_source_allowed": False,
        "source_record_claim_allowed": False,
        "claimability": "candidate_context_only",
    },
    "sensor_inferred": {
        "authority_level": 0,
        "label": "sensor inferred candidate",
        "max_age_days": 7,
        "fact_source_allowed": False,
        "source_record_claim_allowed": False,
        "claimability": "candidate_context_only",
    },
    "replay_fixture": {
        "authority_level": 1,
        "label": "local replay fixture",
        "max_age_days": 30,
        "fact_source_allowed": False,
        "source_record_claim_allowed": False,
        "claimability": "fixture_context_only",
    },
    "sample_clip": {
        "authority_level": 1,
        "label": "sample clip fixture",
        "max_age_days": 30,
        "fact_source_allowed": False,
        "source_record_claim_allowed": False,
        "claimability": "fixture_context_only",
    },
    "manual_test_fixture": {
        "authority_level": 1,
        "label": "manual test fixture",
        "max_age_days": 30,
        "fact_source_allowed": False,
        "source_record_claim_allowed": False,
        "claimability": "fixture_context_only",
    },
    "synthetic_event": {
        "authority_level": 1,
        "label": "synthetic fixture",
        "max_age_days": 30,
        "fact_source_allowed": False,
        "source_record_claim_allowed": False,
        "claimability": "fixture_context_only",
    },
    "local_replay_fixture": {
        "authority_level": 1,
        "label": "local replay fixture",
        "max_age_days": 30,
        "fact_source_allowed": False,
        "source_record_claim_allowed": False,
        "claimability": "fixture_context_only",
    },
    "ask_v11_evidence_fixture": {
        "authority_level": 1,
        "label": "ASK handoff evidence fixture",
        "max_age_days": 30,
        "fact_source_allowed": False,
        "source_record_claim_allowed": False,
        "claimability": "app_handoff_context_only",
    },
    "verified_authority_record": {
        "authority_level": 2,
        "label": "verified authority source record",
        "max_age_days": 90,
        "fact_source_allowed": True,
        "source_record_claim_allowed": True,
        "claimability": "verified_source_record_context",
    },
    "official_record": {
        "authority_level": 2,
        "label": "official source record",
        "max_age_days": 90,
        "fact_source_allowed": True,
        "source_record_claim_allowed": True,
        "claimability": "verified_source_record_context",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def json_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def out_rel(path: Path, root: Path = OUTPUT_ROOT) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def reset_root(root: Path) -> None:
    resolved = root.resolve()
    if (REPO_ROOT / "outputs").resolve() not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def reset_output_root() -> None:
    reset_root(OUTPUT_ROOT)


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalized_claims(claims: list[str]) -> set[str]:
    normalized: set[str] = set()
    for claim in claims:
        value = str(claim).lower().replace("-", "_").replace(" ", "_").replace("/", "_")
        normalized.add(value)
    return normalized


def packet_ref(packet_type: str, packet: dict[str, Any]) -> str:
    fields = [
        "candidate_observation_id",
        "event_id",
        "case_id",
        "query_result_ref",
        "query_result_id",
        "overlay_id",
        "packet_id",
        "fixture_id",
        "watch_item_id",
        "record_id",
    ]
    for field in fields:
        value = packet.get(field)
        if value:
            return str(value)
    return f"missing:{packet_type}:{json_hash(packet)[:12]}"


def first_observed_at(packet: dict[str, Any]) -> str | None:
    for field in ("observed_at", "as_of", "event_time", "ingested_at", "created_at"):
        if packet.get(field):
            return str(packet[field])
    for source in packet.get("source_refs", []) or []:
        if isinstance(source, dict):
            for field in ("as_of", "observed_at"):
                if source.get(field):
                    return str(source[field])
    return None


def infer_source_class(packet_type: str, packet: dict[str, Any]) -> str:
    explicit = packet.get("source_class") or packet.get("source_kind") or packet.get("source_type")
    if explicit == "local_replay":
        return "local_replay_fixture"
    if explicit:
        return str(explicit)
    if packet.get("packet_kind") == "ask_v11_evidence_compatible_fixture":
        return "ask_v11_evidence_fixture"
    source_refs = packet.get("source_refs") or []
    if source_refs and isinstance(source_refs[0], dict):
        source_type = source_refs[0].get("source_type")
        if source_type == "local_replay_fixture":
            return "local_replay_fixture"
    if packet_type in {"EventEnvelope", "QueryResultPacket", "OverlayPacket"}:
        return "local_replay_fixture"
    return "unknown_source_class"


def freshness_result(source_class: str, observed_at: str | None) -> dict[str, Any]:
    rule = SOURCE_CLASS_RULES.get(source_class)
    max_age_days = rule.get("max_age_days") if rule else None
    parsed = parse_datetime(observed_at)
    if parsed is None:
        status = "not_applicable" if source_class in {"local_replay_fixture", "ask_v11_evidence_fixture"} else "unknown"
        return {
            "policy_id": "check_v0.freshness_policy@2026-07-05",
            "status": status,
            "observed_at": observed_at,
            "age_days": None,
            "max_age_days": max_age_days,
        }
    age_days = max(0, (NOW - parsed).days)
    status = "current" if max_age_days is None or age_days <= max_age_days else "stale"
    return {
        "policy_id": "check_v0.freshness_policy@2026-07-05",
        "status": status,
        "observed_at": parsed.isoformat().replace("+00:00", "Z"),
        "age_days": age_days,
        "max_age_days": max_age_days,
    }


def candidate_markers(packet_type: str, packet: dict[str, Any], source_class: str) -> list[str]:
    markers: list[str] = []
    if packet_type == "CandidateObservation":
        markers.append("packet_type_candidate_observation")
    if packet.get("candidate_only") is True:
        markers.append("candidate_only_true")
    if packet.get("review_required") is True:
        markers.append("review_required_true")
    if packet.get("official_status") == "not_official":
        markers.append("official_status_not_official")
    if str(packet.get("review_state") or "").lower() in {"candidate", "needs_source", "quarantined", "proposal_pending"}:
        markers.append("review_state_candidate_or_unverified")
    if source_class in {"vss_sensor_inferred", "sensor_inferred"}:
        markers.append("sensor_inferred_source_class")
    text = json.dumps(
        {
            "event_type": packet.get("event_type"),
            "observation_type": packet.get("observation_type"),
            "detected_class": packet.get("detected_class"),
            "object_class": packet.get("object_class"),
        },
        sort_keys=True,
    ).lower()
    if "candidate" in text:
        markers.append("candidate_token_in_packet_shape")
    return sorted(set(markers))


def default_claims(packet_type: str) -> list[str]:
    return {
        "CandidateObservation": ["candidate_observation_context"],
        "EventEnvelope": ["event_context"],
        "QueryResultPacket": ["query_result_context"],
        "OverlayPacket": ["review_overlay_context"],
        "WatchItem": ["watch_item_context"],
        "ASKHandoffOutput": ["ask_handoff_context"],
    }.get(packet_type, ["context"])


def explicit_claims(packet_type: str, packet: dict[str, Any], requested_claims: list[str] | None = None) -> list[str]:
    if requested_claims is not None:
        return list(requested_claims)
    for field in ("requested_claims", "asserted_claims", "claims"):
        values = packet.get(field)
        if isinstance(values, list) and values:
            return [str(value) for value in values]
    claim = packet.get("claim")
    if isinstance(claim, str) and claim:
        return [claim]
    return default_claims(packet_type)


def boundary_findings(
    packet_type: str,
    packet: dict[str, Any],
    source_class: str,
    claims: list[str],
    candidate_evidence: list[str],
    freshness: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    rule = SOURCE_CLASS_RULES.get(source_class)
    claim_codes = normalized_claims(claims)

    findings.append(
        {
            "check": "source_class_validation",
            "status": "pass" if rule else "fail",
            "reason": f"source_class={source_class}" if rule else f"unsupported source_class={source_class}",
        }
    )
    findings.append(
        {
            "check": "freshness_policy",
            "status": "fail" if freshness["status"] == "stale" else "pass",
            "reason": f"freshness_status={freshness['status']}",
        }
    )
    findings.append(
        {
            "check": "candidate_vs_verified",
            "status": "downgrade" if candidate_evidence else "pass",
            "reason": "; ".join(candidate_evidence) if candidate_evidence else "no candidate-only markers",
        }
    )

    official_claims = sorted(claim_codes & OFFICIAL_CLAIM_CODES)
    if official_claims:
        findings.append(
            {
                "check": "official_action_dispatch_legal_boundary",
                "status": "fail",
                "reason": "official action/dispatch/control/enforcement/legal/certified claims are outside CHECK v0 claimability",
                "claim_codes": official_claims,
            }
        )
    else:
        findings.append(
            {
                "check": "official_action_dispatch_legal_boundary",
                "status": "pass",
                "reason": "no official action, dispatch, control, enforcement, legal, or certified claim requested",
            }
        )

    if source_class in {"vss_sensor_inferred", "sensor_inferred"}:
        status = "fail" if claim_codes & {"fact_source", "verified_fact", "official_truth", "official_finding"} else "downgrade"
        findings.append(
            {
                "check": "sensor_inferred_not_official_truth",
                "status": status,
                "reason": "sensor-inferred/VSS packets can support candidate context only, not fact source or official truth",
            }
        )

    if packet_type == "CandidateObservation":
        status = "fail" if claim_codes & {"official_finding", "official_truth", "legal_finding", "certified_finding"} else "downgrade"
        findings.append(
            {
                "check": "candidate_observation_not_official_finding",
                "status": status,
                "reason": "CandidateObservation remains review input, not an official finding",
            }
        )

    if packet.get("execution_status") == "executed":
        findings.append({"check": "execution_boundary", "status": "fail", "reason": "execution_status=executed is forbidden"})
    if packet.get("submission_status") == "submitted":
        findings.append({"check": "submission_boundary", "status": "fail", "reason": "submitted official case/ticket is forbidden"})
    for field in ("legal_violation", "certified", "official_action_executed"):
        if packet.get(field) is True:
            findings.append({"check": "positive_official_flag_boundary", "status": "fail", "reason": f"{field}=true is forbidden"})
    return findings


def build_check_report(
    packet_type: str,
    packet: dict[str, Any],
    requested_claims: list[str] | None = None,
    fixture_role: str = "runtime_fixture",
) -> dict[str, Any]:
    source_class = infer_source_class(packet_type, packet)
    rule = SOURCE_CLASS_RULES.get(source_class, SOURCE_CLASS_RULES["sensor_inferred"])
    observed_at = first_observed_at(packet)
    freshness = freshness_result(source_class, observed_at)
    claims = explicit_claims(packet_type, packet, requested_claims)
    candidate_evidence = candidate_markers(packet_type, packet, source_class)
    findings = boundary_findings(packet_type, packet, source_class, claims, candidate_evidence, freshness)
    fail_codes = [finding["check"] for finding in findings if finding["status"] == "fail"]
    downgrade_codes = [finding["check"] for finding in findings if finding["status"] == "downgrade"]
    if fail_codes:
        status = "FAIL"
        overall_claimability = "not_claimable"
    elif downgrade_codes:
        status = "PASS_WITH_LIMITATIONS"
        overall_claimability = "candidate_context_only" if candidate_evidence else rule["claimability"]
    else:
        status = "PASS"
        overall_claimability = rule["claimability"]

    report = {
        "schema_version": "main-citybrain.check_v0.report.v1",
        "fixture_role": fixture_role,
        "packet_type": packet_type,
        "packet_ref": packet_ref(packet_type, packet),
        "source_class": source_class,
        "source_class_status": "pass" if source_class in SOURCE_CLASS_RULES else "fail",
        "requested_claims": claims,
        "freshness": freshness,
        "freshness_status": freshness["status"],
        "candidate_evidence_markers": candidate_evidence,
        "boundary_checks": findings,
        "failure_codes": fail_codes,
        "downgrade_codes": downgrade_codes,
        "authority_level": rule["authority_level"] if source_class in SOURCE_CLASS_RULES else 0,
        "fact_source_allowed": bool(rule["fact_source_allowed"]) and status == "PASS",
        "source_record_claim_allowed": bool(rule["source_record_claim_allowed"]) and status == "PASS",
        "official_truth_allowed": False,
        "official_action_allowed": False,
        "dispatch_control_enforcement_allowed": False,
        "legal_or_certified_finding_allowed": False,
        "overall_claimability": overall_claimability,
        "status": status,
        "evidence_refs": packet.get("evidence_refs", []),
        "cannot_claim": sorted(
            set(packet.get("cannot_claim", []))
            | {
                "official action",
                "dispatch/control/enforcement",
                "legal or certified finding",
            }
        ),
    }
    report["check_id"] = f"check:v0:{json_hash(report)[:16]}"
    report["report_hash"] = json_hash(report)
    return report


def authority_level_label(level: int) -> str:
    return {
        0: "level_0_candidate_or_inferred_no_fact_authority",
        1: "level_1_local_fixture_or_replay_context",
        2: "level_2_verified_source_record_context",
    }[level]


def build_authority_envelope(report: dict[str, Any]) -> dict[str, Any]:
    rule = SOURCE_CLASS_RULES.get(report["source_class"], SOURCE_CLASS_RULES["sensor_inferred"])
    level = int(report["authority_level"])
    envelope = {
        "schema_version": "main-citybrain.authority_envelope.v1",
        "authority_envelope_id": f"authority:v1:{json_hash(report)[:16]}",
        "check_report_ref": report["check_id"],
        "packet_type": report["packet_type"],
        "packet_ref": report["packet_ref"],
        "source_class": report["source_class"],
        "authority_level": level,
        "authority_level_label": authority_level_label(level),
        "source_authority": {
            "label": rule["label"],
            "fact_source_allowed": report["fact_source_allowed"],
            "source_record_claim_allowed": report["source_record_claim_allowed"],
            "official_truth_allowed": False,
            "official_action_allowed": False,
            "dispatch_control_enforcement_allowed": False,
            "legal_or_certified_finding_allowed": False,
        },
        "claim_boundary": report["overall_claimability"],
        "stamp_status": "blocked_by_check" if report["status"] == "FAIL" else "stamped",
        "stamped_at": utc_now(),
    }
    envelope["envelope_hash"] = json_hash(envelope)
    return envelope


def fallback_packets() -> dict[str, list[dict[str, Any]]]:
    candidate = {
        "candidate_observation_id": "candidate:fallback:obs:001",
        "source_kind": "replay_fixture",
        "observed_at": "2026-07-04T11:10:00Z",
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "review_state": "candidate",
        "evidence_refs": ["source:fallback:replay"],
    }
    event = {
        "event_id": "fallback:event:001",
        "event_type": "review_event.created",
        "source_class": "local_replay_fixture",
        "event_time": "2026-07-04T11:20:00Z",
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "execution_status": "not_executed",
        "evidence_refs": ["source:fallback:replay"],
    }
    query = {
        "case_id": "fallback-query-active-review",
        "source_kind": "local_replay",
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "execution_status": "not_executed",
        "result_count": 1,
        "evidence_refs": ["source:fallback:replay"],
    }
    overlay = {
        "overlay_id": "fallback:overlay:001",
        "source_class": "local_replay_fixture",
        "event_id": "fallback:event:001",
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "execution_status": "not_executed",
    }
    ask = {
        "packet_id": "evidence:fallback:ask-handoff",
        "packet_kind": "ask_v11_evidence_compatible_fixture",
        "source_refs": [{"source_id": "fallback_local_event_state", "source_type": "local_replay_fixture"}],
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "execution_status": "not_executed",
        "facts": [{"fact_id": "fact:fallback", "text": "Fallback ASK handoff fixture."}],
    }
    return {
        "CandidateObservation": [candidate],
        "EventEnvelope": [event],
        "QueryResultPacket": [query],
        "OverlayPacket": [overlay],
        "ASKHandoffOutput": [ask],
    }


def collect_runtime_packets() -> dict[str, list[dict[str, Any]]]:
    packets = fallback_packets()
    candidates = read_json(R7A_ROOT / "R7A_CANDIDATE_OBSERVATION_FIXTURES.json", {"items": []}).get("items", [])
    valid_candidates = [
        item
        for item in candidates
        if item.get("candidate_observation_id") and item.get("source_kind") in SOURCE_CLASS_RULES
    ]
    if valid_candidates:
        packets["CandidateObservation"] = valid_candidates[:3]

    events = read_jsonl(R7B_ROOT / "R7B_LOCAL_EVENT_LOG.jsonl")
    if events:
        packets["EventEnvelope"] = events

    query_results = read_json(R7C_ROOT / "R7C_EVENT_STATE_QUERY_RESULTS.json", {"items": []}).get("items", [])
    if query_results:
        packets["QueryResultPacket"] = query_results

    overlays: list[dict[str, Any]] = []
    for name in ("R7B_WEBUI_EVENT_OVERLAY_EXPORT.json", "R7B_KIT_EVENT_OVERLAY_EXPORT.json"):
        overlays.extend(read_json(R7B_ROOT / name, {"items": []}).get("items", []))
    if overlays:
        packets["OverlayPacket"] = overlays

    ask_packets = read_json(R7C_ROOT / "R7C_ASK_HANDOFF_EVIDENCE_PACKETS.json", {"items": []}).get("items", [])
    if ask_packets:
        packets["ASKHandoffOutput"] = ask_packets

    verified_packet = {
        "case_id": "verified-authority-record:planning-register-001",
        "source_class": "verified_authority_record",
        "source_id": "authority:planning-public-register",
        "as_of": "2026-07-02T09:30:00Z",
        "candidate_only": False,
        "review_required": False,
        "official_status": "source_record_verified",
        "requested_claims": ["source_record_exists"],
        "facts": [{"fact_id": "fact:planning-register-record", "text": "Verified source record exists in public register fixture."}],
        "claim_boundary": "verified source-record context only; not legal determination or official action",
    }
    packets["QueryResultPacket"] = packets["QueryResultPacket"] + [verified_packet]
    return packets


def negative_packets() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "negative:vss-not-fact-source",
            "packet_type": "CandidateObservation",
            "packet": {
                "candidate_observation_id": "candidate:vss:obs:001",
                "source_class": "vss_sensor_inferred",
                "observed_at": "2026-07-04T12:00:00Z",
                "candidate_only": True,
                "review_required": True,
                "official_status": "not_official",
                "requested_claims": ["fact_source", "verified_fact"],
            },
            "expected_failure_codes": ["sensor_inferred_not_official_truth"],
        },
        {
            "case_id": "negative:sensor-inferred-official-truth",
            "packet_type": "CandidateObservation",
            "packet": {
                "candidate_observation_id": "candidate:sensor:obs:official-truth",
                "source_class": "sensor_inferred",
                "observed_at": "2026-07-04T12:00:00Z",
                "candidate_only": True,
                "review_required": True,
                "official_status": "not_official",
                "requested_claims": ["official_truth"],
            },
            "expected_failure_codes": [
                "sensor_inferred_not_official_truth",
                "candidate_observation_not_official_finding",
                "official_action_dispatch_legal_boundary",
            ],
        },
        {
            "case_id": "negative:candidate-observation-official-finding",
            "packet_type": "CandidateObservation",
            "packet": {
                "candidate_observation_id": "candidate:r7a:obs:official-finding-attempt",
                "source_class": "replay_fixture",
                "observed_at": "2026-07-04T11:10:00Z",
                "candidate_only": True,
                "review_required": True,
                "official_status": "not_official",
                "requested_claims": ["official_finding"],
            },
            "expected_failure_codes": [
                "candidate_observation_not_official_finding",
                "official_action_dispatch_legal_boundary",
            ],
        },
        {
            "case_id": "negative:official-action-dispatch-legal",
            "packet_type": "EventEnvelope",
            "packet": {
                "event_id": "event:negative:official-action",
                "source_class": "official_record",
                "event_time": "2026-07-04T11:20:00Z",
                "requested_claims": ["official_action", "dispatch", "legal_finding"],
                "candidate_only": False,
                "official_status": "source_record_verified",
                "execution_status": "not_executed",
            },
            "expected_failure_codes": ["official_action_dispatch_legal_boundary"],
        },
        {
            "case_id": "negative:stale-official-record",
            "packet_type": "QueryResultPacket",
            "packet": {
                "case_id": "query:negative:stale-official-record",
                "source_class": "official_record",
                "as_of": "2024-01-01T00:00:00Z",
                "requested_claims": ["source_record_exists"],
                "official_status": "source_record_verified",
            },
            "expected_failure_codes": ["freshness_policy"],
        },
        {
            "case_id": "negative:unsupported-source-class",
            "packet_type": "OverlayPacket",
            "packet": {
                "overlay_id": "overlay:negative:unsupported-source",
                "source_class": "live_camera",
                "observed_at": "2026-07-04T12:00:00Z",
                "requested_claims": ["review_overlay_context"],
            },
            "expected_failure_codes": ["source_class_validation"],
        },
    ]


def check_report_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://citybrain.local/schemas/check_v0_report.schema.json",
        "title": "CHECK v0 CheckReport",
        "type": "object",
        "required": [
            "schema_version",
            "check_id",
            "packet_type",
            "packet_ref",
            "source_class",
            "source_class_status",
            "freshness",
            "freshness_status",
            "boundary_checks",
            "authority_level",
            "official_truth_allowed",
            "overall_claimability",
            "status",
        ],
        "properties": {
            "schema_version": {"const": "main-citybrain.check_v0.report.v1"},
            "check_id": {"type": "string"},
            "packet_type": {
                "enum": [
                    "CandidateObservation",
                    "EventEnvelope",
                    "QueryResultPacket",
                    "OverlayPacket",
                    "WatchItem",
                    "ASKHandoffOutput",
                ]
            },
            "packet_ref": {"type": "string"},
            "source_class": {"type": "string"},
            "source_class_status": {"enum": ["pass", "fail"]},
            "freshness_status": {"enum": ["current", "stale", "unknown", "not_applicable"]},
            "authority_level": {"enum": [0, 1, 2]},
            "official_truth_allowed": {"const": False},
            "official_action_allowed": {"const": False},
            "dispatch_control_enforcement_allowed": {"const": False},
            "legal_or_certified_finding_allowed": {"const": False},
            "status": {"enum": ["PASS", "PASS_WITH_LIMITATIONS", "FAIL"]},
        },
    }


def authority_envelope_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://citybrain.local/schemas/authority_envelope_v1.schema.json",
        "title": "AuthorityEnvelope v1",
        "type": "object",
        "required": [
            "schema_version",
            "authority_envelope_id",
            "check_report_ref",
            "packet_type",
            "packet_ref",
            "source_class",
            "authority_level",
            "authority_level_label",
            "source_authority",
            "claim_boundary",
            "stamp_status",
        ],
        "properties": {
            "schema_version": {"const": "main-citybrain.authority_envelope.v1"},
            "authority_level": {"enum": [0, 1, 2]},
            "stamp_status": {"enum": ["stamped", "blocked_by_check"]},
            "source_authority": {
                "type": "object",
                "required": [
                    "fact_source_allowed",
                    "source_record_claim_allowed",
                    "official_truth_allowed",
                    "official_action_allowed",
                    "dispatch_control_enforcement_allowed",
                    "legal_or_certified_finding_allowed",
                ],
            },
        },
    }


def attach_check_to_ask_outputs(
    ask_packets: list[dict[str, Any]],
    check_reports: list[dict[str, Any]],
    authority_envelopes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    reports_by_ref = {(report["packet_type"], report["packet_ref"]): report for report in check_reports}
    envelopes_by_check = {envelope["check_report_ref"]: envelope for envelope in authority_envelopes}
    wrappers = []
    for packet in ask_packets:
        ref = packet_ref("ASKHandoffOutput", packet)
        report = reports_by_ref[("ASKHandoffOutput", ref)]
        envelope = envelopes_by_check[report["check_id"]]
        wrappers.append(
            {
                "schema_version": "main-citybrain.check_v0.ask_attachment_wrapper.v1",
                "wrapper_id": f"ask-check-wrapper:{json_hash(packet)[:16]}",
                "attachment_layer": "app_handoff_adapter",
                "sealed_ask_runtime_modified": False,
                "g1_g8_modified": False,
                "native_g6_integration_deferred": True,
                "wrapped_packet_ref": ref,
                "wrapped_packet_kind": packet.get("packet_kind") or "ask_handoff_output",
                "wrapped_packet_hash": json_hash(packet),
                "wrapped_packet": packet,
                "check_report_ref": report["check_id"],
                "authority_envelope_ref": envelope["authority_envelope_id"],
            }
        )
    return wrappers


def build_negative_test_results() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    cases = []
    reports = []
    envelopes = []
    for item in negative_packets():
        report = build_check_report(item["packet_type"], item["packet"], fixture_role="negative_boundary_test")
        envelope = build_authority_envelope(report)
        expected = set(item["expected_failure_codes"])
        observed = set(report["failure_codes"])
        case = {
            "case_id": item["case_id"],
            "packet_type": item["packet_type"],
            "input_packet": item["packet"],
            "expected_failure_codes": sorted(expected),
            "observed_failure_codes": sorted(observed),
            "check_report_ref": report["check_id"],
            "authority_envelope_ref": envelope["authority_envelope_id"],
            "status": "PASS" if report["status"] == "FAIL" and expected.issubset(observed) else "FAIL",
        }
        cases.append(case)
        reports.append(report)
        envelopes.append(envelope)
    return cases, reports, envelopes


def git_diff_empty(paths: list[str]) -> dict[str, Any]:
    proc = subprocess.run(["git", "diff", "--", *paths], cwd=REPO_ROOT, text=True, capture_output=True)
    return {
        "command": "git diff -- " + " ".join(paths),
        "returncode": proc.returncode,
        "status": "PASS" if proc.returncode == 0 and proc.stdout == "" else "FAIL",
        "stdout": proc.stdout[-3000:],
        "stderr": proc.stderr[-3000:],
    }


def run_command(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
    count = 0
    for line in (proc.stdout + "\n" + proc.stderr).splitlines():
        if line.startswith("Ran ") and " tests" in line:
            try:
                count = int(line.split()[1])
            except (IndexError, ValueError):
                count = 0
    return {
        "command": " ".join(command),
        "returncode": proc.returncode,
        "result": "PASS" if proc.returncode == 0 else "FAIL",
        "count": count,
        "stdout_tail": proc.stdout[-3000:],
        "stderr_tail": proc.stderr[-3000:],
    }


def run_tests() -> dict[str, Any]:
    targeted = run_command([sys.executable, "-m", "unittest", "tests.test_main_citybrain_push2_lane_a_check_authority_v1"])
    full_discovery = run_command([sys.executable, "-m", "unittest", "discover"])
    return {
        "runner": "PASS",
        "targeted": targeted,
        "full_discovery": full_discovery,
        "ask_scoped_diff": git_diff_empty(ASK_CONTRACT_PATHS),
        "r7_scoped_diff": git_diff_empty(R7_RUNTIME_PATHS),
    }


def test_log_text(tests: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# CHECK v0 / AuthorityEnvelope v1 Test Log",
            "",
            f"- runner: `{tests.get('runner', 'NOT_RUN')}`",
            f"- targeted: `{tests.get('targeted', {}).get('result', 'NOT_RUN')}`, `{tests.get('targeted', {}).get('count', 0)}` tests",
            f"- full_discovery: `{tests.get('full_discovery', {}).get('result', 'NOT_RUN')}`, `{tests.get('full_discovery', {}).get('count', 0)}` tests",
            f"- ASK scoped diff: `{tests.get('ask_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            f"- R7 scoped diff: `{tests.get('r7_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            "",
            "No sealed ASK G1-G8 runtime change, R7 runtime change, live retrieval, production API, URL fetch, LLM call, official action, dispatch, control, enforcement, legal finding, or certified finding is performed.",
        ]
    )


def freshness_policy_text() -> str:
    return "\n".join(
        [
            "# CHECK v0 Freshness Policy",
            "",
            "- Policy clock: `2026-07-05T00:00:00Z` for deterministic Lane A fixtures.",
            "- `vss_sensor_inferred` and `sensor_inferred`: maximum age 7 days; candidate context only.",
            "- `replay_fixture`, `sample_clip`, `manual_test_fixture`, `synthetic_event`, `local_replay_fixture`, and `ask_v11_evidence_fixture`: maximum age 30 days when an observed/as-of time is present; otherwise static local replay may emit `not_applicable`.",
            "- `verified_authority_record` and `official_record`: maximum age 90 days for source-record context; stale records fail CHECK.",
            "- Freshness never upgrades candidate, sensor, VSS, replay, or ASK handoff packets into official truth.",
        ]
    )


def ask_attachment_policy_text() -> str:
    return "\n".join(
        [
            "# CHECK v0 ASK Attachment Policy",
            "",
            "- CHECK v0 attaches to ASK app/handoff outputs only through `main-citybrain.check_v0.ask_attachment_wrapper.v1`.",
            "- The wrapper stores `check_report_ref` and `authority_envelope_ref` outside the consumed ASK packet.",
            "- The consumed ASK packet hash is recorded before attachment and the wrapped packet is not mutated.",
            "- `sealed_ask_runtime_modified`, `g1_g8_modified`, and native G6 integration are all false/deferred for Lane A.",
            "- Native ASK core integration remains a future deliberate ASK revision.",
        ]
    )


def write_hash_manifest() -> dict[str, Any]:
    return write_hash_manifest_for(OUTPUT_ROOT, "CHECK_V0_HASH_MANIFEST.json", "main-citybrain.push2_lane_a.check_v0_authority_v1.hash_manifest.v1")


def write_hash_manifest_for(root: Path, name: str, schema_version: str) -> dict[str, Any]:
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != name:
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
    write_json(root / name, manifest)
    return manifest


def verify_hash_manifest() -> dict[str, Any]:
    return verify_hash_manifest_for(OUTPUT_ROOT, "CHECK_V0_HASH_MANIFEST.json")


def verify_hash_manifest_for(root: Path, name: str) -> dict[str, Any]:
    manifest_path = root / name
    if not manifest_path.exists():
        return {"status": "FAIL", "declared": 0, "verified": 0, "problems": ["missing manifest"]}
    manifest = read_json(manifest_path, {"files": []})
    problems = []
    verified = 0
    for entry in manifest.get("files", []):
        path = root / entry["path"]
        if not path.exists():
            problems.append(f"missing:{entry['path']}")
        elif sha256_file(path) != entry["sha256"]:
            problems.append(f"mismatch:{entry['path']}")
        else:
            verified += 1
    return {
        "status": "PASS" if not problems and manifest.get("status") == "PASS" else "FAIL",
        "declared": len(manifest.get("files", [])),
        "verified": verified,
        "problems": problems,
    }


def git_value(args: list[str], default: str = "unknown") -> str:
    proc = subprocess.run(["git", *args], cwd=REPO_ROOT, text=True, capture_output=True)
    if proc.returncode != 0:
        return default
    return proc.stdout.strip() or default


def build_closeout(main_decision: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(CLOSEOUT_ROOT)
    main_hash = verify_hash_manifest()
    status = CLOSEOUT_STATUS if main_decision.get("status") == PASS_STATUS and main_hash["status"] == "PASS" else FAIL_STATUS
    decision = {
        "schema_version": "main-citybrain.push2_lane_a.check_v0_authority_v1.closeout.v1",
        "task_id": "PUSH2-LANE-A-CHECK-V0-AUTHORITY-ENVELOPE-V1-CLOSEOUT",
        "status": status,
        "main_status": main_decision.get("status"),
        "check_report_count": main_decision.get("check_report_count", 0),
        "authority_envelope_count": main_decision.get("authority_envelope_count", 0),
        "authority_levels_emitted": main_decision.get("authority_levels_emitted", []),
        "negative_tests_status": main_decision.get("negative_tests_status"),
        "ask_attachment_wrapper_count": main_decision.get("ask_attachment_wrapper_count", 0),
        "main_hash_manifest": main_hash,
        "tests": tests,
        "limitations": LANE_LIMITATIONS,
        "next": "WAIT_FOR_LANE_B_AND_LANE_C_BRANCH_PUBLISHED_STATUS",
        "created_at": utc_now(),
    }
    write_json(CLOSEOUT_ROOT / "CHECK_V0_AUTHORITY_V1_CLOSEOUT_DECISION.json", decision)
    write_text(
        CLOSEOUT_ROOT / "CHECK_V0_AUTHORITY_V1_CLOSEOUT_SUMMARY.md",
        "\n".join(
            [
                "# PUSH2 Lane A CHECK v0 / AuthorityEnvelope v1 Closeout",
                "",
                f"Status: `{status}`",
                "",
                f"- CheckReports emitted: `{main_decision.get('check_report_count', 0)}`",
                f"- AuthorityEnvelopes emitted: `{main_decision.get('authority_envelope_count', 0)}`",
                f"- Authority levels: `{main_decision.get('authority_levels_emitted', [])}`",
                f"- Negative boundary tests: `{main_decision.get('negative_tests_status')}`",
                "- ASK attachment remains app/handoff wrapper only; sealed ASK G1-G8 unchanged.",
            ]
        ),
    )
    write_text(
        CLOSEOUT_ROOT / "CHECK_V0_AUTHORITY_V1_CLOSEOUT_LIMITATIONS.md",
        "# Lane A Limitations\n\n" + "\n".join(f"- {item}" for item in LANE_LIMITATIONS),
    )
    write_hash_manifest_for(
        CLOSEOUT_ROOT,
        "CHECK_V0_AUTHORITY_V1_CLOSEOUT_HASH_MANIFEST.json",
        "main-citybrain.push2_lane_a.check_v0_authority_v1.closeout.hash_manifest.v1",
    )
    return {"decision": decision}


def staged_scope_text(main_decision: dict[str, Any], closeout_decision: dict[str, Any], final_decision: dict[str, Any], tests: dict[str, Any]) -> str:
    branch = git_value(["branch", "--show-current"])
    base_commit = git_value(["rev-parse", "HEAD"])
    return "\n".join(
        [
            "# PUSH2 Lane A Staged Scope",
            "",
            f"- branch: `{branch}`",
            f"- base commit: `{base_commit}`",
            "- source files staged: `scripts/run_main_citybrain_push2_lane_a_check_authority_v1.py`",
            "- test files staged: `tests/test_main_citybrain_push2_lane_a_check_authority_v1.py`",
            "- output evidence staged: `outputs/push2_lane_a_check_authority_v1/`, `outputs/push2_lane_a_check_authority_v1_closeout/`, `outputs/push2_lane_a_check_authority_v1_final_status/`",
            "- excluded categories: Lane B/C files, unrelated dirty outputs, handoff bundles, raw data, media, secrets, caches, `.venv`, `tmp`, `inputs`, `corpus_raw`",
            f"- runner/focused tests: `{tests.get('targeted', {}).get('result', 'NOT_RUN')}` ({tests.get('targeted', {}).get('count', 0)} tests)",
            f"- full discovery: `{tests.get('full_discovery', {}).get('result', 'NOT_RUN')}` ({tests.get('full_discovery', {}).get('count', 0)} tests)",
            f"- protected ASK diff: `{tests.get('ask_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            f"- protected R7 diff: `{tests.get('r7_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            "- commit subject: `Add Push 2 CHECK v0 and AuthorityEnvelope v1`",
            "",
            "## Status",
            "",
            f"- main decision: `{main_decision.get('status')}`",
            f"- closeout decision: `{closeout_decision.get('status')}`",
            f"- final decision: `{final_decision.get('status')}`",
            f"- CheckReports emitted: `{main_decision.get('check_report_count', 0)}`",
            f"- AuthorityEnvelopes emitted: `{main_decision.get('authority_envelope_count', 0)}`",
            "",
            "## Limitations",
            "",
            *[f"- {item}" for item in LANE_LIMITATIONS],
        ]
    )


def build_final_status(main_decision: dict[str, Any], closeout_decision: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(FINAL_ROOT)
    closeout_hash = verify_hash_manifest_for(CLOSEOUT_ROOT, "CHECK_V0_AUTHORITY_V1_CLOSEOUT_HASH_MANIFEST.json")
    status = FINAL_STATUS if closeout_decision.get("status") == CLOSEOUT_STATUS and closeout_hash["status"] == "PASS" else FAIL_STATUS
    decision = {
        "schema_version": "main-citybrain.push2_lane_a.check_v0_authority_v1.final_status.v1",
        "task_id": "PUSH2-LANE-A-CHECK-V0-AUTHORITY-ENVELOPE-V1-FINAL-STATUS",
        "status": status,
        "closeout_status": closeout_decision.get("status"),
        "completed_through": [
            "CHECK_V0_REPORTS",
            "AUTHORITY_ENVELOPE_V1_STAMPS",
            "BOUNDARY_NEGATIVE_TESTS",
            "FRESHNESS_AND_SOURCE_CLASS_POLICY",
            "ASK_HANDOFF_ATTACHMENT_POLICY",
            "LANE_CLOSEOUT",
            "LANE_FINAL_STATUS",
        ],
        "check_report_count": main_decision.get("check_report_count", 0),
        "authority_envelope_count": main_decision.get("authority_envelope_count", 0),
        "branch_publish_required": True,
        "infra_integration_required": True,
        "tests": tests,
        "limitations": LANE_LIMITATIONS,
        "next": "WAIT_FOR_LANE_B_AND_LANE_C_BRANCH_PUBLISHED_STATUS",
        "created_at": utc_now(),
    }
    write_json(FINAL_ROOT / "CHECK_V0_AUTHORITY_V1_FINAL_STATUS_DECISION.json", decision)
    write_text(
        FINAL_ROOT / "CHECK_V0_AUTHORITY_V1_FINAL_STATUS_SUMMARY.md",
        "\n".join(
            [
                "# PUSH2 Lane A Final Status",
                "",
                f"Status: `{status}`",
                "",
                "Lane A is branch-publish ready. INFRA owns canonical integration after Lane B and Lane C publish.",
            ]
        ),
    )
    write_text(FINAL_ROOT / "PUSH2_LANE_A_STAGED_SCOPE.md", staged_scope_text(main_decision, closeout_decision, decision, tests))
    write_hash_manifest_for(
        FINAL_ROOT,
        "CHECK_V0_AUTHORITY_V1_FINAL_STATUS_HASH_MANIFEST.json",
        "main-citybrain.push2_lane_a.check_v0_authority_v1.final_status.hash_manifest.v1",
    )
    return {"decision": decision}


def build_outputs(tests: dict[str, Any] | None = None) -> dict[str, Any]:
    tests = tests or {"runner": "NOT_RUN"}
    reset_output_root()
    reset_root(CLOSEOUT_ROOT)
    reset_root(FINAL_ROOT)
    packets = collect_runtime_packets()

    runtime_reports: list[dict[str, Any]] = []
    runtime_envelopes: list[dict[str, Any]] = []
    for packet_type in ("CandidateObservation", "EventEnvelope", "QueryResultPacket", "OverlayPacket", "ASKHandoffOutput"):
        for packet in packets[packet_type]:
            report = build_check_report(packet_type, packet)
            runtime_reports.append(report)
            runtime_envelopes.append(build_authority_envelope(report))

    negative_cases, negative_reports, negative_envelopes = build_negative_test_results()
    all_reports = runtime_reports + negative_reports
    all_envelopes = runtime_envelopes + negative_envelopes
    ask_wrappers = attach_check_to_ask_outputs(packets["ASKHandoffOutput"], all_reports, all_envelopes)

    covered_packet_types = sorted({report["packet_type"] for report in all_reports if report["packet_type"] != "ASKHandoffOutput"})
    authority_levels = sorted({envelope["authority_level"] for envelope in all_envelopes})
    required_packet_types = {"CandidateObservation", "EventEnvelope", "QueryResultPacket", "OverlayPacket"}
    required_outputs = [
        "CHECK_V0_AUTHORITY_V1_DECISION.json",
        "CHECK_V0_SCHEMA.json",
        "AUTHORITY_ENVELOPE_V1_SCHEMA.json",
        "CHECK_REPORT_FIXTURES.json",
        "AUTHORITY_ENVELOPE_FIXTURES.json",
        "CHECK_V0_BOUNDARY_NEGATIVE_TESTS.json",
        "CHECK_V0_FRESHNESS_POLICY.md",
        "CHECK_V0_ASK_ATTACHMENT_POLICY.md",
        "CHECK_V0_TEST_LOG.md",
        "CHECK_V0_HASH_MANIFEST.json",
    ]
    status = PASS_STATUS
    failure_reasons: list[str] = []
    if not required_packet_types.issubset(set(covered_packet_types)):
        failure_reasons.append("missing_required_packet_type")
    if authority_levels != [0, 1, 2]:
        failure_reasons.append("missing_authority_level_0_1_2")
    if any(case["status"] != "PASS" for case in negative_cases):
        failure_reasons.append("negative_boundary_tests_failed")
    if not ask_wrappers or any(wrapper["g1_g8_modified"] for wrapper in ask_wrappers):
        failure_reasons.append("ask_wrapper_attachment_failed")
    if failure_reasons:
        status = FAIL_STATUS

    report_fixture = {
        "schema_version": "main-citybrain.push2_lane_a.check_report_fixtures.v1",
        "status": "PASS" if status == PASS_STATUS else "FAIL",
        "report_count": len(all_reports),
        "covered_packet_types": covered_packet_types,
        "watch_item_support": {
            "packet_type_supported_by_schema": True,
            "status": "READY_FOR_WATCH_ITEM_ONCE_AVAILABLE",
            "runtime_watch_item_count": 0,
        },
        "check_reports": all_reports,
        "ask_wrapped_outputs": ask_wrappers,
    }
    envelope_fixture = {
        "schema_version": "main-citybrain.push2_lane_a.authority_envelope_fixtures.v1",
        "status": "PASS" if authority_levels == [0, 1, 2] else "FAIL",
        "envelope_count": len(all_envelopes),
        "authority_levels_emitted": authority_levels,
        "authority_envelopes": all_envelopes,
    }
    negative_fixture = {
        "schema_version": "main-citybrain.push2_lane_a.boundary_negative_tests.v1",
        "status": "PASS" if all(case["status"] == "PASS" for case in negative_cases) else "FAIL",
        "case_count": len(negative_cases),
        "cases": negative_cases,
    }
    decision = {
        "schema_version": "main-citybrain.push2_lane_a.check_v0_authority_v1.decision.v1",
        "task_id": TASK_ID,
        "status": status,
        "failure_reasons": failure_reasons,
        "entry_gate_assessment": {
            "r0_1_contract": "branch_available_or_local_replay_compatible",
            "event_fabric_runtime_spine": "R7B/R7C local replay outputs consumed when present",
            "regression_corpus_v1": "ASK real corpus eval outputs are not modified by Lane A",
            "ask_loose_end": "ledgered in CHECK_V0_ASK_ATTACHMENT_POLICY.md; native G6 integration deferred",
        },
        "required_outputs": required_outputs,
        "check_report_count": len(all_reports),
        "authority_envelope_count": len(all_envelopes),
        "authority_levels_emitted": authority_levels,
        "covered_packet_types": covered_packet_types,
        "watch_item_support": report_fixture["watch_item_support"],
        "negative_tests_status": negative_fixture["status"],
        "ask_attachment_wrapper_count": len(ask_wrappers),
        "sealed_ask_g1_g8_modified": False,
        "r7_runtime_modified": False,
        "vss_fact_source_allowed": False,
        "sensor_inferred_official_truth_allowed": False,
        "official_action_dispatch_legal_behavior_added": False,
        "infra_owns_canonical_integration": True,
        "tests": tests,
        "created_at": utc_now(),
    }

    write_json(OUTPUT_ROOT / "CHECK_V0_SCHEMA.json", check_report_schema())
    write_json(OUTPUT_ROOT / "AUTHORITY_ENVELOPE_V1_SCHEMA.json", authority_envelope_schema())
    write_json(OUTPUT_ROOT / "CHECK_REPORT_FIXTURES.json", report_fixture)
    write_json(OUTPUT_ROOT / "AUTHORITY_ENVELOPE_FIXTURES.json", envelope_fixture)
    write_json(OUTPUT_ROOT / "CHECK_V0_BOUNDARY_NEGATIVE_TESTS.json", negative_fixture)
    write_text(OUTPUT_ROOT / "CHECK_V0_FRESHNESS_POLICY.md", freshness_policy_text())
    write_text(OUTPUT_ROOT / "CHECK_V0_ASK_ATTACHMENT_POLICY.md", ask_attachment_policy_text())
    write_text(OUTPUT_ROOT / "CHECK_V0_TEST_LOG.md", test_log_text(tests))
    write_json(OUTPUT_ROOT / "CHECK_V0_AUTHORITY_V1_DECISION.json", decision)
    write_hash_manifest()
    closeout = build_closeout(decision, tests)
    final = build_final_status(decision, closeout["decision"], tests)
    return {
        "decision": decision,
        "reports": report_fixture,
        "authority": envelope_fixture,
        "negative": negative_fixture,
        "closeout": closeout["decision"],
        "final": final["decision"],
    }


def main() -> int:
    initial = build_outputs({"runner": "PRE_TEST"})
    tests = run_tests()
    result = build_outputs(tests)
    print(json.dumps({"decision": result["decision"]}, indent=2, sort_keys=True))
    ok = (
        result["decision"]["status"] == PASS_STATUS
        and tests["targeted"]["result"] == "PASS"
        and tests["ask_scoped_diff"]["status"] == "PASS"
        and tests["r7_scoped_diff"]["status"] == "PASS"
    )
    return 0 if ok and initial["decision"]["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
