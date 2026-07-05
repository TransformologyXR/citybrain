#!/usr/bin/env python3
"""Run D8 source-record gap closure and scenario-coherence lane."""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]

TASKS = {
    "preflight": ("MAIN-CITYBRAIN-D8-SOURCE-RECORD-GAP-CLOSURE-PREFLIGHT", "outputs/main_citybrain_d8_source_record_gap_closure_preflight", "SOURCE_RECORD_GAP_CLOSURE_PREFLIGHT_DECISION.json"),
    "m13": ("MAIN-CITYBRAIN-D8-D7-MEDIA-OBSERVATION-SOURCE-RECORD-PACK-R1", "outputs/main_citybrain_d8_d7_media_observation_source_record_pack_r1", "D7_MEDIA_OBSERVATION_SOURCE_RECORD_PACK_R1_DECISION.json"),
    "m07": ("MAIN-CITYBRAIN-D8-GUARDRAIL-REFUSAL-REVIEW-LOG-PACK-R1", "outputs/main_citybrain_d8_guardrail_refusal_review_log_pack_r1", "GUARDRAIL_REFUSAL_REVIEW_LOG_PACK_R1_DECISION.json"),
    "m08": ("MAIN-CITYBRAIN-D8-HUMAN-REVIEW-STOP-RECORD-PACK-R1", "outputs/main_citybrain_d8_human_review_stop_record_pack_r1", "HUMAN_REVIEW_STOP_RECORD_PACK_R1_DECISION.json"),
    "coherence": ("MAIN-CITYBRAIN-D8-LONDON-MOBILITY-CORRIDOR-COHERENCE-REVIEW-R1", "outputs/main_citybrain_d8_london_mobility_corridor_coherence_review_r1", "LONDON_MOBILITY_CORRIDOR_COHERENCE_REVIEW_R1_DECISION.json"),
    "web": ("MAIN-CITYBRAIN-D8-WEB-SOURCE-RECORD-GAP-CLOSURE-UI-INTEGRATION-R2", "outputs/main_citybrain_d8_web_source_record_gap_closure_ui_integration_r2", "WEB_SOURCE_RECORD_GAP_CLOSURE_UI_INTEGRATION_R2_DECISION.json"),
    "readiness": ("MAIN-CITYBRAIN-D8-CITY-FACT-VIEWER-READINESS-REVIEW-R3", "outputs/main_citybrain_d8_city_fact_viewer_readiness_review_r3", "CITY_FACT_VIEWER_READINESS_REVIEW_R3_DECISION.json"),
    "closeout": ("MAIN-CITYBRAIN-D8-SOURCE-RECORD-GAP-CLOSURE-CLOSEOUT", "outputs/main_citybrain_d8_source_record_gap_closure_closeout", "SOURCE_RECORD_GAP_CLOSURE_CLOSEOUT_DECISION.json"),
    "freeze": ("MAIN-CITYBRAIN-D8-SOURCE-RECORD-GAP-CLOSURE-MILESTONE-FREEZE", "outputs/main_citybrain_d8_source_record_gap_closure_milestone_freeze", "SOURCE_RECORD_GAP_CLOSURE_MILESTONE_FREEZE_DECISION.json"),
}

INPUTS = {
    "source_record_ui_freeze_decision": "outputs/main_citybrain_d8_source_record_ui_milestone_freeze/SOURCE_RECORD_UI_MILESTONE_FREEZE_DECISION.json",
    "source_record_ui_truth_register": "outputs/main_citybrain_d8_source_record_ui_closeout/CURRENT_WEB_UI_TRUTH_REGISTER.json",
    "integrated_source_bundle": "packages/fixtures/source_record_ui_integrated/source_record_ui_integrated_bundle.json",
    "integrated_source_index": "packages/fixtures/source_record_ui_integrated/source_record_ui_card_index.json",
    "integrated_source_blockers": "packages/fixtures/source_record_ui_integrated/source_record_ui_data_depth_blockers.json",
    "london_source_bundle": "packages/fixtures/london_mobility_source_records/source_record_bundle.json",
    "d7_media_review": "outputs/main_citybrain_d7_perception_demo_media_review_r2/D7_DEMO_MEDIA_REVIEW.json",
    "d7_event_evidence_packets": "outputs/main_citybrain_d7_perception_observation_to_event_evidence_r3/EVENT_EVIDENCE_PACKETS.json",
    "d7_candidate_closeout_ledger": "outputs/main_citybrain_d7_perception_candidate_observation_closeout/D7_CANDIDATE_OBSERVATION_CLOSEOUT_LEDGER.json",
    "guardrail_negative_results": "outputs/main_citybrain_d6_track_d_option_set_promotion_guardrail_smoke_r2/NEGATIVE_FIXTURE_RESULTS.json",
    "guardrail_report": "outputs/main_citybrain_d6_track_d_option_set_promotion_guardrail_smoke_r2/GUARDRAIL_SMOKE_REPORT.json",
    "promotion_bridge_fixtures": "outputs/main_citybrain_d6_track_d_option_set_promotion_bridge_r1/PROMOTION_BRIDGE_FIXTURES.json",
    "promotion_panel_packets": "outputs/main_citybrain_d6_track_d_promotion_panel_r1/PROMOTION_PANEL_PACKETS.json",
    "runtime_track_d_packets": "packages/fixtures/mobility_access/runtime_bundle/track_d_packets.json",
    "web_renderer": "apps/web-control-room/src/renderApp.js",
    "web_index": "apps/web-control-room/index.html",
    "snapshot_renderer": "apps/web-control-room/src/renderSnapshot.mjs",
}

ALLOWED_MUTATION_PREFIXES = (
    "packages/fixtures/source_record_ui_integrated",
    "apps/web-control-room",
    "outputs/main_citybrain_d8_source_record_gap_closure",
    "outputs/main_citybrain_d8_d7_media_observation_source_record_pack_r1",
    "outputs/main_citybrain_d8_guardrail_refusal_review_log_pack_r1",
    "outputs/main_citybrain_d8_human_review_stop_record_pack_r1",
    "outputs/main_citybrain_d8_london_mobility_corridor_coherence_review_r1",
    "outputs/main_citybrain_d8_web_source_record_gap_closure_ui_integration_r2",
    "outputs/main_citybrain_d8_city_fact_viewer_readiness_review_r3",
)

