#!/usr/bin/env python3
"""Assemble Founder Probe Review Pack R1.

This materializes the 16 founder-probe task-card references into readable
review cards and a prefilled response CSV. It prepares review material only:
no founder session, fuel, training rows, live ingestion, forecasts, official
workflow/action, or source-truth mutation are created.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_founder_probe_review_pack_assembler_r1"
PUBLICATION_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-founder-probe-review-pack-assembler-r1"
CARD_DIR = OUTPUT_ROOT / "review_cards"
PUB_CARD_DIR = PUBLICATION_ROOT / "review_cards"

PACKAGE_ID = "MAIN-CITYBRAIN-EPOCH4-FOUNDER-PROBE-REVIEW-PACK-ASSEMBLER-R1"
STATUS = "PASS_MAIN_CITYBRAIN_EPOCH4_FOUNDER_PROBE_REVIEW_PACK_ASSEMBLER_R1_WITH_LIMITATIONS"

INPUTS = {
    "founder_probe_task_card_set": ROOT / "outputs" / "main_citybrain_epoch4_founder_probe_input_kit_r2" / "FOUNDER_PROBE_TASK_CARD_SET.json",
    "founder_probe_input_kit_decision": ROOT / "outputs" / "main_citybrain_epoch4_founder_probe_input_kit_r2" / "FOUNDER_PROBE_INPUT_KIT_DECISION.json",
    "founder_probe_import_schema": ROOT / "outputs" / "main_citybrain_epoch4_founder_probe_input_kit_r2" / "FOUNDER_PROBE_IMPORT_SCHEMA.json",
    "review_packet_360_v2_by_family": ROOT / "outputs" / "main_citybrain_epoch4_review_packet_360_v2_pilot_binder_refresh_r1" / "REVIEW_PACKET_360_V2_BY_FAMILY.json",
    "review_packet_360_r1_by_family": ROOT / "outputs" / "main_citybrain_epoch4_review_packet_360_r1" / "REVIEW_PACKET_360_BY_FAMILY.json",
    "eval_corpus_r2_index": ROOT / "outputs" / "main_citybrain_epoch4_eval_corpus_expansion_r2" / "EVAL_CORPUS_R2_INDEX.json",
    "eval_cases_r2": ROOT / "outputs" / "main_citybrain_epoch4_eval_corpus_expansion_r2" / "EVAL_CASES_R2.jsonl",
    "eval_harness_case_results": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_eval_harness_execution_r1" / "CASE_RESULTS.json",
    "eval_harness_check_assertions": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_eval_harness_execution_r1" / "CHECK_ASSERTION_RESULTS.json",
    "check_v1_stress_report": ROOT / "outputs" / "main_citybrain_epoch4_cer_check_event_stress_eval_r1" / "CHECK_V1_STRESS_REPORT.json",
    "derived_fix_overlay_register": ROOT / "outputs" / "main_citybrain_epoch4_derived_fix_promotion_overlay_r1" / "DERIVED_FIX_OVERLAY_REGISTER.json",
    "derived_fix_overlay_decision": ROOT / "outputs" / "main_citybrain_epoch4_derived_fix_promotion_overlay_r1" / "DERIVED_FIX_PROMOTION_OVERLAY_DECISION.json",
    "incident_event_state_by_family": ROOT / "outputs" / "main_citybrain_epoch4_incident_plan_three_family_product_loop_r1" / "EVENT_STATE_PACKETS_BY_FAMILY.json",
    "incident_check_reports_by_family": ROOT / "outputs" / "main_citybrain_epoch4_incident_plan_three_family_product_loop_r1" / "CHECK_V1_REPORTS_BY_FAMILY.json",
    "incident_brief_packets_by_family": ROOT / "outputs" / "main_citybrain_epoch4_incident_plan_three_family_product_loop_r1" / "BRIEF_V3_PACKETS_BY_FAMILY.json",
    "incident_spatial_packets_by_family": ROOT / "outputs" / "main_citybrain_epoch4_incident_plan_three_family_product_loop_r1" / "SPATIAL_OVERLAY_PACKETS_BY_FAMILY.json",
    "event_fabric_v2_5_consumption": ROOT / "outputs" / "main_citybrain_epoch4_event_fabric_v2_5_long_history_load_r1" / "EVENT_FABRIC_V2_5_CONSUMPTION_DEPTH_REPORT.json",
    "simulation_v2_4_baseline_options": ROOT / "outputs" / "main_citybrain_epoch4_simulation_v2_4_family_sumo_option_runner_r1" / "SIMULATION_V2_4_BASELINE_OPTION_COMPARISON_REPORT.json",
    "non_sumo_option_comparison": ROOT / "outputs" / "main_citybrain_epoch4_non_sumo_domain_option_engines_r1" / "NON_SUMO_BASELINE_OPTION_COMPARISON_REPORT.json",
    "trackb_brief_v3_variants": ROOT / "outputs" / "main_citybrain_epoch4_trackb_maturity_brief_governance_r1" / "BRIEF_V3_VARIANTS.json",
}

TOP_LEVEL_FILES = [
    "FOUNDER_PROBE_REVIEW_INDEX.md",
    "FOUNDER_PROBE_REVIEW_INDEX.html",
    "FOUNDER_PROBE_REVIEW_PACK_SUMMARY.json",
    "FOUNDER_PROBE_RESPONSE_TEMPLATE_PREFILLED.csv",
    "FOUNDER_PROBE_RESPONSE_GUIDE.md",
    "FOUNDER_PROBE_ASSEMBLY_DECISION.json",
    "INPUT_RESOLUTION_REPORT.json",
    "MISSING_EVIDENCE_REPORT.json",
    "NO_FABRICATED_SESSION_GUARD.json",
    "HASH_MANIFEST.json",
]

CSV_FIELDS = [
    "task_id",
    "family",
    "scenario",
    "eval_case",
    "check_ref",
    "derived_overlays",
    "reviewer_id_or_alias",
    "reviewer_type",
    "completed_at",
    "understood_subject",
    "supports_claim",
    "should_downgrade",
    "missing_evidence",
    "brief_usefulness_1_to_5",
    "check_usefulness_1_to_5",
    "simulation_usefulness_1_to_5",
    "spatial_usefulness_1_to_5",
    "review_decision",
    "free_text_notes",
]

REVIEW_FIELDS = [
    "completed_at",
    "understood_subject",
    "supports_claim",
    "should_downgrade",
    "missing_evidence",
    "brief_usefulness_1_to_5",
    "check_usefulness_1_to_5",
    "simulation_usefulness_1_to_5",
    "spatial_usefulness_1_to_5",
    "review_decision",
    "free_text_notes",
]

FOUNDATION_CANNOT_CLAIM = [
    "No founder/operator session result is created by this assembler.",
    "No operator fuel, disposition, training row, or learned label is created.",
    "No live ingestion, production monitoring, forecast, or recommendation authority is created.",
    "No official case, ticket, dispatch, control, enforcement, legal finding, or certified finding is created.",
    "No source or canonical truth is mutated.",
]

FOUNDER_QUESTIONS = [
    "Is the subject understandable?",
    "Does the evidence support the stated claim?",
    "Should the claim be downgraded?",
    "What evidence is missing?",
    "Is the BRIEF useful?",
    "Is CHECK useful?",
    "Is simulation useful or applicable?",
    "Is spatial context useful or applicable?",
    "What should be fixed before showing this to anyone else?",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def status_of(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    return payload.get("status") or payload.get("decision_status") or payload.get("final_status")


def family_aliases(family_id: str) -> list[str]:
    aliases = [family_id]
    if family_id.endswith("_v0"):
        aliases.append(family_id[:-3])
    if family_id == "mobility_access_interruption_v0":
        aliases.append("mobility_access_interruption")
    return list(dict.fromkeys(aliases))


def first_by_family(rows: list[dict[str, Any]], family_id: str, key: str = "family_id") -> dict[str, Any]:
    aliases = set(family_aliases(family_id))
    for row in rows:
        if row.get(key) in aliases:
            return row
    return {}


def family_map_lookup(mapping: dict[str, Any], family_id: str) -> Any:
    for alias in family_aliases(family_id):
        if alias in mapping:
            return mapping[alias]
    return {}


def short_json(value: Any, max_chars: int = 900) -> str:
    text = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 20].rstrip() + "\n  ... truncated\n}"


def md_list(items: list[Any]) -> str:
    if not items:
        return "- None recorded."
    lines = []
    for item in items:
        if isinstance(item, (dict, list)):
            lines.append(f"- `{json.dumps(item, sort_keys=True, ensure_ascii=True)}`")
        else:
            lines.append(f"- {item}")
    return "\n".join(lines)


def scenario_explanation(scenario: str) -> str:
    return {
        "positive_packet_baseline": "Positive packet baseline: can a bounded local/replay packet be understood and reviewed without over-claiming truth?",
        "negative_no_data": "Negative no-data case: does the packet abstain or stay limited when evidence is absent?",
        "stale_freshness": "Freshness downgrade case: does CHECK make stale evidence visible and prevent over-claiming?",
        "contradiction_pair": "Contradiction case: does CHECK surface conflicting evidence and preserve the downgrade/abstain boundary?",
    }.get(scenario, f"Scenario under review: {scenario}")


def input_audit() -> list[dict[str, Any]]:
    rows = []
    for key, path in INPUTS.items():
        if path.suffix == ".jsonl":
            records = read_jsonl(path)
            rows.append({"key": key, "path": rel(path), "exists": path.exists(), "record_count": len(records), "status": "PASS_WITH_LIMITATIONS" if records else None})
        else:
            payload = read_json(path, {})
            rows.append({"key": key, "path": rel(path), "exists": path.exists(), "status": status_of(payload)})
    return rows


def build_sources() -> dict[str, Any]:
    task_set = read_json(INPUTS["founder_probe_task_card_set"], {})
    eval_cases = read_jsonl(INPUTS["eval_cases_r2"])
    review_v2 = read_json(INPUTS["review_packet_360_v2_by_family"], {})
    review_r1 = read_json(INPUTS["review_packet_360_r1_by_family"], {})
    overlay_register = read_json(INPUTS["derived_fix_overlay_register"], {})
    return {
        "task_set": task_set,
        "cards": task_set.get("cards", []),
        "eval_cases": {case.get("case_id"): case for case in eval_cases},
        "eval_index": read_json(INPUTS["eval_corpus_r2_index"], {}),
        "review_v2": {row.get("family_id"): row for row in review_v2.get("packets", [])},
        "review_r1": {row.get("family_id"): row for row in review_r1.get("packets", [])},
        "case_results": read_json(INPUTS["eval_harness_case_results"], {}),
        "check_assertions": read_json(INPUTS["eval_harness_check_assertions"], {}),
        "check_stress": read_json(INPUTS["check_v1_stress_report"], {}),
        "overlays": {row.get("overlay_id"): row for row in overlay_register.get("overlays", [])},
        "overlay_decision": read_json(INPUTS["derived_fix_overlay_decision"], {}),
        "event_state": read_json(INPUTS["incident_event_state_by_family"], {}).get("families", {}),
        "incident_check": read_json(INPUTS["incident_check_reports_by_family"], {}).get("families", {}),
        "incident_brief": read_json(INPUTS["incident_brief_packets_by_family"], {}).get("families", {}),
        "incident_spatial": read_json(INPUTS["incident_spatial_packets_by_family"], {}).get("families", {}),
        "event_v25_rows": read_json(INPUTS["event_fabric_v2_5_consumption"], {}).get("families", []),
        "simulation_v24_rows": read_json(INPUTS["simulation_v2_4_baseline_options"], {}).get("comparisons", []),
        "non_sumo_rows": read_json(INPUTS["non_sumo_option_comparison"], {}).get("families", []),
        "brief_variants": read_json(INPUTS["trackb_brief_v3_variants"], {}),
    }


def match_check_assertion(sources: dict[str, Any], family_id: str, scenario: str) -> dict[str, Any]:
    base_family = family_aliases(family_id)[-1]
    scenario_map = {
        "positive_packet_baseline": "packet_baseline",
        "contradiction_pair": "contradiction_guard",
    }
    case_type = scenario_map.get(scenario)
    if not case_type:
        return {}
    wanted = f"eval:{base_family}:{case_type}:r1"
    for row in sources["check_assertions"].get("results", []):
        if row.get("case_id") == wanted:
            return row
    return {}


def resolve_brief_context(sources: dict[str, Any], family_id: str, brief_refs: list[str]) -> dict[str, Any]:
    incident_brief = family_map_lookup(sources["incident_brief"], family_id)
    if incident_brief:
        return {
            "available": True,
            "source": rel(INPUTS["incident_brief_packets_by_family"]),
            "summary": incident_brief,
            "task_refs": brief_refs,
        }
    if "mobility_access_interruption" in family_aliases(family_id):
        variants = sources["brief_variants"].get("variants", {})
        if variants:
            return {
                "available": True,
                "source": rel(INPUTS["trackb_brief_v3_variants"]),
                "summary": {
                    "variant_kinds": sorted(variants.keys()),
                    "packet_id": variants.get("operator", {}).get("packet_id"),
                    "no_action_boundary": variants.get("operator", {}).get("no_action_boundary"),
                },
                "task_refs": brief_refs,
            }
    return {"available": False, "task_refs": brief_refs, "summary": {}}


def resolve_simulation_context(sources: dict[str, Any], family_id: str, eval_case: dict[str, Any]) -> dict[str, Any]:
    sim_v24 = first_by_family(sources["simulation_v24_rows"], family_id)
    non_sumo = first_by_family(sources["non_sumo_rows"], family_id)
    expected = eval_case.get("expected_simulation_handling")
    return {
        "eval_expected_handling": expected,
        "simulation_v2_4_comparison": sim_v24,
        "non_sumo_option_context": non_sumo,
        "forecast_created": bool(sim_v24.get("forecast_created") or sources.get("non_sumo_option_comparison", {}).get("forecast_created")),
        "recommendation_authority": sim_v24.get("recommendation_authority") or "none",
    }


def resolve_card(card: dict[str, Any], sources: dict[str, Any]) -> dict[str, Any]:
    packet_refs = card.get("packet_refs", {})
    family_id = card["family"]
    scenario = card["scenario"]
    eval_ref = packet_refs.get("eval_case_ref")
    check_ref = packet_refs.get("check_ref")
    eval_case = sources["eval_cases"].get(eval_ref, {})
    review_packet_v2 = family_map_lookup(sources["review_v2"], family_id)
    review_packet_r1 = family_map_lookup(sources["review_r1"], family_id)
    review_packet = review_packet_v2 or review_packet_r1
    review_sections = review_packet.get("sections", {}) if isinstance(review_packet.get("sections"), dict) else {}
    review_packet_source = "review_packet_360_v2_by_family" if review_packet_v2 else ("review_packet_360_r1_by_family" if review_packet_r1 else None)
    event_v25 = first_by_family(sources["event_v25_rows"], family_id)
    incident_event_state = family_map_lookup(sources["event_state"], family_id)
    incident_check = family_map_lookup(sources["incident_check"], family_id)
    incident_spatial = family_map_lookup(sources["incident_spatial"], family_id)
    brief_context = resolve_brief_context(sources, family_id, packet_refs.get("brief_refs", []))
    simulation_context = resolve_simulation_context(sources, family_id, eval_case)
    check_assertion = match_check_assertion(sources, family_id, scenario)
    overlay_refs = packet_refs.get("derived_overlay_refs", [])
    overlays = [sources["overlays"].get(ref, {"overlay_id": ref, "resolved": False}) for ref in overlay_refs]

    missing = []
    if not eval_case:
        missing.append(f"Eval case not found for {eval_ref}.")
    if not review_packet:
        missing.append(f"Review Packet 360 family packet not found for {family_id}; card uses eval, BRIEF, event fabric, and overlay refs instead.")
    if not brief_context.get("available"):
        missing.append(f"BRIEF context not resolved for refs {packet_refs.get('brief_refs', [])}.")
    if not event_v25 and not incident_event_state:
        missing.append(f"Event state not resolved for {family_id}.")
    if overlay_refs and any(not row.get("derived_fix_id") for row in overlays):
        missing.append("One or more derived overlay refs were not found in the overlay register.")
    if not simulation_context["simulation_v2_4_comparison"] and eval_case.get("expected_simulation_handling") != "simulation_not_applicable":
        missing.append(f"Simulation/option comparison not resolved for {family_id}.")

    cannot_claim = list(dict.fromkeys(FOUNDATION_CANNOT_CLAIM + card.get("do_not_claim_reminders", [])))
    if review_packet.get("cannot_claim"):
        cannot_claim.extend([f"Review Packet 360: {claim}" for claim in review_packet["cannot_claim"]])
    if review_sections.get("cannot_claim", {}).get("claims"):
        cannot_claim.extend([f"Review Packet 360: {claim}" for claim in review_sections["cannot_claim"]["claims"]])

    source_refs = []
    if eval_case.get("source_refs"):
        source_refs.extend(eval_case["source_refs"])
    if review_packet.get("source_records"):
        source_refs.extend(review_packet["source_records"])
    source_event_record = review_sections.get("source_event_record", {})
    if source_event_record:
        source_refs.append(source_event_record)

    cer_seg = {
        "cer_entity": review_packet.get("cer_entity"),
        "seg_context": review_packet.get("seg_context"),
        "r1_cer_entity_resolution": review_sections.get("cer_entity_resolution"),
        "r1_seg_context": review_sections.get("seg_context"),
        "raw_id_bypass": review_sections.get("cer_entity_resolution", {}).get("raw_id_bypass", False),
    }

    check_summary = {
        "check_ref": check_ref,
        "expected_check_outcome": eval_case.get("expected_check_outcome"),
        "challenge_class": eval_case.get("challenge_class"),
        "aggregate_stress_outcome_counts": sources["check_stress"].get("outcome_counts", {}),
        "incident_check_context": incident_check,
        "matched_harness_assertion": check_assertion,
        "cannot_claim": cannot_claim,
    }

    event_state = {
        "eval_expected_event_handling": eval_case.get("expected_event_handling"),
        "event_fabric_v2_5": event_v25,
        "incident_plan_state": incident_event_state,
    }

    spatial_context = {
        "task_spatial_refs": packet_refs.get("spatial_refs", []),
        "incident_spatial": incident_spatial,
        "review_packet_spatial_refs": review_packet.get("spatial_overlay_refs") or review_sections.get("spatial_overlay_refs"),
        "event_fabric_v2_5_spatial_handoff_count": event_v25.get("spatial_handoff_count"),
    }

    return {
        "task_id": card["task_id"],
        "family": family_id,
        "scenario": scenario,
        "eval_case": eval_ref,
        "check_ref": check_ref,
        "derived_overlay_refs": overlay_refs,
        "what_this_task_tests": scenario_explanation(scenario),
        "source_evidence_summary": {
            "source_refs": source_refs,
            "source_class": eval_case.get("source_class"),
            "replay_mode": eval_case.get("replay_mode"),
            "expected_product_claim": eval_case.get("expected_product_claim"),
            "review_packet_source": review_packet_source,
            "review_packet_id": review_packet.get("packet_id") or review_packet.get("family_id"),
        },
        "cer_seg_context": cer_seg,
        "check_v1_summary": check_summary,
        "event_state": event_state,
        "simulation_option_context": simulation_context,
        "brief_summary": brief_context,
        "spatial_refs": spatial_context,
        "derived_overlay_summary": overlays,
        "cannot_claim": cannot_claim,
        "founder_review_questions": FOUNDER_QUESTIONS,
        "csv_row_guidance": CSV_FIELDS,
        "missing_evidence": missing,
        "known_limitations": card.get("known_limitations", []),
        "status": "PASS_WITH_LIMITATIONS",
    }


def card_markdown(card: dict[str, Any]) -> str:
    overlay_refs = card["derived_overlay_refs"]
    overlay_summary = [
        {
            "overlay_id": row.get("overlay_id"),
            "queue": row.get("queue"),
            "permitted_scope": row.get("permitted_scope"),
            "promoted_to_source_truth": row.get("promoted_to_source_truth"),
            "promoted_to_canonical_truth": row.get("promoted_to_canonical_truth"),
            "requires_review": row.get("requires_review"),
        }
        for row in card["derived_overlay_summary"]
    ]
    return f"""# Founder Probe Review Card: {card['task_id']}

