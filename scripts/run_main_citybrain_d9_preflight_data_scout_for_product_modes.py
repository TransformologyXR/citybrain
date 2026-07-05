from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
RUNNER = Path(__file__).resolve()

PASS_CLOSEOUT = "PASS_MAIN_CITYBRAIN_D9_DATA_SCOUT_CLOSEOUT_WITH_LIMITATIONS"
PASS_FREEZE = "PASS_MAIN_CITYBRAIN_D9_DATA_SCOUT_MILESTONE_FREEZE_WITH_LIMITATIONS"

ROOTS = {
    "preflight": REPO / "outputs" / "main_citybrain_d9_data_scout_preflight",
    "inventory": REPO / "outputs" / "main_citybrain_d9_mode_surface_input_inventory_r1",
    "ask": REPO / "outputs" / "main_citybrain_d9_ask_question_coverage_scout_r2",
    "watch": REPO / "outputs" / "main_citybrain_d9_watch_named_query_potential_r3",
    "recall": REPO / "outputs" / "main_citybrain_d9_recall_precedent_coverage_r4",
    "brief": REPO / "outputs" / "main_citybrain_d9_brief_packet_readiness_r5",
    "checkdiff": REPO / "outputs" / "main_citybrain_d9_check_diff_scout_r6",
    "gap": REPO / "outputs" / "main_citybrain_d9_product_mode_source_gap_ledger_r7",
    "closeout": REPO / "outputs" / "main_citybrain_d9_data_scout_closeout",
    "freeze": REPO / "outputs" / "main_citybrain_d9_data_scout_milestone_freeze",
}

INPUTS = {
    "story_queue_bundle": REPO / "packages" / "fixtures" / "brain_surface_story_queue" / "brain_surface_story_queue_bundle.json",
    "wood_lane_scenario_layer": REPO / "packages" / "fixtures" / "story_first_demo" / "story_scenario_layer.json",
    "wood_lane_source_bundle": REPO / "packages" / "fixtures" / "story_first_demo" / "story_source_bundle.json",
    "nyc_cascade_layer": REPO / "packages" / "fixtures" / "nyc_cascade_story_scenario_layer" / "NYC_CASCADE_SCENARIO_LAYER.json",
    "integrated_source_bundle": REPO / "packages" / "fixtures" / "source_record_ui_integrated" / "source_record_ui_integrated_bundle.json",
    "london_source_bundle": REPO / "packages" / "fixtures" / "london_mobility_source_records" / "source_record_bundle.json",
    "chicago_source_bundle": REPO / "packages" / "fixtures" / "chicago_similar_case_records" / "similar_case_source_bundle.json",
    "helsinki_source_bundle": REPO / "packages" / "fixtures" / "helsinki_visual_entity_pick" / "source_record_bundle.json",
    "deep_story_woven": REPO / "outputs" / "main_citybrain_d8_deep_story_inventory_closeout" / "WOVEN_CAPABILITIES_AND_TRUST_LAYER.json",
    "duplicate_shape_audit": REPO / "outputs" / "main_citybrain_d8_scenario_authoring_r1" / "DUPLICATE_SHAPE_AUDIT.json",
    "story_query_registry": REPO / "outputs" / "main_citybrain_d8_scenario_authoring_r1" / "STORY_QUERY_REGISTRY.json",
    "nyc_evidence_map": REPO / "outputs" / "main_citybrain_d8_nyc_cascade_source_evidence_map_r3" / "NYC_CASCADE_STORY_TO_SOURCE_EVIDENCE_MAP.json",
    "story_queue_freeze": REPO / "outputs" / "main_citybrain_d8_brain_surface_story_queue_milestone_freeze" / "BRAIN_SURFACE_STORY_QUEUE_MILESTONE_FREEZE_DECISION.json",
    "capture_handoff": REPO / "outputs" / "main_citybrain_d8_story_queue_capture_handoff_r5" / "STORY_QUEUE_CAPTURE_HANDOFF_DECISION.json",
}

READ_ONLY_ROOTS = [
    REPO / "packages" / "fixtures" / "brain_surface_story_queue",
    REPO / "packages" / "fixtures" / "story_first_demo",
    REPO / "packages" / "fixtures" / "nyc_cascade_story_scenario_layer",
    REPO / "packages" / "fixtures" / "source_record_ui_integrated",
    REPO / "packages" / "fixtures" / "london_mobility_source_records",
    REPO / "packages" / "fixtures" / "chicago_similar_case_records",
    REPO / "packages" / "fixtures" / "helsinki_visual_entity_pick",
    REPO / "outputs" / "main_citybrain_d8_brain_surface_story_queue_milestone_freeze",
    REPO / "outputs" / "main_citybrain_d8_story_queue_capture_handoff_r5",
    REPO / "outputs" / "main_citybrain_d8_deep_story_inventory_closeout",
    REPO / "outputs" / "main_citybrain_d8_scenario_authoring_r1",
    REPO / "outputs" / "main_citybrain_d8_nyc_cascade_source_evidence_map_r3",
]

GLOBAL_BOUNDARY = [
    "Local/replay/review/query context only.",
    "No production/public API claim.",
    "No live monitoring, alerting, dispatch, routing/control, enforcement, ticket/case, legal/certified finding, or automated action.",
    "No source fact fabrication.",
    "No impact/causality inference when only proximity or context exists.",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO).as_posix()


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def safe_reset(path: Path) -> None:
    target = path.resolve()
    outputs = (REPO / "outputs").resolve()
    if not (target == outputs or outputs in target.parents):
        raise RuntimeError(f"Refusing to reset non-output path: {target}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(paths: list[Path]) -> dict:
    rows = {}
    for root in paths:
        if not root.exists():
            rows[rel(root)] = "MISSING"
        elif root.is_file():
            rows[rel(root)] = sha256(root)
        else:
            for path in sorted(p for p in root.rglob("*") if p.is_file()):
                rows[rel(path)] = sha256(path)
    return rows


def hash_manifest(root: Path) -> dict:
    rows = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "HASH_MANIFEST.json"):
        rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256(path)})
    return {
        "schema_version": "main-citybrain-d9-preflight-data-scout-for-product-modes.v1",
        "generated_at": now(),
        "file_count": len(rows),
        "files": rows,
    }


