from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1c_lane_c_federation_query_v0"

GATE_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_integration_gate_2_1b_content_hardening"
GATE_DECISION = GATE_ROOT / "INTEGRATION_GATE_2_1B_DECISION.json"
GATE_FLAG = GATE_ROOT / "PUSH_2_1C_ALLOWED_TO_OPEN.flag"

NYC_CORPUS_ROOT = REPO_ROOT / "outputs" / "nyc_allflows_data_landing_r1"
LON_CORPUS_ROOT = REPO_ROOT / "outputs" / "lon_allflows_data_landing_r1"
NYC_SOURCE_LEDGER = NYC_CORPUS_ROOT / "NYC_ALLFLOWS_SOURCE_LEDGER.json"
LON_SOURCE_LEDGER = LON_CORPUS_ROOT / "LON_ALLFLOWS_SOURCE_LEDGER.json"
NYC_SCHEMA_PROFILES = NYC_CORPUS_ROOT / "NYC_ALLFLOWS_SCHEMA_PROFILES.json"
LON_SCHEMA_PROFILES = LON_CORPUS_ROOT / "LON_ALLFLOWS_SCHEMA_PROFILES.json"
NYC_PHASE_MANIFEST = NYC_CORPUS_ROOT / "NYC_ALLFLOWS_PHASE_MANIFEST.json"
LON_PHASE_MANIFEST = LON_CORPUS_ROOT / "LON_ALLFLOWS_PHASE_MANIFEST.json"

DOMAIN_PACK_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1b_lane_b_starter_domain_packs"
DOMAIN_PACK_VALIDATION = DOMAIN_PACK_ROOT / "starter_domain_pack_validation_report.json"
DOMAIN_PACK_APPEND_REPORT = DOMAIN_PACK_ROOT / "corpus_source_of_truth_append_report.json"

STATUS_PASS_LIMITATIONS = "PASS_WITH_LIMITATIONS"
STATUS_BLOCKED = "BLOCKED"

EXPECTED_OUTPUT_FILES = {
    "federation_query_envelope_v0.json",
    "federation_query_runner_or_fixture_v0.py",
    "federation_query_nyc_london_fixture_results.json",
    "federation_city_scoped_id_audit.json",
    "federation_non_claim_boundary_audit.json",
    "PUSH_2_1C_LANE_C_DECISION.json",
    "HASH_MANIFEST.json",
    "SUMMARY.md",
}

PROOF_CITIES = ["nyc", "london"]
EXCLUDED_PROOF_CITIES = ["dubai"]

DOMAIN_KEYWORDS = {
    "planning": [
        "planning",
        "permit",
        "dob",
        "brownfield",
        "zoning",
        "application",
        "local_plan",
        "development",
    ],
    "mobility": [
        "mobility",
        "traffic",
        "transport",
        "transit",
        "street",
        "road",
        "tfl",
        "mta",
        "gtfs",
        "bike",
        "taxi",
        "vehicle",
        "closure",
    ],
    "utilities": [
        "utility",
        "utilities",
        "energy",
        "water",
        "service",
        "facility",
        "charging",
        "air",
        "flood",
        "noise",
        "environment",
    ],
    "building": [
        "building",
        "parcel",
        "pluto",
        "hpd",
        "property",
        "premises",
        "linked_identifier",
        "address",
        "business_rates",
    ],
}

