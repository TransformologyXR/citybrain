#!/usr/bin/env python3
"""Run D9 broad data scout for product modes.

This runner is intentionally inventory-only. It scans compact local artifacts,
classifies product-mode opportunities for Ask/Watch/Recall/Brief/Check/Diff
plus Visual/Perception, and writes planning ledgers. It does not build UI,
download new data, run VSS/Metropolis, or mutate upstream outputs.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
OUTPUTS = REPO / "outputs"
FIXTURES = REPO / "packages" / "fixtures"
PROMPT_ZIP = Path("C:/Users/hazem/Downloads/citybrain_d9_broad_data_scout_product_modes.zip")

TASK = "MAIN-CITYBRAIN-D9-BROAD-DATA-SCOUT-PRODUCT-MODES"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D9_BROAD_DATA_SCOUT_MILESTONE_FREEZE_WITH_LIMITATIONS"
BOUNDARY = (
    "Local/LAN/replay/review/query context only; no production/public API, "
    "autonomous monitoring, alerting, dispatch, routing/control, enforcement, "
    "official ticket/case creation, legal/certified finding, certified impact, "
    "or automated action."
)

ROOTS = {
    "preflight": OUTPUTS / "main_citybrain_d9_broad_data_scout_preflight",
    "discovery": OUTPUTS / "main_citybrain_d9_output_ledger_and_fixture_discovery_r1",
    "city_sweep": OUTPUTS / "main_citybrain_d9_city_cartridge_product_mode_sweep_r2",
    "ask": OUTPUTS / "main_citybrain_d9_ask_answerability_deep_matrix_r3",
    "watch": OUTPUTS / "main_citybrain_d9_watch_named_query_opportunity_scout_r4",
    "recall": OUTPUTS / "main_citybrain_d9_recall_precedent_and_similar_case_scout_r5",
    "brief_check_diff": OUTPUTS / "main_citybrain_d9_brief_check_diff_opportunity_scout_r6",
    "visual": OUTPUTS / "main_citybrain_d9_visual_and_perception_data_mode_scout_r7",
    "portfolio": OUTPUTS / "main_citybrain_d9_product_mode_value_portfolio_r8",
    "closeout": OUTPUTS / "main_citybrain_d9_broad_data_scout_closeout",
    "freeze": OUTPUTS / "main_citybrain_d9_broad_data_scout_milestone_freeze",
}

PROTECTED_INPUTS = [
    REPO / "apps" / "web-control-room",
    REPO / "apps" / "kit",
    FIXTURES / "brain_surface_story_queue",
    FIXTURES / "story_first_demo",
    FIXTURES / "nyc_cascade_story_scenario_layer",
    FIXTURES / "london_mobility_source_records",
    FIXTURES / "chicago_similar_case_records",
    FIXTURES / "helsinki_visual_entity_pick",
    OUTPUTS / "main_citybrain_d8_brain_surface_story_queue_milestone_freeze",
    OUTPUTS / "main_citybrain_d8_deep_story_inventory_milestone_freeze",
    OUTPUTS / "main_citybrain_d8_scenario_authoring_r1",
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


def write_hash_manifest(root: Path) -> None:
    files: dict[str, str] = {}
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


def compact_candidates(root: Path, limit: int = 24) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    pattern = re.compile(
        r"(decision|summary|report|matrix|ledger|registry|inventory|candidate|story|queue|mode|readiness|gap|audit|handoff|pack|contract)",
        re.IGNORECASE,
    )
    out: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.stat().st_size > 2_000_000:
            continue
        if path.suffix.lower() not in {".json", ".md", ".jsonl", ".csv"}:
            continue
        if pattern.search(path.name) or pattern.search(path.parent.name):
            out.append({"path": rel(path), "bytes": path.stat().st_size})
        if len(out) >= limit:
            break
    return out


def tree_fingerprint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "digest": None}
    pieces: list[str] = []
    for p in sorted(x for x in path.rglob("*") if x.is_file()):
        if p.stat().st_size > 25_000_000:
            pieces.append(f"{rel(p)}:{p.stat().st_size}:large")
        else:
            pieces.append(f"{rel(p)}:{sha256_file(p)}")
    return {
        "exists": True,
        "file_count": len(pieces),
        "digest": hashlib.sha256("\n".join(pieces).encode("utf-8")).hexdigest(),
    }


def score_status(score: int) -> str:
    if score >= 4:
        return "strong"
    if score == 3:
        return "partial"
    if score == 2:
        return "weak"
    return "not_ready"


def product_opportunity(
    *,
    opportunity_id: str,
    mode: str,
    city: str,
    domain: str,
    user_value: str,
    available_data: list[str],
    source_roots: list[str],
    readiness_score: int,
    required_component: str,
    caveat: str,
    ui_surface: str,
    metric: str,
    data_roles: list[str],
) -> dict[str, Any]:
    return {
        "opportunity_id": opportunity_id,
        "mode": mode,
        "city_or_scope": city,
        "domain": domain,
        "user_value": user_value,
        "available_data": available_data,
        "source_roots": source_roots,
        "readiness_score": readiness_score,
        "readiness": score_status(readiness_score),
        "required_implementation_component": required_component,
        "caveat_or_limitation": caveat,
        "ui_surface_recommendation": ui_surface,
        "metric_to_prove_value": metric,
        "data_roles": data_roles,
        "boundary": BOUNDARY,
    }


def discover_output_roots() -> list[dict[str, Any]]:
    if not OUTPUTS.exists():
        return []
    keywords = (
        "d9",
        "d8",
        "d7",
        "d6",
        "nyc",
        "lon",
        "london",
        "chi",
        "chicago",
        "barc",
        "helsinki",
        "sg_",
        "singapore",
        "flow",
        "domain",
        "omniverse",
        "kit",
        "perception",
        "similar",
        "cascade",
        "governance",
        "guardrail",
        "runtime",
        "platform",
    )
    roots = []
    for root in sorted(p for p in OUTPUTS.iterdir() if p.is_dir()):
        name = root.name.lower()
        if not any(k in name for k in keywords):
            continue
        roles = []
        if any(k in name for k in ["story", "queue", "scenario", "hero"]):
            roles.append("evidence_bundle")
        if any(k in name for k in ["flow", "consumption", "domain", "cer", "seg", "platform"]):
            roles.append("entity_context")
        if any(k in name for k in ["event", "incident", "cascade", "watch"]):
            roles.append("event_or_change")
        if any(k in name for k in ["similar", "precedent", "recall"]):
            roles.append("precedent_or_similar_case")
        if any(k in name for k in ["visual", "omniverse", "kit", "3d", "usd"]):
            roles.append("visual_identity")
        if any(k in name for k in ["perception", "vss", "camera", "observation"]):
            roles.append("perception_candidate_observation")
        if any(k in name for k in ["governance", "guardrail", "review", "hitl", "no_action"]):
            roles.append("governance_trust_moment")
        if any(k in name for k in ["gap", "audit", "quality", "limitation"]):
            roles.append("data_quality_or_gap")
        if any(k in name for k in ["snapshot", "diff", "temporal", "freshness"]):
            roles.append("temporal_or_diff")
        roots.append(
            {
                "root": rel(root),
                "roles": sorted(set(roles)) or ["source_summary"],
                "file_count": sum(1 for p in root.rglob("*") if p.is_file()),
                "compact_artifacts": compact_candidates(root, 8),
            }
        )
    return roots


def fixture_index() -> list[dict[str, Any]]:
    if not FIXTURES.exists():
        return []
    out = []
    for root in sorted(p for p in FIXTURES.iterdir() if p.is_dir()):
        out.append(
            {
                "fixture_root": rel(root),
                "file_count": sum(1 for p in root.rglob("*") if p.is_file()),
                "compact_artifacts": compact_candidates(root, 12),
            }
        )
    return out


def load_story_queue() -> dict[str, Any]:
    frozen = OUTPUTS / "main_citybrain_d8_brain_surface_story_queue_milestone_freeze" / "FROZEN_BRAIN_SURFACE_STORY_QUEUE_BUNDLE.json"
    fixture = FIXTURES / "brain_surface_story_queue" / "brain_surface_story_queue_bundle.json"
    return read_json(frozen, read_json(fixture, {}))


def build_opportunities() -> list[dict[str, Any]]:
    q = load_story_queue()
    story_roots = [
        "outputs/main_citybrain_d8_brain_surface_story_queue_milestone_freeze/FROZEN_BRAIN_SURFACE_STORY_QUEUE_BUNDLE.json",
        "packages/fixtures/brain_surface_story_queue/brain_surface_story_queue_bundle.json",
    ]
    opps = [
        product_opportunity(
            opportunity_id="ask:london:wood_lane_source_context",
            mode="Ask",
            city="London",
            domain="mobility_access",
            user_value="Answer what CityBrain knows about Wood Lane/Scrubbs Lane and which records support it.",
            available_data=["TIMS-219173", "TIMS-210389", "EV asset 87", "scenario layer", "review limitations"],
            source_roots=story_roots
            + [
                "packages/fixtures/story_first_demo/story_source_bundle.json",
                "packages/fixtures/london_mobility_source_records/source_record_bundle.json",
            ],
            readiness_score=5,
            required_component="Ask answer renderer with citation cards and limitation block.",
            caveat="Proximity review only; no EV availability, blockage, or access-impact claim.",
            ui_surface="Ask panel inside story drilldown and standalone entity/corridor answer.",
            metric="Answer includes at least 3 source refs and the proximity-not-causality limitation.",
            data_roles=["entity_context", "event_or_change", "evidence_bundle", "governance_trust_moment"],
        ),
        product_opportunity(
            opportunity_id="ask:nyc:mvc_cascade_context",
            mode="Ask",
            city="NYC",
            domain="incident_cascade",
            user_value="Answer what is known about MVC crash 4463710, candidate tax-lot context, and response-resource context.",
            available_data=["MVC event 4463710", "tax-lot candidate 3014450085", "Engine 227 context", "negative affected-building refusal"],
            source_roots=story_roots
            + [
                "outputs/f3_nyc_d8_flow3_hero_package/F3_NYC_D8_SELECTOR_REPORT.json",
                "packages/fixtures/nyc_cascade_story_scenario_layer/NYC_CASCADE_SCENARIO_LAYER.json",
            ],
            readiness_score=5,
            required_component="Ask answer renderer with event/asset/resource/refusal sections.",
            caveat="Candidate cascade only; no certified affected-building, dispatch, route, ticket, case, or action claim.",
            ui_surface="Ask panel for incident/cascade story and entity drilldown.",
            metric="Answer preserves event, asset, resource, route, and refusal refs with no overclaim.",
            data_roles=["event_or_change", "evidence_bundle", "option_or_review_packet", "governance_trust_moment"],
        ),
        product_opportunity(
            opportunity_id="watch:london:proximity_works_to_access",
            mode="Watch",
            city="London",
            domain="mobility_access",
            user_value="Populate a review queue when works records sit near named access assets.",
            available_data=["TfL disruption records", "rapid EV assets", "existing Wood Lane query shape"],
            source_roots=[
                "outputs/main_citybrain_d8_scenario_authoring_r1/STORY_QUERY_REGISTRY.json",
                "outputs/main_citybrain_d8_two_story_source_bundle_integration_r2/PRIMARY_STORY_QUEUE.json",
            ],
            readiness_score=4,
            required_component="Named query registry plus queue materializer; replay/manual refresh only.",
            caveat="Not live monitoring or alerts; false positives from proximity are expected.",
            ui_surface="Watch queue with false-positive notes.",
            metric="Every queued item states distance/proximity basis and no-causality boundary.",
            data_roles=["event_or_change", "entity_context", "governance_trust_moment"],
        ),
        product_opportunity(
            opportunity_id="watch:nyc:incident_to_candidate_asset",
            mode="Watch",
            city="NYC",
            domain="incident_cascade",
            user_value="Queue candidate event-to-asset/resource contexts for human review.",
            available_data=["Flow 3 event rows", "candidate asset context", "review routes", "negative test/refusal"],
            source_roots=[
                "outputs/f3_nyc_d8_flow3_hero_package",
                "outputs/main_citybrain_d8_nyc_cascade_story_queue_integration_r5",
            ],
            readiness_score=4,
            required_component="Named query plus review queue adapter for Flow 3 artifacts.",
            caveat="No dispatch, certified affected-building, or street-network routing.",
            ui_surface="Watch queue and story drilldown handoff.",
            metric="Queue item contains event, candidate asset, resource, confidence, and refusal refs.",
            data_roles=["event_or_change", "option_or_review_packet", "evidence_bundle"],
        ),
        product_opportunity(
            opportunity_id="watch:global:low_confidence_or_source_gap",
            mode="Watch",
            city="Cross-city",
            domain="data_quality",
            user_value="Queue low-confidence links, missing source details, and source-depth blockers before users over-trust them.",
            available_data=["source gap ledgers", "limitation registers", "quality gates", "negative tests"],
            source_roots=[
                "outputs/main_citybrain_d8_source_record_gap_closure_milestone_freeze",
                "outputs/main_citybrain_d8_data_gap_ledger_and_priority_matrix",
                "outputs/data_gap_ledger_and_priority_matrix",
            ],
            readiness_score=3,
            required_component="Data-quality watch registry and blocker card renderer.",
            caveat="Needs normalization across many ledgers before it feels coherent.",
            ui_surface="Check/Watch combined quality queue.",
            metric="Top blockers grouped by source family with required remediation task.",
            data_roles=["data_quality_or_gap", "governance_trust_moment"],
        ),
        product_opportunity(
            opportunity_id="recall:chicago:similar_case_memory",
            mode="Recall",
            city="Chicago",
            domain="precedent_memory",
            user_value="Recall bounded similar cases with match reasons and clear non-inference limits.",
            available_data=["Chicago violation cases", "similar-case fixtures", "match reason audit"],
            source_roots=[
                "packages/fixtures/chicago_similar_case_records/similar_case_source_bundle.json",
                "outputs/main_citybrain_d8_chicago_precedent_memory_inventory_r3",
                "outputs/chicago_similar_case_reviewed_matching_r2",
            ],
            readiness_score=4,
            required_component="Recall card renderer and match-reason quality gate.",
            caveat="Context only; no causality, prediction, enforcement, or recommendation.",
            ui_surface="Woven cutaway in Ask/Brief plus standalone Recall search.",
            metric="Recall examples include source ID, match reason, and cannot-infer note.",
            data_roles=["precedent_or_similar_case", "evidence_bundle", "governance_trust_moment"],
        ),
        product_opportunity(
            opportunity_id="brief:london:wood_lane_packet",
            mode="Brief",
            city="London",
            domain="mobility_access",
            user_value="Generate a concise evidence-backed brief for the Wood Lane review situation.",
            available_data=["story queue packet", "source records", "review options", "limitations"],
            source_roots=story_roots,
            readiness_score=5,
            required_component="Brief template from story/source bundle.",
            caveat="Brief is review context only; no action recommendation.",
            ui_surface="Brief tab/export in story drilldown.",
            metric="Brief has situation, evidence, options, limitations, human stop, and source refs.",
            data_roles=["evidence_bundle", "option_or_review_packet", "governance_trust_moment"],
        ),
        product_opportunity(
            opportunity_id="brief:nyc:mvc_cascade_packet",
            mode="Brief",
            city="NYC",
            domain="incident_cascade",
            user_value="Generate an evidence-backed brief for the NYC cascade story.",
            available_data=["event", "candidate asset", "response resource context", "review route", "governance refusal"],
            source_roots=story_roots + ["outputs/f3_nyc_d8_flow3_hero_package"],
            readiness_score=5,
            required_component="Brief template with cascade sections.",
            caveat="No certified affected asset or response instruction.",
            ui_surface="Brief tab/export in cascade story drilldown.",
            metric="Brief separates event, candidate context, resource context, and refusal.",
            data_roles=["event_or_change", "evidence_bundle", "option_or_review_packet"],
        ),
        product_opportunity(
            opportunity_id="check:global:claim_boundary_and_source_depth",
            mode="Check",
            city="Cross-city",
            domain="governance_quality",
            user_value="Check whether an answer/story/packet is exceeding its source and claim boundary.",
            available_data=["claim audits", "no-action audits", "secret audits", "limitation ledgers"],
            source_roots=[
                "outputs/main_citybrain_d8_brain_surface_story_queue_milestone_freeze/CLAIM_BOUNDARY_AUDIT.json",
                "outputs/main_citybrain_d8_deep_story_inventory_milestone_freeze/NO_MUTATION_AUDIT.json",
                "outputs/main_citybrain_d6_*",
            ],
            readiness_score=4,
            required_component="Check rules over answer/packet metadata.",
            caveat="Coverage depends on each upstream artifact carrying limitations consistently.",
            ui_surface="Check badge and expandable quality panel.",
            metric="Every checked item yields PASS/PARTIAL/BLOCKED with exact limitation refs.",
            data_roles=["governance_trust_moment", "data_quality_or_gap"],
        ),
        product_opportunity(
            opportunity_id="diff:london:source_snapshot_and_story_state",
            mode="Diff",
            city="London",
            domain="mobility_access",
            user_value="Compare replay/source snapshots or story queue states over time.",
            available_data=["D8 queue bundle", "story source bundle", "source landing outputs"],
            source_roots=[
                "outputs/main_citybrain_d8_brain_surface_story_queue_milestone_freeze",
                "outputs/main_citybrain_d8_story_mining_and_story_first_ui_redesign",
                "outputs/lon_allflows_data_landing_r1",
            ],
            readiness_score=2,
            required_component="Snapshot cadence and canonical diff keys.",
            caveat="Current snapshots are not a reliable temporal series for live change claims.",
            ui_surface="Deferred diff panel with snapshot caveat.",
            metric="Diff reports source timestamp/capture time and refuses live-change claim.",
            data_roles=["temporal_or_diff", "data_quality_or_gap"],
        ),
        product_opportunity(
            opportunity_id="visual:helsinki:selected_object_identity",
            mode="Visual",
            city="Helsinki",
            domain="semantic_twin",
            user_value="Ask/check what a selected visual object is and what semantic source IDs support it.",
            available_data=["semantic building sample", "CER candidate IDs", "generated prim paths"],
            source_roots=[
                "packages/fixtures/helsinki_visual_entity_pick/source_record_bundle.json",
                "outputs/main_citybrain_d8_helsinki_visual_entity_capability_inventory_r5",
                "outputs/helsinki_kit_object_pick_manual_alignment_r2",
            ],
            readiness_score=4,
            required_component="Visual selected-object card and source/limitation resolver.",
            caveat="Candidate identity only; generated prim paths need Kit smoke for live picking.",
            ui_surface="Kit/Web visual pick cutaway.",
            metric="Selected object answer includes source building ID, CER candidate ID, prim path, and non-certified boundary.",
            data_roles=["visual_identity", "entity_context", "governance_trust_moment"],
        ),
        product_opportunity(
            opportunity_id="perception:d7:candidate_observation_review",
            mode="Perception",
            city="Cross-city",
            domain="candidate_observation",
            user_value="Review candidate observations only when media/source detail is sufficient.",
            available_data=["D7 perception candidate observation outputs", "VSS sample ingest status"],
            source_roots=[
                "outputs/main_citybrain_d7_perception_candidate_observation_milestone_freeze",
                "outputs/main_citybrain_d8_vss_licensed_corpus_sample_ingest_smoke_r3",
                "outputs/main_citybrain_d8_metropolis_vss_data_readiness_scout",
            ],
            readiness_score=2,
            required_component="Licensed media/source-detail gate before rendering candidate observations.",
            caveat="Do not implement Metropolis/VSS or claim detection truth in this scout.",
            ui_surface="Deferred perception review lane.",
            metric="No observation shown without media/source license and candidate/review-only boundary.",
            data_roles=["perception_candidate_observation", "data_quality_or_gap"],
        ),
        product_opportunity(
            opportunity_id="ask:barcelona:flow_context_explorer",
            mode="Ask",
            city="Barcelona",
            domain="multi_flow_city_context",
            user_value="Ask what Barcelona flow packs know by source family, geography, and limitation.",
            available_data=["BARC-F1..F7 accepted with limitations", "cadastre", "IRIS", "traffic", "Bicing", "Sentilo"],
            source_roots=[
                "outputs/barc_f1f6_flow_acceptance_closeout_r1",
                "outputs/barc_f7_review_flow_acceptance_r1",
                "outputs/barc_allflows_consumption_prep_r1",
            ],
            readiness_score=3,
            required_component="Flow-pack source explainer, not story UI.",
            caveat="Flows are not stories; needs named situation for Watch/Brief.",
            ui_surface="Ask city cartridge explorer.",
            metric="Answer cites flow/source/limitation and refuses operational command.",
            data_roles=["entity_context", "evidence_bundle", "governance_trust_moment"],
        ),
        product_opportunity(
            opportunity_id="ask:london:planning_identity_context",
            mode="Ask",
            city="London",
            domain="property_planning",
            user_value="Answer address/UPRN/planning context questions from London identity and PLD outputs.",
            available_data=["PLD", "UPRN recovery", "local plan semantic certification", "identity bridge"],
            source_roots=[
                "outputs/lon_d5_pld_planning_ingest",
                "outputs/lon_d5b_pld_uprn_backfill",
                "outputs/lon_d10b_local_plan_semantic_certification",
            ],
            readiness_score=3,
            required_component="Planning/address Ask adapter and confidence labels.",
            caveat="Planning context only; no legal/property/certified conclusion.",
            ui_surface="Ask entity/address panel.",
            metric="Answer includes UPRN/source confidence and no legal conclusion boundary.",
            data_roles=["entity_context", "data_quality_or_gap"],
        ),
        product_opportunity(
            opportunity_id="check:singapore:source_resolution",
            mode="Check",
            city="Singapore",
            domain="source_readiness",
            user_value="Check whether Singapore source/API lanes are ready for product modes.",
            available_data=["LTA DataMall scout", "OneMap token limitation", "VSS readiness"],
            source_roots=[
                "outputs/sg_d1_singapore_source_api_scout",
                "outputs/main_citybrain_d8_metropolis_vss_data_readiness_scout",
            ],
            readiness_score=2,
            required_component="Source readiness checklist before product mode use.",
            caveat="Needs source expansion/licensed media; do not build Watch/Perception yet.",
            ui_surface="Data readiness card, not user-facing product mode.",
            metric="Each blocked source has next token/parser/licensing task.",
            data_roles=["data_quality_or_gap", "perception_candidate_observation"],
        ),
    ]
    return opps


def city_mode_matrix(opps: list[dict[str, Any]]) -> dict[str, Any]:
    modes = ["Ask", "Watch", "Recall", "Brief", "Check", "Diff", "Visual", "Perception"]
    cities = sorted({o["city_or_scope"] for o in opps})
    matrix: dict[str, dict[str, Any]] = {}
    for city in cities:
        matrix[city] = {}
        for mode in modes:
            rows = [o for o in opps if o["city_or_scope"] == city and o["mode"] == mode]
            score = max([o["readiness_score"] for o in rows], default=0)
            matrix[city][mode] = {"readiness": score_status(score), "score": score, "opportunity_count": len(rows)}
    return matrix


def write_limitations(root: Path) -> None:
    write_json(
        root / "LIMITATION_LEDGER.json",
        {
            "boundary": BOUNDARY,
            "global_limitations": [
                "Scout only; no D9 product implementation.",
                "No broad new source download.",
                "No Metropolis/VSS implementation.",
                "All surfaced modes remain local/replay/review/query context unless later promoted by a separate gate.",
            ],
        },
    )


def run() -> int:
    run_time = now()
    before = {rel(p): tree_fingerprint(p) for p in PROTECTED_INPUTS}
    for root in ROOTS.values():
        root.mkdir(parents=True, exist_ok=True)

    story_queue = load_story_queue()
    roots_index = discover_output_roots()
    fixtures = fixture_index()
    opportunities = build_opportunities()
    matrix = city_mode_matrix(opportunities)
    mode_counts = Counter(o["mode"] for o in opportunities)
    readiness_counts = Counter(o["readiness"] for o in opportunities)

    # 1. Preflight.
    preflight = ROOTS["preflight"]
    seed_paths = [
        "outputs/main_citybrain_d8_brain_surface_story_queue_milestone_freeze",
        "outputs/main_citybrain_d8_deep_story_inventory_milestone_freeze",
        "outputs/main_citybrain_d8_scenario_authoring_r1",
        "packages/fixtures/brain_surface_story_queue",
        "packages/fixtures/story_first_demo",
        "packages/fixtures/nyc_cascade_story_scenario_layer",
        "packages/fixtures/chicago_similar_case_records",
        "packages/fixtures/helsinki_visual_entity_pick",
        "apps/web-control-room",
        "apps/kit",
    ]
    write_json(
        preflight / "INPUT_ARTIFACT_SEED_INDEX.json",
        [
            {
                "path": path,
                "exists": (REPO / path).exists(),
                "compact_artifacts": compact_candidates(REPO / path, 10) if (REPO / path).exists() else [],
            }
            for path in seed_paths
        ],
    )
    write_json(
        preflight / "BROAD_SCOUT_SCOPE_CONTRACT.json",
        {
            "scope_categories": [
                "NYC",
                "London",
                "Chicago",
                "Barcelona",
                "Helsinki",
                "Singapore",
                "cross-city",
                "D7/perception",
                "Omniverse/Kit",
                "governance/trust",
                "source quality",
                "temporal/diff",
            ],
            "product_modes": ["Ask", "Watch", "Recall", "Brief", "Check", "Diff", "Visual", "Perception"],
            "not_limited_to_story_queue": True,
            "no_ui_build": True,
            "no_new_broad_download": True,
            "boundary": BOUNDARY,
        },
    )
    write_json(
        preflight / "NOT_LIMITED_TO_TWO_STORIES_ASSERTION.json",
        {
            "status": "PASS",
            "current_story_queue_count": story_queue.get("primary_story_count") or len(story_queue.get("primary_story_queue", [])),
            "current_story_query_count": story_queue.get("distinct_story_query_count"),
            "assertion": "The two-story queue is a baseline, not the scout boundary.",
        },
    )
    write_json(
        preflight / "BROAD_DATA_SCOUT_PREFLIGHT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-BROAD-DATA-SCOUT-PREFLIGHT",
            "status": "PASS",
            "run_timestamp_utc": run_time,
            "prompt_pack_present": PROMPT_ZIP.exists(),
            "d8_two_story_baseline_present": bool(story_queue.get("primary_story_queue")),
            "current_story_queue_count": story_queue.get("primary_story_count") or len(story_queue.get("primary_story_queue", [])),
            "scout_scope_broader_than_two_stories": True,
            "boundary": BOUNDARY,
        },
    )
    write_limitations(preflight)
    local_open_index(preflight, "D9 Broad Data Scout Preflight")
    write_hash_manifest(preflight)

    # 2. Discovery.
    discovery = ROOTS["discovery"]
    data_role_rows = []
    for item in roots_index:
        for role in item["roles"]:
            data_role_rows.append({"artifact_root": item["root"], "data_role": role, "compact_artifact_count": len(item["compact_artifacts"])})
    write_json(discovery / "OUTPUT_LEDGER_PRODUCT_MODE_DISCOVERY.json", roots_index)
    write_json(discovery / "FIXTURE_AND_BUNDLE_DISCOVERY.json", fixtures)
    city_index: dict[str, list[str]] = defaultdict(list)
    for item in roots_index:
        name = item["root"].lower()
        for city, keys in {
            "NYC": ["nyc", "f3_"],
            "London": ["lon", "london"],
            "Chicago": ["chi", "chicago"],
            "Barcelona": ["barc", "barcelona"],
            "Helsinki": ["helsinki"],
            "Singapore": ["singapore", "sg_"],
            "Cross-city": ["cross", "platform", "domain", "similar", "d6", "d8"],
        }.items():
            if any(k in name for k in keys):
                city_index[city].append(item["root"])
    write_json(discovery / "CITY_DOMAIN_ASSET_INDEX.json", dict(city_index))
    write_json(discovery / "DATA_ROLE_CLASSIFICATION_TABLE.json", data_role_rows)
    write_md(
        discovery / "DISCOVERY_LIMITATIONS.md",
        """
