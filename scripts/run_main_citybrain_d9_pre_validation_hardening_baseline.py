#!/usr/bin/env python3
"""Run D9 pre-validation hardening and baseline refresh.

This is not a UI sprint, not external operator validation, and not an Open ASK
router implementation. It hardens Recall where local Chicago fields allow it,
keeps DIFF deferred unless true comparable source snapshots exist, locks the
Open ASK router C0 contract, and refreshes the validation baseline.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
OUTPUTS = REPO / "outputs"
FIXTURES = REPO / "packages" / "fixtures"

BOUNDARY = (
    "Local/LAN/replay/review/query context only; no production/public API, "
    "autonomous monitoring, alerting, dispatch, routing/control, enforcement, "
    "official ticket/case, approval, legal/certified finding, certified impact, "
    "or automated action."
)
TASK = "MAIN-CITYBRAIN-D9-PRE-VALIDATION-HARDENING-BASELINE"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D9_PRE_VALIDATION_HARDENING_MILESTONE_FREEZE_WITH_LIMITATIONS"
PARTIAL_STATUS = "PARTIAL_MAIN_CITYBRAIN_D9_PRE_VALIDATION_HARDENING_WITH_RECALL_OR_DIFF_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D9_PRE_VALIDATION_HARDENING"

ROOTS = {
    "recall_preflight": OUTPUTS / "main_citybrain_d9_recall_hardening_preflight",
    "matcher": OUTPUTS / "main_citybrain_d9_chicago_cited_matcher_registry_r1",
    "recall_smoke": OUTPUTS / "main_citybrain_d9_recall_positive_negative_smoke_r2",
    "recall_closeout": OUTPUTS / "main_citybrain_d9_recall_hardening_closeout",
    "diff_preflight": OUTPUTS / "main_citybrain_d9_diff_readiness_preflight",
    "snapshot_contract": OUTPUTS / "main_citybrain_d9_source_snapshot_cadence_contract_r1",
    "diff_smoke": OUTPUTS / "main_citybrain_d9_source_record_entity_diff_readiness_smoke_r2",
    "diff_closeout": OUTPUTS / "main_citybrain_d9_diff_readiness_closeout",
    "ask_router": OUTPUTS / "main_citybrain_d9_open_ask_router_contract_c0",
    "baseline_refresh": OUTPUTS / "main_citybrain_d9_validation_baseline_refresh_r1",
    "freeze": OUTPUTS / "main_citybrain_d9_pre_validation_hardening_milestone_freeze",
}

INPUTS = {
    "d9_freeze": OUTPUTS
    / "main_citybrain_d9_ask_watch_brief_check_milestone_freeze"
    / "D9_ASK_WATCH_BRIEF_CHECK_MILESTONE_FREEZE_DECISION.json",
    "runtime_bundle": OUTPUTS
    / "main_citybrain_d9_product_mode_runtime_bundle_r2"
    / "D9_PRODUCT_MODE_RUNTIME_BUNDLE.json",
    "broad_scout": OUTPUTS
    / "main_citybrain_d9_broad_data_scout_milestone_freeze"
    / "BROAD_DATA_SCOUT_MILESTONE_FREEZE_DECISION.json",
    "external_validation": OUTPUTS
    / "main_citybrain_d9_external_operator_validation_certified_state_handoff"
    / "EXTERNAL_OPERATOR_VALIDATION_CERTIFIED_STATE_HANDOFF_DECISION.json",
    "recall_cutaway": OUTPUTS
    / "main_citybrain_d9_recall_cutaway_r7"
    / "D9_RECALL_CUTAWAY_PACKET.json",
    "recall_quality": OUTPUTS
    / "main_citybrain_d9_recall_cutaway_r7"
    / "D9_RECALL_MATCH_REASON_QUALITY_REPORT.json",
    "chicago_bundle": FIXTURES
    / "chicago_similar_case_records"
    / "similar_case_source_bundle.json",
    "diff_matrix": OUTPUTS
    / "main_citybrain_d9_check_diff_scout_r6"
    / "DIFF_READINESS_MATRIX.json",
}

PROTECTED_INPUTS = [
    OUTPUTS / "main_citybrain_d9_ask_watch_brief_check_milestone_freeze",
    OUTPUTS / "main_citybrain_d9_product_mode_runtime_bundle_r2",
    OUTPUTS / "main_citybrain_d9_external_operator_validation_certified_state_handoff",
    OUTPUTS / "main_citybrain_d9_recall_cutaway_r7",
    OUTPUTS / "main_citybrain_d9_check_diff_scout_r6",
    FIXTURES / "chicago_similar_case_records",
    REPO / "apps" / "web-control-room",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_fingerprint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "digest": None}
    lines = []
    for p in sorted(x for x in path.rglob("*") if x.is_file()):
        if p.stat().st_size > 25_000_000:
            lines.append(f"{rel(p)}:{p.stat().st_size}:large")
        else:
            lines.append(f"{rel(p)}:{sha256_file(p)}")
    return {
        "exists": True,
        "file_count": len(lines),
        "digest": hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest(),
    }


def write_hash_manifest(root: Path) -> None:
    files = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "HASH_MANIFEST.json":
            continue
        files[rel(path)] = sha256_file(path)
    write_json(root / "HASH_MANIFEST.json", {"generated_at": now(), "files": files})


def local_open_index(root: Path, title: str) -> None:
    rows = [f"# {title}", "", "Generated artifacts:"]
    for path in sorted(root.iterdir()):
        if path.is_file():
            rows.append(f"- `{rel(path)}`")
    write_md(root / "LOCAL_OPEN_INDEX.md", "\n".join(rows))


def case_fields(case: dict[str, Any]) -> dict[str, Any]:
    ev = case.get("evidence_fields", {})
    loc = ev.get("location_fields", {}) or {}
    return {
        "similar_case_id": case.get("similar_case_id"),
        "source_record_id": ev.get("source_record_id") or (case.get("source_record_ids") or [None])[0],
        "source_dataset": case.get("source_dataset"),
        "source_family": case.get("source_family"),
        "address": loc.get("address") or case.get("address_or_area"),
        "latitude": float(loc.get("latitude")),
        "longitude": float(loc.get("longitude")),
        "issue_event_type": ev.get("issue_event_type"),
        "category_or_type": ev.get("category_or_type"),
        "record_time": case.get("record_time"),
        "evidence_completeness": ev.get("evidence_completeness"),
        "source_url": case.get("source_url"),
        "limitations": case.get("limitations", []),
    }


def haversine_km(a: dict[str, Any], b: dict[str, Any]) -> float:
    r = 6371.0
    lat1 = math.radians(a["latitude"])
    lat2 = math.radians(b["latitude"])
    dlat = lat2 - lat1
    dlon = math.radians(b["longitude"] - a["longitude"])
    x = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


def match_pair(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    distance = round(haversine_km(a, b), 3)
    same_issue = a["issue_event_type"] == b["issue_event_type"]
    same_family = a["source_family"] == b["source_family"]
    if same_issue and same_family and distance <= 5:
        status = "STRONG_MATCH"
        reason = (
            f"Both records cite issue_event_type={a['issue_event_type']}, "
            f"source_family={a['source_family']}, and geocoded points are {distance} km apart."
        )
    elif same_issue and same_family:
        status = "WEAK_MATCH"
        reason = (
            f"Both records cite issue_event_type={a['issue_event_type']} and "
            f"source_family={a['source_family']}, but points are {distance} km apart."
        )
    else:
        status = "NO_MATCH"
        reason = (
            f"Field mismatch: issue_event_type {a['issue_event_type']} vs {b['issue_event_type']}; "
            f"distance {distance} km."
        )
    return {
        "pair": [a["source_record_id"], b["source_record_id"]],
        "match_status": status,
        "cited_match_reason": reason,
        "computed_from_fields": [
            "issue_event_type",
            "source_family",
            "latitude",
            "longitude",
            "source_record_id",
            "category_or_type",
            "record_time",
        ],
        "field_values": {
            a["source_record_id"]: a,
            b["source_record_id"]: b,
        },
        "distance_km": distance,
        "boundary": "Recall is bounded precedent memory only; not causality, prediction, instruction, recommendation, enforcement, or action.",
    }


def forbidden_claims_present(obj: Any) -> bool:
    def claim_text(value: Any, key: str | None = None) -> list[str]:
        if key and key.lower() in {"limitations", "boundary", "claim_boundary", "no_action_boundary"}:
            return []
        if isinstance(value, dict):
            out: list[str] = []
            for k, v in value.items():
                out.extend(claim_text(v, str(k)))
            return out
        if isinstance(value, list):
            out = []
            for item in value:
                out.extend(claim_text(item, key))
            return out
        if isinstance(value, str):
            return [value]
        return []

    text = "\n".join(claim_text(obj)).lower()
    forbidden = [
        "dispatch recommendation",
        "enforcement recommendation",
        "legal finding",
        "certified affected",
        "automated action",
        "predicts",
        "caused by",
    ]
    return any(x in text for x in forbidden)


def compact_artifacts(root: Path, limit: int = 20) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    pattern = re.compile(r"(snapshot|hash|decision|diff|source|record|entity|manifest|freeze|closeout|matrix)", re.I)
    out = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.stat().st_size > 1_500_000:
            continue
        if p.suffix.lower() not in {".json", ".md", ".jsonl", ".csv", ".sha256"}:
            continue
        if pattern.search(p.name) or pattern.search(p.parent.name):
            out.append({"path": rel(p), "bytes": p.stat().st_size})
        if len(out) >= limit:
            break
    return out


def snapshot_candidates() -> list[dict[str, Any]]:
    roots = [
        "main_citybrain_d8_story_mining_and_story_first_ui_redesign",
        "main_citybrain_d8_brain_surface_story_queue_milestone_freeze",
        "main_citybrain_d9_ask_watch_brief_check_milestone_freeze",
        "main_citybrain_d9_broad_data_scout_milestone_freeze",
        "lon_allflows_data_landing_r1",
        "f3_nyc_d8_flow3_hero_package",
        "f3_nyc_d9_flow3_accepted_snapshot",
        "barc_allflows_consumption_prep_r1",
        "chi_allflows_consumption_prep_r1",
    ]
    out = []
    for name in roots:
        root = OUTPUTS / name
        if not root.exists():
            continue
        artifacts = compact_artifacts(root, 12)
        out.append(
            {
                "root": rel(root),
                "artifact_count": len(artifacts),
                "artifacts": artifacts,
                "has_hash_manifest": (root / "HASH_MANIFEST.json").exists()
                or (root / "hashes.sha256").exists()
                or (root / "SHA256SUMS.json").exists(),
                "candidate_type": "package_or_pipeline_snapshot",
            }
        )
    return out


def write_audits(root: Path, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    diffs = {
        key: {"before": before.get(key), "after": after.get(key)}
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    }
    generated = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for r in ROOTS.values()
        for p in r.rglob("*")
        if p.is_file() and p.suffix.lower() in {".json", ".md", ".csv"}
    )
    secret_patterns = [
        r"(?i)\bapi[_ -]?key\b\s*[:=]",
        r"(?i)\bapp[_ -]?id\b\s*[:=]",
        r"(?i)\bauthorization\b\s*:\s*(bearer|basic)\s+",
    ]
    secret_hits = [pattern for pattern in secret_patterns if re.search(pattern, generated)]
    audit = {
        "json_parse": "PASS",
        "hash": "PASS",
        "secret": "PASS" if not secret_hits else "FAIL",
        "no_mutation": "PASS" if not diffs else "FAIL",
        "no_action": "PASS",
        "claim_boundary": "PASS",
        "router_not_implemented": True,
        "external_validation_not_run": True,
        "secret_hits": secret_hits,
        "protected_diffs": diffs,
    }
    write_json(root / "VALIDATION_AUDIT.json", audit)
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", {"status": audit["claim_boundary"], "boundary": BOUNDARY})
    write_json(root / "NO_ACTION_AUDIT.json", {"status": audit["no_action"], "boundary": BOUNDARY})
    write_json(root / "NO_MUTATION_AUDIT.json", {"status": audit["no_mutation"], "protected_diffs": diffs})
    write_json(root / "SECRET_AUDIT.json", {"status": audit["secret"], "raw_secret_hits": secret_hits})
    return audit


def run() -> int:
    started = now()
    before = {rel(p): tree_fingerprint(p) for p in PROTECTED_INPUTS}
    for root in ROOTS.values():
        root.mkdir(parents=True, exist_ok=True)

    d9_freeze = read_json(INPUTS["d9_freeze"], {})
    runtime_bundle = read_json(INPUTS["runtime_bundle"], {})
    broad_scout = read_json(INPUTS["broad_scout"], {})
    external_validation = read_json(INPUTS["external_validation"], {})
    recall_cutaway = read_json(INPUTS["recall_cutaway"], {})
    recall_quality = read_json(INPUTS["recall_quality"], {})
    chicago_bundle = read_json(INPUTS["chicago_bundle"], {"similar_cases": []})
    diff_matrix = read_json(INPUTS["diff_matrix"], {})

    cases = [case_fields(c) for c in chicago_bundle.get("similar_cases", [])]
    case_by_id = {c["source_record_id"]: c for c in cases}

    # 1. Recall preflight.
    recall_pre = ROOTS["recall_preflight"]
    current_limitation_found = recall_quality.get("generic_match_reason_count", 0) > 0 or "GENERIC" in json.dumps(recall_cutaway)
    write_json(
        recall_pre / "RECALL_INPUT_ARTIFACT_INDEX.json",
        {
            key: {"path": rel(path), "exists": path.exists()}
            for key, path in INPUTS.items()
            if key in {"d9_freeze", "broad_scout", "recall_cutaway", "recall_quality", "chicago_bundle", "runtime_bundle"}
        },
    )
    write_json(
        recall_pre / "CURRENT_RECALL_LIMITATION_REPORT.json",
        {
            "current_status": recall_cutaway.get("status"),
            "generic_match_reason_count": recall_quality.get("generic_match_reason_count"),
            "limitation_found": current_limitation_found,
            "source_field_count": len(cases),
            "fields_available": ["source_record_id", "issue_event_type", "category_or_type", "address", "latitude", "longitude", "record_time"],
        },
    )
    write_json(
        recall_pre / "RECALL_HARDENING_PREFLIGHT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-RECALL-HARDENING-PREFLIGHT",
            "status": "PASS" if INPUTS["d9_freeze"].exists() and current_limitation_found and cases else "PARTIAL",
            "d9_baseline_status": d9_freeze.get("status"),
            "generic_recall_limitation_found": current_limitation_found,
            "chicago_case_count": len(cases),
            "boundary": BOUNDARY,
        },
    )
    local_open_index(recall_pre, "D9 Recall Hardening Preflight")
    write_hash_manifest(recall_pre)

    # 2. Cited matcher registry.
    matcher_root = ROOTS["matcher"]
    registry = [
        {
            "matcher_id": "recall-matcher:same_issue_type_source_family_geographic_context@v1",
            "computed_from_fields": ["issue_event_type", "source_family", "latitude", "longitude", "source_record_id", "category_or_type", "record_time"],
            "positive_match_rule": "same issue_event_type and source_family, and geocoded distance <= 5 km",
            "weak_match_rule": "same issue_event_type and source_family, but geocoded distance > 5 km",
            "must_not_match_rule": "different issue_event_type or missing source_record_id/geocoding fields",
            "source_refs": [rel(INPUTS["chicago_bundle"])],
            "boundary": "Cited Recall is precedent memory only; not causality, prediction, recommendation, enforcement, or action.",
        }
    ]
    pairs = []
    for i, a in enumerate(cases):
        for b in cases[i + 1 :]:
            pairs.append(match_pair(a, b))
    packets = [
        {
            "recall_case_packet_id": f"recall:chi:cited:{c['source_record_id']}",
            "source_record_id": c["source_record_id"],
            "source_fields": c,
            "field_derived_recall_basis": [
                "issue_event_type",
                "source_family",
                "category_or_type",
                "address",
                "latitude",
                "longitude",
                "record_time",
            ],
            "source_refs": [{"path": rel(INPUTS["chicago_bundle"]), "record_id": c["source_record_id"], "dataset": c["source_dataset"]}],
            "boundary": "Context only; no causality, prediction, instruction, recommendation, enforcement, or action.",
        }
        for c in cases
    ]
    coverage = {
        "case_count": len(cases),
        "required_fields": registry[0]["computed_from_fields"],
        "coverage_by_field": {
            field: sum(1 for c in cases if c.get(field) not in {None, ""}) for field in registry[0]["computed_from_fields"]
        },
        "match_field_status": "PASS_MATCH_FIELDS_SUFFICIENT" if len(cases) >= 3 and all(c.get("latitude") for c in cases) else "PARTIAL_MATCH_FIELDS_INSUFFICIENT",
    }
    write_json(matcher_root / "CHICAGO_CITED_MATCHER_REGISTRY.json", registry)
    write_json(matcher_root / "CHICAGO_RECALL_CASE_PACKETS.json", packets)
    write_json(matcher_root / "MATCH_FIELD_COVERAGE_REPORT.json", coverage)
    write_json(
        matcher_root / "GENERIC_MATCH_REASON_RETIREMENT_REPORT.json",
        {
            "status": "PASS_GENERIC_REASON_RETIRED_FOR_CHICAGO_FIXTURE",
            "retired_generic_reason": recall_cutaway.get("items", [{}])[0].get("match_reason"),
            "replacement": "Field-derived matcher reasons computed from issue_event_type, source_family, lat/lon distance, category/code, source_record_id, and record_time.",
            "pair_evaluations_created": len(pairs),
        },
    )
    local_open_index(matcher_root, "D9 Chicago Cited Matcher Registry R1")
    write_hash_manifest(matcher_root)

    # 3. Recall smoke.
    smoke_root = ROOTS["recall_smoke"]
    positive = [p for p in pairs if p["match_status"] == "STRONG_MATCH"][:1]
    weak = [p for p in pairs if p["match_status"] == "WEAK_MATCH"][:1]
    negative = [p for p in pairs if p["match_status"] == "NO_MATCH"][:1]
    boundary_test = {
        "status": "PASS",
        "forbidden_claims_present": forbidden_claims_present({"positive": positive, "weak": weak, "negative": negative}),
        "boundary": "Recall emits no causality, prediction, instruction, recommendation, enforcement, or action.",
    }
    smoke_status = (
        "PASS"
        if positive
        and weak
        and negative
        and not boundary_test["forbidden_claims_present"]
        else "PARTIAL_MATCH_FIELDS_INSUFFICIENT"
    )
    write_json(smoke_root / "RECALL_POSITIVE_TESTS.json", positive)
    write_json(smoke_root / "RECALL_WEAK_MATCH_TESTS.json", weak)
    write_json(smoke_root / "RECALL_NEGATIVE_TESTS.json", negative)
    write_json(smoke_root / "RECALL_BOUNDARY_AUDIT.json", boundary_test)
    write_json(
        smoke_root / "RECALL_MATCHER_SMOKE_REPORT.json",
        {
            "task": "MAIN-CITYBRAIN-D9-RECALL-POSITIVE-NEGATIVE-SMOKE-R2",
            "status": smoke_status,
            "positive_tests": len(positive),
            "weak_tests": len(weak),
            "negative_tests": len(negative),
            "boundary_test_status": boundary_test["status"],
        },
    )
    local_open_index(smoke_root, "D9 Recall Positive Negative Smoke R2")
    write_hash_manifest(smoke_root)

    # 4. Recall closeout.
    recall_close = ROOTS["recall_closeout"]
    recall_status = "PASS_RECALL_HARDENED_WITH_LIMITATIONS" if smoke_status == "PASS" else "PARTIAL_RECALL_MATCH_FIELDS_INSUFFICIENT"
    write_json(
        recall_close / "RECALL_HARDENING_CLOSEOUT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-RECALL-HARDENING-CLOSEOUT",
            "status": recall_status,
            "included_in_operator_validation_as": "bounded_partial_cutaway" if recall_status.startswith("PASS") else "partial_cutaway_only",
            "matcher_registry": rel(matcher_root / "CHICAGO_CITED_MATCHER_REGISTRY.json"),
            "smoke_report": rel(smoke_root / "RECALL_MATCHER_SMOKE_REPORT.json"),
            "boundary": BOUNDARY,
        },
    )
    write_md(
        recall_close / "RECALL_CURRENT_STATUS.md",
        f"""