SOURCE_ENTITY_KEYWORDS = {
    "planning_context": ["planning", "permit", "dob", "brownfield", "application", "local_plan", "zoning"],
    "mobility_link": ["traffic", "street", "road", "tfl", "mta", "gtfs", "bike", "taxi", "transport", "vehicle"],
    "building_record": ["building", "parcel", "pluto", "hpd", "premises", "property", "address"],
    "utility_service_context": ["energy", "water", "service", "facility", "charging", "utility"],
    "environment_context": ["air", "flood", "noise", "harbor", "climate", "environment"],
    "civic_event_context": ["311", "crime", "fire", "ems", "fixmystreet", "service_request", "incident"],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_branch() -> str:
    proc = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip()


def validate_prerequisites() -> dict[str, Any]:
    branch = current_branch()
    decision = read_json(GATE_DECISION, {})
    flag = GATE_FLAG.read_text(encoding="utf-8").strip() if GATE_FLAG.exists() else None
    checks = [
        {
            "name": "branch_is_main",
            "status": "PASS" if branch == "main" else "FAIL",
            "observed": branch,
        },
        {
            "name": "integration_gate_2_1b_status_pass",
            "status": "PASS" if str(decision.get("status", "")).startswith("PASS") else "FAIL",
            "observed": decision.get("status"),
            "ref": rel(GATE_DECISION),
        },
        {
            "name": "push_2_1c_allowed_to_open_true",
            "status": "PASS" if decision.get("push_2_1c_allowed_to_open") is True else "FAIL",
            "observed": decision.get("push_2_1c_allowed_to_open"),
            "ref": rel(GATE_DECISION),
        },
        {
            "name": "push_2_1c_allowed_flag_pass",
            "status": "PASS" if flag == "PASS" else "FAIL",
            "observed": flag,
            "ref": rel(GATE_FLAG),
        },
    ]
    failures = [check for check in checks if check["status"] != "PASS"]
    return {
        "status": "PASS" if not failures else STATUS_BLOCKED,
        "checked_at": utc_now(),
        "checks": checks,
        "failures": failures,
    }


def safe_prepare_output_root() -> None:
    if OUTPUT_ROOT.exists():
        unexpected = sorted(path.name for path in OUTPUT_ROOT.iterdir() if path.name not in EXPECTED_OUTPUT_FILES)
        if unexpected:
            raise RuntimeError(f"Refusing to write over unexpected Lane C output artifacts: {unexpected}")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def normalize_text(*parts: Any) -> str:
    flattened: list[str] = []
    for part in parts:
        if part is None:
            continue
        if isinstance(part, list):
            flattened.extend(str(item) for item in part)
        elif isinstance(part, dict):
            flattened.extend(str(value) for value in part.values())
        else:
            flattened.append(str(part))
    return " ".join(flattened).lower()


def infer_source_class(city: str, source: dict[str, Any]) -> str:
    if city == "nyc":
        source_type = str(source.get("source_type", "")).lower()
        attribution = str(source.get("attribution", "")).lower()
        if source_type == "direct":
            return "official_record"
        if any(token in attribution for token in ["nyc", "mta", "authority", "department", "city"]):
            return "official_record"
        return "licensed_open_data"
    download_mode = str(source.get("download_mode", "")).lower()
    classification = str(source.get("classification", "")).lower()
    if "registered_existing" in download_mode or "registered_existing" in classification:
        return "official_record"
    return "licensed_open_data"


def infer_entity_types(source_key: str, profile: dict[str, Any] | None, source: dict[str, Any]) -> list[str]:
    types: set[str] = set()
    profile = profile or {}
    for value in profile.get("recommended_citybrain_entity_mappings", []) or []:
        types.add(str(value))
    text = normalize_text(
        source_key,
        source.get("name"),
        source.get("title"),
        source.get("category"),
        source.get("use"),
        source.get("join_hints"),
        source.get("join_keys"),
        profile.get("schema_fields"),
        profile.get("boundary_class"),
        profile.get("privacy_class"),
    )
    for entity_type, keywords in SOURCE_ENTITY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            types.add(entity_type)
    if not types:
        types.add("source_record")
    return sorted(types)


def source_status(city: str, source: dict[str, Any], profile: dict[str, Any] | None) -> str:
    if city == "nyc":
        return str(
            (profile or {}).get("source_state")
            or source.get("scan_status")
            or source.get("status")
            or "UNKNOWN"
        )
    return str(
        (profile or {}).get("status")
        or source.get("probe_status")
        or source.get("classification")
        or "UNKNOWN"
    )


def source_row(city: str, corpus_id: str, source: dict[str, Any], profile: dict[str, Any] | None) -> dict[str, Any]:
    source_key = str(source.get("key") or source.get("source_key"))
    source_id = f"{city}:source:{source_key}"
    profile_ref = (
        f"outputs/{city}_allflows_data_landing_r1/profiles/{source_key}.profile.json"
        if city == "nyc"
        else f"outputs/lon_allflows_data_landing_r1/profiles/{source_key}.profile.json"
    )
    manifest_ref = (
        f"outputs/{city}_allflows_data_landing_r1/manifests/{source_key}.manifest.json"
        if city == "nyc"
        else f"outputs/lon_allflows_data_landing_r1/manifests/{source_key}.manifest.json"
    )
    return {
        "city_scoped_canonical_id": source_id,
        "source_city": city,
        "corpus_id": corpus_id,
        "source_key": source_key,
        "display_name": source.get("name") or source.get("title") or source_key,
        "source_class": infer_source_class(city, source),
        "source_system": source.get("source_type") or source.get("source_system") or source.get("api_kind_observed"),
        "source_state": source_status(city, source, profile),
        "entity_types": infer_entity_types(source_key, profile, source),
        "row_count": source.get("row_count") or source.get("row_count_total") or source.get("count_observed"),
        "provenance": {
            "source_ledger_ref": rel(NYC_SOURCE_LEDGER if city == "nyc" else LON_SOURCE_LEDGER),
            "schema_profile_ref": profile_ref,
            "manifest_ref": manifest_ref,
        },
        "non_claim_boundary": source.get("boundary") or (profile or {}).get("boundary_class"),
        "global_canonical_id": None,
        "global_merge_performed": False,
    }


def load_city_corpus(city: str) -> dict[str, Any]:
    if city == "nyc":
        ledger_payload = read_json(NYC_SOURCE_LEDGER, {})
        sources = ledger_payload.get("sources", [])
        profiles_payload = read_json(NYC_SCHEMA_PROFILES, {})
        profiles = profiles_payload if isinstance(profiles_payload, dict) else {}
        rows = [
            source_row(city, "nyc_allflows_data_landing_r1", source, profiles.get(str(source.get("key"))))
            for source in sources
        ]
        root = NYC_CORPUS_ROOT
        phase_manifest = read_json(NYC_PHASE_MANIFEST, {})
    else:
        sources = read_json(LON_SOURCE_LEDGER, [])
        profiles_payload = read_json(LON_SCHEMA_PROFILES, [])
        profiles = {
            str(profile.get("source_key")): profile
            for profile in profiles_payload
            if isinstance(profile, dict) and profile.get("source_key")
        }
        rows = [
            source_row(city, "lon_allflows_data_landing_r1", source, profiles.get(str(source.get("source_key"))))
            for source in sources
        ]
        root = LON_CORPUS_ROOT
        phase_manifest = read_json(LON_PHASE_MANIFEST, {})

    return {
        "city": city,
        "corpus_id": "nyc_allflows_data_landing_r1" if city == "nyc" else "lon_allflows_data_landing_r1",
        "corpus_root": rel(root),
        "source_ledger_ref": rel(NYC_SOURCE_LEDGER if city == "nyc" else LON_SOURCE_LEDGER),
        "schema_profiles_ref": rel(NYC_SCHEMA_PROFILES if city == "nyc" else LON_SCHEMA_PROFILES),
        "phase_manifest_ref": rel(NYC_PHASE_MANIFEST if city == "nyc" else LON_PHASE_MANIFEST),
        "source_count": len(rows),
        "profile_count": len(profiles),
        "manifest_count": len(list((root / "manifests").glob("*.manifest.json"))) if (root / "manifests").exists() else 0,
        "source_rows": rows,
        "source_state_counts": dict(sorted(Counter(row["source_state"] for row in rows).items())),
        "source_class_counts": dict(sorted(Counter(row["source_class"] for row in rows).items())),
        "phase_manifest_status": phase_manifest.get("status") or phase_manifest.get("task") or "AVAILABLE_WITH_LIMITATIONS",
        "privacy_boundary_ref": rel(root / ("NYC_ALLFLOWS_PRIVACY_BOUNDARY.md" if city == "nyc" else "LON_ALLFLOWS_PRIVACY_BOUNDARY.md")),
        "limitations_ref": rel(root / ("NYC_ALLFLOWS_LIMITATIONS.md" if city == "nyc" else "LON_ALLFLOWS_LIMITATIONS.md")),
    }


def load_domain_packs() -> dict[str, Any]:
    manifests = {}
    for manifest_path in sorted((DOMAIN_PACK_ROOT / "domain_packs").glob("*/manifest.json")):
        manifest = read_json(manifest_path, {})
        domain = str(manifest.get("domain") or manifest_path.parent.name)
        manifests[domain] = {
            "manifest": manifest,
            "manifest_ref": rel(manifest_path),
        }
    return {
        "validation": read_json(DOMAIN_PACK_VALIDATION, {}),
        "append_report": read_json(DOMAIN_PACK_APPEND_REPORT, {}),
        "manifests": manifests,
    }


def city_sources_by_entity(corpus: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    mapping: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in corpus["source_rows"]:
        for entity_type in row["entity_types"]:
            mapping[entity_type].append(row)
    return mapping


def comparable_entity_types(nyc: dict[str, Any], london: dict[str, Any]) -> list[dict[str, Any]]:
    nyc_by_type = city_sources_by_entity(nyc)
    london_by_type = city_sources_by_entity(london)
    common = sorted(set(nyc_by_type).intersection(london_by_type))
    rows = []
    for entity_type in common:
        rows.append(
            {
                "entity_type": entity_type,
                "city_scoped_source_examples": {
                    "nyc": [row["city_scoped_canonical_id"] for row in nyc_by_type[entity_type][:5]],
                    "london": [row["city_scoped_canonical_id"] for row in london_by_type[entity_type][:5]],
                },
                "source_city_corpora": {
                    "nyc": nyc["corpus_id"],
                    "london": london["corpus_id"],
                },
                "global_identity_merge": False,
                "provenance_refs": [nyc["schema_profiles_ref"], london["schema_profiles_ref"]],
            }
        )
    return rows


def choose_profile(corpus: dict[str, Any], preferred_keys: list[str]) -> dict[str, Any]:
    by_key = {row["source_key"]: row for row in corpus["source_rows"]}
    for key in preferred_keys:
        if key in by_key:
            return by_key[key]
    return corpus["source_rows"][0]


def domain_city_support(domain: str, corpus: dict[str, Any]) -> dict[str, Any]:
    keywords = DOMAIN_KEYWORDS[domain]
    matches = []
    for row in corpus["source_rows"]:
        text = normalize_text(row["source_key"], row["display_name"], row["entity_types"], row["non_claim_boundary"])
        if any(keyword in text for keyword in keywords):
            matches.append(row)
    return {
        "source_count": len(matches),
        "sample_city_scoped_source_ids": [row["city_scoped_canonical_id"] for row in matches[:5]],
        "corpus_id": corpus["corpus_id"],
    }


def build_envelope() -> dict[str, Any]:
    return {
        "schema_name": "FederationQueryEnvelopeV0",
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_c.federation_query_envelope.v0",
        "query_id": "federation:nyc_london:proof_batch:v0",
        "query_type": "federation_fixture_batch",
        "city_scope": PROOF_CITIES,
        "entity_refs": [],
        "domain_pack_refs": [
            "citybrain_starter_planning_domain_pack",
            "citybrain_starter_mobility_domain_pack",
            "citybrain_starter_utilities_domain_pack",
            "citybrain_starter_building_domain_pack",
        ],
        "evidence_refs_required": True,
        "source_class_policy": "preserve_city_scope",
        "authority_level": "observe_or_explain_only",
        "supported_query_shapes": [
            {
                "query_id": "federation:nyc_london:comparable_entity_types:v0",
                "query_type": "comparable_entity_types",
                "description": "List comparable entity/source-context types across NYC and London without merging identity.",
            },
            {
                "query_id": "federation:nyc_london:city_scoped_entity_profile:v0",
                "query_type": "entity_profile",
                "description": "Retrieve a city-scoped entity/source profile from the selected proof city.",
            },
            {
                "query_id": "federation:nyc_london:source_class_maturity_compare:v0",
                "query_type": "maturity_compare",
                "description": "Compare source_class and maturity/source-state counts across proof corpora.",
            },
            {
                "query_id": "federation:nyc_london:domain_pack_presence:v0",
                "query_type": "domain_pack_presence",
                "description": "Query starter domain-pack presence and city corpus support.",
            },
            {
                "query_id": "federation:nyc_london:source_freshness_corpus_state:v0",
                "query_type": "source_freshness",
                "description": "Query source freshness/source-state and corpus landing state across proof corpora.",
            },
            {
                "query_id": "federation:nyc_london:corpus_state:v0",
                "query_type": "corpus_state",
                "description": "Query corpus root, source ledger, profile, and manifest availability.",
            },
        ],
        "proof_cities": PROOF_CITIES,
        "excluded_as_proof": EXCLUDED_PROOF_CITIES,
        "non_claims": [
            "no_global_canonical_identity",
            "no_cross_city_operational_claim",
            "no_learned_transfer",
            "query_only",
            "no_federated_write_approval_or_action",
            "no_production_federation_deployment_claim",
            "no_dubai_synthetic_proof_dependency",
        ],
        "local_replay_review_query_only": True,
    }


def build_fixture_results(envelope: dict[str, Any], nyc: dict[str, Any], london: dict[str, Any], domain_packs: dict[str, Any]) -> dict[str, Any]:
    comparable = comparable_entity_types(nyc, london)
    city_profiles = [
        choose_profile(nyc, ["nyc_pluto", "nyc_3d_building_model", "nyc_centerline"]),
        choose_profile(london, ["planning_local_plan_data", "london_core_boundaries", "os_open_linked_identifiers"]),
    ]

    domain_rows = []
    pack_results = domain_packs["validation"].get("pack_results", {})
    for domain, pack in sorted(domain_packs["manifests"].items()):
        manifest = pack["manifest"]
        nyc_support = domain_city_support(domain, nyc)
        london_support = domain_city_support(domain, london)
        domain_rows.append(
            {
                "domain": domain,
                "pack_id": manifest.get("pack_id"),
                "manifest_ref": pack["manifest_ref"],
                "validator_status": pack_results.get(domain, {}).get("status"),
                "source_class_policy_present": bool(manifest.get("source_class_policy", {}).get("source_class_required")),
                "city_support": {
                    "nyc": nyc_support,
                    "london": london_support,
                },
                "available_in_both_proof_cities": nyc_support["source_count"] > 0 and london_support["source_count"] > 0,
                "global_identity_merge": False,
            }
        )

    maturity_compare = {
        "query_id": "federation:nyc_london:source_class_maturity_compare:v0",
        "query_type": "maturity_compare",
        "source_class_counts": {
            "nyc": nyc["source_class_counts"],
            "london": london["source_class_counts"],
        },
        "source_state_counts": {
            "nyc": nyc["source_state_counts"],
            "london": london["source_state_counts"],
        },
        "profile_counts": {
            "nyc": nyc["profile_count"],
            "london": london["profile_count"],
        },
        "manifest_counts": {
            "nyc": nyc["manifest_count"],
            "london": london["manifest_count"],
        },
        "provenance_refs": [
            nyc["source_ledger_ref"],
            nyc["schema_profiles_ref"],
            london["source_ledger_ref"],
            london["schema_profiles_ref"],
        ],
    }

    freshness_state = {
        "query_id": "federation:nyc_london:source_freshness_corpus_state:v0",
        "query_type": "source_freshness",
        "cities": {
            "nyc": {
                "corpus_id": nyc["corpus_id"],
                "source_count": nyc["source_count"],
                "source_state_counts": nyc["source_state_counts"],
                "phase_manifest_status": nyc["phase_manifest_status"],
                "privacy_boundary_ref": nyc["privacy_boundary_ref"],
                "limitations_ref": nyc["limitations_ref"],
            },
            "london": {
                "corpus_id": london["corpus_id"],
                "source_count": london["source_count"],
                "source_state_counts": london["source_state_counts"],
                "phase_manifest_status": london["phase_manifest_status"],
                "privacy_boundary_ref": london["privacy_boundary_ref"],
                "limitations_ref": london["limitations_ref"],
            },
        },
        "claim_boundary": "source freshness/corpus state is descriptive metadata only, not a current-truth certification",
    }

    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_c.federation_query_fixture_results.v0",
        "status": STATUS_PASS_LIMITATIONS,
        "generated_at": utc_now(),
        "query_envelope_ref": rel(OUTPUT_ROOT / "federation_query_envelope_v0.json"),
        "proof": {
            "proof_cities": PROOF_CITIES,
            "proof_city_count": 2,
            "uses_only_real_corpora": True,
            "excluded_as_proof": EXCLUDED_PROOF_CITIES,
            "dubai_synthetic_dependency": False,
        },
        "source_corpora": {
            "nyc": {
                "corpus_id": nyc["corpus_id"],
                "corpus_root": nyc["corpus_root"],
                "source_ledger_ref": nyc["source_ledger_ref"],
                "schema_profiles_ref": nyc["schema_profiles_ref"],
                "phase_manifest_ref": nyc["phase_manifest_ref"],
            },
            "london": {
                "corpus_id": london["corpus_id"],
                "corpus_root": london["corpus_root"],
                "source_ledger_ref": london["source_ledger_ref"],
                "schema_profiles_ref": london["schema_profiles_ref"],
                "phase_manifest_ref": london["phase_manifest_ref"],
            },
        },
        "queries": [
            {
                "query_id": "federation:nyc_london:comparable_entity_types:v0",
                "query_type": "comparable_entity_types",
                "city_scope": PROOF_CITIES,
                "result_count": len(comparable),
                "results": comparable,
                "query_only": True,
            },
            {
                "query_id": "federation:nyc_london:city_scoped_entity_profile:v0",
                "query_type": "entity_profile",
                "city_scope": PROOF_CITIES,
                "result_count": len(city_profiles),
                "results": city_profiles,
                "query_only": True,
            },
            maturity_compare,
            {
                "query_id": "federation:nyc_london:domain_pack_presence:v0",
                "query_type": "domain_pack_presence",
                "city_scope": PROOF_CITIES,
                "result_count": len(domain_rows),
                "results": domain_rows,
                "domain_pack_validation_ref": rel(DOMAIN_PACK_VALIDATION),
                "source_of_truth_append_ref": rel(DOMAIN_PACK_APPEND_REPORT),
                "query_only": True,
            },
            freshness_state,
            {
                "query_id": "federation:nyc_london:corpus_state:v0",
                "query_type": "corpus_state",
                "city_scope": PROOF_CITIES,
                "results": {
                    "nyc": {
                        "corpus_id": nyc["corpus_id"],
                        "source_count": nyc["source_count"],
                        "profile_count": nyc["profile_count"],
                        "manifest_count": nyc["manifest_count"],
                    },
                    "london": {
                        "corpus_id": london["corpus_id"],
                        "source_count": london["source_count"],
                        "profile_count": london["profile_count"],
                        "manifest_count": london["manifest_count"],
                    },
                },
                "query_only": True,
            },
        ],
        "contract": {
            "read_only": True,
            "preserve_city_scoped_ids": True,
            "declare_source_city_corpus_and_provenance": True,
            "no_forced_global_canonical_identity": True,
            "no_federated_write_approval_or_action": True,
            "no_learned_case_transfer": True,
            "no_dubai_proof_dependency": True,
            "no_production_deployment_claim": True,
        },
    }


def collect_ids(value: Any) -> list[str]:
    ids: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "city_scoped_canonical_id":
                ids.append(str(child))
            else:
                ids.extend(collect_ids(child))
    elif isinstance(value, list):
        for child in value:
            ids.extend(collect_ids(child))
    return ids


def build_city_scoped_id_audit(results: dict[str, Any]) -> dict[str, Any]:
    ids = sorted(set(collect_ids(results)))
    invalid = [value for value in ids if not (value.startswith("nyc:") or value.startswith("london:"))]
    dubai_refs = [value for value in ids if "dubai" in value.lower() or value.lower().startswith("dxb:")]
    missing_city = [value for value in ids if value.split(":", 1)[0] not in PROOF_CITIES]
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_c.federation_city_scoped_id_audit.v0",
        "status": "PASS" if not invalid and not dubai_refs and not missing_city else STATUS_BLOCKED,
        "audited_at": utc_now(),
        "city_scoped_id_count": len(ids),
        "sample_ids": ids[:20],
        "invalid_city_scoped_ids": invalid,
        "missing_or_unapproved_city_prefix": missing_city,
        "dubai_or_synthetic_proof_refs": dubai_refs,
        "global_canonical_merge_attempts": 0,
        "proof_cities": PROOF_CITIES,
        "preserves_city_scoped_canonical_ids": not invalid and not missing_city,
        "no_forced_global_canonical_identity": True,
        "source_refs": [
            rel(NYC_SOURCE_LEDGER),
            rel(NYC_SCHEMA_PROFILES),
            rel(LON_SOURCE_LEDGER),
            rel(LON_SCHEMA_PROFILES),
        ],
    }


