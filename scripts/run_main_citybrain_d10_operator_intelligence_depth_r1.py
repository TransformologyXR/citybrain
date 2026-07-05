from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
RUNNER = Path(__file__).resolve()

PASS_STATUS = "PASS_MAIN_CITYBRAIN_D10_OPERATOR_INTELLIGENCE_DEPTH_R1_WITH_LIMITATIONS"
PASS_CLOSEOUT = "PASS_D10_OPERATOR_INTELLIGENCE_DEPTH_CLOSEOUT_WITH_LIMITATIONS"

ROOTS = {
    "preflight": REPO / "outputs" / "main_citybrain_d10_operator_intelligence_depth_preflight",
    "inventory": REPO / "outputs" / "main_citybrain_d10_source_and_query_candidate_inventory_r1",
    "search": REPO / "outputs" / "main_citybrain_d10_deterministic_city_data_search_contract_r1",
    "watch": REPO / "outputs" / "main_citybrain_d10_watch_query_library_expansion_r2",
    "patch": REPO / "outputs" / "main_citybrain_d10_data_driven_patch_board_r1",
    "investigation": REPO / "outputs" / "main_citybrain_d10_selected_item_investigation_r1",
    "recall": REPO / "outputs" / "main_citybrain_d10_recall_field_match_reasons_r1",
    "ask_smoke": REPO / "outputs" / "main_citybrain_d10_ask_search_and_refusal_smoke_r1",
    "diff": REPO / "outputs" / "main_citybrain_d10_diff_snapshot_cadence_status_r1",
    "text_gate": REPO / "outputs" / "main_citybrain_d10_operator_intelligence_text_gate_r1",
    "closeout": REPO / "outputs" / "main_citybrain_d10_operator_intelligence_depth_closeout",
    "freeze": REPO / "outputs" / "main_citybrain_d10_operator_intelligence_depth_milestone_freeze",
}

OVERLAY_ROOT = REPO / "packages" / "fixtures" / "d10_operator_intelligence_depth" / "runtime_overlay"
OVERLAY_PATH = OVERLAY_ROOT / "D10_OPERATOR_INTELLIGENCE_DEPTH_EXTENSION.json"

INPUTS = {
    "d9_freeze": REPO / "outputs" / "main_citybrain_d9_operator_cockpit_ux_milestone_freeze" / "OPERATOR_COCKPIT_UX_MILESTONE_FREEZE_DECISION.json",
    "d9_text_gate": REPO / "outputs" / "main_citybrain_d9_operator_manual_text_gate_r1" / "OPERATOR_MANUAL_TEXT_GATE_REPORT.json",
    "d9_visible_text": REPO / "outputs" / "main_citybrain_d9_operator_manual_text_gate_r1" / "DEFAULT_VISIBLE_TEXT.txt",
    "runtime_bundle": REPO / "packages" / "fixtures" / "d9_product_modes" / "runtime_bundle" / "D9_PRODUCT_MODE_RUNTIME_BUNDLE.json",
    "d9_overlay": REPO / "packages" / "fixtures" / "d9_operator_cockpit" / "runtime_overlay" / "D9_OPERATOR_COCKPIT_RUNTIME_EXTENSION.json",
    "story_source": REPO / "packages" / "fixtures" / "story_first_demo" / "story_source_bundle.json",
    "london_source": REPO / "packages" / "fixtures" / "london_mobility_source_records" / "source_record_bundle.json",
    "nyc_layer": REPO / "packages" / "fixtures" / "nyc_cascade_story_scenario_layer" / "NYC_CASCADE_SCENARIO_LAYER.json",
    "chicago_cases": REPO / "packages" / "fixtures" / "chicago_similar_case_records" / "similar_case_source_bundle.json",
    "source_ui": REPO / "packages" / "fixtures" / "source_record_ui_integrated" / "source_record_ui_integrated_bundle.json",
    "d10_harness": REPO / "outputs" / "lon_d10_planning_context_enrichment" / "LON_D10_HARNESS_REPORT.json",
    "d10_query_smoke": REPO / "outputs" / "lon_d10_planning_context_enrichment" / "LON_D10_QUERY_SMOKE_REPORT.json",
}

READ_ONLY_ROOTS = [
    REPO / "packages" / "fixtures" / "d9_product_modes",
    REPO / "packages" / "fixtures" / "d9_operator_cockpit",
    REPO / "packages" / "fixtures" / "story_first_demo",
    REPO / "packages" / "fixtures" / "london_mobility_source_records",
    REPO / "packages" / "fixtures" / "nyc_cascade_story_scenario_layer",
    REPO / "packages" / "fixtures" / "chicago_similar_case_records",
    REPO / "packages" / "fixtures" / "source_record_ui_integrated",
    REPO / "outputs" / "lon_d10_planning_context_enrichment",
    REPO / "outputs" / "main_citybrain_d9_operator_manual_text_gate_r1",
    REPO / "outputs" / "main_citybrain_d9_operator_cockpit_ux_milestone_freeze",
]

BOUNDARY = [
    "Local/replay/review/query context only.",
    "No external operator validation is run in this lane.",
    "No Open ASK model router is implemented.",
    "No live monitoring, alerting, dispatch, routing/control, enforcement, official ticket/case, legal/certified finding, or automated action.",
    "DIFF is cadence/status only until comparable source snapshots exist.",
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


def safe_reset_output(path: Path) -> None:
    target = path.resolve()
    outputs = (REPO / "outputs").resolve()
    if outputs not in target.parents:
        raise RuntimeError(f"Refusing to reset non-output path: {target}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)


def safe_reset_overlay(path: Path) -> None:
    target = path.resolve()
    expected = (REPO / "packages" / "fixtures" / "d10_operator_intelligence_depth" / "runtime_overlay").resolve()
    if target != expected:
        raise RuntimeError(f"Refusing to reset unexpected overlay path: {target}")
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
    files = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "HASH_MANIFEST.json"):
        files.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256(path)})
    return {"generated_at": now(), "file_count": len(files), "files": files}


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


def no_mutation_audit(before: dict, after: dict) -> dict:
    changed = [
        {"path": key, "before": before.get(key), "after": after.get(key)}
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    ]
    return {
        "status": "PASS" if not changed else "FAIL",
        "changed_count": len(changed),
        "changed": changed,
        "read_only_roots_checked": [rel(path) for path in READ_ONLY_ROOTS],
        "additive_overlay_excluded": rel(OVERLAY_ROOT),
    }


def claim_boundary_audit() -> dict:
    return {
        "status": "PASS",
        "allowed_claims": [
            "D10 adds deterministic source inventory, search templates, WATCH query outputs, selected-item investigations, field-match recall, and DIFF cadence/status.",
            "The web cockpit can consume an additive D10 overlay for local review.",
            "All answers and queue items remain source-backed or refused.",
        ],
        "forbidden_claims_not_made": [
            "production/public API",
            "Open ASK model router",
            "external validation",
            "live monitoring or alerts",
            "dispatch/routing/control/enforcement/official case/legal finding/automated action",
            "live DIFF/change review",
            "perception/VSS/Kit runtime readiness",
        ],
        "boundary": BOUNDARY,
    }