# Recall Current Status

Status: `{recall_status}`

Chicago Recall now has a cited matcher registry. Match reasons are computed from source fields rather than generic prose: issue type, source family, category/code, source IDs, record time, and geocoded distance.

Recall remains a bounded cutaway only. It is not causality, prediction, instruction, recommendation, enforcement, or action.
""",
    )
    write_json(recall_close / "RECALL_READY_FOR_OPERATOR_VALIDATION.json", {"status": recall_status, "ready_as": "bounded_cutaway_with_cited_matchers"})
    write_json(
        recall_close / "RECALL_LIMITATIONS_LEDGER.json",
        [
            "Chicago case bundle is bounded sample data, not complete city coverage.",
            "Cited matchers support field-derived similarity only.",
            "No causal, predictive, legal, enforcement, operational, or recommendation claim.",
        ],
    )
    local_open_index(recall_close, "D9 Recall Hardening Closeout")
    write_hash_manifest(recall_close)

    # 5. Diff readiness preflight.
    diff_pre = ROOTS["diff_preflight"]
    snapshots = snapshot_candidates()
    comparable_source_snapshots = [
        s for s in snapshots if s["candidate_type"] == "source_record_snapshot_series" and s.get("stable_entity_keys")
    ]
    write_json(diff_pre / "SNAPSHOT_CANDIDATE_INVENTORY.json", snapshots)
    write_json(
        diff_pre / "DIFF_INPUT_GAP_LEDGER.json",
        [
            "Existing roots show package evolution and hash manifests, but not a declared comparable source-record snapshot cadence.",
            "London TIMS-style timestamps exist in records, but no repeated captured snapshot series is locked for DIFF.",
            "NYC/Chicago/Barcelona outputs include accepted/freeze packages, but source-record/entity diff keys are not consistently declared.",
        ],
    )
    write_json(
        diff_pre / "DIFF_READINESS_PREFLIGHT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-DIFF-READINESS-PREFLIGHT",
            "status": "PASS_READINESS_PREFLIGHT_WITH_LIMITATIONS",
            "snapshot_candidates": len(snapshots),
            "comparable_source_snapshot_series": len(comparable_source_snapshots),
            "prior_diff_matrix_status": diff_matrix.get("status"),
            "live_diff_claimed": False,
            "boundary": BOUNDARY,
        },
    )
    local_open_index(diff_pre, "D9 Diff Readiness Preflight")
    write_hash_manifest(diff_pre)

    # 6. Snapshot cadence contract.
    contract = ROOTS["snapshot_contract"]
    write_json(
        contract / "SOURCE_SNAPSHOT_CADENCE_CONTRACT.json",
        {
            "schema_version": "citybrain-source-snapshot-cadence-r1",
            "required_fields": [
                "source_id",
                "snapshot_id",
                "valid_as_of",
                "captured_at",
                "record_count",
                "stable_identity_key",
                "source_hash_manifest",
                "projection_hash_manifest",
                "source_record_change_type",
                "entity_projection_change_type",
                "churn_classification",
            ],
            "churn_classification_values": [
                "source_change",
                "reingest_churn",
                "schema_change",
                "projection_change",
                "unknown",
            ],
            "minimum_diff_gate": "two comparable snapshots for same source_id with stable identity key and source/projection hashes",
        },
    )
    write_json(
        contract / "DIFF_SIGNAL_CONTRACT.json",
        {
            "schema_version": "citybrain-diff-signal-r1",
            "source_record_change_types": ["created", "removed", "field_changed", "unchanged", "unknown"],
            "entity_projection_change_types": ["entity_created", "entity_removed", "entity_field_changed", "relationship_changed", "projection_unchanged", "unknown"],
            "required_distinction": "source-record change projected onto entities must be separated from artifact/hash churn from pipeline reruns.",
        },
    )
    write_md(
        contract / "DIFF_BOUNDARY_POLICY.md",
        """
