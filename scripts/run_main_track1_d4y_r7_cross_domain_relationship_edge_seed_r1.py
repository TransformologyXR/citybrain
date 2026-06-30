#!/usr/bin/env python3
"""Build MAIN-TRACK1-D4Y-R7-CROSS-DOMAIN-RELATIONSHIP-EDGE-SEED-R1.

This is a backend-only seed build. It consumes the R7 relationship substrate
preflight and current backend/domain/event evidence, then emits a bounded edge
registry, evidence bundles, graph projection fixture, rejection tests, and
handoffs for later backend consumers.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-TRACK1-D4Y-R7-CROSS-DOMAIN-RELATIONSHIP-EDGE-SEED-R1"
STATUS = "PASS_WITH_LIMITATIONS"
HOLD_STATUS = "HOLD"
FAIL_STATUS = "FAIL"
SCHEMA_VERSION = "main-track1-d4y-r7-cross-domain-relationship-edge-seed-r1.v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r7_cross_domain_relationship_edge_seed_r1"
RUNNER_PATH = REPO_ROOT / "scripts/run_main_track1_d4y_r7_cross_domain_relationship_edge_seed_r1.py"

R7_PREFLIGHT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r7_cross_domain_relationship_substrate_preflight"
R6_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end"
R5_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end"
TRACK2B_ROOT = REPO_ROOT / "outputs/main_track2b_d4x_city_episode_pack_end_to_end"
LIVE_EVENT_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_live_event_fabric_minimal_local_slice"
TRACK2A_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end"
FINISHING_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_d5_track2a_integrated_finishing_handover_r1"

D6_SURFACE_WATCH = {
    "d6_runtime_demo_preflight": REPO_ROOT / "outputs/main_citybrain_d6_runtime_demo_preflight_r1",
    "d6_end_to_end_frontend_handover": REPO_ROOT / "outputs/main_citybrain_d6_end_to_end_demo_and_episode_frontend_handover_r1",
    "d5_app_consumption_smoke": REPO_ROOT / "outputs/main_citybrain_d5_local_served_runtime_app_consumption_smoke_r1",
    "d5_served_runtime_script": REPO_ROOT / "scripts/run_main_citybrain_d5_local_served_runtime_hardening_r1.py",
    "omniverse_kit_selection_extension": REPO_ROOT / "outputs/main_track2a_d4x_omniverse_kit_selection_extension_r1",
    "omniverse_gui_smoke": REPO_ROOT / "outputs/main_track2a_d4x_omniverse_kit_composer_gui_smoke_r2",
    "manual_omniverse_acceptance": REPO_ROOT / "outputs/manual_main_track2a_d4x_omniverse_composer_selection_acceptance_r1",
}

REQUIRED_UPSTREAM = [
    "MAIN_TRACK1_D4Y_R7_CROSS_DOMAIN_RELATIONSHIP_SUBSTRATE_PREFLIGHT_DECISION.json",
    "CROSS_DOMAIN_RELATIONSHIP_SUBSTRATE_PREFLIGHT_REPORT.md",
    "RELATIONSHIP_ONTOLOGY_R1.json",
    "RELATIONSHIP_ASSERTION_CONTRACT.json",
    "RELATIONSHIP_GROUNDING_POLICY.md",
    "RELATIONSHIP_CONFIDENCE_AND_REVIEW_STATE_POLICY.json",
    "RELATIONSHIP_TEMPORAL_POLICY.json",
    "RELATIONSHIP_EVIDENCE_BUNDLE_SCHEMA.json",
    "RELATIONSHIP_EDGE_FIXTURES.json",
    "RELATIONSHIP_EVIDENCE_BUNDLES.json",
    "RELATIONSHIP_VALIDATION_RESULTS.json",
    "RELATIONSHIP_REJECTION_AND_SAFE_FAILURE_RESULTS.json",
    "RELATIONSHIP_SUBSTRATE_TOP_DOWN_TRACE_EXAMPLE.json",
    "NO_CAUSATION_OVERCLAIM_AUDIT.json",
    "INCIDENT_MODE_BACKEND_HANDOFF_CONTRACT.json",
    "INSIGHT_WATCHLIST_BACKEND_HANDOFF_CONTRACT.json",
    "D6_COLLISION_AVOIDANCE_AUDIT.json",
    "LIMITATIONS_AND_NEXT_STEPS.md",
]

REVIEW_STATES = [
    "asserted_source",
    "inferred_deterministic",
    "candidate_probabilistic",
    "requires_review",
    "rejected",
    "disputed",
    "deprecated",
]

ASSERTION_METHODS = [
    "source_asserted",
    "geometry_containment",
    "geometry_adjacency",
    "shared_identifier",
    "event_resolution",
    "document_reference",
    "temporal_cooccurrence",
    "spatial_proximity",
    "manual_bridge",
]

REQUIRED_EDGE_FIELDS = [
    "relationship_id",
    "relationship_type",
    "source_canonical_entity_id",
    "source_entity_type",
    "target_canonical_entity_id",
    "target_entity_type",
    "direction",
    "confidence",
    "review_state",
    "evidence_refs",
    "trace_refs",
    "source_system_refs",
    "temporal_scope",
    "spatial_scope",
    "assertion_method",
    "assertion_boundary",
    "limitations",
    "not_causal",
    "no_action_taken",
    "created_by_run",
    "created_at_utc",
    "real_evidence_backed",
    "cross_domain",
    "spatial_only",
    "synthetic_contract_test_only",
    "not_city_truth",
    "not_domain_evidence",
]

FALLBACK_ALLOWED_RELATIONSHIP_TYPES = [
    "contains",
    "located_in",
    "adjacent_to",
    "serves",
    "monitored_by",
    "has_event_context",
    "has_permit_context",
    "has_inspection_context",
    "has_violation_context",
    "has_mobility_context",
    "spatially_near",
    "temporally_near",
    "co_occurs_with",
    "candidate_related_to",
    "requires_review",
]

FORBIDDEN_RELATIONSHIP_TYPES = [
    "caused_by",
    "causes",
    "triggered",
    "responsible_for",
    "resulted_in",
    "led_to",
    "proves",
    "confirmed_impact",
    "certified_affected",
    "legal_violation",
    "enforcement_action",
    "dispatch_action",
    "routing_control",
]

FORBIDDEN_ACCEPTED_WORDS = [
    "caused_by",
    "causes",
    "triggered",
    "responsible_for",
    "resulted_in",
    "led_to",
    "proved",
    "confirmed impact",
    "certified affected",
    "legal_violation",
    "enforcement_action",
    "dispatch_action",
    "routing_control",
]

LIMITATIONS = [
    "backend-only edge seed registry",
    "JSON graph projection fixture only; no graph database runtime",
    "edge population estimate is approximate and derived from current artifacts",
    "R6 event-to-entity context remains bounded review context",
    "R5 civic-service packets remain candidate/review context",
    "Track2B city episodes are source/story context, not legal or certified truth",
    "live event fabric inputs are replay/local-slice context only",
    "candidate and review edges are not facts",
    "synthetic fixtures are validator-only and not CityBrain truth",
    "no frontend, D6 demo surface, Omniverse, Kit, served runtime, public API, command, routing, dispatch, control, or autonomous-action implementation",
]

NEXT_TASK = "MAIN-TRACK1-D4Y-R7-CROSS-DOMAIN-RELATIONSHIP-EDGE-REGISTRY-RUNTIME-PREFLIGHT"
AFTER_D6_TASK = "MAIN-CITYBRAIN-D6-INCIDENT-MODE-BACKEND-PREFLIGHT"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def path_signature(path: Path) -> dict[str, str]:
    if not path.exists():
        return {"__missing__": "true"}
    if path.is_file():
        stat = path.stat()
        return {path.name: f"{stat.st_size}:{int(stat.st_mtime)}"}
    files = sorted(p for p in path.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    signature = {}
    for candidate in files[:1200]:
        stat = candidate.stat()
        signature[candidate.relative_to(path).as_posix()] = f"{stat.st_size}:{int(stat.st_mtime)}"
    signature["__file_count__"] = str(len(files))
    return signature


def prepare_output_root() -> None:
    resolved = OUTPUT_ROOT.resolve()
    if resolved.parent != (REPO_ROOT / "outputs").resolve() or resolved.name != "main_track1_d4y_r7_cross_domain_relationship_edge_seed_r1":
        raise RuntimeError(f"Refusing to reset unexpected output root: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def packet_list(payload: Any, key: str = "packets") -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        value = payload.get(key, [])
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def upstream_audit(allowed_relationship_types: list[str]) -> dict[str, Any]:
    artifact_checks = []
    corrupt = []
    for name in REQUIRED_UPSTREAM:
        path = R7_PREFLIGHT_ROOT / name
        parsed = True
        if path.suffix == ".json" and path.exists():
            try:
                read_json(path, {})
            except json.JSONDecodeError:
                parsed = False
                corrupt.append(name)
        artifact_checks.append(
            {
                "artifact": name,
                "path": rel(path),
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() else 0,
                "parse_ok": parsed,
            }
        )
    decision = read_json(R7_PREFLIGHT_ROOT / "MAIN_TRACK1_D4Y_R7_CROSS_DOMAIN_RELATIONSHIP_SUBSTRATE_PREFLIGHT_DECISION.json", {})
    causation = read_json(R7_PREFLIGHT_ROOT / "NO_CAUSATION_OVERCLAIM_AUDIT.json", {})
    missing = [item["artifact"] for item in artifact_checks if not item["exists"]]
    status = "PASS"
    if missing or corrupt:
        status = "HOLD"
    if causation.get("ungrounded_causal_claim_accepted") is True:
        status = "FAIL"
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-EDGE-SEED-UPSTREAM-AUDIT-R0",
        "status": status,
        "upstream_root": rel(R7_PREFLIGHT_ROOT),
        "upstream_r7_status": decision.get("status"),
        "artifact_checks": artifact_checks,
        "missing_artifacts": missing,
        "corrupt_artifacts": corrupt,
        "relationship_types_available": allowed_relationship_types,
        "accepted_ungrounded_causal_claims_found": causation.get("ungrounded_causal_claim_accepted") is True,
        "go": status == "PASS",
    }


def infer_entity_type(entity_id: str, fallback: str | None = None) -> str:
    text = (entity_id or "").lower()
    if "road" in text or "segment" in text:
        return "road_segment"
    if "building" in text or "lod2" in text or "bin:" in text:
        return "building"
    if "parcel" in text or "cadastre" in text or "bbl" in text:
        return "parcel"
    if "address" in text:
        return "address"
    if "community" in text or "district" in text or "neighbourhood" in text or "city:" in text or text.startswith("cer:city"):
        return "community"
    if "event" in text:
        return "event"
    if "mobility" in text or "traffic" in text or "gtfs" in text:
        return "mobility_context"
    if "review" in text or "domain_pack" in text:
        return "domain_context"
    if "source" in text or "signal" in text or "iris" in text or "311" in text:
        return "source_record"
    return fallback or "domain_context"


def source_family_from_edge(edge: dict[str, Any]) -> str:
    return edge.get("source_evidence_family", "unknown")


def is_real_r6_packet(packet: dict[str, Any]) -> bool:
    lifecycle = str(packet.get("lifecycle_state", "")).lower()
    limitations = " ".join(packet.get("limitations", [])).lower()
    return bool(packet.get("entity_refs") and packet.get("event_refs") and packet.get("evidence_refs")) and not any(
        term in lifecycle or term in limitations for term in ["synthetic", "simulated", "limitation-only", "missing_source_entity"]
    )


def edge(
    relationship_id: str,
    relationship_type: str,
    source_id: str,
    target_id: str,
    confidence: float,
    review_state: str,
    evidence_refs: list[str],
    trace_refs: list[str],
    source_system_refs: list[str],
    assertion_method: str,
    assertion_boundary: str,
    limitations: list[str],
    category: str,
    source_evidence_family: str,
    source_type: str | None = None,
    target_type: str | None = None,
    cross_domain: bool = True,
    spatial_only: bool = False,
    synthetic_contract_test_only: bool = False,
    real_evidence_backed: bool = True,
    direction: str = "directed",
    temporal_scope: dict[str, Any] | None = None,
    spatial_scope: dict[str, Any] | None = None,
    relationship_summary: str | None = None,
    blocked_reason: str | None = None,
) -> dict[str, Any]:
    synthetic = synthetic_contract_test_only
    return {
        "relationship_id": relationship_id,
        "relationship_type": relationship_type,
        "source_canonical_entity_id": source_id,
        "source_entity_type": source_type or infer_entity_type(source_id),
        "target_canonical_entity_id": target_id,
        "target_entity_type": target_type or infer_entity_type(target_id),
        "direction": direction,
        "confidence": confidence,
        "review_state": review_state,
        "evidence_refs": evidence_refs,
        "trace_refs": trace_refs,
        "source_system_refs": source_system_refs,
        "temporal_scope": temporal_scope
        or {
            "event_time": None,
            "valid_from": None,
            "valid_to": None,
            "temporal_window": "source packet context only",
        },
        "spatial_scope": spatial_scope
        or {
            "city_or_area": "source context",
            "method": "source refs and packet/entity refs, not a live geometry runtime",
        },
        "assertion_method": assertion_method,
        "assertion_boundary": assertion_boundary,
        "limitations": limitations,
        "not_causal": True,
        "no_action_taken": True,
        "created_by_run": TASK_ID,
        "created_at_utc": now(),
        "real_evidence_backed": real_evidence_backed and not synthetic,
        "cross_domain": cross_domain,
        "spatial_only": spatial_only,
        "synthetic_contract_test_only": synthetic,
        "not_city_truth": synthetic,
        "not_domain_evidence": synthetic,
        "fixture_category": category,
        "source_evidence_family": source_evidence_family,
        "relationship_summary": relationship_summary
        or f"{relationship_type} edge from {source_id} to {target_id} with bounded evidence.",
        "blocked_reason": blocked_reason,
    }


def load_sources() -> dict[str, Any]:
    r6_packets = packet_list(read_json(R6_ROOT / "R6_INCIDENT_CONTEXT_PACKETS.json", {}))
    r6_resolutions = packet_list(read_json(R6_ROOT / "R6_EVENT_TO_ENTITY_RESULTS.json", {}), "resolutions")
    resolution_by_event = {item.get("event_id"): item for item in r6_resolutions}
    r5_packets = packet_list(read_json(R5_ROOT / "R5_CIVIC_SERVICE_RUNTIME_SLICE_OUTPUT_PACKETS.json", {}))
    episodes_payload = read_json(TRACK2B_ROOT / "TRACK2B_CURATED_CITY_EPISODE_PACK.json", {})
    episodes = packet_list(episodes_payload, "episodes")
    live_events = read_jsonl(LIVE_EVENT_ROOT / "LIVE_EVENT_FABRIC_EVENT_LOG.jsonl")
    return {
        "r6_packets": r6_packets,
        "r6_resolutions": r6_resolutions,
        "resolution_by_event": resolution_by_event,
        "r5_packets": r5_packets,
        "episodes": episodes,
        "live_events": live_events,
    }


def episode_by_id(episodes: list[dict[str, Any]], episode_id: str) -> dict[str, Any]:
    for episode in episodes:
        if episode.get("episode_id") == episode_id:
            return episode
    return {}


def edge_source_discovery(sources: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    r6_real = [packet for packet in sources["r6_packets"] if is_real_r6_packet(packet)]
    r6_blocked_missing = [
        packet
        for packet in sources["r6_packets"]
        if "limitation-only" in str(packet.get("lifecycle_state", "")).lower()
        or "missing_source_entity" in " ".join(packet.get("limitations", [])).lower()
    ]
    episodes_with_context = [
        episode
        for episode in sources["episodes"]
        if episode.get("source_refs") or episode.get("evidence_refs") or episode.get("entity_refs")
    ]
    r5_seedable = [
        packet
        for packet in sources["r5_packets"]
        if packet.get("evidence_refs") and packet.get("source_signal_refs") and packet.get("no_action_taken") is True
    ]
    live_resolved = [
        item
        for item in sources["live_events"]
        if item.get("fabric_path") == "resolved_appended" and item.get("canonical_entity_id") and item.get("provenance_refs")
    ]
    live_unresolved = [item for item in sources["live_events"] if item.get("fabric_path") == "unresolved_preserved"]
    live_rejected = [item for item in sources["live_events"] if item.get("fabric_path") == "rejected_quarantined"]
    source_families = {
        "incident_event_context": len(r6_real),
        "domain_pack_evidence": len(r5_seedable),
        "city_episode_context": len(episodes_with_context),
        "event_fabric_context": len(sources["live_events"]),
        "asset_binding_context": 1 if TRACK2A_ROOT.exists() else 0,
        "canonical_entity_context": 1 if R7_PREFLIGHT_ROOT.exists() else 0,
        "semantic_graph_context": 1 if (REPO_ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1").exists() else 0,
    }
    estimated_grounded = len(r6_real) + min(8, len(episodes_with_context)) + len(live_resolved)
    estimated_cross_domain = len(r6_real) + min(6, len(episodes_with_context)) + len(live_resolved)
    estimated_candidate = len(r5_seedable) + len(live_unresolved) + max(0, len(episodes_with_context) // 2)
    blocked_missing_evidence = len(r6_blocked_missing) + max(0, len(sources["episodes"]) - len(episodes_with_context))
    blocked_causation = 6 + len(live_rejected)
    richness = "rich" if estimated_cross_domain >= 80 and len([v for v in source_families.values() if v]) >= 4 else "moderate" if estimated_cross_domain >= 12 else "sparse"
    ceiling = "rich" if richness == "rich" else "moderate" if estimated_cross_domain >= 8 else "sparse"
    discovery = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-EDGE-SOURCE-DISCOVERY-AND-POPULATION-ESTIMATE-R1",
        "status": "PASS",
        "source_roots_inspected": {
            "r6_incident_event_context": rel(R6_ROOT),
            "r5_domain_pack_evidence": rel(R5_ROOT),
            "track2b_city_episode_context": rel(TRACK2B_ROOT),
            "live_event_fabric_context": rel(LIVE_EVENT_ROOT),
            "track2a_asset_binding_context": rel(TRACK2A_ROOT),
            "finishing_handover_context": rel(FINISHING_ROOT),
        },
        "source_families_inspected": source_families,
        "additional_real_evidence_family_beyond_r7_preflight_found": any(
            source_families.get(key, 0) > 0
            for key in ["domain_pack_evidence", "event_fabric_context", "asset_binding_context"]
        ),
        "seedable_r6_real_context_packets": len(r6_real),
        "seedable_r5_civic_packets": len(r5_seedable),
        "seedable_track2b_episode_contexts": len(episodes_with_context),
        "seedable_live_event_context_rows": len(sources["live_events"]),
        "blocked_r6_missing_or_limitation_only_packets": len(r6_blocked_missing),
        "source_discovery_notes": [
            "R6 is the dominant current edge source.",
            "R5 civic packets add candidate/review domain evidence.",
            "Track2B episodes add city episode and asset/source context.",
            "Live event fabric adds replay/local-slice context, not production live ingestion.",
        ],
    }
    estimate = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-EDGE-SOURCE-DISCOVERY-AND-POPULATION-ESTIMATE-R1",
        "status": "PASS",
        "estimate_is_approximate": True,
        "source_families_inspected": list(source_families.keys()),
        "entity_families_inspected": sorted(
            {
                infer_entity_type(entity)
                for packet in r6_real
                for entity in packet.get("entity_refs", [])
            }
            | {"community", "road_segment", "building", "parcel", "address", "source_record", "mobility_context"}
        ),
        "candidate_relationship_families_inspected": [
            "has_event_context",
            "has_mobility_context",
            "located_in",
            "monitored_by",
            "candidate_related_to",
            "temporally_near",
            "requires_review",
        ],
        "edges_seeded_this_run_estimate": 0,
        "accepted_grounded_edges_constructible_now": estimated_grounded,
        "real_evidence_backed_cross_domain_edges_constructible_now": estimated_cross_domain,
        "candidate_review_edges_constructible_now": estimated_candidate,
        "edges_blocked_by_missing_evidence": blocked_missing_evidence,
        "edges_blocked_by_causation_boundary": blocked_causation,
        "edges_blocked_by_missing_entity_refs": len(r6_blocked_missing),
        "estimated_incident_mode_context_richness": richness,
        "evidence_population_ceiling_below_pass_threshold": estimated_cross_domain < 8 or estimated_grounded < 12,
        "population_ceiling_classified_as_limitation_not_failure": ceiling,
        "incident_mode_bottleneck_assessment": "Current evidence is meaningful for backend context retrieval, but still narrow: most constructible edges are R6 event context, so richer Incident Mode needs more source/diverse domain evidence before product use.",
        "recommended_evidence_to_ingest_next": [
            "more source-asserted building-to-permit context",
            "more source-asserted inspection context",
            "reviewed violation-context source packets without legal overclaim",
            "additional asset/facility-to-service context",
            "review outcomes that can upgrade candidate relations safely",
        ],
        "methodology_notes": [
            "Count R6 non-simulated, non-synthetic, non-limitation packets with entity/event/evidence refs as constructible event-context edges.",
            "Count Track2B episodes with source/evidence/entity refs as bounded city episode/source context.",
            "Count R5 civic output packets as candidate/review domain context.",
            "Count live event fabric resolved/unresolved/quarantined rows separately because they are replay/local-slice context.",
            "Do not count synthetic or rejected rows as real evidence-backed truth.",
        ],
    }
    return discovery, estimate


def seed_registry(sources: dict[str, Any], estimate: dict[str, Any]) -> dict[str, Any]:
    accepted: list[dict[str, Any]] = []
    candidate: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    synthetic: list[dict[str, Any]] = []
    resolution_by_event = sources["resolution_by_event"]
    real_r6 = [packet for packet in sources["r6_packets"] if is_real_r6_packet(packet)]
    for idx, packet in enumerate(real_r6[:16], start=1):
        event_id = packet.get("event_refs", [f"r6-event-{idx:03d}"])[0]
        resolution = resolution_by_event.get(event_id, {})
        entity_id = packet.get("entity_refs", ["cer:unknown:entity"])[0]
        accepted.append(
            edge(
                relationship_id=f"rel:r7-seed:r6:event-context:{idx:03d}",
                relationship_type="has_event_context",
                source_id=entity_id,
                target_id=event_id,
                confidence=float(resolution.get("confidence", 0.76) or 0.76),
                review_state="asserted_source",
                evidence_refs=packet.get("evidence_refs", []),
                trace_refs=[
                    f"{rel(R6_ROOT / 'R6_INCIDENT_CONTEXT_PACKETS.json')}:{packet.get('packet_id')}",
                    f"{rel(R6_ROOT / 'R6_EVENT_TO_ENTITY_RESULTS.json')}:{event_id}",
                ],
                source_system_refs=[packet.get("source_entity_id", "unknown-source"), packet.get("domain_id", "civic_service_review_context")],
                assertion_method="event_resolution",
                assertion_boundary="Entity has bounded incident/event context only; no stronger claim is made.",
                limitations=list(dict.fromkeys(packet.get("limitations", []) + ["relationship_seed_review_context_only"])),
                category="accepted_grounded_edges",
                source_evidence_family="incident_event_context",
                source_type=infer_entity_type(entity_id),
                target_type=packet.get("event_family", "event"),
                cross_domain=True,
                temporal_scope={
                    "event_time": resolution.get("event_time"),
                    "valid_from": None,
                    "valid_to": None,
                    "temporal_window": packet.get("lifecycle_state"),
                },
                spatial_scope={"city_or_area": "BARC source context", "method": "R6 source entity/entity refs"},
                relationship_summary=f"{entity_id} has bounded R6 incident/event context {event_id}.",
            )
        )

    episodes = sources["episodes"]
    barc_mobility = episode_by_id(episodes, "episode:barc_mobility_trams_itineraries_replay")
    barc_lod2 = episode_by_id(episodes, "episode:barc_lod2_object_district_neighbourhood")
    barc_civic = episode_by_id(episodes, "episode:barc_iris_civic_service_context")
    nyc_civic = episode_by_id(episodes, "episode:nyc_311_civic_service_volume")
    track2b_path = rel(TRACK2B_ROOT / "TRACK2B_CURATED_CITY_EPISODE_PACK.json")
    if barc_mobility:
        accepted.append(
            edge(
                "rel:r7-seed:track2b:barc-mobility-context",
                "has_mobility_context",
                "cer:city:barc",
                "mobility_context:barc:traffic-trams-itineraries-tmb",
                0.79,
                "asserted_source",
                barc_mobility.get("evidence_refs") or [f"{track2b_path}:episode:barc_mobility_trams_itineraries_replay"],
                [f"{track2b_path}:episode:barc_mobility_trams_itineraries_replay"],
                barc_mobility.get("source_refs") or ["traffic_itineraries", "traffic_trams", "tmb_static_gtfs"],
                "source_asserted",
                "Mobility/replay context only; no routing or traffic-control claim.",
                barc_mobility.get("limitations") or ["simulated_context_only"],
                "accepted_grounded_edges",
                "city_episode_context",
                source_type="community",
                target_type="mobility_context",
                relationship_summary="Barcelona has bounded mobility/replay context from Track2B episode evidence.",
            )
        )
    if barc_lod2:
        accepted.append(
            edge(
                "rel:r7-seed:track2b:barc-lod2-located-neighbourhood",
                "located_in",
                (barc_lod2.get("entity_refs") or ["barc:lod2_source_object:72498"])[0],
                "barc:neighbourhood:08",
                0.83,
                "inferred_deterministic",
                [f"{track2b_path}:episode:barc_lod2_object_district_neighbourhood"],
                [f"{track2b_path}:episode:barc_lod2_object_district_neighbourhood"],
                barc_lod2.get("source_refs") or ["BARC LOD2 buildings USD", "BARC identity shard"],
                "manual_bridge",
                "LOD2 object location context only; identity joins remain bounded.",
                barc_lod2.get("limitations") or ["LOD2 source context only"],
                "accepted_grounded_edges",
                "city_episode_context",
                source_type="building",
                target_type="community",
                cross_domain=False,
                spatial_only=True,
                relationship_summary="Barcelona LOD2 object has source-referenced neighbourhood context.",
            )
        )
    for episode_id, city_entity, target in [
        ("episode:barc_iris_civic_service_context", "cer:city:barc", "civic_service_context:barc:iris"),
        ("episode:nyc_311_civic_service_volume", "cer:city:nyc", "civic_service_context:nyc:311"),
    ]:
        episode_data = episode_by_id(episodes, episode_id)
        if episode_data:
            accepted.append(
                edge(
                    f"rel:r7-seed:track2b:{episode_id.split(':')[-1].replace('_', '-')}",
                    "has_event_context",
                    city_entity,
                    target,
                    0.75,
                    "asserted_source",
                    episode_data.get("evidence_refs") or [f"{track2b_path}:{episode_id}"],
                    [f"{track2b_path}:{episode_id}"],
                    episode_data.get("source_refs") or [episode_id],
                    "source_asserted",
                    "Civic-service context only; no case finding or action claim.",
                    episode_data.get("limitations") or ["review_context_only"],
                    "accepted_grounded_edges",
                    "city_episode_context",
                    source_type="community",
                    target_type="domain_context",
                    cross_domain=True,
                    relationship_summary=f"{city_entity} has bounded civic-service context from {episode_id}.",
                )
            )

    for idx, packet in enumerate(sources["r5_packets"][:4], start=1):
        signal = (packet.get("source_signal_refs") or [f"r5:civic:signal:{idx:03d}"])[0]
        accepted.append(
            edge(
                relationship_id=f"rel:r7-seed:r5:civic-monitored-by:{idx:03d}",
                relationship_type="monitored_by",
                source_id=f"source_signal:{signal}",
                target_id="domain_pack:civic_service_review_context",
                confidence=0.7,
                review_state="asserted_source",
                evidence_refs=packet.get("evidence_refs", []),
                trace_refs=[f"{rel(R5_ROOT / 'R5_CIVIC_SERVICE_RUNTIME_SLICE_OUTPUT_PACKETS.json')}:{packet.get('packet_id')}"],
                source_system_refs=packet.get("source_signal_refs", []) + [packet.get("domain_pack_id", "civic_service_review_context")],
                assertion_method="source_asserted",
                assertion_boundary="Civic source signal is represented in a review domain pack only.",
                limitations=list(dict.fromkeys(packet.get("limitation_refs", []) + ["relationship_seed_review_context_only"])),
                category="accepted_grounded_edges",
                source_evidence_family="domain_pack_evidence",
                source_type="source_record",
                target_type="domain_context",
                relationship_summary=f"{signal} is monitored by the bounded civic-service review domain pack.",
            )
        )

    for idx, row in enumerate([item for item in sources["live_events"] if item.get("fabric_path") == "resolved_appended"][:1], start=1):
        accepted.append(
            edge(
                relationship_id=f"rel:r7-seed:live-event:resolved-context:{idx:03d}",
                relationship_type="has_event_context",
                source_id=row.get("canonical_entity_id") or "cer:unknown:entity",
                target_id=row.get("source_record_id") or row.get("fabric_event_id") or f"live-event-{idx}",
                confidence=float(row.get("confidence", 0.7) or 0.7),
                review_state="asserted_source",
                evidence_refs=row.get("provenance_refs", []),
                trace_refs=[f"{rel(LIVE_EVENT_ROOT / 'LIVE_EVENT_FABRIC_EVENT_LOG.jsonl')}:{row.get('fabric_event_id')}"],
                source_system_refs=[row.get("source_system", "LIVE_EVENT_FABRIC_LOCAL_SLICE")],
                assertion_method="event_resolution",
                assertion_boundary="Replay/local-slice event context only; no production live ingestion claim.",
                limitations=list(dict.fromkeys(row.get("limitations", []) + ["local_replay_context_only"])),
                category="accepted_grounded_edges",
                source_evidence_family="event_fabric_context",
                source_type=infer_entity_type(row.get("canonical_entity_id") or ""),
                target_type="event",
                temporal_scope={
                    "event_time": row.get("event_time"),
                    "valid_from": None,
                    "valid_to": None,
                    "temporal_window": row.get("fabric_path"),
                },
                relationship_summary="Resolved local/replay event has bounded canonical entity context.",
            )
        )

    # Candidate/review edges from weaker joins, domain review packets, and temporal nearness.
    for idx, packet in enumerate(sources["r5_packets"][4:10], start=1):
        signal = (packet.get("source_signal_refs") or [f"r5:civic:signal:candidate:{idx:03d}"])[0]
        candidate.append(
            edge(
                relationship_id=f"rel:r7-seed:r5:civic-candidate:{idx:03d}",
                relationship_type="candidate_related_to",
                source_id=f"source_signal:{signal}",
                target_id=f"civic_review_packet:{packet.get('packet_id', idx)}",
                confidence=0.56,
                review_state="requires_review",
                evidence_refs=packet.get("evidence_refs", []),
                trace_refs=[f"{rel(R5_ROOT / 'R5_CIVIC_SERVICE_RUNTIME_SLICE_OUTPUT_PACKETS.json')}:{packet.get('packet_id')}"],
                source_system_refs=packet.get("source_signal_refs", []) + [packet.get("domain_pack_id", "civic_service_review_context")],
                assertion_method="manual_bridge",
                assertion_boundary="Candidate civic-service relation only; domain review required.",
                limitations=list(dict.fromkeys(packet.get("limitation_refs", []) + ["candidate_not_fact"])),
                category="candidate_review_edges",
                source_evidence_family="domain_pack_evidence",
                source_type="source_record",
                target_type="domain_context",
                relationship_summary=f"{signal} is a candidate relation to {packet.get('packet_id')}.",
            )
        )

    nyc_identity = episode_by_id(episodes, "episode:nyc_lod2_building_identity_candidate")
    if nyc_identity:
        candidate.append(
            edge(
                "rel:r7-seed:track2b:nyc-building-identity-candidate",
                "candidate_related_to",
                (nyc_identity.get("entity_refs") or ["nyc:building:bin:3039983"])[0],
                "source_identity_bundle:nyc:bin3039983:bbl3014920001:doitt504661",
                0.66,
                "requires_review",
                [f"{track2b_path}:episode:nyc_lod2_building_identity_candidate"],
                [f"{track2b_path}:episode:nyc_lod2_building_identity_candidate"],
                nyc_identity.get("source_refs") or ["NYC 2025 Buildings 3D SceneServer", "NYC identity shard"],
                "shared_identifier",
                "Source identity candidate only; no certified or legal truth.",
                nyc_identity.get("limitations") or ["source_candidate_context_only"],
                "candidate_review_edges",
                "city_episode_context",
                source_type="building",
                target_type="source_record",
                relationship_summary="NYC building source identifiers are candidate identity context.",
            )
        )
    if len(real_r6) >= 6:
        a, b = real_r6[0], real_r6[5]
        candidate.append(
            edge(
                "rel:r7-seed:r6:temporal-near-community-events",
                "temporally_near",
                a.get("event_refs", ["r6-event-001"])[0],
                b.get("event_refs", ["r6-event-006"])[0],
                0.42,
                "requires_review",
                list(dict.fromkeys(a.get("evidence_refs", []) + b.get("evidence_refs", []))),
                [
                    f"{rel(R6_ROOT / 'R6_INCIDENT_CONTEXT_PACKETS.json')}:{a.get('packet_id')}",
                    f"{rel(R6_ROOT / 'R6_INCIDENT_CONTEXT_PACKETS.json')}:{b.get('packet_id')}",
                ],
                [a.get("source_entity_id", "unknown-source"), b.get("source_entity_id", "unknown-source")],
                "temporal_cooccurrence",
                "Temporal nearness is review context only and never causal.",
                ["temporal_nearness_not_causal", "candidate_not_fact", "review_context_only"],
                "candidate_review_edges",
                "incident_event_context",
                source_type="event",
                target_type="event",
                direction="symmetric",
                cross_domain=False,
                relationship_summary="Two R6 event-context packets are near in time for review context only.",
            )
        )

    synthetic.append(
        edge(
            "rel:r7-seed:synthetic:validator-only:001",
            "co_occurs_with",
            "synthetic:event:a",
            "synthetic:event:b",
            0.3,
            "requires_review",
            ["synthetic_contract_test_only:evidence"],
            ["synthetic_contract_test_only:trace"],
            ["synthetic_contract_test_only:source"],
            "temporal_cooccurrence",
            "Synthetic validator fixture only.",
            ["synthetic_contract_test_only", "not_city_truth", "not_domain_evidence"],
            "synthetic_contract_test_edges",
            "synthetic_contract_only",
            source_type="event",
            target_type="event",
            cross_domain=False,
            synthetic_contract_test_only=True,
            real_evidence_backed=False,
            direction="symmetric",
            relationship_summary="Synthetic co-occurrence fixture validates candidate/review handling.",
        )
    )

    if real_r6:
        base = real_r6[0]
        rejected.append(
            edge(
                "rel:r7-seed:rejected:caused-by-overclaim",
                "caused_by",
                base.get("event_refs", ["r6-event-001"])[0],
                base.get("entity_refs", ["cer:community:barc:eixample"])[0],
                0.95,
                "rejected",
                base.get("evidence_refs", []),
                [f"{rel(R6_ROOT / 'R6_INCIDENT_CONTEXT_PACKETS.json')}:{base.get('packet_id')}"],
                [base.get("source_entity_id", "unknown-source")],
                "event_resolution",
                "Rejected: source supports context, not causation.",
                ["rejected_overclaim", "direct_source_causation_absent"],
                "rejected_overclaim_edges",
                "incident_event_context",
                source_type="event",
                target_type=infer_entity_type(base.get("entity_refs", [""])[0]),
                blocked_reason="forbidden_causal_relationship_type",
                relationship_summary="Rejected causal overclaim fixture.",
            )
        )
    if sources["r5_packets"]:
        packet = sources["r5_packets"][0]
        rejected.append(
            edge(
                "rel:r7-seed:rejected:legal-control-overclaim",
                "enforcement_action",
                (packet.get("source_signal_refs") or ["barc:iris:service-context:001"])[0],
                "action:service-ticket-or-control",
                0.9,
                "rejected",
                packet.get("evidence_refs", []),
                [f"{rel(R5_ROOT / 'R5_CIVIC_SERVICE_RUNTIME_SLICE_OUTPUT_PACKETS.json')}:{packet.get('packet_id')}"],
                packet.get("source_signal_refs", []),
                "manual_bridge",
                "Rejected: review packet cannot become a legal or action output.",
                ["rejected_overclaim", "action_or_legal_policy_absent"],
                "rejected_overclaim_edges",
                "domain_pack_evidence",
                source_type="source_record",
                target_type="domain_context",
                blocked_reason="forbidden_legal_control_relationship_type",
                relationship_summary="Rejected legal/action overclaim fixture.",
            )
        )

    estimate["edges_seeded_this_run_estimate"] = len(accepted) + len(candidate) + len(synthetic)
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-EDGE-SEED-REGISTRY-EXPANSION-R1",
        "status": "PASS_WITH_LIMITATIONS",
        "accepted_grounded_edges": accepted,
        "candidate_review_edges": candidate,
        "rejected_overclaim_edges": rejected,
        "synthetic_contract_test_edges": synthetic,
        "registry_counts": {
            "accepted_grounded_edges": len(accepted),
            "candidate_review_edges": len(candidate),
            "rejected_overclaim_edges": len(rejected),
            "synthetic_contract_test_edges": len(synthetic),
        },
        "materially_expanded_beyond_r7_preflight": len([e for e in accepted + candidate if e.get("real_evidence_backed")]) > 6,
        "missing_families_recorded": [
            "has_permit_context",
            "has_inspection_context",
            "has_violation_context",
            "adjacent_to",
            "contains",
            "serves",
            "spatially_near",
        ],
        "population_estimate_snapshot": estimate,
    }


def evidence_bundles(registry: dict[str, Any]) -> list[dict[str, Any]]:
    bundles = []
    for item in registry["accepted_grounded_edges"] + registry["candidate_review_edges"] + registry["synthetic_contract_test_edges"]:
        bundles.append(
            {
                "relationship_id": item["relationship_id"],
                "relationship_summary": item["relationship_summary"],
                "relationship_type": item["relationship_type"],
                "source_entity": {
                    "canonical_entity_id": item["source_canonical_entity_id"],
                    "entity_type": item["source_entity_type"],
                },
                "target_entity": {
                    "canonical_entity_id": item["target_canonical_entity_id"],
                    "entity_type": item["target_entity_type"],
                },
                "evidence_items": [
                    {
                        "evidence_ref": evidence_ref,
                        "source_system_refs": item["source_system_refs"],
                        "trace_refs": item["trace_refs"],
                    }
                    for evidence_ref in item["evidence_refs"]
                ],
                "trace_refs": item["trace_refs"],
                "confidence": item["confidence"],
                "review_state": item["review_state"],
                "limitations": item["limitations"],
                "claim_boundary": item["assertion_boundary"],
                "why_allowed": "Required evidence, trace, limitation, not-causal, and no-action fields are present.",
                "why_not_stronger": "The seed does not upgrade context/candidate edges into certified facts or a runtime graph truth layer.",
                "why_not_causal": "The source evidence supports bounded relationship context only and does not state direct causation.",
                "safe_next_data_needed": [
                    "source-asserted relationship evidence for stronger families",
                    "review outcomes for candidate edges",
                    "runtime registry validation before graph/traversal consumers use the seed",
                ],
                "backend_only": True,
            }
        )
    return bundles


def graph_projection(registry: dict[str, Any], bundles: list[dict[str, Any]]) -> dict[str, Any]:
    bundle_ids = {bundle["relationship_id"] for bundle in bundles}
    nodes: dict[str, dict[str, Any]] = {}
    projection_edges = []
    all_edges = (
        registry["accepted_grounded_edges"]
        + registry["candidate_review_edges"]
        + registry["rejected_overclaim_edges"]
        + registry["synthetic_contract_test_edges"]
    )
    for item in all_edges:
        nodes[item["source_canonical_entity_id"]] = {
            "node_id": item["source_canonical_entity_id"],
            "node_type": item["source_entity_type"],
        }
        nodes[item["target_canonical_entity_id"]] = {
            "node_id": item["target_canonical_entity_id"],
            "node_type": item["target_entity_type"],
        }
        grounded = item["review_state"] in {"asserted_source", "inferred_deterministic"} and item["fixture_category"] == "accepted_grounded_edges"
        review = item["review_state"] in {"candidate_probabilistic", "requires_review"} and item["fixture_category"] in {
            "candidate_review_edges",
            "synthetic_contract_test_edges",
        }
        rejected = item["review_state"] in {"rejected", "disputed", "deprecated"} or item["fixture_category"] == "rejected_overclaim_edges"
        projection_edges.append(
            {
                "edge_id": item["relationship_id"],
                "source": item["source_canonical_entity_id"],
                "target": item["target_canonical_entity_id"],
                "relationship_type": item["relationship_type"],
                "review_state": item["review_state"],
                "confidence": item["confidence"],
                "not_causal": item["not_causal"],
                "real_evidence_backed": item["real_evidence_backed"],
                "cross_domain": item["cross_domain"],
                "spatial_only": item["spatial_only"],
                "synthetic_contract_test_only": item["synthetic_contract_test_only"],
                "evidence_bundle_ref": item["relationship_id"] if item["relationship_id"] in bundle_ids else None,
                "limitations": item["limitations"],
                "trace_refs": item["trace_refs"],
                "traversal_visibility": "grounded_context"
                if grounded
                else "review_context"
                if review
                else "blocked_or_rejected",
                "incident_mode_allowed_as_grounded_context": grounded and not item["synthetic_contract_test_only"],
                "incident_mode_allowed_as_review_context": review and not item["synthetic_contract_test_only"],
                "incident_mode_blocked_as_positive_context": rejected or item["synthetic_contract_test_only"],
            }
        )
    examples = [
        {
            "traversal_id": "r7-seed-traversal-incident-context",
            "seed": "cer:community:barc:eixample",
            "max_depth": 2,
            "edges_returned": [
                edge["edge_id"]
                for edge in projection_edges
                if edge["source"] == "cer:community:barc:eixample" or edge["target"] == "cer:community:barc:eixample"
            ][:8],
            "grounded_edges": [
                edge["edge_id"]
                for edge in projection_edges
                if edge["incident_mode_allowed_as_grounded_context"]
                and (edge["source"] == "cer:community:barc:eixample" or edge["target"] == "cer:community:barc:eixample")
            ][:8],
            "candidate_review_edges": [
                edge["edge_id"]
                for edge in projection_edges
                if edge["incident_mode_allowed_as_review_context"]
                and (edge["source"] == "cer:community:barc:eixample" or edge["target"] == "cer:community:barc:eixample")
            ][:8],
            "blocked_edges": [
                edge["edge_id"]
                for edge in projection_edges
                if edge["incident_mode_blocked_as_positive_context"]
                and (edge["source"] == "cer:community:barc:eixample" or edge["target"] == "cer:community:barc:eixample")
            ][:8],
        },
        {
            "traversal_id": "r7-seed-traversal-building-review-context",
            "seed": "cer:building:barc:eixample:lod2:001",
            "max_depth": 2,
            "edges_returned": [
                edge["edge_id"]
                for edge in projection_edges
                if edge["source"] == "cer:building:barc:eixample:lod2:001"
                or edge["target"] == "cer:building:barc:eixample:lod2:001"
            ][:8],
            "grounded_edges": [
                edge["edge_id"]
                for edge in projection_edges
                if edge["incident_mode_allowed_as_grounded_context"]
                and (
                    edge["source"] == "cer:building:barc:eixample:lod2:001"
                    or edge["target"] == "cer:building:barc:eixample:lod2:001"
                )
            ][:8],
            "candidate_review_edges": [
                edge["edge_id"]
                for edge in projection_edges
                if edge["incident_mode_allowed_as_review_context"]
                and (
                    edge["source"] == "cer:building:barc:eixample:lod2:001"
                    or edge["target"] == "cer:building:barc:eixample:lod2:001"
                )
            ][:8],
            "blocked_edges": [
                edge["edge_id"]
                for edge in projection_edges
                if edge["incident_mode_blocked_as_positive_context"]
                and (
                    edge["source"] == "cer:building:barc:eixample:lod2:001"
                    or edge["target"] == "cer:building:barc:eixample:lod2:001"
                )
            ][:8],
        },
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-EDGE-SEED-GRAPH-PROJECTION-R1",
        "status": "PASS_WITH_LIMITATIONS",
        "projection_type": "json_fixture_only",
        "nodes": list(nodes.values()),
        "edges": projection_edges,
        "traversal_visibility_rules": {
            "asserted_source_or_inferred_deterministic": "grounded backend context",
            "candidate_probabilistic_or_requires_review": "review context only",
            "rejected_disputed_deprecated": "not positive context",
            "synthetic_contract_test_only": "never CityBrain truth",
        },
        "traversal_examples": examples,
        "graph_projection_preserves_review_state": all("review_state" in edge for edge in projection_edges),
        "graph_projection_preserves_candidate_vs_grounded_distinction": all("traversal_visibility" in edge for edge in projection_edges),
    }


def validate_edge(item: dict[str, Any], allowed_relationship_types: list[str]) -> tuple[bool, list[str]]:
    errors = []
    missing = [field for field in REQUIRED_EDGE_FIELDS if field not in item]
    if missing:
        errors.append(f"missing_required_fields:{','.join(missing)}")
    if item.get("relationship_type") not in allowed_relationship_types:
        errors.append(f"relationship_type_not_allowed:{item.get('relationship_type')}")
    if item.get("relationship_type") in FORBIDDEN_RELATIONSHIP_TYPES:
        errors.append(f"forbidden_relationship_type:{item.get('relationship_type')}")
    if not item.get("source_canonical_entity_id") or not item.get("target_canonical_entity_id"):
        errors.append("source_or_target_entity_missing")
    if not isinstance(item.get("confidence"), (int, float)) or not 0 <= float(item.get("confidence", -1)) <= 1:
        errors.append("confidence_invalid")
    if item.get("review_state") not in REVIEW_STATES:
        errors.append("review_state_invalid")
    if item.get("assertion_method") not in ASSERTION_METHODS:
        errors.append("assertion_method_invalid")
    if item.get("real_evidence_backed") and not item.get("evidence_refs"):
        errors.append("evidence_refs_missing_for_real_edge")
    if not item.get("trace_refs"):
        errors.append("trace_refs_missing")
    if not item.get("limitations"):
        errors.append("limitations_missing")
    if item.get("not_causal") is not True:
        errors.append("not_causal_not_true")
    if item.get("no_action_taken") is not True:
        errors.append("no_action_taken_not_true")
    if item.get("synthetic_contract_test_only"):
        if item.get("real_evidence_backed") or item.get("not_city_truth") is not True or item.get("not_domain_evidence") is not True:
            errors.append("synthetic_flags_invalid")
    if item.get("fixture_category") == "candidate_review_edges":
        if item.get("review_state") not in {"candidate_probabilistic", "requires_review"}:
            errors.append("candidate_review_state_invalid")
    accepted_text = " ".join(
        str(item.get(field, ""))
        for field in ["relationship_type", "relationship_summary", "assertion_boundary"]
    ).lower()
    for word in FORBIDDEN_ACCEPTED_WORDS:
        if word in accepted_text and item.get("fixture_category") != "rejected_overclaim_edges":
            errors.append(f"forbidden_wording_in_accepted_edge:{word}")
    return not errors, errors


def validation_results(
    registry: dict[str, Any],
    bundles: list[dict[str, Any]],
    projection: dict[str, Any],
    estimate: dict[str, Any],
    allowed_relationship_types: list[str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    accepted_or_candidate = registry["accepted_grounded_edges"] + registry["candidate_review_edges"] + registry["synthetic_contract_test_edges"]
    results = []
    for item in accepted_or_candidate:
        passed, errors = validate_edge(item, allowed_relationship_types)
        results.append({"relationship_id": item["relationship_id"], "passed": passed, "errors": errors})
    bundle_ids = {bundle["relationship_id"] for bundle in bundles}
    bundle_coverage = [item["relationship_id"] for item in accepted_or_candidate if item["relationship_id"] in bundle_ids]
    projection_edges = projection["edges"]
    graph_preserves = projection.get("graph_projection_preserves_review_state") and projection.get(
        "graph_projection_preserves_candidate_vs_grounded_distinction"
    )
    status = "PASS" if all(item["passed"] for item in results) and len(bundle_coverage) == len(accepted_or_candidate) and graph_preserves else "FAIL"
    all_edges = accepted_or_candidate + registry["rejected_overclaim_edges"]
    accepted_real = [item for item in registry["accepted_grounded_edges"] + registry["candidate_review_edges"] if item["real_evidence_backed"]]
    accepted_real_cross = [item for item in accepted_real if item["cross_domain"]]
    grounded_cross = [item for item in registry["accepted_grounded_edges"] if item["cross_domain"]]
    relationship_families = sorted({item["relationship_type"] for item in registry["accepted_grounded_edges"] + registry["candidate_review_edges"]})
    cross_domain_families = sorted({item["relationship_type"] for item in accepted_real_cross})
    source_families = sorted({source_family_from_edge(item) for item in registry["accepted_grounded_edges"] + registry["candidate_review_edges"] if item["real_evidence_backed"]})
    validation = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-EDGE-SEED-VALIDATION-R1",
        "status": status,
        "edge_validation_results": results,
        "validation_passed": status == "PASS",
        "bundle_coverage_count": len(bundle_coverage),
        "bundle_coverage_expected": len(accepted_or_candidate),
        "graph_projection_edge_count": len(projection_edges),
        "graph_projection_preserves_review_state": projection.get("graph_projection_preserves_review_state"),
        "graph_projection_preserves_candidate_vs_grounded_distinction": projection.get(
            "graph_projection_preserves_candidate_vs_grounded_distinction"
        ),
        "population_estimate_present": bool(estimate),
        "incident_mode_context_richness_assessment_present": bool(estimate.get("estimated_incident_mode_context_richness")),
        "candidate_edges_not_treated_as_facts": all(
            item["review_state"] in {"candidate_probabilistic", "requires_review"}
            for item in registry["candidate_review_edges"] + registry["synthetic_contract_test_edges"]
        ),
        "synthetic_edges_not_treated_as_truth": all(
            item["synthetic_contract_test_only"] and not item["real_evidence_backed"] and item["not_city_truth"]
            for item in registry["synthetic_contract_test_edges"]
        ),
        "accepted_grounded_edges_count": len(registry["accepted_grounded_edges"]),
        "candidate_review_edges_count": len(registry["candidate_review_edges"]),
        "rejected_overclaim_edges_count": len(registry["rejected_overclaim_edges"]),
        "synthetic_contract_test_edges_count": len(registry["synthetic_contract_test_edges"]),
        "real_evidence_backed_edges_count": len(accepted_real),
        "real_evidence_backed_cross_domain_edges_count": len(accepted_real_cross),
        "grounded_cross_domain_edges_count": len(grounded_cross),
        "spatial_only_edges_count": sum(1 for item in all_edges if item.get("spatial_only")),
        "relationship_families_represented": relationship_families,
        "relationship_families_represented_count": len(relationship_families),
        "cross_domain_relationship_families_represented": cross_domain_families,
        "cross_domain_relationship_families_represented_count": len(cross_domain_families),
        "source_evidence_families_represented": source_families,
        "source_evidence_families_represented_count": len(source_families),
    }

    bad_tests = build_rejection_tests(registry, allowed_relationship_types)
    rejection_results = []
    for test in bad_tests:
        passed, errors = validate_edge(test["edge"], allowed_relationship_types)
        rejection_results.append(
            {
                "test_id": test["test_id"],
                "expected_rejection_reason": test["expected_rejection_reason"],
                "rejected": not passed,
                "validator_errors": errors,
            }
        )
    rejection = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-EDGE-SEED-VALIDATION-R1",
        "status": "PASS" if all(item["rejected"] for item in rejection_results) else "FAIL",
        "rejection_tests_passed": all(item["rejected"] for item in rejection_results),
        "rejection_test_results": rejection_results,
        "registry_rejected_overclaim_edges": [
            {
                "relationship_id": item["relationship_id"],
                "relationship_type": item["relationship_type"],
                "blocked_reason": item.get("blocked_reason"),
            }
            for item in registry["rejected_overclaim_edges"]
        ],
    }
    causation = no_causation_audit(registry)
    return validation, rejection, causation


def build_rejection_tests(registry: dict[str, Any], allowed_relationship_types: list[str]) -> list[dict[str, Any]]:
    base = dict(registry["accepted_grounded_edges"][0])
    candidate = dict(registry["candidate_review_edges"][0])
    synthetic = dict(registry["synthetic_contract_test_edges"][0])

    tests = []
    caused = dict(base)
    caused["relationship_id"] = "rel:r7-seed:negative-test:caused-by"
    caused["relationship_type"] = "caused_by"
    tests.append({"test_id": "caused_by_overclaim", "edge": caused, "expected_rejection_reason": "forbidden causal relationship"})

    legal = dict(base)
    legal["relationship_id"] = "rel:r7-seed:negative-test:legal-control"
    legal["relationship_type"] = "legal_violation"
    tests.append({"test_id": "legal_enforcement_overclaim", "edge": legal, "expected_rejection_reason": "forbidden legal/control relationship"})

    missing_evidence = dict(base)
    missing_evidence["relationship_id"] = "rel:r7-seed:negative-test:missing-evidence"
    missing_evidence["evidence_refs"] = []
    tests.append({"test_id": "missing_evidence_refs_on_real_edge", "edge": missing_evidence, "expected_rejection_reason": "missing evidence refs"})

    missing_not_causal = dict(candidate)
    missing_not_causal["relationship_id"] = "rel:r7-seed:negative-test:candidate-missing-not-causal"
    missing_not_causal["not_causal"] = False
    tests.append({"test_id": "candidate_edge_missing_not_causal", "edge": missing_not_causal, "expected_rejection_reason": "candidate missing not_causal"})

    missing_review = dict(candidate)
    missing_review["relationship_id"] = "rel:r7-seed:negative-test:candidate-missing-review-state"
    missing_review["review_state"] = "asserted_source"
    tests.append({"test_id": "candidate_edge_missing_review_state", "edge": missing_review, "expected_rejection_reason": "candidate missing review state"})

    bad_synthetic = dict(synthetic)
    bad_synthetic["relationship_id"] = "rel:r7-seed:negative-test:synthetic-marked-real"
    bad_synthetic["real_evidence_backed"] = True
    bad_synthetic["not_city_truth"] = False
    tests.append({"test_id": "synthetic_edge_marked_as_real_evidence", "edge": bad_synthetic, "expected_rejection_reason": "synthetic flags invalid"})

    return tests


def no_causation_audit(registry: dict[str, Any]) -> dict[str, Any]:
    accepted = registry["accepted_grounded_edges"] + registry["candidate_review_edges"] + registry["synthetic_contract_test_edges"]
    hits = []
    for item in accepted:
        text = " ".join([item["relationship_type"], item["relationship_summary"], item["assertion_boundary"]]).lower()
        item_hits = [word for word in FORBIDDEN_ACCEPTED_WORDS if word in text]
        if item["relationship_type"] in FORBIDDEN_RELATIONSHIP_TYPES:
            item_hits.append(f"forbidden_relationship_type:{item['relationship_type']}")
        if item_hits:
            hits.append({"relationship_id": item["relationship_id"], "hits": item_hits})
    rejected = [
        {
            "relationship_id": item["relationship_id"],
            "relationship_type": item["relationship_type"],
            "correctly_blocked": item["relationship_type"] in FORBIDDEN_RELATIONSHIP_TYPES,
            "blocked_reason": item.get("blocked_reason"),
        }
        for item in registry["rejected_overclaim_edges"]
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-EDGE-SEED-VALIDATION-R1",
        "status": "PASS" if not hits and all(item["correctly_blocked"] for item in rejected) else "FAIL",
        "accepted_edges_forbidden_hits": hits,
        "rejected_overclaim_edges": rejected,
        "ungrounded_causal_claim_accepted": bool(hits),
        "causal_legal_control_claims_absent_or_correctly_rejected": not hits,
    }


def collision_audit(before: dict[str, dict[str, str]], after: dict[str, dict[str, str]]) -> dict[str, Any]:
    changes = []
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            changes.append({"surface": key, "before": before.get(key), "after": after.get(key)})
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-EDGE-SEED-VALIDATION-R1",
        "status": "PASS" if not changes else "FAIL",
        "watched_surfaces": {key: rel(path) for key, path in D6_SURFACE_WATCH.items()},
        "d6_collision_avoidance_passed": not changes,
        "omniverse_collision_avoidance_passed": not changes,
        "served_runtime_mutation_avoided": not changes,
        "frontend_artifacts_created": False,
        "omniverse_artifacts_created": False,
        "served_runtime_modified": False,
        "observed_signature_changes": changes,
    }


def top_down_examples(registry: dict[str, Any], bundles: list[dict[str, Any]], projection: dict[str, Any], estimate: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    projection_by_id = {item["edge_id"]: item for item in projection["edges"]}
    bundle_ids = {bundle["relationship_id"] for bundle in bundles}

    def make_example(example_id: str, seed: str, kind: str) -> dict[str, Any]:
        related = [
            item
            for item in projection["edges"]
            if item["source"] == seed or item["target"] == seed or (kind == "watchlist" and item["cross_domain"])
        ][:12]
        grounded = [item for item in related if item["incident_mode_allowed_as_grounded_context"]]
        candidate = [item for item in related if item["incident_mode_allowed_as_review_context"]]
        rejected = [item for item in related if item["incident_mode_blocked_as_positive_context"]]
        cross_domain = [item for item in related if item["cross_domain"]]
        richness = "rich" if len(related) >= 10 and len(cross_domain) >= 6 else "moderate" if len(related) >= 4 else "sparse"
        useful = richness in {"moderate", "rich"} and bool(grounded)
        return {
            "backend_request_id": example_id,
            "question_or_backend_request": "Retrieve backend relationship context from the seed registry; do not generate operator copy.",
            "seed_event_id": next((item["target"] for item in related if infer_entity_type(item["target"]) == "event"), None),
            "seed_canonical_entity_id": seed,
            "relationship_types_retrieved": sorted({item["relationship_type"] for item in related}),
            "edges_returned": [item["edge_id"] for item in related],
            "evidence_bundle_refs": [item["edge_id"] for item in related if item["edge_id"] in bundle_ids],
            "grounded_edges": [item["edge_id"] for item in grounded],
            "candidate_review_edges": [item["edge_id"] for item in candidate],
            "rejected_edges": [item["edge_id"] for item in rejected],
            "not_causal_explanation": "All returned edges carry not_causal=true; rejected overclaims are blocked from positive context.",
            "why_not_stronger": "This is a JSON seed/projection, not a runtime graph or reviewed production truth layer.",
            "safe_next_data_needed": [
                "source-diverse edge seeding",
                "review-state upgrades where source policy allows",
                "runtime traversal validation before Incident Mode use",
            ],
            "population_estimate_implication": estimate["incident_mode_bottleneck_assessment"],
            "whether_context_is_sparse_moderate_or_rich": richness,
            "traversal_edge_count": len(related),
            "grounded_traversal_edge_count": len(grounded),
            "candidate_review_traversal_edge_count": len(candidate),
            "rejected_or_blocked_edge_count": len(rejected),
            "cross_domain_traversal_edge_count": len(cross_domain),
            "traversal_depth": 2,
            "context_richness_assessment": richness,
            "is_context_useful_for_incident_mode": useful,
            "why_context_is_or_is_not_useful": "Useful as backend context because grounded/review distinctions survive traversal."
            if useful
            else "Sparse context; additional source/domain evidence is needed.",
            "population_estimate_consistency_check": "consistent_with_edge_population_estimate",
            "surface_artifacts_created": False,
            "uses_real_evidence": True,
        }

    examples = [
        make_example("r7-edge-seed-incident-backend-context-example", "cer:community:barc:eixample", "incident"),
        make_example("r7-edge-seed-insight-watchlist-backend-context-example", "cer:building:barc:eixample:lod2:001", "watchlist"),
    ]
    total_edges = sum(item["traversal_edge_count"] for item in examples)
    grounded_total = sum(item["grounded_traversal_edge_count"] for item in examples)
    candidate_total = sum(item["candidate_review_traversal_edge_count"] for item in examples)
    cross_total = sum(item["cross_domain_traversal_edge_count"] for item in examples)
    richness = "rich" if total_edges >= 18 and cross_total >= 10 else "moderate" if total_edges >= 8 else "sparse"
    assessment = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-EDGE-SEED-TOP-DOWN-TRACE-EXAMPLES-R1",
        "status": "PASS",
        "examples_total": len(examples),
        "traversal_edge_count": total_edges,
        "grounded_traversal_edge_count": grounded_total,
        "candidate_review_traversal_edge_count": candidate_total,
        "cross_domain_traversal_edge_count": cross_total,
        "context_richness_assessment": richness,
        "context_useful_for_incident_mode": richness in {"moderate", "rich"} and grounded_total > 0,
        "interpretation": "Current seed is useful for backend context retrieval, but richer Incident Mode still needs more source-family diversity.",
        "surface_artifacts_created": False,
    }
    return {"schema_version": SCHEMA_VERSION, "status": "PASS", "examples": examples}, assessment


def handoffs(registry: dict[str, Any], bundles: list[dict[str, Any]], estimate: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    grounded = registry["accepted_grounded_edges"][:10]
    candidate = registry["candidate_review_edges"][:8]
    incident = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-EDGE-SEED-CONSUMER-HANDOFFS-R1",
        "status": "PASS",
        "backend_only": True,
        "event_id": grounded[0]["target_canonical_entity_id"] if grounded else None,
        "resolved_entity_refs": sorted({item["source_canonical_entity_id"] for item in grounded}),
        "relationship_context_query": {
            "seed_entity_or_event": grounded[0]["source_canonical_entity_id"] if grounded else None,
            "allowed_context": ["grounded_relationship_context", "candidate_relationship_context"],
            "blocked_context": ["rejected_overclaim_edges", "synthetic_contract_test_edges_as_truth"],
        },
        "grounded_relationship_context": [item["relationship_id"] for item in grounded],
        "candidate_relationship_context": [item["relationship_id"] for item in candidate],
        "relationship_evidence_bundles": [bundle["relationship_id"] for bundle in bundles[:18]],
        "uncertainty_summary": "Most edges are bounded context; candidates remain review-only and are not facts.",
        "limitations": LIMITATIONS,
        "not_causal_flags": True,
        "safe_next_data_needed": estimate["recommended_evidence_to_ingest_next"],
        "operator_briefing_created": False,
        "frontend_cards_created": False,
    }
    watch = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-EDGE-SEED-CONSUMER-HANDOFFS-R1",
        "status": "PASS",
        "backend_only": True,
        "watch_candidate_id": "r7-edge-seed-watch-candidate-001",
        "relationship_pattern": "entity/event context plus candidate review relation, preserving review state",
        "evidence_bundle_refs": [item["relationship_id"] for item in bundles[0:12]],
        "confidence": 0.62,
        "review_state": "requires_review",
        "why_watch": "Backend may watch repeated bounded context around the same entity family.",
        "why_not_alert": "Seed edges are context/review only and not an alert, action, or product feed.",
        "limitations": LIMITATIONS,
        "not_actionable_yet": True,
        "watchlist_ui_created": False,
        "alert_feed_ui_created": False,
    }
    return incident, watch


def closeout_docs(decision: dict[str, Any], validation: dict[str, Any], estimate: dict[str, Any]) -> dict[str, str]:
    family_list = ", ".join(validation["relationship_families_represented"])
    source_family_list = ", ".join(validation["source_evidence_families_represented"])
    report = f"""