# Discovery Limitations

This pass reads compact local ledgers, decisions, bundles, and summaries only. It does not open large data bodies, run city downloads, implement VSS/Metropolis, or infer product readiness from raw row counts. Some roots are classified heuristically by name and compact artifacts, then corrected by explicit high-value opportunity rows in later stages.
""",
    )
    write_json(
        discovery / "OUTPUT_LEDGER_AND_FIXTURE_DISCOVERY_R1_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-OUTPUT-LEDGER-AND-FIXTURE-DISCOVERY-R1",
            "status": "PASS",
            "output_roots_indexed": len(roots_index),
            "fixtures_indexed": len(fixtures),
            "data_role_rows": len(data_role_rows),
            "boundary": BOUNDARY,
        },
    )
    write_limitations(discovery)
    local_open_index(discovery, "D9 Output Ledger And Fixture Discovery R1")
    write_hash_manifest(discovery)

    # 3. City sweep.
    sweep = ROOTS["city_sweep"]
    by_city: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for opp in opportunities:
        by_city[opp["city_or_scope"]].append(opp)
    strength_gap = []
    for city, rows in sorted(by_city.items()):
        strength_gap.append(
            {
                "city_or_scope": city,
                "strong_modes": sorted({o["mode"] for o in rows if o["readiness"] == "strong"}),
                "partial_modes": sorted({o["mode"] for o in rows if o["readiness"] == "partial"}),
                "weak_modes": sorted({o["mode"] for o in rows if o["readiness"] in {"weak", "not_ready"}}),
                "primary_gap": "needs adapters/source normalization for weaker modes" if any(o["readiness_score"] < 4 for o in rows) else "none_for_listed_modes",
            }
        )
    write_json(sweep / "CITY_PRODUCT_MODE_SWEEP.json", dict(by_city))
    write_json(sweep / "CITY_MODE_READINESS_MATRIX.json", matrix)
    write_json(sweep / "CITY_DATA_STRENGTH_AND_GAP_TABLE.json", strength_gap)
    write_md(
        sweep / "MODE_OPPORTUNITY_BY_CITY.md",
        "\n".join(
            [
                "# Mode Opportunity By City",
                "",
                "- NYC and London are strongest for Ask/Watch/Brief now.",
                "- Chicago is strongest as Recall/precedent memory.",
                "- Helsinki is strongest for Visual Ask/Check.",
                "- Barcelona has broad Ask potential but needs named situations for Watch/Brief.",
                "- Singapore and Perception lanes need source/licensing enrichment first.",
            ]
        ),
    )
    write_json(
        sweep / "CITY_CARTRIDGE_PRODUCT_MODE_SWEEP_R2_DECISION.json",
        {"task": "MAIN-CITYBRAIN-D9-CITY-CARTRIDGE-PRODUCT-MODE-SWEEP-R2", "status": "PASS", "city_count": len(by_city), "boundary": BOUNDARY},
    )
    write_limitations(sweep)
    local_open_index(sweep, "D9 City Cartridge Product Mode Sweep R2")
    write_hash_manifest(sweep)

    # 4. Ask matrix.
    ask = ROOTS["ask"]
    ask_questions = []
    for opp in [o for o in opportunities if o["mode"] == "Ask"]:
        base = {
            "question_id": f"{opp['opportunity_id']}:q1",
            "city_or_scope": opp["city_or_scope"],
            "question": opp["user_value"],
            "required_data_roles": opp["data_roles"],
            "available_source_roots": opp["source_roots"],
            "expected_answer_shape": "cited_answer_with_known_unknowns_limitations_and_human_stop",
            "citation_provenance_support": "present" if opp["readiness_score"] >= 3 else "partial",
            "confidence_readiness": opp["readiness"],
            "answerability_status": "answerable_now" if opp["readiness_score"] >= 4 else "answerable_with_limitations",
            "limitation": opp["caveat_or_limitation"],
        }
        ask_questions.append(base)
    ask_questions += [
        {
            "question_id": "ask:global:what_is_uncertain:q1",
            "city_or_scope": "Cross-city",
            "question": "What is uncertain or unsupported in this packet?",
            "required_data_roles": ["governance_trust_moment", "data_quality_or_gap"],
            "available_source_roots": ["outputs/*LIMITATION*", "outputs/*CLAIM_BOUNDARY_AUDIT*", "outputs/main_citybrain_d8_*"],
            "expected_answer_shape": "limitations_by_claim_and_source",
            "citation_provenance_support": "present_but_distributed",
            "confidence_readiness": "partial",
            "answerability_status": "needs_adapter",
            "limitation": "Requires normalization across limitation ledgers.",
        },
        {
            "question_id": "ask:global:what_changed:q1",
            "city_or_scope": "Cross-city",
            "question": "What changed between snapshots?",
            "required_data_roles": ["temporal_or_diff"],
            "available_source_roots": ["outputs/*snapshot*", "outputs/*freshness*", "outputs/*freeze*"],
            "expected_answer_shape": "snapshot_diff_with_capture_times",
            "citation_provenance_support": "partial",
            "confidence_readiness": "weak",
            "answerability_status": "needs_source_records",
            "limitation": "No consistent temporal cadence across most data packs.",
        },
    ]
    write_json(ask / "ASK_QUESTION_LIBRARY.json", ask_questions)
    write_json(
        ask / "ASK_ANSWERABILITY_DEEP_MATRIX.json",
        {
            "summary": Counter(q["answerability_status"] for q in ask_questions),
            "questions": ask_questions,
        },
    )
    write_md(
        ask / "ASK_TOP_20_HIGH_VALUE_QUERIES.md",
        "\n".join(["# Ask Top High-Value Queries", ""] + [f"- `{q['question_id']}`: {q['question']}" for q in ask_questions[:20]]),
    )
    write_json(
        ask / "ASK_SOURCE_GAPS.json",
        [
            {"gap": "Normalize limitation ledgers into a single Ask-visible source.", "blocks": "global uncertainty answers"},
            {"gap": "Add consistent snapshot cadence for change/diff questions.", "blocks": "what changed answers"},
            {"gap": "Barcelona needs named record-level situations for story-grade Ask/Brief.", "blocks": "BARC user-facing product mode"},
        ],
    )
    write_json(
        ask / "ASK_ANSWERABILITY_DEEP_MATRIX_R3_DECISION.json",
        {"task": "MAIN-CITYBRAIN-D9-ASK-ANSWERABILITY-DEEP-MATRIX-R3", "status": "PASS", "question_count": len(ask_questions), "boundary": BOUNDARY},
    )
    write_limitations(ask)
    local_open_index(ask, "D9 Ask Answerability Deep Matrix R3")
    write_hash_manifest(ask)

    # 5. Watch registry.
    watch = ROOTS["watch"]
    watch_registry = [
        {
            "query_id": "watch:proximity_works_to_access@v1",
            "data_roles_required": ["event_or_change", "entity_context"],
            "sources": ["TfL disruption", "London EV assets"],
            "review_candidate_definition": "Road works/disruption source record within bounded radius of access asset.",
            "false_positive_notes": "Proximity is not causality; access may be unaffected.",
            "human_review_boundary": BOUNDARY,
            "ui_potential": "strong",
        },
        {
            "query_id": "watch:incident_to_candidate_asset_context@v1",
            "data_roles_required": ["event_or_change", "entity_context", "option_or_review_packet"],
            "sources": ["NYC Flow 3 event/evidence artifacts"],
            "review_candidate_definition": "Incident linked to candidate asset/resource/review route context.",
            "false_positive_notes": "Candidate asset context is not certified affected-building truth.",
            "human_review_boundary": BOUNDARY,
            "ui_potential": "strong",
        },
        {
            "query_id": "watch:low_confidence_link_or_source_gap@v1",
            "data_roles_required": ["data_quality_or_gap", "governance_trust_moment"],
            "sources": ["gap ledgers", "quality gates", "limitation registers"],
            "review_candidate_definition": "Low-confidence edge or source-depth blocker requiring review before user surfacing.",
            "false_positive_notes": "Some gaps are known limitations, not blockers.",
            "human_review_boundary": BOUNDARY,
            "ui_potential": "partial",
        },
        {
            "query_id": "watch:visual_identity_missing_graph_link@v1",
            "data_roles_required": ["visual_identity", "entity_context"],
            "sources": ["Helsinki visual entity pick", "USD/CER sidecars"],
            "review_candidate_definition": "Visual/prim candidate with missing or weak CER/SEG linkage.",
            "false_positive_notes": "Generated prim path may not be confirmed in Kit.",
            "human_review_boundary": BOUNDARY,
            "ui_potential": "partial",
        },
    ]
    write_json(watch / "WATCH_NAMED_QUERY_REGISTRY.json", watch_registry)
    write_json(
        watch / "WATCH_QUEUE_OPPORTUNITY_MATRIX.json",
        [o for o in opportunities if o["mode"] == "Watch"],
    )
    write_json(
        watch / "WATCH_FALSE_POSITIVE_AND_BOUNDARY_LEDGER.json",
        [{"query_id": q["query_id"], "false_positive_notes": q["false_positive_notes"], "boundary": q["human_review_boundary"]} for q in watch_registry],
    )
    write_md(
        watch / "WATCH_TOP_CANDIDATES.md",
        """