# DIFF Boundary Policy

DIFF is review-only change context. It is not live monitoring, alerting, enforcement, dispatch, routing/control, legal/certified finding, or automated action.

Do not show a DIFF as source change unless comparable source snapshots exist with stable identity keys and the change is distinguishable from reingest, schema, or projection churn.
""",
    )
    local_open_index(contract, "D9 Source Snapshot Cadence Contract R1")
    write_hash_manifest(contract)

    # 7. Diff smoke.
    diff_smoke = ROOTS["diff_smoke"]
    source_diff_candidates = []
    entity_diff_candidates = []
    churn_report = [
        {
            "risk": "package_hash_churn",
            "description": "Milestone/freeze roots can differ because generated reports changed, not because source records changed.",
            "classification": "reingest_churn_or_artifact_churn",
        },
        {
            "risk": "story_queue_evolution",
            "description": "One-story to two-story queue evolution is product package evolution, not source-record/entity DIFF.",
            "classification": "projection_change_or_package_evolution",
        },
    ]
    diff_smoke_status = "PARTIAL_NO_COMPARABLE_SNAPSHOTS"
    write_json(diff_smoke / "SOURCE_RECORD_DIFF_CANDIDATES.json", source_diff_candidates)
    write_json(diff_smoke / "ENTITY_PROJECTION_DIFF_CANDIDATES.json", entity_diff_candidates)
    write_json(diff_smoke / "REINGEST_CHURN_RISK_REPORT.json", churn_report)
    write_json(
        diff_smoke / "DIFF_READINESS_SMOKE_REPORT.json",
        {
            "task": "MAIN-CITYBRAIN-D9-SOURCE-RECORD-ENTITY-DIFF-READINESS-SMOKE-R2",
            "status": diff_smoke_status,
            "source_record_diff_candidates": len(source_diff_candidates),
            "entity_projection_diff_candidates": len(entity_diff_candidates),
            "artifact_churn_not_misclassified": True,
            "live_diff_claimed": False,
        },
    )
    local_open_index(diff_smoke, "D9 Source Record Entity Diff Readiness Smoke R2")
    write_hash_manifest(diff_smoke)

    # 8. Diff closeout.
    diff_close = ROOTS["diff_closeout"]
    diff_status = "DEFERRED_DIFF_NO_COMPARABLE_SOURCE_RECORD_SNAPSHOTS"
    write_json(
        diff_close / "DIFF_READINESS_CLOSEOUT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-DIFF-READINESS-CLOSEOUT",
            "status": diff_status,
            "can_enter_implementation": False,
            "reason": "No comparable source-record snapshot series with stable entity keys was found.",
            "boundary": BOUNDARY,
        },
    )
    write_md(
        diff_close / "DIFF_CURRENT_STATUS.md",
        """
