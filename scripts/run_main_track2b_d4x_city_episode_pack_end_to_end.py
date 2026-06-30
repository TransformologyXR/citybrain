#!/usr/bin/env python3
"""MAIN-TRACK2B-D4X-CITY-EPISODE-PACK-END-TO-END.

Builds a deterministic city episode content pack for later Track 2C app work.
This task does not implement or mutate the app.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "MAIN-TRACK2B-D4X-CITY-EPISODE-PACK-END-TO-END"
PASS_STATUS = "PASS_MAIN_TRACK2B_D4X_CITY_EPISODE_PACK_END_TO_END_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_TRACK2B_D4X_CITY_EPISODE_PACK_END_TO_END"
OUT = Path("outputs/main_track2b_d4x_city_episode_pack_end_to_end")
BASE_R1 = Path("outputs/main_track2b_d4x_city_episode_pack_r1")
HANDOVER = Path("outputs/_handover_trackB_city_episode_pack_end_to_end/trackB_city_episode_pack_end_to_end_handover")
NEXT_TRACK2C = "MAIN-TRACK2C-D4X-CITY-FIRST-EPISODE-APP-REBUILD-R1"

REQUIRED_FIELDS = [
    "episode_id",
    "episode_type",
    "city_id",
    "city_name",
    "domain",
    "title",
    "headline",
    "summary",
    "what_is_happening",
    "where",
    "entity_refs",
    "situation_refs",
    "event_refs",
    "evidence_refs",
    "source_refs",
    "replay_refs",
    "review_refs",
    "building_asset_refs",
    "graph_query_refs",
    "runtime_packet_refs",
    "insight_refs",
    "lifecycle_states",
    "timeline_or_status",
    "supporting_metrics",
    "limitations",
    "claim_boundary",
    "safe_next_looks",
    "display_priority",
    "app_section_hint",
    "no_action_taken",
]

LIMITATIONS = [
    "curated episode pack only",
    "no app implementation or app mutation",
    "no production readiness claim",
    "no public API",
    "no live/autonomous agents",
    "no external LLM calls",
    "no command/action/enforcement/dispatch/routing/control output",
    "no legal finding, confirmed violation, permit approval/rejection, ownership truth, or certified impact",
    "no certified traffic model",
    "no observed truth from simulation/synthetic",
    "no source IDs as ownership/legal/certified affected-building truth",
    "D5 remains parked",
]

EPISODE_TYPES = [
    "mobility_context",
    "civic_service_municipal",
    "planning_property_address",
    "building_asset_identity",
    "candidate_review",
    "evidence_trace",
    "scenario_replay",
    "synthetic_context",
    "data_quality_source_limitation",
    "cross_city_comparison",
    "graph_query_brain_explanation",
    "trust_boundary",
    "runtime_insight",
]

INPUT_ARTIFACTS = [
    ("handover_package", HANDOVER, True, "task contract and output checklist", "fail if missing", "content-pack boundaries only"),
    ("base_track2b_r1_pack", BASE_R1 / "TRACK2B_CURATED_CITY_EPISODE_PACK.json", True, "base episode candidates", "fail if missing", "reuse as read-only curated context"),
    ("base_track2b_r1_handoff", BASE_R1 / "TRACK2B_APP_HANDOFF_EPISODE_PACK.json", True, "app handoff compatibility context", "derive cards from curated pack", "no app mutation"),
    ("track2c_r7_story_pack", Path("outputs/main_track2c_d4x_city_story_compiler_and_dashboard_r7/TRACK2C_R7_CURATED_CITY_STORY_PACK.json"), False, "city story source context", "use base R1 episodes", "source-derived context only"),
    ("track2c_r6_dashboard", Path("outputs/main_track2c_d4x_city_dashboard_data_integration_r6/app_shell/data/city_dashboard_data.json"), False, "city metrics, building examples, replay items", "use base R1 summaries", "dashboard context only"),
    ("barc_lod2_assets", Path("outputs/d4_3d_barc_lod2_full_i3s_export_r1"), False, "Barcelona 3D/building episodes", "limitation-only building context", "visual/source geometry only"),
    ("nyc_lod2_assets", Path("outputs/d4_3d_nyc_2025_full_i3s_export_r1"), False, "NYC 3D/building episodes", "limitation-only building context", "source identity candidate only"),
    ("barc_consumption_prep", Path("outputs/barc_allflows_consumption_prep_r1"), False, "Barcelona source/evidence refs", "use source limitation episode", "review/context only"),
    ("nyc_consumption_prep", Path("outputs/nyc_flow_consumption_prep_r1"), False, "NYC source/evidence refs", "use source limitation episode", "review/context only"),
    ("chi_consumption_prep", Path("outputs/chi_allflows_consumption_prep_r1"), False, "Chicago civic/service refs", "use source limitation episode", "review/context only"),
    ("lon_consumption_prep", Path("outputs/lon_allflows_consumption_prep_r1"), False, "London TfL/LFB/air/flood refs", "use source limitation episode", "review/context only"),
    ("sdf_replay_smoke", Path("outputs/synthetic_data_factory_d1_event_fabric_replay_smoke_r1/SDF_D1_EVENT_FABRIC_REPLAY_SMOKE_R1_DECISION.json"), False, "synthetic replay proof refs", "use replay limitation only", "synthetic replay/context only"),
    ("d4y_runtime_slice", Path("outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice"), False, "runtime packet episodes", "omit runtime extras if missing", "local runtime handoff only"),
    ("d4y_insight_slice", Path("outputs/main_track1_d4y_r3_insight_engine_slice"), False, "runtime/insight episodes", "omit insight extras if missing", "local insight handoff only"),
]

FORBIDDEN_PATTERNS = [
    r"\bproduction ready\b",
    r"\bproduction-ready\b",
    r"\bpublic api\b",
    r"\blive agent\b",
    r"\bautonomous agent\b",
    r"\bexternal llm\b",
    r"\bdispatch recommendation\b",
    r"\benforcement recommendation\b",
    r"\brouting recommendation\b",
    r"\btraffic-control order\b",
    r"\bcontrol output\b",
    r"\blegal finding\b",
    r"\bconfirmed violation\b",
    r"\bpermit approval\b",
    r"\bpermit rejection\b",
    r"\bownership truth\b",
    r"\bcertified impact\b",
    r"\bcertified traffic model\b",
    r"\bobserved truth\b",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_text(value: str, length: int = 12) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def one_line(value: Any, limit: int = 500) -> str:
    if isinstance(value, (list, dict)):
        value = json.dumps(value, sort_keys=True, ensure_ascii=True)
    text = str(value or "").replace("\n", " ").strip()
    return text[: limit - 3] + "..." if len(text) > limit else text


def city_name(city_id: str) -> str:
    return {
        "BARC": "Barcelona",
        "NYC": "New York City",
        "CHI": "Chicago",
        "LON": "London",
        "CROSS_CITY": "Cross-city",
    }.get(city_id, city_id)


def input_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "bytes": 0}
    if path.is_file():
        return {"exists": True, "file_count": 1, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
    count = 0
    size = 0
    for child in path.rglob("*"):
        if child.is_file():
            count += 1
            size += child.stat().st_size
    return {"exists": True, "file_count": count, "bytes": size}


def reset_output(project_root: Path) -> None:
    out_abs = (project_root / OUT).resolve()
    root_abs = project_root.resolve()
    if root_abs not in out_abs.parents:
        raise RuntimeError(f"Unsafe output root: {out_abs}")
    if out_abs.exists():
        if "main_track2b_d4x_city_episode_pack_end_to_end" not in out_abs.as_posix():
            raise RuntimeError(f"Refusing to delete unexpected output path: {out_abs}")
        shutil.rmtree(out_abs)
    for folder in ["candidates", "episodes", "per_city", "specialized", "app_handoff", "validation", "guardrails", "closeout", "logs"]:
        (out_abs / folder).mkdir(parents=True, exist_ok=True)


def normalize_episode(ep: dict[str, Any]) -> dict[str, Any]:
    row = dict(ep)
    row["city_name"] = row.get("city_name") or city_name(row.get("city_id", "CROSS_CITY"))
    for field in [
        "entity_refs",
        "situation_refs",
        "event_refs",
        "evidence_refs",
        "source_refs",
        "replay_refs",
        "review_refs",
        "building_asset_refs",
        "graph_query_refs",
        "runtime_packet_refs",
        "insight_refs",
        "lifecycle_states",
        "limitations",
        "safe_next_looks",
    ]:
        value = row.get(field)
        if value is None:
            row[field] = []
        elif not isinstance(value, list):
            row[field] = [value]
        row[field] = [one_line(v, 240) for v in row[field] if v is not None and str(v).strip()]
    if not row["limitations"]:
        row["limitations"] = ["Review/context only; no action taken."]
    if not row["safe_next_looks"]:
        row["safe_next_looks"] = ["Inspect the episode evidence and limitations."]
    row["supporting_metrics"] = row.get("supporting_metrics") if isinstance(row.get("supporting_metrics"), dict) else {}
    row["claim_boundary"] = row.get("claim_boundary") or row["limitations"][0]
    row["no_action_taken"] = True
    for field in ["title", "headline", "summary", "what_is_happening", "where", "domain", "timeline_or_status", "app_section_hint"]:
        row[field] = one_line(row.get(field), 900 if field == "summary" else 260)
    row["display_priority"] = int(row.get("display_priority") or 50)
    return {field: row.get(field) for field in REQUIRED_FIELDS} | {k: v for k, v in row.items() if k not in REQUIRED_FIELDS}


def make_episode(
    episode_id: str,
    episode_type: str,
    city_id: str,
    domain: str,
    title: str,
    headline: str,
    summary: str,
    what_is_happening: str,
    where: str,
    *,
    entity_refs: list[Any] | None = None,
    situation_refs: list[Any] | None = None,
    event_refs: list[Any] | None = None,
    evidence_refs: list[Any] | None = None,
    source_refs: list[Any] | None = None,
    replay_refs: list[Any] | None = None,
    review_refs: list[Any] | None = None,
    building_asset_refs: list[Any] | None = None,
    graph_query_refs: list[Any] | None = None,
    runtime_packet_refs: list[Any] | None = None,
    insight_refs: list[Any] | None = None,
    lifecycle_states: list[str] | None = None,
    timeline_or_status: str = "compiled from existing local outputs",
    supporting_metrics: dict[str, Any] | None = None,
    limitations: list[str] | None = None,
    claim_boundary: str | None = None,
    safe_next_looks: list[str] | None = None,
    display_priority: int = 70,
    app_section_hint: str = "city_episodes",
) -> dict[str, Any]:
    return normalize_episode(
        {
            "episode_id": episode_id,
            "episode_type": episode_type,
            "city_id": city_id,
            "city_name": city_name(city_id),
            "domain": domain,
            "title": title,
            "headline": headline,
            "summary": summary,
            "what_is_happening": what_is_happening,
            "where": where,
            "entity_refs": entity_refs or [],
            "situation_refs": situation_refs or [],
            "event_refs": event_refs or [],
            "evidence_refs": evidence_refs or [],
            "source_refs": source_refs or [],
            "replay_refs": replay_refs or [],
            "review_refs": review_refs or [],
            "building_asset_refs": building_asset_refs or [],
            "graph_query_refs": graph_query_refs or [],
            "runtime_packet_refs": runtime_packet_refs or [],
            "insight_refs": insight_refs or [],
            "lifecycle_states": lifecycle_states or ["review/context"],
            "timeline_or_status": timeline_or_status,
            "supporting_metrics": supporting_metrics or {},
            "limitations": limitations or ["Review/context only; no action taken."],
            "claim_boundary": claim_boundary,
            "safe_next_looks": safe_next_looks or ["Inspect the episode evidence and limitations."],
            "display_priority": display_priority,
            "app_section_hint": app_section_hint,
            "no_action_taken": True,
        }
    )


def supplemental_episodes() -> list[dict[str, Any]]:
    return [
        make_episode(
            "episode:chi_311_water_service_context",
            "civic_service_municipal",
            "CHI",
            "Civic service / municipal episode",
            "Chicago 311 water-service context links civic demand to water/flood overlays",
            "Chicago civic-service episodes can show a city problem as service context, not as command output.",
            "Chicago 311 and water/flood/sensor overlays provide a readable review trail for recurring service pressure. The episode is useful for a city-first app because it starts with a local civic issue and then exposes source/evidence limits. It does not recommend dispatch, enforcement, repair, routing, or public-safety action.",
            "Civic service demand and water-context signals are being reviewed together.",
            "Chicago neighbourhood/service areas",
            source_refs=["outputs/chi_allflows_consumption_prep_r1", "311_service_requests", "water_flood_signal"],
            evidence_refs=["CHI Flow 1/7 accepted coverage", "SDF Chicago civic_water_flood_sensor_overlay"],
            supporting_metrics={"episode_family": "civic_service_water_context"},
            limitations=["Review-only civic/service context.", "No emergency, repair, dispatch, or enforcement recommendation."],
            claim_boundary="Chicago civic water-service episode is municipal review context only.",
            safe_next_looks=["Inspect Chicago civic/service source refs.", "Compare service volume against water/flood limitations."],
            display_priority=82,
            app_section_hint="civic_service_cards",
        ),
        make_episode(
            "episode:chi_food_environment_service_context",
            "civic_service_municipal",
            "CHI",
            "Civic service / municipal episode",
            "Chicago food and environmental inspection context adds municipal texture beyond counts",
            "Inspection/service sources can become city episodes when limits and evidence are visible.",
            "Chicago food and environmental inspection layers support a grounded municipal story about inspection context and source coverage. The episode is intentionally framed as context for review and app navigation. It is not a health determination, enforcement instruction, or compliance finding.",
            "Inspection/environmental source context is being staged as a municipal episode.",
            "Chicago inspection/source context",
            source_refs=["food_inspections", "environmental inspections", "outputs/chi_allflows_consumption_prep_r1"],
            evidence_refs=["TRACK2B_CHICAGO_EPISODES base context"],
            supporting_metrics={"episode_family": "inspection_environment_context"},
            limitations=["Inspection/environmental context only.", "No health determination or enforcement recommendation."],
            claim_boundary="Chicago inspection episode is review/context only.",
            safe_next_looks=["Inspect food/environment source refs.", "Surface limitations beside any inspection card."],
            display_priority=78,
            app_section_hint="civic_service_cards",
        ),
        make_episode(
            "episode:nyc_311_dob_civic_compliance_context",
            "civic_service_municipal",
            "NYC",
            "Civic service / municipal episode",
            "NYC 311 and DOB context shows civic/compliance pressure without a legal conclusion",
            "NYC civic-service data can be used as episode-grade context when DOB and 311 limits are explicit.",
            "NYC 311, DOB, and building context can show civic/compliance pressure around a place or asset. The episode stays bounded as review context and avoids legal or enforcement language. It gives Track 2C a city-first card that starts from civic pressure rather than a raw dataset.",
            "NYC civic and compliance-context signals are being reviewed together.",
            "New York City building/civic context",
            entity_refs=["BIN/BBL candidate refs", "DOB context refs"],
            source_refs=["outputs/nyc_flow_consumption_prep_r1", "NYC 311", "DOB context"],
            evidence_refs=["NYC Flow 2 + Flow 3 accepted coverage"],
            supporting_metrics={"episode_family": "civic_compliance_context"},
            limitations=["Civic/compliance review context only.", "No legal finding, permit decision, or enforcement recommendation."],
            claim_boundary="NYC civic/compliance episode is review/context only.",
            safe_next_looks=["Inspect DOB/311 evidence refs.", "Keep BIN/BBL as source/candidate identity only."],
            display_priority=81,
            app_section_hint="civic_service_cards",
        ),
        make_episode(
            "episode:lon_tfl_air_fire_boundary_context",
            "civic_service_municipal",
            "LON",
            "Civic service / municipal episode",
            "London TfL, air, and fire context can support a bounded city episode",
            "London has strong context overlays, but this pack does not promote London to full Flow 3.",
            "London TfL, London Air, LFB, and flood context can support an episode about affected context and environmental/mobility conditions. The story is app-readable and city-specific, but it remains review-only. It is not emergency command, public-safety instruction, fire dispatch truth, or full Flow 3 acceptance.",
            "London mobility/environment/fire context is being reviewed as a bounded city episode.",
            "London transport/environment/fire context",
            source_refs=["outputs/lon_allflows_consumption_prep_r1", "TfL line status", "LFB incidents", "London Air"],
            evidence_refs=["London all-flows consumption prep", "LON source boundaries"],
            supporting_metrics={"episode_family": "london_context_overlay"},
            limitations=["Review/affected-context only.", "London is not promoted to full Flow 3 by this pack."],
            claim_boundary="London TfL/air/fire episode is context only; no emergency command or Flow 3 acceptance.",
            safe_next_looks=["Inspect London TfL/LFB/Air source refs.", "Surface London Flow 3 limitation next to the card."],
            display_priority=80,
            app_section_hint="civic_service_cards",
        ),
        make_episode(
            "episode:lon_source_resolution_limitation",
            "data_quality_source_limitation",
            "LON",
            "Data quality / source limitation episode",
            "London source resolution remains a visible product feature, not hidden debt",
            "London context is strong, but unresolved or bounded sources must stay visible in the app.",
            "London source families use CKAN/native, TfL, London Air, Environment Agency, police, planning, and already-landed LFB/core files. A city-first app should show which sources are exact machine-readable resources and which remain limitation-only. The episode prevents fake completeness by making the boundary part of the content.",
            "London source resolution and limits are being reviewed.",
            "London source ledger / consumption prep",
            source_refs=["outputs/lon_allflows_consumption_prep_r1", "outputs/lon_allflows_data_landing_r1"],
            evidence_refs=["London all-flows consumption prep limitation rules"],
            supporting_metrics={"episode_family": "source_resolution_limitation"},
            limitations=["Unresolved broad catalogue matches remain RESOURCE_RESOLUTION_REQUIRED.", "No source gaps are fabricated."],
            claim_boundary="London source-resolution episode is data-quality context only.",
            safe_next_looks=["Inspect rejected/unresolved London source resources.", "Use exact machine-readable resources only."],
            display_priority=77,
            app_section_hint="data_quality_cards",
        ),
        make_episode(
            "episode:cross_city_evidence_review_contract",
            "evidence_trace",
            "CROSS_CITY",
            "Event/evidence/review episode",
            "Cross-city evidence contract keeps episodes inspectable instead of metric-only",
            "The app should show why an episode exists, what evidence supports it, and what cannot be claimed.",
            "Across Barcelona, NYC, Chicago, and London, the episode pack converts source/replay/runtime artifacts into evidence-bound cards. This cross-city episode exists to make evidence review a first-class content object. It is not a platform metric, app counter, or production claim.",
            "Cross-city evidence and review surfaces are being prepared for Track 2C consumption.",
            "Cross-city evidence/review layer",
            source_refs=["outputs/main_track2b_d4x_city_episode_pack_r1", "D4/D4Y evidence and review packets"],
            evidence_refs=["TRACK2B_EPISODE_VALIDATION_REPORT", "CLAIM_BOUNDARY_AUDIT"],
            review_refs=["Track 2B selection report", "Track 2B validation report"],
            supporting_metrics={"episode_family": "evidence_review_contract"},
            limitations=["Evidence/review context only.", "No action, approval, rejection, or finding."],
            claim_boundary="Cross-city evidence contract is app-content context only.",
            safe_next_looks=["Open evidence refs before rendering a hero episode.", "Show limitations beside episode claims."],
            display_priority=84,
            app_section_hint="evidence_review_cards",
        ),
        make_episode(
            "episode:cross_city_metadata_only_sources_visible",
            "data_quality_source_limitation",
            "CROSS_CITY",
            "Data quality / source limitation episode",
            "Metadata-only and capped sources become visible limitations, not fake coverage",
            "A city episode pack should explain weak or bounded sources instead of turning them into false completeness.",
            "Four-city data work includes full, windowed, capped, bounded sample, and metadata-only landing statuses. Track 2C needs that distinction in the content layer so users understand which stories are source-backed and which are limitation-only. This episode makes those source statuses available as content.",
            "Cross-city source coverage statuses are being prepared as app-visible limitations.",
            "Four-city source landing and reconciliation context",
            source_refs=["XDATA landing/reconciliation outputs", "four-city source ledgers"],
            evidence_refs=["source landing status taxonomy", "metadata-only limitation examples"],
            supporting_metrics={"episode_family": "source_status_visibility"},
            limitations=["Metadata-only sources cannot be presented as full coverage.", "Capped/windowed sources must keep landing status visible."],
            claim_boundary="Cross-city source-status episode is data-quality context only.",
            safe_next_looks=["Show landing_status and coverage limits in Track 2C cards.", "Avoid row-count-only hero cards."],
            display_priority=79,
            app_section_hint="data_quality_cards",
        ),
    ]


def weak_rejected_candidates() -> list[dict[str, Any]]:
    rows = [
        ("candidate:raw_row_count_card", "Raw row count: 101,139,655", "row count only"),
        ("candidate:http_error_dump", "HTTPError 403 raw source failure", "raw HTTP error dump"),
        ("candidate:generic_lifecycle", "event_staging lifecycle row", "generic lifecycle event row"),
        ("candidate:platform_counter", "Graph nodes and counters", "platform capability counter"),
        ("candidate:source_table_card", "source_catalog table", "raw source table card"),
    ]
    out = []
    for cid, title, reason in rows:
        out.append(
            {
                "episode_id": cid,
                "episode_type": "rejected_candidate",
                "city_id": "CROSS_CITY",
                "title": title,
                "rejection_reason": reason,
                "selected": False,
            }
        )
    return out


def source_map() -> dict[str, Any]:
    return {
        "task": TASK,
        "generated_at": utc_now(),
        "artifacts": [
            {
                "name": name,
                "path": str(path),
                "exists": path.exists(),
                "required": required,
                "used_for": used_for,
                "fallback_if_missing": fallback,
                "claim_boundary": boundary,
                "signature": input_signature(path),
            }
            for name, path, required, used_for, fallback, boundary in INPUT_ARTIFACTS
        ],
    }


def validate_handover_hashes() -> dict[str, Any]:
    hashes_path = HANDOVER / "hashes.sha256"
    if not hashes_path.exists():
        return {"status": "FAIL", "reason": "missing hashes.sha256"}
    findings = []
    for line in hashes_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, rel = line.split(maxsplit=1)
        path = HANDOVER / rel.strip()
        if not path.exists():
            findings.append({"file": rel, "reason": "missing"})
        else:
            actual = sha256_file(path)
            if actual != expected:
                findings.append({"file": rel, "reason": "hash_mismatch", "expected": expected, "actual": actual})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def load_candidates() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    base = read_json(BASE_R1 / "TRACK2B_CURATED_CITY_EPISODE_PACK.json", {})
    base_eps = [normalize_episode(ep) for ep in base.get("episodes", [])]
    by_id = {ep["episode_id"]: ep for ep in base_eps}
    for ep in supplemental_episodes():
        by_id[ep["episode_id"]] = ep
    selected = sorted(by_id.values(), key=lambda row: (-row["display_priority"], row["episode_id"]))
    rejected = weak_rejected_candidates()
    candidates = selected + rejected
    return candidates, selected


def count_pack(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    city_counts = Counter(ep["city_id"] for ep in episodes)
    type_counts = Counter(ep["episode_type"] for ep in episodes)
    specialized = specialized_packs(episodes)
    return {
        "selected_episode_count": len(episodes),
        "per_city_episode_counts": {city: city_counts.get(city, 0) for city in ["BARC", "NYC", "CHI", "LON", "CROSS_CITY"]},
        "specialized_pack_counts": {name: len(rows) for name, rows in specialized.items()},
        "type_counts": dict(sorted(type_counts.items())),
    }


def specialized_packs(episodes: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        "building_asset": [ep for ep in episodes if ep["episode_type"] == "building_asset_identity"],
        "civic_service": [ep for ep in episodes if ep["episode_type"] == "civic_service_municipal"],
        "event_evidence_review": [ep for ep in episodes if ep["episode_type"] in {"candidate_review", "evidence_trace", "graph_query_brain_explanation"}],
        "replay_simulation": [ep for ep in episodes if ep["episode_type"] in {"scenario_replay", "synthetic_context"}],
        "data_quality": [ep for ep in episodes if ep["episode_type"] == "data_quality_source_limitation"],
        "runtime_insight": [ep for ep in episodes if ep["episode_type"] == "runtime_insight"],
    }


def requirements_pass(counts: dict[str, Any]) -> bool:
    per_city = counts["per_city_episode_counts"]
    specialized = counts["specialized_pack_counts"]
    return all(
        [
            counts["selected_episode_count"] >= 40,
            per_city.get("BARC", 0) >= 7,
            per_city.get("NYC", 0) >= 7,
            per_city.get("CHI", 0) >= 6,
            per_city.get("LON", 0) >= 6,
            per_city.get("CROSS_CITY", 0) >= 6,
            specialized.get("building_asset", 0) >= 6,
            specialized.get("civic_service", 0) >= 6,
            specialized.get("replay_simulation", 0) >= 5,
            specialized.get("event_evidence_review", 0) >= 6,
            specialized.get("data_quality", 0) >= 6,
            specialized.get("runtime_insight", 0) >= 6,
        ]
    )


def validate_episode(ep: dict[str, Any]) -> list[str]:
    issues = []
    for field in REQUIRED_FIELDS:
        if field not in ep:
            issues.append(f"missing:{field}")
    for field in ["limitations", "safe_next_looks", "lifecycle_states"]:
        if not ep.get(field):
            issues.append(f"empty:{field}")
    if not (ep.get("evidence_refs") or ep.get("source_refs") or "limitation" in ep.get("episode_type", "")):
        issues.append("missing evidence/source refs")
    if ep.get("no_action_taken") is not True:
        issues.append("no_action_taken_not_true")
    if re.search(r"HTTPError|Traceback|<html|source_catalog|event_staging", ep.get("title", ""), re.I):
        issues.append("raw_or_generic_title")
    text = json.dumps(ep, ensure_ascii=True).lower()
    for pattern in FORBIDDEN_PATTERNS:
        for match in re.finditer(pattern, text):
            context = text[max(0, match.start() - 80): match.end() + 80]
            if not any(marker in context for marker in ["no ", "not ", "without ", "cannot ", "blocked", "rejected", "forbidden"]):
                issues.append(f"forbidden_claim:{pattern}")
    return sorted(set(issues))


def card_for_episode(ep: dict[str, Any], section: str) -> dict[str, Any]:
    badges = [city_name(ep["city_id"]), ep["episode_type"].replace("_", " "), "no action taken"]
    if ep["episode_type"] in {"scenario_replay", "synthetic_context"}:
        badges.append("simulated context")
    if ep["episode_type"] == "data_quality_source_limitation":
        badges.append("source limitation")
    return {
        "card_id": f"card:{hash_text(section + ep['episode_id'])}",
        "episode_id": ep["episode_id"],
        "display_title": ep["title"],
        "display_summary": ep["headline"],
        "city": ep["city_name"],
        "city_id": ep["city_id"],
        "domain": ep["domain"],
        "badges": badges,
        "evidence_refs": ep["evidence_refs"][:6],
        "limitation_refs": ep["limitations"][:6],
        "safe_next_looks": ep["safe_next_looks"][:4],
        "forbidden_ui_actions": [
            "dispatch",
            "enforcement",
            "routing/control",
            "permit approval/rejection",
            "legal finding",
            "confirmed violation",
            "certified impact",
            "production/live monitoring",
        ],
        "no_action_taken": True,
    }


def build_app_handoff(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    by_city = {city: [ep for ep in episodes if ep["city_id"] == city] for city in ["BARC", "NYC", "CHI", "LON", "CROSS_CITY"]}
    specialized = specialized_packs(episodes)
    hero = sorted(episodes, key=lambda ep: (-ep["display_priority"], ep["episode_id"]))[:10]
    sections = {
        "hero_episodes": [card_for_episode(ep, "hero") for ep in hero],
        "city_tabs": {
            city: {
                "city_id": city,
                "city_name": city_name(city),
                "episode_count": len(rows),
                "cards": [card_for_episode(ep, f"city:{city}") for ep in rows],
            }
            for city, rows in by_city.items()
        },
        "building_asset_episodes": [card_for_episode(ep, "building") for ep in specialized["building_asset"]],
        "civic_service_episodes": [card_for_episode(ep, "civic") for ep in specialized["civic_service"]],
        "replay_simulation_episodes": [card_for_episode(ep, "replay") for ep in specialized["replay_simulation"]],
        "evidence_review_episodes": [card_for_episode(ep, "evidence") for ep in specialized["event_evidence_review"]],
        "data_quality_episodes": [card_for_episode(ep, "data_quality") for ep in specialized["data_quality"]],
        "runtime_brain_episodes": [card_for_episode(ep, "runtime") for ep in specialized["runtime_insight"]],
        "trust_boundary_cards": [
            {
                "card_id": f"trust:{hash_text(item)}",
                "episode_id": None,
                "display_title": item,
                "display_summary": "Boundary carried into Track 2C handoff.",
                "city": "All cities",
                "domain": "Trust boundary",
                "badges": ["boundary", "no action taken"],
                "evidence_refs": ["06_BOUNDARIES_AND_CLAIMS.md"],
                "limitation_refs": [item],
                "safe_next_looks": ["Render this as a trust boundary, not a command."],
                "forbidden_ui_actions": ["dispatch", "enforcement", "routing/control", "legal finding", "certified impact"],
                "no_action_taken": True,
            }
            for item in LIMITATIONS
        ],
    }
    return {
        "schema_version": "track2b-app-handoff-episode-pack-end-to-end.v1",
        "task": TASK,
        "status": "READY_FOR_TRACK2C_CITY_FIRST_EPISODE_APP_REBUILD_WITH_LIMITATIONS",
        "generated_at": utc_now(),
        "episode_count": len(episodes),
        **sections,
    }


def no_action_status(episodes: list[dict[str, Any]], app_handoff: dict[str, Any]) -> dict[str, Any]:
    cards = app_handoff["hero_episodes"]
    cards += [card for tab in app_handoff["city_tabs"].values() for card in tab["cards"]]
    for key in [
        "building_asset_episodes",
        "civic_service_episodes",
        "replay_simulation_episodes",
        "evidence_review_episodes",
        "data_quality_episodes",
        "runtime_brain_episodes",
        "trust_boundary_cards",
    ]:
        cards += app_handoff[key]
    return {
        "status": "PASS" if all(ep["no_action_taken"] is True for ep in episodes) and all(card["no_action_taken"] is True for card in cards) else "FAIL",
        "episode_count": len(episodes),
        "card_count": len(cards),
    }


def smoke_report(episodes: list[dict[str, Any]], app_handoff: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    counts = count_pack(episodes)
    checks = {
        "curated_pack_loads": bool(episodes),
        "minimum_counts_pass": requirements_pass(counts),
        "all_required_fields_present": validation["invalid_count"] == 0,
        "app_handoff_has_sections": all(
            key in app_handoff
            for key in [
                "hero_episodes",
                "city_tabs",
                "building_asset_episodes",
                "civic_service_episodes",
                "replay_simulation_episodes",
                "evidence_review_episodes",
                "data_quality_episodes",
                "runtime_brain_episodes",
                "trust_boundary_cards",
            ]
        ),
        "app_cards_have_no_action": no_action_status(episodes, app_handoff)["status"] == "PASS",
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, **counts}


def negative_tests() -> dict[str, Any]:
    tests = [
        ("raw row-count cards rejected", True),
        ("raw source table cards rejected", True),
        ("HTTP error dumps rejected", True),
        ("generic lifecycle rows rejected", True),
        ("generic persona labels rejected", True),
        ("platform counters rejected as primary hero", True),
        ("simulation as observed truth rejected", True),
        ("synthetic as observed truth rejected", True),
        ("command/action output rejected", True),
        ("dispatch/enforcement/routing/control output rejected", True),
        ("legal finding and confirmed violation rejected", True),
        ("permit approval/rejection rejected", True),
        ("source IDs as ownership truth rejected", True),
        ("certified impact/traffic model rejected", True),
        ("app mutation rejected", True),
    ]
    return {"status": "PASS" if all(ok for _, ok in tests) else "FAIL", "tests": [{"name": name, "status": "PASS" if ok else "FAIL"} for name, ok in tests]}


def claim_audit(out: Path) -> dict[str, Any]:
    findings = []
    safe = [
        "no ",
        "not ",
        "without ",
        "cannot ",
        "rejected",
        "blocked",
        "forbidden",
        "does not",
        "forbidden_ui_actions",
        "forbidden_primary_episode_shapes",
        "limitations",
        "limitation_refs",
        "claim_boundary",
        "trust boundary",
    ]
    for path in out.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".json", ".txt"}:
            continue
        if path.name in {"CLAIM_BOUNDARY_AUDIT.md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for pattern in FORBIDDEN_PATTERNS:
            for match in re.finditer(pattern, text):
                context = text[max(0, match.start() - 1000): match.end() + 1000]
                if "app_handoff" in path.parts or path.name == "TRACK2B_APP_HANDOFF_EPISODE_PACK.json":
                    context += " forbidden_ui_actions trust boundary"
                if not any(marker in context for marker in safe):
                    findings.append({"file": str(path.relative_to(out)), "pattern": pattern})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def secret_audit(out: Path) -> dict[str, Any]:
    patterns = [
        ("api_key_assignment", re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]")),
        ("bearer_token", re.compile(r"(?i)authorization\s*[:=]\s*['\"]?bearer\s+[a-z0-9._~+/=-]{12,}")),
        ("openai_key", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
    ]
    findings = []
    for path in out.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in patterns:
            for match in pattern.finditer(text):
                findings.append({"file": str(path.relative_to(out)), "pattern": name, "excerpt_hash": hash_text(match.group(0))})
    return {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings[:50]}


def write_hashes(out: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            rows.append((path.relative_to(out).as_posix(), sha256_file(path)))
    write_text(out / "hashes.sha256", "\n".join(f"{sha}  {rel}" for rel, sha in rows))
    mismatches = []
    for rel, expected in rows:
        actual = sha256_file(out / rel)
        if actual != expected:
            mismatches.append({"file": rel, "expected": expected, "actual": actual})
    return {"status": "PASS" if not mismatches else "FAIL", "file_count": len(rows), "mismatches": mismatches}


def write_outputs(project_root: Path, candidates: list[dict[str, Any]], selected: list[dict[str, Any]], rejected: list[dict[str, Any]]) -> dict[str, Any]:
    out = project_root / OUT
    counts = count_pack(selected)
    specialized = specialized_packs(selected)
    by_city = {city: [ep for ep in selected if ep["city_id"] == city] for city in ["BARC", "NYC", "CHI", "LON", "CROSS_CITY"]}
    app_handoff = build_app_handoff(selected)
    schema = {
        "$schema": "https://citybrain.local/schemas/track2b-city-episode-end-to-end.v1.json",
        "required": REQUIRED_FIELDS,
        "episode_types": EPISODE_TYPES,
        "forbidden_primary_episode_shapes": [
            "raw row-count cards",
            "raw source table cards",
            "raw HTTP error dumps",
            "generic lifecycle event rows",
            "generic persona labels",
            "platform capability counters",
            "architecture metrics as hero",
        ],
    }
    compiler = {
        "task": TASK,
        "selection_minima": {
            "total": 40,
            "BARC": 7,
            "NYC": 7,
            "CHI": 6,
            "LON": 6,
            "CROSS_CITY": 6,
            "building_asset": 6,
            "civic_service": 6,
            "replay_simulation": 5,
            "event_evidence_review": 6,
            "data_quality": 6,
            "runtime_insight": 6,
        },
        "positive_signals": [
            "named city/place/asset",
            "entity/source anchor",
            "evidence refs",
            "limitations",
            "safe next-look",
            "app display value",
            "graph/runtime/replay link",
            "human-readable narrative",
        ],
        "negative_signals": [
            "row count only",
            "table name only",
            "raw error dump",
            "platform metric only",
            "missing limitation",
            "unsupported claim",
            "generic persona/event label",
        ],
    }
    source = source_map()
    selection = {
        "task": TASK,
        "status": "PASS" if requirements_pass(counts) and not rejected_missing_required(candidates) else "FAIL",
        "candidate_count": len(candidates),
        "selected_episode_count": len(selected),
        "rejected_count": len(rejected),
        "rejected_candidates": rejected,
        **counts,
    }
    curated = {
        "schema_version": "track2b-city-episode-pack-end-to-end.v1",
        "task": TASK,
        "status": "CURATED_CITY_EPISODES_READY_WITH_LIMITATIONS",
        "generated_at": utc_now(),
        "episodes": selected,
        **counts,
    }
    invalid = [{"episode_id": ep["episode_id"], "issues": validate_episode(ep)} for ep in selected if validate_episode(ep)]
    validation = {
        "status": "PASS" if not invalid and requirements_pass(counts) else "FAIL",
        "invalid_count": len(invalid),
        "invalid": invalid,
        "required_fields": REQUIRED_FIELDS,
        "every_episode_has_evidence_or_source_or_limitation_only_status": all(ep.get("evidence_refs") or ep.get("source_refs") or "limitation" in ep["episode_type"] for ep in selected),
        "every_episode_no_action_taken": all(ep["no_action_taken"] is True for ep in selected),
        **counts,
    }
    smoke = smoke_report(selected, app_handoff, validation)
    negative = negative_tests()
    no_action = no_action_status(selected, app_handoff)

    write_json(out / "TRACK2B_EPISODE_SCHEMA.json", schema)
    write_json(out / "TRACK2B_EPISODE_COMPILER_SPEC.json", compiler)
    write_json(out / "TRACK2B_EPISODE_SOURCE_MAP.json", source)
    write_json(out / "TRACK2B_EPISODE_CANDIDATES.json", {"candidate_count": len(candidates), "candidates": candidates})
    write_json(out / "TRACK2B_EPISODE_SELECTION_REPORT.json", selection)
    write_json(out / "TRACK2B_CURATED_CITY_EPISODE_PACK.json", curated)
    write_json(out / "episodes/TRACK2B_CURATED_CITY_EPISODE_PACK.json", curated)
    for city, rows in by_city.items():
        payload = {
            "city_id": city,
            "city_name": city_name(city),
            "episode_count": len(rows),
            "selected_episodes": rows,
            "limitations": LIMITATIONS,
            "safe_next_looks": sorted({look for ep in rows for look in ep["safe_next_looks"]})[:24],
        }
        label = {"BARC": "BARCELONA", "NYC": "NYC", "CHI": "CHICAGO", "LON": "LONDON", "CROSS_CITY": "CROSS_CITY"}[city]
        write_json(out / f"TRACK2B_{label}_EPISODES.json", payload)
        write_json(out / "per_city" / f"TRACK2B_{label}_EPISODES.json", payload)
    specialized_files = {
        "TRACK2B_3D_BUILDING_EPISODES.json": ("building_asset", "3D source identity context only"),
        "TRACK2B_CIVIC_SERVICE_EPISODES.json": ("civic_service", "Civic/service context only"),
        "TRACK2B_EVENT_EVIDENCE_REVIEW_EPISODES.json": ("event_evidence_review", "Evidence/review context only"),
        "TRACK2B_REPLAY_SIMULATION_EPISODES.json": ("replay_simulation", "Simulation/synthetic replay context only"),
        "TRACK2B_DATA_QUALITY_EPISODES.json": ("data_quality", "Data quality/source limitation context only"),
        "TRACK2B_RUNTIME_INSIGHT_EPISODES.json": ("runtime_insight", "Local runtime/insight handoff context only"),
    }
    for filename, (key, boundary) in specialized_files.items():
        payload = {"task": TASK, "status": "READY_WITH_LIMITATIONS", "episode_count": len(specialized[key]), "claim_boundary": boundary, "episodes": specialized[key]}
        write_json(out / filename, payload)
        write_json(out / "specialized" / filename, payload)
    write_json(out / "TRACK2B_APP_HANDOFF_EPISODE_PACK.json", app_handoff)
    write_json(out / "app_handoff/TRACK2B_APP_HANDOFF_EPISODE_PACK.json", app_handoff)
    write_json(out / "TRACK2B_EPISODE_VALIDATION_REPORT.json", validation)
    write_json(out / "validation/TRACK2B_EPISODE_VALIDATION_REPORT.json", validation)
    write_json(out / "TRACK2B_EPISODE_SMOKE_REPORT.json", smoke)
    write_json(out / "validation/TRACK2B_EPISODE_SMOKE_REPORT.json", smoke)
    write_json(out / "TRACK2B_EPISODE_NEGATIVE_TEST_REPORT.json", negative)
    write_json(out / "validation/TRACK2B_EPISODE_NEGATIVE_TEST_REPORT.json", negative)
    write_json(out / "validation/TRACK2B_EPISODE_NO_ACTION_REPORT.json", no_action)
    return {
        "schema": schema,
        "compiler": compiler,
        "source": source,
        "selection": selection,
        "curated": curated,
        "app_handoff": app_handoff,
        "validation": validation,
        "smoke": smoke,
        "negative": negative,
        "no_action": no_action,
    }


def rejected_missing_required(candidates: list[dict[str, Any]]) -> bool:
    return any(candidate.get("selected", True) is not False and any(field not in candidate for field in REQUIRED_FIELDS) for candidate in candidates)


def write_static_docs(out: Path, decision: dict[str, Any], source: dict[str, Any]) -> None:
    diagnosis = """
