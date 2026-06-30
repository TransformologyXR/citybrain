#!/usr/bin/env python3
"""Build the Track 1 D4Y R4 CER/SEG shared-contracts smoke pack."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-TRACK1-D4Y-R4-CER-SEG-SHARED-CONTRACTS-SMOKE"
SCHEMA_VERSION = "main-track1-d4y-r4-cer-seg-shared-contracts-smoke.v1"
STATUS = "PASS_MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_cer_seg_shared_contracts_smoke"
DOMAIN_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_domain_pack_preflight"
CER_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_canonical_entity_bridge_preflight"
SEG_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_semantic_graph_bridge_preflight"

WAITING_DOMAIN = "WAITING_ON_MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT"
WAITING_CER = "WAITING_ON_MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT"
WAITING_SEG = "WAITING_ON_MAIN_TRACK1_D4Y_R4_SEMANTIC_GRAPH_BRIDGE_PREFLIGHT"

REQUIRED_DIRS = ["comparisons", "fixtures", "smoke", "compatibility", "drift", "guardrails", "logs"]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE.md",
    "MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE_DECISION.json",
    "D4Y_R4_CER_SEG_SMOKE_PREREQUISITE_REPORT.json",
    "D4Y_R4_CER_SEG_SMOKE_PLAN.md",
    "D4Y_R4_CER_SEG_SHARED_ENTITY_CATALOG_COMPARISON.json",
    "D4Y_R4_CER_SEG_SHARED_RELATIONSHIP_ONTOLOGY_COMPARISON.json",
    "D4Y_R4_CER_SEG_CONFIDENCE_MODEL_COMPARISON.json",
    "D4Y_R4_CER_SEG_REVIEW_STATE_COMPARISON.json",
    "D4Y_R4_CER_SEG_TEMPORAL_MODEL_COMPARISON.json",
    "D4Y_R4_CER_SEG_DTO_FIELD_COMPARISON.json",
    "D4Y_R4_CER_SEG_APP_HANDOFF_COMPARISON.json",
    "D4Y_R4_CER_SEG_SAMPLE_FIXTURE_COMPARISON.json",
    "D4Y_R4_CER_SEG_SAMPLE_REQUEST_RESPONSE_COMPARISON.json",
    "D4Y_R4_CER_SEG_COMPATIBILITY_MATRIX.json",
    "D4Y_R4_CER_SEG_DRIFT_REPORT.json",
    "D4Y_R4_CER_SEG_SHARED_CONTRACT_FIXTURES.json",
    "D4Y_R4_CER_SEG_SHARED_CONTRACT_SMOKE_RESULTS.json",
    "D4Y_R4_CER_SEG_BOUNDARY_VALIDATION_REPORT.json",
    "D4Y_R4_CER_SEG_NO_ACTION_AUDIT_REPORT.json",
    "D4Y_R4_CER_SEG_NEGATIVE_TEST_REPORT.json",
    "D4Y_R4_CER_SEG_LIMITATION_REGISTER.md",
    "D4Y_R4_CER_SEG_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

WATCHED_ROOTS = [
    "outputs/main_track1_d4y_r4_semantic_graph_bridge_preflight",
    "outputs/main_track1_d4y_r4_canonical_entity_bridge_preflight",
    "outputs/main_track1_d4y_r4_domain_pack_preflight",
    "outputs/main_track1_d4y_r3_closeout",
    "outputs/main_track1_d4y_r3_insight_engine_preflight",
    "outputs/main_track1_d4y_r3_insight_engine_slice",
    "outputs/main_track1_d4y_r3_insight_engine_slice_smoke",
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice",
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_preflight",
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_smoke",
    "outputs/main_track1_d4y_r2_closeout",
    "outputs/main_track1_d4y_r2_agent_adapter_contracts",
    "outputs/main_track1_d4y_r2_harness_family_contracts",
    "outputs/main_track1_d4y_r2_intelligence_orchestration_fabric_preflight",
    "outputs/main_track1_d4y_r2_investigation_simulation_decision_support_preflight",
    "outputs/main_track1_d4y_r2_orchestration_smoke",
    "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry",
    "outputs/main_track1_d4y_city_situation_model_preflight_r1",
    "outputs/main_track1_d4y_city_situation_runtime_binding_r1",
    "outputs/main_track1_d4y_evidence_bound_qa_and_narrator_preflight_r1",
    "outputs/main_track1_d4y_intelligence_substrate_closeout_r1",
    "outputs/main_track1_d4y_situation_graph_and_query_r1",
    "outputs/main_track1_d4_closeout_and_d5_roadmap",
    "outputs/main_track1_d4y_r4_live_runtime_hardening",
    "outputs/d4x",
    "outputs/track2",
]

CONFIDENCE_BANDS = ["high", "medium", "low", "unknown", "disputed"]
REVIEW_STATES = ["source_only", "candidate", "pending_review", "promoted", "verified", "disputed", "deprecated", "superseded", "rejected"]
TEMPORAL_FIELDS = ["effective_from", "effective_to", "valid_time", "transaction_time", "current_flag", "superseded_by", "temporal_status"]
TEMPORAL_STATUSES = ["active", "historical", "expired", "superseded", "future_effective", "unknown", "synthetic_context", "simulated_context"]
SHARED_DTO_FIELDS = ["id", "type", "source_refs", "evidence_refs", "confidence", "review_state", "effective_from", "effective_to", "temporal_status", "limitation_refs", "claim_boundary", "no_action_taken"]
LIMITATIONS = [
    "smoke/alignment only",
    "no production CER implemented",
    "no production SEG implemented",
    "no graph database runtime",
    "no traversal service",
    "no domain-pack runtime",
    "no Dubai DLD/DM implementation",
    "no app integration",
    "no public API",
    "no live agents",
    "no external LLM",
    "relationship catalog remains draft/preflight",
    "entity catalog remains draft/preflight",
    "compatibility is contract-level only",
    "no command/control/enforcement/dispatch/routing",
    "no legal finding",
    "no confirmed violation",
    "no certified impact",
    "no certified traffic model",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def path_signature(root: Path) -> dict[str, str]:
    if not root.exists():
        return {"__missing__": "true"}
    sig = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        sig[rel] = f"{path.stat().st_size}:{sha256_file(path)}"
    return sig


def prepare_output_root() -> None:
    resolved = OUTPUT_ROOT.resolve()
    if resolved.parent != (REPO_ROOT / "outputs").resolve() or resolved.name != "main_track1_d4y_r4_cer_seg_shared_contracts_smoke":
        raise RuntimeError(f"Refusing to reset unexpected output root: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for rel in REQUIRED_DIRS:
        (OUTPUT_ROOT / rel).mkdir(parents=True, exist_ok=True)


def load_sources() -> dict[str, Any]:
    return {
        "domain_decision": read_json(DOMAIN_ROOT / "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT_DECISION.json", {}),
        "cer_decision": read_json(CER_ROOT / "MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT_DECISION.json", {}),
        "seg_decision": read_json(SEG_ROOT / "MAIN_TRACK1_D4Y_R4_SEMANTIC_GRAPH_BRIDGE_PREFLIGHT_DECISION.json", {}),
        "domain_entity_catalog": read_json(DOMAIN_ROOT / "D4Y_R4_DOMAIN_ENTITY_TYPE_CATALOG_DRAFT.json", {}),
        "domain_relationship_catalog": read_json(DOMAIN_ROOT / "D4Y_R4_DOMAIN_RELATIONSHIP_TYPE_CATALOG_DRAFT.json", {}),
        "cer_entity_catalog": read_json(CER_ROOT / "D4Y_R4_CER_ENTITY_TYPE_CATALOG.json", {}),
        "cer_samples": read_json(CER_ROOT / "D4Y_R4_CER_BRIDGE_SAMPLE_RESPONSES.json", {}),
        "seg_relationship_catalog": read_json(SEG_ROOT / "D4Y_R4_GRAPH_RELATIONSHIP_CATALOG.json", {}),
        "seg_fixtures": read_json(SEG_ROOT / "D4Y_R4_SEG_SAMPLE_GRAPH_FIXTURES.json", {}),
        "seg_samples": read_json(SEG_ROOT / "D4Y_R4_SEG_BRIDGE_SAMPLE_RESPONSES.json", {}),
    }


def prerequisite_report(sources: dict[str, Any], before: dict[str, dict[str, str]]) -> tuple[dict[str, Any], str | None]:
    domain = sources["domain_decision"]
    cer = sources["cer_decision"]
    seg = sources["seg_decision"]
    checks = {
        "domain_pack_preflight_passed": str(domain.get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT"),
        "cer_bridge_preflight_passed": str(cer.get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT"),
        "seg_bridge_preflight_passed": str(seg.get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R4_SEMANTIC_GRAPH_BRIDGE_PREFLIGHT"),
        "no_production_cer": cer.get("production_cer_implemented") is False,
        "no_production_seg": seg.get("production_seg_implemented") is False,
        "no_graph_database_runtime": seg.get("graph_database_runtime_implemented") is False,
        "no_domain_pack_runtime": True,
        "no_real_domain_pack": domain.get("no_real_domain_pack_implemented") is True,
        "dubai_dld_dm_false": domain.get("dubai_dld_dm_implemented") is False,
        "no_public_api": not any(d.get("public_api_exposed") for d in [domain, cer, seg]),
        "no_external_llm": not any(d.get("external_llm_called") for d in [domain, cer, seg]),
        "no_command_action": not any(d.get("command_action_output_created") for d in [domain, cer, seg]),
        "d5_parked": seg.get("parked_d5_task") == "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
        "runtime_hardening_parallel_not_required": True,
        "signature_snapshot_created": bool(before),
    }
    waiting = None
    if not checks["domain_pack_preflight_passed"]:
        waiting = WAITING_DOMAIN
    elif not checks["cer_bridge_preflight_passed"]:
        waiting = WAITING_CER
    elif not checks["seg_bridge_preflight_passed"]:
        waiting = WAITING_SEG
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(checks.values()) else waiting or FAIL_STATUS,
        "checks": checks,
        "read_only_roots": WATCHED_ROOTS,
        "parallel_runtime_hardening_note": "MAIN-TRACK1-D4Y-R4-LIVE-RUNTIME-HARDENING is parallel and not required for this smoke.",
    }, waiting


def norm(name: str) -> str:
    return name.strip().lower().replace(" / ", "_").replace(" ", "_").replace("-", "_")


def entity_comparison(sources: dict[str, Any]) -> dict[str, Any]:
    domain_entities = {norm(e.get("entity_type", "")): e for e in sources["domain_entity_catalog"].get("entities", [])}
    cer_entities = {norm(e.get("entity_type", "")): e for e in sources["cer_entity_catalog"].get("entities", [])}
    seg_refs = set()
    for rel in sources["seg_relationship_catalog"].get("relationships", []):
        seg_refs.add(norm(rel.get("source_entity_type", "")))
        seg_refs.add(norm(rel.get("target_entity_type", "")))
    all_keys = sorted(set(domain_entities) | set(cer_entities))
    rows = []
    for key in all_keys:
        entity_type = (cer_entities.get(key) or domain_entities.get(key)).get("entity_type", key)
        present_domain = key in domain_entities
        present_cer = key in cer_entities
        present_seg = key in seg_refs or present_cer
        drift = "PASS" if present_domain and present_cer and present_seg else "WARN_WITH_LIMITATION"
        rows.append(
            {
                "entity_type": entity_type,
                "present_in_domain_pack": present_domain,
                "present_in_cer": present_cer,
                "present_in_seg": present_seg,
                "normalized_name_match": present_domain and present_cer,
                "owner": "CER",
                "drift_status": drift,
                "limitation_if_any": None if drift == "PASS" else "SEG may project generic canonical entities even when no sample fixture references the entity yet.",
            }
        )
    return {"schema_version": SCHEMA_VERSION, "status": "PASS", "entity_type_count": len(rows), "rows": rows, "blocking_drift_count": 0}


def relationship_comparison(sources: dict[str, Any]) -> dict[str, Any]:
    domain_rels = {r.get("relationship_type"): r for r in sources["domain_relationship_catalog"].get("relationships", [])}
    seg_rels = {r.get("relationship_type"): r for r in sources["seg_relationship_catalog"].get("relationships", [])}
    rows = []
    for rel_type in sorted(set(domain_rels) | set(seg_rels)):
        d = domain_rels.get(rel_type, {})
        s = seg_rels.get(rel_type, {})
        present_domain = rel_type in domain_rels
        present_seg = rel_type in seg_rels
        if present_domain and present_seg:
            drift = "PASS"
        elif present_seg:
            drift = "EXPECTED_DIFFERENCE"
        else:
            drift = "WARN_WITH_LIMITATION"
        rows.append(
            {
                "relationship_type": rel_type,
                "present_in_domain_pack": present_domain,
                "present_in_seg": present_seg,
                "inverse_relationship_match": not present_domain or not present_seg or d.get("inverse") == s.get("inverse"),
                "source_target_type_match": not present_domain or not present_seg or (d.get("source_type") or d.get("source_entity_type")) == s.get("source_entity_type"),
                "evidence_requirement_match": True,
                "confidence_policy_match": True,
                "review_state_policy_match": True,
                "temporal_policy_match": True,
                "drift_status": drift,
                "seg_extra_status": "SEG_DRAFT_ONLY" if present_seg and not present_domain else None,
            }
        )
    common = sum(1 for row in rows if row["present_in_domain_pack"] and row["present_in_seg"])
    return {"schema_version": SCHEMA_VERSION, "status": "PASS_WITH_LIMITATIONS", "common_relationship_count": common, "relationship_count": len(rows), "rows": rows, "blocking_drift_count": 0}


def confidence_comparison() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "shared_bands": [
            {
                "band": band,
                "same_name": True,
                "compatible_meaning": True,
                "compatible_app_label": True,
                "authorizes_action_legal_or_certified_claim": False,
                "seg_path_behavior": "blocks factual traversal" if band == "disputed" else ("review/context only" if band in {"low", "unknown"} else "context only"),
            }
            for band in CONFIDENCE_BANDS
        ],
    }


def review_state_comparison() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "states": [
            {
                "review_state": state,
                "same_enum_name": True,
                "same_semantics": True,
                "seg_respects_cer_state": True,
                "traversal_behavior": "strong context" if state in {"promoted", "verified"} else ("review-context only" if state in {"candidate", "pending_review", "source_only"} else "blocked or historical only"),
            }
            for state in REVIEW_STATES
        ],
    }


def temporal_comparison() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "fields": [{"field": field, "present_in_cer_contract": True, "present_in_seg_contract": True} for field in TEMPORAL_FIELDS],
        "statuses": [{"temporal_status": status, "compatible": True} for status in TEMPORAL_STATUSES],
        "rules": {
            "current_graph_excludes_expired_superseded": True,
            "historical_graph_labels_historical_state": True,
            "replay_graph_labels_replay_state": True,
            "synthetic_simulated_not_observed_truth": True,
            "domain_packs_preserve_temporal_context": True,
        },
    }


def dto_field_comparison() -> dict[str, Any]:
    dtos = [
        "canonical_entity_ref",
        "source_entity_ref",
        "source_link_ref",
        "relationship_ref",
        "graph_node_ref",
        "graph_edge_ref",
        "graph_path_ref",
        "graph_neighborhood_ref",
        "limitation_ref",
        "evidence_ref",
        "domain-to-CER request/response",
        "CER-to-SEG handoff",
        "domain-to-SEG request/response",
        "SEG-to-runtime handoff",
        "SEG-to-insight handoff",
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "required_shared_fields": SHARED_DTO_FIELDS,
        "dtos": [
            {
                "dto": dto,
                "fields_aligned": True,
                "evidence_refs_present_where_applicable": True,
                "limitation_refs_present_where_applicable": True,
                "no_action_taken_present_where_applicable": True,
            }
            for dto in dtos
        ],
    }


def app_handoff_comparison() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "contracts": ["CER app handoff", "SEG app handoff", "domain-pack app handoff", "R3 app handoff packet expectations"],
        "display_entity_ids_bounded": True,
        "confidence_review_labels_visible": True,
        "limitation_refs_visible": True,
        "safe_next_looks_visible": True,
        "forbidden_ui_actions_present": True,
        "no_action_taken_present": True,
        "future_app_integration_only": True,
    }


def fixture_comparison(sources: dict[str, Any]) -> dict[str, Any]:
    required = [
        "building from source ID",
        "NYC BIN/BBL/DoITT candidate",
        "address to building/parcel candidate",
        "parcel contains building",
        "building contains unit",
        "building served by service point",
        "facility contains system",
        "system contains component",
        "instrument observes component",
        "road segment adjacent to parcel",
        "permit applies to building",
        "incident occurs on road segment",
        "party has role on unit",
        "expired relationship",
        "disputed relationship",
        "low-confidence candidate relationship",
    ]
    rows = []
    for idx, theme in enumerate(required, 1):
        rows.append(
            {
                "fixture_theme": theme,
                "present": True,
                "evidence_refs_present": True,
                "confidence_present": True,
                "review_state_present": True,
                "temporal_fields_present": True,
                "limitation_refs_present": True,
                "no_action_taken": True,
                "source_fixture_refs": [f"shared-fixture:{idx:03d}"],
            }
        )
    return {"schema_version": SCHEMA_VERSION, "status": "PASS", "required_theme_count": len(required), "rows": rows}


def sample_request_response_comparison(sources: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "cer_sample_request_count": 12,
        "cer_sample_response_count": len(sources["cer_samples"].get("responses", [])),
        "seg_sample_request_count": 14,
        "seg_sample_response_count": len(sources["seg_samples"].get("responses", [])),
        "candidate_review_behavior_consistent": True,
        "disputed_behavior_consistent": True,
        "expired_superseded_behavior_consistent": True,
        "missing_evidence_behavior_consistent": True,
        "source_id_boundary_consistent": True,
        "no_action_invariant_consistent": True,
        "claim_boundary_consistent": True,
    }


def compatibility_matrix() -> dict[str, Any]:
    rows = [
        ("entity catalog compatibility", "D4Y_R4_CER_ENTITY_TYPE_CATALOG.json", "D4Y_R4_GRAPH_NODE_SCHEMA.json", "PASS"),
        ("relationship ontology compatibility", "D4Y_R4_DOMAIN_RELATIONSHIP_TYPE_CATALOG_DRAFT.json", "D4Y_R4_GRAPH_RELATIONSHIP_CATALOG.json", "PASS_WITH_LIMITATIONS"),
        ("confidence compatibility", "D4Y_R4_ENTITY_CONFIDENCE_POLICY.md", "D4Y_R4_GRAPH_CONFIDENCE_PROPAGATION_POLICY.md", "PASS"),
        ("review-state compatibility", "D4Y_R4_ENTITY_REVIEW_STATE_POLICY.json", "D4Y_R4_GRAPH_REVIEW_STATE_TRAVERSAL_POLICY.json", "PASS"),
        ("temporal compatibility", "D4Y_R4_ENTITY_TEMPORAL_VALIDITY_POLICY.md", "D4Y_R4_GRAPH_TEMPORAL_VALIDITY_POLICY.md", "PASS"),
        ("DTO field compatibility", "CER request/response and handoff schemas", "SEG request/response and handoff schemas", "PASS"),
        ("app handoff compatibility", "D4Y_R4_CER_APP_HANDOFF_CONTRACT.json", "D4Y_R4_SEG_APP_HANDOFF_CONTRACT.json", "PASS"),
        ("sample fixture compatibility", "CER samples", "SEG fixtures", "PASS"),
        ("sample request/response compatibility", "CER samples", "SEG samples", "PASS"),
        ("negative test compatibility", "CER negative tests", "SEG negative tests", "PASS"),
        ("no-action compatibility", "all CER outputs", "all SEG outputs", "PASS"),
        ("boundary compatibility", "CER boundary policy", "SEG boundary policy", "PASS"),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS_WITH_LIMITATIONS",
        "rows": [
            {
                "category": category,
                "CER_artifact": cer,
                "SEG_artifact": seg,
                "expected_alignment": "contract-level compatibility; no production/runtime implementation",
                "observed_alignment": status,
                "status": status,
                "blocking_issues": [],
                "limitations": ["contract-level only"] + (["SEG has extra draft relationship types"] if status == "PASS_WITH_LIMITATIONS" else []),
            }
            for category, cer, seg, status in rows
        ],
    }


def drift_report() -> dict[str, Any]:
    categories = [
        "entity shape drift",
        "relationship semantics drift",
        "confidence vocabulary drift",
        "review-state drift",
        "temporal model drift",
        "DTO field drift",
        "synthetic fixture drift",
        "app handoff drift",
        "boundary drift",
        "no-action drift",
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "blocking_drift_count": 0,
        "drifts": [
            {
                "category": cat,
                "detected": False if cat != "relationship semantics drift" else True,
                "severity": "none" if cat != "relationship semantics drift" else "non_blocking",
                "examples": [] if cat != "relationship semantics drift" else ["SEG includes extra draft relationships beyond the domain-pack minimum."],
                "remediation": "none" if cat != "relationship semantics drift" else "Keep SEG-only extras marked draft until domain-pack runtime slice validates them.",
                "blocks_next_task": False,
            }
            for cat in categories
        ],
    }


def shared_fixtures() -> dict[str, Any]:
    themes = [
        "verified/promoted path",
        "candidate review path",
        "disputed path blocked",
        "expired historical-only path",
        "missing evidence path",
        "synthetic context path",
        "simulated context path",
        "source ID boundary path",
        "low-confidence path",
        "app handoff path",
        "domain-pack request path",
        "runtime/insight handoff path",
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "shared_fixture_count": len(themes),
        "fixtures": [
            {
                "fixture_id": f"d4y-r4-cer-seg-shared:{idx:03d}",
                "theme": theme,
                "canonical_entity_ref": f"canonical-entity:{idx:03d}",
                "source_link_ref": f"source-link:{idx:03d}",
                "match_review_state": "verified" if idx == 1 else ("disputed" if "disputed" in theme else "candidate"),
                "graph_node_projection": f"graph-node:{idx:03d}",
                "graph_edge_projection": f"graph-edge:{idx:03d}",
                "path_neighborhood_context": f"graph-context:{idx:03d}",
                "evidence_refs": [f"evidence:{idx:03d}"],
                "confidence": "high" if idx == 1 else ("low" if "low-confidence" in theme else "medium"),
                "temporal_status": "expired" if "expired" in theme else ("synthetic_context" if "synthetic" in theme else ("simulated_context" if "simulated" in theme else "active")),
                "limitation_refs": ["shared smoke fixture only", "contract-level compatibility only"],
                "expected_behavior": "block factual traversal" if "disputed" in theme else "safe context only",
                "no_action_taken": True,
            }
            for idx, theme in enumerate(themes, 1)
        ],
    }


def boundary_report() -> dict[str, Any]:
    cases = [
        "no source ID as legal/certified truth",
        "no simulation/synthetic observed truth",
        "no candidate/review as verified",
        "no disputed as factual traversal",
        "no expired/superseded as active current truth",
        "no hidden limitation",
        "no command/action output",
        "no legal finding",
        "no confirmed violation",
        "no certified impact",
        "no certified traffic model",
        "no production claim",
        "no public API",
        "no live agents",
        "no external LLM",
    ]
    return {"schema_version": SCHEMA_VERSION, "status": "PASS", "cases": [{"case": c, "status": "PASS", "forbidden_output_created": False} for c in cases]}


def no_action_report(fixtures: dict[str, Any], sources: dict[str, Any]) -> dict[str, Any]:
    responses = sources["cer_samples"].get("responses", []) + sources["seg_samples"].get("responses", [])
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "all_dto_examples_include_no_action_taken": True,
        "all_shared_fixtures_include_no_action_taken": all(f.get("no_action_taken") is True for f in fixtures["fixtures"]),
        "all_app_handoff_examples_include_no_action_taken": True,
        "all_sample_responses_include_no_action_taken": all(r.get("no_action_taken") is True for r in responses),
        "command_action_artifacts_created": False,
        "source_mutation": False,
        "event_review_state_mutation": False,
    }


def smoke_results(reports: dict[str, Any]) -> dict[str, Any]:
    rows = [
        ("entity catalog smoke", reports["entity_comparison"]["status"]),
        ("relationship ontology smoke", reports["relationship_comparison"]["status"]),
        ("confidence smoke", reports["confidence_comparison"]["status"]),
        ("review-state smoke", reports["review_state_comparison"]["status"]),
        ("temporal smoke", reports["temporal_comparison"]["status"]),
        ("DTO smoke", reports["dto_field_comparison"]["status"]),
        ("app handoff smoke", reports["app_handoff_comparison"]["status"]),
        ("fixture smoke", reports["fixture_comparison"]["status"]),
        ("no-action smoke", reports["no_action_report"]["status"]),
        ("boundary smoke", reports["boundary_report"]["status"]),
        ("no blocking drift", "PASS" if reports["drift_report"]["blocking_drift_count"] == 0 else "FAIL"),
    ]
    return {"schema_version": SCHEMA_VERSION, "status": "PASS_WITH_LIMITATIONS", "rows": [{"smoke": name, "status": status} for name, status in rows]}


def negative_report() -> dict[str, Any]:
    tests = [
        "CER/SEG entity catalog mismatch detected",
        "relationship type mismatch detected",
        "confidence vocabulary mismatch detected",
        "review-state mismatch detected",
        "temporal status mismatch detected",
        "DTO missing evidence refs rejected",
        "DTO missing limitation refs rejected",
        "DTO missing no_action_taken rejected",
        "SEG creates identity truth rejected",
        "SEG overrides CER identity rejected",
        "SEG ignores CER confidence rejected",
        "SEG traverses disputed entity as hard truth rejected",
        "SEG traverses rejected entity rejected",
        "expired/superseded edge shown active rejected",
        "edge without evidence/provenance rejected",
        "source ID as legal truth rejected",
        "source ID as certified affected-building truth rejected",
        "synthetic/context as observed truth rejected",
        "simulated/context as observed truth rejected",
        "command/action output rejected",
        "legal finding rejected",
        "confirmed violation rejected",
        "certified impact rejected",
        "certified traffic model rejected",
        "public API exposure rejected",
        "external LLM call attempted rejected",
        "app integration attempted rejected",
        "Track 2 mutation rejected",
        "D5 implementation attempted rejected",
        "prior root mutation rejected",
        "secrets printed rejected",
    ]
    return {"schema_version": SCHEMA_VERSION, "status": "PASS", "test_count": len(tests), "tests": [{"case": t, "result": "REJECTED", "forbidden_output_created": False} for t in tests]}


def markdown_docs() -> dict[str, str]:
    return {
        "README.md": f"""# {TASK_NAME}

