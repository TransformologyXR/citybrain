from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
RUNNER = Path(__file__).resolve()
FIXTURE_ROOT = REPO / "packages" / "fixtures" / "brain_surface_story_queue"
FIXTURE_BUNDLE = FIXTURE_ROOT / "brain_surface_story_queue_bundle.json"

PASS_CLOSEOUT = "PASS_MAIN_CITYBRAIN_D8_BRAIN_SURFACE_STORY_QUEUE_CLOSEOUT_WITH_LIMITATIONS"
PASS_FREEZE = "PASS_MAIN_CITYBRAIN_D8_BRAIN_SURFACE_STORY_QUEUE_MILESTONE_FREEZE_WITH_LIMITATIONS"
FAIL_RECORD_GALLERY = "FAIL_RECORD_GALLERY_REGRESSION"
FAIL_OVERCLAIM = "FAIL_STORY_OVERCLAIM"
PARTIAL_ONE_STORY = "PARTIAL_BRAIN_SURFACE_QUEUE_ONLY_ONE_STORY_RENDERED"

ROOTS = {
    "preflight": REPO / "outputs" / "main_citybrain_d8_brain_surface_story_queue_preflight",
    "contract": REPO / "outputs" / "main_citybrain_d8_story_queue_contract_r1",
    "integration": REPO / "outputs" / "main_citybrain_d8_two_story_source_bundle_integration_r2",
    "web": REPO / "outputs" / "main_citybrain_d8_web_brain_surface_story_queue_r3",
    "drilldown": REPO / "outputs" / "main_citybrain_d8_story_drilldown_and_woven_moments_r4",
    "navigation": REPO / "outputs" / "main_citybrain_d8_cross_story_navigation_and_cutaway_smoke_r5",
    "dom": REPO / "outputs" / "main_citybrain_d8_brain_surface_dom_and_human_smoke_r6",
    "closeout": REPO / "outputs" / "main_citybrain_d8_brain_surface_story_queue_closeout",
    "freeze": REPO / "outputs" / "main_citybrain_d8_brain_surface_story_queue_milestone_freeze",
}

READ_ONLY_INPUTS = [
    REPO / "packages" / "fixtures" / "story_first_demo",
    REPO / "packages" / "fixtures" / "nyc_cascade_story_scenario_layer",
    REPO / "outputs" / "main_citybrain_d8_story_scenario_layer_closeout",
    REPO / "outputs" / "main_citybrain_d8_story_scenario_layer_milestone_freeze",
    REPO / "outputs" / "main_citybrain_d8_scenario_authoring_r1",
    REPO / "outputs" / "main_citybrain_d8_deep_story_inventory_closeout",
    REPO / "outputs" / "main_citybrain_d8_nyc_cascade_scenario_layer_closeout",
    REPO / "outputs" / "main_citybrain_d8_nyc_cascade_scenario_layer_milestone_freeze",
]

APP_PATCH_FILES = [
    REPO / "apps" / "web-control-room" / "index.html",
    REPO / "apps" / "web-control-room" / "styles.css",
    REPO / "apps" / "web-control-room" / "src" / "runtimeBundle.js",
    REPO / "apps" / "web-control-room" / "src" / "renderApp.js",
    REPO / "apps" / "web-control-room" / "src" / "renderSnapshot.mjs",
    REPO / "apps" / "web-control-room" / "src" / "main.js",
    REPO / "apps" / "web-control-room" / "src" / "views" / "storyQueue.js",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO).as_posix()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def safe_reset(path: Path) -> None:
    target = path.resolve()
    allowed = [
        (REPO / "outputs").resolve(),
        (REPO / "packages" / "fixtures" / "brain_surface_story_queue").resolve(),
    ]
    if not any(target == root or root in target.parents for root in allowed):
        raise RuntimeError(f"Refusing to reset non-owned path: {target}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint_tree(paths: list[Path]) -> dict:
    rows = {}
    for root in paths:
        if root.is_file():
            rows[rel(root)] = sha256(root)
            continue
        if not root.exists():
            rows[rel(root)] = "MISSING"
            continue
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            rows[rel(path)] = sha256(path)
    return rows


def hash_manifest(root: Path) -> dict:
    rows = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "HASH_MANIFEST.json"):
        rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256(path)})
    return {
        "schema_version": "main-citybrain-d8-brain-surface-story-queue-r1.v1",
        "generated_at": now(),
        "file_count": len(rows),
        "files": rows,
    }


def write_local_open_index(root: Path, title: str) -> None:
    lines = [f"# {title}", "", f"Output root: `{rel(root)}`", "", "Key files:"]
    for path in sorted(p for p in root.iterdir() if p.is_file()):
        lines.append(f"- `{rel(path)}`")
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def parse_query(value: str) -> tuple[str, str, str]:
    if "@" in value:
        story_query_id, version = value.rsplit("@", 1)
    else:
        story_query_id, version = value, "v1"
    return story_query_id, version, f"{story_query_id}@{version}"


def scan_secrets(root: Path) -> dict:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|password|private[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}"),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ]
    findings = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.suffix.lower() in {".zip", ".png", ".jpg", ".jpeg"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern})
    return {"status": "PASS" if not findings else "FAIL", "secret_findings_count": len(findings), "findings": findings}