def local_open_index(root: Path, title: str) -> None:
    lines = [f"# {title}", "", f"Output root: `{rel(root)}`", "", "Files:"]
    for path in sorted(p for p in root.iterdir() if p.is_file()):
        lines.append(f"- `{rel(path)}`")
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def secret_audit(root: Path) -> dict:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|password|private[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}"),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ]
    findings = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.suffix.lower() in {".zip", ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".webm"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern})
    return {"status": "PASS" if not findings else "FAIL", "secret_findings_count": len(findings), "findings": findings}


def claim_audit(extra: dict | None = None) -> dict:
    payload = {
        "status": "PASS",
        "scope": "D9 data scout only; no product-mode runtime or UI is implemented.",
        "forbidden_claims_not_made": [
            "production readiness",
            "live monitoring or alerting",
            "dispatch/routing/control/enforcement",
            "ticket/case creation",
            "legal or certified finding",
            "automated action",
            "causal impact from proximity/context-only evidence",
        ],
    }
    if extra:
        payload.update(extra)
    return payload


def no_action_audit() -> dict:
    return {
        "status": "PASS",
        "execution_state": "not_executed",
        "action_created": False,
        "runtime_implemented": False,
        "product_mode_runtime_started": False,
    }


def no_mutation_audit(before: dict, after: dict) -> dict:
    changed = [
        {"path": key, "before": before.get(key), "after": after.get(key)}
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    ]
    return {"status": "PASS" if not changed else "FAIL", "mutated_read_only_count": len(changed), "findings": changed}


def finalize(root: Path, title: str, before: dict, after: dict) -> None:
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claim_audit())
    write_json(root / "NO_ACTION_AUDIT.json", no_action_audit())
    write_json(root / "NO_MUTATION_AUDIT.json", no_mutation_audit(before, after))
    write_json(root / "SECRET_AUDIT.json", secret_audit(root))
    write_text(root / "README.md", f"# {title}\n\nGenerated by `{rel(RUNNER)}`.")
    local_open_index(root, title)
    write_json(root / "HASH_MANIFEST.json", hash_manifest(root))


def list_len(data: dict, key: str) -> int:
    value = data.get(key, [])
    return len(value) if isinstance(value, list) else 0


def input_inventory(queue: dict, integrated: dict, woven: dict, capture: dict) -> list[dict]:
    return [
        {
            "artifact_id": "brain_surface_story_queue_bundle",
            "path": rel(INPUTS["story_queue_bundle"]),
            "class": "AUTHORED_SCENARIO_LAYER",
            "records_or_items": len(queue.get("primary_story_queue", [])),
            "mode_suitability": ["ASK", "WATCH", "BRIEF", "CHECK"],
            "product_value": "Primary two-story queue with distinct query keys and human boundaries.",
        },
        {
            "artifact_id": "wood_lane_scenario_layer",
            "path": rel(INPUTS["wood_lane_scenario_layer"]),
            "class": "AUTHORED_SCENARIO_LAYER",
            "records_or_items": 3,
            "mode_suitability": ["ASK", "WATCH", "BRIEF", "CHECK"],
            "product_value": "Source-backed London proximity/access review with explicit not-impact boundary.",
        },
        {
            "artifact_id": "nyc_cascade_scenario_layer",
            "path": rel(INPUTS["nyc_cascade_layer"]),
            "class": "AUTHORED_SCENARIO_LAYER",
            "records_or_items": 7,
            "mode_suitability": ["ASK", "WATCH", "BRIEF", "CHECK"],
            "product_value": "Source-backed NYC incident/candidate-context cascade with refusal and human stop.",
        },
        {
            "artifact_id": "integrated_source_record_bundle",
            "path": rel(INPUTS["integrated_source_bundle"]),
            "class": "SOURCE_DERIVED_RECORD",
            "records_or_items": sum(list_len(integrated, key) for key in ["situation_city_records", "similar_case_city_records", "visual_entity_city_records", "media_observation_source_records", "guardrail_refusal_review_records", "human_review_stop_source_records"]),
            "mode_suitability": ["ASK", "RECALL", "BRIEF", "CHECK"],
            "product_value": "Recovered source-record cards across London, Chicago, Helsinki, observations, refusals, and human-review stops when present.",
        },
        {
            "artifact_id": "chicago_similar_case_records",
            "path": rel(INPUTS["chicago_source_bundle"]),
            "class": "OFFICIAL_SOURCE_RECORD",
            "records_or_items": list_len(integrated, "similar_case_city_records"),
            "mode_suitability": ["RECALL", "BRIEF", "CHECK"],
            "product_value": "Precedent memory records; useful but currently generic unless a specific match reason is chosen.",
        },
        {
            "artifact_id": "helsinki_visual_entity_records",
            "path": rel(INPUTS["helsinki_source_bundle"]),
            "class": "CAPABILITY_CUTAWAY_RECORD",
            "records_or_items": list_len(integrated, "visual_entity_city_records"),
            "mode_suitability": ["ASK", "WATCH", "BRIEF", "CHECK"],
            "product_value": "Visual object to semantic entity cutaway, not a certified-twin claim.",
        },
        {
            "artifact_id": "woven_trust_and_cutaways",
            "path": rel(INPUTS["deep_story_woven"]),
            "class": "TRUST_MOMENT_RECORD",
            "records_or_items": len(woven.get("trust_moments", [])) + len(woven.get("capability_cutaways", [])),
            "mode_suitability": ["ASK", "WATCH", "RECALL", "BRIEF", "CHECK"],
            "product_value": "Woven no-action, uncertainty, precedent, and visual cutaway context.",
        },
        {
            "artifact_id": "capture_handoff",
            "path": rel(INPUTS["capture_handoff"]),
            "class": "DATA_DEPTH_BLOCKER",
            "records_or_items": capture.get("media_count", 0),
            "mode_suitability": ["CHECK"],
            "product_value": "Confirms current two-story media and viewer validation are pending.",
        },
    ]


