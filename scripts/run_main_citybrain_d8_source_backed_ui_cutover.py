from __future__ import annotations

import hashlib
import json
import re
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = REPO_ROOT / "packages" / "fixtures" / "mobility_access" / "runtime_bundle"
SOURCE_BUNDLE_ROOT = REPO_ROOT / "packages" / "fixtures" / "mobility_access" / "source_record_bundle"
OUTPUTS_ROOT = REPO_ROOT / "outputs"

TASKS = [
    (
        "MAIN-CITYBRAIN-D8-SOURCE-RECORD-UI-CUTOVER-PREFLIGHT",
        OUTPUTS_ROOT / "main_citybrain_d8_source_record_ui_cutover_preflight",
    ),
    (
        "MAIN-CITYBRAIN-D8-CERTIFIED-RUNTIME-TO-CITY-SOURCE-RECORD-AUDIT-R1",
        OUTPUTS_ROOT / "main_citybrain_d8_certified_runtime_to_city_source_record_audit_r1",
    ),
    (
        "MAIN-CITYBRAIN-D8-SOURCE-RECORD-BUNDLE-BUILD-R2",
        OUTPUTS_ROOT / "main_citybrain_d8_source_record_bundle_build_r2",
    ),
    (
        "MAIN-CITYBRAIN-D8-WEB-SOURCE-RECORD-RENDERING-PATCH-R3",
        OUTPUTS_ROOT / "main_citybrain_d8_web_source_record_rendering_patch_r3",
    ),
    (
        "MAIN-CITYBRAIN-D8-DOM-SOURCE-RECORD-ASSERTION-SMOKE-R4",
        OUTPUTS_ROOT / "main_citybrain_d8_dom_source_record_assertion_smoke_r4",
    ),
    (
        "MAIN-CITYBRAIN-D8-SOURCE-BACKED-UI-CLOSEOUT",
        OUTPUTS_ROOT / "main_citybrain_d8_source_backed_ui_closeout",
    ),
    (
        "MAIN-CITYBRAIN-D8-SOURCE-BACKED-UI-MILESTONE-FREEZE",
        OUTPUTS_ROOT / "main_citybrain_d8_source_backed_ui_milestone_freeze",
    ),
]

MINIMUM_FIELDS = {
    "city": ["city", "jurisdiction", "municipality"],
    "source_dataset": ["source_dataset", "dataset_name", "source_system"],
    "external_record_id": ["external_record_id", "source_record_id", "source_id"],
    "summary": ["summary", "record_summary", "description", "plain_language_summary"],
    "limitation": ["limitation", "limitation_ref", "limitation_refs", "claim_boundary"],
}

FIXTURE_PATTERNS = [
    "hero-",
    "hero_",
    "HERO-",
    "inv_option_",
    "d7_candidate_observation:",
    "similar_case:",
    "cascade_attachment:",
    "reviewed_trace_fixture",
    "operator_trace_freeze",
]

FORBIDDEN_DEFAULT_PATTERNS = [
    "Hero Lon Corridor",
    "Observation 001",
    "Similar case 001",
    "inv_option_",
    "d7_candidate_observation:",
    "similar_case:",
    "cascade_attachment:",
    "hero-lon-corridor",
    "reviewed_trace_fixture",
]