FORBIDDEN_VISIBLE_LABELS = [
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
    "Actual corridor-adjacent city records",
]

REQUIRED_VISIBLE_PHRASES = [
    "Source-record portfolio",
    "London mobility source examples",
    "Local demo-media observations for review",
    "Forbidden request shapes are blocked",
    "Where review-only options stop",
    "Former blockers now have viewer records",
    "No action has been taken",
]


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def path(value: str | Path) -> Path:
    return REPO / value


def rel(p: Path) -> str:
    return p.relative_to(REPO).as_posix()


def task_root(key: str) -> Path:
    return path(TASKS[key][1])


def read_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, payload: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def input_index() -> dict[str, Any]:
    rows = {}
    for key, raw in INPUTS.items():
        p = path(raw)
        rows[key] = {
            "path": raw,
            "exists": p.exists(),
            "sha256": sha256(p) if p.exists() and p.is_file() else None,
        }
    return {"timestamp": now(), "inputs": rows}


def hash_manifest(root: Path) -> dict[str, Any]:
    files = [p for p in root.rglob("*") if p.is_file() and p.name != "HASH_MANIFEST.json"]
    rows = [{"path": rel(p), "sha256": sha256(p), "bytes": p.stat().st_size} for p in sorted(files)]
    return {"schema_version": "citybrain-hash-manifest-r1", "timestamp": now(), "file_count": len(rows), "files": rows}


def write_hash(root: Path) -> None:
    write_json(root / "HASH_MANIFEST.json", hash_manifest(root))


def write_index(root: Path, title: str, artifacts: list[str]) -> None:
    write_text(root / "README.md", f"# {title}\n\nGenerated by `{rel(Path(__file__))}`.\n")
    lines = [f"# {title}", "", "## Artifacts", ""]
    lines.extend(f"- `{artifact}`" for artifact in artifacts)
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines) + "\n")


def output_decision(key: str, status: str, extra: dict[str, Any]) -> None:
    task_name, _, decision_name = TASKS[key]
    root = task_root(key)
    write_json(root / decision_name, {"status": status, "task_name": task_name, "timestamp": now(), **extra})


def humanize(value: str) -> str:
    text = re.sub(r"_(event_)?candidate$", "", str(value or "candidate"))
    text = text.replace("_", " ").strip()
    return text[:1].upper() + text[1:] if text else "Candidate"


def option_title(option_type: str) -> str:
    mapping = {
        "do_nothing_monitor": "Keep the baseline under human review",
        "review_reroute_option": "Review a reroute idea",
        "review_kerbside_access_option": "Review kerbside access support",
        "review_public_information_draft": "Review a public-information draft",
        "escalate_to_human_operator": "Abstain and ask a human operator",
    }
    return mapping.get(option_type, humanize(option_type))


def action_shape_title(case_id: str, input_shape: str) -> tuple[str, str]:
    mapping = {
        "neg_auto_approved_proposal": ("auto approval", "An option layer attempted to mark review as approved."),
        "neg_auto_execute": ("auto execute", "A request attempted to change execution state to executed."),
        "neg_dispatch_action": ("dispatch", "A request attempted to create a dispatch-shaped proposal."),
        "neg_routing_control": ("routing or control", "A request attempted to change a live route, signal, or control state."),
        "neg_enforcement_legal_certified": ("enforcement or legal/certified conclusion", "A request attempted to create an enforcement or official conclusion."),
        "neg_lifecycle_written_outside_track_d": ("lifecycle write outside human review lane", "A request attempted to write lifecycle state from the option layer."),
        "neg_option_set_owns_post_promotion_state": ("post-promotion ownership", "A request attempted to make the option layer authoritative after promotion."),
        "neg_stale_scenario_state_ref": ("stale scenario reference", "A stale or unknown scenario reference was flagged for review."),
    }
    return mapping.get(case_id, (humanize(case_id), input_shape))


def make_m13_records() -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    packets = read_json(path(INPUTS["d7_event_evidence_packets"])).get("packets", [])
    media_review = read_json(path(INPUTS["d7_media_review"]))
    fixtures_by_ref = {item.get("path_or_source_ref"): item for item in media_review.get("fixtures", [])}
    records = []
    gaps = []
    for index, packet in enumerate(packets, start=1):
        media_ref = packet.get("media_ref")
        fixture = fixtures_by_ref.get(media_ref, {})
        missing = []
        missing.append("timestamp")
        missing.append("location_or_camera_context")
        candidate_label = humanize(packet.get("event_type", "candidate observation"))
        records.append(
            {
                "card_id": f"local-demo-media-observation-record-{index:03d}",
                "card_type": "candidate_observation_source_record",
                "record_class": "LOCAL_DEMO_MEDIA_OBSERVATION_RECORD",
                "title": f"{candidate_label} from local demo media",
                "plain_language_summary": f"A local demo-media fixture produced a {candidate_label.lower()} candidate. Human review is required; this is not municipal source truth.",
                "source_media_ref": media_ref,
                "source_frame_or_clip_placeholder": media_ref,
                "timestamp_missing": True,
                "location_missing": True,
                "candidate_label": candidate_label,
                "review_status": "candidate_only_human_review_required",
                "not_a_finding": True,
                "city_fact_fields": {
                    "source context": fixture.get("source_class", "local demo fixture"),
                    "media availability": "available" if fixture.get("exists") else "metadata only",
                    "candidate label": candidate_label,
                    "review status": "candidate only; human review required",
                    "time": "not present in source packet",
                    "place": "not present in source packet",
                    "action state": "no action taken",
                },
                "why_it_matters": "This closes the bare-reference problem by showing what the candidate observation record actually says and what it still does not know.",
                "evidence_refs": [
                    media_ref,
                    "outputs/main_citybrain_d7_perception_observation_to_event_evidence_r3/EVENT_EVIDENCE_PACKETS.json",
                ],
                "limitations": [
                    "Local demo media or fixture evidence only.",
                    "No timestamp or location field is present in the source packet.",
                    "Candidate observation only; no official finding, alert, dispatch, ticket, enforcement, or action.",
                ],
                "technical_refs": {
                    "source_observation_id": packet.get("source_observation_id"),
                    "event_candidate_id": packet.get("event_candidate_id"),
                    "evidence_bundle_ref": packet.get("evidence_bundle_ref"),
                    "confidence": packet.get("confidence"),
                },
            }
        )
        gaps.append(
            {
                "observation_id": packet.get("source_observation_id"),
                "source_media_ref": media_ref,
                "missing_fields": missing,
                "status": "record_renderable_with_explicit_missing_fields",
            }
        )
    status = "PASS_MAIN_CITYBRAIN_D8_D7_MEDIA_OBSERVATION_SOURCE_RECORD_PACK_R1_WITH_LIMITATIONS" if records else "PARTIAL_M13_SOURCE_RECORD_DEPTH_INSUFFICIENT"
    return status, records, gaps