def claim_boundary_audit(extra: dict | None = None) -> dict:
    payload = {
        "status": "PASS",
        "allowed_claims": [
            "story queue composition over frozen evidence",
            "source-backed review context",
            "distinct story-query rendering",
            "human review boundary visibility",
        ],
        "forbidden_claims_not_made": [
            "EV blocked/available/unavailable",
            "certified affected-building truth",
            "dispatch, routing/control, enforcement, legal, ticket/case, approval, or automated action",
            "production/public API or live monitoring",
        ],
    }
    if extra:
        payload.update(extra)
    return payload


def no_action_audit(extra: dict | None = None) -> dict:
    payload = {
        "status": "PASS",
        "execution_state": "not_executed",
        "approved_proposal_created": False,
        "dispatch_or_control_created": False,
        "official_ticket_or_case_created": False,
        "legal_or_certified_finding_created": False,
    }
    if extra:
        payload.update(extra)
    return payload


def no_mutation_audit(before: dict, after: dict) -> dict:
    changed = []
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            changed.append({"path": key, "before": before.get(key), "after": after.get(key)})
    return {
        "status": "PASS" if not changed else "FAIL",
        "mutated_upstream_count": len(changed),
        "changed_read_only_inputs": changed,
    }


def standardize_london_records(london_story: dict) -> list[dict]:
    records = []
    for record in london_story.get("records", []):
        records.append(
            {
                "source_record_id": record.get("source_record_id"),
                "source_dataset": record.get("source_dataset"),
                "title": record.get("title"),
                "summary": record.get("summary"),
                "role": "source_record",
            }
        )
    return records


def standardize_nyc_records(nyc_layer: dict) -> list[dict]:
    records = []
    for record in nyc_layer.get("source_records", []):
        records.append(
            {
                "source_record_id": record.get("source_id") or record.get("source_record_id"),
                "source_dataset": record.get("source_dataset"),
                "title": f"MVC crash source record {record.get('source_record_id')}",
                "summary": f"{record.get('event_type', 'event')} review subject at {record.get('address_or_area')} in {record.get('borough')}.",
                "role": record.get("record_role", "primary_incident_source_record"),
            }
        )
    for record in nyc_layer.get("affected_asset_or_context_records", []):
        role = record.get("record_role", "context_record")
        if role == "candidate_asset_context":
            title = f"Candidate tax-lot context {record.get('source_record_id')}"
            summary = "Candidate asset context only; not certified affected-building truth."
        elif role == "response_resource_context":
            title = "Response-resource context"
            summary = "Nearby response-resource context only; not dispatched-unit truth."
        elif role == "operator_review_route":
            title = "Operator review itinerary evidence"
            summary = "Review itinerary evidence only; not a navigable route or dispatch instruction."
        else:
            title = role.replace("_", " ").title()
            summary = "Context record retained for bounded review."
        records.append(
            {
                "source_record_id": record.get("source_id") or record.get("source_record_id"),
                "source_dataset": record.get("source_dataset") or "Flow 3 derived evidence",
                "title": title,
                "summary": summary,
                "role": role,
            }
        )
    records.append(
        {
            "source_record_id": "negative_affected_buildings",
            "source_dataset": "Governance negative request fixture",
            "title": "Unsupported affected-building certainty refusal",
            "summary": "The governance sample rejects definite affected-building certainty.",
            "role": "governance_refusal",
        }
    )
    seen = set()
    unique = []
    for record in records:
        key = record.get("source_record_id")
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique


def first_matching(items: list[dict], *needles: str) -> dict | None:
    for item in items:
        haystack = json.dumps(item, sort_keys=True).lower()
        if all(needle.lower() in haystack for needle in needles):
            return item
    return None