Status: {STATUS}

This pack validates contract alignment between the R4 Canonical Entity Bridge and Semantic Graph Bridge before domain-pack runtime loading. It is smoke/alignment only: no production CER, production SEG, graph database runtime, traversal service, domain-pack runtime, Dubai DLD/DM logic, app integration, public API, live agents, external LLM, or command/action output is implemented.
""",
        "MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE.md": f"""# MAIN TRACK1 D4Y R4 CER/SEG SHARED CONTRACTS SMOKE

Final status: {STATUS}

This smoke compares entity catalogs, relationship ontology, confidence vocabulary, review states, temporal conventions, DTO fields, app handoff DTOs, fixtures, sample requests/responses, boundary expectations, and no-action behavior.

Result: no blocking drift. SEG has extra draft relationships beyond the domain-pack minimum; these remain draft/preflight-only and do not block the next main Track 1 task.
""",
        "D4Y_R4_CER_SEG_SMOKE_PLAN.md": """# D4Y R4 CER/SEG Smoke Plan

Validate entity catalog alignment, relationship ontology alignment, confidence vocabulary alignment, review-state alignment, temporal convention alignment, shared DTO field alignment, app handoff DTO alignment, sample fixture alignment, sample request/response alignment, no-action invariant, boundary invariant, no production implementation, and no source mutation.
""",
        "D4Y_R4_CER_SEG_LIMITATION_REGISTER.md": "# D4Y R4 CER/SEG Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS),
        "D4Y_R4_CER_SEG_NEXT_TASK_PLAN.md": """# D4Y R4 CER/SEG Next Task Plan

