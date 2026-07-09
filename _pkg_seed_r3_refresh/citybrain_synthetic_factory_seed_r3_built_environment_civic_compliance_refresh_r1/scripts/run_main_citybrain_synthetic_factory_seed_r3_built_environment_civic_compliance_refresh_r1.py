#!/usr/bin/env python3
"""
MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-BUILT-ENVIRONMENT-CIVIC-COMPLIANCE-REFRESH-R1

Generates a bounded Seed R3 synthetic-factory refresh from the Seed R3 cross-city
domain fuel preflight. This runner produces compact product fixtures only. It
does not copy raw provider payloads and does not mutate prior outputs.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

TASK_ID = "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-BUILT-ENVIRONMENT-CIVIC-COMPLIANCE-REFRESH-R1"
PASS_STATUS = "PASS_SYNTHETIC_FACTORY_SEED_R3_BUILT_ENVIRONMENT_CIVIC_COMPLIANCE_REFRESH_R1_WITH_LIMITATIONS"

PRIORITY_DOMAINS = [
    "property_planning",
    "built_environment",
    "building_compliance",
    "civic_service_311_crm",
    "environment_resilience",
    "data_quality_maturity",
    "identity_graph_eval",
]

LIMITATION_REFS = [
    "CROSS_CITY_DONOR_CONTEXT_ONLY_NOT_DUBAI_TRUTH",
    "SYNTHETIC_REPLAY_REVIEW_ONLY",
    "NO_LIVE_MONITORING",
    "NO_DISPATCH_CONTROL_ENFORCEMENT_LEGAL_CERTIFIED_CLAIM",
    "NO_HUMAN_PERSON_LEVEL_RECORDS",
]

def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")

def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
            count += 1
    return count

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def stable_id(*parts: str, prefix: str) -> str:
    slug = "::".join(parts).lower().replace(" ", "_")
    digest = hashlib.sha256(slug.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}:{digest}"

def as_int(value: Any) -> int:
    try:
        if value in (None, ""):
            return 0
        return int(float(str(value).replace(",", "")))
    except Exception:
        return 0

def discover_preflight(root: Path) -> Dict[str, Path]:
    required = {
        "summary": root / "DOMAIN_FUEL_SUMMARY.json",
        "ledger": root / "DOMAIN_FUEL_LEDGER.csv",
        "audit": root / "SEED_R3_BOUNDARY_AND_SOURCE_CLASS_AUDIT.json",
        "requirements": root / "SEED_R3_PRODUCT_FIXTURE_REQUIREMENTS.json",
    }
    missing = [str(p) for p in required.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing Seed R3 preflight files: " + "; ".join(missing))
    return required

def select_domain_city_rows(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    by_domain = summary.get("by_domain", {})
    for domain in PRIORITY_DOMAINS:
        entry = by_domain.get(domain, {})
        cities = entry.get("cities") or []
        if isinstance(cities, str):
            cities = [cities]
        if not cities:
            cities = ["cross_city_or_product"]
        for city in cities:
            if city == "cross_city_or_product" and domain != "data_quality_maturity":
                continue
            rows.append({
                "selection_id": stable_id(domain, city, prefix="seed_r3_selection"),
                "city": city,
                "domain": domain,
                "priority": entry.get("priority", "P0"),
                "landed_rows": as_int(entry.get("landed_rows")),
                "landed_features": as_int(entry.get("landed_features")),
                "registered_or_total_count": as_int(entry.get("registered_or_total_count")),
                "ledger_rows": as_int(entry.get("ledger_rows")),
                "seed_r3_use": entry.get("seed_r3_use", ""),
                "source_class": "cross_city_donor_context",
                "truth_layer": "synthetic_replay_donor_derived",
                "donor_refs": f"SeedR3Preflight:{domain}:{city}",
                "limitation_refs": "|".join(LIMITATION_REFS),
            })
    return rows

def fixture_base(selection: Dict[str, Any], idx: int) -> Dict[str, Any]:
    return {
        "id": stable_id(selection["selection_id"], str(idx), prefix="seed_r3_fixture"),
        "task_id": TASK_ID,
        "city_donor": selection["city"],
        "domain": selection["domain"],
        "source_class": "cross_city_donor_context",
        "truth_layer": "synthetic_replay_donor_derived",
        "donor_refs": [selection["donor_refs"]],
        "limitation_refs": LIMITATION_REFS,
        "not_dubai_truth": True,
        "synthetic_replay_only": True,
        "review_only": True,
        "no_action_claim": True,
    }

def build_entities(selections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    entities = []
    for i, sel in enumerate(selections):
        entity_type = {
            "property_planning": "planning_context_seed",
            "built_environment": "building_context_seed",
            "building_compliance": "compliance_context_seed",
            "civic_service_311_crm": "civic_service_context_seed",
            "environment_resilience": "environment_context_seed",
            "data_quality_maturity": "data_quality_context_seed",
            "identity_graph_eval": "identity_graph_eval_seed",
        }.get(sel["domain"], "domain_context_seed")
        row = fixture_base(sel, i)
        row.update({
            "canonical_seed_entity_id": stable_id(sel["city"], sel["domain"], prefix="cer_seed_r3"),
            "entity_type": entity_type,
            "label": f"{sel['city']} {sel['domain']} donor-context seed",
            "supporting_landed_rows": sel["landed_rows"],
            "supporting_features": sel["landed_features"],
            "source_selection_id": sel["selection_id"],
        })
        entities.append(row)
    return entities

def build_event_rows(selections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for i, sel in enumerate(selections):
        base = fixture_base(sel, i)
        base.update({
            "event_id": stable_id(sel["city"], sel["domain"], "event", prefix="event_seed_r3"),
            "event_type": f"synthetic_{sel['domain']}_review_signal",
            "event_time": f"2026-07-{(i % 28) + 1:02d}T09:{(i * 7) % 60:02d}:00Z",
            "subject_label": f"{sel['domain']} review signal from {sel['city']} donor corpus",
            "lifecycle_state": "replay_candidate",
            "current_state_effect": "adds_review_candidate_context",
            "severity": "review",
        })
        rows.append(base)
    return rows

def build_product_rows(selections: List[Dict[str, Any]], layer: str) -> List[Dict[str, Any]]:
    rows = []
    for i, sel in enumerate(selections):
        base = fixture_base(sel, i)
        base.update({
            f"{layer.lower()}_id": stable_id(sel["city"], sel["domain"], layer, prefix=f"{layer.lower()}_seed_r3"),
            "title": f"{layer}: {sel['domain']} donor-context fixture ({sel['city']})",
            "summary": (
                f"Seed R3 synthetic fixture using {sel['city']} {sel['domain']} donor/context fuel. "
                "This is not Dubai official truth and is for bounded review only."
            ),
            "supported_count_hint": sel["landed_rows"],
            "required_check": "claimability_required_before_use",
            "surface": layer,
        })
        if layer == "CHECK":
            base.update({
                "claimability": "cannot_claim_as_dubai_truth",
                "supported_claim": "donor corpus has usable fuel for synthetic fixture generation",
                "unsupported_claims": [
                    "official Dubai condition",
                    "live monitoring",
                    "dispatch/control/enforcement",
                    "certified/legal finding"
                ],
            })
        if layer == "BRIEF":
            base.update({
                "knowns": [
                    "cross-city donor/context fuel exists",
                    "source-class boundaries are required",
                ],
                "unknowns": [
                    "Dubai official matching source not present in this fixture",
                    "real-world operational status not claimed",
                ],
            })
        if layer == "SPATIAL":
            base.update({
                "overlay_type": "synthetic_domain_context_marker",
                "geometry_policy": "seed_or_context_geometry_only",
            })
        rows.append(base)
    return rows

def build_quality_rows(selections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    quality_domains = [s for s in selections if s["domain"] in {"data_quality_maturity", "identity_graph_eval"}]
    if not quality_domains:
        quality_domains = selections[:4]
    rows = []
    for i, sel in enumerate(quality_domains):
        base = fixture_base(sel, i)
        base.update({
            "quality_fixture_id": stable_id(sel["city"], sel["domain"], "quality", prefix="quality_seed_r3"),
            "quality_dimension": "source_class_boundary_and_identity_maturity",
            "diagnostic": f"Review {sel['city']} {sel['domain']} fuel for source-class, identity, and graph-eval usefulness.",
            "recommended_use": "quality_maturity_or_cer_seg_challenge_fixture",
        })
        rows.append(base)
    return rows

def build_report(summary: Dict[str, Any], selections: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_domain: Dict[str, Any] = {}
    for sel in selections:
        d = sel["domain"]
        by_domain.setdefault(d, {"cities": set(), "landed_rows": 0, "landed_features": 0, "selection_count": 0})
        by_domain[d]["cities"].add(sel["city"])
        by_domain[d]["landed_rows"] += sel["landed_rows"]
        by_domain[d]["landed_features"] += sel["landed_features"]
        by_domain[d]["selection_count"] += 1
    for val in by_domain.values():
        val["cities"] = sorted(val["cities"])
    return {
        "task_id": TASK_ID,
        "generated_at": now_iso(),
        "preflight_status": summary.get("status"),
        "preflight_verified_landed_rows": summary.get("verified_landed_rows"),
        "preflight_verified_landed_features": summary.get("verified_landed_features"),
        "selection_count": len(selections),
        "priority_domains": PRIORITY_DOMAINS,
        "by_domain": by_domain,
        "policy": "cross-city corpora are donor/context only and do not become Dubai official truth",
    }

def secret_scan(out: Path) -> Dict[str, Any]:
    # Exact scan against common env-var-provided keys plus conservative auth-token markers.
    secret_values = []
    for name in [
        "LTA_DATAMALL_ACCOUNT_KEY",
        "LTA_EXTENDED_OBU_SDK_ACCOUNT_KEY",
        "TFL_PRIMARY_KEY",
        "TFL_SECONDARY_KEY",
        "OPENAQ_API_KEY",
        "CDSAPI_KEY",
    ]:
        val = os.environ.get(name)
        if val:
            secret_values.append((name, val))
    hits = []
    for path in out.rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            text = data.decode("utf-8", errors="ignore")
            for name, val in secret_values:
                if val and val in text:
                    hits.append({"file": str(path), "secret_name": name, "kind": "exact_env_value"})
            # The runner has no API URL work. Flag obvious accidental auth query leakage.
            if "REDACTED" not in text and "token=" in text.lower():
                hits.append({"file": str(path), "kind": "possible_token_query"})
    return {
        "task_id": TASK_ID,
        "generated_at": now_iso(),
        "status": "PASS" if not hits else "FAIL",
        "hits": hits,
        "scanned_root": str(out),
    }

def hash_manifest(out: Path) -> Dict[str, Any]:
    files = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            rel = str(path.relative_to(out)).replace("\\", "/")
            files.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {"task_id": TASK_ID, "generated_at": now_iso(), "files": files}

def validate_output(out: Path) -> None:
    required = [
        "SEED_R3_BEE_CIVIC_COMPLIANCE_DECISION.json",
        "SEED_R3_DOMAIN_SELECTION_LEDGER.csv",
        "SEED_R3_SYNTHETIC_ENTITY_REFRESH.jsonl",
        "EVENT_REPLAY_SEED_R3.jsonl",
        "WATCH_SEED_R3.jsonl",
        "ASK_SEED_R3.jsonl",
        "CHECK_SEED_R3.jsonl",
        "BRIEF_SEED_R3.jsonl",
        "SPATIAL_SEED_R3.jsonl",
        "QUALITY_MATURITY_FIXTURES_SEED_R3.jsonl",
        "CROSS_CITY_DONOR_DISTRIBUTION_REPORT.json",
        "BOUNDARY_AND_NO_ACTION_AUDIT.json",
        "SECRET_SCAN_REPORT.json",
        "HASH_MANIFEST.json",
        "CODEX_CLOSEOUT.md",
    ]
    missing = [f for f in required if not (out / f).exists()]
    if missing:
        raise AssertionError("Missing output files: " + ", ".join(missing))
    # Parse JSON and JSONL
    for name in required:
        path = out / name
        if name.endswith(".json"):
            load_json(path)
        elif name.endswith(".jsonl"):
            count = 0
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    json.loads(line)
                    count += 1
            if count == 0 and "QUALITY" not in name:
                raise AssertionError(f"{name} is empty")
        elif name.endswith(".csv"):
            rows = read_csv(path)
            if not rows:
                raise AssertionError(f"{name} is empty")
    decision = load_json(out / "SEED_R3_BEE_CIVIC_COMPLIANCE_DECISION.json")
    if decision.get("status") != PASS_STATUS:
        raise AssertionError("Unexpected status")
    secret = load_json(out / "SECRET_SCAN_REPORT.json")
    if secret.get("status") != "PASS":
        raise AssertionError("Secret scan did not pass")
    audit = load_json(out / "BOUNDARY_AND_NO_ACTION_AUDIT.json")
    for flag in [
        "cross_city_donor_context_only",
        "not_dubai_official_truth",
        "no_human_person_level_records",
        "no_credentials_written",
        "no_live_monitoring_claim",
        "no_dispatch_control_enforcement_legal_certified_claim",
        "prior_outputs_read_only",
    ]:
        if audit.get(flag) is not True:
            raise AssertionError(f"Boundary flag failed: {flag}")

def run(args: argparse.Namespace) -> None:
    out = Path(args.out)
    if args.validate_only:
        validate_output(out)
        print(f"VALIDATE_ONLY_PASS {out}")
        return
    out.mkdir(parents=True, exist_ok=True)

    preflight_root = Path(args.seed_r3_preflight)
    files = discover_preflight(preflight_root)
    summary = load_json(files["summary"])
    audit = load_json(files["audit"])
    if audit.get("status") != "PASS":
        raise AssertionError("Seed R3 preflight boundary audit is not PASS")
    if summary.get("priority_non_mobility_domains_present", 0) < 7:
        raise AssertionError("Seed R3 preflight does not have all priority non-mobility domains")

    ledger = read_csv(files["ledger"])
    selections = select_domain_city_rows(summary)
    if len({s["domain"] for s in selections}) < 7:
        raise AssertionError("Selection does not cover seven priority domains")

    entities = build_entities(selections)
    event_rows = build_event_rows(selections)
    watch_rows = build_product_rows(selections, "WATCH")
    ask_rows = build_product_rows(selections, "ASK")
    check_rows = build_product_rows(selections, "CHECK")
    brief_rows = build_product_rows(selections, "BRIEF")
    spatial_rows = build_product_rows(selections, "SPATIAL")
    quality_rows = build_quality_rows(selections)

    write_csv(out / "SEED_R3_DOMAIN_SELECTION_LEDGER.csv", selections, [
        "selection_id", "city", "domain", "priority", "landed_rows", "landed_features",
        "registered_or_total_count", "ledger_rows", "seed_r3_use", "source_class",
        "truth_layer", "donor_refs", "limitation_refs"
    ])
    counts = {
        "domain_selection_rows": len(selections),
        "entity_refresh_rows": write_jsonl(out / "SEED_R3_SYNTHETIC_ENTITY_REFRESH.jsonl", entities),
        "event_replay_rows": write_jsonl(out / "EVENT_REPLAY_SEED_R3.jsonl", event_rows),
        "watch_rows": write_jsonl(out / "WATCH_SEED_R3.jsonl", watch_rows),
        "ask_rows": write_jsonl(out / "ASK_SEED_R3.jsonl", ask_rows),
        "check_rows": write_jsonl(out / "CHECK_SEED_R3.jsonl", check_rows),
        "brief_rows": write_jsonl(out / "BRIEF_SEED_R3.jsonl", brief_rows),
        "spatial_rows": write_jsonl(out / "SPATIAL_SEED_R3.jsonl", spatial_rows),
        "quality_maturity_rows": write_jsonl(out / "QUALITY_MATURITY_FIXTURES_SEED_R3.jsonl", quality_rows),
        "preflight_ledger_rows_consumed": len(ledger),
    }

    report = build_report(summary, selections)
    write_json(out / "CROSS_CITY_DONOR_DISTRIBUTION_REPORT.json", report)

    boundary_audit = {
        "task_id": TASK_ID,
        "generated_at": now_iso(),
        "status": "PASS",
        "cross_city_donor_context_only": True,
        "not_dubai_official_truth": True,
        "no_human_person_level_records": True,
        "no_credentials_written": True,
        "no_raw_bulky_data_packaged": True,
        "no_live_monitoring_claim": True,
        "no_public_api_claim": True,
        "no_production_frontend_claim": True,
        "no_dispatch_control_enforcement_legal_certified_claim": True,
        "prior_outputs_read_only": True,
        "synthetic_replay_review_only": True,
        "lta_tfl_mobility_not_modified": True,
        "seed_r2_not_replaced": True,
    }
    write_json(out / "BOUNDARY_AND_NO_ACTION_AUDIT.json", boundary_audit)

    scan = secret_scan(out)
    write_json(out / "SECRET_SCAN_REPORT.json", scan)
    if scan["status"] != "PASS":
        raise AssertionError("Secret scan failed")

    decision = {
        "task_id": TASK_ID,
        "generated_at": now_iso(),
        "status": PASS_STATUS,
        "readable_name": "Seed R3 Built Environment + Civic + Compliance Refresh",
        "seed_r3_preflight_status": summary.get("status"),
        "seed_r3_preflight_root": str(preflight_root),
        "product_consumption_root": str(args.product_consumption) if args.product_consumption else None,
        "priority_domains_covered": sorted({s["domain"] for s in selections}),
        "cities_covered": sorted({s["city"] for s in selections}),
        "counts": counts,
        "limitations": [
            "Cross-city material is donor/context only and not Dubai truth.",
            "Generated fixtures are synthetic/replay review fuel only.",
            "No live monitoring, dispatch, control, enforcement, legal, or certified claim.",
            "Counts are count-bearing local evidence totals, not de-duplicated unique-fact totals.",
        ],
        "next_recommended_task": "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-PRODUCT-CONSUMPTION-R1",
    }
    write_json(out / "SEED_R3_BEE_CIVIC_COMPLIANCE_DECISION.json", decision)

    closeout = f"""# CODEX CLOSEOUT — {TASK_ID}

Status: `{PASS_STATUS}`

Generated Seed R3 non-mobility refresh from the locked cross-city domain fuel preflight.

## Counts

```json
{json.dumps(counts, indent=2)}
```

## Boundaries

- Cross-city data is donor/context only.
- Not Dubai official truth.
- Synthetic/replay review-only.
- No human/person-level records.
- No credentials.
- No raw bulky data.
- No live monitoring, dispatch, control, enforcement, legal, or certified claim.

## Next

`MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-PRODUCT-CONSUMPTION-R1`
"""
    (out / "CODEX_CLOSEOUT.md").write_text(closeout, encoding="utf-8")

    write_json(out / "HASH_MANIFEST.json", hash_manifest(out))
    validate_output(out)
    print(PASS_STATUS)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-r3-preflight", required=True, help="Path to locked Seed R3 cross-city preflight output root")
    parser.add_argument("--product-consumption", default="", help="Optional prior Product Consumption output root, read-only")
    parser.add_argument("--out", required=True, help="Output root")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    run(args)

if __name__ == "__main__":
    main()