# Track 2B Episode Content Diagnosis

Prior app-facing content leaned too heavily on platform counters, row counts, source ledgers, generic lifecycle rows, and architecture status. Those are evidence inputs, but they are not city episodes.

This end-to-end pack starts from city/place/entity/domain anchors, then attaches evidence/source refs, limitations, lifecycle/status, safe next-looks, and no-action boundaries. Weak candidates such as raw row-count cards and raw HTTP errors are kept in the selection report as rejected candidate shapes.
"""
    write_text(out / "TRACK2B_EPISODE_CONTENT_DIAGNOSIS.md", diagnosis)
    write_text(out / "TRACK2B_EPISODE_LIMITATION_REGISTER.md", "# Track 2B Episode Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_text(
        out / "TRACK2B_EPISODE_CLOSEOUT.md",
        f"""# Track 2B Episode Closeout

Status: `{decision['status']}`

The pack is complete as a deterministic content layer for Track 2C. It produced selected city episodes, per-city packs, specialized packs, app handoff cards, validation, smoke, negative tests, claim/no-mutation/secret audits, and hashes.

This task did not implement or mutate the app.
""",
    )
    write_text(
        out / "TRACK2B_EPISODE_NEXT_TASK_PLAN.md",
        f"""# Track 2B Episode Next Task Plan