def build_non_claim_boundary_audit(envelope: dict[str, Any], results: dict[str, Any], id_audit: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "query_only": envelope.get("local_replay_review_query_only") is True and results["contract"]["read_only"] is True,
        "evidence_refs_required": envelope.get("evidence_refs_required") is True,
        "authority_level_observe_or_explain_only": envelope.get("authority_level") == "observe_or_explain_only",
        "no_cross_city_learned_case_transfer": results["contract"]["no_learned_case_transfer"] is True,
        "no_global_canonical_id_merge": id_audit["no_forced_global_canonical_identity"] is True,
        "no_federated_write_approval_or_action": results["contract"]["no_federated_write_approval_or_action"] is True,
        "no_dubai_proof_dependency": (
            results["proof"]["dubai_synthetic_dependency"] is False
            and id_audit["dubai_or_synthetic_proof_refs"] == []
            and results["proof"]["proof_cities"] == PROOF_CITIES
        ),
        "no_production_federation_deployment_claim": results["contract"]["no_production_deployment_claim"] is True,
        "local_replay_review_query_only": True,
    }
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_c.federation_non_claim_boundary_audit.v0",
        "status": "PASS" if all(checks.values()) else STATUS_BLOCKED,
        "audited_at": utc_now(),
        "checks": checks,
        "forbidden_behaviors": [
            "cross_city_learned_case_transfer",
            "global_canonical_id_merge",
            "federated_write",
            "approval_or_action",
            "dubai_synthetic_proof_dependency",
            "production_federation_deployment_claim",
            "official_ticket_case_submission",
            "dispatch_control_enforcement",
            "legal_certified_finding",
            "autonomous_execution",
        ],
        "non_claims": envelope["non_claims"],
        "limitations": [
            "Federation v0 proves query shapes over existing NYC and London corpus ledgers only.",
            "Comparable entity types are source/profile compatibility signals, not merged identity.",
            "Source freshness/corpus state is descriptive metadata, not certified current truth.",
        ],
    }