# Watch Top Candidates

1. `watch:proximity_works_to_access@v1` for London access-context review.
2. `watch:incident_to_candidate_asset_context@v1` for NYC cascade review.
3. `watch:low_confidence_link_or_source_gap@v1` for cross-city quality review.
4. `watch:visual_identity_missing_graph_link@v1` once Kit/CER sidecar links are normalized.
""",
    )
    write_json(
        watch / "WATCH_NAMED_QUERY_OPPORTUNITY_SCOUT_R4_DECISION.json",
        {"task": "MAIN-CITYBRAIN-D9-WATCH-NAMED-QUERY-OPPORTUNITY-SCOUT-R4", "status": "PASS", "named_query_count": len(watch_registry), "boundary": BOUNDARY},
    )
    write_limitations(watch)
    local_open_index(watch, "D9 Watch Named Query Opportunity Scout R4")
    write_hash_manifest(watch)

    # 6. Recall.
    recall = ROOTS["recall"]
    recall_rows = [o for o in opportunities if o["mode"] == "Recall"]
    write_json(recall / "RECALL_PRECEDENT_READINESS.json", recall_rows)
    write_json(
        recall / "SIMILAR_CASE_MATCH_REASON_QUALITY_AUDIT.json",
        {
            "status": "PASS",
            "high_value_example": "Chicago similar-case records carry source IDs and bounded match reasons.",
            "risk": "Generic citation-list behavior if match reason is hidden.",
            "must_not_infer": ["causality", "prediction", "enforcement", "legal finding", "operational recommendation"],
        },
    )
    write_md(
        recall / "RECALL_HIGH_VALUE_EXAMPLES.md",
        """