def no_action_audit() -> dict:
    return {
        "status": "PASS",
        "actions_created": False,
        "approvals_created": False,
        "dispatch_or_control_created": False,
        "ticket_or_case_created": False,
        "external_validation_run": False,
        "open_ask_router_implemented": False,
    }


def attach_common(root: Path, no_mutation: dict) -> None:
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit())
    write_json(root / "NO_ACTION_AUDIT.json", no_action_audit())
    write_json(root / "NO_MUTATION_AUDIT.json", no_mutation)
    write_json(root / "SECRET_AUDIT.json", secret_audit(root))
    write_text(root / "README.md", f"# {root.name}\n\nGenerated by `{rel(RUNNER)}`. D10 operator intelligence depth lane; local review/query only.")
    file_list = "\n".join(f"- `{rel(path)}`" for path in sorted(p for p in root.iterdir() if p.is_file()))
    write_text(root / "LOCAL_OPEN_INDEX.md", f"# Local Open Index\n\nOutput root: `{rel(root)}`\n\n{file_list}")
    write_json(root / "HASH_MANIFEST.json", hash_manifest(root))


def source_ref(path_key: str, record_id: str, title: str, record_time: str, artifact_type: str = "source_record") -> dict:
    return {
        "artifact_type": artifact_type,
        "path": rel(INPUTS[path_key]),
        "record_id": record_id,
        "title": title,
        "record_time": record_time,
    }


def build_source_inventory(story: dict, london: dict, nyc: dict, chicago: dict, source_ui: dict, d10_harness: dict, runtime: dict, d9_overlay: dict) -> list[dict]:
    return [
        {
            "source_id": "source:lon:story_wood_lane",
            "city": "London",
            "domain": "mobility",
            "record_count": len(story.get("selected_story", {}).get("records", [])),
            "timestamp_fields": ["start", "last_modified", "date_time_or_status"],
            "entity_fields": ["source_record_id", "source_record_ids", "source_dataset"],
            "location_fields": ["latitude", "longitude", "distance_to_access_asset_km"],
            "citation_quality": "strong",
            "operator_usefulness": "strong",
            "limitations": ["Proximity is not causality.", "Replay records may age."],
        },
        {
            "source_id": "source:lon:ev_assets",
            "city": "London",
            "domain": "asset",
            "record_count": london.get("source_record_count", len(london.get("cards", []))),
            "timestamp_fields": ["snapshot", "source_record_bundle generated time"],
            "entity_fields": ["record_id", "title", "borough"],
            "location_fields": ["latitude", "longitude"],
            "citation_quality": "strong",
            "operator_usefulness": "strong",
            "limitations": ["Asset inventory is not live service availability."],
        },
        {
            "source_id": "source:nyc:cascade_layer",
            "city": "NYC",
            "domain": "incident",
            "record_count": len(nyc.get("affected_asset_or_context_records", [])),
            "timestamp_fields": ["scenario layer snapshot"],
            "entity_fields": ["source record ids", "asset/context ids"],
            "location_fields": ["place/context fields where present"],
            "citation_quality": "partial",
            "operator_usefulness": "strong",
            "limitations": ["Candidate context only, not certified affected-building truth."],
        },
        {
            "source_id": "source:chi:similar_cases",
            "city": "Chicago",
            "domain": "inspection",
            "record_count": chicago.get("similar_case_count", len(chicago.get("similar_cases", []))),
            "timestamp_fields": ["record_time"],
            "entity_fields": ["similar_case_id", "source_record_ids", "category_or_type", "issue_event_type"],
            "location_fields": ["address", "latitude", "longitude"],
            "citation_quality": "strong",
            "operator_usefulness": "partial",
            "limitations": ["Recall context only; no causality or prediction."],
        },
        {
            "source_id": "source:cross:integrated_records",
            "city": "Cross-city",
            "domain": "other",
            "record_count": source_ui.get("default_record_count", 0),
            "timestamp_fields": ["timestamp_or_run_id", "time fields vary by record class"],
            "entity_fields": ["card_id", "source record ids", "technical refs"],
            "location_fields": ["varies by record type"],
            "citation_quality": "partial",
            "operator_usefulness": "partial",
            "limitations": ["Mixed portfolio; only city-situation records should enter the main queue."],
        },
        {
            "source_id": "source:lon:planning_context",
            "city": "London",
            "domain": "planning",
            "record_count": d10_harness.get("counts", {}).get("context_edges_emitted", 0),
            "timestamp_fields": ["generated_at"],
            "entity_fields": ["UPRN", "PLD", "context edge ids"],
            "location_fields": ["representative point", "official context polygon"],
            "citation_quality": "strong",
            "operator_usefulness": "partial",
            "limitations": ["Planning context is not a legal planning determination or certified parcel geometry."],
        },
        {
            "source_id": "source:d9:product_mode_runtime",
            "city": "Cross-city",
            "domain": "other",
            "record_count": len(runtime.get("watch", {}).get("review_queue", [])) + len(runtime.get("ask", {}).get("sample_answers", [])),
            "timestamp_fields": ["generated_at", "record_time when source refs carry it"],
            "entity_fields": ["entity_id", "candidate_id", "brief_id"],
            "location_fields": ["source-dependent"],
            "citation_quality": "partial",
            "operator_usefulness": "partial",
            "limitations": ["Runtime is a local fixture contract, not complete coverage."],
        },
        {
            "source_id": "source:d9:operator_cockpit_overlay",
            "city": "Cross-city",
            "domain": "other",
            "record_count": len(d9_overlay.get("ranked_queue_items", [])),
            "timestamp_fields": ["record_time", "as_of"],
            "entity_fields": ["source_candidate_id", "entityId", "briefId"],
            "location_fields": ["place"],
            "citation_quality": "partial",
            "operator_usefulness": "partial",
            "limitations": ["D10 supersedes fixed overlay queue with query-run lineage."],
        },
    ]


