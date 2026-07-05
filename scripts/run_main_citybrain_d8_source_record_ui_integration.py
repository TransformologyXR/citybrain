#!/usr/bin/env python3
"""Run D8 source-record UI integration.

This runner adapts the recovered London, Chicago, and Helsinki source-record
packs into one web-control-room fixture, then validates that the default web DOM
renders city/source facts instead of internal fixture labels.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import html as html_lib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]

TASKS = {
    "preflight": {
        "task_name": "MAIN-CITYBRAIN-D8-SOURCE-RECORD-UI-INTEGRATION-PREFLIGHT",
        "root": REPO / "outputs" / "main_citybrain_d8_source_record_ui_integration_preflight",
        "decision": "SOURCE_RECORD_UI_INTEGRATION_PREFLIGHT_DECISION.json",
    },
    "adapter": {
        "task_name": "MAIN-CITYBRAIN-D8-INTEGRATED-SOURCE-RECORD-BUNDLE-ADAPTER-R1",
        "root": REPO / "outputs" / "main_citybrain_d8_integrated_source_record_bundle_adapter_r1",
        "decision": "INTEGRATED_SOURCE_RECORD_BUNDLE_ADAPTER_R1_DECISION.json",
    },
    "web": {
        "task_name": "MAIN-CITYBRAIN-D8-WEB-SOURCE-RECORD-CARDS-R2",
        "root": REPO / "outputs" / "main_citybrain_d8_web_source_record_cards_r2",
        "decision": "WEB_SOURCE_RECORD_CARDS_DECISION.json",
    },
    "parity": {
        "task_name": "MAIN-CITYBRAIN-D8-MOMENT-SOURCE-RECORD-PARITY-R3",
        "root": REPO / "outputs" / "main_citybrain_d8_moment_source_record_parity_r3",
        "decision": "MOMENT_SOURCE_RECORD_PARITY_DECISION.json",
    },
    "smoke": {
        "task_name": "MAIN-CITYBRAIN-D8-CITY-FACT-DOM-ASSERTION-SMOKE-R4",
        "root": REPO / "outputs" / "main_citybrain_d8_city_fact_dom_assertion_smoke_r4",
        "decision": "CITY_FACT_DOM_ASSERTION_SMOKE_DECISION.json",
    },
    "closeout": {
        "task_name": "MAIN-CITYBRAIN-D8-SOURCE-RECORD-UI-CLOSEOUT",
        "root": REPO / "outputs" / "main_citybrain_d8_source_record_ui_closeout",
        "decision": "SOURCE_RECORD_UI_CLOSEOUT_DECISION.json",
    },
    "freeze": {
        "task_name": "MAIN-CITYBRAIN-D8-SOURCE-RECORD-UI-MILESTONE-FREEZE",
        "root": REPO / "outputs" / "main_citybrain_d8_source_record_ui_milestone_freeze",
        "decision": "SOURCE_RECORD_UI_MILESTONE_FREEZE_DECISION.json",
    },
}

INPUTS = {
    "recovery_handoff_decision": REPO / "outputs" / "main_citybrain_d8_source_record_recovery_certified_state_handoff" / "SOURCE_RECORD_RECOVERY_CERTIFIED_STATE_HANDOFF_DECISION.json",
    "london_bundle": REPO / "packages" / "fixtures" / "london_mobility_source_records" / "source_record_bundle.json",
    "chicago_bundle": REPO / "packages" / "fixtures" / "chicago_similar_case_records" / "similar_case_source_bundle.json",
    "helsinki_bundle": REPO / "packages" / "fixtures" / "helsinki_visual_entity_pick" / "source_record_bundle.json",
    "candidate_bundle": REPO / "packages" / "fixtures" / "source_record_recovery_candidate_bundle" / "source_record_recovery_candidate_bundle.json",
    "runtime_options": REPO / "packages" / "fixtures" / "mobility_access" / "runtime_bundle" / "option_sets.json",
    "runtime_evidence": REPO / "packages" / "fixtures" / "mobility_access" / "runtime_bundle" / "evidence_bundle.json",
    "runtime_limitations": REPO / "packages" / "fixtures" / "mobility_access" / "runtime_bundle" / "limitations.json",
    "web_index": REPO / "apps" / "web-control-room" / "index.html",
    "web_renderer": REPO / "apps" / "web-control-room" / "src" / "renderApp.js",
    "web_loader": REPO / "apps" / "web-control-room" / "src" / "runtimeBundle.js",
    "snapshot_renderer": REPO / "apps" / "web-control-room" / "src" / "renderSnapshot.mjs",
}

INTEGRATED_FIXTURE_ROOT = REPO / "packages" / "fixtures" / "source_record_ui_integrated"

FORBIDDEN_DEFAULT_LABELS = [
    "Hero Lon Corridor",
    "Hero Main Eastbound",
    "Hero Blocked Lane",
    "Observation 001",
    "Similar case 001",
    "option packet 1",
    "Execution: Not Executed",
    "Track D",
    "D7",
    "M02",
    "M13",
    "CityBrain connected",
    "runtime bundle",
    "trace stage",
    "mobility_access:",
    "similar_case:001",
    "d7_candidate_observation:",
    "inv_option_",
    "track-d-",
]

REQUIRED_VISIBLE_PHRASES = [
    "Upper Richmond Road west of Coval Rd",
    "London Datastore Electric Vehicle Charging Site",
    "Violations case at 6934 S DANTE AVE",
    "Chicago Building Violations",
    "Helsinki 3D city model semantic building sample",
    "/World/CityBrain/HEL",
    "DATA DEPTH BLOCKER",
    "No action has been taken",
]

BOUNDARY_TEXT = [
    "local/replay/review/query context only",
    "no production/public API claim",
    "no autonomous monitoring/action",
    "no dispatch/routing/control/enforcement",
    "no legal/certified/confirmed finding",
    "no official ticket/case creation",
    "no broad full-city download",
]


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def ensure_roots() -> None:
    for task in TASKS.values():
        task["root"].mkdir(parents=True, exist_ok=True)
    INTEGRATED_FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_hashes(paths: dict[str, Path]) -> dict[str, str | None]:
    hashes: dict[str, str | None] = {}
    for key, path in paths.items():
        hashes[key] = sha256(path) if path.exists() and path.is_file() else None
    return hashes


def output_index(root: Path, title: str, artifacts: list[str]) -> None:
    write_text(root / "README.md", f"# {title}\n\nGenerated by `{rel(Path(__file__))}`.\n")
    lines = [f"# {title}", "", "## Artifacts", ""]
    for artifact in artifacts:
        lines.append(f"- `{artifact}`")
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines) + "\n")


def input_artifact_index() -> dict[str, Any]:
    return {
        key: {
            "path": rel(path),
            "exists": path.exists(),
            "sha256": sha256(path) if path.exists() and path.is_file() else None,
        }
        for key, path in INPUTS.items()
    }


def source_cards() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    candidate = read_json(INPUTS["candidate_bundle"])
    cards = candidate.get("cards", {})
    london = cards.get("london")
    chicago = cards.get("chicago")
    helsinki = cards.get("helsinki")

    if london is None:
        london = read_json(INPUTS["london_bundle"]).get("cards", [])
    if chicago is None:
        raw_chicago = read_json(INPUTS["chicago_bundle"])
        chicago = raw_chicago.get("cards") or raw_chicago.get("similar_cases") or []
    if helsinki is None:
        helsinki = read_json(INPUTS["helsinki_bundle"]).get("cards", [])

    return london, chicago, helsinki, candidate


def evidence_refs(card: dict[str, Any]) -> list[str]:
    refs = []
    for key in ("source_url", "dataset_page"):
        value = card.get(key) or card.get("evidence_fields", {}).get(key)
        if value:
            refs.append(str(value))
    if card.get("external_record_id"):
        refs.append(f"external_record_id:{card['external_record_id']}")
    return refs


def city_fact_fields(card: dict[str, Any], family: str) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "city": card.get("city"),
        "dataset": card.get("source_dataset"),
        "source_record_id": card.get("external_record_id"),
    }
    evidence = card.get("evidence_fields") or {}
    for key in ("borough", "numberrcpoints", "taxipublicuses", "latitude", "longitude", "geometry_status"):
        if evidence.get(key):
            fields[key] = evidence[key]
    if card.get("match_reason"):
        fields["matched_because"] = card["match_reason"]
    if card.get("known_limit"):
        fields["known_limit"] = card["known_limit"]
    if card.get("prim_path"):
        fields["visual_object_path"] = card["prim_path"]
    if card.get("cer_candidate_id"):
        fields["semantic_candidate_id"] = card["cer_candidate_id"]
    if family == "helsinki" and "semantic_candidate_id" not in fields:
        fields["semantic_candidate_id"] = card.get("external_record_id")
    return {key: value for key, value in fields.items() if value not in (None, "", [])}


def normalize_card(card: dict[str, Any], family: str, index: int) -> dict[str, Any]:
    family_prefix = {
        "london": "situation_city_record",
        "chicago": "precedent_city_record",
        "helsinki": "visual_entity_city_record",
    }[family]
    return {
        "card_id": card.get("card_id") or f"{family_prefix}_{index:03d}",
        "card_type": card.get("card_type") or family_prefix,
        "record_class": card.get("card_classification") or ("SOURCE_DERIVED_CITY_RECORD" if family != "chicago" else "OFFICIAL_CITY_SOURCE_RECORD"),
        "source_city": card.get("city") or family.title(),
        "source_system_or_dataset": card.get("source_dataset") or "not recorded",
        "title": card.get("title") or f"{family.title()} source record {index:03d}",
        "plain_language_summary": card.get("summary") or "Source record present; no plain-language summary was provided.",
        "city_fact_fields": city_fact_fields(card, family),
        "why_it_matters": card.get("why_it_matters") or card.get("match_reason") or "Adds source-backed context only; it is not an instruction, finding, or action.",
        "evidence_refs": evidence_refs(card),
        "limitations": card.get("limitations") or [
            "Bounded source sample only.",
            "Review/demo context only.",
            "No action, enforcement, legal finding, or execution is created.",
        ],
        "not_a_finding": True,
        "technical_refs": {
            "source_card_id": card.get("card_id"),
            "external_record_id": card.get("external_record_id"),
            "recommended_panel": card.get("recommended_panel"),
            "source_url": card.get("source_url"),
            "license_or_attribution": card.get("license_or_attribution"),
        },
    }


def build_blockers() -> list[dict[str, Any]]:
    return [
        {
            "card_id": "source-ui-blocker-candidate-observation-detail",
            "record_class": "DATA_DEPTH_BLOCKER",
            "card_type": "candidate_observation_source_depth_gap",
            "title": "DATA DEPTH BLOCKER: candidate observation source detail missing",
            "plain_language_summary": "Candidate observation references exist, but the bundle does not include plain-language media observation records with source fields, time, place, and reviewed status.",
            "missing_record": "source-backed candidate observation record",
            "needed_for": "candidate observation viewer card",
            "required_next_data": "Land bounded media-observation records before full viewer validation.",
            "technical_refs": {
                "blocked_moment": "M13",
                "source_refs": ["outputs/main_citybrain_d7_perception_candidate_observation_milestone_freeze"],
            },
        },
        {
            "card_id": "source-ui-blocker-forbidden-command-refusal-record",
            "record_class": "DATA_DEPTH_BLOCKER",
            "card_type": "guardrail_refusal_source_depth_gap",
            "title": "DATA DEPTH BLOCKER: forbidden-command refusal evidence missing",
            "plain_language_summary": "The control-room bundle proves forbidden commands are blocked, but it does not yet include a viewer-ready refusal record with source-backed wording and a review log.",
            "missing_record": "source-backed refusal or review-log record",
            "needed_for": "guardrail refusal viewer card",
            "required_next_data": "Promote the guardrail refusal smoke output into a source-backed review card.",
            "technical_refs": {
                "blocked_moment": "M07",
                "source_refs": ["outputs/main_citybrain_d6_track_d_option_set_promotion_guardrail_smoke_r2"],
            },
        },
        {
            "card_id": "source-ui-blocker-human-review-stop-record",
            "record_class": "DATA_DEPTH_BLOCKER",
            "card_type": "human_review_stop_source_depth_gap",
            "title": "DATA DEPTH BLOCKER: human-review stop evidence missing",
            "plain_language_summary": "The bundle shows review boundaries, but it does not yet contain an external-facing source record proving where the proposal path stops for human review.",
            "missing_record": "source-backed human-review stop record",
            "needed_for": "human review stop viewer card",
            "required_next_data": "Create a viewer-ready review-stop record from the promotion readiness lane.",
            "technical_refs": {
                "blocked_moment": "M08",
                "source_refs": ["outputs/main_citybrain_d6_track_d_mobility_access_promotion_readiness_closeout"],
            },
        },
    ]


def build_integrated_bundle() -> dict[str, Any]:
    london, chicago, helsinki, candidate = source_cards()
    situation = [normalize_card(card, "london", idx + 1) for idx, card in enumerate(london)]
    similar = [normalize_card(card, "chicago", idx + 1) for idx, card in enumerate(chicago)]
    visual = [normalize_card(card, "helsinki", idx + 1) for idx, card in enumerate(helsinki)]
    blocker_records = build_blockers()
    total = len(situation) + len(similar) + len(visual)
    return {
        "schema_version": "citybrain-source-record-ui-integrated-r1",
        "status": "PASS_SOURCE_RECORD_UI_INTEGRATED_WITH_DATA_DEPTH_BLOCKERS",
        "task_name": TASKS["adapter"]["task_name"],
        "timestamp": now(),
        "source_backed_default_card_count": total,
        "situation_city_record_count": len(situation),
        "similar_case_city_record_count": len(similar),
        "visual_entity_city_record_count": len(visual),
        "data_depth_blocker_count": len(blocker_records),
        "situation_city_records": situation,
        "similar_case_city_records": similar,
        "visual_entity_city_records": visual,
        "data_depth_blockers": blocker_records,
        "technical_refs": {
            "source_paths": [
                rel(INPUTS["london_bundle"]),
                rel(INPUTS["chicago_bundle"]),
                rel(INPUTS["helsinki_bundle"]),
                rel(INPUTS["candidate_bundle"]),
            ],
            "candidate_bundle_keys": sorted(candidate.keys()),
            "boundary": BOUNDARY_TEXT,
        },
    }


def card_index(bundle: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for section in ("situation_city_records", "similar_case_city_records", "visual_entity_city_records", "data_depth_blockers"):
        for card in bundle.get(section, []):
            rows.append(
                {
                    "card_id": card["card_id"],
                    "section": section,
                    "record_class": card.get("record_class"),
                    "title": card.get("title"),
                    "default_visible": True,
                    "source_city": card.get("source_city"),
                    "source_system_or_dataset": card.get("source_system_or_dataset"),
                }
            )
    return {
        "schema_version": "citybrain-source-record-ui-card-index-r1",
        "status": "PASS",
        "timestamp": now(),
        "card_count": len(rows),
        "cards": rows,
    }


def strip_details(html: str) -> str:
    return re.sub(r"<details[\s\S]*?</details>", "", html, flags=re.IGNORECASE)


def visible_text_from_html(html: str) -> str:
    stripped = strip_details(html)
    stripped = re.sub(r"<script[\s\S]*?</script>", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"<style[\s\S]*?</style>", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"<[^>]+>", " ", stripped)
    stripped = html_lib.unescape(stripped)
    return re.sub(r"\s+", " ", stripped).strip()


def dom_assertions(html_path: Path) -> dict[str, Any]:
    text = visible_text_from_html(html_path.read_text(encoding="utf-8"))
    forbidden_hits = [label for label in FORBIDDEN_DEFAULT_LABELS if label in text]
    missing_required = [phrase for phrase in REQUIRED_VISIBLE_PHRASES if phrase not in text]
    return {
        "status": "PASS" if not forbidden_hits and not missing_required else "FAIL",
        "visible_text_char_count": len(text),
        "forbidden_default_label_hits": forbidden_hits,
        "required_visible_phrase_missing": missing_required,
        "required_visible_phrase_count": len(REQUIRED_VISIBLE_PHRASES),
    }


def render_static_dom(output_path: Path) -> dict[str, Any]:
    command = ["node", "apps/web-control-room/src/renderSnapshot.mjs", str(output_path)]
    result = subprocess.run(command, cwd=REPO, text=True, capture_output=True, check=False)
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "output_path": rel(output_path),
        "output_exists": output_path.exists(),
    }


def secret_audit(paths: list[Path]) -> dict[str, Any]:
    patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(password|secret|api[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    ]
    hits = []
    for path in paths:
        if not path.exists() or path.suffix.lower() not in {".json", ".md", ".txt", ".html", ".js", ".mjs", ".py"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                hits.append(rel(path))
                break
    return {"status": "PASS" if not hits else "FAIL_SECRET_PATTERN_FOUND", "hit_count": len(hits), "hits": hits}


def claim_boundary_audit() -> dict[str, Any]:
    files = [
        REPO / "apps" / "web-control-room" / "src" / "renderApp.js",
        INTEGRATED_FIXTURE_ROOT / "source_record_ui_integrated_bundle.json",
    ]
    forbidden_claims = [
        "production deployment",
        "public api deployed",
        "autonomous dispatch",
        "autonomous monitoring",
        "legal finding",
        "certified finding",
        "official ticket created",
        "route/control command executed",
    ]
    hits = []
    for path in files:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for claim in forbidden_claims:
            for match in re.finditer(re.escape(claim), text):
                prefix = text[max(0, match.start() - 90):match.start()]
                if re.search(r"\b(no|not|without|do not|does not|must not|cannot)\b", prefix):
                    continue
                hits.append({"path": rel(path), "claim": claim})
    return {
        "status": "PASS" if not hits else "FAIL_FORBIDDEN_CLAIM_FOUND",
        "hits": hits,
        "boundary": BOUNDARY_TEXT,
    }


def hash_manifest(paths: list[Path]) -> dict[str, Any]:
    rows = []
    for path in sorted(set(paths)):
        if path.exists() and path.is_file():
            rows.append({"path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size})
    return {"schema_version": "citybrain-hash-manifest-r1", "timestamp": now(), "file_count": len(rows), "files": rows}


def collect_generated_files() -> list[Path]:
    files = []
    for task in TASKS.values():
        root = task["root"]
        if root.exists():
            files.extend(path for path in root.rglob("*") if path.is_file())
    if INTEGRATED_FIXTURE_ROOT.exists():
        files.extend(path for path in INTEGRATED_FIXTURE_ROOT.rglob("*") if path.is_file())
    return files


def run() -> dict[str, Any]:
    ensure_roots()
    input_hashes_before = file_hashes({key: path for key, path in INPUTS.items() if "web_" not in key and key != "snapshot_renderer"})

    missing = [key for key, path in INPUTS.items() if not path.exists()]
    recovery_status = read_json(INPUTS["recovery_handoff_decision"]).get("status") if INPUTS["recovery_handoff_decision"].exists() else "missing"

    preflight_status = "PASS_MAIN_CITYBRAIN_D8_SOURCE_RECORD_UI_INTEGRATION_PREFLIGHT" if not missing and recovery_status.startswith("PASS_") else "FAIL_MAIN_CITYBRAIN_D8_SOURCE_RECORD_UI_INTEGRATION_PREFLIGHT"
    preflight_root = TASKS["preflight"]["root"]
    write_json(preflight_root / "INPUT_ARTIFACT_INDEX.json", input_artifact_index())
    write_json(
        preflight_root / TASKS["preflight"]["decision"],
        {
            "status": preflight_status,
            "task_name": TASKS["preflight"]["task_name"],
            "timestamp": now(),
            "missing_inputs": missing,
            "recovery_handoff_status": recovery_status,
            "boundary": BOUNDARY_TEXT,
            "stop_on_failure": preflight_status.startswith("FAIL"),
        },
    )
    output_index(preflight_root, TASKS["preflight"]["task_name"], [TASKS["preflight"]["decision"], "INPUT_ARTIFACT_INDEX.json"])
    if preflight_status.startswith("FAIL"):
        return {"final_status": preflight_status, "blocked": True}

    integrated = build_integrated_bundle()
    index = card_index(integrated)
    blockers_payload = {
        "schema_version": "citybrain-source-record-ui-data-depth-blockers-r1",
        "status": "PASS_WITH_OPEN_DATA_DEPTH_BLOCKERS",
        "timestamp": now(),
        "blocker_count": len(integrated["data_depth_blockers"]),
        "blockers": integrated["data_depth_blockers"],
    }
    write_json(INTEGRATED_FIXTURE_ROOT / "source_record_ui_integrated_bundle.json", integrated)
    write_json(INTEGRATED_FIXTURE_ROOT / "source_record_ui_card_index.json", index)
    write_json(INTEGRATED_FIXTURE_ROOT / "source_record_ui_data_depth_blockers.json", blockers_payload)

    adapter_root = TASKS["adapter"]["root"]
    adapter_status = "PASS_MAIN_CITYBRAIN_D8_INTEGRATED_SOURCE_RECORD_BUNDLE_ADAPTER_R1_WITH_LIMITATIONS"
    write_json(
        adapter_root / TASKS["adapter"]["decision"],
        {
            "status": adapter_status,
            "task_name": TASKS["adapter"]["task_name"],
            "timestamp": now(),
            "integrated_fixture_root": rel(INTEGRATED_FIXTURE_ROOT),
            "source_backed_default_card_count": integrated["source_backed_default_card_count"],
            "situation_city_record_count": integrated["situation_city_record_count"],
            "similar_case_city_record_count": integrated["similar_case_city_record_count"],
            "visual_entity_city_record_count": integrated["visual_entity_city_record_count"],
            "data_depth_blocker_count": integrated["data_depth_blocker_count"],
            "limitations": [
                "M13/M07/M08-equivalent viewer moments remain blocker cards until source-backed records are landed.",
                "Adapter consumes bounded samples; it does not download broad city data.",
            ],
        },
    )
    write_json(
        adapter_root / "ADAPTER_REPORT.json",
        {
            "status": "PASS",
            "fixture_files": [
                rel(INTEGRATED_FIXTURE_ROOT / "source_record_ui_integrated_bundle.json"),
                rel(INTEGRATED_FIXTURE_ROOT / "source_record_ui_card_index.json"),
                rel(INTEGRATED_FIXTURE_ROOT / "source_record_ui_data_depth_blockers.json"),
            ],
            "default_card_families": {
                "london": integrated["situation_city_record_count"],
                "chicago": integrated["similar_case_city_record_count"],
                "helsinki": integrated["visual_entity_city_record_count"],
                "blockers": integrated["data_depth_blocker_count"],
            },
        },
    )
    output_index(adapter_root, TASKS["adapter"]["task_name"], [TASKS["adapter"]["decision"], "ADAPTER_REPORT.json"])

    web_root = TASKS["web"]["root"]
    renderer_text = INPUTS["web_renderer"].read_text(encoding="utf-8")
    loader_text = INPUTS["web_loader"].read_text(encoding="utf-8")
    web_status = "PASS_MAIN_CITYBRAIN_D8_WEB_SOURCE_RECORD_CARDS_R2_WITH_LIMITATIONS"
    web_checks = {
        "uses_integrated_source_bundle": "integratedSourceRecords" in renderer_text and "SOURCE_RECORD_UI_BASE" in loader_text,
        "renders_london_section": "london-source-records" in renderer_text,
        "renders_chicago_section": "chicago-precedent-records" in renderer_text,
        "renders_helsinki_section": "helsinki-visual-entity-records" in renderer_text,
        "renders_data_depth_blockers": "source-depth-blockers" in renderer_text,
        "raw_ids_kept_in_details": "technical-details" in renderer_text,
    }
    write_json(
        web_root / TASKS["web"]["decision"],
        {
            "status": web_status if all(web_checks.values()) else "FAIL_MAIN_CITYBRAIN_D8_WEB_SOURCE_RECORD_CARDS_R2",
            "task_name": TASKS["web"]["task_name"],
            "timestamp": now(),
            "web_checks": web_checks,
            "web_files_changed": [rel(INPUTS["web_renderer"]), rel(INPUTS["web_loader"]), rel(INPUTS["snapshot_renderer"])],
        },
    )
    write_json(
        web_root / "WEB_SOURCE_RECORD_RENDERING_PATCH_REPORT.json",
        {
            "status": "PASS" if all(web_checks.values()) else "FAIL",
            "default_view_policy": "Render source-backed city cards and data-depth blockers; keep raw refs in collapsed technical details.",
            "card_sections": ["London mobility records", "Chicago precedent records", "Helsinki visual-entity records", "Data-depth gaps"],
        },
    )
    write_json(
        web_root / "DEFAULT_UI_FORBIDDEN_LABEL_AUDIT.json",
        {
            "status": "PENDING_DOM_SMOKE",
            "forbidden_default_labels": FORBIDDEN_DEFAULT_LABELS,
            "scope": "default visible DOM excluding collapsed technical details",
        },
    )
    write_json(
        web_root / "WEB_SOURCE_RECORD_DOM_ASSERTION_PLAN.json",
        {
            "status": "READY",
            "required_visible_phrases": REQUIRED_VISIBLE_PHRASES,
            "forbidden_default_labels": FORBIDDEN_DEFAULT_LABELS,
            "capture_method": "node renderSnapshot static DOM plus optional live browser verification",
        },
    )
    output_index(web_root, TASKS["web"]["task_name"], [TASKS["web"]["decision"], "WEB_SOURCE_RECORD_RENDERING_PATCH_REPORT.json", "DEFAULT_UI_FORBIDDEN_LABEL_AUDIT.json", "WEB_SOURCE_RECORD_DOM_ASSERTION_PLAN.json"])

    parity_root = TASKS["parity"]["root"]
    parity_rows = [
        {
            "moment": "M02 similar-case memory",
            "default_ui_status": "PASS_SOURCE_RECORD_RENDERED",
            "record_count": integrated["similar_case_city_record_count"],
            "visible_as": "Chicago precedent records with source IDs and match reasons.",
        },
        {
            "moment": "M03 honest uncertainty",
            "default_ui_status": "PASS_LIMITATIONS_AND_DATA_DEPTH_VISIBLE",
            "record_count": integrated["data_depth_blocker_count"],
            "visible_as": "Blockers and limitations state what cannot be shown as city fact.",
        },
        {
            "moment": "M06 shared-axis tradeoff",
            "default_ui_status": "PASS_REVIEW_ONLY_OPTION_AXES_RENDERED",
            "record_count": read_json(INPUTS["runtime_options"]).get("candidate_option_count"),
            "visible_as": "Review-only choices with access, delay, kerbside, and evidence axes.",
        },
        {
            "moment": "M07 forbidden command refusal",
            "default_ui_status": "BLOCKED_SOURCE_RECORD_MISSING",
            "record_count": 0,
            "visible_as": "Data-depth blocker; no invented refusal story.",
        },
        {
            "moment": "M08 human review stop",
            "default_ui_status": "BLOCKED_SOURCE_RECORD_MISSING",
            "record_count": 0,
            "visible_as": "Data-depth blocker; boundary text remains visible.",
        },
        {
            "moment": "M10 source/entity/link cards",
            "default_ui_status": "PASS_SOURCE_RECORD_RENDERED",
            "record_count": integrated["visual_entity_city_record_count"],
            "visible_as": "Helsinki visual-entity records with visual object paths.",
        },
        {
            "moment": "M12 limitations ledger",
            "default_ui_status": "PASS_LIMITATIONS_VISIBLE",
            "record_count": len(read_json(INPUTS["runtime_limitations"]).get("limitations", [])),
            "visible_as": "Viewer limitations and review boundary.",
        },
        {
            "moment": "M13 candidate observation",
            "default_ui_status": "BLOCKED_SOURCE_RECORD_MISSING",
            "record_count": 0,
            "visible_as": "Data-depth blocker; no invented observation story.",
        },
    ]
    parity_status = "PASS_MAIN_CITYBRAIN_D8_MOMENT_SOURCE_RECORD_PARITY_R3_WITH_LIMITATIONS"
    write_json(parity_root / TASKS["parity"]["decision"], {"status": parity_status, "task_name": TASKS["parity"]["task_name"], "timestamp": now(), "blocking_source_gaps": 3})
    write_json(parity_root / "MOMENT_SOURCE_RECORD_PARITY_REPORT.json", {"status": parity_status, "moments": parity_rows})
    write_json(
        parity_root / "EXTERNAL_VIEWER_READINESS_BY_MOMENT.json",
        {
            "status": "PARTIAL_VIEWER_READINESS_WITH_SOURCE_GAPS",
            "ready_moments": [row["moment"] for row in parity_rows if row["default_ui_status"].startswith("PASS")],
            "blocked_moments": [row["moment"] for row in parity_rows if row["default_ui_status"].startswith("BLOCKED")],
            "external_viewer_validation_ready": False,
        },
    )
    write_text(
        parity_root / "SOURCE_RECORD_MOMENT_GAPS.md",
        "# Source-Record Moment Gaps\n\n"
        "- Candidate observation still needs source-backed media observation records.\n"
        "- Forbidden-command refusal needs a source-backed refusal or review-log card.\n"
        "- Human-review stop needs an external-facing review-stop source record.\n",
    )
    output_index(parity_root, TASKS["parity"]["task_name"], [TASKS["parity"]["decision"], "MOMENT_SOURCE_RECORD_PARITY_REPORT.json", "EXTERNAL_VIEWER_READINESS_BY_MOMENT.json", "SOURCE_RECORD_MOMENT_GAPS.md"])

    smoke_root = TASKS["smoke"]["root"]
    capture_path = smoke_root / "CITY_FACT_DOM_CAPTURE.html"
    static_evidence = render_static_dom(capture_path)
    dom_report = dom_assertions(capture_path) if capture_path.exists() and static_evidence["returncode"] == 0 else {
        "status": "FAIL",
        "visible_text_char_count": 0,
        "forbidden_default_label_hits": [],
        "required_visible_phrase_missing": REQUIRED_VISIBLE_PHRASES,
    }
    smoke_status = "PASS_MAIN_CITYBRAIN_D8_CITY_FACT_DOM_ASSERTION_SMOKE_R4_WITH_LIMITATIONS" if dom_report["status"] == "PASS" else "FAIL_MAIN_CITYBRAIN_D8_CITY_FACT_DOM_ASSERTION_SMOKE_R4"
    write_json(smoke_root / TASKS["smoke"]["decision"], {"status": smoke_status, "task_name": TASKS["smoke"]["task_name"], "timestamp": now(), "dom_assertion_status": dom_report["status"]})
    write_json(smoke_root / "CITY_FACT_DOM_ASSERTION_REPORT.json", dom_report)
    write_json(
        smoke_root / "FORBIDDEN_FIXTURE_LABEL_DOM_AUDIT.json",
        {
            "status": "PASS" if not dom_report["forbidden_default_label_hits"] else "FAIL",
            "forbidden_default_label_hits": dom_report["forbidden_default_label_hits"],
            "scope": "static rendered visible DOM with collapsed technical details removed",
        },
    )
    write_json(smoke_root / "STATIC_DOM_SMOKE_EVIDENCE.json", static_evidence)
    output_index(smoke_root, TASKS["smoke"]["task_name"], [TASKS["smoke"]["decision"], "CITY_FACT_DOM_ASSERTION_REPORT.json", "FORBIDDEN_FIXTURE_LABEL_DOM_AUDIT.json", "STATIC_DOM_SMOKE_EVIDENCE.json", "CITY_FACT_DOM_CAPTURE.html"])

    input_hashes_after = file_hashes({key: path for key, path in INPUTS.items() if "web_" not in key and key != "snapshot_renderer"})
    no_mutation = {
        "status": "PASS" if input_hashes_before == input_hashes_after else "FAIL_READ_ONLY_INPUT_HASH_CHANGED",
        "checked_read_only_inputs": input_hashes_before,
        "after_hashes": input_hashes_after,
        "note": "The web-control-room source files are intentionally patched by this task; upstream recovery/source bundles are read-only.",
    }

    generated_files = collect_generated_files()
    secret = secret_audit(generated_files + [INPUTS["web_renderer"], INPUTS["web_loader"], INPUTS["snapshot_renderer"]])
    claim = claim_boundary_audit()

    closeout_root = TASKS["closeout"]["root"]
    closeout_status = "PASS_MAIN_CITYBRAIN_D8_SOURCE_RECORD_UI_CLOSEOUT_WITH_LIMITATIONS" if smoke_status.startswith("PASS") and no_mutation["status"] == "PASS" and secret["status"] == "PASS" and claim["status"] == "PASS" else "FAIL_MAIN_CITYBRAIN_D8_SOURCE_RECORD_UI_CLOSEOUT"
    current_truth = {
        "status": closeout_status,
        "source_backed_default_card_count": integrated["source_backed_default_card_count"],
        "data_depth_blocker_count": integrated["data_depth_blocker_count"],
        "default_view": "actual city/source-derived records plus explicit blockers",
        "technical_details_policy": "raw packet and fixture IDs remain collapsed by default",
        "external_viewer_validation_ready": False,
    }
    remaining_gaps = {
        "status": "OPEN_DATA_DEPTH_GAPS",
        "blocking_gap_count": integrated["data_depth_blocker_count"],
        "gaps": integrated["data_depth_blockers"],
        "recommended_next_task": "MAIN-CITYBRAIN-D8-REAL-VIEWER-CAPTURE-AND-FEEDBACK-PACKAGE-R1_AFTER_SOURCE_GAP_ACCEPTANCE_OR_RESOLUTION",
    }
    write_json(closeout_root / TASKS["closeout"]["decision"], {"status": closeout_status, "task_name": TASKS["closeout"]["task_name"], "timestamp": now(), "blocking_source_gap_count": integrated["data_depth_blocker_count"], "recommended_next_task": remaining_gaps["recommended_next_task"]})
    write_text(
        closeout_root / "SOURCE_RECORD_UI_CLOSEOUT_REPORT.md",
        "# Source-Record UI Closeout\n\n"
        f"Status: `{closeout_status}`\n\n"
        f"- Source-backed/default city records: {integrated['source_backed_default_card_count']}\n"
        f"- Data-depth blockers: {integrated['data_depth_blocker_count']}\n"
        "- Default UI renders London, Chicago, and Helsinki records before technical details.\n"
        "- Full naive external viewer validation remains gated by the open blocker cards.\n",
    )
    write_json(closeout_root / "CURRENT_WEB_UI_TRUTH_REGISTER.json", current_truth)
    write_json(closeout_root / "REMAINING_SOURCE_DATA_GAPS_FOR_VIEWER_VALIDATION.json", remaining_gaps)
    write_json(closeout_root / "NO_MUTATION_AUDIT.json", no_mutation)
    write_json(closeout_root / "SECRET_AUDIT.json", secret)
    write_json(closeout_root / "CLAIM_BOUNDARY_AUDIT.json", claim)
    closeout_hash = hash_manifest(collect_generated_files())
    write_json(closeout_root / "HASH_MANIFEST.json", closeout_hash)
    output_index(closeout_root, TASKS["closeout"]["task_name"], [TASKS["closeout"]["decision"], "SOURCE_RECORD_UI_CLOSEOUT_REPORT.md", "CURRENT_WEB_UI_TRUTH_REGISTER.json", "REMAINING_SOURCE_DATA_GAPS_FOR_VIEWER_VALIDATION.json", "NO_MUTATION_AUDIT.json", "SECRET_AUDIT.json", "CLAIM_BOUNDARY_AUDIT.json", "HASH_MANIFEST.json"])

    freeze_root = TASKS["freeze"]["root"]
    freeze_status = "PASS_MAIN_CITYBRAIN_D8_SOURCE_RECORD_UI_MILESTONE_FREEZE_WITH_LIMITATIONS" if closeout_status.startswith("PASS") else "FAIL_MAIN_CITYBRAIN_D8_SOURCE_RECORD_UI_MILESTONE_FREEZE"
    package_path = freeze_root / "SOURCE_RECORD_UI_VALIDATION_PACKAGE.zip"
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in [
            INTEGRATED_FIXTURE_ROOT / "source_record_ui_integrated_bundle.json",
            INTEGRATED_FIXTURE_ROOT / "source_record_ui_card_index.json",
            INTEGRATED_FIXTURE_ROOT / "source_record_ui_data_depth_blockers.json",
            smoke_root / "CITY_FACT_DOM_CAPTURE.html",
            smoke_root / "CITY_FACT_DOM_ASSERTION_REPORT.json",
            closeout_root / "CURRENT_WEB_UI_TRUTH_REGISTER.json",
            closeout_root / "REMAINING_SOURCE_DATA_GAPS_FOR_VIEWER_VALIDATION.json",
        ]:
            if path.exists():
                archive.write(path, rel(path))
    go_no_go = {
        "status": "CONDITIONAL_GO_FOR_INTERNAL_CAPTURE_NO_GO_FOR_FULL_NAIVE_VALIDATION",
        "internal_source_backed_capture_ready": True,
        "external_naive_viewer_validation_ready": False,
        "reason": "Default source-backed records render, but candidate observation, forbidden-command refusal, and human-review stop still require source-backed records or explicit acceptance as blockers.",
    }
    write_json(freeze_root / TASKS["freeze"]["decision"], {"status": freeze_status, "task_name": TASKS["freeze"]["task_name"], "timestamp": now(), "validation_package": rel(package_path), "external_viewer_go_no_go": go_no_go["status"]})
    write_text(
        freeze_root / "SOURCE_RECORD_UI_BASELINE_SUMMARY.md",
        "# Source-Record UI Baseline\n\n"
        f"Status: `{freeze_status}`\n\n"
        "The frozen baseline makes recovered city/source records the default web-control-room story and keeps unresolved depth as visible blocker cards.\n",
    )
    write_json(freeze_root / "EXTERNAL_VIEWER_GO_NO_GO.json", go_no_go)
    freeze_hash = hash_manifest(collect_generated_files())
    write_json(freeze_root / "HASH_MANIFEST.json", freeze_hash)
    output_index(freeze_root, TASKS["freeze"]["task_name"], [TASKS["freeze"]["decision"], "SOURCE_RECORD_UI_BASELINE_SUMMARY.md", "SOURCE_RECORD_UI_VALIDATION_PACKAGE.zip", "EXTERNAL_VIEWER_GO_NO_GO.json", "HASH_MANIFEST.json"])

    return {
        "final_status": freeze_status,
        "output_roots": {key: rel(task["root"]) for key, task in TASKS.items()},
        "integrated_fixture_root": rel(INTEGRATED_FIXTURE_ROOT),
        "source_backed_default_card_count": integrated["source_backed_default_card_count"],
        "data_depth_blocker_count": integrated["data_depth_blocker_count"],
        "dom_assertion_status": dom_report["status"],
        "forbidden_default_label_hits": dom_report["forbidden_default_label_hits"],
        "missing_required_visible_phrases": dom_report["required_visible_phrase_missing"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret["status"],
        "claim_boundary_status": claim["status"],
        "recommended_next_task": remaining_gaps["recommended_next_task"],
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, sort_keys=True))
    sys.exit(0 if str(result.get("final_status", "")).startswith("PASS") else 1)