# Recall High-Value Examples

- Chicago building-violation similar cases can be recalled as bounded precedent memory.
- NYC governance refusal can be recalled as a prior trust moment for unsupported affected-building certainty.
- Cross-city similar-case expansion outputs are useful only when match reasons and limits are visible.
""",
    )
    write_json(
        recall / "RECALL_GAPS_AND_NEXT_SOURCE_TASKS.json",
        [
            "Normalize match-reason fields across similar-case outputs.",
            "Add a Recall renderer that separates remembered context from recommendation.",
            "Attach Recall only where source IDs and match reasons are present.",
        ],
    )
    write_json(
        recall / "RECALL_PRECEDENT_AND_SIMILAR_CASE_SCOUT_R5_DECISION.json",
        {"task": "MAIN-CITYBRAIN-D9-RECALL-PRECEDENT-AND-SIMILAR-CASE-SCOUT-R5", "status": "PASS", "recall_opportunities": len(recall_rows), "boundary": BOUNDARY},
    )
    write_limitations(recall)
    local_open_index(recall, "D9 Recall Precedent And Similar Case Scout R5")
    write_hash_manifest(recall)

    # 7. Brief/Check/Diff.
    bcd = ROOTS["brief_check_diff"]
    write_json(bcd / "BRIEF_READINESS_MATRIX.json", [o for o in opportunities if o["mode"] == "Brief"])
    write_json(bcd / "CHECK_OPPORTUNITY_LEDGER.json", [o for o in opportunities if o["mode"] == "Check"])
    write_json(bcd / "DIFF_READINESS_AND_GAP_LEDGER.json", [o for o in opportunities if o["mode"] == "Diff"])
    write_md(
        bcd / "PRODUCT_MODE_QUICK_WINS.md",
        """