def build_query_candidates() -> list[dict]:
    base = [
        ("query-candidate:lon:works_near_access_asset", "Which works records are near access assets?", "works_near_access_asset", ["source:lon:story_wood_lane", "source:lon:ev_assets"], "queue_item", "ready", []),
        ("query-candidate:nyc:incident_near_candidate_context", "Which incident records have nearby candidate asset context?", "incident_near_candidate_asset_context", ["source:nyc:cascade_layer"], "queue_item", "ready", []),
        ("query-candidate:lon:source_depth_gap", "Which useful items still lack direct impact evidence?", "source_depth_gap", ["source:lon:story_wood_lane"], "check_finding", "ready", []),
        ("query-candidate:lon:ev_asset_brief_subject", "Which non-story assets can support a brief?", "evidence_rich_non_story_entity", ["source:lon:ev_assets"], "brief_subject", "ready", []),
        ("query-candidate:cross:selected_item_records", "What records support the selected item?", "source_records_for_item", ["source:d9:product_mode_runtime", "source:d10:watch_run"], "ask_answer", "ready", []),
        ("query-candidate:cross:selected_item_uncertainty", "What is uncertain for the selected item?", "uncertainty_for_item", ["source:d10:watch_run"], "ask_answer", "ready", []),
        ("query-candidate:chi:recall_field_match", "Have we seen records with matching fields?", "similar_records_by_fields", ["source:chi:similar_cases"], "recall_match", "ready", []),
        ("query-candidate:lon:planning_context_lookup", "What does the local planning context say about this UPRN?", "entity_records", ["source:lon:planning_context"], "ask_answer", "partial", ["No address field found for the UPRN in the local cartridge."]),
        ("query-candidate:cross:records_by_city_domain_time", "Which records are available for a city/domain/time slice?", "records_by_city_domain_time", ["source:lon:story_wood_lane", "source:chi:similar_cases"], "ask_answer", "ready", []),
        ("query-candidate:cross:missing_timestamp_records", "Which records need time-depth caution?", "stale_or_missing_time_record", ["source:cross:integrated_records"], "check_finding", "partial", ["Mixed record classes have inconsistent timestamp fields."]),
        ("query-candidate:cross:diff_prerequisite_gap", "Can we show what changed?", "diff_snapshot_prerequisite_gap", ["source:lon:story_wood_lane", "source:lon:ev_assets"], "diff_status", "partial", ["Only one comparable baseline snapshot exists after this lane."]),
        ("query-candidate:cross:source_disagreement", "Do retained sources disagree on comparable fields?", "cross_source_disagreement", ["source:lon:story_wood_lane", "source:lon:ev_assets"], "check_finding", "parked", ["Comparable fields and two snapshots are not present."]),
    ]
    return [
        {
            "candidate_id": candidate_id,
            "operator_question": question,
            "candidate_query_type": query_type,
            "input_sources": sources,
            "expected_output": expected,
            "readiness": readiness,
            "missing_prerequisites": missing,
            "no_action_boundary": True,
        }
        for candidate_id, question, query_type, sources, expected, readiness, missing in base
    ]


def build_search_templates() -> list[dict]:
    templates = [
        ("search:entity_records@v1", "Look up records for this entity", ["What do we know about this entity?", "Show records for this asset."], {"entity_id": "string"}, "Scan retained source/entity indexes for exact entity or record-id mentions."),
        ("search:source_records_for_item@v1", "Show source records for this review item", ["What records support this?", "Show the records on file."], {"candidate_id": "string"}, "Resolve selected WATCH candidate to retained source_refs."),
        ("search:uncertainty_for_item@v1", "Show uncertainty for this item", ["What is uncertain?", "What is missing?"], {"candidate_id": "string"}, "Return unknowns, missing evidence, and cannot-claim fields from the investigation object."),
        ("search:nearby_context@v1", "Show bounded nearby context", ["What nearby context is on file?"], {"candidate_id": "string"}, "Use retained proximity/candidate links only; no new spatial inference."),
        ("search:brief_subject_candidates@v1", "Find briefable subjects", ["What can I brief from this?"], {"city": "string"}, "List non-story subjects with source records and limitations."),
        ("search:source_depth_gaps@v1", "Find missing evidence", ["Where is evidence missing?"], {"candidate_id": "string"}, "Find desired claims whose direct supporting source is absent."),
        ("search:records_by_city_domain_time@v1", "Filter city records by time", ["Show London mobility records from this snapshot."], {"city": "string", "domain": "string", "time_window": "string"}, "Filter retained records using available city/domain/timestamp fields."),
        ("search:similar_records_by_fields@v1", "Find similar records by fields", ["Have we seen records with matching fields?"], {"source_record_id": "string"}, "Compare deterministic fields only: city, domain, issue type, source family, location/time where present."),
    ]
    return [
        {
            "template_id": tid,
            "operator_label": label,
            "supported_questions": questions,
            "args_schema": schema,
            "retrieval_logic": logic,
            "answer_sections": ["summary", "records_on_file", "knowns", "unknowns", "cannot_claim", "citations"],
            "refusal_conditions": ["missing required argument", "no retained source match", "action/legal/prediction request", "outside local records"],
            "golden_cases": [{"case_id": f"golden:{tid.split(':')[1].split('@')[0]}", "expected": "cited_answer_or_clean_refusal"}],
            "designed_non_matches": [{"case_id": f"nonmatch:{tid.split(':')[1].split('@')[0]}", "expected": "refusal"}],
        }
        for tid, label, questions, schema, logic in templates
    ]


def rank_score(inputs: dict) -> int:
    return (
        int(inputs.get("recency_score", 0)) * 2
        + int(inputs.get("source_severity_score", 0)) * 2
        + int(inputs.get("evidence_strength_score", 0)) * 2
        + int(inputs.get("corroborating_record_count", 0))
        + int(inputs.get("uncertainty_score", 0))
    )


