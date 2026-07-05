"""Local/replay Canonical Entity Runtime objects for CityBrain.

CER is deliberately not an identity authority. These helpers create reviewable
entity/assertion objects that preserve source, evidence, CHECK, and Authority
references for downstream Push 4 lanes.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any


SCHEMA_VERSION = "main-citybrain.cer.runtime.r1"

ALLOWED_ASSERTION_STATUSES = [
    "candidate",
    "review_required",
    "accepted_local",
    "rejected_local",
    "conflicted",
    "superseded",
]
FORBIDDEN_ASSERTION_STATUSES = [
    "official_truth",
    "legal_finding",
    "certified_fact",
    "cross_city_authority",
]
REVIEW_ONLY_SOURCE_CLASSES = {
    "vss_derived",
    "sensor_inferred",
    "model_inferred",
    "sample_clip",
    "manual_test_fixture",
    "replay_fixture",
    "local_replay_fixture",
}
CER_NON_CLAIMS = [
    "No production API.",
    "No URL fetch or live retrieval.",
    "No LLM authority.",
    "No official case/ticket submission.",
    "No dispatch/control/enforcement.",
    "No legal/certified finding.",
    "No autonomous workflow.",
    "No live Kit control.",
    "No full citywide twin claim.",
    "No VSS-as-fact-source.",
    "No cross-city claims until federation.",
    "No sealed ASK G1-G8 runtime change.",
    "No protected R7 runtime drift.",
    "Feature branches only; INFRA owns canonical integration.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def slug(value: Any) -> str:
    text = str(value or "unknown").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:80] or "unknown"


def stable_id(prefix: str, *parts: Any) -> str:
    digest = stable_hash([prefix, *parts])[:16]
    return f"{prefix}:{digest}"


def unique(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, list):
            for nested in unique(value):
                if nested not in seen:
                    seen.add(nested)
                    result.append(nested)
            continue
        text = str(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def merged_cannot_claim(*items: Any) -> list[str]:
    return unique([*[item for item in items], CER_NON_CLAIMS])


def check_forbidden_status(status: str) -> None:
    if status in FORBIDDEN_ASSERTION_STATUSES:
        raise ValueError(f"Forbidden CER assertion status: {status}")
    if status not in ALLOWED_ASSERTION_STATUSES:
        raise ValueError(f"Unknown CER assertion status: {status}")


def validate_attribute_assertion(assertion: dict[str, Any]) -> dict[str, Any]:
    status = assertion.get("assertion_status", "")
    check_forbidden_status(status)
    source_class = assertion.get("source_class")
    if source_class in REVIEW_ONLY_SOURCE_CLASSES and status == "accepted_local":
        raise ValueError(f"{source_class} assertions cannot become accepted local truth without review")
    if assertion.get("official_truth_claim") is True:
        raise ValueError("CER assertions cannot claim official truth")
    if assertion.get("cross_city_authority") is True:
        raise ValueError("CER assertions cannot claim cross-city authority")
    if not assertion.get("check_report_ref"):
        raise ValueError("CER assertions must preserve check_report_ref")
    if not assertion.get("authority_envelope_ref"):
        raise ValueError("CER assertions must preserve authority_envelope_ref")
    for field in ["evidence_refs", "limitation_refs", "trace_refs", "cannot_claim"]:
        if not assertion.get(field):
            raise ValueError(f"CER assertion missing {field}")
    return assertion


def build_canonical_entity_ref(
    *,
    entity_type: str,
    source_entity_refs: list[str],
    review_state: str = "review_required",
    namespace: str = "local_replay",
) -> dict[str, Any]:
    source_refs = unique(source_entity_refs)
    canonical_entity_id = f"cer:entity:{slug(namespace)}:{stable_hash(source_refs + [entity_type])[:16]}"
    payload = {
        "schema_version": "main-citybrain.cer.canonical_entity_ref.r1",
        "canonical_entity_id": canonical_entity_id,
        "entity_namespace": namespace,
        "entity_type": entity_type,
        "source_entity_refs": source_refs,
        "review_state": review_state,
        "local_replay_only": True,
        "official_truth_claim": False,
        "cross_city_authority": False,
        "cannot_claim": merged_cannot_claim("official identity authority", "cross-city authority"),
    }
    payload["canonical_entity_hash"] = stable_hash(payload)
    return payload


def build_attribute_assertion(
    *,
    entity_ref: str,
    attribute_name: str,
    attribute_value: Any,
    attribute_value_type: str,
    source_class: str,
    source_ref: str,
    source_record_ref: str,
    evidence_refs: list[str],
    limitation_refs: list[str],
    trace_refs: list[str],
    check_report_ref: str,
    authority_envelope_ref: str,
    assertion_status: str = "review_required",
    review_state: str = "review_required",
    confidence: float = 0.5,
    freshness_status: str = "local_replay_current_for_fixture",
    cannot_claim: list[str] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    check_forbidden_status(assertion_status)
    timestamp = created_at or utc_now()
    payload = {
        "assertion_id": stable_id("cer:assertion", entity_ref, attribute_name, attribute_value, source_ref),
        "schema_version": "main-citybrain.cer.attribute_assertion.r1",
        "entity_ref": entity_ref,
        "attribute_name": attribute_name,
        "attribute_value": attribute_value,
        "attribute_value_type": attribute_value_type,
        "source_class": source_class,
        "source_ref": source_ref,
        "source_record_ref": source_record_ref,
        "evidence_refs": unique(evidence_refs),
        "limitation_refs": unique(limitation_refs),
        "trace_refs": unique(trace_refs),
        "check_report_ref": check_report_ref,
        "authority_envelope_ref": authority_envelope_ref,
        "assertion_status": assertion_status,
        "review_state": review_state,
        "confidence": round(float(confidence), 4),
        "freshness_status": freshness_status,
        "created_at": timestamp,
        "updated_at": timestamp,
        "cannot_claim": merged_cannot_claim(cannot_claim or []),
        "local_replay_only": True,
        "official_truth_claim": False,
        "cross_city_authority": False,
    }
    validate_attribute_assertion(payload)
    payload["assertion_hash"] = stable_hash(payload)
    return payload


def build_entity_identity_record(
    *,
    canonical_entity_ref: dict[str, Any],
    source_entity_refs: list[str],
    source_record_refs: list[str],
    evidence_refs: list[str],
    limitation_refs: list[str],
    trace_refs: list[str],
    check_report_refs: list[str],
    authority_envelope_refs: list[str],
    assertion_refs: list[str],
    conflict_refs: list[str],
    match_candidate_refs: list[str],
) -> dict[str, Any]:
    payload = {
        "schema_version": "main-citybrain.cer.entity_identity_record.r1",
        "identity_record_id": stable_id("cer:identity_record", canonical_entity_ref["canonical_entity_id"]),
        "canonical_entity_ref": canonical_entity_ref,
        "entity_ref": canonical_entity_ref["canonical_entity_id"],
        "entity_type": canonical_entity_ref["entity_type"],
        "identity_status": "candidate_local",
        "review_state": "review_required",
        "source_entity_refs": unique(source_entity_refs),
        "source_record_refs": unique(source_record_refs),
        "evidence_refs": unique(evidence_refs),
        "limitation_refs": unique(limitation_refs),
        "trace_refs": unique(trace_refs),
        "check_report_refs": unique(check_report_refs),
        "authority_envelope_refs": unique(authority_envelope_refs),
        "attribute_assertion_refs": unique(assertion_refs),
        "attribute_conflict_refs": unique(conflict_refs),
        "match_candidate_refs": unique(match_candidate_refs),
        "local_replay_only": True,
        "official_truth_claim": False,
        "cross_city_authority": False,
        "cannot_claim": merged_cannot_claim("official identity resolution", "legal/certified identity finding"),
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    payload["identity_record_hash"] = stable_hash(payload)
    return payload


def detect_attribute_conflicts(assertions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for assertion in assertions:
        key = (assertion["entity_ref"], assertion["attribute_name"])
        groups.setdefault(key, []).append(assertion)
    for (entity_ref, attribute_name), grouped in groups.items():
        values = {json.dumps(item["attribute_value"], sort_keys=True) for item in grouped}
        if len(values) < 2:
            continue
        evidence_refs = unique([item["evidence_refs"] for item in grouped])
        limitation_refs = unique([item["limitation_refs"] for item in grouped])
        trace_refs = unique([item["trace_refs"] for item in grouped])
        payload = {
            "conflict_id": stable_id("cer:conflict", entity_ref, attribute_name, sorted(values)),
            "schema_version": "main-citybrain.cer.attribute_conflict.r1",
            "entity_ref": entity_ref,
            "attribute_name": attribute_name,
            "competing_assertion_refs": [item["assertion_id"] for item in grouped],
            "conflict_type": "competing_attribute_values",
            "evidence_refs": evidence_refs,
            "limitation_refs": limitation_refs,
            "trace_refs": trace_refs,
            "review_state": "review_required",
            "check_report_ref": grouped[0]["check_report_ref"],
            "authority_envelope_ref": grouped[0]["authority_envelope_ref"],
            "cannot_claim": merged_cannot_claim([item["cannot_claim"] for item in grouped], "final attribute truth"),
            "local_replay_only": True,
            "official_truth_claim": False,
            "cross_city_authority": False,
        }
        payload["conflict_hash"] = stable_hash(payload)
        conflicts.append(payload)
    return conflicts


def build_match_candidate(
    *,
    left_entity_ref: str,
    right_entity_ref: str,
    match_features: list[str],
    score: float,
    evidence_refs: list[str],
    limitation_refs: list[str],
    trace_refs: list[str],
    review_state: str = "review_required",
    cannot_claim: list[str] | None = None,
) -> dict[str, Any]:
    payload = {
        "match_candidate_id": stable_id("cer:match_candidate", left_entity_ref, right_entity_ref, match_features),
        "schema_version": "main-citybrain.cer.entity_match_candidate.r1",
        "left_entity_ref": left_entity_ref,
        "right_entity_ref": right_entity_ref,
        "match_features": unique(match_features),
        "score": round(float(score), 4),
        "evidence_refs": unique(evidence_refs),
        "limitation_refs": unique(limitation_refs),
        "trace_refs": unique(trace_refs),
        "review_state": review_state,
        "cannot_claim": merged_cannot_claim(cannot_claim or [], "final identity match", "cross-city recall certainty"),
        "identity_claimed": False,
        "cross_city_claim": False,
        "local_replay_only": True,
    }
    if payload["cross_city_claim"]:
        raise ValueError("CER match candidates cannot claim cross-city matching authority")
    payload["match_candidate_hash"] = stable_hash(payload)
    return payload


def build_entity_review_state(
    *,
    entity_ref: str,
    assertions: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    match_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    status_counts = Counter(assertion["assertion_status"] for assertion in assertions)
    payload = {
        "review_state_id": stable_id("cer:review_state", entity_ref),
        "schema_version": "main-citybrain.cer.entity_review_state.r1",
        "entity_ref": entity_ref,
        "review_state": "review_required" if conflicts or match_candidates else "candidate",
        "assertion_status_counts": dict(sorted(status_counts.items())),
        "attribute_assertion_refs": [assertion["assertion_id"] for assertion in assertions],
        "attribute_conflict_refs": [conflict["conflict_id"] for conflict in conflicts],
        "match_candidate_refs": [candidate["match_candidate_id"] for candidate in match_candidates],
        "accepted_local_count": status_counts.get("accepted_local", 0),
        "official_truth_claim_count": 0,
        "legal_certified_claim_count": 0,
        "local_replay_only": True,
        "cannot_claim": merged_cannot_claim("official review closure", "autonomous workflow"),
    }
    payload["review_state_hash"] = stable_hash(payload)
    return payload


def build_assertion_evidence_links(assertions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    for assertion in assertions:
        payload = {
            "assertion_evidence_link_id": stable_id("cer:assertion_evidence_link", assertion["assertion_id"]),
            "schema_version": "main-citybrain.cer.assertion_evidence_link.r1",
            "assertion_ref": assertion["assertion_id"],
            "entity_ref": assertion["entity_ref"],
            "source_ref": assertion["source_ref"],
            "source_record_ref": assertion["source_record_ref"],
            "evidence_refs": assertion["evidence_refs"],
            "limitation_refs": assertion["limitation_refs"],
            "trace_refs": assertion["trace_refs"],
            "check_report_ref": assertion["check_report_ref"],
            "authority_envelope_ref": assertion["authority_envelope_ref"],
            "local_replay_only": True,
            "cannot_claim": assertion["cannot_claim"],
        }
        payload["assertion_evidence_link_hash"] = stable_hash(payload)
        links.append(payload)
    return links


def build_source_assertion_summary(assertions: list[dict[str, Any]]) -> dict[str, Any]:
    by_source = Counter(assertion["source_class"] for assertion in assertions)
    accepted_by_source = Counter(
        assertion["source_class"] for assertion in assertions if assertion["assertion_status"] == "accepted_local"
    )
    review_only_sources = sorted(source for source in by_source if source in REVIEW_ONLY_SOURCE_CLASSES)
    payload = {
        "schema_version": "main-citybrain.cer.source_assertion_summary.r1",
        "status": "PASS",
        "source_class_counts": dict(sorted(by_source.items())),
        "accepted_local_by_source_class": dict(sorted(accepted_by_source.items())),
        "review_only_source_classes": review_only_sources,
        "vss_truth_created": False,
        "sensor_inferred_official_truth_created": False,
        "official_truth_claim_created": False,
        "legal_certified_claim_created": False,
        "cross_city_authority_created": False,
        "local_replay_only": True,
        "cannot_claim": merged_cannot_claim("VSS as fact source", "sensor inferred official truth"),
    }
    payload["source_assertion_summary_hash"] = stable_hash(payload)
    return payload