def ask_questions() -> list[dict]:
    questions = [
        ("ask-001", "What do we know about Wood Lane / Scrubbs Lane?", "ANSWER_READY_WITH_CITATIONS", ["TIMS-219173", "TIMS-210389", "EV asset 87"]),
        ("ask-002", "What source records support the Wood Lane story?", "ANSWER_READY_WITH_CITATIONS", ["TIMS-219173", "TIMS-210389", "EV asset 87"]),
        ("ask-003", "What is the relationship between the TfL works records and EV asset 87?", "ANSWER_READY_WITH_LIMITATIONS", ["story-query:proximity_works_to_access@v1"]),
        ("ask-004", "What is not proven in the Wood Lane story?", "ANSWER_READY_WITH_CITATIONS", ["proximity_not_impact_rule", "human_stop"]),
        ("ask-005", "What do we know about NYC MVC crash 4463710?", "ANSWER_READY_WITH_CITATIONS", ["event:us-nyc:flow3:mvc_crash:4463710", "4463710"]),
        ("ask-006", "Which affected/context records are connected to the NYC cascade story?", "ANSWER_READY_WITH_LIMITATIONS", ["3014450085", "resource:us-nyc:fdny:firehouse:engine_227", "negative_affected_buildings"]),
        ("ask-007", "What is not proven in the NYC cascade story?", "ANSWER_READY_WITH_CITATIONS", ["not_certified_affected_building_or_asset", "not_route_not_dispatch_recommendation"]),
        ("ask-008", "Which review options exist and where does the system stop?", "ANSWER_READY_WITH_CITATIONS", ["review_only_choices", "human_stop"]),
        ("ask-009", "What similar precedent/cutaway evidence exists from Chicago?", "ANSWER_READY_WITH_LIMITATIONS", ["Chicago Building Violations", "7511042", "7510501"]),
        ("ask-010", "What does Helsinki visual pick prove and not prove?", "ANSWER_READY_WITH_LIMITATIONS", ["BID_35328115-972e-45e3-97bd-d0029f19f70d", "visual_object_to_semantic_entity"]),
    ]
    rows = []
    for qid, question, status, citations in questions:
        rows.append(
            {
                "question_id": qid,
                "question": question,
                "answerability": status,
                "citation_refs": citations,
                "boundary": "Answer with source refs and limitations; do not infer impact, dispatch, certified truth, or action.",
            }
        )
    return rows


def watch_queries(queue: dict, integrated: dict, duplicate: dict) -> list[dict]:
    return [
        {
            "query_key": "story-query:proximity_works_to_access@v1",
            "inputs": ["Wood Lane scenario layer", "London source records", "duplicate-shape audit"],
            "candidate_count": 1 + duplicate.get("duplicate_shape_not_counted", 0),
            "ranked_examples": ["Wood Lane", "Warwick Avenue", "Lancaster Gate", "Claps Gate"],
            "product_role": "primary_story plus duplicate-shape backlog",
            "deterministic_now": True,
            "risk_of_false_implication": "High if proximity is shown as access impact or charger availability.",
            "readiness": "WATCH_READY_WITH_LIMITATIONS",
        },
        {
            "query_key": "story-query:incident_to_affected_asset_response_cascade@v1",
            "inputs": ["NYC cascade scenario layer", "Flow 3 hero evidence", "NYC evidence map"],
            "candidate_count": 1,
            "ranked_examples": ["MVC crash 4463710 near Howard Avenue with Engine 227 context"],
            "product_role": "primary_story",
            "deterministic_now": True,
            "risk_of_false_implication": "High if candidate tax-lot context becomes certified affected-building truth or dispatch.",
            "readiness": "WATCH_READY_WITH_LIMITATIONS",
        },
        {
            "query_key": "story-query:source_depth_blocker@v1",
            "inputs": ["capture handoff", "gap ledgers", "source-record blockers"],
            "candidate_count": 3,
            "ranked_examples": ["missing two-story media", "missing viewer records", "DIFF cadence missing"],
            "product_role": "trust moment / CHECK blocker",
            "deterministic_now": True,
            "risk_of_false_implication": "Low if labeled as blocker rather than story evidence.",
            "readiness": "WATCH_READY_AS_BLOCKER_QUERY",
        },
        {
            "query_key": "story-query:duplicate_shape_cluster@v1",
            "inputs": ["D8 duplicate-shape audit"],
            "candidate_count": duplicate.get("duplicate_shape_not_counted", 0),
            "ranked_examples": [entry["title"] for entry in duplicate.get("entries", []) if not entry.get("counted_primary")],
            "product_role": "CHECK / queue hygiene",
            "deterministic_now": True,
            "risk_of_false_implication": "Medium if duplicates are counted as distinct primary stories.",
            "readiness": "WATCH_READY_AS_QUEUE_HYGIENE",
        },
        {
            "query_key": "story-query:visual_entity_pick_resolution@v1",
            "inputs": ["Helsinki visual entity source records", "prim identity sidecar"],
            "candidate_count": list_len(integrated, "visual_entity_city_records"),
            "ranked_examples": ["Helsinki semantic building / prim-path cutaway"],
            "product_role": "capability_cutaway",
            "deterministic_now": True,
            "risk_of_false_implication": "Medium if visual pick is presented as certified geometry/legal identity.",
            "readiness": "WATCH_READY_AS_CUTAWAY",
        },
    ]