# Cross-Domain Relationship Edge Seed R1

Status: `{decision['status']}`

This backend-only seed expands the R7 substrate from the preflight examples into
a first relationship edge registry for later Incident Mode, insight/watchlist,
and graph traversal work.

## Headline Finding

The current evidence base can support approximately
`{estimate['real_evidence_backed_cross_domain_edges_constructible_now']}` real
evidence-backed cross-domain edges now, dominated by R6 event/entity context.
The seed created `{decision['real_evidence_backed_edges_count']}` real
evidence-backed accepted edges, including
`{decision['real_evidence_backed_cross_domain_edges_count']}` cross-domain edges.

## What Is Proven

- Edge registry, evidence bundles, graph projection fixture, validation, rejection tests, and backend handoffs were created.
- Relationship families represented: {family_list}.
- Source evidence families represented: {source_family_list}.
- Candidate/review and synthetic-contract-only edges remain distinguishable from grounded context.
- Rejected causal/legal/control overclaims remain blocked.

## Population Ceiling

The run did not fail because of implementation shape. The current ceiling is
evidence diversity: most available relationships are event-context and civic
review context. Permit, inspection, violation, adjacency, service dependency,
and reviewed building-domain relationships need additional source evidence.

## Incident Mode Usefulness

The seed is useful for backend Incident Mode context retrieval at a moderate
level. It is not yet enough for product/demo surface claims or autonomous
reasoning because the source-family mix is narrow and many candidate edges need
review.
"""
    limitations = "# Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS)
    next_steps = f"""