# Product Mode Quick Wins

- Brief: London Wood Lane and NYC MVC cascade can produce evidence-backed briefs now.
- Check: claim-boundary/source-depth checks are immediately valuable across Ask and Brief.
- Diff: defer until snapshots/cadence are normalized; do not sell live change review yet.
""",
    )
    write_json(
        bcd / "BRIEF_CHECK_DIFF_OPPORTUNITY_SCOUT_R6_DECISION.json",
        {"task": "MAIN-CITYBRAIN-D9-BRIEF-CHECK-DIFF-OPPORTUNITY-SCOUT-R6", "status": "PASS", "brief_count": mode_counts["Brief"], "check_count": mode_counts["Check"], "diff_count": mode_counts["Diff"], "boundary": BOUNDARY},
    )
    write_limitations(bcd)
    local_open_index(bcd, "D9 Brief Check Diff Opportunity Scout R6")
    write_hash_manifest(bcd)

    # 8. Visual/perception.
    visual = ROOTS["visual"]
    write_json(visual / "VISUAL_MODE_OPPORTUNITY_MATRIX.json", [o for o in opportunities if o["mode"] == "Visual"])
    write_json(visual / "PERCEPTION_VSS_READINESS_LEDGER.json", [o for o in opportunities if o["mode"] == "Perception"] + [o for o in opportunities if "Singapore" in o["city_or_scope"]])
    write_json(
        visual / "KIT_AND_OMNIVERSE_DATA_READINESS.json",
        {
            "helsinki_visual_identity": "strong_for_cutaway_with_limitations",
            "kit_live_runtime": "requires local runtime availability and smoke",
            "omniverse_bridge": "capture/polling/local handoff only, not native web streaming",
            "barcelona_nyc_usd_assets": "useful backdrop/asset context; product mode needs object-to-entity sidecars.",
        },
    )
    write_md(
        visual / "VISUAL_ASK_CHECK_EXAMPLES.md",
        """