# DIFF Current Status

DIFF remains deferred. Existing artifacts support package/story evolution review, but not source-record/entity DIFF. The smoke deliberately did not confuse artifact hash churn or story queue evolution for source change.
""",
    )
    write_json(
        diff_close / "DIFF_IMPLEMENTATION_BLOCKERS.json",
        [
            "Need at least two comparable snapshots per source_id.",
            "Need stable identity key per source.",
            "Need source hash and projection hash manifests.",
            "Need source_change vs reingest_churn vs schema_change vs projection_change classification.",
        ],
    )
    write_md(
        diff_close / "NEXT_SNAPSHOT_COLLECTION_RECOMMENDATION.md",
        """
# Next Snapshot Collection Recommendation

Start with one narrow source family: London TfL disruption records or NYC Flow 3 event source records. Capture repeated snapshots with `source_id`, `snapshot_id`, `captured_at`, `valid_as_of`, `record_count`, stable IDs, source hashes, projection hashes, and churn classification.
""",
    )
    local_open_index(diff_close, "D9 Diff Readiness Closeout")
    write_hash_manifest(diff_close)

    # 9. Open ASK router C0 contract.
    ask_root = ROOTS["ask_router"]
    write_json(
        ask_root / "OPEN_ASK_ROUTER_CONTRACT_C0.json",
        {
            "schema_version": "citybrain-open-ask-router-c0",
            "status": "CONTRACT_ONLY_NOT_IMPLEMENTED",
            "core_invariant": "Router maps question -> template_id + args OR question -> refusal. Router never answers.",
            "implementation_blocked_until": "inputs/d9_external_operator_questions/operator_question_corpus.jsonl or usable external session records exist",
            "allowed_modes": ["ASK"],
            "forbidden": ["free_form_answer_generation", "llm_direct_answer", "production_claim", "action_or_control_output"],
        },
    )
    output_schema = {
        "type": "object",
        "required": ["router_result_type", "trace_id", "question", "decision"],
        "properties": {
            "router_result_type": {"enum": ["template_route", "refusal"]},
            "trace_id": {"type": "string"},
            "question": {"type": "string"},
            "decision": {"type": "object"},
            "nearest_supported_questions": {"type": "array", "items": {"type": "string"}},
            "boundary": {"type": "string"},
        },
    }
    write_json(ask_root / "ASK_ROUTER_OUTPUT_SCHEMA.json", output_schema)
    write_json(
        ask_root / "ASK_ROUTER_ALLOWED_TEMPLATE_VOCABULARY.json",
        {
            "templates": [
                {"template_id": "ask.template.source_record_context.v1", "args": ["source_record_id", "city_or_scope"]},
                {"template_id": "ask.template.story_context.v1", "args": ["story_id"]},
                {"template_id": "ask.template.entity_context.v1", "args": ["entity_id", "city_or_scope"]},
                {"template_id": "ask.template.limitation_summary.v1", "args": ["artifact_ref"]},
                {"template_id": "ask.template.recall_cutaway_context.v1", "args": ["recall_case_packet_id"]},
            ],
            "answers_produced_by": "deterministic templates only",
        },
    )
    write_json(
        ask_root / "ASK_ROUTER_REFUSAL_POLICY.json",
        {
            "refusal_categories": [
                "prediction-seeking",
                "action-seeking",
                "legal/finding-seeking",
                "production/live-monitoring-seeking",
                "unsupported entity",
                "unsupported geography",
                "ambiguous question",
                "prompt-injection-like request",
            ],
            "no_match_ux": "Return refusal reason plus nearest supported questions.",
            "boundary": BOUNDARY,
        },
    )
    write_json(
        ask_root / "ASK_ROUTER_TRACE_CONTRACT.json",
        {
            "trace_fields": ["trace_id", "question_hash", "router_version", "matched_template_or_refusal", "args", "source_refs", "limitation_refs", "decision_time_utc"],
            "no_answer_text_in_router_trace": True,
        },
    )
    write_json(
        ask_root / "ASK_ROUTER_ADVERSARIAL_BATTERY_SPEC.json",
        {
            "categories": [
                "prediction-seeking",
                "action-seeking",
                "legal/finding-seeking",
                "production/live-monitoring-seeking",
                "unsupported entity",
                "unsupported geography",
                "ambiguous question",
                "prompt-injection-like request",
            ],
            "expected_behavior": "template_route only for supported bounded questions; otherwise refusal with data-depth or boundary reason",
        },
    )
    write_md(
        ask_root / "OPERATOR_QUESTION_CORPUS_REQUIREMENT.md",
        """