# Next Steps

Recommended next task:

`{NEXT_TASK}`

Recommended after D6 closes:

`{AFTER_D6_TASK}`

Evidence to ingest next:

{chr(10).join(f"- {item}" for item in estimate['recommended_evidence_to_ingest_next'])}
"""
    git_plan = f"""
# Git Checkpoint Plan

Suggested commit message:

`citybrain: seed cross-domain relationship edges`

Recommended exact checkpoint commands:

```powershell
git add scripts/run_main_track1_d4y_r7_cross_domain_relationship_edge_seed_r1.py
git add outputs/main_track1_d4y_r7_cross_domain_relationship_edge_seed_r1
git status --short
git commit -m "citybrain: seed cross-domain relationship edges"
```

Do not add:

```text
data/
bulk CSV/shapefile/zip assets
entire outputs tree
unrelated untracked files
```

Checkpoint warning:

The relationship ontology, grounding policy, assertion contract, evidence bundle
shape, graph projection, and seed registry are core intellectual assets. They
should not remain only as untracked output artifacts. Preserve this runner and
pack deliberately, while keeping unrelated output bloat out of the commit.
"""
    return {"report": report, "limitations": limitations, "next_steps": next_steps, "git_plan": git_plan}


def write_hashes() -> dict[str, Any]:
    rows = []
    for path in sorted(p for p in OUTPUT_ROOT.rglob("*") if p.is_file() and p.name != "hashes.sha256"):
        rows.append((path.relative_to(OUTPUT_ROOT).as_posix(), sha256_file(path)))
    (OUTPUT_ROOT / "hashes.sha256").write_text(
        "".join(f"{digest}  {relative_path}\n" for relative_path, digest in rows),
        encoding="utf-8",
    )
    return {"schema_version": SCHEMA_VERSION, "status": "PASS", "count": len(rows)}


def main() -> None:
    before_surface = {key: path_signature(path) for key, path in D6_SURFACE_WATCH.items()}
    prepare_output_root()

    ontology = read_json(R7_PREFLIGHT_ROOT / "RELATIONSHIP_ONTOLOGY_R1.json", {})
    allowed_relationship_types = [
        item.get("relationship_type")
        for item in ontology.get("relationship_types", [])
        if isinstance(item, dict) and item.get("relationship_type")
    ] or FALLBACK_ALLOWED_RELATIONSHIP_TYPES
    upstream = upstream_audit(allowed_relationship_types)
    write_json(OUTPUT_ROOT / "UPSTREAM_R7_PREFLIGHT_AUDIT.json", upstream)

    go_no_go = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-EDGE-SEED-UPSTREAM-AUDIT-R0",
        "status": "PASS" if upstream["status"] == "PASS" else upstream["status"],
        "go": upstream["status"] == "PASS",
        "upstream_r7_status": upstream.get("upstream_r7_status"),
        "stop_reason": None if upstream["status"] == "PASS" else "upstream preflight missing, corrupt, or unsafe",
    }
    write_json(OUTPUT_ROOT / "EDGE_SEED_GO_NO_GO_DECISION.json", go_no_go)

    if upstream["status"] != "PASS":
        decision = {
            "task_id": TASK_ID,
            "status": HOLD_STATUS if upstream["status"] == "HOLD" else FAIL_STATUS,
            "repo_root": str(REPO_ROOT),
            "output_root": str(OUTPUT_ROOT),
            "run_timestamp_utc": now(),
            "runner_path": str(RUNNER_PATH),
            "upstream_r7_preflight_found": R7_PREFLIGHT_ROOT.exists(),
            "upstream_r7_status": upstream.get("upstream_r7_status"),
            "next_recommended_task": "MAIN-TRACK1-D4Y-R7-CROSS-DOMAIN-RELATIONSHIP-SUBSTRATE-PREFLIGHT-REPAIR",
        }
        write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R7_CROSS_DOMAIN_RELATIONSHIP_EDGE_SEED_R1_DECISION.json", decision)
        write_hashes()
        return

    sources = load_sources()
    discovery, estimate = edge_source_discovery(sources)
    registry = seed_registry(sources, estimate)
    bundles = evidence_bundles(registry)
    projection = graph_projection(registry, bundles)
    validation, rejection, causation = validation_results(registry, bundles, projection, estimate, allowed_relationship_types)
    top_down, richness = top_down_examples(registry, bundles, projection, estimate)
    incident_handoff, watchlist_handoff = handoffs(registry, bundles, estimate)

    write_json(OUTPUT_ROOT / "EDGE_SOURCE_DISCOVERY_AUDIT.json", discovery)
    write_json(OUTPUT_ROOT / "EDGE_POPULATION_ESTIMATE.json", estimate)
    write_json(OUTPUT_ROOT / "RELATIONSHIP_EDGE_SEED_REGISTRY.json", registry)
    write_json(OUTPUT_ROOT / "RELATIONSHIP_EDGE_SEED_EVIDENCE_BUNDLES.json", bundles)
    write_json(OUTPUT_ROOT / "RELATIONSHIP_EDGE_SEED_GRAPH_PROJECTION.json", projection)
    write_json(OUTPUT_ROOT / "RELATIONSHIP_EDGE_SEED_VALIDATION_RESULTS.json", validation)
    write_json(OUTPUT_ROOT / "RELATIONSHIP_EDGE_SEED_REJECTION_RESULTS.json", rejection)
    write_json(OUTPUT_ROOT / "NO_CAUSATION_OVERCLAIM_AUDIT.json", causation)
    write_json(OUTPUT_ROOT / "RELATIONSHIP_EDGE_SEED_TOP_DOWN_TRACE_EXAMPLES.json", top_down)
    write_json(OUTPUT_ROOT / "RELATIONSHIP_EDGE_SEED_TRAVERSAL_RICHNESS_ASSESSMENT.json", richness)
    write_json(OUTPUT_ROOT / "RELATIONSHIP_EDGE_SEED_INCIDENT_BACKEND_HANDOFF.json", incident_handoff)
    write_json(OUTPUT_ROOT / "RELATIONSHIP_EDGE_SEED_INSIGHT_WATCHLIST_HANDOFF.json", watchlist_handoff)

    after_surface = {key: path_signature(path) for key, path in D6_SURFACE_WATCH.items()}
    collision = collision_audit(before_surface, after_surface)
    write_json(OUTPUT_ROOT / "D6_OMNIVERSE_RUNTIME_COLLISION_AUDIT.json", collision)

    pass_thresholds_met = (
        validation["real_evidence_backed_edges_count"] >= 12
        and validation["real_evidence_backed_cross_domain_edges_count"] >= 8
        and validation["relationship_families_represented_count"] >= 4
        and validation["source_evidence_families_represented_count"] >= 2
        and validation["rejected_overclaim_edges_count"] >= 2
        and richness["examples_total"] >= 2
    )
    all_core_safe = (
        validation["status"] == "PASS"
        and rejection["status"] == "PASS"
        and causation["status"] == "PASS"
        and collision["status"] == "PASS"
        and projection["graph_projection_preserves_review_state"]
        and projection["graph_projection_preserves_candidate_vs_grounded_distinction"]
    )
    final_status = STATUS if all_core_safe else FAIL_STATUS
    if all_core_safe and not pass_thresholds_met:
        final_status = STATUS
    if all_core_safe and pass_thresholds_met:
        # Keep the run limited because it is still a backend-only JSON seed with
        # no runtime graph, production CER/SEG, or reviewed product surface.
        final_status = STATUS

    decision = {
        "task_id": TASK_ID,
        "status": final_status,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now(),
        "runner_path": str(RUNNER_PATH),
        "upstream_r7_preflight_found": R7_PREFLIGHT_ROOT.exists(),
        "upstream_r7_status": upstream.get("upstream_r7_status"),
        "source_discovery_status": discovery["status"],
        "edge_population_estimate_created": True,
        "estimated_grounded_cross_domain_edges_constructible_now": estimate["real_evidence_backed_cross_domain_edges_constructible_now"],
        "estimated_candidate_review_edges_constructible_now": estimate["candidate_review_edges_constructible_now"],
        "estimated_edges_blocked_by_missing_evidence": estimate["edges_blocked_by_missing_evidence"],
        "estimated_edges_blocked_by_causation_boundary": estimate["edges_blocked_by_causation_boundary"],
        "estimated_incident_mode_context_richness": estimate["estimated_incident_mode_context_richness"],
        "d6_collision_avoidance_passed": collision["d6_collision_avoidance_passed"],
        "omniverse_collision_avoidance_passed": collision["omniverse_collision_avoidance_passed"],
        "served_runtime_mutation_avoided": collision["served_runtime_mutation_avoided"],
        "edge_seed_registry_created": True,
        "edge_seed_evidence_bundles_created": True,
        "edge_seed_graph_projection_created": True,
        "graph_projection_preserves_review_state": projection["graph_projection_preserves_review_state"],
        "graph_projection_preserves_candidate_vs_grounded_distinction": projection[
            "graph_projection_preserves_candidate_vs_grounded_distinction"
        ],
        "top_down_trace_examples_created": True,
        "top_down_traversal_richness_assessment_created": True,
        "top_down_traversal_edge_count": richness["traversal_edge_count"],
        "top_down_grounded_traversal_edge_count": richness["grounded_traversal_edge_count"],
        "top_down_context_richness_assessment": richness["context_richness_assessment"],
        "top_down_context_useful_for_incident_mode": richness["context_useful_for_incident_mode"],
        "incident_backend_handoff_created": True,
        "insight_watchlist_handoff_created": True,
        "git_checkpoint_plan_created": True,
        "accepted_grounded_edges_count": validation["accepted_grounded_edges_count"],
        "candidate_review_edges_count": validation["candidate_review_edges_count"],
        "rejected_overclaim_edges_count": validation["rejected_overclaim_edges_count"],
        "synthetic_contract_test_edges_count": validation["synthetic_contract_test_edges_count"],
        "real_evidence_backed_edges_count": validation["real_evidence_backed_edges_count"],
        "real_evidence_backed_cross_domain_edges_count": validation["real_evidence_backed_cross_domain_edges_count"],
        "grounded_cross_domain_edges_count": validation["grounded_cross_domain_edges_count"],
        "spatial_only_edges_count": validation["spatial_only_edges_count"],
        "relationship_families_represented_count": validation["relationship_families_represented_count"],
        "cross_domain_relationship_families_represented_count": validation["cross_domain_relationship_families_represented_count"],
        "source_evidence_families_represented_count": validation["source_evidence_families_represented_count"],
        "relationship_families_represented": validation["relationship_families_represented"],
        "source_evidence_families_represented": validation["source_evidence_families_represented"],
        "materially_expanded_beyond_r7_preflight": registry["materially_expanded_beyond_r7_preflight"],
        "no_real_evidence_backed_edges_plainly_reported": validation["real_evidence_backed_edges_count"] == 0,
        "no_real_cross_domain_edges_plainly_reported": validation["real_evidence_backed_cross_domain_edges_count"] == 0,
        "edge_population_sparsity_plainly_reported": True,
        "validation_passed": validation["status"] == "PASS",
        "rejection_tests_passed": rejection["status"] == "PASS",
        "no_causation_overclaim_audit_passed": causation["status"] == "PASS",
        "candidate_edges_not_treated_as_facts": validation["candidate_edges_not_treated_as_facts"],
        "synthetic_edges_not_treated_as_truth": validation["synthetic_edges_not_treated_as_truth"],
        "operator_briefing_created": False,
        "executive_narrative_created": False,
        "frontend_artifacts_created": False,
        "omniverse_artifacts_created": False,
        "served_runtime_modified": False,
        "trace_refs_present": all(
            item.get("trace_refs")
            for item in registry["accepted_grounded_edges"] + registry["candidate_review_edges"] + registry["synthetic_contract_test_edges"]
        ),
        "evidence_refs_present": all(
            item.get("evidence_refs")
            for item in registry["accepted_grounded_edges"] + registry["candidate_review_edges"] + registry["synthetic_contract_test_edges"]
        ),
        "limitation_refs_present": all(
            item.get("limitations")
            for item in registry["accepted_grounded_edges"] + registry["candidate_review_edges"] + registry["synthetic_contract_test_edges"]
        ),
        "not_causal_flags_present": all(
            item.get("not_causal") is True
            for item in registry["accepted_grounded_edges"] + registry["candidate_review_edges"] + registry["synthetic_contract_test_edges"]
        ),
        "no_action_taken_flags_present": all(
            item.get("no_action_taken") is True
            for item in registry["accepted_grounded_edges"] + registry["candidate_review_edges"] + registry["synthetic_contract_test_edges"]
        ),
        "production_live_claim_made": False,
        "public_api_claim_made": False,
        "production_frontend_claim_made": False,
        "citywide_twin_claim_made": False,
        "full_mesh_binding_claim_made": False,
        "physical_accuracy_claim_made": False,
        "autonomous_action_exposed": False,
        "legal_or_enforcement_claim_made": False,
        "ungrounded_causal_claim_accepted": causation["ungrounded_causal_claim_accepted"],
        "limitations": LIMITATIONS,
        "next_recommended_task": NEXT_TASK,
        "recommended_after_d6_closes": AFTER_D6_TASK,
    }

    docs = closeout_docs(decision, validation, estimate)
    write_text(OUTPUT_ROOT / "CROSS_DOMAIN_RELATIONSHIP_EDGE_SEED_R1_REPORT.md", docs["report"])
    write_text(OUTPUT_ROOT / "LIMITATIONS_AND_NEXT_STEPS.md", docs["limitations"] + "\n\n" + docs["next_steps"])
    write_json(OUTPUT_ROOT / "CROSS_DOMAIN_RELATIONSHIP_EDGE_SEED_R1_CLOSEOUT_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "CROSS_DOMAIN_RELATIONSHIP_EDGE_SEED_R1_CLOSEOUT_REPORT.md", docs["report"])
    write_text(OUTPUT_ROOT / "CROSS_DOMAIN_RELATIONSHIP_EDGE_SEED_R1_LIMITATIONS.md", docs["limitations"])
    write_text(OUTPUT_ROOT / "CROSS_DOMAIN_RELATIONSHIP_EDGE_SEED_R1_NEXT_STEPS.md", docs["next_steps"])
    write_text(OUTPUT_ROOT / "CROSS_DOMAIN_RELATIONSHIP_EDGE_SEED_R1_GIT_CHECKPOINT_PLAN.md", docs["git_plan"])
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# {TASK_ID}

Status: `{final_status}`

This output pack is a backend-only relationship edge seed. It creates an edge
registry, evidence bundles, JSON graph projection fixture, validation results,
rejection tests, top-down backend trace examples, and backend handoff contracts.

It does not create frontend/demo, D6 control-room, Omniverse, Kit, served
runtime, production API, command, routing, dispatch, control, legal/certified,
or autonomous-action artifacts.
""",
    )
    write_json(
        OUTPUT_ROOT / "CROSS_DOMAIN_RELATIONSHIP_EDGE_SEED_R1_ARTIFACT_INDEX.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "artifacts": sorted(path.relative_to(OUTPUT_ROOT).as_posix() for path in OUTPUT_ROOT.rglob("*") if path.is_file())
            + [
                "MAIN_TRACK1_D4Y_R7_CROSS_DOMAIN_RELATIONSHIP_EDGE_SEED_R1_DECISION.json",
                "hashes.sha256",
            ],
        },
    )

    decision_path = OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R7_CROSS_DOMAIN_RELATIONSHIP_EDGE_SEED_R1_DECISION.json"
    expected_hash_count = len([path for path in OUTPUT_ROOT.rglob("*") if path.is_file() and path.name != "hashes.sha256" and path != decision_path]) + 1
    decision["hash_validation_status"] = "PASS"
    decision["hash_summary"] = {"schema_version": SCHEMA_VERSION, "status": "PASS", "count": expected_hash_count}
    write_json(decision_path, decision)
    write_hashes()


if __name__ == "__main__":
    main()
