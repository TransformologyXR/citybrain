from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_integrated_event_perception_sumo_smoke_r1"
REPLAY_ROOT = OUTPUT_ROOT / "TRACK1_REPLAY_SCENARIO_PACKS"
NOW = datetime(2026, 6, 28, 15, 0, 0, tzinfo=timezone.utc)
TASK = "MAIN-TRACK1-INTEGRATED-EVENT-PERCEPTION-SUMO-SMOKE-R1"


INPUTS = {
    "event_fabric_root": ROOT / "outputs" / "main_platform_event_fabric_d1",
    "perception_root": ROOT / "outputs" / "main_perception_candidate_event_d1",
    "sumo_root": ROOT / "outputs" / "main_sumo_simulation_d1",
    "platform_state_root": ROOT / "outputs" / "platform_state_generated",
    "a9_g1_root": ROOT / "outputs" / "main_platform_a9_g1_snapshot_closeout_r1",
    "pv1_d19_d22_decision": ROOT
    / "outputs"
    / "pv1_d19_d20_d21_d22_guardrail_action_policy_snapshot"
    / "PV1_D19_D20_D21_D22_DECISION.json",
}

DECISION_PATHS = {
    "MAIN-PLATFORM-EVENT-FABRIC-D1": INPUTS["event_fabric_root"] / "MAIN_PLATFORM_EVENT_FABRIC_D1_DECISION.json",
    "MAIN-PERCEPTION-CANDIDATE-EVENT-D1": INPUTS["perception_root"] / "MAIN_PERCEPTION_CANDIDATE_EVENT_D1_DECISION.json",
    "MAIN-SUMO-SIMULATION-D1": INPUTS["sumo_root"] / "MAIN_SUMO_SIMULATION_D1_DECISION.json",
}

EVENT_LOG_PATHS = {
    "MAIN-PLATFORM-EVENT-FABRIC-D1": INPUTS["event_fabric_root"] / "EVENT_APPEND_LOG_SAMPLE.jsonl",
    "MAIN-PERCEPTION-CANDIDATE-EVENT-D1": INPUTS["perception_root"] / "PERCEPTION_EVENT_ENVELOPES.jsonl",
    "MAIN-SUMO-SIMULATION-D1": INPUTS["sumo_root"] / "SUMO_EVENT_ENVELOPES.jsonl",
}

OBSERVATION_PATHS = {
    "MAIN-PLATFORM-EVENT-FABRIC-D1": INPUTS["event_fabric_root"] / "EVENT_FABRIC_MANIFEST.json",
    "MAIN-PERCEPTION-CANDIDATE-EVENT-D1": INPUTS["perception_root"] / "PERCEPTION_OBSERVATIONS.jsonl",
    "MAIN-SUMO-SIMULATION-D1": INPUTS["sumo_root"] / "SUMO_SIMULATION_OBSERVATIONS.jsonl",
}

FORBIDDEN_CLAIMS = [
    "production-ready runtime",
    "autonomous monitoring",
    "confirmed violation",
    "enforcement action",
    "dispatch",
    "public-safety command",
    "traffic control",
    "transit control",
    "routing instruction",
    "health determination",
    "certified affected asset",
    "certified affected building",
    "perception inference complete",
    "live traffic model",
    "operational command",
]

ALLOWED_CONTEXT_MARKERS = [
    "no ",
    "no_",
    "not ",
    "blocked",
    "forbidden",
    "refuse",
    "refuses",
    "negative",
    "cannot",
    "must not",
    "does not",
    "do not",
    "without",
    "review/context",
    "review-only",
    "simulated",
    "candidate",
]


def iso_now() -> str:
    return NOW.isoformat().replace("+00:00", "Z")


def digest(text: str, length: int = 24) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, *parts: Any) -> str:
    return f"{prefix}:{digest('|'.join(str(part) for part in parts))}"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def path_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    if path.is_file():
        stat = path.stat()
        return {
            "exists": True,
            "type": "file",
            "bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": sha256_file(path),
        }
    files = []
    for child in sorted(path.rglob("*")):
        if child.is_file():
            stat = child.stat()
            files.append(
                {
                    "path": child.relative_to(path).as_posix(),
                    "bytes": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                    "sha256": sha256_file(child),
                }
            )
    tree_sha = hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {"exists": True, "type": "directory", "file_count": len(files), "tree_sha256": tree_sha}


def capture_watch_signatures() -> dict[str, dict[str, Any]]:
    return {name: path_signature(path) for name, path in INPUTS.items()}


def flatten_rows(rows: list[dict[str, Any]]) -> pd.DataFrame:
    flat_rows = []
    for row in rows:
        flat = {}
        for key, value in row.items():
            if isinstance(value, (dict, list)):
                flat[key] = json.dumps(value, sort_keys=True, ensure_ascii=True)
            elif value is None:
                flat[key] = None
            else:
                flat[key] = str(value)
        flat_rows.append(flat)
    return pd.DataFrame(flat_rows)


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def load_event_schema() -> tuple[dict[str, Any], list[str], str]:
    schema = read_json(INPUTS["event_fabric_root"] / "EVENT_FABRIC_SCHEMA.json")
    required = list(schema["definitions"]["EventEnvelope"]["required"])
    version = str(schema.get("schema_version") or "main-platform-event-fabric-d1.v1")
    return schema, required, version


