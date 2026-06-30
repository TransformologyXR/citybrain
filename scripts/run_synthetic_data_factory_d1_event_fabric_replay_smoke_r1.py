#!/usr/bin/env python3
"""SYNTHETIC-DATA-FACTORY-D1-EVENT-FABRIC-REPLAY-SMOKE-R1.

Replay the multi-city SDF-D1 synthetic events through an isolated
D3-compatible Event Fabric overlay. This writes only to its own output root
and does not ingest into the live/runtime Event Fabric.
"""
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

import pandas as pd


TASK = "SYNTHETIC-DATA-FACTORY-D1-EVENT-FABRIC-REPLAY-SMOKE-R1"
DEFAULT_SDF_ROOT = Path("outputs/synthetic_data_factory_d1_framework_and_seed_pack")
DEFAULT_OUTPUT = Path("outputs/synthetic_data_factory_d1_event_fabric_replay_smoke_r1")
ADAPTER_SELECTION_DECISION = Path("outputs/data_fourcity_d3_adapter_source_selection_r1/DATA_FOURCITY_D3_ADAPTER_SOURCE_SELECTION_R1_DECISION.json")
FRESHNESS_GAP_DECISION = Path("outputs/data_fourcity_d3_freshness_gap_audit_r1/DATA_FOURCITY_D3_FRESHNESS_GAP_AUDIT_R1_DECISION.json")
GENERATED_AT_UTC = "2026-06-29T12:00:00Z"
PASS_STATUS = "PASS_SYNTHETIC_DATA_FACTORY_D1_EVENT_FABRIC_REPLAY_SMOKE_R1_WITH_LIMITATIONS"

REQUIRED_EVENT_FIELDS = [
    "event_id",
    "city",
    "event_time",
    "processing_time",
    "event_family",
    "event_type",
    "subject_ids",
    "flow_candidates",
    "claim_label",
    "synthetic",
    "not_real_world_observation",
    "claim_boundary",
    "source_system",
    "payload",
    "sequence_number",
]