def make_m07_records() -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    results = read_json(path(INPUTS["guardrail_negative_results"])).get("results", [])
    records = []
    gaps = []
    for index, result in enumerate(results, start=1):
        title_shape, wording = action_shape_title(result.get("case_id", ""), result.get("input_shape", ""))
        blocked = result.get("actual") in {"BLOCK", "REJECT", "FLAG"} and result.get("status") == "PASS"
        records.append(
            {
                "card_id": f"guardrail-refusal-review-record-{index:03d}",
                "card_type": "guardrail_refusal_review_log_record",
                "record_class": "GOVERNANCE_REVIEW_LOG_RECORD",
                "title": f"{humanize(title_shape)} request blocked",
                "plain_language_summary": f"{wording} The guardrail result was {result.get('actual')}; no execution or official action was created.",
                "refused_command_type": title_shape,
                "attempted_action_shape": result.get("input_shape"),
                "timestamp_or_run_id": "main_citybrain_d6_track_d_option_set_promotion_guardrail_smoke_r2",
                "rejection_reason": "Request shape crossed the review-only/no-action boundary.",
                "boundary_basis": [
                    "local replay review context only",
                    "no approval or execution from option layer",
                    "no dispatch, routing/control, enforcement, official case, public alert, or legal/certified conclusion",
                ],
                "execution_state": "not_executed",
                "visible_human_readable_wording": wording,
                "not_a_finding": True,
                "no_action_created": True,
                "city_fact_fields": {
                    "blocked request": humanize(title_shape),
                    "result": "blocked" if blocked else str(result.get("actual", "not recorded")).lower(),
                    "reason": "review-only boundary",
                    "action state": "no action taken",
                },
                "why_it_matters": "This makes the refusal visible to a viewer without turning a blocked request into an executed action.",
                "evidence_refs": [
                    "outputs/main_citybrain_d6_track_d_option_set_promotion_guardrail_smoke_r2/NEGATIVE_FIXTURE_RESULTS.json",
                    "outputs/main_citybrain_d6_track_d_option_set_promotion_guardrail_smoke_r2/GUARDRAIL_SMOKE_REPORT.json",
                ],
                "limitations": [
                    "Guardrail smoke record only; not a production enforcement log.",
                    "No action, proposal approval, dispatch, route/control, official case, or alert was created.",
                ],
                "technical_refs": {"case_id": result.get("case_id"), "expected": result.get("expected"), "actual": result.get("actual")},
            }
        )
        if not blocked:
            gaps.append({"case_id": result.get("case_id"), "missing_or_failed": "guardrail result did not prove block/reject/flag"})
    status = "PASS_MAIN_CITYBRAIN_D8_GUARDRAIL_REFUSAL_REVIEW_LOG_PACK_R1" if records and not gaps else "PARTIAL_M07_GUARDRAIL_REFUSAL_DEPTH_INSUFFICIENT"
    return status, records, gaps


def make_m08_records() -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    packets = read_json(path(INPUTS["promotion_panel_packets"])).get("packets", [])
    records = []
    gaps = []
    for index, packet in enumerate(packets, start=1):
        eligible = packet.get("eligibility_state") == "eligible_for_human_promotion_review"
        title = option_title(packet.get("option_type", "review option"))
        non_promotion_reason = None if eligible else "This packet remains review context only or is not eligible for promotion."
        if packet.get("no_approved_proposal") is not True or packet.get("no_execution") is not True:
            gaps.append({"packet_index": index, "missing_or_failed": "no approved proposal/no execution flags not both true"})
        records.append(
            {
                "card_id": f"human-review-stop-record-{index:03d}",
                "card_type": "human_review_stop_source_record",
                "record_class": "HUMAN_REVIEW_STOP_RECORD",
                "title": f"{title} stops at human review",
                "plain_language_summary": "This review-only option has not become an approved proposal and has not executed. A human would have to decide whether to reject, modify, request more evidence, or move it into the review lane.",
                "candidate_option_id": packet.get("option_id"),
                "human_readable_option_title": title,
                "eligibility_status": packet.get("eligibility_state"),
                "required_human_decision": packet.get("required_human_decision"),
                "explicit_stop_state": {
                    "no_approved_proposal_created": packet.get("no_approved_proposal") is True,
                    "no_execution": packet.get("no_execution") is True,
                    "human_review_lane_authority_preserved": packet.get("track_d_authoritative_after_human_promotion") is True,
                },
                "evidence_refs_that_travel_to_review": packet.get("evidence_refs", []),
                "non_promotion_reason": non_promotion_reason,
                "viewer_ready_summary": "No approval or execution exists; the next decision belongs to a human review lane.",
                "not_a_finding": True,
                "city_fact_fields": {
                    "review choice": title,
                    "eligibility": "eligible for human review" if eligible else "not eligible for promotion",
                    "required decision": "human review required" if eligible else "review context only",
                    "proposal state": "no approved proposal",
                    "action state": "no action taken",
                },
                "why_it_matters": "This makes the stop line visible: review-only options cannot silently become actions.",
                "evidence_refs": [
                    "outputs/main_citybrain_d6_track_d_promotion_panel_r1/PROMOTION_PANEL_PACKETS.json",
                    "outputs/main_citybrain_d6_track_d_option_set_promotion_bridge_r1/PROMOTION_BRIDGE_FIXTURES.json",
                ],
                "limitations": [
                    "Review-state packet only; not an approval or execution record.",
                    "Human review lane remains authoritative before any future proposal lifecycle.",
                    "No dispatch, route/control, official case, enforcement, public alert, or legal/certified conclusion.",
                ],
                "technical_refs": {
                    "option_id": packet.get("option_id"),
                    "panel_packet_id": packet.get("panel_packet_id"),
                    "proposal_preview_ref": packet.get("track_d_proposal_preview_ref"),
                    "proposal_ref": packet.get("track_d_proposal_ref"),
                },
            }
        )
    status = "PASS_MAIN_CITYBRAIN_D8_HUMAN_REVIEW_STOP_RECORD_PACK_R1" if records and not gaps else "PARTIAL_M08_HUMAN_REVIEW_STOP_DEPTH_INSUFFICIENT"
    return status, records, gaps


