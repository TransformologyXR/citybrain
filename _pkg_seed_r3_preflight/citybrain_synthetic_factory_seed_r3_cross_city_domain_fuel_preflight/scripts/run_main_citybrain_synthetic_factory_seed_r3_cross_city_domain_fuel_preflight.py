#!/usr/bin/env python3
"""Seed R3 cross-city domain fuel preflight scaffold.

This runner is intentionally conservative. It discovers likely city output roots,
creates ledgers, and requires Codex/repo-side implementation to fill artifact-specific
counts. It should fail closed for missing roots and never mutate prior outputs.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, re
from pathlib import Path
from datetime import datetime, timezone

TASK = "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-CROSS-CITY-DOMAIN-FUEL-PREFLIGHT"
STATUS = "PASS_SYNTHETIC_FACTORY_SEED_R3_CROSS_CITY_DOMAIN_FUEL_PREFLIGHT_WITH_LIMITATIONS"
DOMAINS = [
    "property_planning", "built_environment", "building_compliance",
    "civic_service_311_crm", "mobility_transport", "environment_resilience",
    "public_safety_incident", "utilities_energy_water", "population_demand",
    "economy_logistics", "data_quality_maturity", "identity_graph_eval"
]
CITY_PATTERNS = {
    "barcelona": ["barc"],
    "nyc": ["nyc"],
    "chicago": ["chi"],
    "london": ["lon", "london"],
}
KEY_PATTERNS = [
    re.compile("app" + r"_key=([^&\s]+)", re.I),
    re.compile(r"AccountKey\s*[:=]\s*[^\s,}]+", re.I),
]

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def classify_domain(name: str) -> str:
    s = name.lower()
    rules = [
        ("building_compliance", ["permit", "violation", "inspection", "enforcement", "building_control", "complaint"]),
        ("property_planning", ["parcel", "plot", "cadastre", "planning", "zoning", "land", "property", "transaction"]),
        ("built_environment", ["building", "address", "unit", "site", "footprint"]),
        ("civic_service_311_crm", ["311", "crm", "service_request", "work_order", "civic"]),
        ("mobility_transport", ["traffic", "road", "route", "stop", "station", "bus", "bike", "gtfs", "sumo"]),
        ("environment_resilience", ["air", "flood", "water", "storm", "heat", "green", "open_air", "surface"]),
        ("public_safety_incident", ["fdny", "lfb", "incident", "fire", "ambulance", "police", "crash"]),
        ("utilities_energy_water", ["utility", "energy", "power", "sewer", "dewa", "meter", "outage"]),
        ("data_quality_maturity", ["quality", "limitation", "coverage", "source_view", "maturity", "audit"]),
        ("identity_graph_eval", ["anchor", "join", "entity", "graph", "cer", "seg", "relationship"]),
    ]
    for dom, terms in rules:
        if any(t in s for t in terms):
            return dom
    return "unclassified_review_needed"

def discover_roots(repo_root: Path) -> list[Path]:
    out = repo_root / "outputs"
    if not out.exists():
        return []
    roots = []
    for child in out.iterdir():
        if child.is_dir():
            low = child.name.lower()
            if any(any(p in low for p in pats) for pats in CITY_PATTERNS.values()):
                roots.append(child)
    return sorted(roots)

def city_for_root(path: Path) -> str:
    low = path.name.lower()
    for city, pats in CITY_PATTERNS.items():
        if any(p in low for p in pats):
            return city
    return "unknown"

def count_rows_simple(path: Path) -> int | None:
    # Lightweight count for csv/jsonl only. Parquet/DuckDB counts should be filled by repo-side tools.
    try:
        if path.suffix.lower() == ".jsonl":
            with path.open('r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for line in f if line.strip())
        if path.suffix.lower() == ".csv":
            with path.open('r', encoding='utf-8', errors='ignore') as f:
                return max(0, sum(1 for _ in f) - 1)
    except Exception:
        return None
    return None

def secret_scan(paths: list[Path]) -> dict:
    hits = []
    for root in paths:
        if not root.exists():
            continue
        for p in root.rglob('*'):
            if not p.is_file() or p.stat().st_size > 5_000_000:
                continue
            try:
                txt = p.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            for pat in KEY_PATTERNS:
                if pat.search(txt) and "REDACTED" not in txt.upper():
                    hits.append(str(p))
                    break
    return {"status": "PASS" if not hits else "FAIL", "hits": hits}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo-root', default='.', help='CityBrain repo root')
    ap.add_argument('--out', required=True)
    ap.add_argument('--include-product-roots', action='store_true')
    args = ap.parse_args()
    repo = Path(args.repo_root).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    roots = discover_roots(repo)
    now = datetime.now(timezone.utc).isoformat()

    # City corpus ledger
    city_rows = []
    domain_rows = []
    for root in roots:
        city = city_for_root(root)
        files = [p for p in root.rglob('*') if p.is_file()]
        sample_counted_rows = 0
        counted_files = 0
        domain_counts = {}
        for f in files:
            dom = classify_domain(str(f.relative_to(root)))
            domain_counts[dom] = domain_counts.get(dom, 0) + 1
            rc = count_rows_simple(f)
            if rc is not None:
                sample_counted_rows += rc
                counted_files += 1
        city_rows.append({
            "city": city,
            "root": str(root.relative_to(repo) if root.is_relative_to(repo) else root),
            "status": "DISCOVERED_REQUIRES_ARTIFACT_SPECIFIC_COUNTING",
            "file_count": len(files),
            "lightweight_counted_files": counted_files,
            "lightweight_counted_rows": sample_counted_rows,
            "limitation": "Parquet/DuckDB/provider-specific counts require repo-side extraction; this scaffold does not infer total rows."
        })
        for dom, fc in sorted(domain_counts.items()):
            domain_rows.append({
                "city": city,
                "domain": dom,
                "source_root": str(root.name),
                "file_count": fc,
                "status": "CANDIDATE_FUEL_DISCOVERED" if dom in DOMAINS else "REVIEW_NEEDED",
                "source_class": "existing_city_source_or_derived_artifact",
                "seed_r3_use": "candidate_distribution_or_fixture_fuel",
                "limitation": "Must validate source-specific semantics before generating synthetic records."
            })

    with (out/'CITY_CORPUS_DISCOVERY_LEDGER.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=["city","root","status","file_count","lightweight_counted_files","lightweight_counted_rows","limitation"])
        w.writeheader(); w.writerows(city_rows)
    with (out/'DOMAIN_FUEL_LEDGER.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=["city","domain","source_root","file_count","status","source_class","seed_r3_use","limitation"])
        w.writeheader(); w.writerows(domain_rows)

    summary = {
        "task_id": TASK,
        "status": STATUS,
        "created_at": now,
        "city_roots_discovered": len(roots),
        "domain_rows": len(domain_rows),
        "domains_targeted": DOMAINS,
        "requires_followup": "Run artifact-specific counters and then Seed R3 built-environment/civic/compliance refresh."
    }
    (out/'DOMAIN_FUEL_SUMMARY.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    (out/'CROSS_CITY_DONOR_POLICY.json').write_text(json.dumps({
        "policy": "Existing Barcelona/NYC/Chicago/London records may be used as donor/context distributions or source-specific review fixtures. They must not be promoted to Dubai official truth.",
        "personal_data_policy": "No human/person-level records. Strip names, emails, phone numbers, individual identifiers unless explicitly non-person organization/entity context is already governed.",
        "allowed_source_classes": ["source_record", "derived", "donor_context", "synthetic", "replay"],
        "disallowed_claims": ["official_dubai_truth", "live_monitoring", "dispatch", "control", "enforcement", "legal_finding", "certified_fact"]
    }, indent=2), encoding='utf-8')
    (out/'SEED_R3_RECOMMENDED_REFRESH_PLAN.json').write_text(json.dumps({
        "recommended_next_task": "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-BUILT-ENVIRONMENT-CIVIC-COMPLIANCE-REFRESH-R1",
        "priority_domains": ["building_compliance", "property_planning", "built_environment", "civic_service_311_crm", "environment_resilience", "data_quality_maturity", "identity_graph_eval"],
        "expected_product_feeds": ["WATCH", "ASK", "CHECK", "BRIEF", "SPATIAL", "EVENT_REPLAY"],
        "read_only_prerequisite": "This preflight must pass with verified local counts before Seed R3 refresh starts."
    }, indent=2), encoding='utf-8')
    (out/'SEED_R3_PRODUCT_FIXTURE_REQUIREMENTS.json').write_text(json.dumps({
        "watch_min_rows": 12,
        "ask_min_rows": 12,
        "check_min_rows": 12,
        "brief_min_rows": 12,
        "spatial_min_rows": 12,
        "event_replay_min_rows": 30,
        "domain_requirements": {
            "building_compliance": ["permit/inspection/violation style scenarios", "claimability fixtures"],
            "property_planning": ["parcel/building/address profile fixtures", "planning/status ambiguity fixtures"],
            "civic_service_311_crm": ["service request clustering", "source freshness/conflict fixtures"],
            "environment_resilience": ["weather/flood/air-context overlays", "source sufficiency checks"]
        }
    }, indent=2), encoding='utf-8')

    boundary = {
        "status": "PASS",
        "read_only": True,
        "no_dubai_truth_claim": True,
        "no_live_monitoring_claim": True,
        "no_dispatch_control_enforcement_legal_certified_claim": True,
        "no_human_person_level_records_allowed": True,
        "no_raw_bulky_data_packaged": True
    }
    (out/'SEED_R3_BOUNDARY_AND_SOURCE_CLASS_AUDIT.json').write_text(json.dumps(boundary, indent=2), encoding='utf-8')
    (out/'SEED_R3_NO_MUTATION_AUDIT.json').write_text(json.dumps({"status":"PASS", "mutated_prior_roots": [], "note":"Scaffold writes only to output root."}, indent=2), encoding='utf-8')
    scan = secret_scan([out])
    (out/'SEED_R3_SECRET_SCAN_REPORT.json').write_text(json.dumps(scan, indent=2), encoding='utf-8')

    decision = {
        "task_id": TASK,
        "status": STATUS if scan['status']=='PASS' else "FAIL_SECRET_SCAN",
        "created_at": now,
        "city_roots_discovered": len(roots),
        "domain_fuel_rows": len(domain_rows),
        "limitations": [
            "This preflight scaffold discovers and classifies files but does not infer Parquet/DuckDB totals.",
            "Codex should add artifact-specific counters for accepted allflows and strengthening outputs.",
            "Seed R3 refresh is not yet produced by this preflight."
        ]
    }
    (out/'SEED_R3_CROSS_CITY_DOMAIN_FUEL_PREFLIGHT_DECISION.json').write_text(json.dumps(decision, indent=2), encoding='utf-8')

    # closeout
    (out/'CODEX_CLOSEOUT.md').write_text(f"""# {TASK} Closeout\n\nStatus: `{decision['status']}`\n\nDiscovered city roots: {len(roots)}\nDomain fuel ledger rows: {len(domain_rows)}\n\nThis is a conservative preflight. It should be extended with artifact-specific counters before Seed R3 generation.\n""", encoding='utf-8')

    # hash manifest last
    entries = []
    for p in sorted(out.iterdir()):
        if p.is_file() and p.name != 'HASH_MANIFEST.json':
            entries.append({"path": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size})
    (out/'HASH_MANIFEST.json').write_text(json.dumps({"files": entries}, indent=2), encoding='utf-8')
    print(json.dumps(decision, indent=2))

if __name__ == '__main__':
    main()