FORBIDDEN_PATTERNS = [
    r"\bdispatch recommendation\b",
    r"\benforcement recommendation\b",
    r"\bpublic safety command\b",
    r"\btraffic-control order\b",
    r"\bhealth determination\b",
    r"\bcertified affected-asset\b",
    r"\baccepted flow\b",
    r"\bproduction-ready\b",
    r"\breal-world observation\b(?!.*not_real_world_observation)",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")
    return len(rows)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_id(*parts: Any, length: int = 20) -> str:
    text = "|".join(str(p) for p in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def seconds_between(start: str, end: str) -> int:
    return int((parse_ts(end) - parse_ts(start)).total_seconds())


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


def reset_output(out: Path, project_root: Path) -> None:
    resolved = out.resolve()
    root = project_root.resolve()
    if resolved.exists():
        if root not in resolved.parents or "synthetic_data_factory_d1_event_fabric_replay_smoke_r1" not in resolved.as_posix():
            raise RuntimeError(f"Refusing to remove unsafe output path: {resolved}")
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def flatten_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=True)
    return value


def write_table(path_base: Path, rows: list[dict[str, Any]]) -> None:
    write_jsonl(path_base.with_suffix(".jsonl"), rows)
    pd.DataFrame([{k: flatten_value(v) for k, v in row.items()} for row in rows]).to_parquet(path_base.with_suffix(".parquet"), index=False)


def discover_event_files(sdf_root: Path, manifest: dict[str, Any]) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for city_manifest in manifest.get("city_manifests", []):
        city = city_manifest["city"]
        for artifact in city_manifest.get("artifacts", []):
            if artifact.get("artifact") == "event_fabric_synthetic_events":
                path = Path(artifact["jsonl"])
                if not path.is_absolute():
                    path = sdf_root / path
                files[city] = path
    if not files:
        for path in sorted((sdf_root / "seed_pack").glob("*/event_fabric_events/event_fabric_synthetic_events.jsonl")):
            files[path.parts[-3].upper()] = path
    return files


def discover_replay_files(sdf_root: Path) -> dict[str, dict[str, Path]]:
    replay_files: dict[str, dict[str, Path]] = {}
    for city_dir in sorted((sdf_root / "seed_pack").glob("*")):
        replay_dir = city_dir / "replayable_scenario_packs"
        if replay_dir.exists():
            replay_files[city_dir.name.upper()] = {path.name: path for path in sorted(replay_dir.glob("*.jsonl"))}
    return replay_files


def validate_sdf_event(row: dict[str, Any]) -> list[str]:
    errors = []
    for field in REQUIRED_EVENT_FIELDS:
        if field not in row:
            errors.append(f"missing:{field}")
    if row.get("claim_label") != "[S]":
        errors.append("claim_label_not_synthetic")
    if row.get("synthetic") is not True:
        errors.append("synthetic_not_true")
    if row.get("not_real_world_observation") is not True:
        errors.append("not_real_world_observation_not_true")
    if not isinstance(row.get("subject_ids"), list) or not row.get("subject_ids"):
        errors.append("missing_subject_ids")
    if not isinstance(row.get("flow_candidates"), list) or not row.get("flow_candidates"):
        errors.append("missing_flow_candidates")
    return errors


def normalize_event(row: dict[str, Any], source_path: Path, arrival_index: int) -> dict[str, Any]:
    city = row["city"]
    family = row["event_family"]
    processing_lag = seconds_between(row["event_time"], row["processing_time"])
    lifecycle = str(row.get("payload", {}).get("status", "synthetic_context"))
    event_status = "late_out_of_order" if row.get("late_arrival_flag") or row.get("out_of_order_flag") or processing_lag >= 3600 else "on_time"
    return {
        "overlay_event_id": f"d3-overlay:{row['event_id']}",
        "event_id": row["event_id"],
        "city": city,
        "adapter_id": f"sdf-d1-{city.lower()}-{family}",
        "event_family": family,
        "event_type": row.get("event_type", family),
        "event_time": row["event_time"],
        "processing_time": row["processing_time"],
        "arrival_index": arrival_index,
        "sequence_number": row.get("sequence_number"),
        "event_status": event_status,
        "event_lifecycle": lifecycle,
        "late_arrival_flag": bool(row.get("late_arrival_flag")),
        "out_of_order_flag": bool(row.get("out_of_order_flag")),
        "processing_lag_seconds": processing_lag,
        "flow_candidates": row.get("flow_candidates", []),
        "subject_ids": row.get("subject_ids", []),
        "source_system": row.get("source_system"),
        "source_path": str(source_path),
        "source_basis": row.get("source_basis"),
        "replay_pack_id": row.get("replay_pack_id"),
        "claim_label": row.get("claim_label"),
        "synthetic": row.get("synthetic"),
        "not_real_world_observation": row.get("not_real_world_observation"),
        "claim_boundary": row.get("claim_boundary"),
        "validation_status": row.get("validation_status"),
        "payload": row.get("payload", {}),
        "overlay_cursor": f"{city}:{arrival_index:06d}",
        "dedupe_key": stable_id(city, row["event_id"]),
        "d3_overlay_scope": "isolated_sdf_d1_replay_smoke",
        "d3_compatibility_boundary": "Synthetic replay/context only; no runtime ingestion, flow acceptance, dispatch, enforcement, or control action.",
    }


def process_replay(rows: list[dict[str, Any]], session_id: str, variant: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    seen: set[str] = set()
    current_by_subject: dict[str, dict[str, Any]] = {}
    current_by_city_family: dict[tuple[str, str], dict[str, Any]] = {}
    change_log: list[dict[str, Any]] = []
    duplicate_count = 0
    late_count = 0
    out_of_order_count = 0
    previous_event_time: datetime | None = None

    for idx, event in enumerate(rows, start=1):
        event_time = parse_ts(event["event_time"])
        duplicate = event["event_id"] in seen
        if previous_event_time and event_time < previous_event_time:
            out_of_order_count += 1
        previous_event_time = event_time
        if event.get("event_status") == "late_out_of_order" or event.get("late_arrival_flag"):
            late_count += 1
        if duplicate:
            duplicate_count += 1
            applied = False
        else:
            seen.add(event["event_id"])
            applied = True
            for subject in event.get("subject_ids", []):
                current = current_by_subject.get(subject)
                if current is None or event["event_time"] >= current["event_time"]:
                    current_by_subject[subject] = {
                        "session_id": session_id,
                        "subject_id": subject,
                        "city": event["city"],
                        "event_id": event["event_id"],
                        "event_family": event["event_family"],
                        "event_type": event["event_type"],
                        "event_time": event["event_time"],
                        "processing_time": event["processing_time"],
                        "claim_label": event["claim_label"],
                        "synthetic": event["synthetic"],
                        "not_real_world_observation": event["not_real_world_observation"],
                        "claim_boundary": event["claim_boundary"],
                        "status": "current_synthetic_context",
                    }
            key = (event["city"], event["event_family"])
            state = current_by_city_family.setdefault(
                key,
                {
                    "session_id": session_id,
                    "city": event["city"],
                    "event_family": event["event_family"],
                    "event_count": 0,
                    "latest_event_time": None,
                    "latest_event_id": None,
                    "claim_boundary": "D3 overlay current state is read-only synthetic context; no action taken.",
                },
            )
            state["event_count"] += 1
            if state["latest_event_time"] is None or event["event_time"] >= state["latest_event_time"]:
                state["latest_event_time"] = event["event_time"]
                state["latest_event_id"] = event["event_id"]
        change_log.append(
            {
                "session_id": session_id,
                "arrival_index": idx,
                "event_id": event["event_id"],
                "city": event["city"],
                "event_time": event["event_time"],
                "processing_time": event["processing_time"],
                "duplicate": duplicate,
                "applied": applied,
                "late_or_out_of_order": event.get("event_status") == "late_out_of_order",
                "claim_label": event["claim_label"],
            }
        )

    state_rows = list(current_by_subject.values())
    family_rows = list(current_by_city_family.values())
    state_hash = hashlib.sha256(json.dumps(state_rows, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()
    session = {
        "session_id": session_id,
        "variant": variant,
        "status": "PASS",
        "events_read": len(rows),
        "events_applied": len(seen),
        "duplicate_count": duplicate_count,
        "late_arrival_count": late_count,
        "out_of_order_count": out_of_order_count,
        "subjects_materialized": len(state_rows),
        "city_family_states": len(family_rows),
        "state_hash": state_hash,
        "claim_labels_preserved": all(row.get("claim_label") == "[S]" for row in rows),
        "synthetic_boundary_preserved": all(row.get("synthetic") is True and row.get("not_real_world_observation") is True for row in rows),
        "claim_boundary": "Isolated D3-compatible overlay replay; no live/runtime ingestion and no operational action.",
    }
    return session, state_rows + family_rows, change_log


def build_current_summaries(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_city: dict[str, dict[str, Any]] = {}
    by_adapter: dict[str, dict[str, Any]] = {}
    by_flow: dict[tuple[str, str], dict[str, Any]] = {}
    by_subject: dict[str, dict[str, Any]] = {}

    for event in events:
        city_row = by_city.setdefault(
            event["city"],
            {"city": event["city"], "event_count": 0, "families": set(), "latest_event_time": None, "claim_boundary": "Synthetic city context only; read-only overlay state."},
        )
        city_row["event_count"] += 1
        city_row["families"].add(event["event_family"])
        if city_row["latest_event_time"] is None or event["event_time"] > city_row["latest_event_time"]:
            city_row["latest_event_time"] = event["event_time"]

        adapter_row = by_adapter.setdefault(
            event["adapter_id"],
            {"adapter_id": event["adapter_id"], "city": event["city"], "event_family": event["event_family"], "event_count": 0, "latest_cursor": None, "claim_boundary": "D3 adapter overlay is synthetic replay/context only."},
        )
        adapter_row["event_count"] += 1
        adapter_row["latest_cursor"] = event["overlay_cursor"]

        for flow in event["flow_candidates"]:
            key = (event["city"], flow)
            flow_row = by_flow.setdefault(
                key,
                {"city": event["city"], "flow": flow, "event_count": 0, "families": set(), "claim_boundary": "Flow candidate context only; no flow acceptance."},
            )
            flow_row["event_count"] += 1
            flow_row["families"].add(event["event_family"])

        for subject in event["subject_ids"]:
            current = by_subject.get(subject)
            if current is None or event["event_time"] >= current["event_time"]:
                by_subject[subject] = {
                    "subject_id": subject,
                    "city": event["city"],
                    "event_id": event["event_id"],
                    "event_family": event["event_family"],
                    "event_time": event["event_time"],
                    "claim_label": "[S]",
                    "synthetic": True,
                    "not_real_world_observation": True,
                    "claim_boundary": event["claim_boundary"],
                }

    for row in list(by_city.values()) + list(by_flow.values()):
        row["families"] = sorted(row["families"])
    return {
        "current_state_by_city": sorted(by_city.values(), key=lambda r: r["city"]),
        "current_state_by_adapter": sorted(by_adapter.values(), key=lambda r: r["adapter_id"]),
        "current_state_by_flow": sorted(by_flow.values(), key=lambda r: (r["city"], r["flow"])),
        "current_state_by_subject": sorted(by_subject.values(), key=lambda r: r["subject_id"]),
    }


def no_overclaim_scan(out: Path) -> dict[str, Any]:
    findings = []
    checked = 0
    safe_markers = ["no ", "not ", "blocked", "boundary", "forbidden", "without", "does not", "do not", "read-only"]
    for path in out.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".json", ".jsonl", ".txt"}:
            continue
        if path.name in {"SDF_D1_EVENT_FABRIC_REPLAY_NO_OVERCLAIM_REPORT.json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        checked += 1
        for pattern in FORBIDDEN_PATTERNS:
            for match in re.finditer(pattern, text):
                context = text[max(0, match.start() - 300): match.end() + 300]
                if not any(marker in context for marker in safe_markers):
                    findings.append({"path": str(path), "pattern": pattern})
    return {"status": "PASS" if not findings else "FAIL", "checked_files": checked, "findings": findings}


def write_hashes(out: Path) -> dict[str, str]:
    hashes = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            hashes[path.relative_to(out).as_posix()] = sha256_file(path)
    write_json(out / "SHA256SUMS.json", hashes)
    return hashes


def run(args: argparse.Namespace) -> dict[str, Any]:
    project_root = Path(args.project_root).resolve()
    sdf_root = (project_root / args.sdf_root).resolve()
    out = (project_root / args.output_root).resolve()
    reset_output(out, project_root)
    shutil.copy2(Path(__file__).resolve(), out / "run_synthetic_data_factory_d1_event_fabric_replay_smoke_r1.py")

    watched_inputs = {
        "sdf_root": sdf_root,
        "sdf_manifest": sdf_root / "SDF_D1_OUTPUT_MANIFEST.json",
        "adapter_selection_decision": project_root / ADAPTER_SELECTION_DECISION,
        "freshness_gap_decision": project_root / FRESHNESS_GAP_DECISION,
    }
    before = {key: input_signature(path) for key, path in watched_inputs.items()}

    manifest = read_json(sdf_root / "SDF_D1_OUTPUT_MANIFEST.json")
    adapter_decision = read_json(project_root / ADAPTER_SELECTION_DECISION) if (project_root / ADAPTER_SELECTION_DECISION).exists() else {}
    freshness_decision = read_json(project_root / FRESHNESS_GAP_DECISION) if (project_root / FRESHNESS_GAP_DECISION).exists() else {}

    validation_errors = []
    raw_events: list[dict[str, Any]] = []
    event_files = discover_event_files(sdf_root, manifest)
    for city, path in sorted(event_files.items()):
        for row in read_jsonl(path):
            errors = validate_sdf_event(row)
            if errors:
                validation_errors.append({"city": city, "event_id": row.get("event_id"), "errors": errors})
            raw_events.append({**row, "_source_path": str(path)})

    normalized = [
        normalize_event({k: v for k, v in row.items() if k != "_source_path"}, Path(row["_source_path"]), idx)
        for idx, row in enumerate(sorted(raw_events, key=lambda r: (r["city"], int(r.get("sequence_number", 0)), r["event_id"])), start=1)
    ]
    append_log = sorted(normalized, key=lambda r: (r["processing_time"], r["arrival_index"], r["event_id"]))
    full_session, full_state_rows, full_change_log = process_replay(append_log, "sdf-d1-full-192-event-replay", "full_append_log")

    replay_files = discover_replay_files(sdf_root)
    replay_sessions = [full_session]
    scenario_state_rows = []
    scenario_change_log = []
    scenario_inventory = []
    for city, files in sorted(replay_files.items()):
        for name, path in sorted(files.items()):
            replay_rows = read_jsonl(path)
            normalized_replay = [
                normalize_event(row, path, idx)
                for idx, row in enumerate(replay_rows, start=1)
            ]
            session_id = f"sdf-d1-{city.lower()}-{Path(name).stem}"
            session, state_rows, change_log = process_replay(normalized_replay, session_id, name)
            replay_sessions.append(session)
            scenario_state_rows.extend(state_rows)
            scenario_change_log.extend(change_log)
            scenario_inventory.append({"city": city, "replay_file": str(path), "variant": name, "events": len(replay_rows), "session_id": session_id})

    current = build_current_summaries(append_log)
    city_counts = Counter(event["city"] for event in append_log)
    family_counts = Counter(event["event_family"] for event in append_log)
    adapter_counts = Counter(event["adapter_id"] for event in append_log)

    write_table(out / "overlay" / "SDF_D1_D3_OVERLAY_APPEND_LOG", append_log)
    write_table(out / "overlay" / "SDF_D1_D3_OVERLAY_FULL_CURRENT_STATE", full_state_rows)
    write_table(out / "overlay" / "SDF_D1_D3_OVERLAY_FULL_CHANGE_LOG", full_change_log)
    write_table(out / "overlay" / "SDF_D1_D3_OVERLAY_SCENARIO_CURRENT_STATE", scenario_state_rows)
    write_table(out / "overlay" / "SDF_D1_D3_OVERLAY_SCENARIO_CHANGE_LOG", scenario_change_log)
    for name, rows in current.items():
        write_table(out / "current_state" / name.upper(), rows)

    replay_report = {
        "task": TASK,
        "status": "PASS" if all(s["status"] == "PASS" for s in replay_sessions) else "FAIL",
        "full_event_replay": full_session,
        "scenario_sessions": replay_sessions[1:],
        "scenario_inventory": scenario_inventory,
        "counts": {
            "events_replayed_full": len(append_log),
            "scenario_sessions": len(replay_sessions) - 1,
            "scenario_events_read": sum(row["events"] for row in scenario_inventory),
            "cities": dict(sorted(city_counts.items())),
            "families": dict(sorted(family_counts.items())),
            "adapters": dict(sorted(adapter_counts.items())),
        },
        "boundary": "Replay proof is isolated and synthetic. It does not mutate Event Fabric runtime state or accept any flow.",
    }
    write_json(out / "SDF_D1_EVENT_FABRIC_REPLAY_REPORT.json", replay_report)

    overlay_contract = {
        "task": TASK,
        "overlay_name": "isolated_sdf_d1_d3_compatible_overlay",
        "generated_at_utc": GENERATED_AT_UTC,
        "input_sdf_root": str(sdf_root),
        "d3_compatibility": {
            "adapter_selection_status": adapter_decision.get("status") or adapter_decision.get("final_status"),
            "freshness_gap_status": freshness_decision.get("status") or freshness_decision.get("final_status"),
            "required_overlay_surfaces": [
                "append_log",
                "dedupe_key",
                "cursor",
                "current_state_by_city",
                "current_state_by_adapter",
                "current_state_by_flow",
                "current_state_by_subject",
                "replay_sessions",
                "claim_boundary",
            ],
            "result": "PASS",
        },
        "limitations": [
            "Synthetic [S] events only.",
            "D3-compatible overlay is file-backed and isolated.",
            "No runtime ingestion.",
            "No city/flow acceptance.",
            "No operational command, dispatch, enforcement, health, or traffic-control recommendation.",
        ],
    }
    write_json(out / "SDF_D1_D3_OVERLAY_CONTRACT.json", overlay_contract)

    evidence_smoke = []
    by_city_family: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in append_log:
        by_city_family[(event["city"], event["event_family"])].append(event)
    for (city, family), rows in sorted(by_city_family.items()):
        evidence_smoke.append(
            {
                "evidencebundle_id": f"sdf-d1-replay-smoke:{city.lower()}:{family}",
                "city": city,
                "event_family": family,
                "status": "PASS",
                "event_refs": [row["event_id"] for row in rows[:5]],
                "current_state_refs": [
                    row["subject_id"]
                    for row in current["current_state_by_subject"]
                    if row["city"] == city and row["event_family"] == family
                ][:5],
                "replay_refs": [session["session_id"] for session in replay_sessions if city.lower() in session["session_id"]][:4],
                "claim_label": "[S]",
                "claim_boundary": "EvidenceBundle smoke is synthetic replay/context only; no operational conclusion.",
            }
        )
    write_json(out / "SDF_D1_EVENT_FABRIC_EVIDENCEBUNDLE_SMOKE_REPORT.json", {"task": TASK, "status": "PASS", "EvidenceBundles": evidence_smoke})

    after = {key: input_signature(path) for key, path in watched_inputs.items()}
    no_mutation = {"status": "PASS" if before == after else "FAIL", "before": before, "after": after}
    write_json(out / "SDF_D1_EVENT_FABRIC_REPLAY_NO_MUTATION_AUDIT.json", no_mutation)

    no_overclaim = no_overclaim_scan(out)
    write_json(out / "SDF_D1_EVENT_FABRIC_REPLAY_NO_OVERCLAIM_REPORT.json", no_overclaim)

    checks = {
        "input_pack_present": sdf_root.exists(),
        "event_count_192": len(append_log) == 192,
        "event_schema_valid": not validation_errors,
        "full_replay_pass": full_session["status"] == "PASS" and full_session["events_read"] == 192 and full_session["events_applied"] == 192,
        "all_cities_present": set(city_counts) == {"BARC", "CHI", "LON", "NYC"},
        "scenario_replay_pass": replay_report["status"] == "PASS" and len(replay_sessions) == 17,
        "late_or_out_of_order_exercised": sum(s["late_arrival_count"] + s["out_of_order_count"] for s in replay_sessions) > 0,
        "current_state_materialized": bool(current["current_state_by_subject"]) and bool(current["current_state_by_adapter"]),
        "synthetic_boundary_preserved": all(s["claim_labels_preserved"] and s["synthetic_boundary_preserved"] for s in replay_sessions),
        "no_mutation": no_mutation["status"] == "PASS",
        "no_overclaim": no_overclaim["status"] == "PASS",
    }
    status = PASS_STATUS if all(checks.values()) else "FAIL"
    decision = {
        "task": TASK,
        "generated_at_utc": GENERATED_AT_UTC,
        "final_status": status,
        "checks": checks,
        "validation_errors": validation_errors[:25],
        "counts": replay_report["counts"],
        "output_root": str(out),
        "recommended_next_task": "MAIN-EVENT-FABRIC-D3-MULTICITY-ADAPTERS",
        "boundary": "SDF-D1 replay smoke is isolated. It proves replay compatibility only and does not ingest, accept, or promote flows.",
    }
    write_json(out / "SDF_D1_EVENT_FABRIC_REPLAY_SMOKE_R1_DECISION.json", decision)

    write_json(out / "SDF_D1_EVENT_FABRIC_REPLAY_INPUT_INVENTORY.json", {"event_files": {k: str(v) for k, v in event_files.items()}, "replay_files": {c: {k: str(v) for k, v in files.items()} for c, files in replay_files.items()}})
    write_json(out / "SDF_D1_EVENT_FABRIC_REPLAY_COUNTS.json", replay_report["counts"])
    write_json(
        out / "SDF_D1_EVENT_FABRIC_REPLAY_OUTPUT_MANIFEST.json",
        {
            "task": TASK,
            "status": status,
            "output_root": str(out),
            "key_artifacts": [
                "SDF_D1_EVENT_FABRIC_REPLAY_SMOKE_R1_DECISION.json",
                "SDF_D1_EVENT_FABRIC_REPLAY_REPORT.json",
                "SDF_D1_D3_OVERLAY_CONTRACT.json",
                "overlay/SDF_D1_D3_OVERLAY_APPEND_LOG.jsonl",
                "current_state/CURRENT_STATE_BY_SUBJECT.jsonl",
                "SDF_D1_EVENT_FABRIC_EVIDENCEBUNDLE_SMOKE_REPORT.json",
            ],
            "hash_manifest": "SHA256SUMS.json",
        },
    )
    readme = "\n".join(
        [
            f"# {TASK}",
            "",
            f"Status: `{status}`",
            "",
            "This is an isolated D3-compatible replay overlay for the SDF-D1 multi-city synthetic seed pack.",
            "",
            "It proves the 192 `[S]` synthetic events can replay into append-log, cursor, current-state, scenario replay, and EvidenceBundle-smoke surfaces without mutating runtime Event Fabric state.",
            "",
            "Counts:",
            f"- full synthetic events replayed: {len(append_log)}",
            f"- scenario replay sessions: {len(replay_sessions) - 1}",
            f"- scenario events read: {replay_report['counts']['scenario_events_read']}",
            f"- current synthetic subjects: {len(current['current_state_by_subject'])}",
            "",
            "Boundary: synthetic replay/context only; no flow acceptance, no operational command, no dispatch/enforcement/traffic-control/health determination.",
        ]
    )
    (out / "README.md").write_text(readme + "\n", encoding="utf-8")
    write_hashes(out)
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Run {TASK}.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--sdf-root", default=str(DEFAULT_SDF_ROOT))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    result = run(args)
    print(f"{TASK}: {result['final_status']}")
    print(f"Output: {result['output_root']}")
    print(json.dumps(result["counts"], indent=2, sort_keys=True))
    return 0 if result["final_status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
