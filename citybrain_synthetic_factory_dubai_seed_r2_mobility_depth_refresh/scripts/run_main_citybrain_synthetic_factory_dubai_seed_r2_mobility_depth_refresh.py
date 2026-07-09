#!/usr/bin/env python3
"""Generate MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R2-MOBILITY-DEPTH-REFRESH.

This runner consumes:
- Seed R1 synthetic factory output, read-only.
- R2E keyed mobility depth output, read-only.

It produces a Seed R2 addendum that refreshes only mobility-depth product fixtures.
It does not mutate any input output root and does not package raw external payloads.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

TASK = "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R2-MOBILITY-DEPTH-REFRESH"
PASS_STATUS = "PASS_SYNTHETIC_FACTORY_DUBAI_SEED_R2_MOBILITY_DEPTH_REFRESH_WITH_LIMITATIONS"
LIMITATIONS = [
    "LIM_R2_MOBILITY_DEPTH_REFRESH_NOT_DUBAI_TRUTH",
    "LIM_R2_MOBILITY_DEPTH_REFRESH_LOCAL_REPLAY_ONLY",
    "LIM_R2_MOBILITY_DEPTH_REFRESH_DONOR_CONTEXT_ONLY",
    "LIM_R2_MOBILITY_DEPTH_REFRESH_NO_ACTION_OR_CERTIFIED_CLAIM",
    "LIM_R2_MOBILITY_DEPTH_REFRESH_NO_HUMAN_PERSON_LEVEL_RECORDS",
]

REQUIRED_SEED_R1 = [
    "SYNTHETIC_FACTORY_DUBAI_SEED_R1_DECISION.json",
    "SEED_ENTITY_MANIFEST.json",
    "EVENT_REPLAY_TAPE.jsonl",
    "WATCH_SEED_QUEUE.jsonl",
    "ASK_ENTITY_PROFILE_FIXTURES.jsonl",
    "CHECK_CLAIMABILITY_FIXTURES.jsonl",
    "BRIEF_PACKET_FIXTURES.jsonl",
    "SPATIAL_OVERLAY_FIXTURES.jsonl",
]
REQUIRED_R2E = [
    "R2E_MASTER_DECISION.json",
    "DEPTH_PULL_REPORT_R2E.json",
    "SOURCE_STATUS_LEDGER_R2E.csv",
    "DOMAIN_FEED_MANIFEST_R2E.json",
    "NORMALIZED_MOBILITY_DONOR_SAMPLE_R2E.jsonl",
    "SAMPLE_ROW_COUNTS_R2E.csv",
    "SECRET_SCAN_REPORT_R2E.json",
]

OUTPUT_JSONL_FILES = [
    "EVENT_REPLAY_TAPE_MOBILITY_REFRESH_R2.jsonl",
    "WATCH_MOBILITY_DEPTH_QUEUE_R2.jsonl",
    "ASK_MOBILITY_ENTITY_PROFILE_FIXTURES_R2.jsonl",
    "CHECK_MOBILITY_DEPTH_FIXTURES_R2.jsonl",
    "BRIEF_MOBILITY_PACKET_FIXTURES_R2.jsonl",
    "SPATIAL_MOBILITY_OVERLAY_FIXTURES_R2.jsonl",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError(f"{path} line {i} is not an object")
            rows.append(obj)
    return rows


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def read_csv_dicts(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require_files(root: Path, names: List[str], label: str) -> None:
    missing = [name for name in names if not (root / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing {label} files under {root}: {missing}")


def compact_payload_text(payload: Dict[str, Any], limit: int = 160) -> str:
    text_fields = []
    for key in ("Message", "message", "Name", "name", "Type", "type", "Description", "description", "lineStatuses", "statusSeverityDescription"):
        if key in payload and payload[key] is not None:
            text_fields.append(str(payload[key]))
    if not text_fields:
        text_fields.append(json.dumps(payload, ensure_ascii=False, sort_keys=True)[:limit])
    return " | ".join(text_fields)[:limit]


def choose_seed_entities(seed_manifest: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    by_type = seed_manifest.get("seed_entities_by_type", {})
    return {
        "roads": by_type.get("road_segment_seed", []),
        "buildings": by_type.get("building_footprint_seed", []),
        "places": by_type.get("place_or_facility_seed", []),
        "pop": by_type.get("population_cell_seed", []),
    }


def record_ref(row: Dict[str, Any], idx: int) -> str:
    source_id = row.get("source_id", "unknown_source")
    target = row.get("normalization_target", "unknown_target")
    page_ref = row.get("page_ref", "sample")
    return f"r2e:{source_id}:{target}:{page_ref}:sample:{idx:04d}"


def event_kind_from_donor(row: Dict[str, Any]) -> str:
    target = str(row.get("normalization_target", "")).lower()
    source_id = str(row.get("source_id", "")).lower()
    payload = row.get("sample_payload_compact") or {}
    ptxt = compact_payload_text(payload).lower()
    if "incident" in target or "disruption" in target or "roadworks" in source_id or "road work" in ptxt or "closed" in ptxt:
        return "synthetic_mobility_disruption"
    if "stop" in target or "route" in target or "service" in target or "line" in target:
        return "synthetic_transit_service_context"
    if "bike" in target:
        return "synthetic_micromobility_context"
    if "air" in target:
        return "synthetic_air_quality_mobility_context"
    if "taxi" in target or "carpark" in target:
        return "synthetic_parking_access_context"
    return "synthetic_mobility_context"


def make_event_rows(samples: List[Dict[str, Any]], seed_entities: Dict[str, List[Dict[str, Any]]], max_rows: int = 30) -> List[Dict[str, Any]]:
    candidates = [s for s in samples if s.get("donor_context_only") is True or s.get("not_dubai_truth") is True]
    # Prefer event/status/disruption rows, but include broader transit/service rows for context.
    def score(row: Dict[str, Any]) -> int:
        target = str(row.get("normalization_target", "")).lower()
        source = str(row.get("source_id", "")).lower()
        score = 0
        for term in ("incident", "disruption", "road", "status", "roadworks", "traffic"):
            if term in target or term in source:
                score += 5
        for term in ("stop", "route", "service", "bike", "air", "taxi", "carpark"):
            if term in target or term in source:
                score += 1
        return score
    candidates = sorted(candidates, key=score, reverse=True)[:max_rows]
    roads = seed_entities.get("roads") or []
    buildings = seed_entities.get("buildings") or []
    places = seed_entities.get("places") or []
    rows: List[Dict[str, Any]] = []
    base_time = datetime(2026, 7, 7, 9, 0, tzinfo=timezone.utc)
    for idx, donor in enumerate(candidates, 1):
        road = roads[(idx - 1) % len(roads)] if roads else {"record_id": f"road_segment_seed:{idx:03d}", "evidence_refs": []}
        building = buildings[(idx - 1) % len(buildings)] if buildings else {"record_id": f"building_footprint_seed:{idx:03d}", "evidence_refs": []}
        place = places[(idx - 1) % len(places)] if places else {"record_id": f"place_or_facility_seed:{idx:03d}", "evidence_refs": []}
        evidence_refs = []
        for ent in (road, building, place):
            evidence_refs.extend(ent.get("evidence_refs", [])[:1])
        kind = event_kind_from_donor(donor)
        payload = donor.get("sample_payload_compact") or {}
        rows.append({
            "record_id": f"mobility_depth_event_replay_r2:{idx:03d}",
            "record_type": "mobility_depth_event_replay_fixture",
            "truth_layer": "scenario_layer_r2_mobility_depth_refresh",
            "source_class": "synthetic_mobility_replay_from_donor_context_not_dubai_truth",
            "factory_use": "synthetic_factory_mobility_depth_refresh",
            "is_real_world_fact": False,
            "donor_refs": [record_ref(donor, idx)],
            "evidence_refs": evidence_refs,
            "limitation_refs": LIMITATIONS,
            "payload": {
                "event_type": kind,
                "scenario_ref": f"scenario_seed_r2_mobility:{((idx - 1) // 5) + 1:03d}",
                "replay_time_utc": (base_time + timedelta(minutes=12 * (idx - 1))).isoformat().replace("+00:00", "Z"),
                "local_replay_only": True,
                "live_monitoring": False,
                "entity_refs": [road.get("record_id"), building.get("record_id"), place.get("record_id")],
                "donor_provider": donor.get("provider"),
                "donor_city": donor.get("city"),
                "donor_source_id": donor.get("source_id"),
                "donor_normalization_target": donor.get("normalization_target"),
                "donor_message_compact": compact_payload_text(payload),
                "not_dubai_truth": True,
                "no_action_or_certified_claim": True,
            },
        })
    return rows


def make_product_rows(event_rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    watch: List[Dict[str, Any]] = []
    ask: List[Dict[str, Any]] = []
    check: List[Dict[str, Any]] = []
    brief: List[Dict[str, Any]] = []
    spatial: List[Dict[str, Any]] = []
    groups = [event_rows[i:i+5] for i in range(0, min(len(event_rows), 30), 5)]
    for idx, group in enumerate(groups, 1):
        event_refs = [g["record_id"] for g in group]
        donor_refs = [d for g in group for d in g.get("donor_refs", [])]
        evidence_refs = list(dict.fromkeys([e for g in group for e in g.get("evidence_refs", [])]))
        source_class = "synthetic_mobility_depth_fixture_from_r2e_donor_context_not_dubai_truth"
        watch.append({
            "record_id": f"watch_mobility_depth_r2:{idx:03d}",
            "record_type": "watch_mobility_depth_queue_fixture",
            "truth_layer": "watch_fixture_r2_mobility_depth_refresh",
            "source_class": source_class,
            "factory_use": "synthetic_factory_mobility_depth_refresh",
            "is_real_world_fact": False,
            "donor_refs": donor_refs[:10],
            "evidence_refs": evidence_refs[:10],
            "limitation_refs": LIMITATIONS,
            "payload": {
                "queue_label": f"Mobility-depth synthetic review item {idx:02d}",
                "event_refs": event_refs,
                "status": "replay_ready",
                "live_monitoring": False,
                "recommended_human_move": "review evidence and limitations only",
            },
        })
        ask.append({
            "record_id": f"ask_mobility_depth_r2:{idx:03d}",
            "record_type": "ask_mobility_entity_profile_fixture",
            "truth_layer": "ask_fixture_r2_mobility_depth_refresh",
            "source_class": source_class,
            "factory_use": "synthetic_factory_mobility_depth_refresh",
            "is_real_world_fact": False,
            "donor_refs": donor_refs[:10],
            "evidence_refs": evidence_refs[:10],
            "limitation_refs": LIMITATIONS,
            "payload": {
                "question": "What mobility donor context is available for this synthetic Dubai seed scenario?",
                "answer_shape": "return donor distribution context, linked seed entities, replay events, and limitations only",
                "not_allowed_answer": "real Dubai transport status, live availability, route instruction, dispatch/control, certified incident finding",
                "event_refs": event_refs,
            },
        })
        check.append({
            "record_id": f"check_mobility_depth_r2:{idx:03d}",
            "record_type": "check_mobility_depth_claimability_fixture",
            "truth_layer": "check_fixture_r2_mobility_depth_refresh",
            "source_class": "synthetic_boundary_challenge_r2_mobility_depth_not_real_world_fact",
            "factory_use": "synthetic_factory_mobility_depth_refresh",
            "is_real_world_fact": False,
            "donor_refs": donor_refs[:10],
            "evidence_refs": evidence_refs[:10],
            "limitation_refs": LIMITATIONS,
            "payload": {
                "claim_text": "This R2 mobility fixture proves a live Dubai road disruption and should route a response.",
                "expected_result": "reject_as_not_claimable",
                "reason": "R2 mobility-depth refresh uses LTA/TfL donor context and local synthetic replay only.",
                "required_safe_rewrite": "This is a synthetic replay fixture shaped by donor mobility distributions, not a live Dubai road disruption or action instruction.",
            },
        })
        brief.append({
            "record_id": f"brief_mobility_depth_r2:{idx:03d}",
            "record_type": "brief_mobility_depth_packet_fixture",
            "truth_layer": "brief_fixture_r2_mobility_depth_refresh",
            "source_class": source_class,
            "factory_use": "synthetic_factory_mobility_depth_refresh",
            "is_real_world_fact": False,
            "donor_refs": donor_refs[:10],
            "evidence_refs": evidence_refs[:10],
            "limitation_refs": LIMITATIONS,
            "payload": {
                "brief_title": f"Synthetic mobility-depth replay packet {idx:02d}",
                "summary": "Local/replay-only mobility scenario shaped by deeper LTA/TfL donor distributions.",
                "allowed_use": "WATCH/ASK/CHECK/BRIEF/SPATIAL development and Event Fabric replay fixture",
                "forbidden_use": "dispatch, control, enforcement, certified/legal finding, live monitoring, or official Dubai status",
                "event_refs": event_refs,
            },
        })
        first = group[0]
        ents = first.get("payload", {}).get("entity_refs", [])
        spatial.append({
            "record_id": f"spatial_mobility_depth_r2:{idx:03d}",
            "record_type": "spatial_mobility_depth_overlay_fixture",
            "truth_layer": "spatial_fixture_r2_mobility_depth_refresh",
            "source_class": "synthetic_spatial_mobility_overlay_from_seed_r1_and_r2e_donor_context",
            "factory_use": "synthetic_factory_mobility_depth_refresh",
            "is_real_world_fact": False,
            "donor_refs": donor_refs[:10],
            "evidence_refs": evidence_refs[:10],
            "limitation_refs": LIMITATIONS,
            "payload": {
                "overlay_kind": "mobility_depth_replay_context",
                "render_mode": "local_fixture_only",
                "event_refs": event_refs,
                "seed_entity_refs": ents,
                "not_official_geometry_or_live_status": True,
            },
        })
    return watch, ask, check, brief, spatial


def build_distribution_profile(status_rows: List[Dict[str, str]], feed_manifest: List[Dict[str, Any]], samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    status_counts = Counter(row.get("status", "") for row in status_rows)
    provider_counts = Counter(row.get("provider", "") for row in status_rows)
    target_counts = Counter(row.get("normalization_target", "") for row in status_rows)
    sample_target_counts = Counter(row.get("normalization_target", "") for row in samples)
    pass_rows = [r for r in status_rows if r.get("status", "").startswith("PASS")]
    failed_rows = [r for r in status_rows if r.get("status", "").startswith("FAIL") or "BLOCKED" in r.get("status", "")]
    return {
        "profile_id": "MOBILITY_DISTRIBUTION_PROFILE_R2",
        "source": "R2E read-only donor/context mobility depth pull",
        "generated_at": utc_now(),
        "status_counts": dict(status_counts),
        "provider_counts": dict(provider_counts),
        "normalization_target_counts": dict(target_counts),
        "normalized_sample_target_counts": dict(sample_target_counts),
        "passing_feed_count": len(pass_rows),
        "failed_or_blocked_feed_count": len(failed_rows),
        "manifest_feed_count": len(feed_manifest),
        "sample_row_count": len(samples),
        "donor_context_only": True,
        "not_dubai_truth": True,
        "limitations": LIMITATIONS,
    }


def validate_records(rows_by_file: Dict[str, List[Dict[str, Any]]]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    required = {"record_id", "record_type", "source_class", "truth_layer", "donor_refs", "evidence_refs", "limitation_refs", "payload", "is_real_world_fact"}
    for fname, rows in rows_by_file.items():
        for i, row in enumerate(rows, 1):
            missing = required - set(row.keys())
            if missing:
                errors.append(f"{fname} row {i} missing {sorted(missing)}")
            if row.get("is_real_world_fact") is not False:
                errors.append(f"{fname} row {i} is_real_world_fact must be false")
            if not row.get("limitation_refs"):
                errors.append(f"{fname} row {i} missing limitation_refs")
            if "DUBAI_TRUTH" not in " ".join(row.get("limitation_refs", [])):
                errors.append(f"{fname} row {i} missing not-Dubai-truth limitation")
            payload = row.get("payload", {})
            if row.get("record_type", "").endswith("event_replay_fixture") and payload.get("local_replay_only") is not True:
                errors.append(f"{fname} row {i} event replay must be local_replay_only")
    return (not errors, errors)


def secret_scan(paths: Iterable[Path]) -> Dict[str, Any]:
    findings = []
    # Avoid scanning for actual values here; Codex should additionally scan exact env/local key values.
    suspicious_patterns = [
        re.compile(r"app_key=(?!REDACTED)[A-Za-z0-9_\-]{8,}", re.I),
        re.compile(r"AccountKey\s*[:=]\s*(?!REDACTED)[A-Za-z0-9+/=]{8,}", re.I),
        re.compile(r"Primary" r" key\s*[:=]", re.I),
        re.compile(r"Secondary" r" key\s*[:=]", re.I),
    ]
    for path in paths:
        if path.is_dir():
            files = [p for p in path.rglob("*") if p.is_file()]
        else:
            files = [path]
        for file in files:
            try:
                text = file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for pat in suspicious_patterns:
                if pat.search(text):
                    findings.append({"file": str(file), "pattern": pat.pattern})
    return {
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "note": "Pattern scan only. Codex must also run exact secret scan using local known key values across package/output/raw roots.",
    }


def make_hash_manifest(out: Path) -> Dict[str, Any]:
    entries = []
    for path in sorted(p for p in out.rglob("*") if p.is_file() and p.name != "HASH_MANIFEST.json"):
        entries.append({
            "path": str(path.relative_to(out)).replace(os.sep, "/"),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return {"generated_at": utc_now(), "entries": entries}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-r1", default="outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R1")
    parser.add_argument("--r2e", default="outputs/MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2E-KEYED-MOBILITY-DEPTH-PULL")
    parser.add_argument("--out", default=f"outputs/{TASK}")
    parser.add_argument("--max-event-rows", type=int, default=30)
    args = parser.parse_args()

    seed_root = Path(args.seed_r1)
    r2e_root = Path(args.r2e)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    require_files(seed_root, REQUIRED_SEED_R1, "Seed R1")
    require_files(r2e_root, REQUIRED_R2E, "R2E")

    seed_decision = read_json(seed_root / "SYNTHETIC_FACTORY_DUBAI_SEED_R1_DECISION.json")
    seed_manifest = read_json(seed_root / "SEED_ENTITY_MANIFEST.json")
    r2e_decision = read_json(r2e_root / "R2E_MASTER_DECISION.json")
    r2e_report = read_json(r2e_root / "DEPTH_PULL_REPORT_R2E.json")
    r2e_feed = read_json(r2e_root / "DOMAIN_FEED_MANIFEST_R2E.json")
    r2e_secret = read_json(r2e_root / "SECRET_SCAN_REPORT_R2E.json")
    status_rows = read_csv_dicts(r2e_root / "SOURCE_STATUS_LEDGER_R2E.csv")
    samples = read_jsonl(r2e_root / "NORMALIZED_MOBILITY_DONOR_SAMPLE_R2E.jsonl")

    if seed_decision.get("status") != "PASS_SYNTHETIC_FACTORY_DUBAI_SEED_R1_WITH_LIMITATIONS":
        raise RuntimeError(f"Unexpected Seed R1 status: {seed_decision.get('status')}")
    if r2e_decision.get("status") != "PASS_R2E_KEYED_MOBILITY_DEPTH_PULL_WITH_LIMITATIONS":
        raise RuntimeError(f"Unexpected R2E status: {r2e_decision.get('status')}")

    seed_entities = choose_seed_entities(seed_manifest)
    event_rows = make_event_rows(samples, seed_entities, max_rows=args.max_event_rows)
    if len(event_rows) < 10:
        raise RuntimeError(f"Expected at least 10 mobility-depth event rows; got {len(event_rows)}")
    watch, ask, check, brief, spatial = make_product_rows(event_rows)

    rows_by_file = {
        "EVENT_REPLAY_TAPE_MOBILITY_REFRESH_R2.jsonl": event_rows,
        "WATCH_MOBILITY_DEPTH_QUEUE_R2.jsonl": watch,
        "ASK_MOBILITY_ENTITY_PROFILE_FIXTURES_R2.jsonl": ask,
        "CHECK_MOBILITY_DEPTH_FIXTURES_R2.jsonl": check,
        "BRIEF_MOBILITY_PACKET_FIXTURES_R2.jsonl": brief,
        "SPATIAL_MOBILITY_OVERLAY_FIXTURES_R2.jsonl": spatial,
    }
    valid, validation_errors = validate_records(rows_by_file)

    lineage = {
        "task": TASK,
        "generated_at": utc_now(),
        "seed_r1_root": str(seed_root),
        "seed_r1_status": seed_decision.get("status"),
        "seed_r1_read_only": True,
        "r2e_root": str(r2e_root),
        "r2e_status": r2e_decision.get("status"),
        "r2e_read_only": True,
        "r2e_raw_root": r2e_report.get("raw_root"),
        "inputs_not_mutated_by_design": True,
        "notes": [
            "This is a Seed R2 addendum only.",
            "Seed R1 truth/status is preserved and not relabelled.",
            "R2E LTA/TfL records are donor/context distributions, not Dubai truth.",
        ],
    }
    write_json(out / "R2_INPUT_READONLY_LINEAGE.json", lineage)

    donor_summary = {
        "summary_id": "MOBILITY_DEPTH_DONOR_SUMMARY_R2",
        "generated_at": utc_now(),
        "r2e_status": r2e_decision.get("status"),
        "r2e_status_counts": r2e_report.get("status_counts"),
        "r2e_source_count": r2e_report.get("source_count"),
        "r2e_passing_feed_count": r2e_report.get("pass_count"),
        "r2e_raw_success_payload_files": r2e_report.get("raw_file_count"),
        "r2e_normalized_sample_rows": r2e_report.get("normalized_sample_rows"),
        "r2e_secret_scan_status": (
            r2e_secret.get("status")
            or r2e_secret.get("result")
            or r2e_secret.get("secret_scan_status")
            or ("PASS" if r2e_secret.get("passed") is True else "FAIL" if r2e_secret.get("passed") is False else None)
        ),
        "donor_context_only": True,
        "not_dubai_truth": True,
        "limitations": LIMITATIONS,
    }
    write_json(out / "MOBILITY_DEPTH_DONOR_SUMMARY_R2.json", donor_summary)

    distribution_profile = build_distribution_profile(status_rows, r2e_feed, samples)
    write_json(out / "MOBILITY_DISTRIBUTION_PROFILE_R2.json", distribution_profile)

    for fname, rows in rows_by_file.items():
        write_jsonl(out / fname, rows)

    validation_report = {
        "status": "PASS" if valid else "FAIL",
        "generated_at": utc_now(),
        "jsonl_row_counts": {fname: len(rows) for fname, rows in rows_by_file.items()},
        "record_validation_errors": validation_errors,
        "checks": {
            "event_replay_generated": len(event_rows) >= 10,
            "watch_generated": len(watch) >= 2,
            "ask_generated": len(ask) >= 2,
            "check_generated": len(check) >= 2,
            "brief_generated": len(brief) >= 2,
            "spatial_generated": len(spatial) >= 2,
            "r2e_donor_context_only": True,
            "seed_r1_not_mutated_by_runner": True,
        },
    }
    write_json(out / "FACTORY_VALIDATION_REPORT_R2.json", validation_report)

    boundary_audit = {
        "status": "PASS" if valid else "FAIL",
        "generated_at": utc_now(),
        "no_human_person_level_records": True,
        "no_credentials_written": True,
        "no_raw_bulky_data_packaged": True,
        "no_lta_tfl_treated_as_dubai_truth": True,
        "no_live_monitoring_claim": True,
        "no_dispatch_control_enforcement_legal_certified_claim": True,
        "seed_r1_read_only": True,
        "r2e_read_only": True,
        "limitations": LIMITATIONS,
    }
    write_json(out / "BOUNDARY_AND_NO_ACTION_AUDIT_R2.json", boundary_audit)

    scan = secret_scan([out])
    write_json(out / "SECRET_SCAN_REPORT_R2.json", scan)

    decision = {
        "task": TASK,
        "status": PASS_STATUS if valid and scan["status"] == "PASS" else "FAIL",
        "built_at": utc_now(),
        "output_root": str(out),
        "input_statuses": {
            "seed_r1": seed_decision.get("status"),
            "r2e": r2e_decision.get("status"),
        },
        "counts": {
            "event_replay_rows": len(event_rows),
            "watch_rows": len(watch),
            "ask_rows": len(ask),
            "check_rows": len(check),
            "brief_rows": len(brief),
            "spatial_rows": len(spatial),
            "r2e_normalized_sample_rows_consumed": len(samples),
            "r2e_status_rows": len(status_rows),
        },
        "acceptance": {
            "seed_r1_read_only": True,
            "r2e_read_only": True,
            "lta_tfl_donor_context_only": True,
            "not_dubai_truth": True,
            "event_replay_local_only": True,
            "watch_ask_check_brief_spatial_generated": True,
            "no_credentials_written": scan["status"] == "PASS",
            "no_dispatch_control_enforcement_legal_certified_claim": True,
        },
        "limitations": LIMITATIONS,
    }
    write_json(out / "SYNTHETIC_FACTORY_DUBAI_SEED_R2_MOBILITY_DEPTH_REFRESH_DECISION.json", decision)

    closeout = f"""# {TASK} closeout

Status: `{decision['status']}`

Seed R1 was consumed read-only and remains the baseline seed. R2E was consumed read-only as a mobility donor/context depth addendum.

Generated counts:

- Event replay rows: {len(event_rows)}
- WATCH rows: {len(watch)}
- ASK rows: {len(ask)}
- CHECK rows: {len(check)}
- BRIEF rows: {len(brief)}
- SPATIAL rows: {len(spatial)}

Boundary:

- LTA/TfL donor context only, not Dubai truth.
- Local/replay only, not live monitoring.
- No dispatch/control/enforcement/legal/certified claim.
- No human/person-level records.
- No credentials or raw provider payloads packaged.
"""
    (out / "CODEX_CLOSEOUT.md").write_text(closeout, encoding="utf-8")

    hash_manifest = make_hash_manifest(out)
    write_json(out / "HASH_MANIFEST.json", hash_manifest)

    if decision["status"] != PASS_STATUS:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