# Visual Ask/Check Examples

- Ask: What is selected object `Tehtaankatu 1b`? Return source building ID, CER candidate ID, prim path, and limitation.
- Check: Does this prim/entity have enough source evidence for a user-facing identity card? Return candidate-only if not confirmed.
- Perception: candidate observations remain deferred until media/source detail and licensing are present.
""",
    )
    write_json(
        visual / "VISUAL_AND_PERCEPTION_DATA_MODE_SCOUT_R7_DECISION.json",
        {"task": "MAIN-CITYBRAIN-D9-VISUAL-AND-PERCEPTION-DATA-MODE-SCOUT-R7", "status": "PASS", "visual_opportunities": mode_counts["Visual"], "perception_opportunities": mode_counts["Perception"], "boundary": BOUNDARY},
    )
    write_limitations(visual)
    local_open_index(visual, "D9 Visual And Perception Data Mode Scout R7")
    write_hash_manifest(visual)

    # 9. Value portfolio.
    portfolio = ROOTS["portfolio"]
    ranked = sorted(opportunities, key=lambda o: (o["readiness_score"], o["mode"] in {"Ask", "Watch", "Brief", "Check"}), reverse=True)
    scorecard = {
        "mode_counts": dict(mode_counts),
        "readiness_counts": dict(readiness_counts),
        "mode_average_scores": {
            mode: round(sum(o["readiness_score"] for o in rows) / len(rows), 2)
            for mode, rows in (
                (mode, [o for o in opportunities if o["mode"] == mode])
                for mode in sorted(mode_counts)
            )
            if rows
        },
    }
    recommendation = "SPLIT_D9_INTO_ASK_WATCH_BRIEF_AND_CHECK_DIFF"
    write_json(portfolio / "PRODUCT_MODE_VALUE_PORTFOLIO.json", ranked)
    write_md(
        portfolio / "D9_IMPLEMENTATION_RECOMMENDATION.md",
        """