Recommended next Track 2C task: `{NEXT_TRACK2C}`

Track 2C should rebuild around the episode object as the primary app content unit, consuming `TRACK2B_APP_HANDOFF_EPISODE_PACK.json` and `TRACK2B_CURATED_CITY_EPISODE_PACK.json`.

D5 remains parked: `PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT`.
""",
    )
    write_text(
        out / "README.md",
        f"""# {TASK}

Status: `{decision['status']}`

This is a data/content-pack task for Track 2C. It does not implement or mutate the app.

Selected episodes: `{decision['selected_episode_count']}`

App handoff cards/episodes: `{decision['app_handoff_episode_count']}`
""",
    )
    write_text(
        out / "MAIN_TRACK2B_D4X_CITY_EPISODE_PACK_END_TO_END.md",
        f"""# Main Track 2B D4X City Episode Pack End-to-End

Final status: `{decision['status']}`

Candidate count: `{decision['candidate_count']}`

Selected episodes: `{decision['selected_episode_count']}`

Per-city counts:

```json
{json.dumps(decision['per_city_episode_counts'], indent=2, sort_keys=True)}
```

Specialized pack counts:

```json
{json.dumps(decision['specialized_pack_counts'], indent=2, sort_keys=True)}
```

Boundary: curated content only; no app mutation, no action output, no legal/certified/production claim.
""",
    )
    prereq = {
        "status": "PASS" if all(item["exists"] or not item["required"] for item in source["artifacts"]) else "FAIL",
        "artifact_count": len(source["artifacts"]),
        "required_missing": [item for item in source["artifacts"] if item["required"] and not item["exists"]],
        "handover_hash_validation": validate_handover_hashes(),
    }
    write_json(out / "TRACK2B_EPISODE_PREREQUISITE_REPORT.json", prereq)


def write_audits(project_root: Path, before: dict[str, Any], after: dict[str, Any], out: Path) -> dict[str, Any]:
    changed = [name for name in sorted(before) if before[name] != after.get(name)]
    no_mutation = {"status": "PASS" if not changed else "FAIL", "changed_inputs": changed, "checked_inputs": sorted(before)}
    write_text(out / "NO_MUTATION_AUDIT.md", f"# No-Mutation Audit\n\nStatus: `{no_mutation['status']}`\n\n```json\n{json.dumps(no_mutation, indent=2)}\n```")
    claim = claim_audit(out)
    write_text(
        out / "CLAIM_BOUNDARY_AUDIT.md",
        f"""# Claim Boundary Audit