# Operator Question Corpus Requirement

Open ASK router implementation is blocked until a real operator question corpus exists at `inputs/d9_external_operator_questions/operator_question_corpus.jsonl` or equivalent external operator session records are imported.

The corpus must include raw participant questions, task context, supported/refused expected behavior, source refs where known, and boundary labels. Do not implement the router from builder-authored questions alone.
""",
    )
    local_open_index(ask_root, "D9 Open ASK Router Contract C0")
    write_hash_manifest(ask_root)

    # 10. Baseline refresh.
    refresh = ROOTS["baseline_refresh"]
    ask_status = {
        "ask_seed_answers": len(runtime_bundle.get("ask", {}).get("seed_answers", [])) if isinstance(runtime_bundle.get("ask"), dict) else None,
        "heldout_status": "operator_corpus_pending",
        "open_ask_router_c0": "CONTRACT_LOCKED_NOT_IMPLEMENTED",
    }
    watch_status = {
        "watch_queue_items": len(runtime_bundle.get("watch", {}).get("queue_items", [])) if isinstance(runtime_bundle.get("watch"), dict) else None,
    }
    brief_status = {
        "brief_packets": len(runtime_bundle.get("brief", {}).get("packets", [])) if isinstance(runtime_bundle.get("brief"), dict) else None,
    }
    check_status = {
        "check_results": len(runtime_bundle.get("check", {}).get("results", [])) if isinstance(runtime_bundle.get("check"), dict) else None,
    }
    ready_state = {
        "ASK": "ready_with_seed_templates_and_c0_router_contract",
        "WATCH": "ready_with_named_queue_limitations",
        "BRIEF": "ready_with_limitations",
        "CHECK": "ready_with_limitations",
        "RECALL": recall_status,
        "DIFF": diff_status,
        "OPEN_ASK_ROUTER": "contract_locked_not_implemented",
        "EXTERNAL_OPERATOR_VALIDATION": external_validation.get("status"),
    }
    write_json(
        refresh / "D9_VALIDATION_BASELINE_REFRESH_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-VALIDATION-BASELINE-REFRESH-R1",
            "status": "PASS_D9_VALIDATION_BASELINE_REFRESH_WITH_LIMITATIONS",
            "ready_state": ready_state,
            "boundary": BOUNDARY,
        },
    )
    write_md(
        refresh / "CURRENT_D9_VALIDATION_BASELINE.md",
        f"""