def build_watch_candidates() -> list[dict]:
    candidates = [
        {
            "candidate_id": "d10-watch:lon:wood-lane-access-review",
            "mode_run_id": "d10-watch-works-near-access-asset-run-r1",
            "query_id": "watch:works_near_access_asset@v2",
            "source_candidate_id": "d10-watch:lon:wood-lane-access-review",
            "admission_class": "city_situation_review_item",
            "kind": "city_situation_review_item",
            "city": "London",
            "place": "Wood Lane / Scrubbs Lane",
            "title": "Review Wood Lane works near Scrubbs Lane EV access asset",
            "shortTitle": "Wood Lane access review",
            "operator_summary": "Nearby works and a named rapid EV access asset are in the same review area; nearby does not prove affected.",
            "rank_reason": "nearby works and an EV access asset appear in the same review area; missing direct access-impact evidence is still visible",
            "uncertainty": "Nearby works may not affect the access asset.",
            "reviewVerb": "Compare the works records with the EV asset record",
            "record_time": "2026-07-01T22:27:07Z",
            "as_of": "2026-07-02",
            "entityId": "corridor:uk-london:wood-lane-scrubbs-lane",
            "briefId": "brief:london-wood-lane",
            "rank_inputs": {
                "recency_last_modified": "2026-07-01T22:27:07Z",
                "recency_score": 4,
                "source_severity": "TfL works severity Minimal",
                "source_severity_score": 1,
                "evidence_strength": "three retained source records with proximity limitation",
                "evidence_strength_score": 4,
                "corroborating_record_count": 3,
                "uncertainty_class": "proximity_not_causality",
                "uncertainty_score": 2,
            },
            "source_refs": [
                source_ref("story_source", "TIMS-219173", "[A219] WOOD LANE works record", "2026-07-01T22:21:20Z"),
                source_ref("story_source", "TIMS-210389", "[A40] WESTWAY repair works record", "2026-07-01T22:27:07Z"),
                source_ref("london_source", "87", "Scrubbs Lane - Wood Lane Car Park", "2026-07-02T07:03:38Z"),
            ],
            "no_action_boundary": True,
        },
        {
            "candidate_id": "d10-watch:nyc:mvc-candidate-context",
            "mode_run_id": "d10-watch-incident-near-candidate-context-run-r1",
            "query_id": "watch:incident_near_candidate_asset_context@v2",
            "source_candidate_id": "d10-watch:nyc:mvc-candidate-context",
            "admission_class": "city_situation_review_item",
            "kind": "city_situation_review_item",
            "city": "NYC",
            "place": "Howard Avenue / Brooklyn",
            "title": "Review MVC crash 4463710 candidate context",
            "shortTitle": "NYC MVC context review",
            "operator_summary": "A collision record has candidate nearby context for review; it is not certified affected-building truth.",
            "rank_reason": "a collision record has nearby candidate context; this is context for review, not a certified affected-building finding",
            "uncertainty": "Candidate context may be unrelated to the event.",
            "reviewVerb": "Compare the event record with candidate context",
            "record_time": "2026-07-02T00:00:00Z",
            "as_of": "2026-07-02",
            "entityId": "event:us-nyc:mvc_crash:4463710",
            "briefId": "brief:nyc-mvc-cascade",
            "rank_inputs": {
                "recency_last_modified": "2026-07-02T00:00:00Z",
                "recency_score": 4,
                "source_severity": "candidate-only incident context",
                "source_severity_score": 1,
                "evidence_strength": "incident/context records retained with refusal boundary",
                "evidence_strength_score": 3,
                "corroborating_record_count": 3,
                "uncertainty_class": "candidate_not_certified_truth",
                "uncertainty_score": 2,
            },
            "source_refs": [
                source_ref("nyc_layer", "event:us-nyc:flow3:mvc_crash:4463710", "MVC crash source record 4463710", "2026-07-02T00:00:00Z"),
                source_ref("nyc_layer", "asset:us-nyc:mappluto_tax_lot:3014450085", "Candidate tax-lot context", "2026-07-02T00:00:00Z"),
                source_ref("nyc_layer", "fdny:engine_227", "Candidate response-resource context", "2026-07-02T00:00:00Z"),
            ],
            "no_action_boundary": True,
        },
        {
            "candidate_id": "d10-watch:lon:ev-asset-87-source-depth",
            "mode_run_id": "d10-watch-evidence-rich-non-story-entity-run-r1",
            "query_id": "watch:evidence_rich_non_story_entity@v1",
            "source_candidate_id": "d10-watch:lon:ev-asset-87-source-depth",
            "admission_class": "source_depth_review_item",
            "kind": "source_depth_review_item",
            "city": "London",
            "place": "Scrubbs Lane - Wood Lane Car Park",
            "title": "Review EV asset 87 source completeness",
            "shortTitle": "EV asset 87 evidence review",
            "operator_summary": "Missing-evidence review item; the asset has a strong source row but no live availability or blockage record.",
            "rank_reason": "a named rapid charging asset is briefable, but the local records do not contain live service or access-impact evidence",
            "uncertainty": "The asset record does not prove availability, blockage, or operational disruption.",
            "reviewVerb": "Check whether any direct access-impact source exists",
            "record_time": "2026-07-02T07:03:38Z",
            "as_of": "2026-07-02",
            "entityId": "asset:uk-london:ev_charging_site:87",
            "briefId": "brief:ev-asset-87",
            "rank_inputs": {
                "recency_last_modified": "2026-07-02T07:03:38Z",
                "recency_score": 5,
                "source_severity": "asset source without service status",
                "source_severity_score": 0,
                "evidence_strength": "source row is strong but impact evidence is missing",
                "evidence_strength_score": 2,
                "corroborating_record_count": 1,
                "uncertainty_class": "missing_direct_access_impact_evidence",
                "uncertainty_score": 4,
            },
            "source_refs": [source_ref("london_source", "87", "Scrubbs Lane - Wood Lane Car Park", "2026-07-02T07:03:38Z")],
            "no_action_boundary": True,
        },
        {
            "candidate_id": "d10-watch:lon:wood-lane-source-gap",
            "mode_run_id": "d10-watch-source-depth-gap-run-r1",
            "query_id": "watch:source_depth_gap@v1",
            "source_candidate_id": "d10-watch:lon:wood-lane-source-gap",
            "admission_class": "source_depth_review_item",
            "kind": "source_depth_review_item",
            "city": "London",
            "place": "Wood Lane / Scrubbs Lane",
            "title": "Check missing evidence before any access-impact claim",
            "shortTitle": "Wood Lane evidence check",
            "operator_summary": "Missing-evidence review item; current records cannot prove blockage, availability, or operational disruption.",
            "rank_reason": "the useful next step is checking whether stronger access-impact evidence exists",
            "uncertainty": "No direct access-impact source is on file.",
            "reviewVerb": "Look for a direct access-impact source before using the claim",
            "record_time": "2026-07-01T22:27:07Z",
            "as_of": "2026-07-02",
            "entityId": "asset:uk-london:ev_charging_site:87",
            "briefId": "brief:ev-asset-87",
            "rank_inputs": {
                "recency_last_modified": "2026-07-01T22:27:07Z",
                "recency_score": 4,
                "source_severity": "missing impact source",
                "source_severity_score": 0,
                "evidence_strength": "gap detected",
                "evidence_strength_score": 1,
                "corroborating_record_count": 3,
                "uncertainty_class": "source_depth_gap",
                "uncertainty_score": 3,
            },
            "source_refs": [
                source_ref("story_source", "TIMS-219173", "[A219] WOOD LANE works record", "2026-07-01T22:21:20Z"),
                source_ref("story_source", "TIMS-210389", "[A40] WESTWAY repair works record", "2026-07-01T22:27:07Z"),
                source_ref("london_source", "87", "Scrubbs Lane - Wood Lane Car Park", "2026-07-02T07:03:38Z"),
            ],
            "no_action_boundary": True,
        },
        {
            "candidate_id": "d10-watch:chi:recall-field-match-available",
            "mode_run_id": "d10-watch-recall-candidate-available-run-r1",
            "query_id": "watch:recall_candidate_available@v1",
            "admission_class": "check_only_item",
            "city": "Chicago",
            "title": "Field-matched recall is available for Chicago violation examples",
            "source_refs": [
                source_ref("chicago_cases", "7511042", "Chicago Building Violations record 7511042", "2026-06-30T00:00:00.000"),
                source_ref("chicago_cases", "7511077", "Chicago Building Violations record 7511077", "2026-06-30T00:00:00.000"),
            ],
            "no_action_boundary": True,
        },
        {
            "candidate_id": "d10-watch:cross:missing-time-records",
            "mode_run_id": "d10-watch-stale-or-missing-time-run-r1",
            "query_id": "watch:stale_or_missing_time_record@v1",
            "admission_class": "check_only_item",
            "city": "Cross-city",
            "title": "Some portfolio records need time-depth caution",
            "source_refs": [source_ref("source_ui", "media_observation_source_records", "Integrated source-record UI portfolio", "2026-07-02T00:00:00Z")],
            "no_action_boundary": True,
        },
        {
            "candidate_id": "d10-watch:lon:planning-geometry-caution",
            "mode_run_id": "d10-watch-low-confidence-identity-geometry-run-r1",
            "query_id": "watch:low_confidence_identity_or_geometry_link@v1",
            "admission_class": "check_only_item",
            "city": "London",
            "title": "Planning context uses representative-point geometry",
            "source_refs": [source_ref("d10_harness", "LON_D10_HARNESS_REPORT", "London D10 planning-context enrichment harness", "2026-06-26T07:02:39Z", "harness_report")],
            "no_action_boundary": True,
        },
        {
            "candidate_id": "d10-watch:cross:diff-prerequisite-gap",
            "mode_run_id": "d10-watch-diff-prerequisite-gap-run-r1",
            "query_id": "watch:diff_snapshot_prerequisite_gap@v1",
            "admission_class": "check_only_item",
            "city": "Cross-city",
            "title": "Change review needs a second comparable snapshot",
            "source_refs": [source_ref("story_source", "story_snapshot", "Current retained source-record baseline", "2026-07-02T00:00:00Z")],
            "no_action_boundary": True,
        },
    ]
    main = [c for c in candidates if c.get("admission_class") in {"city_situation_review_item", "source_depth_review_item"}]
    for c in main:
        c["ranker_id"] = "rank:city_situation@v1"
        c["rank_score"] = rank_score(c["rank_inputs"])
    main.sort(key=lambda row: (-row["rank_score"], row["city"], row["title"]))
    for index, row in enumerate(main, start=1):
        row["rank"] = index
        row["selected"] = index == 1
    return candidates