## Task Identity

- Task id: `{card['task_id']}`
- Family: `{card['family']}`
- Scenario: `{card['scenario']}`
- Eval case: `{card['eval_case']}`
- CHECK ref: `{card['check_ref']}`
- Derived overlays: `{';'.join(overlay_refs)}`

## What This Task Tests

{card['what_this_task_tests']}

## Source / Evidence Summary

```json
{short_json(card['source_evidence_summary'])}
```

## CER / SEG Context

```json
{short_json(card['cer_seg_context'])}
```

## CHECK v1 Summary

```json
{short_json(card['check_v1_summary'])}
```

## Event State

```json
{short_json(card['event_state'])}
```

## Simulation / Option Context

```json
{short_json(card['simulation_option_context'])}
```

## BRIEF Summary

```json
{short_json(card['brief_summary'])}
```

## Spatial Refs

```json
{short_json(card['spatial_refs'])}
```

## Derived Overlay Summary

```json
{short_json(overlay_summary)}
```

## Missing Evidence Notes

{md_list(card['missing_evidence'])}

## Cannot-Claim Block

{md_list(card['cannot_claim'])}

## What You Should Judge

{md_list(card['founder_review_questions'])}

## CSV Row Guidance

Fill the review columns for this exact task in `FOUNDER_PROBE_RESPONSE_TEMPLATE_PREFILLED.csv`.
Keep stable metadata unchanged: `task_id`, `family`, `scenario`, `eval_case`, `check_ref`, `derived_overlays`, `reviewer_id_or_alias`, and `reviewer_type`.