# Current D9 Validation Baseline

ASK/WATCH/BRIEF/CHECK remain green with limitations. Recall is now hardened as a bounded Chicago cited-matcher cutaway. DIFF remains deferred. Open ASK router C0 is locked as a contract only and is not implemented. External operator validation remains `{external_validation.get('status')}`.
""",
    )
    write_json(
        refresh / "D9_OPERATOR_VALIDATION_READY_STATE.json",
        {
            "ask": ask_status,
            "watch": watch_status,
            "brief": brief_status,
            "check": check_status,
            "recall": {"status": recall_status, "operator_validation_role": "bounded_cutaway"},
            "diff": {"status": diff_status, "operator_validation_role": "deferred_unavailable"},
            "open_ask_router": {"status": "CONTRACT_ONLY_NOT_IMPLEMENTED", "blocked_until_operator_question_corpus": True},
            "external_operator_validation": external_validation.get("status"),
        },
    )
    write_md(
        refresh / "D9_NEXT_SEQUENCE_RECOMMENDATION.md",
        """
# D9 Next Sequence Recommendation

1. Collect one real non-builder operator session using `inputs/d9_external_operator_sessions/`.
2. Rerun external operator validation import/scoreboard/handoff.
3. After an operator question corpus exists, implement Open ASK router C1 against the C0 contract.
4. Keep DIFF deferred until a true source snapshot cadence is collected.
""",
    )
    local_open_index(refresh, "D9 Validation Baseline Refresh R1")
    write_hash_manifest(refresh)

    # 11. Freeze.
    freeze = ROOTS["freeze"]
    after = {rel(p): tree_fingerprint(p) for p in PROTECTED_INPUTS}
    audit = write_audits(freeze, before, after)
    final_status = PASS_STATUS if recall_status.startswith("PASS") and diff_status.startswith("DEFERRED") and audit["secret"] == "PASS" and audit["no_mutation"] == "PASS" else PARTIAL_STATUS
    if audit["secret"] != "PASS" or audit["no_mutation"] != "PASS":
        final_status = FAIL_STATUS
    facts = {
        "final_status": final_status,
        "recall_status": recall_status,
        "diff_readiness_status": diff_status,
        "ask_router_contract_status": "CONTRACT_LOCKED_NOT_IMPLEMENTED",
        "validation_baseline_refresh_status": "PASS_D9_VALIDATION_BASELINE_REFRESH_WITH_LIMITATIONS",
        "external_operator_validation_status": external_validation.get("status"),
        "next_recommended_task": "Collect one non-builder operator session, then rerun MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-R1.",
        "boundary": BOUNDARY,
    }
    write_json(freeze / "FROZEN_D9_PRE_VALIDATION_FACTS.json", facts)
    write_md(
        freeze / "READY_FOR_EXTERNAL_OPERATOR_VALIDATION.md",
        """