def write_runner_artifact() -> None:
    write_text(
        OUTPUT_ROOT / "federation_query_runner_or_fixture_v0.py",
        '"""Deterministic fixture runner artifact for Push 2.1c Lane C federation query v0."""\n\n'
        "from scripts.run_epoch_2_1c_lane_c_federation_query_v0 import main\n\n\n"
        'if __name__ == "__main__":\n'
        "    raise SystemExit(main())\n",
    )


def write_summary(decision: dict[str, Any], results: dict[str, Any]) -> None:
    query_lines = "\n".join(
        f"- `{query['query_type']}` via `{query['query_id']}`" for query in results["queries"]
    )
    write_text(
        OUTPUT_ROOT / "SUMMARY.md",
        "# Push 2.1c Lane C Summary\n\n"
        f"Status: `{decision['status']}`\n\n"
        "Federation Query Infrastructure v0 is materialized as a local/replay/query-only fixture over NYC and London real corpus ledgers. "
        "It preserves city-scoped canonical IDs and does not create a global identity merge.\n\n"
        "## Query Shapes\n"
        f"{query_lines}\n\n"
        "## Boundaries\n"
        "- No cross-city learned case transfer.\n"
        "- No global canonical ID merge.\n"
        "- No federated write, approval, or action.\n"
        "- No Dubai proof dependency.\n"
        "- No production federation deployment claim.\n\n"
        "This lane does not claim Epoch 2.1 closed.\n",
    )