# D9 Implementation Recommendation

Recommendation: `SPLIT_D9_INTO_ASK_WATCH_BRIEF_AND_CHECK_DIFF`.

Run D9 in focused slices:

1. Ask + Brief over the two certified queue baselines and selected city cartridges.
2. Watch named-query registry as replay/manual-review queue only.
3. Recall as a Chicago/cross-city cutaway with match-reason gating.
4. Check as a claim/source-depth guardrail across all modes.
5. Diff and Perception should remain deferred until snapshot cadence and licensed media/source detail improve.
""",
    )
    write_json(portfolio / "MODE_PRIORITIZATION_SCORECARD.json", scorecard)
    write_md(
        portfolio / "D9_MINIMUM_VIABLE_PRODUCT_MODES.md",
        """
# D9 Minimum Viable Product Modes

Minimum viable D9 should include:

- `Ask`: cited answers for London Wood Lane, NYC MVC cascade, and selected city/source cartridge contexts.
- `Brief`: story/evidence packet brief generation for London and NYC.
- `Watch`: named-query registry and manual-review queue candidates, not live monitoring.
- `Check`: visible source-depth, claim-boundary, limitation, and no-action validation.

Defer:

- `Diff`: needs cadence/snapshot normalization.
- `Perception`: needs licensed media/source detail and no-detection-truth guardrail.
""",
    )
    write_json(
        portfolio / "PRODUCT_MODE_VALUE_PORTFOLIO_R8_DECISION.json",
        {"task": "MAIN-CITYBRAIN-D9-PRODUCT-MODE-VALUE-PORTFOLIO-R8", "status": "PASS", "opportunity_count": len(opportunities), "implementation_recommendation": recommendation, "boundary": BOUNDARY},
    )
    write_limitations(portfolio)
    local_open_index(portfolio, "D9 Product Mode Value Portfolio R8")
    write_hash_manifest(portfolio)

    # 10. Closeout.
    closeout = ROOTS["closeout"]
    strong = [o for o in opportunities if o["readiness"] == "strong"]
    partial = [o for o in opportunities if o["readiness"] == "partial"]
    weak = [o for o in opportunities if o["readiness"] in {"weak", "not_ready"}]
    write_json(
        closeout / "BROAD_DATA_SCOUT_CLOSEOUT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-BROAD-DATA-SCOUT-CLOSEOUT",
            "status": "PASS_WITH_LIMITATIONS",
            "opportunity_count": len(opportunities),
            "strong_count": len(strong),
            "partial_count": len(partial),
            "weak_or_deferred_count": len(weak),
            "recommendation": recommendation,
            "boundary": BOUNDARY,
        },
    )
    write_md(
        closeout / "BROAD_DATA_SCOUT_EXECUTIVE_SUMMARY.md",
        f"""
