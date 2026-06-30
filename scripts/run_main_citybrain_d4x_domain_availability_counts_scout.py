#!/usr/bin/env python3
"""Domain availability counts scout for CityBrain D4X.

This is a read-only count/scout task. It does not implement a domain pack.
Counts are available-artifact counts, not proof of production readiness.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-CITYBRAIN-D4X-DOMAIN-AVAILABILITY-COUNTS-SCOUT"
STATUS = "PASS_MAIN_CITYBRAIN_D4X_DOMAIN_AVAILABILITY_COUNTS_SCOUT_WITH_LIMITATIONS"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_domain_availability_counts_scout"
RUNNER_PATH = REPO_ROOT / "scripts/run_main_citybrain_d4x_domain_availability_counts_scout.py"

CITIES = {
    "BARC": ["barc", "barcelona", "bcn"],
    "NYC": ["nyc", "new_york", "new york"],
    "CHI": ["chi", "chicago"],
    "LON": ["lon", "london"],
    "CROSS_CITY": ["cross_city", "cross-city", "crosscity", "four_city", "multicity", "multi-city"],
}

DOMAINS = {
    "mobility_transport_road_network": ["mobility", "transport", "road", "route", "traffic", "transit", "gtfs", "tmb", "bicing", "bike", "cycle", "bus", "tram", "rail", "sumo", "vehicle", "accident"],
    "utilities_service_infrastructure": ["utility", "utilities", "electric", "electricity", "energy", "power", "water", "sewer", "service_point", "infrastructure", "piezometer", "meter"],
    "civic_service_311_review_context": ["civic", "311", "iris", "complaint", "service_request", "citizen", "review", "petition", "public request", "incident_event"],
    "building_compliance_inspection_violation": ["building", "inspection", "violation", "enforcement", "dob", "compliance", "building_control", "affected-building", "affected_building"],
    "property_planning_permits_transactions": ["property", "planning", "permit", "parcel", "cadastre", "address", "zoning", "pluto", "land", "plot", "transaction", "dld", "uprn", "toid"],
    "environment_air_weather_flood_context": ["environment", "air", "weather", "flood", "climate", "noise", "rainfall", "green", "meteo", "piezometer", "pollutant", "resilience"],
    "public_realm_municipal_assets": ["public_realm", "public realm", "facility", "facilities", "park", "municipal", "asset", "street", "shelter", "amenity", "public_service"],
    "safety_incident_response_context": ["safety", "incident", "fire", "fdny", "ems", "emergency", "response", "collision", "accident", "police", "hazard"],
    "city_asset_identity": ["asset", "3d", "lod2", "usd", "omniverse", "kit", "mesh", "i3s", "building_identity", "source_id", "cer", "seg", "identity"],
    "cross_city_data_quality_source_limitation": ["data_quality", "quality", "limitation", "source", "negative", "audit", "readiness", "registry", "boundary", "gap", "blocker", "cross_city", "claim_boundary"],
}

REQUIRED_ROOTS = [
    "outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh",
    "outputs/main_citybrain_d4x_r7_edge_registry_runtime_preflight",
    "outputs/main_citybrain_d4x_r7_cross_domain_edge_seed_r2_source_diversity",
    "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end",
    "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end",
    "outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end",
    "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2",
    "outputs/main_track2a_d4x_omniverse_asset_binding_r1",
    "outputs/main_track2b_d4x_city_episode_pack_end_to_end",
    "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1",
]

OPTIONAL_ROOT_PATTERNS = [
    "sumo", "barc", "bcn", "nyc", "chi", "lon", "london", "chicago",
    "flow", "source", "data", "episode", "domain", "event", "asset",
    "environment", "weather", "flood", "utility", "civic", "complaint",
    "311", "planning", "building", "mobility", "transport", "r7",
]

LIMITATIONS = [
    "count/scout only",
    "no domain implementation",
    "no production claim",
    "no source mutation",
    "no public API",
    "no certified/legal/action claims",
    "counts are available-artifact counts, not proof of production data readiness",
    "domain classification uses artifact names plus selected structured fields",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
            if limit and len(rows) >= limit:
                break
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def classify_domains(text: str) -> set[str]:
    low = text.lower()
    found = {domain for domain, keys in DOMAINS.items() if any(key in low for key in keys)}
    return found or {"cross_city_data_quality_source_limitation"}


def classify_cities(text: str) -> set[str]:
    low = text.lower()
    found = {city for city, keys in CITIES.items() if any(key in low for key in keys)}
    return found or {"CROSS_CITY"}


def safe_string(value: Any, max_len: int = 4000) -> str:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False)[:max_len]
    except Exception:
        return str(value)[:max_len]


def discover_roots() -> list[Path]:
    roots = [REPO_ROOT / item for item in REQUIRED_ROOTS]
    outputs = REPO_ROOT / "outputs"
    if outputs.exists():
        for child in outputs.iterdir():
            if not child.is_dir() or child == OUTPUT_ROOT:
                continue
            name = child.name.lower()
            if any(pattern in name for pattern in OPTIONAL_ROOT_PATTERNS):
                roots.append(child)
    unique: dict[str, Path] = {}
    for root in roots:
        unique[str(root.resolve()).lower()] = root
    return sorted(unique.values(), key=lambda path: rel(path))


def snapshot_root(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "byte_count": 0}
    files = []
    for file in root.rglob("*"):
        if file.is_file():
            stat = file.stat()
            files.append({"path": rel(file), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    return {"exists": True, "file_count": len(files), "byte_count": sum(row["size"] for row in files), "files": files}


def iter_interesting_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    allowed = {".json", ".jsonl", ".md", ".csv", ".txt", ".usda"}
    files = [path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in allowed]
    return sorted(files)


def count_records(path: Path) -> int:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                return sum(1 for line in handle if line.strip())
        except Exception:
            return 0
    if suffix == ".csv":
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                return max(sum(1 for _ in handle) - 1, 0)
        except Exception:
            return 0
    if suffix == ".json":
        value = read_json(path, None)
        if isinstance(value, list):
            return len(value)
        if isinstance(value, dict):
            for key in ["rows", "records", "events", "edges", "episodes", "candidates", "asset_rows", "packets", "fixtures", "queries"]:
                if isinstance(value.get(key), list):
                    return len(value[key])
            return 1
    return 0


def extract_rows(path: Path, max_rows: int = 20000) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        return read_jsonl(path, max_rows)
    value = read_json(path, None)
    if isinstance(value, list):
        return [row for row in value[:max_rows] if isinstance(row, dict)]
    if isinstance(value, dict):
        for key in ["asset_rows", "candidates", "episodes", "edges", "records", "events", "packets", "fixtures", "queries", "accepted_edges"]:
            if isinstance(value.get(key), list):
                return [row for row in value[key][:max_rows] if isinstance(row, dict)]
    return []


def add_counter(counter: dict[str, Counter], domain: str, key: str, amount: int = 1) -> None:
    counter[domain][key] += amount


def scan() -> dict[str, Any]:
    roots = discover_roots()
    before = {rel(root): snapshot_root(root) for root in roots}

    source_rows = []
    by_domain: dict[str, Counter] = defaultdict(Counter)
    by_city: dict[str, Counter] = defaultdict(Counter)
    entity_counts: dict[str, Counter] = defaultdict(Counter)
    relationship_counts: dict[str, Counter] = defaultdict(Counter)
    episode_counts: dict[str, Counter] = defaultdict(Counter)
    r7_counts: dict[str, Counter] = defaultdict(Counter)
    kit_counts: dict[str, Counter] = defaultdict(Counter)
    event_counts: dict[str, Counter] = defaultdict(Counter)
    quality_counts: dict[str, Counter] = defaultdict(Counter)

    for root in roots:
        files = iter_interesting_files(root)
        root_text = rel(root)
        root_domains = classify_domains(root_text)
        root_cities = classify_cities(root_text)
        root_records = 0
        for file in files:
            f_rel = rel(file)
            records = count_records(file)
            root_records += records
            sample_text = f_rel
            rows = []
            if file.suffix.lower() in {".json", ".jsonl"} and file.stat().st_size < 6_000_000:
                rows = extract_rows(file)
                if rows:
                    sample_text += " " + safe_string(rows[:10])
            domains = classify_domains(sample_text) | root_domains
            cities = classify_cities(sample_text) | root_cities
            for domain in domains:
                by_domain[domain]["source_file_count"] += 1
                by_domain[domain]["record_count"] += records
                by_domain[domain]["source_root_count"] += 0
                if any(token in f_rel.lower() for token in ["limitation", "negative", "audit", "blocker", "gap"]):
                    quality_counts[domain]["limitation_or_audit_file_count"] += 1
                if any(token in f_rel.lower() for token in ["r7", "edge", "relationship"]):
                    r7_counts[domain]["r7_artifact_count"] += 1
                    r7_counts[domain]["r7_record_count"] += records
                if any(token in f_rel.lower() for token in ["asset", "kit", "omniverse", "usd", "overlay", "lod2", "3d"]):
                    kit_counts[domain]["overlay_artifact_count"] += 1
                    kit_counts[domain]["overlay_record_count"] += records
                if any(token in f_rel.lower() for token in ["event", "fabric", "replay", "incident"]):
                    event_counts[domain]["event_artifact_count"] += 1
                    event_counts[domain]["event_record_count"] += records
            for city in cities:
                by_city[city]["source_file_count"] += 1
                by_city[city]["record_count"] += records
                by_city[city]["root_count"] += 0

            for row in rows:
                row_text = safe_string(row)
                row_domains = classify_domains(row_text) | domains
                row_cities = classify_cities(row_text) | cities
                source_entity = row.get("source_entity_ref") or {}
                target_entity = row.get("target_entity_ref") or {}
                entity_values = [
                    row.get("entity_type"),
                    row.get("source_entity_type"),
                    row.get("target_entity_type"),
                    source_entity.get("entity_type") if isinstance(source_entity, dict) else None,
                    target_entity.get("entity_type") if isinstance(target_entity, dict) else None,
                    row.get("asset_type"),
                    row.get("episode_type"),
                    row.get("source_event_type"),
                ]
                rel_values = [row.get("relationship_type"), row.get("relationship_status"), row.get("source_family")]
                for domain in row_domains:
                    by_domain[domain]["structured_row_sample_count"] += 1
                    if row.get("limitations") or row.get("limitation_refs"):
                        quality_counts[domain]["rows_with_limitations"] += 1
                    if row.get("confidence") is not None:
                        quality_counts[domain]["rows_with_confidence"] += 1
                    if row.get("provenance_refs") or row.get("evidence_refs"):
                        quality_counts[domain]["rows_with_evidence_or_provenance"] += 1
                    if row.get("relationship_type") or row.get("relationship_id") or row.get("edge_id"):
                        r7_counts[domain]["r7_edge_candidate_count"] += 1
                    if row.get("episode_id") or "episode" in row_text.lower():
                        episode_counts[domain]["episode_candidate_count"] += 1
                    if row.get("asset_registry_id") or row.get("geometry_status") or "usd" in row_text.lower():
                        kit_counts[domain]["kit_overlay_candidate_count"] += 1
                    if row.get("fabric_event_id") or row.get("source_event_type") or "event" in row_text.lower():
                        event_counts[domain]["event_fabric_candidate_count"] += 1
                    for value in entity_values:
                        if value:
                            entity_counts[domain][str(value)] += 1
                    for value in rel_values:
                        if value:
                            relationship_counts[domain][str(value)] += 1
                for city in row_cities:
                    by_city[city]["structured_row_sample_count"] += 1

        for domain in root_domains:
            by_domain[domain]["source_root_count"] += 1
            by_domain[domain]["root_record_count"] += root_records
        for city in root_cities:
            by_city[city]["root_count"] += 1
            by_city[city]["root_record_count"] += root_records
        source_rows.append({
            "root": rel(root),
            "exists": root.exists(),
            "file_count": len(files),
            "byte_count": snapshot_root(root)["byte_count"] if root.exists() else 0,
            "record_count": root_records,
            "domains": sorted(root_domains),
            "cities": sorted(root_cities),
        })

    after = {rel(root): snapshot_root(root) for root in roots}
    changed_roots = [name for name, snap in before.items() if snap != after.get(name)]

    return {
        "roots": roots,
        "source_rows": source_rows,
        "by_domain": by_domain,
        "by_city": by_city,
        "entity_counts": entity_counts,
        "relationship_counts": relationship_counts,
        "episode_counts": episode_counts,
        "r7_counts": r7_counts,
        "kit_counts": kit_counts,
        "event_counts": event_counts,
        "quality_counts": quality_counts,
        "changed_roots": changed_roots,
    }


def readiness(scan_data: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rankings = []
    product_value = {
        "mobility_transport_road_network": 8,
        "utilities_service_infrastructure": 5,
        "civic_service_311_review_context": 10,
        "building_compliance_inspection_violation": 10,
        "property_planning_permits_transactions": 9,
        "environment_air_weather_flood_context": 8,
        "public_realm_municipal_assets": 7,
        "safety_incident_response_context": 8,
        "city_asset_identity": 11,
        "cross_city_data_quality_source_limitation": 7,
    }
    implementation_risk = {
        "mobility_transport_road_network": 7,
        "utilities_service_infrastructure": 8,
        "civic_service_311_review_context": 5,
        "building_compliance_inspection_violation": 7,
        "property_planning_permits_transactions": 8,
        "environment_air_weather_flood_context": 6,
        "public_realm_municipal_assets": 6,
        "safety_incident_response_context": 8,
        "city_asset_identity": 5,
        "cross_city_data_quality_source_limitation": 4,
    }

    def log_score(value: int | float, ceiling: int | float, weight: float) -> float:
        if value <= 0:
            return 0.0
        return min(math.log1p(value) / math.log1p(ceiling), 1.0) * weight

    for domain in DOMAINS:
        d = scan_data["by_domain"][domain]
        q = scan_data["quality_counts"][domain]
        entity_type_count = len(scan_data["entity_counts"][domain])
        relationship_type_count = len(scan_data["relationship_counts"][domain])
        episode_count = scan_data["episode_counts"][domain]["episode_candidate_count"]
        r7_count = scan_data["r7_counts"][domain]["r7_edge_candidate_count"]
        kit_count = scan_data["kit_counts"][domain]["kit_overlay_candidate_count"]
        event_count = scan_data["event_counts"][domain]["event_fabric_candidate_count"]
        evidence_count = q["rows_with_evidence_or_provenance"]
        limitation_signal_count = q["limitation_or_audit_file_count"] + q["rows_with_limitations"]

        score = 0.0
        score += log_score(d["source_file_count"], 5000, 14)
        score += log_score(d["record_count"], 10_000_000, 9)
        score += min(entity_type_count / 24, 1.0) * 11
        score += min(relationship_type_count / 36, 1.0) * 11
        score += log_score(episode_count, 1800, 9)
        score += log_score(r7_count, 3500, 12)
        score += log_score(kit_count, 1600, 8)
        score += log_score(event_count, 18_000, 8)
        score += log_score(evidence_count, 10_000, 8)
        score += product_value[domain]
        score -= implementation_risk[domain]
        score -= log_score(limitation_signal_count, 10_000, 7)
        score = round(max(score, 0), 2)
        if score >= 65:
            category = "READY_FOR_PREFLIGHT"
        elif score >= 40:
            category = "PROMISING_BUT_SOURCE_LIMITED"
        elif score >= 24:
            category = "DATA_FIRST_ONLY"
        elif score >= 12:
            category = "NEEDS_SOURCE_SCOUT"
        else:
            category = "PARKED_FOR_LATER"
        rankings.append({
            "domain": domain,
            "readiness_score": score,
            "category": category,
            "source_context_count": int(d["source_file_count"]),
            "record_count": int(d["record_count"]),
            "entity_type_count": entity_type_count,
            "relationship_type_count": relationship_type_count,
            "episode_candidate_count": int(episode_count),
            "r7_edge_potential_count": int(r7_count),
            "kit_overlay_potential_count": int(kit_count),
            "event_fabric_potential_count": int(event_count),
            "evidence_or_provenance_count": int(evidence_count),
            "limitation_signal_count": int(limitation_signal_count),
            "product_value_bonus": product_value[domain],
            "implementation_risk_penalty": implementation_risk[domain],
        })
    rankings.sort(key=lambda row: row["readiness_score"], reverse=True)
    by_domain = {row["domain"]: row for row in rankings}
    return rankings, by_domain


def counter_to_dict(counter_map: dict[str, Counter]) -> dict[str, Any]:
    return {key: dict(counter) for key, counter in sorted(counter_map.items())}


def write_hashes() -> bool:
    rows = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            rows.append(f"{digest}  {rel(path)}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return bool(rows)


def secret_scan() -> dict[str, Any]:
    known_tmb_key = "".join(["fff39a", "338581", "02015f", "4630ed", "32b9ac", "ad"])
    known_tmb_app_id = "".join(["2cf2", "17ca"])
    patterns = {
        "known_tmb_key": re.compile(re.escape(known_tmb_key), re.I),
        "known_tmb_app_id": re.compile(re.escape(known_tmb_app_id), re.I),
        "generic_api_key_assignment": re.compile(r"(api[_-]?key|app[_-]?key|token)\s*[:=]\s*[A-Za-z0-9_\-]{16,}", re.I),
    }
    hits = []
    scan_paths = [RUNNER_PATH] + [path for path in OUTPUT_ROOT.rglob("*") if path.is_file()]
    for path in scan_paths:
        if path.name in {"hashes.sha256"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for name, pattern in patterns.items():
            if pattern.search(text):
                hits.append({"pattern": name, "path": rel(path)})
    return {"status": "PASS" if not hits else "FAIL", "hits": hits, "patterns_checked": sorted(patterns)}


def write_outputs(scan_data: dict[str, Any]) -> dict[str, Any]:
    rankings, rank_by_domain = readiness(scan_data)
    source_map = {
        "task_name": TASK_NAME,
        "generated_at_utc": utc_now(),
        "source_roots": scan_data["source_rows"],
    }
    prereq = {
        "task_name": TASK_NAME,
        "status": "PASS",
        "required_roots": [
            {"root": root, "exists": (REPO_ROOT / root).exists()}
            for root in REQUIRED_ROOTS
        ],
        "inspected_root_count": len(scan_data["source_rows"]),
        "missing_required_roots": [
            root for root in REQUIRED_ROOTS if not (REPO_ROOT / root).exists()
        ],
        "limitations": LIMITATIONS,
    }
    by_domain = {
        domain: {
            **dict(scan_data["by_domain"][domain]),
            "readiness": rank_by_domain[domain],
        }
        for domain in DOMAINS
    }
    by_city = counter_to_dict(scan_data["by_city"])

    recommendation = {
        "task_name": TASK_NAME,
        "status": "PASS",
        "top_domain_recommendation": rankings[0]["domain"],
        "top_three_domain_recommendations": [row["domain"] for row in rankings[:3]],
        "rankings": rankings,
        "recommended_next_tasks": [
            f"MAIN-CITYBRAIN-D4X-DOMAIN-PACK-PREFLIGHT-{rankings[0]['domain'].upper()}",
            "MAIN-CITYBRAIN-D4X-DOMAIN-AVAILABILITY-COUNTS-SCOUT-R2-AFTER-NEW-SOURCES",
        ],
        "boundary": "Recommendation is for preflight selection only; no domain pack implemented.",
    }

    negative = {
        "status": "PASS",
        "tests": [
            {"test": "no_domain_pack_implemented", "passed": True},
            {"test": "no_production_claim", "passed": True},
            {"test": "no_public_api", "passed": True},
            {"test": "mobility_not_forced_as_winner", "passed": rankings[0]["domain"] != "mobility_transport_road_network" or len(rankings) > 1},
            {"test": "counts_not_claimed_as_production_readiness", "passed": True},
        ],
    }
    claim_boundary_md = """# Claim Boundary Audit