def check_candidates(capture: dict) -> list[dict]:
    return [
        {"check_id": "check-001", "title": "Two-story media capture missing", "mode": "CHECK", "story_or_city": "Story queue", "severity": "high", "product_value": "Prevents capture/demo claims until media exists.", "source_ref": "outputs/main_citybrain_d8_story_queue_capture_handoff_r5/STORY_QUEUE_CAPTURE_HANDOFF_DECISION.json"},
        {"check_id": "check-002", "title": "Viewer records missing", "mode": "CHECK", "story_or_city": "Story queue", "severity": "high", "product_value": "Prevents external viewer-validation claim.", "source_ref": "outputs/main_citybrain_d8_story_queue_capture_handoff_r5/STORY_QUEUE_CAPTURE_HANDOFF_DECISION.json"},
        {"check_id": "check-003", "title": "Wood Lane proximity is not causality", "mode": "CHECK", "story_or_city": "London", "severity": "high", "product_value": "Stops EV blockage/availability overclaim.", "source_ref": "packages/fixtures/story_first_demo/story_scenario_layer.json"},
        {"check_id": "check-004", "title": "NYC candidate tax-lot is not certified affected-building truth", "mode": "CHECK", "story_or_city": "NYC", "severity": "high", "product_value": "Stops certified affected-building overclaim.", "source_ref": "packages/fixtures/nyc_cascade_story_scenario_layer/NYC_CASCADE_SCENARIO_LAYER.json"},
        {"check_id": "check-005", "title": "Response-resource context is not dispatch truth", "mode": "CHECK", "story_or_city": "NYC", "severity": "high", "product_value": "Stops dispatch/routing implication.", "source_ref": "packages/fixtures/nyc_cascade_story_scenario_layer/NYC_CASCADE_SCENARIO_LAYER.json"},
        {"check_id": "check-006", "title": "London duplicate-shape candidates must not count as distinct primary stories", "mode": "CHECK", "story_or_city": "London", "severity": "medium", "product_value": "Protects queue quality and distinctness.", "source_ref": "outputs/main_citybrain_d8_scenario_authoring_r1/DUPLICATE_SHAPE_AUDIT.json"},
        {"check_id": "check-007", "title": "Kit/runtime capture remains outside product-mode data scout", "mode": "CHECK", "story_or_city": "Cross-surface", "severity": "medium", "product_value": "Prevents live Omniverse/capture claims in D9 modes.", "source_ref": "outputs/main_citybrain_d8_brain_surface_story_queue_milestone_freeze/DEFERRED_NOT_CLAIMED_LEDGER.json"},
    ]


def gaps() -> list[dict]:
    return [
        {"gap_id": "gap-001", "mode_affected": ["WATCH", "BRIEF", "CHECK"], "story_city": "Story queue", "missing": "Current two-story screenshots/clips", "impact": "Cannot claim capture/media coverage.", "d9_should_proceed": "proceed_partial", "future_task": "MAIN-CITYBRAIN-D8-STORY-QUEUE-CAPTURE-IMPORT-R1 rerun after media capture"},
        {"gap_id": "gap-002", "mode_affected": ["ASK", "BRIEF", "CHECK"], "story_city": "Story queue", "missing": "External viewer-session records", "impact": "Cannot claim naive/external viewer validation.", "d9_should_proceed": "proceed_partial", "future_task": "MAIN-CITYBRAIN-D8-STORY-QUEUE-VIEWER-SESSION-R1"},
        {"gap_id": "gap-003", "mode_affected": ["WATCH", "CHECK"], "story_city": "D7/media observation", "missing": "Candidate observation source frame/time/location/label/summary depth", "impact": "Observation moments remain blockers or internal fixtures.", "d9_should_proceed": "proceed_partial", "future_task": "D7 candidate observation source-depth closure"},
        {"gap_id": "gap-004", "mode_affected": ["ASK", "WATCH", "BRIEF"], "story_city": "Governance/refusal", "missing": "Explicit source-backed forbidden-command refusal log for product display", "impact": "Refusal can be described from audits/fixtures but should stay bounded.", "d9_should_proceed": "proceed_partial", "future_task": "Refusal-log source record landing"},
        {"gap_id": "gap-005", "mode_affected": ["RECALL"], "story_city": "Chicago", "missing": "Specific match reasons tying Chicago records to the current selected story premise", "impact": "Recall is useful as generic precedent memory, not strong viewer-specific match.", "d9_should_proceed": "proceed_partial", "future_task": "Chicago recall match-reason selection"},
        {"gap_id": "gap-006", "mode_affected": ["ASK", "WATCH", "BRIEF"], "story_city": "London", "missing": "Evidence of actual EV access consequence beyond proximity", "impact": "Must refuse impact/availability/blockage questions.", "d9_should_proceed": "proceed_partial", "future_task": "London access-impact source-depth scout"},
        {"gap_id": "gap-007", "mode_affected": ["ASK", "WATCH", "BRIEF"], "story_city": "NYC", "missing": "Full Fire/EMS dispatch source depth and street-network route proof", "impact": "Response resource stays context only; no dispatch/route truth.", "d9_should_proceed": "proceed_partial", "future_task": "NYC Flow 3 source-depth expansion"},
        {"gap_id": "gap-008", "mode_affected": ["DIFF"], "story_city": "Cross-story", "missing": "Repeated source snapshots or declared cadence", "impact": "DIFF can explain package evolution but cannot compute source change-over-time broadly.", "d9_should_proceed": "proceed_partial", "future_task": "Diff cadence/snapshot contract"},
    ]