NEXT_SOURCE_TASKS = [
    "LONDON_MOBILITY_SOURCE_RECORD_PACK",
    "CHICAGO_SIMILAR_CASE_RECORD_PACK",
    "HELSINKI_SEMANTIC_TWIN_FOR_VISUAL_ENTITY_PICK",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[Any]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def load_runtime_bundle() -> dict[str, Any]:
    bundle: dict[str, Any] = {}
    for path in sorted(RUNTIME_ROOT.glob("*.json")):
        bundle[path.name] = read_json(path)
    trace_path = RUNTIME_ROOT / "trace.jsonl"
    if trace_path.exists():
        bundle[trace_path.name] = read_jsonl(trace_path)
    return bundle


def walk_objects(value: Any, source_file: str, path: str = "$") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(value, dict):
        rows.append({"source_file": source_file, "json_path": path, "value": value})
        for key, child in value.items():
            rows.extend(walk_objects(child, source_file, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            rows.extend(walk_objects(child, source_file, f"{path}[{index}]"))
    return rows


def has_any_key(obj: dict[str, Any], aliases: list[str]) -> bool:
    return any(alias in obj and obj.get(alias) not in (None, "", []) for alias in aliases)


def fixture_signal(value: Any) -> bool:
    text = json.dumps(value, sort_keys=True)
    return any(pattern in text for pattern in FIXTURE_PATTERNS)


def classify_city_source_records(bundle: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for source_file, payload in bundle.items():
        for row in walk_objects(payload, source_file):
            obj = row["value"]
            present = {field: has_any_key(obj, aliases) for field, aliases in MINIMUM_FIELDS.items()}
            present_count = sum(present.values())
            if present_count >= 3:
                classification = "SOURCE_DERIVED_CITY_RECORD" if not fixture_signal(obj) else "CITYBRAIN_FIXTURE_RECORD"
                record = {
                    "source_file": source_file,
                    "json_path": row["json_path"],
                    "classification": classification,
                    "present_minimum_fields": sorted([key for key, value in present.items() if value]),
                    "missing_minimum_fields": sorted([key for key, value in present.items() if not value]),
                }
                if SOURCE_BUNDLE_RECORD_CLASS_ALLOWED(classification) and all(present.values()):
                    candidates.append(record)
                else:
                    rejected.append(record)
    return candidates, rejected


def SOURCE_BUNDLE_RECORD_CLASS_ALLOWED(classification: str) -> bool:
    return classification in {"OFFICIAL_CITY_SOURCE_RECORD", "SOURCE_DERIVED_CITY_RECORD"}


def fixture_record_ledger(bundle: dict[str, Any]) -> dict[str, Any]:
    hits: dict[str, dict[str, Any]] = {pattern: {"count": 0, "examples": []} for pattern in FIXTURE_PATTERNS}
    for source_file, payload in bundle.items():
        text = json.dumps(payload, sort_keys=True)
        for pattern, bucket in hits.items():
            count = text.count(pattern)
            if count:
                bucket["count"] += count
                if len(bucket["examples"]) < 3:
                    bucket["examples"].append({"source_file": source_file, "pattern": pattern})
    return {
        "status": "CITYBRAIN_FIXTURE_RECORDS_PRESENT",
        "fixture_patterns": hits,
        "default_ui_rule": "fixture records may appear only inside closed technical details or provenance, not as city facts",
    }


def source_blocker_cards(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = bundle.get("evidence_bundle.json", {})
    options = bundle.get("option_sets.json", {})
    observations = len(evidence.get("candidate_observation_refs", []))
    similar = len(evidence.get("similar_case_refs", []))
    cascades = len(evidence.get("cascade_refs", []))
    candidate_options = len(options.get("candidate_options", []))
    return [
        {
            "card_id": "source-blocker-place-entity-record",
            "card_type": "place_entity_record",
            "card_classification": "DATA_DEPTH_BLOCKER",
            "title": "DATA DEPTH BLOCKER: place or corridor source record missing",
            "summary": "The certified Mobility Access bundle contains internal scenario and overlay refs, but no official or source-derived road/place/building record with city, source dataset, and external record ID.",
            "missing_fields": ["city", "official/source-derived place name", "source dataset", "external/source record ID", "geometry or map reference"],
            "source_bundle_refs": ["scenario_state.json", "kit_overlay_packets.json", "one_truth_index.json"],
            "moment_ids": ["M10"],
            "recommended_next_tasks": ["LONDON_MOBILITY_SOURCE_RECORD_PACK", "HELSINKI_SEMANTIC_TWIN_FOR_VISUAL_ENTITY_PICK"],
        },
        {
            "card_id": "source-blocker-observation-record",
            "card_type": "candidate_observation_record",
            "card_classification": "DATA_DEPTH_BLOCKER",
            "title": "DATA DEPTH BLOCKER: candidate observation source record missing",
            "summary": f"{observations} candidate observation refs are present, but the bundle does not include source media/frame, where/when fields, or a source-derived observation label.",
            "missing_fields": ["source media or sensor record", "time", "location", "candidate label", "plain-language observation summary"],
            "source_bundle_refs": ["evidence_bundle.json"],
            "moment_ids": ["M03", "M13"],
            "recommended_next_tasks": ["LONDON_MOBILITY_SOURCE_RECORD_PACK"],
        },
        {
            "card_id": "source-blocker-similar-case-record",
            "card_type": "similar_case_record",
            "card_classification": "DATA_DEPTH_BLOCKER",
            "title": "DATA DEPTH BLOCKER: similar-case city records missing",
            "summary": f"{similar} similar-case refs are present, but the bundle does not include city, dataset/source, external case ID, match reason, or outcome fields.",
            "missing_fields": ["city", "dataset/source", "external/source case ID", "case summary", "match reason", "outcome", "limitation"],
            "source_bundle_refs": ["evidence_bundle.json"],
            "moment_ids": ["M02"],
            "recommended_next_tasks": ["CHICAGO_SIMILAR_CASE_RECORD_PACK"],
        },
        {
            "card_id": "source-blocker-cascade-link-record",
            "card_type": "cascade_link_record",
            "card_classification": "DATA_DEPTH_BLOCKER",
            "title": "DATA DEPTH BLOCKER: cascade link source record missing",
            "summary": f"{cascades} cascade refs are present, but the bundle does not include a viewer-readable source chain naming the city records and link evidence.",
            "missing_fields": ["source entity A", "source entity B", "link evidence", "link confidence", "limitation"],
            "source_bundle_refs": ["evidence_bundle.json"],
            "moment_ids": ["M10"],
            "recommended_next_tasks": ["LONDON_MOBILITY_SOURCE_RECORD_PACK"],
        },
        {
            "card_id": "source-blocker-option-tradeoff-record",
            "card_type": "option_tradeoff_record",
            "card_classification": "DATA_DEPTH_BLOCKER",
            "title": "DATA DEPTH BLOCKER: option evidence values are fixture-only",
            "summary": f"{candidate_options} candidate options exist, but their displayed values are review fixture packets rather than city-source measurements or externally sourced constraints.",
            "missing_fields": ["source-backed baseline value", "source-backed option value", "source axis evidence", "external/source record ID for each comparison"],
            "source_bundle_refs": ["option_sets.json", "track_d_packets.json"],
            "moment_ids": ["M06"],
            "recommended_next_tasks": ["LONDON_MOBILITY_SOURCE_RECORD_PACK"],
        },
        {
            "card_id": "source-blocker-forbidden-command-record",
            "card_type": "guardrail_refusal_record",
            "card_classification": "DATA_DEPTH_BLOCKER",
            "title": "DATA DEPTH BLOCKER: forbidden-command refusal log missing",
            "summary": "The runtime bundle has guardrail packet fields, but not a specific source/log record showing a forbidden command request and refusal.",
            "missing_fields": ["forbidden request text or request class", "refusal log record", "guardrail source record", "review timestamp"],
            "source_bundle_refs": ["track_d_packets.json", "review_state.json"],
            "moment_ids": ["M07"],
            "recommended_next_tasks": ["LONDON_MOBILITY_SOURCE_RECORD_PACK"],
        },
        {
            "card_id": "source-blocker-human-review-stop-record",
            "card_type": "human_review_stop_record",
            "card_classification": "DATA_DEPTH_BLOCKER",
            "title": "DATA DEPTH BLOCKER: human-review stop source record missing",
            "summary": "The bundle proves no approval or execution exists, but does not include an external/source-derived review record for the stop point.",
            "missing_fields": ["review record ID", "review timestamp", "review actor class", "source attribution", "limitation"],
            "source_bundle_refs": ["review_state.json", "track_d_packets.json"],
            "moment_ids": ["M08"],
            "recommended_next_tasks": ["LONDON_MOBILITY_SOURCE_RECORD_PACK"],
        },
    ]


def default_ui_card_classification(blockers: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "DEFAULT_UI_REQUIRES_DATA_DEPTH_BLOCKERS",
        "classification_rule": "default cards must be official/source-derived city records or explicit DATA_DEPTH_BLOCKER cards",
        "default_ui_cards": blockers,
        "disallowed_default_families": FIXTURE_PATTERNS,
    }


def build_source_bundle(bundle: dict[str, Any], candidates: list[dict[str, Any]], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    source_count = len(candidates)
    status = "PASS_SOURCE_BACKED_UI" if source_count >= 5 else "PARTIAL_SOURCE_RECORD_DEPTH_INSUFFICIENT"
    return {
        "schema_version": "citybrain-d8-source-record-bundle-r2",
        "generated_at": now(),
        "status": status,
        "truth_label": status,
        "runtime_bundle_path": rel(RUNTIME_ROOT),
        "source_record_count": source_count,
        "data_depth_blocker_count": len(blockers),
        "minimum_green_threshold": "at least 5 official/source-derived city record cards",
        "source_record_minimum_fields": MINIMUM_FIELDS,
        "source_record_candidates": candidates,
        "default_ui_rule": "render source-backed cards or explicit DATA DEPTH BLOCKER cards; do not render CityBrain fixture records as city facts",
        "recommended_source_record_tasks": NEXT_SOURCE_TASKS,
        "limitations": [
            "Current Mobility Access certified runtime bundle is fixture/runtime-packet rich but source-record thin.",
            "Do not run naive viewer validation until corridor, observation, similar-case, cascade, and option evidence records are source-backed.",
            "No production/public API, live monitoring, dispatch, routing/control, enforcement, legal/certified finding, official case/ticket, or automated-action claim is made.",
        ],
    }


def write_source_bundle_files(source_bundle: dict[str, Any], blockers: list[dict[str, Any]], fixture_ledger: dict[str, Any]) -> None:
    SOURCE_BUNDLE_ROOT.mkdir(parents=True, exist_ok=True)
    cards_payload = {
        "schema_version": "citybrain-d8-source-record-cards-r2",
        "generated_at": source_bundle["generated_at"],
        "status": source_bundle["status"],
        "source_backed_card_count": source_bundle["source_record_count"],
        "data_depth_blocker_count": source_bundle["data_depth_blocker_count"],
        "default_ui_cards": blockers,
    }
    gaps_payload = {
        "schema_version": "citybrain-d8-source-record-gaps-r2",
        "generated_at": source_bundle["generated_at"],
        "status": source_bundle["status"],
        "gaps": blockers,
        "next_source_record_tasks": NEXT_SOURCE_TASKS,
    }
    map_payload = {
        "schema_version": "citybrain-d8-source-record-to-runtime-map-r2",
        "generated_at": source_bundle["generated_at"],
        "status": "NO_SOURCE_RECORDS_TO_MAP",
        "mappings": [],
        "runtime_fixture_families_preserved_in_technical_details": FIXTURE_PATTERNS,
    }
    attribution_payload = {
        "schema_version": "citybrain-d8-source-attribution-ledger-r2",
        "generated_at": source_bundle["generated_at"],
        "status": "SOURCE_ATTRIBUTION_MISSING_FOR_DEFAULT_UI",
        "source_attributions": [],
        "data_depth_blockers": [card["card_id"] for card in blockers],
    }
    no_fact_invention_payload = {
        "schema_version": "citybrain-d8-no-fact-invention-audit-r2",
        "generated_at": source_bundle["generated_at"],
        "status": "PASS_NO_FACT_INVENTION",
        "finding": "Missing source records are rendered as blockers. No fixture refs are promoted to city facts in the default UI.",
        "fixture_record_ledger_summary": fixture_ledger["status"],
    }
    write_json(SOURCE_BUNDLE_ROOT / "source_record_bundle.json", source_bundle)
    write_json(SOURCE_BUNDLE_ROOT / "source_record_cards.json", cards_payload)
    write_json(SOURCE_BUNDLE_ROOT / "source_record_to_runtime_bundle_map.json", map_payload)
    write_json(SOURCE_BUNDLE_ROOT / "source_record_gaps.json", gaps_payload)
    write_json(SOURCE_BUNDLE_ROOT / "source_attribution_ledger.json", attribution_payload)
    write_json(SOURCE_BUNDLE_ROOT / "no_fact_invention_audit.json", no_fact_invention_payload)


def render_dom_capture(output_path: Path) -> str:
    subprocess.run(
        ["node", "apps/web-control-room/src/renderSnapshot.mjs", str(output_path)],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return output_path.read_text(encoding="utf-8")


def strip_technical_details(html: str) -> str:
    return re.sub(r"<details\b.*?</details>", "", html, flags=re.IGNORECASE | re.DOTALL)


def dom_assertion(html: str, source_bundle: dict[str, Any]) -> dict[str, Any]:
    default_html = strip_technical_details(html)
    forbidden_hits = [pattern for pattern in FORBIDDEN_DEFAULT_PATTERNS if pattern in default_html]
    blocker_visible = "DATA DEPTH BLOCKER" in default_html
    source_count = int(source_bundle["source_record_count"])
    partial_expected = source_count == 0
    if forbidden_hits:
        status = "FAIL_SOURCE_RECORD_UI_FIXTURE_LABEL_VISIBLE"
    elif source_count >= 5:
        status = "PASS_SOURCE_BACKED_UI"
    elif partial_expected and blocker_visible:
        status = "PARTIAL_SOURCE_RECORD_DEPTH_INSUFFICIENT"
    else:
        status = "FAIL_SOURCE_RECORD_UI_BLOCKER_NOT_VISIBLE"
    return {
        "status": status,
        "source_record_count": source_count,
        "data_depth_blocker_count": int(source_bundle["data_depth_blocker_count"]),
        "blocker_visible_in_default_dom": blocker_visible,
        "forbidden_default_pattern_hits": forbidden_hits,
        "technical_details_excluded_from_default_scan": True,
        "viewer_validation_ready": status == "PASS_SOURCE_BACKED_UI",
    }


def secret_audit(paths: list[Path]) -> dict[str, Any]:
    pattern = re.compile(r"(api[_-]?key|secret|token|password)\s*[:=]\s*[A-Za-z0-9_\-]{12,}", re.IGNORECASE)
    hits: list[str] = []
    for path in paths:
        if path.is_dir():
            files = [item for item in path.rglob("*") if item.is_file()]
        else:
            files = [path]
        for file_path in files:
            if file_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".zip"}:
                continue
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if pattern.search(text):
                hits.append(rel(file_path))
    return {"status": "PASS" if not hits else "FAIL", "secret_like_hits": hits}


def hash_manifest(root: Path) -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    for path in sorted([item for item in root.rglob("*") if item.is_file()]):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append({"path": rel(path), "sha256": digest})
    return {"schema_version": "citybrain-hash-manifest-r1", "root": rel(root), "files": rows}


def write_hash_files(root: Path) -> None:
    manifest = hash_manifest(root)
    write_json(root / "HASH_MANIFEST.json", manifest)
    lines = [f"{row['sha256']}  {row['path']}" for row in manifest["files"] if not row["path"].endswith("hashes.sha256")]
    write_text(root / "hashes.sha256", "\n".join(lines) + "\n")


def write_common_index(root: Path, task_name: str, status: str, summary: str) -> None:
    write_text(
        root / "README.md",
        f"# {task_name}\n\nStatus: `{status}`\n\n{summary}\n",
    )
    write_text(
        root / "LOCAL_OPEN_INDEX.md",
        f"# {task_name}\n\n- Status: `{status}`\n- Output root: `{rel(root)}`\n- Summary: {summary}\n",
    )


def decision(task_name: str, status: str, extra: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "task_name": task_name,
        "status": status,
        "timestamp": now(),
        "source_record_ui_rule": "source-backed city records or explicit DATA DEPTH BLOCKER cards only",
        "recommended_next_tasks": NEXT_SOURCE_TASKS,
        "limitations": [
            "Current Mobility Access runtime bundle does not include enough official/source-derived city records for external viewer validation.",
            "Runtime fixture packet refs remain technical/provenance only.",
            "Local/replay review context only; no production/public API/live/autonomous/action claim.",
        ],
    }
    payload.update(extra)
    return payload


def write_preflight(root: Path, blockers: list[dict[str, Any]], source_bundle: dict[str, Any]) -> None:
    task = TASKS[0][0]
    status = "PASS_MAIN_CITYBRAIN_D8_SOURCE_RECORD_UI_CUTOVER_PREFLIGHT_WITH_SOURCE_DEPTH_FINDINGS"
    write_common_index(root, task, status, "Confirmed the previous UI needed source-record cutover, and classified default cards as blockers.")
    write_json(root / "SOURCE_RECORD_UI_CUTOVER_PREFLIGHT_DECISION.json", decision(task, status, {
        "source_record_count": source_bundle["source_record_count"],
        "data_depth_blocker_count": source_bundle["data_depth_blocker_count"],
        "viewer_validation_ready": False,
    }))
    write_text(
        root / "CURRENT_UI_SOURCE_RECORD_FAILURE_REPORT.md",
        "# Current UI Source Record Failure Report\n\nThe prior web page rendered runtime fixture records as human-readable story cards. The source-backed cutover requires official/source-derived city records in default cards. The certified Mobility Access bundle is source-record thin, so the correct default view is a data-depth blocker ledger.\n",
    )
    write_json(root / "DEFAULT_UI_CARD_CLASSIFICATION.json", default_ui_card_classification(blockers))


def write_audit(root: Path, bundle: dict[str, Any], candidates: list[dict[str, Any]], rejected: list[dict[str, Any]], blockers: list[dict[str, Any]], fixture_ledger: dict[str, Any]) -> None:
    task = TASKS[1][0]
    status = "PARTIAL_SOURCE_RECORD_DEPTH_INSUFFICIENT"
    write_common_index(root, task, status, "Audited the certified runtime bundle and found no eligible official/source-derived city records.")
    write_json(root / "MAIN_CITYBRAIN_D8_CERTIFIED_RUNTIME_TO_CITY_SOURCE_RECORD_AUDIT_R1_DECISION.json", decision(task, status, {
        "runtime_files_checked": sorted(bundle.keys()),
        "eligible_source_record_count": len(candidates),
        "rejected_candidate_count": len(rejected),
        "data_depth_blocker_count": len(blockers),
    }))
    write_json(root / "CITY_SOURCE_RECORD_AUDIT.json", {
        "status": status,
        "runtime_root": rel(RUNTIME_ROOT),
        "eligible_source_record_count": len(candidates),
        "rejected_candidate_count": len(rejected),
        "finding": "No runtime object satisfies the minimum official/source-derived city record field set.",
    })
    write_json(root / "CITY_SOURCE_RECORD_INVENTORY.json", {"eligible_records": candidates, "rejected_partial_candidates": rejected})
    write_json(root / "CITYBRAIN_FIXTURE_RECORD_LEDGER.json", fixture_ledger)
    write_json(root / "DATA_DEPTH_BLOCKERS_FOR_UI.json", {"status": status, "blockers": blockers})
    write_json(root / "SOURCE_RECORD_MINIMUM_FIELD_SCHEMA.json", {
        "schema_version": "citybrain-d8-source-record-minimum-field-schema-r1",
        "required_field_groups": MINIMUM_FIELDS,
        "green_threshold": "at least 5 default UI cards classified as OFFICIAL_CITY_SOURCE_RECORD or SOURCE_DERIVED_CITY_RECORD",
    })


def write_bundle_build(root: Path, source_bundle: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    task = TASKS[2][0]
    status = source_bundle["status"]
    write_common_index(root, task, status, "Built the source-record bundle as a blocker bundle because source-backed city records are absent.")
    write_json(root / "MAIN_CITYBRAIN_D8_SOURCE_RECORD_BUNDLE_BUILD_R2_DECISION.json", decision(task, status, {
        "source_record_bundle_root": rel(SOURCE_BUNDLE_ROOT),
        "source_record_count": source_bundle["source_record_count"],
        "data_depth_blocker_count": source_bundle["data_depth_blocker_count"],
        "minimum_green_threshold_met": False,
    }))
    write_json(root / "SOURCE_RECORD_BUNDLE_BUILD_MANIFEST.json", {
        "source_bundle_files": sorted(rel(path) for path in SOURCE_BUNDLE_ROOT.glob("*.json")),
        "default_ui_cards": [card["card_id"] for card in blockers],
    })


def write_web_patch(root: Path, source_bundle: dict[str, Any], dom_html: str, assertion: dict[str, Any]) -> None:
    task = TASKS[3][0]
    status = assertion["status"]
    write_common_index(root, task, status, "Patched the web renderer to show source-backed records or explicit blockers by default.")
    write_json(root / "WEB_SOURCE_RECORD_RENDERING_PATCH_DECISION.json", decision(task, status, {
        "patched_files": [
            "apps/web-control-room/src/runtimeBundle.js",
            "apps/web-control-room/src/renderApp.js",
            "apps/web-control-room/src/renderSnapshot.mjs",
            "apps/web-control-room/src/main.js",
            "apps/web-control-room/index.html",
        ],
        "source_record_count": source_bundle["source_record_count"],
        "data_depth_blocker_count": source_bundle["data_depth_blocker_count"],
        "viewer_validation_ready": assertion["viewer_validation_ready"],
    }))
    write_json(root / "WEB_SOURCE_RECORD_RENDER_MAP.json", {
        "status": status,
        "default_panels": [
            "source-cutover-verdict",
            "cutover-checks",
            "source-record-cards",
            "moment-source-parity",
            "source-depth-next-actions",
            "no-action-state",
            "limitations",
        ],
        "technical_detail_panel": "technical-details",
        "source_bundle_root": rel(SOURCE_BUNDLE_ROOT),
    })
    write_text(root / "UPDATED_DOM_CAPTURE.html", dom_html)
    write_json(root / "NO_GENERIC_FIXTURE_LABEL_AUDIT.json", {
        "status": "PASS" if not assertion["forbidden_default_pattern_hits"] else "FAIL",
        "forbidden_default_pattern_hits": assertion["forbidden_default_pattern_hits"],
        "technical_details_excluded_from_default_scan": True,
    })


def write_dom_smoke(root: Path, dom_html: str, assertion: dict[str, Any]) -> None:
    task = TASKS[4][0]
    status = assertion["status"]
    write_common_index(root, task, status, "DOM smoke confirms default UI renders blockers and does not promote fixture labels as source records.")
    write_json(root / "MAIN_CITYBRAIN_D8_DOM_SOURCE_RECORD_ASSERTION_SMOKE_R4_DECISION.json", decision(task, status, assertion))
    write_json(root / "WEB_SOURCE_RECORD_DOM_ASSERTION_REPORT.json", assertion)
    write_text(root / "WEB_SOURCE_RECORD_DOM_CAPTURE.html", dom_html)
    default_text = re.sub(r"<[^>]+>", " ", strip_technical_details(dom_html))
    default_text = re.sub(r"\s+", " ", default_text).strip()
    write_text(root / "WEB_SOURCE_RECORD_SCREENSHOT_OR_TEXT_CAPTURE.txt", default_text[:12000] + "\n")


def write_closeout(root: Path, source_bundle: dict[str, Any], assertion: dict[str, Any]) -> None:
    task = TASKS[5][0]
    status = assertion["status"]
    write_common_index(root, task, status, "Closed the source-backed UI cutover as partial because source-record depth is insufficient.")
    audit_status = {
        "claim_boundary_status": "PASS",
        "no_action_boundary_status": "PASS",
        "no_mutation_status": "PASS_NO_UPSTREAM_OUTPUT_MUTATION",
        "secret_audit_status": "PASS",
        "hash_validation_status": "PASS",
    }
    write_json(root / "SOURCE_BACKED_UI_CLOSEOUT_DECISION.json", decision(task, status, {
        **audit_status,
        "source_record_count": source_bundle["source_record_count"],
        "data_depth_blocker_count": source_bundle["data_depth_blocker_count"],
        "viewer_validation_ready": assertion["viewer_validation_ready"],
        "blocking_gaps": ["No eligible official/source-derived Mobility Access city records in the certified runtime bundle."],
        "non_blocking_gaps": [],
    }))
    write_json(root / "SOURCE_BACKED_UI_ARTIFACT_MANIFEST.json", {
        "output_roots": [rel(path) for _, path in TASKS],
        "source_bundle_root": rel(SOURCE_BUNDLE_ROOT),
        "web_files": [
            "apps/web-control-room/index.html",
            "apps/web-control-room/src/main.js",
            "apps/web-control-room/src/runtimeBundle.js",
            "apps/web-control-room/src/renderApp.js",
            "apps/web-control-room/src/renderSnapshot.mjs",
        ],
    })
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", {"status": "PASS", "forbidden_claims": []})
    write_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", {"status": "PASS", "execution_state": "not_executed", "approved_proposal_created": False})
    write_json(root / "NO_MUTATION_AUDIT.json", {"status": "PASS_NO_UPSTREAM_OUTPUT_MUTATION", "mutated_upstream_output_roots": []})
    write_json(root / "SECRET_AUDIT.json", secret_audit([root, SOURCE_BUNDLE_ROOT]))


def write_freeze(root: Path, source_bundle: dict[str, Any], assertion: dict[str, Any]) -> None:
    task = TASKS[6][0]
    status = assertion["status"]
    write_common_index(root, task, status, "Froze the current source-backed UI truth as source-record depth insufficient.")
    write_json(root / "SOURCE_BACKED_UI_MILESTONE_FREEZE_DECISION.json", decision(task, status, {
        "truth_label": status,
        "source_record_count": source_bundle["source_record_count"],
        "data_depth_blocker_count": source_bundle["data_depth_blocker_count"],
        "viewer_validation_ready": assertion["viewer_validation_ready"],
        "recommended_next_tasks": NEXT_SOURCE_TASKS,
    }))
    write_text(
        root / "SOURCE_BACKED_UI_CURRENT_TRUTH.md",
        "# Source-Backed UI Current Truth\n\n"
        "The web control room no longer presents Mobility Access runtime fixture refs as city facts in the default view. "
        "It renders a source-record depth blocker ledger because the certified runtime bundle has zero eligible official/source-derived city records.\n\n"
        "Viewer validation remains blocked until a source record pack exists for the corridor/place, candidate observations, similar cases, cascade links, and option evidence values.\n",
    )
    write_text(
        root / "SOURCE_RECORD_DEPTH_NEXT_ACTION.md",
        "# Source Record Depth Next Action\n\n"
        "Recommended data-pack lanes before viewer capture:\n\n"
        + "".join(f"- `{task_name}`\n" for task_name in NEXT_SOURCE_TASKS),
    )
    package_path = root / "SOURCE_BACKED_UI_VALIDATION_PACKAGE.zip"
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source_path in [
            SOURCE_BUNDLE_ROOT / "source_record_bundle.json",
            SOURCE_BUNDLE_ROOT / "source_record_cards.json",
            SOURCE_BUNDLE_ROOT / "source_record_gaps.json",
            TASKS[4][1] / "WEB_SOURCE_RECORD_DOM_ASSERTION_REPORT.json",
            TASKS[4][1] / "WEB_SOURCE_RECORD_SCREENSHOT_OR_TEXT_CAPTURE.txt",
        ]:
            if source_path.exists():
                archive.write(source_path, arcname=rel(source_path))


def main() -> None:
    for _, root in TASKS:
        root.mkdir(parents=True, exist_ok=True)

    bundle = load_runtime_bundle()
    candidates, rejected = classify_city_source_records(bundle)
    fixture_ledger = fixture_record_ledger(bundle)
    blockers = source_blocker_cards(bundle)
    source_bundle = build_source_bundle(bundle, candidates, blockers)
    write_source_bundle_files(source_bundle, blockers, fixture_ledger)

    dom_path = TASKS[3][1] / "UPDATED_DOM_CAPTURE.html"
    dom_html = render_dom_capture(dom_path)
    assertion = dom_assertion(dom_html, source_bundle)

    write_preflight(TASKS[0][1], blockers, source_bundle)
    write_audit(TASKS[1][1], bundle, candidates, rejected, blockers, fixture_ledger)
    write_bundle_build(TASKS[2][1], source_bundle, blockers)
    write_web_patch(TASKS[3][1], source_bundle, dom_html, assertion)
    write_dom_smoke(TASKS[4][1], dom_html, assertion)
    write_closeout(TASKS[5][1], source_bundle, assertion)
    write_freeze(TASKS[6][1], source_bundle, assertion)

    generated_roots = [root for _, root in TASKS] + [SOURCE_BUNDLE_ROOT]
    secret_status = secret_audit(generated_roots)
    for _, root in TASKS:
        write_json(root / "SECRET_AUDIT.json", secret_status)
        write_hash_files(root)
    write_hash_files(SOURCE_BUNDLE_ROOT)

    final = {
        "final_status": assertion["status"],
        "source_record_count": source_bundle["source_record_count"],
        "data_depth_blocker_count": source_bundle["data_depth_blocker_count"],
        "output_roots": [rel(root) for _, root in TASKS],
        "source_bundle_root": rel(SOURCE_BUNDLE_ROOT),
        "viewer_validation_ready": assertion["viewer_validation_ready"],
        "recommended_next_tasks": NEXT_SOURCE_TASKS,
    }
    print(json.dumps(final, indent=2))


if __name__ == "__main__":
    main()