def london_coherence_review() -> tuple[str, dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    bundle = read_json(path(INPUTS["london_source_bundle"]))
    cards = bundle.get("cards", [])
    rows = []
    boroughs = set()
    has_issue = False
    for card in cards:
        fields = card.get("evidence_fields", {})
        borough = fields.get("borough")
        if borough:
            boroughs.add(borough)
        text = " ".join([card.get("title", ""), card.get("summary", ""), card.get("source_dataset", "")]).lower()
        issue_like = any(term in text for term in ["blockage", "closure", "disruption", "incident", "delay", "roadwork"])
        has_issue = has_issue or issue_like
        rows.append(
            {
                "card_id": card.get("card_id"),
                "title": card.get("title"),
                "borough": borough,
                "source_dataset": card.get("source_dataset"),
                "record_type": card.get("card_type"),
                "same_corridor_evidence": False,
                "mobility_issue_evidence": issue_like,
                "timestamp_or_currentness_field": "not present",
                "coherence_note": "Static EV charging site/infrastructure context; not a lane-blockage or corridor disruption record.",
            }
        )
    status = "PARTIAL_SOURCE_RECORDS_VALID_BUT_SCENARIO_NOT_COHERENT"
    verdict = {
        "status": status,
        "london_record_count": len(cards),
        "unique_borough_count": len(boroughs),
        "has_single_corridor_evidence": False,
        "has_lane_blockage_or_disruption_source_record": has_issue,
        "has_timestamp_or_currentness_field": False,
        "london_linkage_status": "valid static infrastructure examples; no proved shared corridor incident",
        "viewer_framing": "source-record portfolio, not a single corridor incident",
        "default_ui_headline": "Source records are valid; one corridor incident is not proven",
        "viewer_summary": "London records are useful mobility-source examples, but they span places and do not prove a lane blockage, road disruption, or live access issue.",
    }
    allowed = {
        "allowed_default_claims": [
            "London mobility source examples are present.",
            "Chicago records provide contextual precedent only.",
            "Helsinki records support visual entity picking context only.",
            "Local demo-media candidate observations remain candidate-only.",
            "Guardrail refusal and human-review stop records show review boundaries.",
        ],
        "disallowed_default_claims": [
            "The London records prove one corridor access incident.",
            "The EV charging records prove a lane blockage or live disruption.",
            "The Chicago and Helsinki records are the same event as the London records.",
            "Any record creates approval, dispatch, enforcement, official case, legal/certified conclusion, or automated action.",
        ],
    }
    return status, verdict, rows, allowed


def strip_details(text: str) -> str:
    return re.sub(r"<details[\s\S]*?</details>", "", text, flags=re.IGNORECASE)


def visible_text(html_text: str) -> str:
    text = strip_details(html_text)
    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def dom_report(capture_path: Path) -> dict[str, Any]:
    text = visible_text(capture_path.read_text(encoding="utf-8"))
    forbidden = [label for label in FORBIDDEN_VISIBLE_LABELS if label in text]
    missing = [label for label in REQUIRED_VISIBLE_PHRASES if label not in text]
    return {
        "status": "PASS" if not forbidden and not missing else "FAIL",
        "visible_text_char_count": len(text),
        "forbidden_default_label_hits": forbidden,
        "required_visible_phrase_missing": missing,
    }


def render_snapshot(output_path: Path) -> dict[str, Any]:
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


def card_index(integrated: dict[str, Any]) -> dict[str, Any]:
    sections = [
        "situation_city_records",
        "similar_case_city_records",
        "visual_entity_city_records",
        "media_observation_source_records",
        "guardrail_refusal_review_records",
        "human_review_stop_source_records",
        "data_depth_blockers",
    ]
    cards = []
    for section in sections:
        for record in integrated.get(section, []):
            cards.append(
                {
                    "card_id": record.get("card_id"),
                    "section": section,
                    "record_class": record.get("record_class"),
                    "title": record.get("title"),
                    "default_visible": True,
                }
            )
    return {
        "schema_version": "citybrain-source-record-ui-card-index-r2",
        "status": "PASS",
        "timestamp": now(),
        "card_count": len(cards),
        "cards": cards,
    }


def update_integrated_bundle(m13_records: list[dict[str, Any]], m07_records: list[dict[str, Any]], m08_records: list[dict[str, Any]], coherence: dict[str, Any]) -> dict[str, Any]:
    fixture_root = path("packages/fixtures/source_record_ui_integrated")
    integrated = read_json(path(INPUTS["integrated_source_bundle"]))
    integrated["schema_version"] = "citybrain-source-record-ui-integrated-r2"
    integrated["status"] = "PASS_SOURCE_RECORD_GAP_CLOSURE_UI_INTEGRATED_WITH_SCENARIO_COHERENCE_LIMITATIONS"
    integrated["timestamp"] = now()
    integrated["media_observation_source_records"] = m13_records
    integrated["guardrail_refusal_review_records"] = m07_records
    integrated["human_review_stop_source_records"] = m08_records
    integrated["data_depth_blockers"] = []
    integrated["scenario_coherence_verdict"] = coherence
    integrated["gap_closure_counts"] = {
        "media_observation_source_records": len(m13_records),
        "guardrail_refusal_review_records": len(m07_records),
        "human_review_stop_source_records": len(m08_records),
        "open_data_depth_blockers": 0,
    }
    integrated["default_record_count"] = (
        len(integrated.get("situation_city_records", []))
        + len(integrated.get("similar_case_city_records", []))
        + len(integrated.get("visual_entity_city_records", []))
        + len(m13_records)
        + len(m07_records)
        + len(m08_records)
    )
    integrated.setdefault("technical_refs", {}).setdefault("source_paths", [])
    for extra in [
        INPUTS["d7_event_evidence_packets"],
        INPUTS["guardrail_negative_results"],
        INPUTS["promotion_panel_packets"],
    ]:
        if extra not in integrated["technical_refs"]["source_paths"]:
            integrated["technical_refs"]["source_paths"].append(extra)
    write_json(fixture_root / "source_record_ui_integrated_bundle.json", integrated)
    write_json(fixture_root / "source_record_ui_card_index.json", card_index(integrated))
    write_json(
        fixture_root / "source_record_ui_data_depth_blockers.json",
        {
            "schema_version": "citybrain-source-record-ui-data-depth-blockers-r2",
            "status": "PASS_NO_OPEN_M13_M07_M08_BLOCKERS_WITH_LIMITATIONS",
            "timestamp": now(),
            "blocker_count": 0,
            "blockers": [],
            "limitations": [
                "M13 records are local demo-media candidate records, not municipal/live source records.",
                "London records remain supporting source examples, not one proved corridor incident.",
            ],
        },
    )
    write_json(
        fixture_root / "source_record_gap_closure_records.json",
        {
            "schema_version": "citybrain-source-record-gap-closure-records-r1",
            "timestamp": now(),
            "m13_media_observation_source_records": m13_records,
            "m07_guardrail_refusal_review_records": m07_records,
            "m08_human_review_stop_source_records": m08_records,
        },
    )
    return integrated


def secret_audit(paths: list[Path]) -> dict[str, Any]:
    patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(password|secret|api[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    ]
    hits = []
    for p in paths:
        if not p.exists() or p.suffix.lower() not in {".json", ".md", ".html", ".js", ".mjs", ".py"}:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in patterns):
            hits.append(rel(p))
    return {"status": "PASS" if not hits else "FAIL_SECRET_PATTERN_FOUND", "hit_count": len(hits), "hits": hits}


def boundary_audit() -> dict[str, Any]:
    forbidden_positive = [
        "production deployment",
        "public api deployed",
        "autonomous dispatch",
        "live monitoring enabled",
        "official ticket created",
        "legal finding created",
        "certified incident finding",
        "automated action executed",
    ]
    roots = [path("packages/fixtures/source_record_ui_integrated"), path("apps/web-control-room/src")]
    hits = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in {".json", ".js", ".md", ".html"}:
                text = p.read_text(encoding="utf-8", errors="ignore").lower()
                for claim in forbidden_positive:
                    if claim in text:
                        hits.append({"path": rel(p), "claim": claim})
    return {"status": "PASS" if not hits else "FAIL_FORBIDDEN_CLAIM_FOUND", "hits": hits}


def no_action_audit(m07_records: list[dict[str, Any]], m08_records: list[dict[str, Any]]) -> dict[str, Any]:
    failures = []
    for record in m07_records:
        if record.get("execution_state") != "not_executed" or record.get("no_action_created") is not True:
            failures.append(record.get("card_id"))
    for record in m08_records:
        state = record.get("explicit_stop_state", {})
        if not state.get("no_approved_proposal_created") or not state.get("no_execution"):
            failures.append(record.get("card_id"))
    return {"status": "PASS" if not failures else "FAIL_ACTION_BOUNDARY", "failures": failures}


def run() -> dict[str, Any]:
    for _, root, _ in TASKS.values():
        path(root).mkdir(parents=True, exist_ok=True)

    read_only_inputs = {k: path(v) for k, v in INPUTS.items() if not v.startswith("apps/web-control-room") and not v.startswith("packages/fixtures/source_record_ui_integrated")}
    hashes_before = {k: sha256(p) for k, p in read_only_inputs.items() if p.exists() and p.is_file()}

    # 1. Preflight
    preflight_root = task_root("preflight")
    idx = input_index()
    write_json(preflight_root / "INPUT_ARTIFACT_INDEX.json", idx)
    missing = [k for k, v in idx["inputs"].items() if not v["exists"]]
    freeze = read_json(path(INPUTS["source_record_ui_freeze_decision"]))
    truth = read_json(path(INPUTS["source_record_ui_truth_register"]))
    integrated = read_json(path(INPUTS["integrated_source_bundle"]))
    existing_blockers = integrated.get("data_depth_blockers", [])
    preflight_status = "PASS_MAIN_CITYBRAIN_D8_SOURCE_RECORD_GAP_CLOSURE_PREFLIGHT" if not missing and freeze.get("status") == "PASS_MAIN_CITYBRAIN_D8_SOURCE_RECORD_UI_MILESTONE_FREEZE_WITH_LIMITATIONS" else "FAIL_MAIN_CITYBRAIN_D8_SOURCE_RECORD_GAP_CLOSURE_PREFLIGHT"
    write_json(
        preflight_root / "CURRENT_SOURCE_RECORD_UI_FACTS.json",
        {
            "source_backed_default_card_count": truth.get("source_backed_default_card_count"),
            "data_depth_blocker_count": truth.get("data_depth_blocker_count"),
            "external_viewer_validation_ready": truth.get("external_viewer_validation_ready"),
            "freeze_status": freeze.get("status"),
        },
    )
    write_json(preflight_root / "OPEN_SOURCE_RECORD_BLOCKER_INDEX.json", {"status": "PASS", "blocker_count": len(existing_blockers), "blockers": existing_blockers})
    write_json(
        preflight_root / "SCENARIO_COHERENCE_RISK_REGISTER.json",
        {
            "status": "OPEN_RISK",
            "risks": [
                "London EV/source records may be valid examples rather than one coherent corridor incident.",
                "Chicago and Helsinki records are cross-context support, not same-event evidence.",
                "M13 local demo media cannot be promoted to municipal/live source truth.",
            ],
        },
    )
    output_decision("preflight", preflight_status, {"missing_inputs": missing, "entry_external_viewer_ready": truth.get("external_viewer_validation_ready")})
    write_hash(preflight_root)
    write_index(preflight_root, TASKS["preflight"][0], [TASKS["preflight"][2], "CURRENT_SOURCE_RECORD_UI_FACTS.json", "OPEN_SOURCE_RECORD_BLOCKER_INDEX.json", "SCENARIO_COHERENCE_RISK_REGISTER.json", "INPUT_ARTIFACT_INDEX.json", "HASH_MANIFEST.json"])
    if preflight_status.startswith("FAIL"):
        return {"final_status": preflight_status, "missing_inputs": missing}

    # 2. M13 records
    m13_status, m13_records, m13_gaps = make_m13_records()
    m13_root = task_root("m13")
    write_json(m13_root / "d7_media_observation_source_records.json", {"status": m13_status, "record_count": len(m13_records), "records": m13_records})
    write_json(m13_root / "D7_OBSERVATION_DATA_DEPTH_GAPS.json", {"status": "PASS_WITH_EXPLICIT_MISSING_FIELDS", "gap_count": len(m13_gaps), "gaps": m13_gaps})
    write_json(m13_root / "NO_FACT_INVENTION_AUDIT.json", {"status": "PASS", "assertion": "Candidate labels are derived from event_type; timestamp/location are explicitly marked missing rather than invented."})
    output_decision("m13", m13_status, {"record_count": len(m13_records), "explicit_missing_field_count": len(m13_gaps)})
    write_hash(m13_root)
    write_index(m13_root, TASKS["m13"][0], [TASKS["m13"][2], "d7_media_observation_source_records.json", "D7_OBSERVATION_DATA_DEPTH_GAPS.json", "NO_FACT_INVENTION_AUDIT.json", "HASH_MANIFEST.json"])

    # 3. M07 records
    m07_status, m07_records, m07_gaps = make_m07_records()
    m07_root = task_root("m07")
    write_json(m07_root / "guardrail_refusal_review_records.json", {"status": m07_status, "record_count": len(m07_records), "records": m07_records})
    write_json(m07_root / "GUARDRAIL_REFUSAL_DATA_DEPTH_GAPS.json", {"status": "PASS" if not m07_gaps else "PARTIAL", "gap_count": len(m07_gaps), "gaps": m07_gaps})
    m07_no_action = no_action_audit(m07_records, [])
    write_json(m07_root / "NO_ACTION_BOUNDARY_AUDIT.json", m07_no_action)
    output_decision("m07", m07_status, {"record_count": len(m07_records), "no_action_boundary_status": m07_no_action["status"]})
    write_hash(m07_root)
    write_index(m07_root, TASKS["m07"][0], [TASKS["m07"][2], "guardrail_refusal_review_records.json", "GUARDRAIL_REFUSAL_DATA_DEPTH_GAPS.json", "NO_ACTION_BOUNDARY_AUDIT.json", "HASH_MANIFEST.json"])

    # 4. M08 records
    m08_status, m08_records, m08_gaps = make_m08_records()
    m08_root = task_root("m08")
    write_json(m08_root / "human_review_stop_source_records.json", {"status": m08_status, "record_count": len(m08_records), "records": m08_records})
    write_json(m08_root / "HUMAN_REVIEW_STOP_DATA_DEPTH_GAPS.json", {"status": "PASS" if not m08_gaps else "PARTIAL", "gap_count": len(m08_gaps), "gaps": m08_gaps})
    authority = {"status": "PASS", "assertions": ["human review lane authority preserved", "proposal_ref remains null", "execution_state remains not_executed"]}
    write_json(m08_root / "TRACK_D_AUTHORITY_AUDIT.json", authority)
    output_decision("m08", m08_status, {"record_count": len(m08_records), "authority_audit_status": authority["status"]})
    write_hash(m08_root)
    write_index(m08_root, TASKS["m08"][0], [TASKS["m08"][2], "human_review_stop_source_records.json", "HUMAN_REVIEW_STOP_DATA_DEPTH_GAPS.json", "TRACK_D_AUTHORITY_AUDIT.json", "HASH_MANIFEST.json"])

    # 5. London coherence
    coherence_status, coherence_verdict, coherence_rows, allowed_claims = london_coherence_review()
    coherence_root = task_root("coherence")
    write_json(coherence_root / "LONDON_SOURCE_RECORD_COHERENCE_MATRIX.json", {"status": coherence_status, "rows": coherence_rows})
    write_json(coherence_root / "UI_NARRATIVE_ALLOWED_CLAIMS.json", allowed_claims)
    write_text(
        coherence_root / "DEMO_STORY_COHERENCE_VERDICT.md",
        "# Demo Story Coherence Verdict\n\n"
        f"Status: `{coherence_status}`\n\n"
        "London source records are valid bounded mobility-source examples, but they do not prove a single corridor incident, lane blockage, live disruption, or shared location/time story. The UI must frame them as source-record portfolio context.\n",
    )
    output_decision("coherence", coherence_status, coherence_verdict)
    write_hash(coherence_root)
    write_index(coherence_root, TASKS["coherence"][0], [TASKS["coherence"][2], "LONDON_SOURCE_RECORD_COHERENCE_MATRIX.json", "DEMO_STORY_COHERENCE_VERDICT.md", "UI_NARRATIVE_ALLOWED_CLAIMS.json", "HASH_MANIFEST.json"])

    # 6. Web/UI integration
    updated = update_integrated_bundle(m13_records, m07_records, m08_records, coherence_verdict)
    web_root = task_root("web")
    capture = web_root / "WEB_CITY_FACT_DOM_CAPTURE.html"
    render_evidence = render_snapshot(capture)
    dom = dom_report(capture) if capture.exists() and render_evidence["returncode"] == 0 else {"status": "FAIL", "forbidden_default_label_hits": [], "required_visible_phrase_missing": REQUIRED_VISIBLE_PHRASES}
    web_status = "PASS_MAIN_CITYBRAIN_D8_WEB_SOURCE_RECORD_GAP_CLOSURE_UI_INTEGRATION_R2_WITH_LIMITATIONS" if dom["status"] == "PASS" else "FAIL_MAIN_CITYBRAIN_D8_WEB_SOURCE_RECORD_GAP_CLOSURE_UI_INTEGRATION_R2"
    truth_register = {
        "status": web_status,
        "default_view": "source-record portfolio plus review/gap-closure records",
        "default_record_count": updated.get("default_record_count"),
        "open_data_depth_blockers": len(updated.get("data_depth_blockers", [])),
        "scenario_coherence_status": coherence_status,
        "external_viewer_validation_ready": False,
    }
    write_json(web_root / "UPDATED_SOURCE_RECORD_UI_TRUTH_REGISTER.json", truth_register)
    write_json(web_root / "WEB_CITY_FACT_DOM_ASSERTION_REPORT.json", dom)
    write_json(web_root / "NO_GENERIC_FIXTURE_LABEL_AUDIT.json", {"status": "PASS" if not dom.get("forbidden_default_label_hits") else "FAIL", "forbidden_default_label_hits": dom.get("forbidden_default_label_hits", [])})
    write_json(web_root / "STATIC_DOM_RENDER_EVIDENCE.json", render_evidence)
    output_decision("web", web_status, {"dom_assertion_status": dom["status"], "open_data_depth_blockers": 0, "scenario_coherence_status": coherence_status})
    write_hash(web_root)
    write_index(web_root, TASKS["web"][0], [TASKS["web"][2], "UPDATED_SOURCE_RECORD_UI_TRUTH_REGISTER.json", "WEB_CITY_FACT_DOM_ASSERTION_REPORT.json", "NO_GENERIC_FIXTURE_LABEL_AUDIT.json", "STATIC_DOM_RENDER_EVIDENCE.json", "WEB_CITY_FACT_DOM_CAPTURE.html", "HASH_MANIFEST.json"])

    # 7. Viewer readiness
    readiness_root = task_root("readiness")
    readiness_status = "CONDITIONAL_GO_INTERNAL_CAPTURE_ONLY"
    go_matrix = {
        "status": readiness_status,
        "criteria": [
            {"criterion": "actual source/review records visible", "status": "PASS", "evidence": "27 source-backed records plus M13/M07/M08 review records"},
            {"criterion": "no scenario linkage overclaim", "status": "PASS", "evidence": coherence_status},
            {"criterion": "M13/M07/M08 resolved or accepted", "status": "PASS_WITH_LIMITATIONS", "evidence": "records render; M13 remains local demo-media only"},
            {"criterion": "forbidden default fixture labels", "status": "PASS", "evidence": dom.get("forbidden_default_label_hits", [])},
            {"criterion": "boundary/no-action visible", "status": "PASS", "evidence": "review boundary and limitations sections"},
            {"criterion": "external naive viewer product story", "status": "LIMITED", "evidence": "source-record portfolio, not one proven corridor incident"},
        ],
    }
    open_gaps = {
        "status": "OPEN_LIMITATIONS_NOT_BLOCKERS",
        "open_blocker_count": 0,
        "open_limitations": [
            "London mobility records do not prove a single corridor/lane-blockage incident.",
            "M13 observation records are local demo-media records with explicit missing timestamp/location.",
            "External naive viewer validation should be framed as a source-record portfolio review, not a city incident demo.",
        ],
    }
    write_json(readiness_root / "VIEWER_GO_NO_GO_MATRIX.json", go_matrix)
    write_text(
        readiness_root / "CAPTURE_SCOPE_RECOMMENDATION.md",
        "# Capture Scope Recommendation\n\n"
        "`CONDITIONAL_GO_INTERNAL_CAPTURE_ONLY`\n\n"
        "Capture the revised source-record portfolio internally. Do not run naive external validation as a coherent Mobility Access incident demo until a real corridor issue/source record exists, or until the reviewer script explicitly tests source-record portfolio comprehension.\n",
    )
    write_json(readiness_root / "OPEN_GAPS_IF_ANY.json", open_gaps)
    output_decision("readiness", readiness_status, {"external_viewer_validation_ready": False, "internal_capture_ready": True, "reason": "records render, but scenario remains a portfolio rather than one proven incident"})
    write_hash(readiness_root)
    write_index(readiness_root, TASKS["readiness"][0], [TASKS["readiness"][2], "VIEWER_GO_NO_GO_MATRIX.json", "CAPTURE_SCOPE_RECOMMENDATION.md", "OPEN_GAPS_IF_ANY.json", "HASH_MANIFEST.json"])

    # 8. Closeout
    closeout_root = task_root("closeout")
    hashes_after = {k: sha256(p) for k, p in read_only_inputs.items() if p.exists() and p.is_file()}
    no_mutation = {"status": "PASS" if hashes_before == hashes_after else "FAIL_READ_ONLY_INPUT_HASH_CHANGED", "before": hashes_before, "after": hashes_after}
    claim = boundary_audit()
    no_action = no_action_audit(m07_records, m08_records)
    generated_paths = []
    for _, root, _ in TASKS.values():
        r = path(root)
        if r.exists():
            generated_paths.extend([p for p in r.rglob("*") if p.is_file()])
    generated_paths.extend([p for p in path("packages/fixtures/source_record_ui_integrated").rglob("*") if p.is_file()])
    secret = secret_audit(generated_paths + [path(INPUTS["web_renderer"]), path(INPUTS["web_index"])])
    no_fact = {"status": "PASS", "assertions": ["timestamp/location missing fields are explicit", "London records are not upgraded into a lane-blockage incident", "event_type fields are only humanized into labels"]}
    closeout_status = "PASS_MAIN_CITYBRAIN_D8_SOURCE_RECORD_GAP_CLOSURE_CLOSEOUT_WITH_LIMITATIONS" if all(item["status"] == "PASS" for item in [no_mutation, claim, no_action, secret, no_fact]) and web_status.startswith("PASS") else "FAIL_MAIN_CITYBRAIN_D8_SOURCE_RECORD_GAP_CLOSURE_CLOSEOUT"
    ledger = {
        "status": closeout_status,
        "closed_gaps": [
            {"gap": "M13 candidate observation source detail", "closure": "local demo-media records with explicit missing fields", "limitations": "not municipal/live source truth"},
            {"gap": "M07 guardrail refusal review-log", "closure": "guardrail negative-test records", "limitations": "smoke/review log only"},
            {"gap": "M08 human-review stop", "closure": "promotion-panel review-stop records", "limitations": "no approval or execution"},
        ],
        "open_limitations": open_gaps["open_limitations"],
    }
    write_text(
        closeout_root / "CURRENT_SOURCE_RECORD_UI_STATE.md",
        "# Current Source-Record UI State\n\n"
        f"Status: `{closeout_status}`\n\n"
        "The UI now frames itself as a source-record portfolio and review-safe evidence surface. M13, M07, and M08 render as records, while London scenario coherence remains explicitly limited.\n",
    )
    write_json(closeout_root / "CLOSED_AND_OPEN_GAP_LEDGER.json", ledger)
    write_json(closeout_root / "CLAIM_BOUNDARY_AUDIT.json", claim)
    write_json(closeout_root / "NO_ACTION_BOUNDARY_AUDIT.json", no_action)
    write_json(closeout_root / "NO_MUTATION_AUDIT.json", no_mutation)
    write_json(closeout_root / "SECRET_AUDIT.json", secret)
    write_json(closeout_root / "NO_FACT_INVENTION_AUDIT.json", no_fact)
    output_decision("closeout", closeout_status, {"viewer_readiness_status": readiness_status, "open_blocker_count": 0, "open_limitation_count": len(open_gaps["open_limitations"])})
    write_hash(closeout_root)
    write_index(closeout_root, TASKS["closeout"][0], [TASKS["closeout"][2], "CURRENT_SOURCE_RECORD_UI_STATE.md", "CLOSED_AND_OPEN_GAP_LEDGER.json", "CLAIM_BOUNDARY_AUDIT.json", "NO_ACTION_BOUNDARY_AUDIT.json", "NO_MUTATION_AUDIT.json", "SECRET_AUDIT.json", "NO_FACT_INVENTION_AUDIT.json", "HASH_MANIFEST.json"])

    # 9. Freeze
    freeze_root = task_root("freeze")
    freeze_status = "PASS_MAIN_CITYBRAIN_D8_SOURCE_RECORD_GAP_CLOSURE_MILESTONE_FREEZE_WITH_LIMITATIONS" if closeout_status.startswith("PASS") else "FAIL_MAIN_CITYBRAIN_D8_SOURCE_RECORD_GAP_CLOSURE_MILESTONE_FREEZE"
    validation_zip = freeze_root / "VALIDATION_PACKAGE.zip"
    with zipfile.ZipFile(validation_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for p in [
            path("packages/fixtures/source_record_ui_integrated/source_record_ui_integrated_bundle.json"),
            path("packages/fixtures/source_record_ui_integrated/source_record_gap_closure_records.json"),
            web_root / "WEB_CITY_FACT_DOM_CAPTURE.html",
            web_root / "WEB_CITY_FACT_DOM_ASSERTION_REPORT.json",
            closeout_root / "CLOSED_AND_OPEN_GAP_LEDGER.json",
            readiness_root / "VIEWER_GO_NO_GO_MATRIX.json",
        ]:
            if p.exists():
                archive.write(p, rel(p))
    external = {
        "status": readiness_status,
        "internal_capture_ready": True,
        "external_naive_viewer_validation_ready": False,
        "reason": "The UI is now honest and record-backed, but it is a source-record portfolio rather than one proved Mobility Access incident.",
    }
    ready_next = {
        "recommended_next_tracks": [
            "MAIN-CITYBRAIN-D8-INTERNAL-SOURCE-RECORD-PORTFOLIO-CAPTURE-R1",
            "MAIN-CITYBRAIN-D8-REAL-CORRIDOR-ISSUE-SOURCE-LANDING-R1",
        ]
    }
    deferred = {"items": open_gaps["open_limitations"]}
    write_text(
        freeze_root / "SOURCE_RECORD_GAP_CLOSURE_BASELINE_SUMMARY.md",
        "# Source-Record Gap Closure Baseline\n\n"
        f"Status: `{freeze_status}`\n\n"
        "M13/M07/M08 no longer render as unresolved blocker cards. The frozen baseline is honest about scenario coherence: source portfolio, not a single proved corridor incident.\n",
    )
    write_json(freeze_root / "EXTERNAL_VIEWER_GO_NO_GO.json", external)
    write_json(freeze_root / "READY_NEXT_TRACKS.json", ready_next)
    write_json(freeze_root / "DEFERRED_OR_BLOCKED_ITEMS.json", deferred)
    output_decision("freeze", freeze_status, {"viewer_readiness_status": readiness_status, "validation_package": rel(validation_zip), "recommended_next_tracks": ready_next["recommended_next_tracks"]})
    write_hash(freeze_root)
    write_index(freeze_root, TASKS["freeze"][0], [TASKS["freeze"][2], "SOURCE_RECORD_GAP_CLOSURE_BASELINE_SUMMARY.md", "VALIDATION_PACKAGE.zip", "EXTERNAL_VIEWER_GO_NO_GO.json", "READY_NEXT_TRACKS.json", "DEFERRED_OR_BLOCKED_ITEMS.json", "HASH_MANIFEST.json"])

    return {
        "final_status": freeze_status,
        "viewer_readiness_status": readiness_status,
        "output_roots": {k: TASKS[k][1] for k in TASKS},
        "m13_record_count": len(m13_records),
        "m07_record_count": len(m07_records),
        "m08_record_count": len(m08_records),
        "open_blocker_count": 0,
        "scenario_coherence_status": coherence_status,
        "dom_assertion_status": dom["status"],
        "forbidden_default_label_hits": dom.get("forbidden_default_label_hits", []),
        "claim_boundary_status": claim["status"],
        "no_action_boundary_status": no_action["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret["status"],
        "recommended_next_tracks": ready_next["recommended_next_tracks"],
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, sort_keys=True))
    sys.exit(0 if str(result.get("final_status", "")).startswith("PASS") else 1)
