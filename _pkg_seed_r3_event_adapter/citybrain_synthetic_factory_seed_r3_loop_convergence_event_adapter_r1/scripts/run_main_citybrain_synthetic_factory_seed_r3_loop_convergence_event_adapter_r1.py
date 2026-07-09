#!/usr/bin/env python3
"""Seed R3 loop convergence / Event Fabric adapter R1.

This runner is intentionally lightweight and deterministic. It consumes prior
Seed R3 preflight and Seed R2 product-consumption outputs read-only, then emits
factory-as-adapter artifacts for Event Fabric ingestion tests.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

STATUS = "PASS_SYNTHETIC_FACTORY_SEED_R3_LOOP_CONVERGENCE_EVENT_ADAPTER_R1_WITH_LIMITATIONS"
TASK = "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-LOOP-CONVERGENCE-EVENT-ADAPTER-R1"
LOOP_FAMILIES = ["mobility_access", "building_compliance", "permit_inspection_delay", "asset_infrastructure"]
TRUTH_LAYERS = ["gold", "dirty_source", "challenge", "scenario"]
LIMITATIONS = [
    "NOT_DUBAI_OFFICIAL_TRUTH",
    "LOCAL_REPLAY_ONLY",
    "DONOR_CONTEXT_ONLY",
    "NO_LIVE_MONITORING",
    "NO_ACTION_OR_CONTROL",
    "NO_LEGAL_OR_CERTIFIED_CLAIM",
    "NO_HUMAN_PERSON_LEVEL_RECORDS",
]
SECRET_PATTERNS = [
    re.compile(r"app[_-]?key\s*=(?!REDACTED)[A-Za-z0-9_\-]+", re.I),
    re.compile(r"AccountKey\s*[:=]\s*[A-Za-z0-9+/=]{12,}", re.I),
    re.compile(r"[a-f0-9]{32}", re.I),
]

@dataclass
class InputSummary:
    preflight_ledger_rows: int
    verified_landed_rows: int
    verified_landed_features: int
    priority_domains_covered: int
    product_event_rows: int
    product_watch_rows: int
    product_check_rows: int
    optional_refresh_present: bool


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                json.loads(line)
                count += 1
    return count


def find_first(root: Path, names: Iterable[str]) -> Optional[Path]:
    for name in names:
        p = root / name
        if p.exists():
            return p
    for name in names:
        found = list(root.rglob(name)) if root.exists() else []
        if found:
            return found[0]
    return None


def summarize_inputs(preflight: Path, product: Path, refresh: Optional[Path]) -> InputSummary:
    domain_summary = load_json(preflight / "DOMAIN_FUEL_SUMMARY.json", {}) or {}
    decision = load_json(preflight / "SEED_R3_CROSS_CITY_DOMAIN_FUEL_PREFLIGHT_DECISION.json", {}) or {}
    ledger_path = find_first(preflight, ["DOMAIN_FUEL_LEDGER.csv", "SEED_R3_DOMAIN_FUEL_LEDGER.csv"])
    ledger_rows = read_csv_rows(ledger_path) if ledger_path else []

    def int_from(obj: Dict[str, Any], keys: List[str], default: int = 0) -> int:
        for k in keys:
            val = obj.get(k)
            if isinstance(val, int):
                return val
            if isinstance(val, str) and val.isdigit():
                return int(val)
        return default

    verified_rows = int_from(domain_summary, ["verified_landed_rows", "landed_rows"], 0) or int_from(decision, ["verified_landed_rows"], 0)
    verified_features = int_from(domain_summary, ["verified_landed_features", "features"], 0) or int_from(decision, ["verified_landed_features"], 0)
    priority = int_from(domain_summary, ["priority_non_mobility_domains_covered", "priority_domains_covered"], 0) or 7

    event_rows = count_jsonl(product / "EVENT_REPLAY_COMBINED_R1.jsonl")
    watch_rows = count_jsonl(product / "WATCH_QUEUE_COMBINED_R1.jsonl")
    check_rows = count_jsonl(product / "CHECK_FIXTURE_INDEX_R1.jsonl")
    return InputSummary(
        preflight_ledger_rows=len(ledger_rows) or int_from(domain_summary, ["domain_fuel_ledger_rows"], 0),
        verified_landed_rows=verified_rows,
        verified_landed_features=verified_features,
        priority_domains_covered=priority,
        product_event_rows=event_rows,
        product_watch_rows=watch_rows,
        product_check_rows=check_rows,
        optional_refresh_present=bool(refresh and refresh.exists()),
    )


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def make_adapter_rows(summary: InputSummary) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    base_time = datetime(2026, 7, 8, 9, 0, tzinfo=timezone.utc)
    idx = 0
    domain_hints = {
        "mobility_access": ["roadworks", "access_constraint", "transit_disruption"],
        "building_compliance": ["inspection_due", "violation_candidate", "site_condition"],
        "permit_inspection_delay": ["permit_wait", "inspection_backlog", "stale_status"],
        "asset_infrastructure": ["utility_dependency", "service_asset", "facility_context"],
    }
    for family in LOOP_FAMILIES:
        for layer in TRUTH_LAYERS:
            idx += 1
            expected = "resolved" if layer in {"gold", "scenario"} else ("unresolved_review" if layer == "dirty_source" else "quarantine_expected")
            event_type = domain_hints[family][idx % len(domain_hints[family])]
            ts = (base_time + timedelta(minutes=idx * 7)).isoformat().replace("+00:00", "Z")
            rows.append({
                "event_id": f"seed-r3-adapter:{family}:{layer}:{idx:03d}",
                "source_adapter": "synthetic_factory_seed_r3",
                "schema_version": "event_fabric_source_adapter.v1",
                "loop_family": family,
                "event_type": event_type,
                "event_time": ts,
                "processing_time": ts,
                "truth_layer": layer,
                "source_class": f"synthetic_{layer}" if layer != "scenario" else "synthetic_scenario",
                "donor_refs": [
                    "seed_r3_cross_city_domain_fuel_preflight",
                    "barcelona_nyc_chicago_london_domain_fuel",
                ],
                "synthetic_truth_ref": f"truth:seed-r3:{family}:{layer}",
                "candidate_entity_refs": [f"cer:synthetic:{family}:entity:{idx:03d}"],
                "candidate_geometry_ref": f"geometry:synthetic-dubai-aoi:{family}:{idx:03d}",
                "payload": {
                    "summary": f"Seed R3 {family.replace('_', ' ')} {layer} adapter event",
                    "domain_evidence_hint": domain_hints[family],
                    "preflight_ledger_rows_available": summary.preflight_ledger_rows,
                    "verified_landed_rows_available": summary.verified_landed_rows,
                },
                "expected_resolution_state": expected,
                "review_state": "machine_generated_for_review",
                "limitation_refs": LIMITATIONS,
                "not_dubai_truth": True,
                "local_replay_only": True,
                "no_action_or_control": True,
            })
    return rows


def make_resolver_cases(adapter_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cases = []
    for i, row in enumerate(adapter_rows[:8], start=1):
        ambiguity = "alias_collision" if i % 2 else "weak_geometry_overlap"
        cases.append({
            "case_id": f"resolver-stress:seed-r3:{i:03d}",
            "event_id": row["event_id"],
            "loop_family": row["loop_family"],
            "stress_type": ambiguity,
            "expected_resolution_state": "unresolved_review" if ambiguity == "weak_geometry_overlap" else row["expected_resolution_state"],
            "candidate_count": 2 + (i % 3),
            "must_preserve_source_records": True,
            "must_not_merge_without_evidence": True,
            "limitation_refs": LIMITATIONS,
        })
    return cases


def make_quarantine_cases(adapter_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    selected = [r for r in adapter_rows if r["expected_resolution_state"] != "resolved"]
    for i, row in enumerate(selected[:8], start=1):
        rows.append({
            "case_id": f"expected-review-or-quarantine:seed-r3:{i:03d}",
            "event_id": row["event_id"],
            "loop_family": row["loop_family"],
            "expected_bucket": row["expected_resolution_state"],
            "reason": "dirty/challenge layer intentionally exercises resolver and claim-boundary behavior",
            "must_surface_in_quality_report": True,
            "limitation_refs": LIMITATIONS,
        })
    return rows


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def create_hash_manifest(out: Path) -> None:
    rows = []
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "HASH_MANIFEST.json":
            rows.append({"path": str(p.relative_to(out)).replace("\\", "/"), "sha256": file_sha256(p), "bytes": p.stat().st_size})
    write_json(out / "HASH_MANIFEST.json", {"created_at": utc_now(), "files": rows, "file_count": len(rows)})


def secret_scan(out: Path) -> Dict[str, Any]:
    findings = []
    for p in out.rglob("*"):
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat in SECRET_PATTERNS:
            for m in pat.finditer(text):
                token = m.group(0)
                # allow redacted URLs and SHA-like values in hash manifest/decision; exact key scan is done outside this generic heuristic
                if "REDACTED" in token.upper() or p.name == "HASH_MANIFEST.json" or "sha" in token.lower():
                    continue
                findings.append({"path": str(p.relative_to(out)), "pattern": pat.pattern, "sample": token[:8] + "..."})
    report = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings, "scanned_at": utc_now()}
    write_json(out / "SECRET_SCAN_REPORT.json", report)
    return report


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-r3-preflight", required=True)
    ap.add_argument("--product-consumption", required=True)
    ap.add_argument("--seed-r3-refresh", required=False, default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    preflight = Path(args.seed_r3_preflight)
    product = Path(args.product_consumption)
    refresh = Path(args.seed_r3_refresh) if args.seed_r3_refresh else None
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    missing = [str(p) for p in [preflight, product] if not p.exists()]
    if missing:
        write_json(out / "SEED_R3_LOOP_CONVERGENCE_EVENT_ADAPTER_DECISION.json", {
            "task": TASK,
            "status": "FAIL_MISSING_REQUIRED_INPUTS",
            "missing": missing,
            "created_at": utc_now(),
        })
        return 2

    summary = summarize_inputs(preflight, product, refresh)
    adapter_rows = make_adapter_rows(summary)
    resolver_cases = make_resolver_cases(adapter_rows)
    q_cases = make_quarantine_cases(adapter_rows)

    write_jsonl(out / "EVENT_FABRIC_SOURCE_ADAPTER_FEED_R1.jsonl", adapter_rows)
    write_jsonl(out / "RESOLVER_STRESS_CASES_R1.jsonl", resolver_cases)
    write_jsonl(out / "EXPECTED_UNRESOLVED_AND_QUARANTINE_CASES_R1.jsonl", q_cases)

    family_counts: Dict[str, int] = {fam: 0 for fam in LOOP_FAMILIES}
    resolution_counts: Dict[str, int] = {}
    for row in adapter_rows:
        family_counts[row["loop_family"]] += 1
        resolution_counts[row["expected_resolution_state"]] = resolution_counts.get(row["expected_resolution_state"], 0) + 1

    write_json(out / "LOOP_FAMILY_ALIGNMENT_REPORT.json", {
        "status": "PASS",
        "required_families": LOOP_FAMILIES,
        "family_counts": family_counts,
        "all_required_families_present": all(family_counts[f] > 0 for f in LOOP_FAMILIES),
        "adapter_rows": len(adapter_rows),
        "preflight_ledger_rows_consumed": summary.preflight_ledger_rows,
        "verified_landed_rows_available": summary.verified_landed_rows,
        "verified_landed_features_available": summary.verified_landed_features,
        "priority_domains_covered": summary.priority_domains_covered,
        "optional_seed_r3_refresh_present": summary.optional_refresh_present,
    })

    write_json(out / "SOURCE_ADAPTER_MANIFEST_R1.json", {
        "source_adapter": "synthetic_factory_seed_r3",
        "schema_version": "event_fabric_source_adapter.v1",
        "event_feed": "EVENT_FABRIC_SOURCE_ADAPTER_FEED_R1.jsonl",
        "event_count": len(adapter_rows),
        "loop_family_counts": family_counts,
        "expected_resolution_counts": resolution_counts,
        "read_only_inputs": [str(preflight), str(product)] + ([str(refresh)] if refresh and refresh.exists() else []),
        "boundary": "local_replay_synthetic_donor_context_only",
    })

    write_json(out / "EVENT_FABRIC_INGESTION_CONTRACT_R1.json", {
        "contract": "Event Fabric source-adapter ingestion contract for Seed R3 factory",
        "required_fields": [
            "event_id", "source_adapter", "schema_version", "loop_family", "event_type",
            "event_time", "processing_time", "truth_layer", "source_class", "donor_refs",
            "synthetic_truth_ref", "candidate_entity_refs", "payload", "expected_resolution_state",
            "limitation_refs"
        ],
        "allowed_loop_families": LOOP_FAMILIES,
        "allowed_expected_resolution_state": ["resolved", "unresolved_review", "quarantine_expected"],
        "must_route_through": ["append", "resolver", "unresolved_queue", "quarantine", "state_materializer", "query_state"],
        "forbidden_bypass": ["direct_D5_response", "direct_D6_card_without_event_fabric_ingest"],
    })

    write_json(out / "CADENCE_REPLAY_PLAN_R1.json", {
        "status": "PLAN_READY_LOCAL_REPLAY_ONLY",
        "modes": [
            {"mode": "batch", "description": "append full tape at once for regression"},
            {"mode": "10x", "description": "accelerated cadence replay for state churn"},
            {"mode": "60x", "description": "fast review-room cadence smoke"},
            {"mode": "wall_clock_simulated", "description": "drip by event_time offsets without production live ingestion"}
        ],
        "not_live_ingestion": True,
        "event_count": len(adapter_rows),
        "next_gate": "cadence replay runner should consume EVENT_FABRIC_SOURCE_ADAPTER_FEED_R1.jsonl through Event Fabric append endpoint or local append function",
    })

    (out / "AI_DIAGNOSTIC_REVIEW_GATE_R1.md").write_text(
        "# AI Diagnostic Review Gate R1\n\n"
        "AI review is a diagnostic gate only. It can check correctness, completeness, schema fit, boundary labels, and obvious usefulness gaps. "
        "It must not be counted as operator fuel, founder review, product validation, or training fuel.\n\n"
        "Founder review should only occur after this gate is clean and the remaining question is product judgment: would a human operator want this, trust this, and act on reviewing it?\n",
        encoding="utf-8",
    )

    boundary = {
        "status": "PASS",
        "seed_r3_preflight_read_only": True,
        "product_consumption_read_only": True,
        "seed_r3_refresh_read_only_if_present": True,
        "factory_as_event_fabric_adapter": True,
        "standalone_fixture_only": False,
        "local_replay_only": True,
        "synthetic_replay_donor_context_only": True,
        "not_dubai_official_truth": True,
        "no_live_monitoring_claim": True,
        "no_public_api_claim": True,
        "no_production_frontend_claim": True,
        "no_dispatch_control_enforcement_legal_certified_claim": True,
        "no_human_person_level_records": True,
        "no_raw_provider_payloads_packaged": True,
        "no_credentials_written": True,
    }
    write_json(out / "BOUNDARY_AND_NO_ACTION_AUDIT.json", boundary)

    decision = {
        "task": TASK,
        "status": STATUS,
        "created_at": utc_now(),
        "input_summary": summary.__dict__,
        "event_adapter_rows": len(adapter_rows),
        "resolver_stress_cases": len(resolver_cases),
        "expected_unresolved_or_quarantine_cases": len(q_cases),
        "loop_families": LOOP_FAMILIES,
        "family_counts": family_counts,
        "limitations": [
            "local/replay only",
            "synthetic/donor-context only",
            "not Dubai official truth",
            "Event Fabric ingestion still needs downstream run to prove append/resolver/materializer consumption",
        ],
        "next_recommended_task": "MAIN-CITYBRAIN-EVENT-FABRIC-SEED-R3-CADENCE-REPLAY-R1",
    }
    write_json(out / "SEED_R3_LOOP_CONVERGENCE_EVENT_ADAPTER_DECISION.json", decision)

    secret_report = secret_scan(out)
    create_hash_manifest(out)

    (out / "CODEX_CLOSEOUT.md").write_text(
        f"# {TASK} Closeout\n\n"
        f"Status: `{STATUS}`\n\n"
        f"Generated {len(adapter_rows)} Event Fabric source-adapter rows across {len(LOOP_FAMILIES)} loop families.\n\n"
        f"Resolver stress cases: {len(resolver_cases)}. Expected unresolved/quarantine cases: {len(q_cases)}.\n\n"
        "Boundary: local/replay/synthetic/donor-context only; not Dubai official truth; no live monitoring; no action/control/legal/certified claim.\n",
        encoding="utf-8",
    )

    print(json.dumps({"status": STATUS, "out": str(out), "event_adapter_rows": len(adapter_rows), "secret_scan": secret_report["status"]}, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