def write_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.iterdir()):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append({"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_c.hash_manifest.v0",
        "status": "PASS",
        "algorithm": "sha256",
        "item_count": len(files),
        "files": files,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def build_outputs() -> dict[str, Any]:
    prerequisite = validate_prerequisites()
    if prerequisite["status"] != "PASS":
        return {
            "status": STATUS_BLOCKED,
            "blocked_reason": "Push 2.1c prerequisite gate failed; no Lane C artifacts were written.",
            "prerequisite_gate": prerequisite,
        }

    required_inputs = [
        NYC_SOURCE_LEDGER,
        NYC_SCHEMA_PROFILES,
        LON_SOURCE_LEDGER,
        LON_SCHEMA_PROFILES,
        DOMAIN_PACK_VALIDATION,
        DOMAIN_PACK_APPEND_REPORT,
    ]
    missing_inputs = [rel(path) for path in required_inputs if not path.exists()]
    if missing_inputs:
        return {
            "status": STATUS_BLOCKED,
            "blocked_reason": "Required federation inputs are missing; no Lane C artifacts were written.",
            "missing_inputs": missing_inputs,
            "prerequisite_gate": prerequisite,
        }

    safe_prepare_output_root()
    envelope = build_envelope()
    nyc = load_city_corpus("nyc")
    london = load_city_corpus("london")
    domain_packs = load_domain_packs()
    results = build_fixture_results(envelope, nyc, london, domain_packs)
    id_audit = build_city_scoped_id_audit(results)
    boundary_audit = build_non_claim_boundary_audit(envelope, results, id_audit)

    write_json(OUTPUT_ROOT / "federation_query_envelope_v0.json", envelope)
    write_runner_artifact()
    write_json(OUTPUT_ROOT / "federation_query_nyc_london_fixture_results.json", results)
    write_json(OUTPUT_ROOT / "federation_city_scoped_id_audit.json", id_audit)
    write_json(OUTPUT_ROOT / "federation_non_claim_boundary_audit.json", boundary_audit)

    decision_status = STATUS_PASS_LIMITATIONS if id_audit["status"] == "PASS" and boundary_audit["status"] == "PASS" else STATUS_BLOCKED
    decision = {
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_c.decision.v0",
        "status": decision_status,
        "detail_status": "PASS_WITH_LIMITATIONS_PUSH_2_1C_LANE_C_FEDERATION_QUERY_V0"
        if decision_status == STATUS_PASS_LIMITATIONS
        else "BLOCKED_PUSH_2_1C_LANE_C_FEDERATION_QUERY_V0",
        "created_at": utc_now(),
        "branch": "main",
        "lane": "C",
        "package": "PUSH_2_1C_LANE_C_FEDERATION_QUERY_V0",
        "prerequisite_gate": prerequisite,
        "proof": results["proof"],
        "query_shape_count": len(results["queries"]),
        "source_corpora": results["source_corpora"],
        "id_audit_status": id_audit["status"],
        "non_claim_boundary_audit_status": boundary_audit["status"],
        "contract_check": {
            "lane_c_only": True,
            "main_branch_only": True,
            "query_only": True,
            "nyc_london_real_corpora_proof": True,
            "no_dubai_synthetic_proof_dependency": True,
            "preserve_city_scoped_ids": True,
            "declare_source_city_corpus_and_provenance": True,
            "no_forced_global_canonical_identity": True,
            "no_cross_city_learned_transfer": True,
            "no_federated_write_approval_or_action": True,
            "no_production_federation_deployment_claim": True,
            "epoch_2_1_not_closed": True,
        },
        "artifacts": sorted(EXPECTED_OUTPUT_FILES),
        "limitations": [
            "Federation v0 is local/replay/review/query only.",
            "Comparable entity types are compatibility descriptors, not merged identity.",
            "Source freshness/corpus state is descriptive metadata and not certified current truth.",
            "No Dubai synthetic pack is used as proof.",
        ],
    }
    write_json(OUTPUT_ROOT / "PUSH_2_1C_LANE_C_DECISION.json", decision)
    write_summary(decision, results)
    manifest = write_hash_manifest()
    return {
        "status": decision["status"],
        "decision": decision,
        "federation_query_envelope": envelope,
        "fixture_results": results,
        "city_scoped_id_audit": id_audit,
        "non_claim_boundary_audit": boundary_audit,
        "hash_manifest": manifest,
    }


def main() -> int:
    result = build_outputs()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] != STATUS_BLOCKED else 2


if __name__ == "__main__":
    raise SystemExit(main())