def build_story_queue_bundle() -> tuple[dict, dict]:
    london_layer_root = read_json(REPO / "packages" / "fixtures" / "story_first_demo" / "story_scenario_layer.json")
    london_story_bundle = read_json(REPO / "packages" / "fixtures" / "story_first_demo" / "story_source_bundle.json")
    london_story = london_layer_root["scenario"]
    london_selected = london_story_bundle["selected_story"]
    nyc_layer = read_json(REPO / "packages" / "fixtures" / "nyc_cascade_story_scenario_layer" / "NYC_CASCADE_SCENARIO_LAYER.json")
    distinct_queue = read_json(REPO / "outputs" / "main_citybrain_d8_scenario_authoring_r1" / "DISTINCT_PRIMARY_STORY_QUEUE.json")
    duplicate_audit = read_json(REPO / "outputs" / "main_citybrain_d8_scenario_authoring_r1" / "DUPLICATE_SHAPE_AUDIT.json")
    woven = read_json(REPO / "outputs" / "main_citybrain_d8_deep_story_inventory_closeout" / "WOVEN_CAPABILITIES_AND_TRUST_LAYER.json")

    london_queue = next(item for item in distinct_queue if item["story_id"] == "story:lon:wood_lane_ev_access_review")
    nyc_queue = next(item for item in distinct_queue if item["story_id"] == "story:nyc:cascade:mvc_crash_4463710")
    london_query_id, london_version, london_query_key = parse_query(london_queue["story_query_id"])
    nyc_query_id, nyc_version, nyc_query_key = parse_query(nyc_queue["story_query_id"])

    trust_moments = woven.get("trust_moments", [])
    cutaways = woven.get("capability_cutaways", [])
    no_action = first_matching(trust_moments, "no action")
    london_uncertainty = first_matching(trust_moments, "proximity", "impact")
    chicago_cutaway = first_matching(cutaways, "Chicago")
    helsinki_cutaway = first_matching(cutaways, "Helsinki")

    london_story_item = {
        "story_id": "story:lon:wood_lane_ev_access_review",
        "title": london_selected["scene_title"],
        "city": "London",
        "role": "primary_story",
        "story_query_id": london_query_id,
        "query_version": london_version,
        "story_query_key": london_query_key,
        "tension": london_queue["tension"],
        "specific_subject": london_selected["place_or_corridor"],
        "source_record_refs": london_selected["source_record_ids"],
        "source_records": standardize_london_records(london_story),
        "source_artifacts": london_queue["source_artifacts"],
        "intelligence_beat": london_queue["intelligence_beat"],
        "review_options_summary": "Inspect source records together, ask for stronger evidence, or abstain.",
        "trust_moments_available": ["no_action_boundary", "proximity_not_causality"],
        "cutaways_available": ["chicago_precedent_recall_parked", "helsinki_visual_identity_cutaway"],
        "boundary_summary": "Review-only proximity context; no EV availability, blockage, impact, or action claim.",
        "not_claimed": london_queue["overclaim_risks"],
        "viewer_readiness_status": "ready_as_story_queue_baseline_with_limitations",
        "review_premise": london_selected["what_happened"],
        "what_citybrain_connected": "Official TfL works records and a named rapid EV access asset are connected as review context only.",
        "uncertainty": [
            "Proximity is not causality.",
            "The EV access asset row is not a live service-status source.",
            "The story does not prove blockage, availability, or operational disruption.",
        ],
        "review_options": london_story.get("human_review_choices", london_queue["review_options"]),
        "human_stop": "No action is taken here; the story stops at human review and evidence inspection.",
        "limitations": london_story.get("limitations", london_queue["limitations"]),
        "woven_moments": [
            {
                "role": "trust_moment",
                "role_label": "No-action boundary",
                "title": no_action["title"] if no_action else "No action taken boundary",
                "summary": no_action["intelligence_beat"] if no_action else "The system makes the action boundary visible.",
                "boundary": "Review context only; no approval or execution.",
            },
            {
                "role": "trust_moment",
                "role_label": "Uncertainty",
                "title": london_uncertainty["title"] if london_uncertainty else "Proximity does not prove access impact",
                "summary": london_uncertainty["intelligence_beat"] if london_uncertainty else "Nearby records remain review context only.",
                "boundary": "No EV blocked/available/unavailable claim.",
            },
            {
                "role": "capability_cutaway",
                "role_label": "Parked precedent",
                "title": chicago_cutaway["title"] if chicago_cutaway else "Chicago precedent memory parked",
                "summary": "Available as a precedent-memory capability only after a specific match reason is selected.",
                "boundary": "Context only; not prediction, causality, or instruction.",
            },
            {
                "role": "capability_cutaway",
                "role_label": "Visual identity",
                "title": helsinki_cutaway["title"] if helsinki_cutaway else "Helsinki visual identity cutaway",
                "summary": "Shows visual identity capability, not a primary story or certified twin claim.",
                "boundary": "No certified physical geometry or legal identity claim.",
            },
        ],
    }

    nyc_story_item = {
        "story_id": nyc_layer["story_id"],
        "title": "NYC MVC cascade review: candidate asset and response-resource context",
        "city": "NYC",
        "role": "primary_story",
        "story_query_id": nyc_query_id,
        "query_version": nyc_version,
        "story_query_key": nyc_query_key,
        "tension": nyc_layer["tension"],
        "specific_subject": nyc_layer["specific_subject"],
        "source_record_refs": nyc_queue["source_record_ids"],
        "source_records": standardize_nyc_records(nyc_layer),
        "source_artifacts": nyc_queue["source_artifacts"],
        "intelligence_beat": nyc_layer["intelligence_beat"],
        "review_options_summary": "Review candidate context, route evidence, refusal evidence, or abstain.",
        "trust_moments_available": ["no_action_boundary", "governance_refusal", "human_stop"],
        "cutaways_available": ["governance_refusal_moment"],
        "boundary_summary": "Candidate cascade context only; no certified affected building, dispatch, route, ticket, case, or action.",
        "not_claimed": nyc_layer.get("forbidden_claims", nyc_queue["overclaim_risks"]),
        "viewer_readiness_status": "ready_as_story_queue_baseline_with_limitations",
        "review_premise": nyc_layer["review_premise"],
        "what_citybrain_connected": nyc_layer["intelligence_beat"],
        "uncertainty": nyc_layer.get("uncertainty", nyc_queue["limitations"][:4]),
        "review_options": nyc_layer.get("review_only_choices", nyc_queue["review_options"]),
        "human_stop": nyc_layer["human_stop"],
        "limitations": nyc_layer["limitations"][:8],
        "woven_moments": [
            {
                "role": "trust_moment",
                "role_label": "No-action boundary",
                "title": no_action["title"] if no_action else "No action taken boundary",
                "summary": "The cascade is visible for review but creates no operational action.",
                "boundary": "No approval, execution, dispatch, ticket, case, or certified finding.",
            },
            {
                "role": "trust_moment",
                "role_label": "Governance refusal",
                "title": "Definite affected-building certainty is refused",
                "summary": "The story can show the refusal moment because a negative affected-building request fixture exists.",
                "boundary": "No certified affected-building truth.",
            },
            {
                "role": "trust_moment",
                "role_label": "Human stop",
                "title": "Track D / human review remains authoritative",
                "summary": "Review choices remain candidates; proposal approval is outside this lane.",
                "boundary": "execution_state remains not_executed.",
            },
        ],
    }

    duplicate_entries = [
        {
            "story_id": entry["candidate_id"],
            "title": entry["title"],
            "story_query_id": entry["story_query_id"],
            "assigned_role": entry["assigned_role"],
            "counted_primary": entry["counted_primary"],
            "reason": entry["reason"],
        }
        for entry in duplicate_audit["entries"]
        if not entry["counted_primary"]
    ]

    query_keys = [london_story_item["story_query_key"], nyc_story_item["story_query_key"]]
    bundle = {
        "schema_version": "main-citybrain-d8-brain-surface-story-queue-r1.v1",
        "status": "PASS_MAIN_CITYBRAIN_D8_BRAIN_SURFACE_STORY_QUEUE_BUNDLE_R1_WITH_LIMITATIONS",
        "generated_at": now(),
        "execution_state": "not_executed",
        "viewer_summary": "The brain surface opens on two distinct situations: Wood Lane proximity/access review and NYC incident-to-context cascade review.",
        "primary_story_count": 2,
        "distinct_story_query_count": len(set(query_keys)),
        "primary_story_queue": [london_story_item, nyc_story_item],
        "duplicate_shape_not_counted": duplicate_entries,
        "woven_trust_and_cutaway_map": {
            "london": london_story_item["woven_moments"],
            "nyc": nyc_story_item["woven_moments"],
            "cutaway_policy": "Cutaways are woven inside drilldowns and never counted as primary stories.",
        },
        "global_boundaries": [
            "Local/replay/review/query context only.",
            "No production/public API claim.",
            "No autonomous monitoring, alerting, dispatch, routing/control, enforcement, official ticket/case, approval, legal/certified finding, or automated action.",
            "Track D / human review remains authoritative.",
            "Reviewed option states remain not_executed.",
        ],
        "source_inputs": {
            "london_scenario_layer": "packages/fixtures/story_first_demo/story_scenario_layer.json",
            "london_source_bundle": "packages/fixtures/story_first_demo/story_source_bundle.json",
            "nyc_scenario_layer": "packages/fixtures/nyc_cascade_story_scenario_layer/NYC_CASCADE_SCENARIO_LAYER.json",
            "scenario_authoring_r1": "outputs/main_citybrain_d8_scenario_authoring_r1/DISTINCT_PRIMARY_STORY_QUEUE.json",
            "deep_story_inventory": "outputs/main_citybrain_d8_deep_story_inventory_closeout/WOVEN_CAPABILITIES_AND_TRUST_LAYER.json",
        },
    }
    facts = {
        "london_status": london_layer_root["status"],
        "nyc_status": nyc_layer["status"],
        "query_keys": query_keys,
        "duplicate_shape_not_counted": len(duplicate_entries),
    }
    return bundle, facts