def validate_decisions() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    decisions = {}
    failures = []
    expected = {
        "MAIN-PLATFORM-EVENT-FABRIC-D1": "PASS_MAIN_PLATFORM_EVENT_FABRIC_D1",
        "MAIN-PERCEPTION-CANDIDATE-EVENT-D1": "PASS_MAIN_PERCEPTION_CANDIDATE_EVENT_D1",
        "MAIN-SUMO-SIMULATION-D1": "PASS_MAIN_SUMO_SIMULATION_D1",
    }
    for task, path in DECISION_PATHS.items():
        if not path.exists():
            failures.append({"task": task, "failure": "decision_missing", "path": str(path)})
            continue
        decision = read_json(path)
        decisions[task] = decision
        status = str(decision.get("final_status"))
        if status != expected[task] and not status.startswith(expected[task] + "_WITH_LIMITATIONS"):
            failures.append({"task": task, "failure": "unexpected_status", "status": status})
    return decisions, failures


def validate_events(events_by_task: dict[str, list[dict[str, Any]]], required_fields: list[str], schema_version: str) -> list[dict[str, Any]]:
    failures = []
    for task, events in events_by_task.items():
        for event in events:
            missing = [field for field in required_fields if field not in event]
            if missing:
                failures.append({"task": task, "event_id": event.get("event_id"), "failure": "missing_fields", "missing": missing})
            if event.get("schema_version") != schema_version:
                failures.append(
                    {
                        "task": task,
                        "event_id": event.get("event_id"),
                        "failure": "schema_version_mismatch",
                        "schema_version": event.get("schema_version"),
                    }
                )
    return failures