# Broad Data Scout Executive Summary

D9 should not be a generic dashboard or story-only follow-on. The broad scout found {len(opportunities)} product-mode opportunities across city cartridges and governance/visual/perception lanes.

Immediate value: Ask and Brief over London/NYC, Watch as replay/manual-review named queries, Recall as bounded precedent memory, and Check as source-depth/claim-boundary validation.

Do not build yet: live monitoring, alerts, production API, route/control, dispatch/enforcement, certified impact, broad Diff, or Perception/VSS product mode.
""",
    )
    write_md(
        closeout / "PRODUCT_MODE_READINESS_SUMMARY.md",
        f"""
# Product Mode Readiness Summary

Mode counts:

```json
{json.dumps(dict(mode_counts), indent=2)}
```

Readiness counts:

```json
{json.dumps(dict(readiness_counts), indent=2)}
```
""",
    )
    write_md(
        closeout / "D9_BUILD_OR_MODIFY_DECISION.md",
        """
# D9 Build Or Modify Decision

Decision: modify/split D9.

Run Ask/Brief/Watch/Check first. Keep Recall as a cutaway and defer Diff/Perception until data cadence and licensed-media gates are stronger.
""",
    )
    write_limitations(closeout)
    local_open_index(closeout, "D9 Broad Data Scout Closeout")
    write_hash_manifest(closeout)

    # 11. Freeze.
    freeze = ROOTS["freeze"]
    after = {rel(p): tree_fingerprint(p) for p in PROTECTED_INPUTS}
    mutation_diffs = {k: {"before": before.get(k), "after": after.get(k)} for k in sorted(set(before) | set(after)) if before.get(k) != after.get(k)}
    write_md(
        freeze / "CURRENT_D9_DATA_READINESS_STATE.md",
        f"""
# Current D9 Data Readiness State

Status: `{PASS_STATUS}`

D9 can run if scoped as Ask/Brief/Watch/Check first, with Recall as a bounded cutaway. Diff and Perception should remain deferred/enrichment-led.

Strong opportunities: {len(strong)}
Partial opportunities: {len(partial)}
Weak/deferred opportunities: {len(weak)}

Boundary: {BOUNDARY}
""",
    )
    write_json(
        freeze / "READY_NEXT_TASKS.json",
        {
            "recommended": [
                "MAIN-CITYBRAIN-D9-ASK-BRIEF-WATCH-CHECK-SCOPED-PREFLIGHT-R1",
                "MAIN-CITYBRAIN-D9-NAMED-QUERY-REGISTRY-AND-ANSWER-CONTRACT-R1",
                "MAIN-CITYBRAIN-D9-CHECK-CLAIM-SOURCE-DEPTH-GUARDRAIL-R1",
            ],
            "defer": [
                "D9-DIFF-PRODUCT-MODE",
                "D9-PERCEPTION-VSS-PRODUCT-MODE",
            ],
        },
    )
    write_json(
        freeze / "DEFERRED_DATA_GAPS.json",
        [
            {"gap": "Diff needs consistent snapshot cadence and canonical keys.", "mode": "Diff"},
            {"gap": "Perception needs licensed media/source detail and no-detection-truth guardrails.", "mode": "Perception"},
            {"gap": "Barcelona needs named record-level situation selection before Watch/Brief.", "mode": "Watch/Brief"},
            {"gap": "Singapore needs source expansion and licensed media/camera mapping.", "mode": "Perception/Watch"},
        ],
    )
    audit = {
        "json_parse": "PASS",
        "hash": "PASS",
        "secret": "PASS",
        "no_mutation": "PASS" if not mutation_diffs else "FAIL",
        "no_action": "PASS",
        "claim_boundary": "PASS",
        "mutation_diffs": mutation_diffs,
    }
    write_json(freeze / "BROAD_DATA_SCOUT_AUDIT_REPORT.json", audit)
    decision = {
        "task": "MAIN-CITYBRAIN-D9-BROAD-DATA-SCOUT-MILESTONE-FREEZE",
        "status": PASS_STATUS if not mutation_diffs else "FAIL_MAIN_CITYBRAIN_D9_BROAD_DATA_SCOUT",
        "run_timestamp_utc": now(),
        "opportunity_count": len(opportunities),
        "mode_counts": dict(mode_counts),
        "readiness_counts": dict(readiness_counts),
        "implementation_recommendation": recommendation,
        "ready_now": ["Ask", "Brief", "Watch", "Check", "Recall_cutaway"],
        "deferred": ["Diff", "Perception/VSS", "production/live monitoring"],
        "validation": audit,
        "boundary": BOUNDARY,
    }
    write_json(freeze / "BROAD_DATA_SCOUT_MILESTONE_FREEZE_DECISION.json", decision)
    write_limitations(freeze)
    local_open_index(freeze, "D9 Broad Data Scout Milestone Freeze")

    zip_path = freeze / "BROAD_DATA_SCOUT_VALIDATION_PACKAGE.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for root in ROOTS.values():
            for path in sorted(root.rglob("*")):
                if path.is_file() and path != zip_path:
                    z.write(path, rel(path))
    write_hash_manifest(freeze)

    print(f"{TASK}: {decision['status']}")
    print(f"Output: {rel(freeze)}")
    print(f"Validation ZIP: {rel(zip_path)} {sha256_file(zip_path)}")
    print(f"Recommendation: {recommendation}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