Fields:

{md_list(CSV_FIELDS)}
"""


def index_markdown(cards: list[dict[str, Any]]) -> str:
    lines = [
        "# Founder Probe Review Index",
        "",
        f"Package: `{PACKAGE_ID}`",
        f"Status: `{STATUS}`",
        "",
        "This is founder-internal review material only. It does not run a session or create fuel, training rows, learned labels, live ingestion, forecasts, official actions, or source-truth mutation.",
        "",
        "| Task | Family | Scenario | Eval case | CHECK ref | Missing notes | Card |",
        "| --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for card in cards:
        path = f"review_cards/{card['task_id']}.md"
        lines.append(
            f"| `{card['task_id']}` | `{card['family']}` | `{card['scenario']}` | `{card['eval_case']}` | `{card['check_ref']}` | {len(card['missing_evidence'])} | [{card['task_id']}]({path}) |"
        )
    lines.extend(
        [
            "",
            "## Next Manual Step",
            "",
            "Read the cards, then fill `FOUNDER_PROBE_RESPONSE_TEMPLATE_PREFILLED.csv` manually. Do not fabricate responses from this assembler output.",
        ]
    )
    return "\n".join(lines)


def index_html(cards: list[dict[str, Any]]) -> str:
    rows = []
    for card in cards:
        href = f"review_cards/{html.escape(card['task_id'])}.md"
        rows.append(
            "<tr>"
            f"<td><code>{html.escape(card['task_id'])}</code></td>"
            f"<td>{html.escape(card['family'])}</td>"
            f"<td>{html.escape(card['scenario'])}</td>"
            f"<td><code>{html.escape(card['eval_case'])}</code></td>"
            f"<td><code>{html.escape(card['check_ref'])}</code></td>"
            f"<td>{len(card['missing_evidence'])}</td>"
            f"<td><a href=\"{href}\">open card</a></td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Founder Probe Review Index</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1d2733; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ccd4dd; padding: 8px; vertical-align: top; }}
    th {{ background: #eef3f7; text-align: left; }}
    code {{ white-space: nowrap; }}
    .guard {{ border-left: 4px solid #65758b; padding: 8px 12px; background: #f6f8fa; }}
  </style>
</head>
<body>
  <h1>Founder Probe Review Index</h1>
  <p><strong>Status:</strong> <code>{html.escape(STATUS)}</code></p>
  <p class="guard">Founder-internal review material only. No session, fuel, training rows, live ingestion, forecasts, official action, or source-truth mutation are created.</p>
  <table>
    <thead>
      <tr><th>Task</th><th>Family</th><th>Scenario</th><th>Eval case</th><th>CHECK ref</th><th>Missing notes</th><th>Card</th></tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>
"""