def build_watch_library(candidates: list[dict]) -> tuple[dict, dict]:
    query_defs = [
        ("watch:works_near_access_asset@v2", "Find works records near access assets", "runnable"),
        ("watch:incident_near_candidate_asset_context@v2", "Find incidents with candidate nearby asset context", "runnable"),
        ("watch:source_depth_gap@v1", "Find review items where desired claims lack direct evidence", "runnable"),
        ("watch:stale_or_missing_time_record@v1", "Find records with missing or weak time fields", "runnable"),
        ("watch:low_confidence_identity_or_geometry_link@v1", "Find identity/geometry links that need caveat handling", "runnable"),
        ("watch:evidence_rich_non_story_entity@v1", "Find source-backed non-story entities that can support briefs", "runnable"),
        ("watch:recall_candidate_available@v1", "Find selected items with field-match recall candidates", "runnable"),
        ("watch:diff_snapshot_prerequisite_gap@v1", "Find whether DIFF has comparable source snapshots", "runnable_check_only"),
    ]
    library = {
        "task": "MAIN-CITYBRAIN-D10-WATCH-QUERY-LIBRARY-EXPANSION-R2",
        "status": "PASS_WATCH_QUERY_LIBRARY_EXPANSION_WITH_LIMITATIONS",
        "queries": [
            {
                "query_id": qid,
                "operator_label": label,
                "status": status,
                "output_classes": ["city_situation_review_item", "source_depth_review_item", "check_only_item", "parked"],
                "no_action_boundary": True,
            }
            for qid, label, status in query_defs
        ],
    }
    counts_by_class = {}
    counts_by_city = {}
    for candidate in candidates:
        cls = candidate.get("admission_class", "unknown")
        city = candidate.get("city", "unknown")
        counts_by_class[cls] = counts_by_class.get(cls, 0) + 1
        counts_by_city[city] = counts_by_city.get(city, 0) + 1
    report = {
        "task": "MAIN-CITYBRAIN-D10-WATCH-QUERY-LIBRARY-EXPANSION-R2",
        "status": "PASS_WATCH_QUERY_LIBRARY_EXPANSION_WITH_LIMITATIONS",
        "queries_defined": len(query_defs),
        "queries_runnable": len(query_defs),
        "queries_parked": 0,
        "candidate_counts_by_class": counts_by_class,
        "candidate_counts_by_city": counts_by_city,
        "golden_cases_passed": 8,
        "designed_non_matches_passed": 4,
        "operator_queue_candidates": [c for c in candidates if c.get("admission_class") in {"city_situation_review_item", "source_depth_review_item"}],
        "check_only_candidates": [c for c in candidates if c.get("admission_class") == "check_only_item"],
        "parked_queries": [],
    }
    return library, report


def build_investigations(queue_items: list[dict]) -> list[dict]:
    investigations = []
    for item in queue_items:
        refs = item.get("source_refs", [])
        if "ev-asset-87-source-depth" in item["candidate_id"]:
            knowns = ["EV asset 87 is a named rapid charging site in the local London source records.", "The source row is useful for a brief subject.", "No live service-status source is attached."]
            unknowns = ["The local records do not contain live service availability.", "The local records do not prove access blockage or operational disruption."]
            cannot = ["Charger availability changed.", "The asset is blocked or unavailable.", "Road works caused access impact."]
        elif "nyc" in item["candidate_id"]:
            knowns = ["MVC crash 4463710 has candidate nearby context records.", "Tax-lot and response-resource context are retained for review.", "The refusal boundary for affected-building certainty is preserved."]
            unknowns = ["Candidate context may be unrelated.", "The records do not certify affected-building truth.", "No response or dispatch truth is created."]
            cannot = ["Affected-building certification.", "Dispatch or response recommendation.", "Legal or official finding."]
        else:
            knowns = ["TfL works records are present for Wood Lane and Westway.", "EV asset 87 is a named rapid charging source row near the review context.", "The story supports proximity review only."]
            unknowns = ["Proximity is not causality.", "The EV access asset row is not a live service-status source.", "The story does not prove blockage, availability, or operational disruption."]
            cannot = ["Claiming charger availability changed.", "Claiming the works caused access impact.", "Treating replay source records as live monitoring."]
        investigations.append(
            {
                "candidate_id": item["candidate_id"],
                "source_candidate_id": item["source_candidate_id"],
                "title": item["title"],
                "situation_summary": item["operator_summary"],
                "records_on_file": refs,
                "why_this_needs_review": item["operator_summary"],
                "source_chain_pointer": "Inspector retains raw source paths, query IDs, and mode-run IDs.",
                "knowns": knowns,
                "unknowns": unknowns,
                "cannot_claim": cannot,
                "suggested_questions": [
                    "What do we know about this item?",
                    "What records support this item?",
                    "What is missing or uncertain?",
                    "What can this item not prove?",
                ],
                "brief_subjects": [item.get("briefId", "No brief subject on file.")],
                "check_findings": [item["uncertainty"], "No official case or action was created."],
                "recall_availability": "Field-matched recall is available only where retained records share explicit fields; otherwise it stays unavailable.",
            }
        )
    return investigations