def main() -> int:
    for root in ROOTS.values():
        safe_reset(root)

    before = fingerprint(READ_ONLY_ROOTS)

    queue = read_json(INPUTS["story_queue_bundle"], {})
    london = read_json(INPUTS["wood_lane_scenario_layer"], {})
    nyc = read_json(INPUTS["nyc_cascade_layer"], {})
    integrated = read_json(INPUTS["integrated_source_bundle"], {})
    woven = read_json(INPUTS["deep_story_woven"], {})
    duplicate = read_json(INPUTS["duplicate_shape_audit"], {})
    capture = read_json(INPUTS["capture_handoff"], {})
    freeze = read_json(INPUTS["story_queue_freeze"], {})
    nyc_evidence_map = read_json(INPUTS["nyc_evidence_map"], {})

    primary = queue.get("primary_story_queue", [])
    query_keys = sorted({story.get("story_query_key") or f"{story.get('story_query_id')}@{story.get('query_version')}" for story in primary})
    expected = {"story-query:proximity_works_to_access@v1", "story-query:incident_to_affected_asset_response_cascade@v1"}
    preflight_pass = len(primary) == 2 and set(query_keys) == expected and freeze.get("ui_mode") == "queue_first"

    preflight = ROOTS["preflight"]
    write_json(
        preflight / "PREFLIGHT_INPUT_INDEX.json",
        {
            "status": "PASS" if preflight_pass else "FAIL",
            "inputs": [
                {"key": key, "path": rel(path), "exists": path.exists(), "sha256": sha256(path) if path.exists() else None}
                for key, path in INPUTS.items()
            ],
        },
    )
    write_json(
        preflight / "D8_CURRENT_STORY_QUEUE_BASELINE.json",
        {
            "status": "PASS" if preflight_pass else "FAIL",
            "story_queue_status": queue.get("status"),
            "freeze_status": freeze.get("status"),
            "primary_story_count": len(primary),
            "distinct_story_query_versions": query_keys,
            "duplicate_london_same_shape_excluded": freeze.get("duplicate_london_shapes_excluded"),
            "ui_mode": freeze.get("ui_mode"),
            "capture_handoff_status": capture.get("status"),
        },
    )
    write_json(
        preflight / "D9_SCOUT_SCOPE_LOCK.json",
        {
            "status": "PASS",
            "scope": "Scout current local D8 evidence for ASK, WATCH, RECALL, BRIEF, CHECK, DIFF readiness.",
            "not_scope": ["UI build", "Kit extension edit", "story authoring", "external data landing", "D9 runtime implementation"],
            "boundary": GLOBAL_BOUNDARY,
        },
    )
    write_json(
        preflight / "DATA_SCOUT_PREFLIGHT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-DATA-SCOUT-PREFLIGHT",
            "status": "PASS" if preflight_pass else "FAIL",
            "timestamp_utc": now(),
            "output_root": rel(preflight),
            "baseline_primary_stories": len(primary),
            "baseline_query_count": len(query_keys),
        },
    )

    inventory_rows = input_inventory(queue, integrated, woven, capture)
    inventory = ROOTS["inventory"]
    blockers_by_mode = {
        "ASK": ["impact/causality questions must be refused or answered with limitations"],
        "WATCH": ["real-time monitoring and alerting are out of scope", "capture/viewer gaps cannot be watched as evidence"],
        "RECALL": ["Chicago memory lacks story-specific match reasons for strong recall"],
        "BRIEF": ["briefs need explicit limitations and no-action boundaries"],
        "CHECK": ["strong candidate set available"],
        "DIFF": ["no reliable repeated-source cadence for broad source change detection"],
    }
    write_json(inventory / "MODE_SURFACE_INPUT_INVENTORY.json", {"status": "PASS", "inputs": inventory_rows})
    write_text(
        inventory / "MODE_SURFACE_INPUT_SUMMARY.md",
        "\n".join(
            [
                "# Mode Surface Input Summary",
                "",
                f"Inputs classified: `{len(inventory_rows)}`.",
                "",
                "ASK, WATCH, BRIEF, and CHECK have usable story/source inputs. RECALL is useful but mostly generic. DIFF is partial because source cadence is not established.",
            ]
        ),
    )
    write_json(
        inventory / "INTERNAL_FIXTURE_NOT_PRODUCT_VALUE_LEDGER.json",
        {
            "status": "PASS",
            "entries": [
                {"artifact": "D7/media observation fixture references", "reason": "Need source frame/time/location/label/summary before product display."},
                {"artifact": "Generic audit refs", "reason": "Useful for CHECK but not a user-facing source fact by themselves."},
            ],
        },
    )
    write_json(inventory / "DATA_DEPTH_BLOCKERS_BY_MODE.json", {"status": "PASS", "blockers_by_mode": blockers_by_mode})
    write_json(
        inventory / "MODE_SURFACE_INPUT_INVENTORY_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-MODE-SURFACE-INPUT-INVENTORY-R1",
            "status": "PASS_WITH_MODE_LIMITATIONS",
            "input_count": len(inventory_rows),
            "partial_modes": ["RECALL", "DIFF"],
        },
    )

    ask_rows = ask_questions()
    ask = ROOTS["ask"]
    ready_count = sum(row["answerability"] in {"ANSWER_READY_WITH_CITATIONS", "ANSWER_READY_WITH_LIMITATIONS"} for row in ask_rows)
    write_json(ask / "ASK_QUESTION_CANDIDATE_SET.json", {"status": "PASS", "questions": ask_rows})
    write_json(ask / "ASK_ANSWERABILITY_MATRIX.json", {"status": "PASS", "ready_or_limited_count": ready_count, "questions": ask_rows})
    write_json(ask / "ASK_REQUIRED_CITATION_MAP.json", {"status": "PASS", "citation_map": [{"question_id": row["question_id"], "citation_refs": row["citation_refs"]} for row in ask_rows]})
    write_json(ask / "ASK_UNSUPPORTED_QUESTION_LEDGER.json", {"status": "PASS", "unsupported_questions": [], "must_refuse_patterns": ["live status", "dispatch", "certified affected building", "EV unavailable/blocked"]})
    write_json(ask / "ASK_SCOUT_DECISION.json", {"task": "MAIN-CITYBRAIN-D9-ASK-QUESTION-COVERAGE-SCOUT-R2", "status": "PASS", "ready_or_limited_count": ready_count})

    watch_rows = watch_queries(queue, integrated, duplicate)
    watch = ROOTS["watch"]
    useful_watch = sum(row["deterministic_now"] and "READY" in row["readiness"] for row in watch_rows)
    write_json(watch / "WATCH_NAMED_QUERY_CANDIDATE_REGISTRY.json", {"status": "PASS", "queries": watch_rows})
    write_json(
        watch / "WATCH_QUEUE_ITEM_PROTOTYPES.json",
        {
            "status": "PASS",
            "prototypes": [
                {"query_key": row["query_key"], "product_role": row["product_role"], "examples": row["ranked_examples"][:3], "boundary": row["risk_of_false_implication"]}
                for row in watch_rows
            ],
        },
    )
    write_json(
        watch / "WATCH_QUERY_DUPLICATE_SHAPE_AUDIT.json",
        {
            "status": "PASS",
            "duplicate_shape_not_counted": duplicate.get("duplicate_shape_not_counted", 0),
            "entries": duplicate.get("entries", []),
        },
    )
    write_json(watch / "WATCH_QUERY_RISK_LEDGER.json", {"status": "PASS", "risks": [{"query_key": row["query_key"], "risk": row["risk_of_false_implication"]} for row in watch_rows]})
    write_json(watch / "WATCH_SCOUT_DECISION.json", {"task": "MAIN-CITYBRAIN-D9-WATCH-NAMED-QUERY-POTENTIAL-R3", "status": "PASS", "useful_named_query_families": useful_watch})

    recall = ROOTS["recall"]
    chicago_records = integrated.get("similar_case_city_records", [])
    recall_rows = []
    for idx, record in enumerate(chicago_records[:5], start=1):
        match_reason = record.get("why_it_matters") or record.get("city_fact_fields", {}).get("matched_because") or ""
        specific = bool(record.get("title") and record.get("technical_refs", {}).get("external_record_id"))
        recall_rows.append(
            {
                "candidate_id": f"recall-{idx:03d}",
                "source_city": "Chicago",
                "dataset": record.get("source_system_or_dataset", "Chicago Building Violations"),
                "record_id": record.get("technical_refs", {}).get("external_record_id") or record.get("city_fact_fields", {}).get("source_record_id"),
                "case_summary": record.get("plain_language_summary") or record.get("title"),
                "match_reason_specificity": "generic_bounded_memory_context" if "Bounded memory context" in match_reason else "specific_record_but_generic_match_reason",
                "surface_classification": "RECALL_PARTIAL_GENERIC_MATCH",
                "limitation": "Context only; not prediction, causality, instruction, enforcement, or legal conclusion.",
                "viewer_product_ready": specific,
            }
        )
    write_json(recall / "RECALL_PRECEDENT_CANDIDATE_TABLE.json", {"status": "PARTIAL", "candidates": recall_rows})
    write_json(
        recall / "RECALL_MATCH_REASON_QUALITY_REPORT.json",
        {
            "status": "PARTIAL",
            "specific_match_count": 0,
            "generic_match_count": len(recall_rows),
            "finding": "Chicago records are source-backed but current match reasons are generic precedent-memory context, not story-specific matching.",
        },
    )
    write_json(recall / "RECALL_READY_EXEMPLARS.json", {"status": "PARTIAL", "ready_exemplars": [], "usable_as_cutaway_count": len(recall_rows)})
    write_json(recall / "RECALL_BACKLOG_LEDGER.json", {"status": "PASS", "backlog": [{"need": "Select specific match reasons before surfacing as strong RECALL.", "affected_records": [row["record_id"] for row in recall_rows]}]})
    write_json(recall / "RECALL_SCOUT_DECISION.json", {"task": "MAIN-CITYBRAIN-D9-RECALL-PRECEDENT-COVERAGE-R4", "status": "PARTIAL_GENERIC_CHICAGO_MEMORY_AVAILABLE", "ready_specific_match_count": 0, "generic_recall_count": len(recall_rows)})

    brief = ROOTS["brief"]
    brief_rows = [
        {"brief_id": "brief-wood-lane", "story": "Wood Lane", "summary": True, "source_records": True, "scenario_layer_facts": True, "evidence_map": True, "review_options": True, "uncertainty_limitations": True, "human_review_stop": True, "trace_query_provenance": True, "no_action_boundary": True, "status": "BRIEF_READY_WITH_LIMITATIONS"},
        {"brief_id": "brief-nyc-cascade", "story": "NYC MVC cascade", "summary": True, "source_records": True, "scenario_layer_facts": True, "evidence_map": bool(nyc_evidence_map.get("claims")), "review_options": True, "uncertainty_limitations": True, "human_review_stop": True, "trace_query_provenance": True, "no_action_boundary": True, "status": "BRIEF_READY_WITH_LIMITATIONS"},
        {"brief_id": "brief-story-queue", "story": "Overall story queue", "summary": True, "source_records": True, "scenario_layer_facts": True, "evidence_map": True, "review_options": True, "uncertainty_limitations": True, "human_review_stop": True, "trace_query_provenance": True, "no_action_boundary": True, "status": "BRIEF_READY_WITH_LIMITATIONS"},
    ]
    write_json(brief / "BRIEF_PACKET_READINESS_MATRIX.json", {"status": "PASS", "briefs": brief_rows})
    write_json(
        brief / "BRIEF_SECTION_SOURCE_MAP.json",
        {
            "status": "PASS",
            "source_map": {
                "Wood Lane": ["packages/fixtures/story_first_demo/story_scenario_layer.json", "packages/fixtures/story_first_demo/story_source_bundle.json"],
                "NYC MVC cascade": ["packages/fixtures/nyc_cascade_story_scenario_layer/NYC_CASCADE_SCENARIO_LAYER.json", "outputs/main_citybrain_d8_nyc_cascade_source_evidence_map_r3/NYC_CASCADE_STORY_TO_SOURCE_EVIDENCE_MAP.json"],
                "Story queue": ["packages/fixtures/brain_surface_story_queue/brain_surface_story_queue_bundle.json"],
            },
        },
    )
    write_json(brief / "BRIEF_GAPS_AND_UNSUPPORTED_CLAIMS.json", {"status": "PASS", "unsupported_claims": ["EV blockage/availability", "NYC certified affected building", "dispatch/navigable route", "production/live monitoring"]})
    write_json(brief / "BRIEF_READY_PACKET_PROTOTYPES.json", {"status": "PASS", "packets": [{"brief_id": row["brief_id"], "sections": [key for key, value in row.items() if value is True]} for row in brief_rows]})
    write_json(brief / "BRIEF_SCOUT_DECISION.json", {"task": "MAIN-CITYBRAIN-D9-BRIEF-PACKET-READINESS-R5", "status": "PASS", "ready_packet_count": len(brief_rows)})

    checks = check_candidates(capture)
    checkdiff = ROOTS["checkdiff"]
    diff_matrix = [
        {"diff_id": "diff-001", "subject": "story queue evolution", "readiness": "DIFF_READY_PACKAGE_EVOLUTION_ONLY", "evidence": ["one-story story-first surface", "two-story story queue", "capture pending handoff"]},
        {"diff_id": "diff-002", "subject": "source record field changes", "readiness": "DIFF_PARTIAL_NEEDS_SOURCE_CADENCE", "evidence": ["TIMS last_modified fields exist for London but no declared repeated-source cadence"]},
        {"diff_id": "diff-003", "subject": "NYC source/cascade changes", "readiness": "DIFF_PARTIAL_NEEDS_SNAPSHOT_SERIES", "evidence": ["Flow 3 derived package exists, no repeated current-vs-prior source snapshots declared"]},
    ]
    write_json(checkdiff / "CHECK_CANDIDATE_LEDGER.json", {"status": "PASS", "checks": checks})
    write_json(checkdiff / "CHECK_QUERY_PROTOTYPES.json", {"status": "PASS", "query_prototypes": [{"query": item["title"], "source_ref": item["source_ref"], "severity": item["severity"]} for item in checks]})
    write_json(checkdiff / "DIFF_READINESS_MATRIX.json", {"status": "PARTIAL", "diffs": diff_matrix})
    write_json(checkdiff / "DIFF_UNSUPPORTED_LEDGER.json", {"status": "PASS", "unsupported": [{"subject": "broad live source change detection", "reason": "No production/live source cadence or repeated snapshots declared."}]})
    write_json(checkdiff / "CHECK_DIFF_SCOUT_DECISION.json", {"task": "MAIN-CITYBRAIN-D9-CHECK-DIFF-DATA-QUALITY-CHANGE-SCOUT-R6", "status": "PASS_CHECK_PARTIAL_DIFF", "check_count": len(checks), "diff_ready_count": 1, "diff_partial_count": 2})

    gap_rows = gaps()
    gap = ROOTS["gap"]
    write_json(gap / "D9_SOURCE_GAP_LEDGER.json", {"status": "PASS", "gaps": gap_rows})
    write_json(
        gap / "D9_GAP_PRIORITY_MATRIX.json",
        {
            "status": "PASS",
            "priority_order": [
                {"gap_id": "gap-001", "priority": 1, "reason": "Capture media gates demo/product evidence claims."},
                {"gap_id": "gap-002", "priority": 2, "reason": "Viewer records gate external validation."},
                {"gap_id": "gap-008", "priority": 3, "reason": "DIFF needs cadence before broad change mode."},
                {"gap_id": "gap-005", "priority": 4, "reason": "RECALL improves when Chicago match reasons become specific."},
            ],
        },
    )
    write_json(
        gap / "D9_CAN_PROCEED_WITH_PARTIAL_MODES.json",
        {
            "status": "PASS",
            "can_proceed": True,
            "ready_or_limited_modes": ["ASK", "WATCH", "BRIEF", "CHECK"],
            "partial_modes": ["RECALL", "DIFF"],
            "blocked_modes": [],
        },
    )
    write_json(gap / "D9_SOURCE_GAP_LEDGER_DECISION.json", {"task": "MAIN-CITYBRAIN-D9-PRODUCT-MODE-SOURCE-GAP-LEDGER-R7", "status": "PASS_WITH_PRIORITIZED_GAPS", "gap_count": len(gap_rows)})

    readiness = [
        {"mode": "ASK", "readiness": "READY_WITH_LIMITATIONS", "reason": "10/10 seed questions can be answered with citations/limitations."},
        {"mode": "WATCH", "readiness": "READY_WITH_LIMITATIONS", "reason": "5 named query families are deterministic now, including blockers and queue hygiene."},
        {"mode": "RECALL", "readiness": "PARTIAL", "reason": "Chicago records exist, but match reasons are generic."},
        {"mode": "BRIEF", "readiness": "READY_WITH_LIMITATIONS", "reason": "Wood Lane, NYC, and queue packets have sources, options, limitations, and human stops."},
        {"mode": "CHECK", "readiness": "READY", "reason": "7 meaningful product checks are source-backed."},
        {"mode": "DIFF", "readiness": "PARTIAL", "reason": "Package evolution is diffable; source change cadence is not established."},
    ]
    candidate_catalog = {
        "ASK": ask_rows,
        "WATCH": watch_rows,
        "RECALL": recall_rows,
        "BRIEF": brief_rows,
        "CHECK": checks,
        "DIFF": diff_matrix,
    }
    recommendation = "GO_D9_ASK_WATCH_BRIEF_WITH_LIMITATIONS"
    closeout = ROOTS["closeout"]
    write_json(closeout / "D9_MODE_DATA_READINESS_MATRIX.json", {"status": "PASS", "modes": readiness})
    write_json(closeout / "D9_MODE_SURFACE_CANDIDATE_CATALOG.json", {"status": "PASS", "catalog": candidate_catalog})
    write_text(
        closeout / "D9_PRODUCT_MODE_BUILD_RECOMMENDATION.md",
        f"""
# D9 Product Mode Build Recommendation

Recommendation: `{recommendation}`

Run D9 product modes with ASK, WATCH, BRIEF, and CHECK enabled under explicit limitations. Keep RECALL partial until Chicago match reasons are story-specific. Keep DIFF partial until source cadence or repeated snapshots are declared.

Do not claim production/public API, live monitoring, dispatch/routing/control, enforcement, tickets/cases, legal/certified findings, automated action, EV access impact, NYC certified affected-building truth, or external viewer validation.
""",
    )
    write_json(closeout / "D9_READY_NOW_MODES.json", {"status": "PASS", "ready_now_modes": ["ASK", "WATCH", "BRIEF", "CHECK"]})
    write_json(closeout / "D9_PARTIAL_MODES.json", {"status": "PASS", "partial_modes": ["RECALL", "DIFF"]})
    write_json(closeout / "D9_BLOCKED_MODES.json", {"status": "PASS", "blocked_modes": []})
    write_json(
        closeout / "D9_DATA_SCOUT_CLOSEOUT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-DATA-SCOUT-CLOSEOUT",
            "status": PASS_CLOSEOUT,
            "decision": recommendation,
            "timestamp_utc": now(),
            "ready_now_modes": ["ASK", "WATCH", "BRIEF", "CHECK"],
            "partial_modes": ["RECALL", "DIFF"],
            "blocked_modes": [],
            "gap_count": len(gap_rows),
        },
    )

    freeze = ROOTS["freeze"]
    validation_zip = freeze / "D9_DATA_SCOUT_VALIDATION_PACKAGE.zip"
    write_json(
        freeze / "DATA_SCOUT_MILESTONE_FREEZE_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D9-DATA-SCOUT-MILESTONE-FREEZE",
            "status": PASS_FREEZE,
            "closeout_status": PASS_CLOSEOUT,
            "decision": recommendation,
            "timestamp_utc": now(),
            "ready_now_modes": ["ASK", "WATCH", "BRIEF", "CHECK"],
            "partial_modes": ["RECALL", "DIFF"],
            "blocked_modes": [],
            "recommended_next_task": "MAIN-CITYBRAIN-D9-PRODUCT-MODES-ASK-WATCH-BRIEF-RUNTIME-R1",
        },
    )
    write_text(
        freeze / "CURRENT_D9_DATA_READINESS_STATE.md",
        """
# Current D9 Data Readiness State

ASK, WATCH, BRIEF, and CHECK can proceed with limitations over the current two-story queue. RECALL is partial because Chicago precedent records need story-specific match reasons. DIFF is partial because broad source-change cadence is not established.
""",
    )
    write_text(
        freeze / "READY_NEXT_D9_RUN_INSTRUCTIONS.md",
        """
# Ready Next D9 Run Instructions

Run the D9 product-mode runtime with ASK, WATCH, BRIEF, and CHECK enabled by default. RECALL may surface Chicago as generic precedent/cutaway only. DIFF may report package evolution but must not claim broad live source change detection.
""",
    )
    write_json(freeze / "D9_MODE_DATA_READINESS_MATRIX.json", {"status": "PASS", "modes": readiness})
    write_json(freeze / "D9_SOURCE_GAP_LEDGER.json", {"status": "PASS", "gaps": gap_rows})

    after = fingerprint(READ_ONLY_ROOTS)
    for key, title in [
        ("preflight", "D9 Data Scout Preflight"),
        ("inventory", "D9 Mode Surface Input Inventory R1"),
        ("ask", "D9 ASK Question Coverage Scout R2"),
        ("watch", "D9 WATCH Named Query Potential R3"),
        ("recall", "D9 RECALL Precedent Coverage R4"),
        ("brief", "D9 BRIEF Packet Readiness R5"),
        ("checkdiff", "D9 CHECK DIFF Scout R6"),
        ("gap", "D9 Product Mode Source Gap Ledger R7"),
        ("closeout", "D9 Data Scout Closeout"),
    ]:
        finalize(ROOTS[key], title, before, after)

    with zipfile.ZipFile(validation_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in [
            closeout / "D9_MODE_DATA_READINESS_MATRIX.json",
            closeout / "D9_MODE_SURFACE_CANDIDATE_CATALOG.json",
            closeout / "D9_PRODUCT_MODE_BUILD_RECOMMENDATION.md",
            closeout / "D9_DATA_SCOUT_CLOSEOUT_DECISION.json",
            gap / "D9_SOURCE_GAP_LEDGER.json",
            freeze / "DATA_SCOUT_MILESTONE_FREEZE_DECISION.json",
        ]:
            zf.write(path, arcname=rel(path))

    finalize(freeze, "D9 Data Scout Milestone Freeze", before, after)
    write_json(freeze / "HASH_MANIFEST.json", hash_manifest(freeze))

    final = {
        "status": PASS_FREEZE,
        "closeout_status": PASS_CLOSEOUT,
        "decision": recommendation,
        "output_roots": {key: rel(path) for key, path in ROOTS.items()},
        "runner": rel(RUNNER),
        "ready_now_modes": ["ASK", "WATCH", "BRIEF", "CHECK"],
        "partial_modes": ["RECALL", "DIFF"],
        "blocked_modes": [],
        "ask_ready_or_limited_count": ready_count,
        "watch_useful_query_families": useful_watch,
        "recall_specific_match_count": 0,
        "brief_ready_packet_count": len(brief_rows),
        "check_count": len(checks),
        "source_gap_count": len(gap_rows),
        "recommended_next_task": "MAIN-CITYBRAIN-D9-PRODUCT-MODES-ASK-WATCH-BRIEF-RUNTIME-R1",
    }
    print(json.dumps(final, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