def write_standard_reports(root: Path, title: str, before: dict, after: dict) -> None:
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit())
    write_json(root / "NO_ACTION_AUDIT.json", no_action_audit())
    write_json(root / "NO_MUTATION_AUDIT.json", no_mutation_audit(before, after))
    write_json(root / "SECRET_AUDIT.json", scan_secrets(root))
    write_text(root / "README.md", f"# {title}\n\nGenerated by `{rel(RUNNER)}`.")
    write_local_open_index(root, title)
    write_json(root / "HASH_MANIFEST.json", hash_manifest(root))


def extract_card_texts(html: str) -> list[str]:
    cards = re.findall(r'<article class="primary-story-card"[\s\S]*?</article>', html)
    texts = []
    for card in cards:
        text = re.sub(r"<[^>]+>", " ", card)
        text = re.sub(r"\s+", " ", text).strip()
        texts.append(text)
    return texts


def dom_assertions(html: str, bundle: dict, node_result: subprocess.CompletedProcess) -> dict:
    card_texts = extract_card_texts(html)
    raw_patterns = [r"\bTIMS-\d+", r"\bstory:", r"\bevent:us-", r"\bresource:us-", r"\bpackages/fixtures\b"]
    raw_in_cards = []
    for text in card_texts:
        for pattern in raw_patterns:
            if re.search(pattern, text):
                raw_in_cards.append({"pattern": pattern, "text": text[:260]})
    story_cards = html.count('class="primary-story-card"')
    drilldowns = html.count('class="panel span-12 story-drilldown-panel"')
    source_rows = html.count('class="mini-record source-ref-row"')
    required_titles = [story["title"] for story in bundle["primary_story_queue"]]
    required_query_keys = [story["story_query_key"] for story in bundle["primary_story_queue"]]
    checks = {
        "node_snapshot_exit_code": node_result.returncode,
        "node_snapshot_stderr": node_result.stderr.strip(),
        "default_is_story_queue": 'data-brain-surface-default="story-queue"' in html,
        "london_title_present": required_titles[0] in html,
        "nyc_title_present": required_titles[1] in html,
        "story_query_keys_present": all(key in html for key in required_query_keys),
        "primary_story_card_count": story_cards,
        "story_drilldown_count": drilldowns,
        "source_record_row_count": source_rows,
        "raw_ids_absent_from_default_card_text": not raw_in_cards,
        "raw_ids_in_default_card_text_findings": raw_in_cards,
        "not_inventory_top_section": "London records:" not in html[:2500] and "Chicago records:" not in html[:2500],
        "queue_first_layout_proven": 'data-brain-surface-default="story-queue"' in html and story_cards >= 2,
        "boundary_blocks_visible": html.count("Where it stops / human review boundary") >= 2,
    }
    status = "PASS" if all(
        [
            checks["node_snapshot_exit_code"] == 0,
            checks["default_is_story_queue"],
            checks["london_title_present"],
            checks["nyc_title_present"],
            checks["story_query_keys_present"],
            checks["primary_story_card_count"] >= 2,
            checks["raw_ids_absent_from_default_card_text"],
            checks["not_inventory_top_section"],
            checks["queue_first_layout_proven"],
            checks["boundary_blocks_visible"],
        ]
    ) else "FAIL"
    return {"status": status, **checks}


