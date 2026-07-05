"""CHECK v1 claim-to-evidence and contradiction helpers.

CHECK v1 consumes CER AttributeAssertions. It does not create official truth,
legal/certified findings, dispatch/control actions, or live retrieval claims.
"""

from __future__ import annotations

from itertools import combinations
from typing import Any

from packages.cer import stable_hash


SCHEMA_VERSION = "main-citybrain.check_v1.runtime.r1"

ALLOWED_CLAIMABILITY_STATUSES = [
    "supported_for_local_review",
    "unsupported",
    "contradicted",
    "insufficient_evidence",
    "stale_evidence",
    "not_authoritative",
    "blocked_by_boundary",
]

FORBIDDEN_CLAIMABILITY_STATUSES = [
    "official_truth",
    "legal_finding",
    "certified_fact",
    "dispatch_authorized",
]

UNIVERSAL_NON_CLAIMS = [
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

SOURCE_DEPTH_PROFILES = {
    "source_record": {
        "source_depth": 1,
        "source_depth_label": "direct_source_record",
        "distinction": "direct source record",
        "can_source_truth": True,
    },
    "dataset_annotation": {
        "source_depth": 2,
        "source_depth_label": "dataset_annotation",
        "distinction": "dataset annotation",
        "can_source_truth": False,
    },
    "manual_review_note": {
        "source_depth": 2,
        "source_depth_label": "manual_review_note",
        "distinction": "manual review note",
        "can_source_truth": False,
    },
    "sensor_inference": {
        "source_depth": 3,
        "source_depth_label": "sensor_inference",
        "distinction": "sensor inference",
        "can_source_truth": False,
    },
    "model_generated_narrative_sidecar": {
        "source_depth": 4,
        "source_depth_label": "model_generated_narrative_sidecar",
        "distinction": "model-generated narrative sidecar",
        "can_source_truth": False,
    },
    "derived_assertion": {
        "source_depth": 5,
        "source_depth_label": "derived_assertion",
        "distinction": "derived assertion",
        "can_source_truth": False,
    },
}

SOURCE_CLASS_TO_PROFILE = {
    "source_record": "source_record",
    "local_replay_fixture": "dataset_annotation",
    "replay_fixture": "dataset_annotation",
    "sample_clip": "dataset_annotation",
    "manual_test_fixture": "manual_review_note",
    "manual_review_note": "manual_review_note",
    "sensor_inferred": "sensor_inference",
    "vss_derived": "model_generated_narrative_sidecar",
    "model_inferred": "model_generated_narrative_sidecar",
    "brief_v2_local_replay": "model_generated_narrative_sidecar",
    "derived_assertion": "derived_assertion",
}

NON_AUTHORITATIVE_SOURCE_CLASSES = {
    "vss_derived",
    "model_inferred",
    "brief_v2_local_replay",
}

BOUNDARY_BLOCKER_TERMS = [
    "official_truth",
    "official action",
    "official_action",
    "official violation",
    "legal_finding",
    "legal finding",
    "certified_fact",
    "certified fact",
    "certified_detection",
    "dispatch_authorized",
    "dispatch authorized",
    "enforcement_action",
    "case submitted",
    "ticket submitted",
    "live camera",
    "production_camera",
]

BOUNDARY_SAFE_NEGATIONS = [
    "not_official",
    "not official",
    "no official",
    "non_official",
]


def _stable_id(prefix: str, *parts: Any) -> str:
    return f"{prefix}:{stable_hash([prefix, *parts])[:16]}"


def _unique(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, list):
            for nested in _unique(value):
                if nested not in seen:
                    seen.add(nested)
                    result.append(nested)
            continue
        text = str(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def validate_claimability_status(status: str) -> str:
    if status in FORBIDDEN_CLAIMABILITY_STATUSES:
        raise ValueError(f"Forbidden CHECK v1 claimability status: {status}")
    if status not in ALLOWED_CLAIMABILITY_STATUSES:
        raise ValueError(f"Unknown CHECK v1 claimability status: {status}")
    return status


def claim_family(assertion: dict[str, Any]) -> str:
    return f"{assertion.get('entity_ref')}::{assertion.get('attribute_name')}"


def _text_blob(assertion: dict[str, Any]) -> str:
    return " ".join(
        str(assertion.get(field, ""))
        for field in ["attribute_name", "attribute_value", "assertion_status", "review_state"]
    ).lower()


def has_boundary_blocker(assertion: dict[str, Any]) -> bool:
    text = _text_blob(assertion)
    if any(term in text for term in BOUNDARY_SAFE_NEGATIONS):
        text = " ".join(part for part in text.split() if part not in BOUNDARY_SAFE_NEGATIONS)
    return any(term in text for term in BOUNDARY_BLOCKER_TERMS)


def source_depth_for_assertion(assertion: dict[str, Any]) -> dict[str, Any]:
    source_class = str(assertion.get("source_class") or "derived_assertion")
    profile_key = SOURCE_CLASS_TO_PROFILE.get(source_class, "derived_assertion")
    profile = SOURCE_DEPTH_PROFILES[profile_key]
    can_source_truth = bool(profile["can_source_truth"]) and source_class not in NON_AUTHORITATIVE_SOURCE_CLASSES
    return {
        "source_depth_score_id": _stable_id("check_v1:source_depth", assertion.get("assertion_id"), source_class),
        "schema_version": "main-citybrain.check_v1.source_depth_score.r1",
        "assertion_ref": assertion.get("assertion_id"),
        "entity_ref": assertion.get("entity_ref"),
        "attribute_name": assertion.get("attribute_name"),
        "source_class": source_class,
        "source_depth": profile["source_depth"],
        "source_depth_label": profile["source_depth_label"],
        "source_depth_distinction": profile["distinction"],
        "can_source_truth": can_source_truth,
        "source_truth_blocked_reason": None if can_source_truth else "review_only_or_sidecar_source_not_truth_authority",
        "source_ref": assertion.get("source_ref"),
        "source_record_ref": assertion.get("source_record_ref"),
        "evidence_ref_count": len(assertion.get("evidence_refs") or []),
        "freshness_status": assertion.get("freshness_status"),
    }


def build_source_depth_fixtures(assertions: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [source_depth_for_assertion(assertion) for assertion in assertions]
    profiles = [
        {
            "profile_key": key,
            "source_depth": value["source_depth"],
            "source_depth_label": value["source_depth_label"],
            "source_depth_distinction": value["distinction"],
            "can_source_truth": value["can_source_truth"],
        }
        for key, value in SOURCE_DEPTH_PROFILES.items()
    ]
    return {
        "schema_version": "main-citybrain.check_v1.source_depth_fixtures.r1",
        "status": "PASS",
        "source_depth_profiles": profiles,
        "source_depth_scores": scores,
    }


def claimability_status_for_assertion(assertion: dict[str, Any], contradicted: bool = False) -> str:
    if has_boundary_blocker(assertion):
        return "blocked_by_boundary"
    if contradicted:
        return "contradicted"
    if not assertion.get("authority_envelope_ref") or not assertion.get("check_report_ref"):
        return "not_authoritative"
    if not assertion.get("evidence_refs"):
        return "insufficient_evidence"
    freshness = str(assertion.get("freshness_status") or "").lower()
    if "stale" in freshness:
        return "stale_evidence"
    if assertion.get("source_class") in NON_AUTHORITATIVE_SOURCE_CLASSES:
        return "not_authoritative"
    status = assertion.get("assertion_status")
    if status in {"rejected_local", "superseded"}:
        return "unsupported"
    return "supported_for_local_review"


def build_claim_to_evidence_mappings(assertions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []
    for assertion in assertions:
        depth = source_depth_for_assertion(assertion)
        payload = {
            "mapping_id": _stable_id("check_v1:claim_evidence", assertion.get("assertion_id")),
            "schema_version": "main-citybrain.check_v1.claim_to_evidence_mapping.r1",
            "claim_ref": assertion.get("assertion_id"),
            "claim_family": claim_family(assertion),
            "claim_text_or_structured_claim": {
                "entity_ref": assertion.get("entity_ref"),
                "attribute_name": assertion.get("attribute_name"),
                "attribute_value": assertion.get("attribute_value"),
                "attribute_value_type": assertion.get("attribute_value_type"),
            },
            "attribute_assertion_refs": [assertion.get("assertion_id")],
            "supporting_evidence_refs": list(assertion.get("evidence_refs") or []),
            "source_ref": assertion.get("source_ref"),
            "source_record_ref": assertion.get("source_record_ref"),
            "source_depth": depth["source_depth"],
            "source_depth_label": depth["source_depth_label"],
            "freshness_status": assertion.get("freshness_status"),
            "check_report_ref": assertion.get("check_report_ref"),
            "authority_envelope_ref": assertion.get("authority_envelope_ref"),
            "trace_refs": list(assertion.get("trace_refs") or []),
            "cannot_claim": _unique([assertion.get("cannot_claim") or [], UNIVERSAL_NON_CLAIMS]),
        }
        payload["mapping_hash"] = stable_hash(payload)
        mappings.append(payload)
    return mappings


def _different_evidence(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return set(left.get("evidence_refs") or []) != set(right.get("evidence_refs") or [])


def _pair_from_assertions(
    left: dict[str, Any],
    right: dict[str, Any],
    conflict: dict[str, Any] | None = None,
) -> dict[str, Any]:
    conflict_ref = (conflict or {}).get("conflict_id")
    payload = {
        "contradiction_id": _stable_id(
            "check_v1:contradiction",
            left.get("assertion_id"),
            right.get("assertion_id"),
            conflict_ref,
        ),
        "schema_version": "main-citybrain.check_v1.contradiction_pair.r1",
        "conflict_ref": conflict_ref,
        "entity_ref": left.get("entity_ref"),
        "attribute_name": left.get("attribute_name"),
        "claim_family": claim_family(left),
        "left_assertion_ref": left.get("assertion_id"),
        "right_assertion_ref": right.get("assertion_id"),
        "competing_assertion_refs": _unique(
            [
                (conflict or {}).get("competing_assertion_refs") or [],
                [left.get("assertion_id"), right.get("assertion_id")],
            ]
        ),
        "left_value": left.get("attribute_value"),
        "right_value": right.get("attribute_value"),
        "incompatible_values": left.get("attribute_value") != right.get("attribute_value"),
        "different_source_refs": left.get("source_ref") != right.get("source_ref"),
        "different_evidence_refs": _different_evidence(left, right),
        "left_supporting_evidence_refs": list(left.get("evidence_refs") or []),
        "right_supporting_evidence_refs": list(right.get("evidence_refs") or []),
        "contradicting_evidence_refs": _unique([left.get("evidence_refs") or [], right.get("evidence_refs") or []]),
        "check_report_refs": _unique([left.get("check_report_ref"), right.get("check_report_ref"), (conflict or {}).get("check_report_ref")]),
        "authority_envelope_refs": _unique(
            [left.get("authority_envelope_ref"), right.get("authority_envelope_ref"), (conflict or {}).get("authority_envelope_ref")]
        ),
        "claimability_impact": "contradicted",
        "retained_same_claim_pair": True,
        "ask_regression_corpus_v4_ready": True,
        "cannot_claim": _unique([left.get("cannot_claim") or [], right.get("cannot_claim") or [], (conflict or {}).get("cannot_claim") or [], UNIVERSAL_NON_CLAIMS]),
        "trace_refs": _unique([left.get("trace_refs") or [], right.get("trace_refs") or [], (conflict or {}).get("trace_refs") or []]),
    }
    payload["contradiction_hash"] = stable_hash(payload)
    return payload


def build_contradiction_pairs(
    assertions: list[dict[str, Any]],
    cer_conflicts: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    by_ref = {assertion["assertion_id"]: assertion for assertion in assertions}
    pairs: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for conflict in cer_conflicts or []:
        grouped = [by_ref[ref] for ref in conflict.get("competing_assertion_refs", []) if ref in by_ref]
        for left, right in combinations(grouped, 2):
            if left.get("entity_ref") != right.get("entity_ref"):
                continue
            if left.get("attribute_name") != right.get("attribute_name"):
                continue
            if left.get("attribute_value") == right.get("attribute_value"):
                continue
            key = tuple(sorted([left["assertion_id"], right["assertion_id"]]))
            if key in seen:
                continue
            seen.add(key)
            pairs.append(_pair_from_assertions(left, right, conflict))
    grouped_by_claim: dict[str, list[dict[str, Any]]] = {}
    for assertion in assertions:
        grouped_by_claim.setdefault(claim_family(assertion), []).append(assertion)
    for grouped in grouped_by_claim.values():
        for left, right in combinations(grouped, 2):
            if left.get("attribute_value") == right.get("attribute_value"):
                continue
            key = tuple(sorted([left["assertion_id"], right["assertion_id"]]))
            if key in seen:
                continue
            seen.add(key)
            pairs.append(_pair_from_assertions(left, right))
    return pairs


def contradiction_index(pairs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for pair in pairs:
        for ref in [pair["left_assertion_ref"], pair["right_assertion_ref"]]:
            index.setdefault(ref, []).append(pair)
    return index


def build_check_reports(
    assertions: list[dict[str, Any]],
    contradiction_pairs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pairs_by_assertion = contradiction_index(contradiction_pairs)
    reports: list[dict[str, Any]] = []
    for assertion in assertions:
        related_pairs = pairs_by_assertion.get(assertion["assertion_id"], [])
        depth = source_depth_for_assertion(assertion)
        contradicting_assertion_refs = _unique(
            [
                [
                    pair["right_assertion_ref"] if pair["left_assertion_ref"] == assertion["assertion_id"] else pair["left_assertion_ref"]
                    for pair in related_pairs
                ]
            ]
        )
        contradicting_evidence_refs = _unique([pair.get("contradicting_evidence_refs") or [] for pair in related_pairs])
        claimability_status = validate_claimability_status(
            claimability_status_for_assertion(assertion, contradicted=bool(related_pairs))
        )
        payload = {
            "check_v1_report_id": _stable_id("check_v1:report", assertion.get("assertion_id")),
            "schema_version": "main-citybrain.check_v1.report.r1",
            "claim_ref": assertion.get("assertion_id"),
            "claim_text_or_structured_claim": {
                "entity_ref": assertion.get("entity_ref"),
                "attribute_name": assertion.get("attribute_name"),
                "attribute_value": assertion.get("attribute_value"),
                "attribute_value_type": assertion.get("attribute_value_type"),
            },
            "attribute_assertion_refs": [assertion.get("assertion_id")],
            "supporting_evidence_refs": list(assertion.get("evidence_refs") or []),
            "contradicting_assertion_refs": contradicting_assertion_refs,
            "contradicting_evidence_refs": contradicting_evidence_refs,
            "source_depth": depth["source_depth"],
            "source_depth_detail": depth,
            "source_class_summary": {
                "source_class": assertion.get("source_class"),
                "source_depth_label": depth["source_depth_label"],
                "can_source_truth": depth["can_source_truth"],
            },
            "freshness_summary": {
                "freshness_status": assertion.get("freshness_status"),
                "is_stale": "stale" in str(assertion.get("freshness_status") or "").lower(),
            },
            "authority_envelope_ref": assertion.get("authority_envelope_ref"),
            "claimability_status": claimability_status,
            "cannot_claim": _unique([assertion.get("cannot_claim") or [], UNIVERSAL_NON_CLAIMS]),
            "safe_next_looks": [
                "Inspect preserved local/replay evidence refs.",
                "Route contradicted or non-authoritative claims to manual review context only.",
                "Keep any ASK corpus fixture as regression evidence, not a finding.",
            ],
            "trace_refs": list(assertion.get("trace_refs") or []),
        }
        payload["report_hash"] = stable_hash(payload)
        reports.append(payload)
    return reports