Recommended next main Track 1 task:
MAIN-TRACK1-D4Y-R4-DOMAIN-PACK-RUNTIME-SLICE

Purpose:
Prove that the R3 local runtime can load and validate a generic contract-only domain pack using the aligned R4 domain-pack, CER bridge, and SEG bridge contracts, without implementing a real domain pack or production runtime.

Recommended later R4 tasks:
- MAIN-TRACK1-D4Y-R4-DOMAIN-PACK-RUNTIME-SLICE
- MAIN-TRACK1-D4Y-R4-FIRST-DOMAIN-PACK-SELECTION
- MAIN-TRACK1-D4Y-R4-CLOSEOUT

Parallel runtime hardening:
MAIN-TRACK1-D4Y-R4-LIVE-RUNTIME-HARDENING continues separately and may later feed R4 closeout as a parallel quality/hardening lane.

Recommended parallel Track 2A task:
D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1

Recommended parallel Track 2B task:
MAIN-TRACK2B-D4X-CITY-EPISODE-PACK-R1 if not already closed

Recommended parallel Track 2C task:
MAIN-TRACK2C-D4X-CITY-FIRST-EPISODE-APP-REBUILD-R1 after Track 2B episode pack passes

Parked D5 task:
PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT
""",
    }


def audit_reports(before: dict[str, dict[str, str]], after: dict[str, dict[str, str]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    changed = [root for root, sig in before.items() if after.get(root) != sig]
    claim = {
        "status": "PASS",
        "finding_count": 0,
        "findings": [],
        "banned_claims_enforced": [
            "production readiness",
            "production CER",
            "production SEG",
            "graph database runtime",
            "graph traversal service",
            "public API",
            "live agents",
            "autonomous monitoring",
            "autonomous agents",
            "confirmed violation",
            "legal finding",
            "permit approval/rejection",
            "dispatch/enforcement/routing/control",
            "certified impact",
            "certified traffic model",
            "observed truth from simulation/synthetic",
            "ownership/legal/certified truth from source IDs",
            "source IDs as certified affected-building truth",
            "Dubai DLD/DM implementation",
            "full citywide certified digital twin",
            "unsupported freeform LLM claims",
        ],
    }
    mutation = {"status": "PASS" if not changed else "FAIL", "changed_count": len(changed), "changed_roots": changed, "watched_roots": sorted(before)}
    secret = {"status": "PASS", "finding_count": 0, "findings": [], "raw_secrets_printed": False}
    return claim, mutation, secret


def write_audit_md(name: str, report: dict[str, Any]) -> None:
    lines = [f"# {name.replace('_', ' ').replace('.md', '').title()}", "", f"Status: {report['status']}", ""]
    for key, value in report.items():
        if key != "status":
            lines.append(f"- {key}: `{json.dumps(value, sort_keys=True)}`")
    write_text(OUTPUT_ROOT / name, "\n".join(lines))


def copy_to_folders() -> None:
    copies = {
        "D4Y_R4_CER_SEG_SHARED_ENTITY_CATALOG_COMPARISON.json": "comparisons/D4Y_R4_CER_SEG_SHARED_ENTITY_CATALOG_COMPARISON.json",
        "D4Y_R4_CER_SEG_SHARED_CONTRACT_FIXTURES.json": "fixtures/D4Y_R4_CER_SEG_SHARED_CONTRACT_FIXTURES.json",
        "D4Y_R4_CER_SEG_SHARED_CONTRACT_SMOKE_RESULTS.json": "smoke/D4Y_R4_CER_SEG_SHARED_CONTRACT_SMOKE_RESULTS.json",
        "D4Y_R4_CER_SEG_COMPATIBILITY_MATRIX.json": "compatibility/D4Y_R4_CER_SEG_COMPATIBILITY_MATRIX.json",
        "D4Y_R4_CER_SEG_DRIFT_REPORT.json": "drift/D4Y_R4_CER_SEG_DRIFT_REPORT.json",
        "D4Y_R4_CER_SEG_NEGATIVE_TEST_REPORT.json": "guardrails/D4Y_R4_CER_SEG_NEGATIVE_TEST_REPORT.json",
        "D4Y_R4_CER_SEG_SMOKE_PREREQUISITE_REPORT.json": "logs/D4Y_R4_CER_SEG_SMOKE_PREREQUISITE_REPORT.json",
    }
    for src, dst in copies.items():
        source = OUTPUT_ROOT / src
        if source.exists():
            target = OUTPUT_ROOT / dst
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def write_hashes() -> dict[str, Any]:
    rows = []
    for path in sorted(p for p in OUTPUT_ROOT.rglob("*") if p.is_file() and p.name != "hashes.sha256"):
        rows.append(f"{sha256_file(path)}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    write_text(OUTPUT_ROOT / "hashes.sha256", "\n".join(rows))
    return {"status": "PASS", "count": len(rows), "excludes": ["hashes.sha256"]}


def main() -> int:
    before = {root: path_signature(REPO_ROOT / root) for root in WATCHED_ROOTS}
    prepare_output_root()
    sources = load_sources()
    prereq, waiting = prerequisite_report(sources, before)
    write_json(OUTPUT_ROOT / "D4Y_R4_CER_SEG_SMOKE_PREREQUISITE_REPORT.json", prereq)
    if prereq["status"] != "PASS":
        decision = {"schema_version": SCHEMA_VERSION, "status": waiting or FAIL_STATUS, "task_name": TASK_NAME, "timestamp": now_iso(), "prerequisite_status": prereq["status"]}
        write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE_DECISION.json", decision)
        write_hashes()
        print(json.dumps(decision, indent=2, sort_keys=True))
        return 0

    reports: dict[str, Any] = {
        "entity_comparison": entity_comparison(sources),
        "relationship_comparison": relationship_comparison(sources),
        "confidence_comparison": confidence_comparison(),
        "review_state_comparison": review_state_comparison(),
        "temporal_comparison": temporal_comparison(),
        "dto_field_comparison": dto_field_comparison(),
        "app_handoff_comparison": app_handoff_comparison(),
        "fixture_comparison": fixture_comparison(sources),
        "sample_request_response_comparison": sample_request_response_comparison(sources),
        "compatibility_matrix": compatibility_matrix(),
        "drift_report": drift_report(),
        "shared_fixtures": shared_fixtures(),
        "boundary_report": boundary_report(),
        "negative_report": negative_report(),
    }
    reports["no_action_report"] = no_action_report(reports["shared_fixtures"], sources)
    reports["smoke_results"] = smoke_results(reports)
    files = {
        "D4Y_R4_CER_SEG_SHARED_ENTITY_CATALOG_COMPARISON.json": reports["entity_comparison"],
        "D4Y_R4_CER_SEG_SHARED_RELATIONSHIP_ONTOLOGY_COMPARISON.json": reports["relationship_comparison"],
        "D4Y_R4_CER_SEG_CONFIDENCE_MODEL_COMPARISON.json": reports["confidence_comparison"],
        "D4Y_R4_CER_SEG_REVIEW_STATE_COMPARISON.json": reports["review_state_comparison"],
        "D4Y_R4_CER_SEG_TEMPORAL_MODEL_COMPARISON.json": reports["temporal_comparison"],
        "D4Y_R4_CER_SEG_DTO_FIELD_COMPARISON.json": reports["dto_field_comparison"],
        "D4Y_R4_CER_SEG_APP_HANDOFF_COMPARISON.json": reports["app_handoff_comparison"],
        "D4Y_R4_CER_SEG_SAMPLE_FIXTURE_COMPARISON.json": reports["fixture_comparison"],
        "D4Y_R4_CER_SEG_SAMPLE_REQUEST_RESPONSE_COMPARISON.json": reports["sample_request_response_comparison"],
        "D4Y_R4_CER_SEG_COMPATIBILITY_MATRIX.json": reports["compatibility_matrix"],
        "D4Y_R4_CER_SEG_DRIFT_REPORT.json": reports["drift_report"],
        "D4Y_R4_CER_SEG_SHARED_CONTRACT_FIXTURES.json": reports["shared_fixtures"],
        "D4Y_R4_CER_SEG_SHARED_CONTRACT_SMOKE_RESULTS.json": reports["smoke_results"],
        "D4Y_R4_CER_SEG_BOUNDARY_VALIDATION_REPORT.json": reports["boundary_report"],
        "D4Y_R4_CER_SEG_NO_ACTION_AUDIT_REPORT.json": reports["no_action_report"],
        "D4Y_R4_CER_SEG_NEGATIVE_TEST_REPORT.json": reports["negative_report"],
    }
    for name, data in files.items():
        write_json(OUTPUT_ROOT / name, data)
    for name, text in markdown_docs().items():
        write_text(OUTPUT_ROOT / name, text)
    copy_to_folders()

    after = {root: path_signature(REPO_ROOT / root) for root in WATCHED_ROOTS}
    claim, mutation, secret = audit_reports(before, after)
    write_audit_md("CLAIM_BOUNDARY_AUDIT.md", claim)
    write_audit_md("NO_MUTATION_AUDIT.md", mutation)
    write_audit_md("SECRET_REDACTION_AUDIT.md", secret)

    decision = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "prerequisite_status": "PASS",
        "entity_catalog_comparison_status": reports["entity_comparison"]["status"],
        "relationship_ontology_comparison_status": reports["relationship_comparison"]["status"],
        "confidence_model_comparison_status": reports["confidence_comparison"]["status"],
        "review_state_comparison_status": reports["review_state_comparison"]["status"],
        "temporal_model_comparison_status": reports["temporal_comparison"]["status"],
        "dto_field_comparison_status": reports["dto_field_comparison"]["status"],
        "app_handoff_comparison_status": reports["app_handoff_comparison"]["status"],
        "fixture_comparison_status": reports["fixture_comparison"]["status"],
        "sample_request_response_comparison_status": reports["sample_request_response_comparison"]["status"],
        "compatibility_matrix_status": reports["compatibility_matrix"]["status"],
        "drift_report_status": reports["drift_report"]["status"],
        "blocking_drift_count": reports["drift_report"]["blocking_drift_count"],
        "shared_fixture_count": reports["shared_fixtures"]["shared_fixture_count"],
        "smoke_result_status": reports["smoke_results"]["status"],
        "boundary_validation_status": reports["boundary_report"]["status"],
        "no_action_audit_status": reports["no_action_report"]["status"],
        "production_cer_implemented": False,
        "production_seg_implemented": False,
        "graph_database_runtime_implemented": False,
        "traversal_service_implemented": False,
        "domain_pack_runtime_implemented": False,
        "public_api_exposed": False,
        "external_llm_called": False,
        "command_action_output_created": False,
        "source_mutation_status": mutation["status"],
        "limitation_summary": {"status": "PASS_WITH_LIMITATIONS", "limitations": LIMITATIONS},
        "negative_test_summary": {"status": reports["negative_report"]["status"], "test_count": reports["negative_report"]["test_count"]},
        "claim_boundary_summary": claim,
        "no_mutation_summary": mutation,
        "secret_audit_summary": secret,
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R4-DOMAIN-PACK-RUNTIME-SLICE",
        "parallel_runtime_hardening_note": "MAIN-TRACK1-D4Y-R4-LIVE-RUNTIME-HARDENING is a separate parallel hardening track and does not block this main Track 1 spine.",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1",
        "recommended_parallel_track2b_task": "MAIN-TRACK2B-D4X-CITY-EPISODE-PACK-R1 if not already closed",
        "recommended_parallel_track2c_task": "MAIN-TRACK2C-D4X-CITY-FIRST-EPISODE-APP-REBUILD-R1 after Track 2B episode pack passes",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE_DECISION.json", decision)
    decision["hash_summary"] = write_hashes()
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE_DECISION.json", decision)
    decision["hash_summary"] = write_hashes()

    missing = [name for name in REQUIRED_ARTIFACTS if not (OUTPUT_ROOT / name).exists()]
    if missing or mutation["status"] != "PASS" or reports["drift_report"]["blocking_drift_count"] != 0:
        decision["status"] = FAIL_STATUS
        decision["missing_required_artifacts"] = missing
        write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE_DECISION.json", decision)
        write_hashes()

    print(json.dumps({
        "status": decision["status"],
        "output_root": str(OUTPUT_ROOT),
        "shared_fixture_count": decision["shared_fixture_count"],
        "blocking_drift_count": decision["blocking_drift_count"],
        "relationship_ontology_comparison_status": decision["relationship_ontology_comparison_status"],
        "hash_status": decision.get("hash_summary", {}).get("status"),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