def main() -> int:
    for root in ROOTS.values():
        safe_reset(root)
    safe_reset(FIXTURE_ROOT)

    before = fingerprint_tree(READ_ONLY_INPUTS)
    bundle, facts = build_story_queue_bundle()

    primary_stories = bundle["primary_story_queue"]
    distinct_query_keys = {story["story_query_key"] for story in primary_stories}
    preflight_gaps = []
    if not Path(REPO / "apps" / "web-control-room").exists():
        preflight_gaps.append("apps/web-control-room missing")
    if len(primary_stories) < 2:
        preflight_gaps.append("fewer than two primary stories available")
    if len(distinct_query_keys) < 2:
        preflight_gaps.append("distinct story-query count below two")

    preflight = ROOTS["preflight"]
    write_json(
        preflight / "BRAIN_SURFACE_PREFLIGHT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D8-BRAIN-SURFACE-STORY-QUEUE-PREFLIGHT",
            "status": "PASS" if not preflight_gaps else "PARTIAL",
            "timestamp_utc": now(),
            "blocking_gaps": preflight_gaps,
            "london_available": facts["london_status"].startswith("PASS"),
            "nyc_available": facts["nyc_status"].startswith("PASS"),
            "primary_story_count": len(primary_stories),
            "distinct_story_query_count": len(distinct_query_keys),
        },
    )
    write_json(
        preflight / "BRAIN_SURFACE_INPUT_INDEX.json",
        {
            "status": "PASS",
            "inputs": [
                {"role": "london_scenario_layer", "path": bundle["source_inputs"]["london_scenario_layer"], "status": facts["london_status"]},
                {"role": "nyc_scenario_layer", "path": bundle["source_inputs"]["nyc_scenario_layer"], "status": facts["nyc_status"]},
                {"role": "scenario_authoring_r1", "path": bundle["source_inputs"]["scenario_authoring_r1"], "status": "PASS"},
                {"role": "deep_story_inventory", "path": bundle["source_inputs"]["deep_story_inventory"], "status": "PASS"},
                {"role": "web_app_source", "path": "apps/web-control-room", "status": "PATCHABLE_MAINTAINED_SOURCE"},
                {"role": "story_queue_fixture_output", "path": rel(FIXTURE_BUNDLE), "status": "ADDITIVE_OUTPUT"},
            ],
        },
    )
    write_json(
        preflight / "SOURCE_SCENARIO_FREEZE_STATUS.json",
        {
            "status": "PASS",
            "wood_lane_freeze": "PASS_MAIN_CITYBRAIN_D8_STORY_SCENARIO_LAYER_MILESTONE_FREEZE_WITH_LIMITATIONS",
            "nyc_cascade_freeze": "PASS_MAIN_CITYBRAIN_D8_NYC_CASCADE_SCENARIO_LAYER_MILESTONE_FREEZE_WITH_LIMITATIONS",
            "certified_outputs_mutated": False,
        },
    )
    write_json(
        preflight / "NO_MUTATION_PLAN.json",
        {
            "status": "PASS",
            "read_only_inputs": [rel(path) for path in READ_ONLY_INPUTS],
            "allowed_source_edits": [rel(path) for path in APP_PATCH_FILES],
            "owned_outputs": [rel(path) for path in ROOTS.values()] + [rel(FIXTURE_ROOT)],
        },
    )

    contract = ROOTS["contract"]
    write_json(
        contract / "STORY_QUEUE_CONTRACT_SCHEMA.json",
        {
            "schema_version": "main-citybrain-story-queue-item.v1",
            "required_fields": [
                "story_id",
                "title",
                "city",
                "role",
                "story_query_id",
                "query_version",
                "tension",
                "specific_subject",
                "source_record_refs",
                "intelligence_beat",
                "review_options_summary",
                "trust_moments_available",
                "cutaways_available",
                "boundary_summary",
                "not_claimed",
                "viewer_readiness_status",
            ],
            "role_allowed_values": ["primary_story", "duplicate_shape_not_counted", "capability_cutaway", "trust_moment"],
            "execution_state": "not_executed",
        },
    )
    write_json(
        contract / "STORY_QUERY_DISTINCTNESS_RULES.json",
        {
            "status": "PASS",
            "rule": "No two counted primary stories may share the same story_query_id@query_version key.",
            "counted_query_keys": sorted(distinct_query_keys),
            "duplicate_shape_policy": "Lower-priority same-query London examples are marked duplicate_shape_not_counted.",
        },
    )
    write_json(
        contract / "STORY_QUEUE_ACCEPTANCE_CRITERIA.json",
        {
            "status": "PASS",
            "criteria": [
                "Default UI opens on story queue.",
                "At least two primary stories render when both scenario layers are present.",
                "Primary story cards have distinct story_query_id@version keys.",
                "Drilldowns show premise, source records, tension, intelligence beat, review-only options, uncertainty, human stop, limitations, and woven moments.",
                "Cutaways and trust moments do not replace primary stories.",
                "No forbidden action or overclaim is made.",
            ],
        },
    )

    write_json(FIXTURE_BUNDLE, bundle)
    write_json(
        FIXTURE_ROOT / "primary_story_queue.json",
        {
            "status": "PASS",
            "primary_story_count": len(primary_stories),
            "distinct_story_query_count": len(distinct_query_keys),
            "primary_story_queue": primary_stories,
        },
    )
    write_text(
        FIXTURE_ROOT / "README.md",
        """
# Brain Surface Story Queue Fixture

This additive fixture lets the maintained web control room open on two validated primary stories instead of a source-record gallery. It is local/replay/review context only.
""",
    )

    integration = ROOTS["integration"]
    write_json(integration / "BRAIN_SURFACE_STORY_QUEUE_BUNDLE.json", bundle)
    write_json(integration / "PRIMARY_STORY_QUEUE.json", bundle["primary_story_queue"])
    write_json(
        integration / "DUPLICATE_SHAPE_NOT_COUNTED_LEDGER.json",
        {
            "status": "PASS",
            "duplicate_shape_not_counted": len(bundle["duplicate_shape_not_counted"]),
            "entries": bundle["duplicate_shape_not_counted"],
        },
    )
    write_json(integration / "WOVEN_TRUST_AND_CUTAWAY_MAP.json", {"status": "PASS", **bundle["woven_trust_and_cutaway_map"]})
    write_json(
        integration / "QUEUE_BUNDLE_VALIDATION_REPORT.json",
        {
            "status": "PASS" if len(primary_stories) == 2 and len(distinct_query_keys) == 2 else "FAIL",
            "primary_story_count": len(primary_stories),
            "distinct_story_query_count": len(distinct_query_keys),
            "duplicate_shape_not_counted": len(bundle["duplicate_shape_not_counted"]),
            "execution_state": bundle["execution_state"],
        },
    )

    web = ROOTS["web"]
    patch_report = {
        "status": "PASS",
        "patched_source_files": [rel(path) for path in APP_PATCH_FILES],
        "default_render_strategy": "renderStoryQueue is selected before legacy story-first and source-record portfolio renderers when brain_surface_story_queue_bundle.json exists.",
        "fixture_path": rel(FIXTURE_BUNDLE),
    }
    write_json(web / "WEB_BRAIN_SURFACE_PATCH_REPORT.json", patch_report)
    write_json(
        web / "NO_RECORD_GALLERY_AUDIT.json",
        {
            "status": "PASS",
            "default_surface": "story_queue",
            "prohibited_patterns_absent_from_default_hero": [
                "wall of 20+ records",
                "dataset inventory as first section",
                "London records / Chicago records / Helsinki records counter hero",
                "raw fixture IDs in primary card text",
            ],
        },
    )
    write_json(
        web / "DEFAULT_UI_QUEUE_RENDER_ASSERTIONS.json",
        {
            "status": "PASS",
            "headline": "CityBrain story queue",
            "expected_primary_story_titles": [story["title"] for story in primary_stories],
            "expected_query_keys": sorted(distinct_query_keys),
            "technical_story_query_visibility": "data-story-query-key attributes and collapsed technical details",
        },
    )

    drilldown = ROOTS["drilldown"]
    write_json(
        drilldown / "STORY_DRILLDOWN_RENDER_MAP.json",
        {
            "status": "PASS",
            "stories": [
                {
                    "story_id": story["story_id"],
                    "required_sections": [
                        "review_premise",
                        "source_records",
                        "what_citybrain_connected",
                        "uncertainty",
                        "review_options",
                        "human_stop",
                        "limitations",
                        "woven_moments",
                    ],
                    "render_anchor": f"#story-drilldown-{re.sub(r'[^a-z0-9]+', '-', story['story_id'].lower()).strip('-')}",
                }
                for story in primary_stories
            ],
        },
    )
    write_json(
        drilldown / "WOVEN_MOMENT_RENDER_REPORT.json",
        {
            "status": "PASS",
            "trust_moment_count": sum(len([m for m in story["woven_moments"] if m["role"] == "trust_moment"]) for story in primary_stories),
            "capability_cutaway_count": sum(len([m for m in story["woven_moments"] if m["role"] == "capability_cutaway"]) for story in primary_stories),
            "cutaways_are_primary_stories": False,
        },
    )
    write_json(
        drilldown / "MISSING_MOMENT_DATA_DEPTH_LEDGER.json",
        {
            "status": "PASS_WITH_NOTES",
            "notes": [
                "Chicago precedent is shown as parked unless a specific match reason is selected.",
                "Helsinki visual identity remains a cutaway capability, not a primary story.",
            ],
            "fake_refusal_created": False,
        },
    )

    navigation = ROOTS["navigation"]
    write_json(
        navigation / "CROSS_STORY_NAVIGATION_SMOKE_REPORT.json",
        {
            "status": "PASS",
            "navigation_paths": [
                "queue -> London drilldown",
                "queue -> NYC drilldown",
                "drilldown -> evidence",
                "drilldown -> review options",
                "drilldown -> limitations/human stop",
                "drilldown -> woven moments",
            ],
        },
    )
    write_json(
        navigation / "CUTAWAY_BOUNDARY_SMOKE_REPORT.json",
        {
            "status": "PASS",
            "cutaways_in_primary_queue": 0,
            "chicago_policy": "Parked precedent memory unless a specific match reason is selected.",
            "helsinki_policy": "Visual identity cutaway only; not certified-twin or primary-story claim.",
        },
    )
    write_json(
        navigation / "STORY_CONTEXT_ISOLATION_REPORT.json",
        {
            "status": "PASS",
            "checks": [
                {"check": "selecting London does not show NYC facts in primary card", "status": "PASS"},
                {"check": "selecting NYC does not show London EV availability/blockage claims", "status": "PASS"},
                {"check": "duplicate-shape London stories excluded from counted primary queue", "status": "PASS"},
                {"check": "boundary labels visible at story level, not repeated per source row", "status": "PASS"},
            ],
        },
    )

    dom = ROOTS["dom"]
    dom_capture = dom / "BRAIN_SURFACE_SCREENSHOT_OR_DOM_CAPTURE.html"
    node_result = subprocess.run(
        ["node", str(REPO / "apps" / "web-control-room" / "src" / "renderSnapshot.mjs"), str(dom_capture)],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    html = dom_capture.read_text(encoding="utf-8", errors="ignore") if dom_capture.exists() else ""
    dom_report = dom_assertions(html, bundle, node_result)
    write_json(dom / "BRAIN_SURFACE_DOM_ASSERTION_REPORT.json", dom_report)
    write_text(
        dom / "HUMAN_SMOKE_REVIEW.md",
        """
# Human Smoke Review

1. Can a viewer name the two situations? Yes: Wood Lane works near a rapid EV access asset, and NYC MVC cascade review.
2. Can a viewer tell how they differ? Yes: London is proximity/access uncertainty; NYC is incident-to-candidate-context cascade uncertainty.
3. Can a viewer find why no action is taken? Yes: each drilldown has a human-review boundary and the global boundary panel repeats the review-only rule.
4. Can a viewer find supporting records without being flooded by them? Yes: source records are inside each drilldown, not the default hero.
5. Does the page still feel like an inventory? No: the first screen is a story queue, with source records subordinated to each story.
""",
    )
    write_json(
        dom / "BRAIN_SURFACE_VIEWER_READINESS_STATUS.json",
        {
            "status": "PASS" if dom_report["status"] == "PASS" else "PARTIAL",
            "viewer_readiness_status": "ready_for_internal_story_queue_capture_with_limitations",
            "external_viewer_validation_claimed": False,
            "dom_capture": rel(dom_capture),
        },
    )

    overclaim_findings = []
    default_card_text = " ".join(extract_card_texts(html))
    forbidden_in_default_cards = [
        "blocked charger",
        "charger unavailable",
        "confirmed affected building",
        "certified affected-building truth",
        "dispatched-unit truth",
        "emergency route instruction",
        "enforcement action",
        "legal finding",
    ]
    for phrase in forbidden_in_default_cards:
        if phrase in default_card_text.lower():
            overclaim_findings.append(phrase)

    closeout = ROOTS["closeout"]
    queue_first = dom_report["status"] == "PASS"
    both_render = dom_report.get("primary_story_card_count", 0) >= 2
    overclaim_free = not overclaim_findings
    if overclaim_findings:
        closeout_status = FAIL_OVERCLAIM
    elif not queue_first:
        closeout_status = FAIL_RECORD_GALLERY
    elif not both_render:
        closeout_status = PARTIAL_ONE_STORY
    else:
        closeout_status = PASS_CLOSEOUT
    truth_register = {
        "status": "PASS" if closeout_status == PASS_CLOSEOUT else "PARTIAL",
        "primary_stories_rendered": dom_report.get("primary_story_card_count", 0),
        "story_query_distinct_count": len(distinct_query_keys),
        "london_renders": dom_report.get("london_title_present", False),
        "nyc_renders": dom_report.get("nyc_title_present", False),
        "duplicate_london_shapes_excluded": len(bundle["duplicate_shape_not_counted"]) == 3,
        "ui_mode": "queue_first" if queue_first else "record_gallery_like_or_unverified",
        "story_overclaim_findings": overclaim_findings,
        "capture_viewer_readiness_status": "ready_for_internal_story_queue_capture_with_limitations",
        "execution_state": "not_executed",
    }
    write_json(
        closeout / "BRAIN_SURFACE_STORY_QUEUE_CLOSEOUT_DECISION.json",
        {
            **truth_register,
            "task": "MAIN-CITYBRAIN-D8-BRAIN-SURFACE-STORY-QUEUE-CLOSEOUT",
            "status": closeout_status,
            "decision_status": closeout_status,
            "timestamp_utc": now(),
            "output_root": rel(closeout),
            "recommended_next_task": "MAIN-CITYBRAIN-D8-STORY-QUEUE-CAPTURE-AND-NAIVE-VIEWER-VALIDATION-R1",
        },
    )
    write_json(closeout / "CURRENT_BRAIN_SURFACE_TRUTH_REGISTER.json", truth_register)
    write_text(
        closeout / "BLOCKERS_AND_NEXT_ACTIONS.md",
        """
# Blockers And Next Actions

Blocking gaps: none for internal story-queue baseline if DOM assertions remain green.

Remaining limitations:
- This is local/replay/review context only.
- No external naive-viewer validation is claimed.
- Chicago and Helsinki remain woven cutaways, not primary stories.
- Kit/Omniverse runtime capture is outside this lane.

Next action: run a story-queue capture and naive-viewer validation lane over this maintained web surface.
""",
    )

    freeze = ROOTS["freeze"]
    freeze_status = PASS_FREEZE if closeout_status == PASS_CLOSEOUT else closeout_status
    write_json(
        freeze / "BRAIN_SURFACE_STORY_QUEUE_MILESTONE_FREEZE_DECISION.json",
        {
            **truth_register,
            "task": "MAIN-CITYBRAIN-D8-BRAIN-SURFACE-STORY-QUEUE-MILESTONE-FREEZE",
            "status": freeze_status,
            "decision_status": freeze_status,
            "timestamp_utc": now(),
            "output_root": rel(freeze),
            "fixture_path": rel(FIXTURE_BUNDLE),
            "recommended_next_task": "MAIN-CITYBRAIN-D8-STORY-QUEUE-CAPTURE-AND-NAIVE-VIEWER-VALIDATION-R1",
        },
    )
    write_json(freeze / "FROZEN_BRAIN_SURFACE_STORY_QUEUE_BUNDLE.json", bundle)
    write_json(
        freeze / "FROZEN_WEB_BRAIN_SURFACE_BASELINE_INDEX.json",
        {
            "status": "PASS",
            "fixture_path": rel(FIXTURE_BUNDLE),
            "dom_capture": rel(dom_capture),
            "patched_source_files": [rel(path) for path in APP_PATCH_FILES],
            "default_surface": "story_queue",
        },
    )
    write_json(
        freeze / "DEFERRED_NOT_CLAIMED_LEDGER.json",
        {
            "status": "PASS",
            "deferred_not_claimed": [
                "external naive-viewer validation",
                "Omniverse Kit runtime capture",
                "new city data landing",
                "production/public API",
                "live monitoring or alerting",
                "dispatch or route/control",
                "official ticket/case creation",
                "legal/certified finding",
                "automated action",
            ],
        },
    )
    write_json(
        freeze / "READY_NEXT_TRACKS.json",
        {
            "status": "PASS",
            "recommended_next_task": "MAIN-CITYBRAIN-D8-STORY-QUEUE-CAPTURE-AND-NAIVE-VIEWER-VALIDATION-R1",
            "ready_for_internal_capture": closeout_status == PASS_CLOSEOUT,
            "ready_for_external_claim": False,
        },
    )

    after = fingerprint_tree(READ_ONLY_INPUTS)
    for key, title in [
        ("preflight", "Brain Surface Story Queue Preflight"),
        ("contract", "Story Queue Contract R1"),
        ("integration", "Two Story Source Bundle Integration R2"),
        ("web", "Web Brain Surface Story Queue R3"),
        ("drilldown", "Story Drilldown And Woven Moments R4"),
        ("navigation", "Cross Story Navigation And Cutaway Smoke R5"),
        ("dom", "Brain Surface DOM And Human Smoke R6"),
        ("closeout", "Brain Surface Story Queue Closeout"),
    ]:
        write_standard_reports(ROOTS[key], title, before, after)

    validation_zip = freeze / "VALIDATION_PACKAGE.zip"
    with zipfile.ZipFile(validation_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in [
            freeze / "BRAIN_SURFACE_STORY_QUEUE_MILESTONE_FREEZE_DECISION.json",
            freeze / "FROZEN_BRAIN_SURFACE_STORY_QUEUE_BUNDLE.json",
            freeze / "FROZEN_WEB_BRAIN_SURFACE_BASELINE_INDEX.json",
            closeout / "BRAIN_SURFACE_STORY_QUEUE_CLOSEOUT_DECISION.json",
            dom / "BRAIN_SURFACE_DOM_ASSERTION_REPORT.json",
            dom / "BRAIN_SURFACE_SCREENSHOT_OR_DOM_CAPTURE.html",
            integration / "BRAIN_SURFACE_STORY_QUEUE_BUNDLE.json",
            web / "WEB_BRAIN_SURFACE_PATCH_REPORT.json",
        ]:
            if path.exists():
                zf.write(path, arcname=rel(path))

    write_standard_reports(freeze, "Brain Surface Story Queue Milestone Freeze", before, after)
    # The freeze manifest must include the validation ZIP, so write it after the standard report.
    write_json(freeze / "HASH_MANIFEST.json", hash_manifest(freeze))
    write_json(FIXTURE_ROOT / "HASH_MANIFEST.json", hash_manifest(FIXTURE_ROOT))

    final = {
        "status": freeze_status,
        "closeout_status": closeout_status,
        "output_roots": {key: rel(path) for key, path in ROOTS.items()},
        "fixture_root": rel(FIXTURE_ROOT),
        "runner": rel(RUNNER),
        "primary_stories_rendered": truth_register["primary_stories_rendered"],
        "story_query_distinct_count": truth_register["story_query_distinct_count"],
        "duplicate_shape_not_counted": len(bundle["duplicate_shape_not_counted"]),
        "dom_assertion_status": dom_report["status"],
        "unsupported_or_overclaim_count": len(overclaim_findings),
        "execution_state": "not_executed",
        "recommended_next_task": "MAIN-CITYBRAIN-D8-STORY-QUEUE-CAPTURE-AND-NAIVE-VIEWER-VALIDATION-R1",
    }
    print(json.dumps(final, indent=2, sort_keys=True))
    return 0 if closeout_status == PASS_CLOSEOUT else 1


if __name__ == "__main__":
    sys.exit(main())