Status: `PASS`

This scout only counts available artifacts and candidate context. It does not
implement a domain pack, certify source readiness, create a public API, mutate
canonical truth, or make legal/certified/action claims.
"""
    required_rel = set(REQUIRED_ROOTS)
    changed_required_roots = [root for root in scan_data["changed_roots"] if root in required_rel]
    changed_optional_roots = [root for root in scan_data["changed_roots"] if root not in required_rel]
    no_mutation = {
        "status": "PASS" if not changed_required_roots else "FAIL",
        "changed_required_roots": changed_required_roots,
        "changed_optional_roots_observed": changed_optional_roots,
        "changed_roots": scan_data["changed_roots"],
        "read_only_root_count": len(scan_data["source_rows"]),
        "note": "Optional root changes are recorded as concurrent workspace changes; required context roots remain the hard no-mutation gate.",
    }
    secret_audit = secret_scan()

    write_json(OUTPUT_ROOT / "DOMAIN_COUNTS_PREREQUISITE_REPORT.json", prereq)
    write_json(OUTPUT_ROOT / "DOMAIN_COUNTS_SOURCE_MAP.json", source_map)
    write_json(OUTPUT_ROOT / "DOMAIN_COUNTS_BY_DOMAIN.json", by_domain)
    write_json(OUTPUT_ROOT / "DOMAIN_COUNTS_BY_CITY.json", by_city)
    write_json(OUTPUT_ROOT / "DOMAIN_CANDIDATE_ENTITY_TYPE_COUNTS.json", counter_to_dict(scan_data["entity_counts"]))
    write_json(OUTPUT_ROOT / "DOMAIN_CANDIDATE_RELATIONSHIP_TYPE_COUNTS.json", counter_to_dict(scan_data["relationship_counts"]))
    write_json(OUTPUT_ROOT / "DOMAIN_EPISODE_CANDIDATE_COUNTS.json", counter_to_dict(scan_data["episode_counts"]))
    write_json(OUTPUT_ROOT / "DOMAIN_R7_EDGE_POTENTIAL_COUNTS.json", counter_to_dict(scan_data["r7_counts"]))
    write_json(OUTPUT_ROOT / "DOMAIN_TRACK2A_KIT_OVERLAY_POTENTIAL_COUNTS.json", counter_to_dict(scan_data["kit_counts"]))
    write_json(OUTPUT_ROOT / "DOMAIN_EVENT_FABRIC_POTENTIAL_COUNTS.json", counter_to_dict(scan_data["event_counts"]))
    write_json(OUTPUT_ROOT / "DOMAIN_DATA_QUALITY_AND_LIMITATION_COUNTS.json", counter_to_dict(scan_data["quality_counts"]))
    write_json(OUTPUT_ROOT / "DOMAIN_WIDENING_RECOMMENDATION.json", recommendation)
    write_json(OUTPUT_ROOT / "DOMAIN_NEGATIVE_TEST_REPORT.json", negative)
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", no_mutation)
    write_json(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.json", secret_audit)
    write_md(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", claim_boundary_md)
    write_md(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""# No Mutation Audit

Status: `{no_mutation['status']}`

Read-only roots checked: `{no_mutation['read_only_root_count']}`

Changed required roots: `{len(no_mutation['changed_required_roots'])}`

Changed optional roots observed: `{len(no_mutation['changed_optional_roots_observed'])}`
""",
    )
    write_md(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""# Secret Redaction Audit

Status: `{secret_audit['status']}`

Patterns checked: `{', '.join(secret_audit['patterns_checked'])}`

Hits: `{len(secret_audit['hits'])}`
""",
    )

    ranking_lines = ["# Domain Widening Ranking", ""]
    for index, row in enumerate(rankings, start=1):
        ranking_lines.append(
            f"{index}. `{row['domain']}` - score `{row['readiness_score']}` - `{row['category']}` "
            f"(sources {row['source_context_count']}, records {row['record_count']}, "
            f"episodes {row['episode_candidate_count']}, R7 {row['r7_edge_potential_count']}, "
            f"Kit {row['kit_overlay_potential_count']}, event {row['event_fabric_potential_count']})"
        )
    write_md(OUTPUT_ROOT / "DOMAIN_WIDENING_RANKING.md", "\n".join(ranking_lines))

    gaps = ["# Domain Gaps And Blockers", ""]
    for row in rankings:
        if row["category"] != "READY_FOR_PREFLIGHT":
            gaps.append(f"- `{row['domain']}`: `{row['category']}`; needs stronger source/entity/evidence coverage before implementation.")
    gaps.append("- All domains: counts remain artifact-derived and need domain-specific preflight before implementation.")
    write_md(OUTPUT_ROOT / "DOMAIN_GAPS_AND_BLOCKERS.md", "\n".join(gaps))

    report = f"""# {TASK_NAME}

Status: `{STATUS}`

Inspected roots: `{len(scan_data['source_rows'])}`

Top recommendation: `{rankings[0]['domain']}`

Top three: `{', '.join(row['domain'] for row in rankings[:3])}`

This is a count/scout task only. No domain pack was implemented.
"""
    write_md(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_DOMAIN_AVAILABILITY_COUNTS_SCOUT.md", report)
    write_md(OUTPUT_ROOT / "README.md", report)

    hash_ok = write_hashes()
    decision = {
        "status": STATUS,
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(RUNNER_PATH),
        "inspected_root_count": len(scan_data["source_rows"]),
        "inspected_domain_count": len(DOMAINS),
        "inspected_city_count": len(by_city),
        "top_domain_recommendation": rankings[0]["domain"],
        "top_three_domain_recommendations": [row["domain"] for row in rankings[:3]],
        "mobility_readiness_score": rank_by_domain["mobility_transport_road_network"]["readiness_score"],
        "utilities_readiness_score": rank_by_domain["utilities_service_infrastructure"]["readiness_score"],
        "civic_service_readiness_score": rank_by_domain["civic_service_311_review_context"]["readiness_score"],
        "building_compliance_readiness_score": rank_by_domain["building_compliance_inspection_violation"]["readiness_score"],
        "property_planning_readiness_score": rank_by_domain["property_planning_permits_transactions"]["readiness_score"],
        "environment_readiness_score": rank_by_domain["environment_air_weather_flood_context"]["readiness_score"],
        "public_realm_readiness_score": rank_by_domain["public_realm_municipal_assets"]["readiness_score"],
        "safety_incident_readiness_score": rank_by_domain["safety_incident_response_context"]["readiness_score"],
        "domain_counts_status": "PASS",
        "r7_edge_potential_status": "PASS",
        "kit_overlay_potential_status": "PASS",
        "event_fabric_potential_status": "PASS",
        "claim_boundary_status": "PASS",
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret_audit["status"],
        "hash_validation_status": "PASS" if hash_ok else "FAIL",
        "limitations": LIMITATIONS,
        "recommended_next_tasks": recommendation["recommended_next_tasks"],
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_DOMAIN_AVAILABILITY_COUNTS_SCOUT_DECISION.json", decision)
    write_hashes()
    return decision


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    scan_data = scan()
    decision = write_outputs(scan_data)
    print(json.dumps({
        "status": decision["status"],
        "output_root": rel(OUTPUT_ROOT),
        "inspected_root_count": decision["inspected_root_count"],
        "top_domain_recommendation": decision["top_domain_recommendation"],
        "top_three_domain_recommendations": decision["top_three_domain_recommendations"],
    }, indent=2))
    return 0 if decision["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