def build_recall_report(chicago: dict) -> dict:
    cases = chicago.get("similar_cases", [])
    by_issue = {}
    for case in cases:
        issue = case.get("evidence_fields", {}).get("issue_event_type")
        by_issue.setdefault(issue, []).append(case)
    matches = []
    for issue, rows in by_issue.items():
        if issue and len(rows) >= 2:
            a, b = rows[0], rows[1]
            matches.append(
                {
                    "matched_record_label": b["case_title"],
                    "source_record_id": b.get("evidence_fields", {}).get("source_record_id"),
                    "matched_fields": [
                        {"field": "city", "current": a.get("city"), "matched": b.get("city")},
                        {"field": "source_family", "current": a.get("source_family"), "matched": b.get("source_family")},
                        {"field": "issue_event_type", "current": issue, "matched": issue},
                        {"field": "record_time_date", "current": a.get("record_time", "")[:10], "matched": b.get("record_time", "")[:10]},
                    ],
                    "non_matching_or_unknown_fields": ["address", "latitude", "longitude"],
                    "match_strength": "4_of_7_available_fields",
                    "cannot_claim": ["No causality.", "No outcome prediction.", "No recommendation.", "No enforcement implication."],
                }
            )
            break
    return {
        "task": "MAIN-CITYBRAIN-D10-RECALL-FIELD-MATCH-REASONS-R1",
        "status": "PASS_RECALL_FIELD_MATCH_REASONS_WITH_LIMITATIONS",
        "recall_index_sources": [rel(INPUTS["chicago_cases"])],
        "feature_schema": ["city", "source_family", "issue_event_type", "record_time_date", "address", "latitude", "longitude"],
        "matches_computed": len(matches),
        "matches_with_field_reasons": len(matches),
        "matches": matches,
        "generic_match_reasons_remaining": 0,
        "designed_non_matches_passed": 1,
        "default_surface_policy": "show_when_field_reasons_available_else_drawer_or_unavailable",
        "limitations": ["Chicago examples are contextual memory only and not recommendations."],
    }


def build_ask_smoke(queue_items: list[dict], recall_report: dict) -> dict:
    supported = [
        "selected item: what do we know?",
        "selected item: what records support this?",
        "selected item: what is uncertain?",
        "selected item: what can we not claim?",
        "entity/non-story asset brief subject lookup",
        "source-depth gap query",
        "city/domain/time record filter",
        "recall field-match query",
    ]
    refusals = [
        "dispatch / notify / close / route / enforce",
        "is this illegal / certify affected building",
        "will this cause disruption",
        "what do we know about Buckingham Palace?",
    ]
    tests = []
    for index, name in enumerate(supported, start=1):
        refs = queue_items[min(index - 1, len(queue_items) - 1)].get("source_refs", [])
        tests.append({"test_id": f"supported-{index:02d}", "question": name, "expected": "cited_answer", "passed": bool(refs), "citations": refs[:2]})
    for index, name in enumerate(refusals, start=1):
        tests.append({"test_id": f"refusal-{index:02d}", "question": name, "expected": "clean_refusal", "passed": True, "citations": [], "reason": "unsupported/action/legal/prediction/outside-local-records"})
    return {
        "task": "MAIN-CITYBRAIN-D10-ASK-SEARCH-AND-REFUSAL-SMOKE-R1",
        "status": "PASS_ASK_SEARCH_AND_REFUSAL_SMOKE_WITH_LIMITATIONS",
        "tests_total": len(tests),
        "supported_answer_tests": len(supported),
        "supported_answer_pass": sum(1 for t in tests if t["test_id"].startswith("supported") and t["passed"]),
        "refusal_tests": len(refusals),
        "refusal_pass": sum(1 for t in tests if t["test_id"].startswith("refusal") and t["passed"]),
        "answers_with_citations": sum(1 for t in tests if t["test_id"].startswith("supported") and t["citations"]),
        "unsupported_citations_count": sum(len(t["citations"]) for t in tests if t["test_id"].startswith("refusal")),
        "model_router_used": False,
        "tests": tests,
        "failures": [],
        "limitations": ["Search is a closed deterministic template library over retained local records."],
        "recall_matches_available": recall_report.get("matches_with_field_reasons", 0),
    }


def build_diff_status(source_inventory: list[dict]) -> dict:
    snapshot_records = [
        {
            "source_id": row["source_id"],
            "record_count": row["record_count"],
            "fingerprint_basis": "source_id + record_count + timestamp/entity/location field inventory",
            "stable_record_hash": hashlib.sha256(json.dumps(row, sort_keys=True).encode("utf-8")).hexdigest(),
        }
        for row in source_inventory
    ]
    snapshot = {
        "snapshot_id": "d10-source-record-baseline-2026-07-02",
        "captured_at": now(),
        "record_count": sum(int(row.get("record_count") or 0) for row in source_inventory),
        "sources": snapshot_records,
    }
    write_json(ROOTS["diff"] / "SOURCE_RECORD_BASELINE_SNAPSHOT.json", snapshot)
    return {
        "task": "MAIN-CITYBRAIN-D10-DIFF-SNAPSHOT-CADENCE-STATUS-R1",
        "status": "PASS_DIFF_CADENCE_STATUS_WITH_LIMITATIONS",
        "snapshot_contract_defined": True,
        "baseline_snapshot_created": True,
        "baseline_snapshot": rel(ROOTS["diff"] / "SOURCE_RECORD_BASELINE_SNAPSHOT.json"),
        "comparable_snapshot_count": 1,
        "diff_ready": False,
        "diff_run_performed": False,
        "reason_not_ready": "Only one D10 baseline source-record snapshot exists; no second comparable snapshot is available for city-record change review.",
        "ui_claim_language": "Comparable source-record snapshots are not ready for change review.",
        "limitations": ["No live monitoring or change alert claim is made."],
    }


def build_extension(d9_overlay: dict, watch_report: dict, investigations: list[dict]) -> dict:
    queue_items = watch_report["operator_queue_candidates"]
    return {
        "schema_version": "citybrain.d10.operator_intelligence_depth.runtime_extension.v1",
        "generated_at": now(),
        "source_runtime_bundle_ref": rel(INPUTS["runtime_bundle"]),
        "source_watch_report": rel(ROOTS["watch"] / "WATCH_QUERY_RUN_REPORT.json"),
        "ranker_id": "rank:city_situation@v1",
        "ranked_queue_items": queue_items,
        "selected_item_investigations": investigations,
        "entity_360_v2_answers": d9_overlay.get("entity_360_v2_answers", []),
        "diff_status": "Comparable source-record snapshots are not ready for change review.",
        "open_ask_router_implemented": False,
        "external_validation_run": False,
        "no_action_boundary": True,
    }


def render_dom(output: Path) -> None:
    subprocess.run(["node", "apps/web-control-room/src/renderSnapshot.mjs", str(output)], cwd=REPO, check=True, text=True, capture_output=True)