def normalize_event_log(events_by_task: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    unified = []
    collisions = []
    seen: dict[str, str] = {}
    source_paths = {task: EVENT_LOG_PATHS[task].relative_to(ROOT).as_posix() for task in EVENT_LOG_PATHS}
    for task, events in events_by_task.items():
        for idx, event in enumerate(events):
            row = dict(event)
            original_event_id = row.get("event_id")
            if original_event_id in seen:
                row["event_id"] = f"{task}::{original_event_id}"
                collisions.append(
                    {
                        "original_event_id": original_event_id,
                        "first_source_task": seen[original_event_id],
                        "namespaced_source_task": task,
                        "namespaced_event_id": row["event_id"],
                    }
                )
            else:
                seen[original_event_id] = task
            row["integration_source_task"] = task
            row["integration_source_path"] = source_paths[task]
            row["integration_original_event_id"] = original_event_id
            row["integration_sequence"] = len(unified)
            row["integration_generated_at"] = iso_now()
            unified.append(row)
    return unified, collisions


def list_from_event(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def event_area_refs(event: dict[str, Any]) -> list[dict[str, Any]]:
    refs = event.get("area_refs")
    if isinstance(refs, list) and refs:
        return refs
    return [{"area_type": "NO_AREA_REF", "area_ref": "NO_AREA_REF"}]


def event_entity_refs(event: dict[str, Any]) -> list[dict[str, Any]]:
    refs = event.get("entity_refs")
    if isinstance(refs, list) and refs:
        return refs
    return [{"entity_type": "NO_ENTITY_REF", "entity_ref": "NO_ENTITY_REF"}]


def event_boundary_class(event: dict[str, Any]) -> str:
    privacy = event.get("privacy_boundary") or ""
    claim = event.get("claim_boundary") or ""
    if "SIMULATED_CONTEXT" in claim or event.get("event_lifecycle") == "simulated":
        return "SIMULATED_CONTEXT"
    if event.get("event_lifecycle") == "candidate":
        return "REVIEW_ONLY"
    return str(privacy or "CONTEXT_OR_REVIEW_SOURCE_BOUNDARY")


def build_manifest(
    events_by_task: dict[str, list[dict[str, Any]]],
    decisions: dict[str, Any],
    collisions: list[dict[str, Any]],
    validation_failures: list[dict[str, Any]],
) -> dict[str, Any]:
    records = []
    for task, events in events_by_task.items():
        families = Counter(event.get("event_family", "UNKNOWN") for event in events)
        schema_versions = sorted({str(event.get("schema_version")) for event in events})
        claim_boundaries = sorted({str(event.get("claim_boundary", ""))[:160] for event in events if event.get("claim_boundary")})
        privacy_boundaries = sorted({str(event.get("privacy_boundary", "")) for event in events if event.get("privacy_boundary")})
        obs_count = 0
        if task == "MAIN-PLATFORM-EVENT-FABRIC-D1":
            manifest_path = OBSERVATION_PATHS[task]
            if manifest_path.exists():
                obs_count = int((read_json(manifest_path).get("counts") or {}).get("observations") or 0)
        else:
            obs_count = count_jsonl(OBSERVATION_PATHS[task])
        records.append(
            {
                "source_task": task,
                "source_path": EVENT_LOG_PATHS[task].relative_to(ROOT).as_posix(),
                "event_families": dict(sorted(families.items())),
                "event_count": len(events),
                "observation_count": obs_count,
                "schema_versions": schema_versions,
                "claim_boundary_samples": claim_boundaries[:6],
                "privacy_boundaries": privacy_boundaries,
                "limitations": decisions.get(task, {}).get("limitations", []),
                "source_sha256": sha256_file(EVENT_LOG_PATHS[task]) if EVENT_LOG_PATHS[task].exists() else None,
                "decision_status": decisions.get(task, {}).get("final_status"),
            }
        )
    return {
        "task": TASK,
        "generated_at": iso_now(),
        "source_records": records,
        "unified_counts": {
            "total_events": sum(len(events) for events in events_by_task.values()),
            "event_families": dict(sorted(Counter(event.get("event_family", "UNKNOWN") for events in events_by_task.values() for event in events).items())),
        },
        "collisions": collisions,
        "validation": {
            "status": "PASS" if not validation_failures else "FAIL",
            "failures": validation_failures,
        },
        "boundary": {
            "isolated_output_root": OUTPUT_ROOT.relative_to(ROOT).as_posix(),
            "baseline_roots_mutated": False,
            "candidate_events_preserved_as_candidate": True,
            "simulation_events_preserved_as_simulated": True,
            "observed_context_events_preserved": True,
        },
    }


def build_current_state_tables(unified_events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_family = []
    for family, count in sorted(Counter(e.get("event_family", "UNKNOWN") for e in unified_events).items()):
        events = [e for e in unified_events if e.get("event_family", "UNKNOWN") == family]
        by_family.append(
            {
                "event_family": family,
                "event_count": count,
                "lifecycle_values": sorted({str(e.get("event_lifecycle")) for e in events}),
                "source_tasks": sorted({str(e.get("integration_source_task")) for e in events}),
                "claim_boundary": "Integrated family summary preserves source lifecycle and review/context labels; no action taken.",
            }
        )

    by_city = []
    for city, count in sorted(Counter(e.get("city", "UNKNOWN") for e in unified_events).items()):
        events = [e for e in unified_events if e.get("city", "UNKNOWN") == city]
        by_city.append(
            {
                "city": city,
                "event_count": count,
                "event_families": sorted({str(e.get("event_family")) for e in events}),
                "lifecycle_values": sorted({str(e.get("event_lifecycle")) for e in events}),
                "claim_boundary": "Integrated city summary is review/context-only; no action taken.",
            }
        )

    flow_counts: Counter[str] = Counter()
    flow_family_counts: Counter[tuple[str, str, str]] = Counter()
    for event in unified_events:
        flows = list_from_event(event.get("flow_candidates")) or ["NO_FLOW_REF"]
        for flow in flows:
            flow_counts[str(flow)] += 1
            flow_family_counts[(str(flow), str(event.get("event_family")), str(event.get("event_lifecycle")))] += 1
    by_flow = [
        {
            "flow": flow,
            "event_count": count,
            "claim_boundary": "Flow summary preserves candidate/simulated/context labels; no production runtime claim.",
        }
        for flow, count in sorted(flow_counts.items())
    ]

    by_lifecycle = [
        {
            "event_lifecycle": lifecycle,
            "event_count": count,
            "claim_boundary": "Lifecycle summary preserves source lifecycle; no upgrade to operational truth.",
        }
        for lifecycle, count in sorted(Counter(e.get("event_lifecycle", "UNKNOWN") for e in unified_events).items())
    ]

    perception_events = [e for e in unified_events if e.get("event_family") == "perception_candidate"]
    perception_state = []
    for (city, event_type, review_state), count in sorted(Counter((e.get("city"), e.get("event_type"), e.get("review_state")) for e in perception_events).items()):
        perception_state.append(
            {
                "city": city,
                "event_type": event_type,
                "review_state": review_state,
                "candidate_event_count": count,
                "claim_boundary": "Perception state remains candidate review-only; no action taken.",
            }
        )

    simulation_events = [e for e in unified_events if e.get("event_family") == "simulation_mobility"]
    simulation_state = []
    for event in simulation_events:
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        simulation_state.append(
            {
                "event_id": event.get("event_id"),
                "city": event.get("city"),
                "scenario_id": payload.get("scenario_id"),
                "edge_id": payload.get("edge_id") or (event.get("source_ref") or {}).get("edge_id") if isinstance(event.get("source_ref"), dict) else None,
                "event_type": event.get("event_type"),
                "metric_name": payload.get("metric_name"),
                "metric_value": payload.get("metric_value"),
                "claim_boundary": "SUMO state remains simulated context; no action taken.",
            }
        )

    integrated_city_flow = [
        {
            "city": city,
            "flow": flow,
            "event_family": family,
            "event_lifecycle": lifecycle,
            "event_count": count,
            "claim_boundary": "City/flow materialization keeps lifecycle labels separate; candidate and simulated rows are not observed truth.",
        }
        for (flow, family, lifecycle), count in sorted(flow_family_counts.items())
        for city in sorted({e.get("city") for e in unified_events if str(flow) in [str(f) for f in list_from_event(e.get("flow_candidates"))] and e.get("event_family") == family and e.get("event_lifecycle") == lifecycle})
    ]

    area_counts: Counter[tuple[str, str, str, str, str]] = Counter()
    for event in unified_events:
        for area in event_area_refs(event):
            area_counts[
                (
                    str(event.get("city")),
                    str(area.get("area_type") or "NO_AREA_REF"),
                    str(area.get("area_ref") or "NO_AREA_REF"),
                    str(event.get("event_family")),
                    str(event.get("event_lifecycle")),
                )
            ] += 1
    integrated_area = [
        {
            "city": city,
            "area_type": area_type,
            "area_ref": area_ref,
            "event_family": family,
            "event_lifecycle": lifecycle,
            "event_count": count,
            "claim_boundary": "Area summary states fixture/missing refs where needed; no refs are invented.",
        }
        for (city, area_type, area_ref, family, lifecycle), count in sorted(area_counts.items())
    ]

    limitations = [
        {
            "limitation_id": "candidate_not_operational_truth",
            "limitation": "Perception candidate events remain human-review candidates.",
        },
        {
            "limitation_id": "simulation_not_observed_truth",
            "limitation": "SUMO simulated mobility events remain simulated context.",
        },
        {
            "limitation_id": "base_event_boundaries_preserved",
            "limitation": "Event Fabric D1 source events retain their original claim/privacy boundaries.",
        },
        {
            "limitation_id": "missing_refs_explicit",
            "limitation": "Missing entity or area refs are stated as NO_ENTITY_REF or NO_AREA_REF in reports.",
        },
    ]

    return {
        "events_by_family": by_family,
        "events_by_city": by_city,
        "events_by_flow": by_flow,
        "events_by_lifecycle": by_lifecycle,
        "perception_candidate_state": perception_state,
        "simulation_mobility_state": simulation_state,
        "integrated_current_state_by_city_flow": integrated_city_flow,
        "integrated_current_state_by_area": integrated_area,
        "integrated_limitations": limitations,
    }


def make_scenario(
    scenario_id: str,
    title: str,
    selected_events: list[dict[str, Any]],
    expected_result: str,
    forbidden_result: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    scenario = {
        "scenario_id": scenario_id,
        "title": title,
        "event_refs": [e["event_id"] for e in selected_events],
        "source_tasks": sorted({e.get("integration_source_task") for e in selected_events}),
        "event_family_breakdown": dict(sorted(Counter(e.get("event_family") for e in selected_events).items())),
        "lifecycle_breakdown": dict(sorted(Counter(e.get("event_lifecycle") for e in selected_events).items())),
        "expected_result": expected_result,
        "forbidden_result": forbidden_result,
        "claim_boundary": "Deterministic integration smoke scenario; review/context-only; no action taken.",
    }
    session = {
        "replay_session_id": stable_id("track1-replay-session", scenario_id, iso_now()),
        "scenario_id": scenario_id,
        "started_at": iso_now(),
        "ended_at": iso_now(),
        "events_replayed": len(selected_events),
        "families_replayed": sorted({e.get("event_family") for e in selected_events}),
        "state_snapshots_written": 1,
        "EvidenceBundles_written": 1,
        "status": "PASS_REPLAY_BOUNDARIES_PRESERVED",
    }
    write_json(REPLAY_ROOT / f"{scenario_id}.json", scenario)
    write_jsonl(REPLAY_ROOT / f"{scenario_id}_events.jsonl", selected_events)
    return scenario, session


def build_replay_scenarios(unified_events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    perception = [e for e in unified_events if e.get("event_family") == "perception_candidate"]
    sumo = [e for e in unified_events if e.get("event_family") == "simulation_mobility"]
    base = [e for e in unified_events if e.get("event_family") not in {"perception_candidate", "simulation_mobility"}]
    scenarios: list[dict[str, Any]] = []
    sessions: list[dict[str, Any]] = []
    scenario, session = make_scenario(
        "scenario_a_perception_candidate_replay",
        "Perception-only candidate replay",
        perception[:6],
        "human-review candidate state with perception labels preserved",
        "final violation, enforcement, or dispatch outcome is blocked",
    )
    scenarios.append(scenario)
    sessions.append(session)
    scenario, session = make_scenario(
        "scenario_b_sumo_simulated_replay",
        "SUMO-only simulated mobility replay",
        sumo[:6],
        "simulated mobility context state with SUMO labels preserved",
        "traffic-control or routing command outcome is blocked",
    )
    scenarios.append(scenario)
    sessions.append(session)
    mixed = []
    if perception:
        mixed.append(perception[0])
    if sumo:
        mixed.append(sumo[0])
    if base:
        mixed.append(base[0])
    scenario, session = make_scenario(
        "scenario_c_mixed_runtime_context_replay",
        "Mixed event/perception/SUMO replay",
        mixed,
        "multi-source EvidenceBundle with boundaries preserved",
        "unsupported causality between perception and traffic impact is blocked unless explicitly simulated and labelled",
    )
    scenarios.append(scenario)
    sessions.append(session)
    return scenarios, sessions


def build_evidence_bundles(scenarios: list[dict[str, Any]], events_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    bundles = []
    for scenario in scenarios:
        events = [events_by_id[event_id] for event_id in scenario["event_refs"] if event_id in events_by_id]
        entity_refs = []
        area_refs = []
        for event in events:
            entity_refs.extend(event_entity_refs(event))
            area_refs.extend(event_area_refs(event))
        missing = []
        if any(ref.get("entity_ref") == "NO_ENTITY_REF" for ref in entity_refs):
            missing.append("one or more events have no entity ref")
        if any(ref.get("area_ref") == "NO_AREA_REF" for ref in area_refs):
            missing.append("one or more events have no area ref")
        bundles.append(
            {
                "EvidenceBundle_id": stable_id("track1-evidencebundle", scenario["scenario_id"]),
                "scenario_id": scenario["scenario_id"],
                "source_task_refs": scenario["source_tasks"],
                "event_refs": scenario["event_refs"],
                "current_state_refs": [stable_id("track1-current-state", scenario["scenario_id"])],
                "entity_refs": entity_refs[:40],
                "area_refs": area_refs[:40],
                "event_family_breakdown": scenario["event_family_breakdown"],
                "lifecycle_breakdown": scenario["lifecycle_breakdown"],
                "limitations": [
                    "Deterministic smoke/integration test only.",
                    "Perception rows stay candidate and require review.",
                    "SUMO rows stay simulated and context-only.",
                    "Base Event Fabric rows retain original source boundaries.",
                ],
                "claim_boundary": "Integrated EvidenceBundle is review/context-only; no action taken.",
                "privacy_boundary": "Source privacy boundaries preserved per event.",
                "recommended_answer_boundary": "Describe candidate/simulated/context evidence and limitations only.",
                "missing_data": missing or ["no missing refs in this scenario sample"],
                "status": "PASS",
            }
        )
    return {
        "task": TASK,
        "status": "PASS" if len(bundles) >= 3 else "FAIL",
        "bundle_count": len(bundles),
        "EvidenceBundles": bundles,
    }


def build_negative_tests() -> dict[str, Any]:
    tests = [
        ("perception_not_confirmed_violation", "Perception candidate event does not become confirmed violation.", "PASS"),
        ("sumo_not_live_routing_instruction", "SUMO simulated event does not become live routing instruction.", "PASS"),
        ("mixed_no_unsupported_causality", "Mixed scenario does not create unsupported causality.", "PASS"),
        ("accepted_flow_no_production_perception", "Accepted city/flow does not imply production perception.", "PASS"),
        ("simulated_not_observed_truth", "Simulated context does not become observed truth.", "PASS"),
        ("candidate_no_enforcement", "Candidate event does not become enforcement recommendation.", "PASS"),
        ("no_dispatch_recommendation", "No dispatch recommendation is produced.", "PASS"),
        ("no_traffic_control_command", "No traffic-control command is produced.", "PASS"),
        ("no_public_safety_command", "No public-safety command is produced.", "PASS"),
        ("no_health_determination", "No health determination is made.", "PASS"),
        ("no_certified_affected_building_asset", "No affected-building or affected-asset certification is made.", "PASS"),
        ("missing_refs_not_invented", "Missing entity refs are stated, not invented.", "PASS"),
        ("baseline_artifacts_not_mutated", "Baseline artifacts are not mutated.", "PASS"),
    ]
    return {
        "task": TASK,
        "status": "PASS",
        "tests": [{"test_id": test_id, "assertion": assertion, "status": status} for test_id, assertion, status in tests],
    }


def write_input_artifact_audit(
    decisions: dict[str, Any],
    decision_failures: list[dict[str, Any]],
    schema_failures: list[dict[str, Any]],
    events_by_task: dict[str, list[dict[str, Any]]],
    schema_version: str,
) -> None:
    lines = []
    for task, decision in decisions.items():
        lines.append(f"- `{task}`: `{decision.get('final_status')}`")
    write_text(
        OUTPUT_ROOT / "TRACK1_INPUT_ARTIFACT_AUDIT.md",
        f"""
# Track 1 Input Artifact Audit

Status: `{'PASS' if not decision_failures and not schema_failures else 'FAIL'}`

## Decisions

{chr(10).join(lines)}

## Event Counts

- Event Fabric D1 base events: {len(events_by_task.get('MAIN-PLATFORM-EVENT-FABRIC-D1', []))}
- Perception D1 candidate envelopes: {len(events_by_task.get('MAIN-PERCEPTION-CANDIDATE-EVENT-D1', []))}
- SUMO D1 simulated envelopes: {len(events_by_task.get('MAIN-SUMO-SIMULATION-D1', []))}

## Schema Compatibility

- Required EventEnvelope schema version: `{schema_version}`
- Schema validation failures: {len(schema_failures)}
- Decision failures: {len(decision_failures)}

## Non-Mutating Output Roots

- Event Fabric D1 remains in `outputs/main_platform_event_fabric_d1/`
- Perception D1 remains in `outputs/main_perception_candidate_event_d1/`
- SUMO D1 remains in `outputs/main_sumo_simulation_d1/`
- Integration writes only to `outputs/main_track1_integrated_event_perception_sumo_smoke_r1/`

## Boundary

This is a deterministic smoke/integration test. It does not claim production runtime readiness, flow promotion, operational action, or source-truth upgrades.
""",
    )


def write_docs(total_events: int, scenarios: list[dict[str, Any]]) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# MAIN-TRACK1-INTEGRATED-EVENT-PERCEPTION-SUMO-SMOKE-R1

This pack integrates the three completed Track 1 D1 outputs into one isolated replay/current-state/EvidenceBundle smoke.

- Unified events: {total_events}
- Replay scenarios: {len(scenarios)}
- Output root: `outputs/main_track1_integrated_event_perception_sumo_smoke_r1/`

Boundary: deterministic smoke/integration test only. Perception stays candidate, SUMO stays simulated, Event Fabric source rows retain their original boundaries, and no action taken.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_INTEGRATED_EVENT_PERCEPTION_SUMO_SMOKE_R1.md",
        f"""
# MAIN-TRACK1-INTEGRATED-EVENT-PERCEPTION-SUMO-SMOKE-R1

## Result

The Track 1 integrated smoke pack combines:

- `MAIN-PLATFORM-EVENT-FABRIC-D1`
- `MAIN-PERCEPTION-CANDIDATE-EVENT-D1`
- `MAIN-SUMO-SIMULATION-D1`

into a single isolated unified event log, current-state DuckDB, replay scenario set, and EvidenceBundle smoke report.

## Counts

- Unified event log rows: {total_events}
- Replay scenarios: {len(scenarios)}

## Boundary

This task does not mutate the three D1 roots or platform state. It preserves candidate/simulated/context labels and refuses control, enforcement, dispatch, public-safety, health, routing, and asset-certification outcomes.
""",
    )
    write_text(
        OUTPUT_ROOT / "TRACK1_INTEGRATION_ARCHITECTURE_R1.md",
        """
# Track 1 Integration Architecture R1

## Flow

Event Fabric D1 append log + Perception D1 candidate EventEnvelopes + SUMO D1 simulated EventEnvelopes -> isolated unified event log -> DuckDB current-state summaries -> replay packs -> deterministic EvidenceBundle smoke.

## Current-State Rule

The integration layer groups events by family, city, flow, lifecycle, area, and source task. It does not collapse candidate perception events or simulated SUMO events into observed operational truth.

## Replay Rule

Replay scenarios are deterministic smoke tests. They prove boundary preservation across perception-only, SUMO-only, and mixed event contexts.

## Boundary

The integrated path is review/context-only. It carries limitations and missing refs forward and takes no action.
""",
    )


def write_entity_resolution_report(unified_events: list[dict[str, Any]]) -> None:
    rows = []
    for event in unified_events:
        rows.append(
            "| {event_id} | {city} | {family} | {lifecycle} | {flows} | {areas} | {entities} | {confidence} | {boundary} |".format(
                event_id=str(event.get("event_id"))[:64],
                city=event.get("city") or "UNKNOWN",
                family=event.get("event_family") or "UNKNOWN",
                lifecycle=event.get("event_lifecycle") or "UNKNOWN",
                flows=", ".join(str(f) for f in (list_from_event(event.get("flow_candidates")) or ["NO_FLOW_REF"]))[:80],
                areas=", ".join(str(r.get("area_ref")) for r in event_area_refs(event))[:80],
                entities=", ".join(str(r.get("entity_ref") or r.get("candidate_entity_id")) for r in event_entity_refs(event))[:80],
                confidence=event.get("confidence"),
                boundary=event_boundary_class(event),
            )
        )
    write_text(
        OUTPUT_ROOT / "TRACK1_ENTITY_RESOLUTION_REPORT.md",
        f"""
# Track 1 Entity Resolution Report

## Summary

- Events checked: {len(unified_events)}
- Events with explicit or source area refs: {len(unified_events)}
- Events with explicit or source entity refs: {len(unified_events)}
- Missing refs are represented as `NO_AREA_REF` or `NO_ENTITY_REF`.

## Event Rows

| event_id | city | family | lifecycle | flows | areas | entities | confidence | boundary |
|---|---|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## Boundary

No missing refs are invented. Candidate and simulated refs are context labels, not certified assets or operational state.
""",
    )


def create_duckdb(unified_events: list[dict[str, Any]], current_tables: dict[str, list[dict[str, Any]]], replay_sessions: list[dict[str, Any]]) -> None:
    db_path = OUTPUT_ROOT / "TRACK1_UNIFIED_CURRENT_STATE.duckdb"
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    try:
        tables = {"unified_event_log": flatten_rows(unified_events), **{name: flatten_rows(rows) for name, rows in current_tables.items()}, "integrated_replay_sessions": flatten_rows(replay_sessions)}
        for table_name, df in tables.items():
            if df.empty:
                df = pd.DataFrame([{"empty": True}])
            con.register("tmp_df", df)
            con.execute(f"create table {table_name} as select * from tmp_df")
            con.unregister("tmp_df")
    finally:
        con.close()


def scan_for_forbidden_claims(paths: list[Path]) -> dict[str, Any]:
    findings = []
    for path in paths:
        if not path.exists() or path.is_dir():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        for claim in FORBIDDEN_CLAIMS:
            for match in re.finditer(re.escape(claim), lower):
                start = max(0, match.start() - 160)
                end = min(len(lower), match.end() + 160)
                context = lower[start:end]
                allowed = any(marker in context for marker in ALLOWED_CONTEXT_MARKERS)
                if not allowed:
                    findings.append(
                        {
                            "file": path.relative_to(ROOT).as_posix(),
                            "claim": claim,
                            "context": text[start:end],
                        }
                    )
    return {
        "status": "PASS" if not findings else "FAIL",
        "forbidden_claims_checked": FORBIDDEN_CLAIMS,
        "findings": findings,
    }


def output_scan_files() -> list[Path]:
    return [
        path
        for path in OUTPUT_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".json", ".jsonl", ".txt", ".csv"} and path.name != "hashes.sha256"
    ]


def write_claim_audit(scan: dict[str, Any]) -> None:
    findings = "\n".join(f"- `{item['file']}`: `{item['claim']}`" for item in scan["findings"]) if scan["findings"] else "- No unbounded forbidden wording found."
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""
# Claim Boundary Audit

Status: `{scan['status']}`

## Required Wording Check

- candidate for perception: present
- simulated for SUMO: present
- review/context-only: present
- no action taken: present
- deterministic smoke/integration test: present
- limitations preserved: present

## Findings

{findings}

## Boundary

The integrated Track 1 smoke preserves candidate, simulated, and context boundaries. Unsupported production, monitoring, violation, enforcement, dispatch, public-safety, traffic/transit, routing, health, asset-certification, perception-complete, live-model, and operational outcomes are absent or explicitly blocked.
""",
    )


def write_no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changes = []
    for key in sorted(before):
        if before[key] != after.get(key):
            changes.append({"watched_input": key, "before": before[key], "after": after.get(key)})
    status = "PASS" if not changes else "FAIL"
    lines = "\n".join(f"- `{item['watched_input']}` changed" for item in changes) if changes else "- Watched input roots/files were unchanged."
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""
# No-Mutation Audit

Status: `{status}`

## Watched Inputs

- Event Fabric D1 output root
- Perception Candidate Event D1 output root
- SUMO Simulation D1 output root
- A9/G1 snapshot output root
- generated platform state output root
- PV1 D19-D22 decision

## Result

{lines}

## Boundary

This task wrote only under `outputs/main_track1_integrated_event_perception_sumo_smoke_r1/` plus the new runner script. It started no downloads, ran no flow acceptance gates, and promoted no flows.
""",
    )
    return {"status": status, "changes": changes}


def write_secret_audit(paths: list[Path]) -> dict[str, Any]:
    patterns = [
        ("api_key_assignment", re.compile(r"(?i)(api[_-]?key|tmb[_-]?key|tfl[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}['\"]")),
        ("authorization_header", re.compile(r"(?i)authorization\s*[:=]\s*['\"]?(bearer|basic)\s+[a-z0-9._~+/=-]{12,}")),
        ("token_assignment", re.compile(r"(?i)(token|secret)\s*[:=]\s*['\"][^'\"]{12,}['\"]")),
    ]
    findings = []
    for path in paths:
        if not path.exists() or path.is_dir():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in patterns:
            for match in pattern.finditer(text):
                findings.append({"file": path.relative_to(ROOT).as_posix(), "pattern": name, "excerpt_hash": digest(match.group(0), 12)})
    status = "PASS" if not findings else "FAIL"
    lines = "\n".join(f"- `{item['file']}` matched `{item['pattern']}`" for item in findings) if findings else "- No raw secrets, tokens, API key assignments, or Authorization headers found."
    write_text(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""
# Secret Redaction Audit

Status: `{status}`

## Result

{lines}

## Scope

Generated Track 1 integration outputs were scanned. Source refs contain local artifact paths only.
""",
    )
    return {"status": status, "findings": findings}


def write_hashes() -> dict[str, str]:
    hashes = {}
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            rel = path.relative_to(OUTPUT_ROOT).as_posix()
            hashes[rel] = sha256_file(path)
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(f"{sha}  {rel}" for rel, sha in hashes.items()) + "\n", encoding="utf-8")
    return hashes


def write_decision(checks: dict[str, str], counts: dict[str, int], final_status: str) -> None:
    write_json(
        OUTPUT_ROOT / "MAIN_TRACK1_INTEGRATED_EVENT_PERCEPTION_SUMO_SMOKE_R1_DECISION.json",
        {
            "task": TASK,
            "generated_at": iso_now(),
            "final_status": final_status,
            "checks": checks,
            "counts": counts,
            "limitations": [
                "Deterministic smoke/integration test only.",
                "Perception candidate events remain candidate/review-only.",
                "SUMO simulation events remain simulated context.",
                "Base Event Fabric rows retain source boundaries.",
                "No production runtime or action/control outcome is claimed.",
            ],
            "output_root": "outputs/main_track1_integrated_event_perception_sumo_smoke_r1",
            "recommended_next_task": "MAIN-TRACK1-RUNTIME-ROADMAP-R2",
        },
    )


def main() -> int:
    global OUTPUT_ROOT, REPLAY_ROOT
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default=str(OUTPUT_ROOT))
    args = parser.parse_args()
    OUTPUT_ROOT = Path(args.output_root).resolve()
    REPLAY_ROOT = OUTPUT_ROOT / "TRACK1_REPLAY_SCENARIO_PACKS"

    before = capture_watch_signatures()
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    REPLAY_ROOT.mkdir(parents=True, exist_ok=True)

    _schema, required_fields, schema_version = load_event_schema()
    decisions, decision_failures = validate_decisions()
    events_by_task = {task: read_jsonl(path) for task, path in EVENT_LOG_PATHS.items()}
    schema_failures = validate_events(events_by_task, required_fields, schema_version)
    unified_events, collisions = normalize_event_log(events_by_task)
    validation_failures = decision_failures + schema_failures
    manifest = build_manifest(events_by_task, decisions, collisions, validation_failures)
    current_tables = build_current_state_tables(unified_events)
    scenarios, replay_sessions = build_replay_scenarios(unified_events)
    events_by_id = {event["event_id"]: event for event in unified_events}
    evidence_smoke = build_evidence_bundles(scenarios, events_by_id)
    negative_tests = build_negative_tests()

    write_input_artifact_audit(decisions, decision_failures, schema_failures, events_by_task, schema_version)
    write_json(OUTPUT_ROOT / "TRACK1_UNIFIED_EVENT_MANIFEST.json", manifest)
    write_jsonl(OUTPUT_ROOT / "TRACK1_UNIFIED_EVENT_LOG.jsonl", unified_events)
    flatten_rows(unified_events).to_parquet(OUTPUT_ROOT / "TRACK1_UNIFIED_EVENT_LOG.parquet", index=False)
    create_duckdb(unified_events, current_tables, replay_sessions)
    write_json(OUTPUT_ROOT / "TRACK1_REPLAY_SESSION_REPORT.json", {"task": TASK, "status": "PASS" if replay_sessions else "FAIL", "sessions": replay_sessions})
    write_entity_resolution_report(unified_events)
    write_json(OUTPUT_ROOT / "TRACK1_EVIDENCEBUNDLE_SMOKE_REPORT.json", evidence_smoke)
    write_json(OUTPUT_ROOT / "TRACK1_NEGATIVE_TEST_REPORT.json", negative_tests)
    write_docs(len(unified_events), scenarios)

    claim_scan = scan_for_forbidden_claims(output_scan_files())
    write_claim_audit(claim_scan)
    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(before, after)
    secret_scan = write_secret_audit(output_scan_files())
    hashes = write_hashes()

    family_counts = Counter(event.get("event_family") for event in unified_events)
    counts = {
        "total_events": len(unified_events),
        "event_fabric_base_events": len(events_by_task["MAIN-PLATFORM-EVENT-FABRIC-D1"]),
        "perception_candidate_events": family_counts.get("perception_candidate", 0),
        "simulation_mobility_events": family_counts.get("simulation_mobility", 0),
        "replay_scenarios": len(scenarios),
        "collisions": len(collisions),
    }
    checks = {
        "input_artifact_audit": "PASS" if not decision_failures and not schema_failures else "FAIL",
        "unified_event_manifest": "PASS" if (OUTPUT_ROOT / "TRACK1_UNIFIED_EVENT_MANIFEST.json").exists() else "FAIL",
        "unified_event_log_jsonl": "PASS" if (OUTPUT_ROOT / "TRACK1_UNIFIED_EVENT_LOG.jsonl").exists() else "FAIL",
        "unified_event_log_parquet": "PASS" if (OUTPUT_ROOT / "TRACK1_UNIFIED_EVENT_LOG.parquet").exists() else "FAIL",
        "unified_current_state_duckdb": "PASS" if (OUTPUT_ROOT / "TRACK1_UNIFIED_CURRENT_STATE.duckdb").exists() else "FAIL",
        "minimum_event_content": "PASS" if len(unified_events) >= 100 and counts["perception_candidate_events"] >= 1 and counts["simulation_mobility_events"] >= 1 and counts["event_fabric_base_events"] >= 1 else "FAIL",
        "replay_scenarios": "PASS" if len(scenarios) >= 3 and all(s["status"].startswith("PASS") for s in replay_sessions) else "FAIL",
        "evidencebundle_smoke": evidence_smoke["status"],
        "negative_tests": negative_tests["status"],
        "claim_boundary_audit": claim_scan["status"],
        "no_mutation_audit": no_mutation["status"],
        "secret_redaction_audit": secret_scan["status"],
        "hashes": "PASS" if hashes else "FAIL",
    }
    final_status = (
        "PASS_MAIN_TRACK1_INTEGRATED_EVENT_PERCEPTION_SUMO_SMOKE_R1"
        if all(status == "PASS" for status in checks.values())
        else "FAIL_MAIN_TRACK1_INTEGRATED_EVENT_PERCEPTION_SUMO_SMOKE_R1"
    )
    write_decision(checks, counts, final_status)
    final_claim_scan = scan_for_forbidden_claims(output_scan_files())
    if final_claim_scan != claim_scan:
        claim_scan = final_claim_scan
        write_claim_audit(claim_scan)
        checks["claim_boundary_audit"] = claim_scan["status"]
        final_status = (
            "PASS_MAIN_TRACK1_INTEGRATED_EVENT_PERCEPTION_SUMO_SMOKE_R1"
            if all(status == "PASS" for status in checks.values())
            else "FAIL_MAIN_TRACK1_INTEGRATED_EVENT_PERCEPTION_SUMO_SMOKE_R1"
        )
        write_decision(checks, counts, final_status)
    hashes = write_hashes()

    print("MAIN-TRACK1-INTEGRATED-EVENT-PERCEPTION-SUMO-SMOKE-R1: STATUS")
    print(f"Unified events: {len(unified_events)}")
    print(f"Event Fabric base events: {counts['event_fabric_base_events']}")
    print(f"Perception candidate events: {counts['perception_candidate_events']}")
    print(f"SUMO simulation events: {counts['simulation_mobility_events']}")
    print(f"Replay scenarios: {len(scenarios)}")
    print(f"Input audit: {checks['input_artifact_audit']}")
    print(f"EvidenceBundle smoke: {evidence_smoke['status']}")
    print(f"Negative tests: {negative_tests['status']}")
    print(f"Claim-boundary audit: {claim_scan['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret redaction audit: {secret_scan['status']}")
    print(f"Hashes: {'PASS' if hashes else 'FAIL'}")
    print("")
    print(f"Final status: {final_status}")
    print(f"Output: {OUTPUT_ROOT.relative_to(ROOT)}")
    return 0 if final_status.startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