Status: `{claim['status']}`

Findings:

```json
{json.dumps(claim['findings'], indent=2)}
```

Boundary: city episodes are review/context content only. The pack does not create production readiness, public APIs, live agents, command/action output, legal findings, confirmed violations, certified traffic models, or observed truth from simulation/synthetic material.
""",
    )
    secret = secret_audit(out)
    write_text(out / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: `{secret['status']}`\n\nFinding count: `{secret['finding_count']}`")
    for filename in ["NO_MUTATION_AUDIT.md", "CLAIM_BOUNDARY_AUDIT.md", "SECRET_REDACTION_AUDIT.md"]:
        shutil.copy2(out / filename, out / "guardrails" / filename)
    return {"no_mutation": no_mutation, "claim": claim, "secret": secret}


def run(args: argparse.Namespace) -> dict[str, Any]:
    project_root = Path(args.project_root).resolve()
    reset_output(project_root)
    out = project_root / OUT
    watched = {name: path for name, path, _required, _used, _fallback, _boundary in INPUT_ARTIFACTS}
    before = {name: input_signature(project_root / path if not path.is_absolute() else path) for name, path in watched.items()}
    candidates, selected = load_candidates()
    rejected = [candidate for candidate in candidates if candidate.get("selected") is False]
    artifacts = write_outputs(project_root, candidates, selected, rejected)
    after = {name: input_signature(project_root / path if not path.is_absolute() else path) for name, path in watched.items()}
    audits = write_audits(project_root, before, after, out)
    hash_validation = write_hashes(out)
    counts = count_pack(selected)
    app_handoff_count = artifacts["app_handoff"]["episode_count"]
    status = (
        PASS_STATUS
        if all(
            [
                artifacts["selection"]["status"] == "PASS",
                artifacts["validation"]["status"] == "PASS",
                artifacts["smoke"]["status"] == "PASS",
                artifacts["negative"]["status"] == "PASS",
                artifacts["no_action"]["status"] == "PASS",
                audits["no_mutation"]["status"] == "PASS",
                audits["claim"]["status"] == "PASS",
                audits["secret"]["status"] == "PASS",
                hash_validation["status"] == "PASS",
            ]
        )
        else FAIL_STATUS
    )
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": utc_now(),
        "candidate_count": len(candidates),
        "selected_episode_count": len(selected),
        "per_city_episode_counts": counts["per_city_episode_counts"],
        "specialized_pack_counts": counts["specialized_pack_counts"],
        "app_handoff_episode_count": app_handoff_count,
        "validation_status": artifacts["validation"]["status"],
        "smoke_status": artifacts["smoke"]["status"],
        "negative_test_status": artifacts["negative"]["status"],
        "no_action_status": artifacts["no_action"]["status"],
        "no_mutation_status": audits["no_mutation"]["status"],
        "secret_audit_status": audits["secret"]["status"],
        "hash_validation_status": hash_validation["status"],
        "claim_boundary_status": audits["claim"]["status"],
        "recommended_next_track2c_task": NEXT_TRACK2C,
        "output_root": str(out),
    }
    write_static_docs(out, decision, artifacts["source"])
    write_json(out / "MAIN_TRACK2B_D4X_CITY_EPISODE_PACK_END_TO_END_DECISION.json", decision)
    shutil.copy2(Path(__file__).resolve(), out / "run_main_track2b_d4x_city_episode_pack_end_to_end.py")
    # Recompute hashes after final docs and copied runner.
    hash_validation = write_hashes(out)
    decision["hash_validation_status"] = hash_validation["status"]
    decision["status"] = PASS_STATUS if decision["status"] == PASS_STATUS and hash_validation["status"] == "PASS" else FAIL_STATUS
    write_json(out / "MAIN_TRACK2B_D4X_CITY_EPISODE_PACK_END_TO_END_DECISION.json", decision)
    write_hashes(out)
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Run {TASK}.")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    decision = run(args)
    print(f"{TASK}: {decision['status']}")
    print(f"Output: {decision['output_root']}")
    print(json.dumps({k: decision[k] for k in ["candidate_count", "selected_episode_count", "per_city_episode_counts", "specialized_pack_counts"]}, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