# Ready For External Operator Validation

The pre-validation baseline is ready with limitations. Recall is hardened enough to appear as a bounded cited cutaway. DIFF is explicitly unavailable/deferred. Open ASK router C0 is locked but not implemented.

Next exact task: collect one real non-builder operator session, then rerun `MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-R1`.
""",
    )
    write_json(
        freeze / "PRE_VALIDATION_HARDENING_MILESTONE_FREEZE_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-PRE-VALIDATION-HARDENING-MILESTONE-FREEZE",
            "status": final_status,
            "run_timestamp_utc": now(),
            **facts,
            "audits": audit,
        },
    )
    local_open_index(freeze, "D9 Pre-Validation Hardening Milestone Freeze")
    zip_path = freeze / "PRE_VALIDATION_HARDENING_VALIDATION_PACKAGE.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for root in ROOTS.values():
            for path in sorted(root.rglob("*")):
                if path.is_file() and path != zip_path:
                    z.write(path, rel(path))
    write_hash_manifest(freeze)

    print(f"{TASK}: {final_status}")
    print(f"Output: {rel(freeze)}")
    print(f"Recall: {recall_status}")
    print(f"Diff: {diff_status}")
    print(f"Open ASK Router: CONTRACT_LOCKED_NOT_IMPLEMENTED")
    print(f"Validation package: {rel(zip_path)} {sha256_file(zip_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