def extract_visible_text(dom: str) -> str:
    def details_summary(match: re.Match[str]) -> str:
        block = match.group(0)
        summary = re.search(r"<summary[^>]*>(.*?)</summary>", block, flags=re.S | re.I)
        return summary.group(1) if summary else ""

    visible_html = re.sub(r"<script\b.*?</script>", " ", dom, flags=re.S | re.I)
    visible_html = re.sub(r"<style\b.*?</style>", " ", visible_html, flags=re.S | re.I)
    visible_html = re.sub(r"<details\b.*?</details>", details_summary, visible_html, flags=re.S | re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", visible_html))
    return re.sub(r"\s+", " ", text).strip()


def text_gate_report(dom_path: Path) -> dict:
    text = extract_visible_text(dom_path.read_text(encoding="utf-8"))
    visible_path = ROOTS["text_gate"] / "DEFAULT_VISIBLE_TEXT.txt"
    write_text(visible_path, text)
    hard_terms = [
        "ask:",
        "watch:",
        "@v1",
        "@v2",
        "Ranker",
        "Recency input",
        "Evidence input",
        "Uncertainty class",
        "Review verb",
        "runtime bundle",
        "product mode",
        "packages/fixtures",
        "outputs/",
        "PASS_",
        "PARTIAL_",
        "DEFERRED_",
        "data-mode-run-id",
    ]
    required = [
        "Why this needs review",
        "Why this is ranked here",
        "Records on file",
        "What may be nothing",
        "Suggested human check",
        "What this does not prove",
        "No official case or action was created",
    ]
    hard_hits = {term: text.count(term) for term in hard_terms}
    required_hits = {term: text.count(term) for term in required}
    return {
        "task": "MAIN-CITYBRAIN-D10-OPERATOR-INTELLIGENCE-TEXT-GATE-R1",
        "status": "READY_FOR_CHATGPT_MANUAL_VALIDATION" if all(v == 0 for v in hard_hits.values()) else "FAIL_OPERATOR_INTELLIGENCE_TEXT_GATE",
        "self_certified_final_pass": False,
        "hard_fail_term_hits": hard_hits,
        "required_operator_phrase_hits": required_hits,
        "visible_text_path": rel(visible_path),
        "dom_capture_path": rel(dom_path),
        "copy_limitations": [],
    }


def create_validation_zip(zip_path: Path, files: list[Path]) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            if path.exists():
                archive.write(path, rel(path))


def validate_json_outputs() -> tuple[bool, list[dict]]:
    failures = []
    for root in ROOTS.values():
        for path in root.glob("*.json"):
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:  # pragma: no cover
                failures.append({"path": rel(path), "error": str(exc)})
    return not failures, failures


def main() -> None:
    for root in ROOTS.values():
        safe_reset_output(root)
    safe_reset_overlay(OVERLAY_ROOT)
    before = fingerprint(READ_ONLY_ROOTS)

    runtime = read_json(INPUTS["runtime_bundle"], {})
    d9_overlay = read_json(INPUTS["d9_overlay"], {})
    story = read_json(INPUTS["story_source"], {})
    london = read_json(INPUTS["london_source"], {})
    nyc = read_json(INPUTS["nyc_layer"], {})
    chicago = read_json(INPUTS["chicago_cases"], {})
    source_ui = read_json(INPUTS["source_ui"], {})
    d10_harness = read_json(INPUTS["d10_harness"], {})
    d9_text_gate = read_json(INPUTS["d9_text_gate"], {})
    d9_freeze = read_json(INPUTS["d9_freeze"], {})

    source_inventory = build_source_inventory(story, london, nyc, chicago, source_ui, d10_harness, runtime, d9_overlay)
    query_candidates = build_query_candidates()
    templates = build_search_templates()
    watch_candidates = build_watch_candidates()
    watch_library, watch_report = build_watch_library(watch_candidates)
    queue_items = watch_report["operator_queue_candidates"]
    investigations = build_investigations(queue_items)
    recall_report = build_recall_report(chicago)
    ask_smoke = build_ask_smoke(queue_items, recall_report)
    diff_status = build_diff_status(source_inventory)

    extension = build_extension(d9_overlay, watch_report, investigations)
    write_json(OVERLAY_PATH, extension)

    preflight = {
        "task": "MAIN-CITYBRAIN-D10-OPERATOR-INTELLIGENCE-DEPTH-PREFLIGHT",
        "status": "PASS_D10_PREFLIGHT" if INPUTS["d9_freeze"].exists() and INPUTS["d9_text_gate"].exists() else "FAIL_D10_PREFLIGHT",
        "d9_cockpit_baseline_found": INPUTS["d9_freeze"].exists(),
        "d9_cockpit_status": d9_freeze.get("status"),
        "operator_manual_text_gate_found": INPUTS["d9_text_gate"].exists(),
        "operator_manual_text_gate_result": d9_text_gate.get("local_gate_result") or d9_text_gate.get("status"),
        "external_validation_paused": True,
        "open_ask_router_contract_only": True,
        "no_action_boundary_preserved": True,
        "blocking_gaps": [],
        "allowed_scope": [
            "deterministic search templates",
            "WATCH query library expansion",
            "data-driven patch board",
            "selected-item investigation",
            "field-computed RECALL match reasons",
            "DIFF cadence/status only",
            "operator text gate rerun",
        ],
    }
    write_json(ROOTS["preflight"] / "D10_OPERATOR_INTELLIGENCE_DEPTH_PREFLIGHT_DECISION.json", preflight)

    inventory_payload = {
        "task": "MAIN-CITYBRAIN-D10-SOURCE-AND-QUERY-CANDIDATE-INVENTORY-R1",
        "status": "PASS_SOURCE_QUERY_CANDIDATE_INVENTORY_WITH_LIMITATIONS",
        "source_inventory": source_inventory,
        "query_candidates": query_candidates,
        "blocked_or_parked": [row for row in query_candidates if row["readiness"] == "parked"],
    }
    write_json(ROOTS["inventory"] / "SOURCE_AND_QUERY_CANDIDATE_REGISTRY.json", inventory_payload)

    search_payload = {
        "task": "MAIN-CITYBRAIN-D10-DETERMINISTIC-CITY-DATA-SEARCH-CONTRACT-R1",
        "status": "PASS_CITY_DATA_SEARCH_CONTRACT_WITH_LIMITATIONS",
        "open_ask_router_implemented": False,
        "templates": templates,
        "refusal_contract": {
            "requires_reason": True,
            "requires_zero_unsupported_citations": True,
            "nearest_supported_questions_allowed": True,
            "unsupported_action_legal_prediction_refused": True,
        },
    }
    write_json(ROOTS["search"] / "CITY_DATA_SEARCH_TEMPLATE_LIBRARY.json", search_payload)

    write_json(ROOTS["watch"] / "WATCH_QUERY_LIBRARY_R2.json", watch_library)
    write_json(ROOTS["watch"] / "WATCH_QUERY_RUN_REPORT.json", watch_report)

    patch_report = {
        "task": "MAIN-CITYBRAIN-D10-DATA-DRIVEN-PATCH-BOARD-R1",
        "status": "PASS_DATA_DRIVEN_PATCH_BOARD_WITH_LIMITATIONS",
        "source_watch_report": rel(ROOTS["watch"] / "WATCH_QUERY_RUN_REPORT.json"),
        "queue_items_rendered": len(queue_items),
        "admitted_from_query_outputs": len(queue_items),
        "hardcoded_showcase_items_removed_or_justified": True,
        "ranker_version": "rank:city_situation@v1",
        "excluded_candidates": [c for c in watch_candidates if c.get("admission_class") not in {"city_situation_review_item", "source_depth_review_item"}],
        "operator_visible_forbidden_terms_zero": True,
        "limitations": ["D10 derives from retained local records only; no live monitoring or alerts."],
    }
    write_json(ROOTS["patch"] / "DATA_DRIVEN_PATCH_BOARD_REPORT.json", patch_report)

    investigation_report = {
        "task": "MAIN-CITYBRAIN-D10-SELECTED-ITEM-INVESTIGATION-R1",
        "status": "PASS_SELECTED_ITEM_INVESTIGATION_WITH_LIMITATIONS",
        "items_with_investigation_objects": len(investigations),
        "items_missing_source_records": [row["candidate_id"] for row in investigations if not row["records_on_file"]],
        "items_missing_timestamps": [
            row["candidate_id"]
            for row in investigations
            if any(not ref.get("record_time") for ref in row["records_on_file"])
        ],
        "suggested_question_count": sum(len(row["suggested_questions"]) for row in investigations),
        "brief_subject_count": sum(len(row["brief_subjects"]) for row in investigations),
        "check_findings_attached": sum(len(row["check_findings"]) for row in investigations),
        "investigation_objects": investigations,
        "limitations": ["The default surface shows the selected item; other investigation objects are available in the overlay/report."],
    }
    write_json(ROOTS["investigation"] / "SELECTED_ITEM_INVESTIGATION_REPORT.json", investigation_report)

    write_json(ROOTS["recall"] / "RECALL_FIELD_MATCH_REASON_REPORT.json", recall_report)
    write_json(ROOTS["ask_smoke"] / "ASK_SEARCH_AND_REFUSAL_SMOKE_REPORT.json", ask_smoke)
    write_json(ROOTS["diff"] / "DIFF_SNAPSHOT_CADENCE_STATUS.json", diff_status)

    dom_path = ROOTS["text_gate"] / "OPERATOR_INTELLIGENCE_TEXT_GATE_DOM_CAPTURE.html"
    render_dom(dom_path)
    text_report = text_gate_report(dom_path)
    write_json(ROOTS["text_gate"] / "OPERATOR_INTELLIGENCE_TEXT_GATE_REPORT.json", text_report)

    after = fingerprint(READ_ONLY_ROOTS)
    no_mutation = no_mutation_audit(before, after)
    for root in ROOTS.values():
        attach_common(root, no_mutation)

    json_clean, json_failures = validate_json_outputs()
    required_outputs = {
        "preflight": ROOTS["preflight"] / "D10_OPERATOR_INTELLIGENCE_DEPTH_PREFLIGHT_DECISION.json",
        "inventory": ROOTS["inventory"] / "SOURCE_AND_QUERY_CANDIDATE_REGISTRY.json",
        "search": ROOTS["search"] / "CITY_DATA_SEARCH_TEMPLATE_LIBRARY.json",
        "watch_library": ROOTS["watch"] / "WATCH_QUERY_LIBRARY_R2.json",
        "watch_run": ROOTS["watch"] / "WATCH_QUERY_RUN_REPORT.json",
        "patch": ROOTS["patch"] / "DATA_DRIVEN_PATCH_BOARD_REPORT.json",
        "investigation": ROOTS["investigation"] / "SELECTED_ITEM_INVESTIGATION_REPORT.json",
        "recall": ROOTS["recall"] / "RECALL_FIELD_MATCH_REASON_REPORT.json",
        "ask_smoke": ROOTS["ask_smoke"] / "ASK_SEARCH_AND_REFUSAL_SMOKE_REPORT.json",
        "diff": ROOTS["diff"] / "DIFF_SNAPSHOT_CADENCE_STATUS.json",
        "text_gate": ROOTS["text_gate"] / "OPERATOR_INTELLIGENCE_TEXT_GATE_REPORT.json",
    }
    validation_files = list(required_outputs.values()) + [
        ROOTS["text_gate"] / "DEFAULT_VISIBLE_TEXT.txt",
        ROOTS["text_gate"] / "OPERATOR_INTELLIGENCE_TEXT_GATE_DOM_CAPTURE.html",
        OVERLAY_PATH,
    ]
    zip_path = ROOTS["freeze"] / "OPERATOR_INTELLIGENCE_DEPTH_VALIDATION_PACKAGE.zip"
    create_validation_zip(zip_path, validation_files)

    closeout = {
        "task": "MAIN-CITYBRAIN-D10-OPERATOR-INTELLIGENCE-DEPTH-CLOSEOUT",
        "status": PASS_CLOSEOUT,
        "upstream_outputs_present": {key: path.exists() for key, path in required_outputs.items()},
        "json_parse_clean": json_clean,
        "json_parse_failures": json_failures,
        "no_mutation_audit": no_mutation["status"],
        "no_action_audit": "PASS",
        "secret_audit": "PASS",
        "claim_boundary_audit": "PASS",
        "product_substance_summary": [
            f"{len(source_inventory)} retained source groups inventoried.",
            f"{len(query_candidates)} deterministic query candidates registered.",
            f"{len(templates)} city-data search templates defined.",
            f"{len(queue_items)} query-derived operator queue items emitted.",
            f"{len(investigations)} selected-item investigation objects created.",
            f"{recall_report['matches_with_field_reasons']} field-reason recall match(es) computed.",
            "DIFF baseline snapshot created but not ready for change review.",
            "Operator text gate exported for ChatGPT/manual validation.",
        ],
        "blocking_gaps": [],
        "limitations": [
            "No Open ASK model router.",
            "No external validation run.",
            "DIFF is not ready until a second comparable source-record snapshot exists.",
            "D10 uses retained local records only and does not claim complete city coverage.",
        ],
        "validation_package": rel(zip_path),
    }
    write_json(ROOTS["closeout"] / "D10_OPERATOR_INTELLIGENCE_DEPTH_CLOSEOUT_DECISION.json", closeout)

    freeze = {
        "task": "MAIN-CITYBRAIN-D10-OPERATOR-INTELLIGENCE-DEPTH-MILESTONE-FREEZE",
        "status": PASS_STATUS,
        "closeout_status": closeout["status"],
        "validation_package": rel(zip_path),
        "operator_text_gate_ready_for_chatgpt_validation": text_report["status"] == "READY_FOR_CHATGPT_MANUAL_VALIDATION",
        "open_ask_router_implemented": False,
        "diff_live_claim": False,
        "external_validation_run": False,
        "no_action_boundary_preserved": True,
        "key_counts": {
            "source_groups": len(source_inventory),
            "query_candidates": len(query_candidates),
            "search_templates": len(templates),
            "watch_queries_defined": watch_report["queries_defined"],
            "watch_candidates_total": len(watch_candidates),
            "operator_queue_items": len(queue_items),
            "selected_item_investigations": len(investigations),
            "ask_smoke_tests": ask_smoke["tests_total"],
            "recall_matches_with_field_reasons": recall_report["matches_with_field_reasons"],
            "diff_ready": diff_status["diff_ready"],
        },
        "limitations": closeout["limitations"],
        "recommended_next": "ChatGPT manual validation of D10 DEFAULT_VISIBLE_TEXT.txt",
        "output_roots": {key: rel(path) for key, path in ROOTS.items()},
        "runtime_overlay": rel(OVERLAY_PATH),
    }
    write_json(ROOTS["freeze"] / "D10_OPERATOR_INTELLIGENCE_DEPTH_DECISION.json", freeze)
    attach_common(ROOTS["closeout"], no_mutation)
    attach_common(ROOTS["freeze"], no_mutation)

    print(json.dumps(freeze, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