def response_guide() -> str:
    return """# Founder Probe Response Guide

Read `FOUNDER_PROBE_REVIEW_INDEX.md` or `FOUNDER_PROBE_REVIEW_INDEX.html`, then open each card under `review_cards/`.

Fill `FOUNDER_PROBE_RESPONSE_TEMPLATE_PREFILLED.csv` manually after review. Stable metadata is already filled and should not be changed:

- `task_id`
- `family`
- `scenario`
- `eval_case`
- `check_ref`
- `derived_overlays`
- `reviewer_id_or_alias`
- `reviewer_type`

Leave review fields blank until a real founder-internal review is performed. This assembler does not create session results, operator fuel, dispositions, training rows, learned labels, external validation, forecasts, or official actions.
"""


def prefilled_csv_rows(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for card in cards:
        row = {
            "task_id": card["task_id"],
            "family": card["family"],
            "scenario": card["scenario"],
            "eval_case": card["eval_case"],
            "check_ref": card["check_ref"],
            "derived_overlays": ";".join(card["derived_overlay_refs"]),
            "reviewer_id_or_alias": "Hazem",
            "reviewer_type": "founder_internal",
        }
        for field in REVIEW_FIELDS:
            row[field] = ""
        rows.append(row)
    return rows


def publish_tree() -> None:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    for source in sorted(OUTPUT_ROOT.rglob("*")):
        if source.is_file() and source.name != "HASH_MANIFEST.json":
            target = PUBLICATION_ROOT / source.relative_to(OUTPUT_ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())


def hash_manifest() -> dict[str, Any]:
    entries = []
    for scan_root in [OUTPUT_ROOT, PUBLICATION_ROOT]:
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*")):
            if path.is_file() and path.name != "HASH_MANIFEST.json":
                entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "algorithm": "sha256",
        "artifact_id": "HASH_MANIFEST",
        "entries": entries,
        "entry_count": len(entries),
        "generated_at": now_iso(),
        "status": "PASS",
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    (PUBLICATION_ROOT / "HASH_MANIFEST.json").write_bytes((OUTPUT_ROOT / "HASH_MANIFEST.json").read_bytes())
    return manifest


def verify_manifest(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing:{rel(path)}"]
    errors = []
    for entry in read_json(path, {}).get("entries", []):
        target = ROOT / entry["path"]
        if not target.exists():
            errors.append(f"missing:{entry['path']}")
        elif sha256_file(target) != entry["sha256"]:
            errors.append(f"mismatch:{entry['path']}")
    return errors


def build_review_pack() -> str:
    sources = build_sources()
    cards = sources["cards"]
    if len(cards) != 16:
        raise RuntimeError(f"Expected 16 founder probe task cards, found {len(cards)}")
    resolved_cards = [resolve_card(card, sources) for card in cards]
    generated_at = now_iso()

    for card in resolved_cards:
        write_json(CARD_DIR / f"{card['task_id']}.json", card)
        write_text(CARD_DIR / f"{card['task_id']}.md", card_markdown(card))

    write_text(OUTPUT_ROOT / "FOUNDER_PROBE_REVIEW_INDEX.md", index_markdown(resolved_cards))
    write_text(OUTPUT_ROOT / "FOUNDER_PROBE_REVIEW_INDEX.html", index_html(resolved_cards))
    write_text(OUTPUT_ROOT / "FOUNDER_PROBE_RESPONSE_GUIDE.md", response_guide())
    write_csv(OUTPUT_ROOT / "FOUNDER_PROBE_RESPONSE_TEMPLATE_PREFILLED.csv", prefilled_csv_rows(resolved_cards))

    missing_rows = [
        {"task_id": card["task_id"], "family": card["family"], "scenario": card["scenario"], "missing_evidence": card["missing_evidence"]}
        for card in resolved_cards
        if card["missing_evidence"]
    ]
    input_rows = input_audit()
    write_json(
        OUTPUT_ROOT / "INPUT_RESOLUTION_REPORT.json",
        {
            "artifact_id": "INPUT_RESOLUTION_REPORT",
            "generated_at": generated_at,
            "input_audit": input_rows,
            "input_count": len(input_rows),
            "task_card_count": len(resolved_cards),
            "all_task_cards_present": len(resolved_cards) == 16,
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        OUTPUT_ROOT / "MISSING_EVIDENCE_REPORT.json",
        {
            "artifact_id": "MISSING_EVIDENCE_REPORT",
            "card_count": len(resolved_cards),
            "cards_with_missing_evidence": len(missing_rows),
            "generated_at": generated_at,
            "missing_evidence": missing_rows,
            "policy": "Missing evidence is marked explicitly and is not invented.",
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        OUTPUT_ROOT / "NO_FABRICATED_SESSION_GUARD.json",
        {
            "artifact_id": "NO_FABRICATED_SESSION_GUARD",
            "external_operator_validation_claimed": False,
            "founder_responses_fabricated": False,
            "learning_arming_allowed": False,
            "official_workflow_or_action_created": False,
            "operator_fuel_created": False,
            "session_results_created": False,
            "source_truth_mutated": False,
            "training_rows_created": False,
            "status": "PASS",
        },
    )
    write_json(
        OUTPUT_ROOT / "FOUNDER_PROBE_REVIEW_PACK_SUMMARY.json",
        {
            "artifact_id": "FOUNDER_PROBE_REVIEW_PACK_SUMMARY",
            "card_count": len(resolved_cards),
            "csv_row_count": len(resolved_cards),
            "families": sorted({card["family"] for card in resolved_cards}),
            "generated_at": generated_at,
            "missing_evidence_card_count": len(missing_rows),
            "package_id": PACKAGE_ID,
            "reviewer_type": "founder_internal",
            "status": "PASS_WITH_LIMITATIONS",
        },
    )
    write_json(
        OUTPUT_ROOT / "FOUNDER_PROBE_ASSEMBLY_DECISION.json",
        {
            "artifact_id": "FOUNDER_PROBE_ASSEMBLY_DECISION",
            "card_count": len(resolved_cards),
            "csv_row_count": len(resolved_cards),
            "evidence_completeness_depends_on_available_prior_artifacts": True,
            "external_operator_validation_claimed": False,
            "forbidden_capabilities_created": [],
            "founder_internal_only": True,
            "founder_responses_fabricated": False,
            "generated_at": generated_at,
            "limitations": [
                "no founder session run",
                "no operator fuel",
                "no external validation",
                "evidence completeness depends on available prior artifacts",
                "review cards are for founder-internal assessment only",
            ],
            "operator_fuel_created": False,
            "package_id": PACKAGE_ID,
            "session_results_created": False,
            "source_truth_mutated": False,
            "status": STATUS,
            "training_rows_created": False,
        },
    )

    publish_tree()
    hash_manifest()
    return STATUS


def required_paths() -> list[Path]:
    paths = [OUTPUT_ROOT / filename for filename in TOP_LEVEL_FILES]
    paths.extend(CARD_DIR / f"founder-probe-r2-{index:02d}.md" for index in range(1, 17))
    paths.extend(CARD_DIR / f"founder-probe-r2-{index:02d}.json" for index in range(1, 17))
    return paths


def publication_paths() -> list[Path]:
    paths = [PUBLICATION_ROOT / filename for filename in TOP_LEVEL_FILES]
    paths.extend(PUB_CARD_DIR / f"founder-probe-r2-{index:02d}.md" for index in range(1, 17))
    paths.extend(PUB_CARD_DIR / f"founder-probe-r2-{index:02d}.json" for index in range(1, 17))
    return paths


def csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate_all() -> list[str]:
    errors: list[str] = []
    for path in required_paths() + publication_paths():
        if not path.exists():
            errors.append(f"missing:{rel(path)}")
    if errors:
        return errors

    decision = read_json(OUTPUT_ROOT / "FOUNDER_PROBE_ASSEMBLY_DECISION.json", {})
    guard = read_json(OUTPUT_ROOT / "NO_FABRICATED_SESSION_GUARD.json", {})
    summary = read_json(OUTPUT_ROOT / "FOUNDER_PROBE_REVIEW_PACK_SUMMARY.json", {})
    missing = read_json(OUTPUT_ROOT / "MISSING_EVIDENCE_REPORT.json", {})
    rows = csv_rows(OUTPUT_ROOT / "FOUNDER_PROBE_RESPONSE_TEMPLATE_PREFILLED.csv")
    card_jsons = [read_json(CARD_DIR / f"founder-probe-r2-{index:02d}.json", {}) for index in range(1, 17)]

    if decision.get("status") != STATUS or not decision.get("status", "").endswith("_WITH_LIMITATIONS"):
        errors.append("decision_status_failed")
    if summary.get("card_count") != 16 or summary.get("csv_row_count") != 16:
        errors.append("summary_counts_failed")
    if len(rows) != 16:
        errors.append("csv_row_count_failed")
    for row in rows:
        if not row.get("task_id"):
            errors.append("csv_missing_task_id")
        if row.get("reviewer_id_or_alias") != "Hazem":
            errors.append(f"csv_reviewer_alias_failed:{row.get('task_id')}")
        if row.get("reviewer_type") != "founder_internal":
            errors.append(f"csv_reviewer_type_failed:{row.get('task_id')}")
        for field in REVIEW_FIELDS:
            if row.get(field):
                errors.append(f"csv_fabricated_review_field:{row.get('task_id')}:{field}")
    for key, value in guard.items():
        if key.endswith("_created") or key in {
            "learning_arming_allowed",
            "founder_responses_fabricated",
            "external_operator_validation_claimed",
            "source_truth_mutated",
            "official_workflow_or_action_created",
        }:
            if value is not False:
                errors.append(f"guard_failed:{key}")
    if not any(card.get("missing_evidence") for card in card_jsons):
        errors.append("missing_evidence_not_represented")
    if missing.get("policy") != "Missing evidence is marked explicitly and is not invented.":
        errors.append("missing_evidence_policy_failed")
    errors.extend(verify_manifest(OUTPUT_ROOT / "HASH_MANIFEST.json"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if not args.validate_only:
        print(build_review_pack())
    errors = validate_all()
    if errors:
        print("VALIDATION FAILED")
        for error in errors:
            print(error)
        return 1
    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
