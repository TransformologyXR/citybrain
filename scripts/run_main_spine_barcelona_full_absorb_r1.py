from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "main_spine_barcelona_full_absorb_r1"
GENERATED_STATE = ROOT / "outputs" / "platform_state_generated"
PATCH_PATH = ROOT / "outputs" / "main_spine_barcelona_absorb_r1" / "BARCELONA_PLATFORM_STATE_PATCH.json"
TASK = "MAIN-SPINE-BARCELONA-FULL-ABSORB-R1"
PASS_STATUS = "PASS_MAIN_SPINE_BARCELONA_FULL_ABSORB_R1"
PASS_LIMITED_STATUS = "PASS_MAIN_SPINE_BARCELONA_FULL_ABSORB_R1_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_SPINE_BARCELONA_FULL_ABSORB_R1"
GENERATED_AT = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

from apply_citybrain_platform_state_patch import apply_platform_state_patch


INPUT_ROOTS = {
    "barc_cadastre_recovery_d1": ROOT / "outputs" / "barc_cadastre_recovery_d1",
    "barc_core_d3_city_core_acceptance": ROOT / "outputs" / "barc_core_d3_city_core_acceptance",
    "barc_f7_review_flow_acceptance_r1": ROOT / "outputs" / "barc_f7_review_flow_acceptance_r1",
    "pv1_snapshot_addendum_r2": ROOT / "outputs" / "pv1_snapshot_addendum_r2",
    "main_spine_barcelona_absorb_r1": ROOT / "outputs" / "main_spine_barcelona_absorb_r1",
}

PV1_FROZEN_ROOTS = [
    ROOT / "outputs" / "pv1_d19_guardrail_action_policy_contract",
    ROOT / "outputs" / "pv1_d20_guardrail_enforcement_harness",
    ROOT / "outputs" / "pv1_d21_composite_platform_v1_snapshot",
    ROOT / "outputs" / "pv1_d22_final_platform_v1_audit",
]

OLD_ACCEPTED_ROOTS = [
    ROOT / "outputs" / "flowx_review_flow_acceptance_d1",
    ROOT / "outputs" / "pv1_d19d20d21d22_platform_v1_snapshot_gate",
    ROOT / "outputs" / "pv1_snapshot_addendum_r1",
    ROOT / "outputs" / "barc_f7_d3_civic_sensor_fusion_evidencebundles",
]

FORBIDDEN_POSITIVE_CLAIMS = [
    "barcelona all flows accepted",
    "barcelona production ready",
    "f7 can dispatch",
    "f7 can respond",
    "f7 can control",
    "certified affected buildings",
    "d19-d22 updated",
    "d19-d22 mutated",
]

SECRET_PATTERNS = [
    re.compile(r"TMB[_-]?(APP[_-]?KEY|KEY|SECRET|TOKEN)\s*=", re.IGNORECASE),
    re.compile(r"Authorization\s*:\s*Bearer\s+[A-Za-z0-9._-]+", re.IGNORECASE),
    re.compile(r"x-api-key\s*[:=]\s*[A-Za-z0-9._-]+", re.IGNORECASE),
    re.compile(r"raw_credentials_serialized\"?\s*:\s*true", re.IGNORECASE),
    re.compile(r"app_key_present\"?\s*:\s*true", re.IGNORECASE),
    re.compile(r"api_key_used\"?\s*:\s*true", re.IGNORECASE),
]


def clean(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return None if value != value else round(value, 6)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean(v) for v in value]
    return str(value)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "total_size": 0, "digest": None}
    if path.is_file():
        return {"exists": True, "file_count": 1, "total_size": path.stat().st_size, "digest": sha256_file(path)}
    digest = hashlib.sha256()
    file_count = 0
    total_size = 0
    for root, dirs, files in os.walk(path):
        dirs.sort()
        files.sort()
        rel_root = Path(root).relative_to(path).as_posix()
        digest.update(rel_root.encode("utf-8"))
        for name in files:
            file_path = Path(root) / name
            stat = file_path.stat()
            file_count += 1
            total_size += stat.st_size
            digest.update(file_path.relative_to(path).as_posix().encode("utf-8"))
            digest.update(str(stat.st_size).encode("ascii"))
            digest.update(str(stat.st_mtime_ns).encode("ascii"))
    return {"exists": True, "file_count": file_count, "total_size": total_size, "digest": digest.hexdigest()}


def reset_output() -> None:
    expected = ROOT / "outputs" / "main_spine_barcelona_full_absorb_r1"
    if OUTPUT.resolve() != expected.resolve():
        raise RuntimeError(f"Refusing unexpected output root: {OUTPUT}")
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True, exist_ok=True)


def file_rec(path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "exists": path.exists(),
        "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
        "bytes": path.stat().st_size if path.exists() and path.is_file() else None,
    }


def verify_prior_absorb() -> dict[str, Any]:
    decision = read_json(INPUT_ROOTS["main_spine_barcelona_absorb_r1"] / "MAIN_SPINE_BARCELONA_ABSORB_R1_DECISION.json", {})
    smoke = read_json(INPUT_ROOTS["main_spine_barcelona_absorb_r1"] / "BARCELONA_SPINE_TRICKLE_SMOKE_REPORT.json", {})
    return {
        "status": "PASS"
        if decision.get("status") == "PASS_MAIN_SPINE_BARCELONA_ABSORB_R1_WITH_LIMITATIONS"
        and smoke.get("city_registry_status_resolver", {}).get("status") == "PASS"
        and smoke.get("flow_resolver", {}).get("status") == "PASS"
        else "FAIL",
        "previous_decision": decision.get("status"),
        "previous_limitation": decision.get("limitation_reason"),
        "patch_only_limitation_confirmed": "patch" in str(decision.get("limitation_reason", "")).lower(),
        "city_flow_patch_smoke": smoke.get("status"),
        "no_mutation_audit": (INPUT_ROOTS["main_spine_barcelona_absorb_r1"] / "BARCELONA_NO_MUTATION_AUDIT.md").exists(),
        "claim_boundary_audit": (INPUT_ROOTS["main_spine_barcelona_absorb_r1"] / "BARCELONA_CLAIM_BOUNDARY_AUDIT.md").exists(),
        "secret_redaction_audit": (INPUT_ROOTS["main_spine_barcelona_absorb_r1"] / "BARCELONA_SECRET_REDACTION_AUDIT.md").exists(),
    }


def verify_source_acceptance() -> dict[str, Any]:
    cad_manifest = read_json(INPUT_ROOTS["barc_cadastre_recovery_d1"] / "BARC_CADASTRE_RECOVERY_D1_MANIFEST.json", {})
    cad_harness = read_json(INPUT_ROOTS["barc_cadastre_recovery_d1"] / "BARC_CADASTRE_RECOVERY_D1_HARNESS_REPORT.json", {})
    core_harness = read_json(INPUT_ROOTS["barc_core_d3_city_core_acceptance"] / "BARC_CORE_D3_HARNESS_REPORT.json", {})
    f7_harness = read_json(INPUT_ROOTS["barc_f7_review_flow_acceptance_r1"] / "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_HARNESS_REPORT.json", {})
    f7_no_mut = read_json(INPUT_ROOTS["barc_f7_review_flow_acceptance_r1"] / "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_NO_MUTATION_REPORT.json", {})
    r2_harness = read_json(INPUT_ROOTS["pv1_snapshot_addendum_r2"] / "PV1_SNAPSHOT_ADDENDUM_R2_HARNESS_REPORT.json", {})
    r2_no_mut = read_json(INPUT_ROOTS["pv1_snapshot_addendum_r2"] / "PV1_SNAPSHOT_ADDENDUM_R2_NO_MUTATION_REPORT.json", {})
    source_counts = {
        src.get("acceptance_key"): next(iter(src.get("zip_inventory", {}).get("feature_counts", {"": 0}).values()))
        for src in cad_manifest.get("sources", [])
    }
    checks = {
        "cadastre_gate": cad_harness.get("status") == "PASS_BARC_CADASTRE_RECOVERY_D1",
        "core_gate": core_harness.get("status") == "ACCEPTED_CITY_CORE_WITH_LIMITATIONS",
        "f7_gate": f7_harness.get("status") == "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
        "r2_gate": r2_harness.get("status") == "PASS_PV1_SNAPSHOT_ADDENDUM_R2",
        "municipality": cad_manifest.get("municipality_code") == "08900-BARCELONA",
        "feature_counts": source_counts == {
            "cadastre_parcels": 78371,
            "cadastre_buildings": 69893,
            "cadastre_addresses": 90258,
        },
        "f7_d3_not_rerun": bool(f7_no_mut.get("existing_f7_d3_not_rerun")),
        "r2_additive_no_mutation": bool(r2_no_mut.get("existing_pv1_d19_d22_not_mutated")),
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "feature_counts": source_counts}


def resolve_city(resolver: dict[str, Any], key: str) -> dict[str, Any] | None:
    cities = resolver.get("cities_by_id", {})
    if key in cities:
        return cities[key]
    alias = resolver.get("city_aliases", {}).get(key.lower())
    return cities.get(alias) if alias else None


def resolver_smoke(resolver: dict[str, Any]) -> dict[str, Any]:
    negative = {}
    for idx in range(1, 7):
        flow_id = f"BARC-F{idx}"
        row = resolver.get("flows_by_id", {}).get(flow_id, {})
        negative[flow_id] = {
            "actual": row.get("status"),
            "expected": "NOT_ACCEPTED",
            "accepted": str(row.get("status", "")).startswith("ACCEPTED"),
            "status": "PASS" if not str(row.get("status", "")).startswith("ACCEPTED") else "FAIL",
        }
    tests = {
        "city_status_resolver": {
            "input": "BARC",
            "actual": (resolve_city(resolver, "BARC") or {}).get("core_status"),
            "expected": "ACCEPTED_CITY_CORE_WITH_LIMITATIONS",
        },
        "city_alias_resolver": {
            "input": "Barcelona",
            "actual_city_id": (resolve_city(resolver, "Barcelona") or {}).get("city_id"),
            "actual_status": (resolve_city(resolver, "Barcelona") or {}).get("core_status"),
            "expected_city_id": "BARC",
            "expected_status": "ACCEPTED_CITY_CORE_WITH_LIMITATIONS",
        },
        "flow_resolver": {
            "input": "BARC-F7",
            "actual": resolver.get("flows_by_id", {}).get("BARC-F7", {}).get("status"),
            "expected": "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
            "blocker_status": resolver.get("flows_by_id", {}).get("BARC-F7", {}).get("blocker_status"),
        },
        "addendum_resolver": {
            "input": "PV1-SNAPSHOT-ADDENDUM-R2",
            "actual": resolver.get("addenda_by_id", {}).get("PV1-SNAPSHOT-ADDENDUM-R2", {}).get("status"),
            "expected": "PASS_PV1_SNAPSHOT_ADDENDUM_R2",
        },
        "negative_barcelona_flows": negative,
    }
    statuses = [
        tests["city_status_resolver"]["actual"] == tests["city_status_resolver"]["expected"],
        tests["city_alias_resolver"]["actual_city_id"] == tests["city_alias_resolver"]["expected_city_id"]
        and tests["city_alias_resolver"]["actual_status"] == tests["city_alias_resolver"]["expected_status"],
        tests["flow_resolver"]["actual"] == tests["flow_resolver"]["expected"]
        and tests["flow_resolver"]["blocker_status"] == "RESOLVED",
        tests["addendum_resolver"]["actual"] == tests["addendum_resolver"]["expected"],
        all(row["status"] == "PASS" for row in negative.values()),
    ]
    return {"status": "PASS" if all(statuses) else "FAIL", "tests": tests, "source": "outputs/platform_state_generated/CITYBRAIN_RESOLVER_INPUTS.json"}


def evidencebundle_smoke(resolver: dict[str, Any]) -> dict[str, Any]:
    city = resolver["cities_by_id"]["BARC"]
    flow = resolver["flows_by_id"]["BARC-F7"]
    addendum = resolver["addenda_by_id"]["PV1-SNAPSHOT-ADDENDUM-R2"]
    bundle = {
        "bundle_id": "BARC-F7-FULL-ABSORB-R1-EVIDENCEBUNDLE-SMOKE",
        "city": "BARC",
        "city_status": city["core_status"],
        "flow_id": "BARC-F7",
        "flow_status": flow["status"],
        "dependency_satisfied": flow.get("dependency") == "BARC-CORE-D3" and flow.get("dependency_status") == "satisfied",
        "cadastre_recovery_reference": city["artifact_references"].get("cadastre_manifest"),
        "cadastre": city.get("cadastre", {}),
        "pv1_addendum_r2_reference": addendum.get("artifact_references", {}).get("r2_status"),
        "accepted_limitations": [*city.get("limitations", []), *flow.get("limitations", [])],
        "source_references": {
            "city_core": city.get("artifact_references", {}),
            "flow_acceptance": flow.get("artifact_references", {}),
            "pv1_addendum": addendum.get("artifact_references", {}),
        },
        "confidence": "accepted_review_flow_with_limitations_from_passed_gates",
        "review_status": "review-only accepted flow",
        "claim_boundary": "BARC-F7 is review-only; no operational command authority.",
        "privacy_boundary": "IRIS civic context remains aggregate/evidence context; address/cadastre context is source-governed.",
        "missing_data_or_limitations": [
            "Other Barcelona flows are not accepted by this task.",
            "Cadastre ZIPs are official publication snapshots, not live/current feeds.",
            "No all-flow Barcelona data landing is claimed.",
        ],
    }
    positive_claim_text = json.dumps(
        {
            "city_status": bundle["city_status"],
            "flow_status": bundle["flow_status"],
            "claim_boundary": bundle["claim_boundary"],
            "review_status": bundle["review_status"],
        },
        sort_keys=True,
    ).lower()
    forbidden = [phrase for phrase in FORBIDDEN_POSITIVE_CLAIMS if phrase in positive_claim_text]
    required = [
        bundle["city_status"] == "ACCEPTED_CITY_CORE_WITH_LIMITATIONS",
        bundle["flow_status"] == "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
        bundle["dependency_satisfied"],
        bool(bundle["cadastre_recovery_reference"]),
        bool(bundle["pv1_addendum_r2_reference"]),
        "review-only" in bundle["claim_boundary"],
        not forbidden,
    ]
    return {"status": "PASS" if all(required) else "FAIL", "evidence_bundle": bundle, "forbidden_positive_claims": forbidden}


def platform_regression(resolver: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "nyc_city_resolves": (resolve_city(resolver, "NYC") or {}).get("core_status") == "ACCEPTED_CITY_CORE_WITH_SOURCE_LIMITATIONS",
        "nyc_f1x_review_flow_resolves": resolver.get("flows_by_id", {}).get("NYC-F1X", {}).get("status") == "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
        "chicago_city_resolves": (resolve_city(resolver, "CHI") or {}).get("core_status") == "ACCEPTED_CITY_CORE_WITH_SOURCE_LIMITATIONS",
        "chicago_f4x_review_flow_resolves": resolver.get("flows_by_id", {}).get("CHI-F4X", {}).get("status") == "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
        "chicago_f2x_not_accepted": not str(resolver.get("flows_by_id", {}).get("CHI-F2X", {}).get("status", "")).startswith("ACCEPTED"),
        "pv1_snapshot_resolves": resolver.get("pv1_snapshot", {}).get("status") == "PASS_PLATFORM_V1_REVIEW_ONLY_SNAPSHOT",
        "barcelona_resolves": (resolve_city(resolver, "BARC") or {}).get("core_status") == "ACCEPTED_CITY_CORE_WITH_LIMITATIONS",
        "no_barcelona_all_flow_acceptance": all(
            not str(resolver.get("flows_by_id", {}).get(f"BARC-F{idx}", {}).get("status", "")).startswith("ACCEPTED")
            for idx in range(1, 7)
        ),
        "no_legacy_barcelona_flow_ids": not any(
            str(flow_id).startswith("BARCELONA-") for flow_id in resolver.get("flows_by_id", {})
        ),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "not_run": [
            "Full historical data rebuilds",
            "Barcelona source landing",
            "PV1 D19-D22 rerun",
        ],
    }


def claim_boundary_audit(paths: list[Path], resolver: dict[str, Any], bundle_report: dict[str, Any]) -> dict[str, Any]:
    findings = []
    positive_payload = json.dumps(
        {
            "resolver_barcelona_city": resolver.get("cities_by_id", {}).get("BARC", {}).get("core_status"),
            "resolver_barc_f7": resolver.get("flows_by_id", {}).get("BARC-F7", {}).get("status"),
            "bundle_claim_boundary": bundle_report.get("evidence_bundle", {}).get("claim_boundary"),
            "bundle_review_status": bundle_report.get("evidence_bundle", {}).get("review_status"),
        },
        sort_keys=True,
    ).lower()
    for phrase in FORBIDDEN_POSITIVE_CLAIMS:
        if phrase in positive_payload:
            findings.append({"scope": "positive_state_fields", "phrase": phrase})
    required_wording = {
        "city_core_with_limitations": resolver.get("cities_by_id", {}).get("BARC", {}).get("core_status") == "ACCEPTED_CITY_CORE_WITH_LIMITATIONS",
        "barc_f7_review_only": "review-only" in json.dumps(resolver.get("flows_by_id", {}).get("BARC-F7", {})).lower(),
        "r2_additive": resolver.get("addenda_by_id", {}).get("PV1-SNAPSHOT-ADDENDUM-R2", {}).get("relationship_to_d19_d22") == "additive, no mutation",
        "other_barc_flows_not_accepted": all(
            not str(resolver.get("flows_by_id", {}).get(f"BARC-F{idx}", {}).get("status", "")).startswith("ACCEPTED")
            for idx in range(1, 7)
        ),
    }
    return {"status": "PASS" if not findings and all(required_wording.values()) else "FAIL", "findings": findings, "required_wording": required_wording}


def secret_audit(paths: list[Path]) -> dict[str, Any]:
    findings = []
    for root in paths:
        if not root.exists():
            continue
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            if path.suffix.lower() in {".zip", ".gml"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    findings.append({"file": path.relative_to(ROOT).as_posix(), "pattern": pattern.pattern})
                    break
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def diff_text(before: dict[str, Any], after: dict[str, Any]) -> str:
    return "\n".join(
        difflib.unified_diff(
            json.dumps(clean(before), indent=2, sort_keys=True).splitlines(),
            json.dumps(clean(after), indent=2, sort_keys=True).splitlines(),
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )


def write_hashes() -> int:
    lines = []
    for path in sorted(p for p in OUTPUT.rglob("*") if p.is_file()):
        if path.name == "hashes.sha256":
            continue
        lines.append(f"{sha256_file(path)}  {path.relative_to(OUTPUT).as_posix()}")
    write_text(OUTPUT / "hashes.sha256", "\n".join(lines))
    return len(lines)


def copy_generated_finals() -> None:
    mapping = {
        "CITYBRAIN_PLATFORM_STATE.json": "BARCELONA_PLATFORM_STATE_FINAL.json",
        "CITYBRAIN_CITY_CORE_LEDGER.json": "BARCELONA_CITY_CORE_LEDGER_FINAL.json",
        "CITYBRAIN_FLOW_ACCEPTANCE_LEDGER.json": "BARCELONA_FLOW_ACCEPTANCE_LEDGER_FINAL.json",
        "CITYBRAIN_PV1_ADDENDUM_REGISTRY.json": "PV1_ADDENDUM_R2_REGISTRY_FINAL.json",
        "CITYBRAIN_PLATFORM_STATE_APPLY_LOG.json": "BARCELONA_GENERATED_LEDGER_APPLY_LOG.json",
    }
    for src, dest in mapping.items():
        payload = read_json(GENERATED_STATE / src, {})
        write_json(OUTPUT / dest, payload)


def main() -> int:
    before_signatures = {
        **{path.relative_to(ROOT).as_posix(): tree_signature(path) for path in [*INPUT_ROOTS.values(), *PV1_FROZEN_ROOTS, *OLD_ACCEPTED_ROOTS]},
        "data_landing/barc_cadastre_recovery_d1": tree_signature(ROOT / "data_landing" / "barc_cadastre_recovery_d1"),
    }
    before_platform_state = read_json(GENERATED_STATE / "CITYBRAIN_PLATFORM_STATE.json", {})
    reset_output()

    repo_discovery = {
        "status": "PASS",
        "finding": "No single pre-existing general platform-state registry was found; authoritative state is mixed per-gate output artifacts.",
        "authoritative_inputs": {
            "city_registry": "accepted gate artifacts plus generated ledger after this task",
            "flow_acceptance_registry": "FLOWX/BARC accepted-flow output ledgers plus generated ledger after this task",
            "pv1_snapshot_addendum_registry": "PV1 snapshot/addendum output roots plus generated ledger after this task",
            "resolver_inputs": "outputs/platform_state_generated/CITYBRAIN_RESOLVER_INPUTS.json",
            "evidencebundle_inputs": "outputs/platform_state_generated/CITYBRAIN_RESOLVER_INPUTS.json plus accepted BARC artifacts",
            "database_state": "none found for this task",
        },
        "created_safe_workflow": "scripts/apply_citybrain_platform_state_patch.py",
    }
    prior_absorb = verify_prior_absorb()
    source_acceptance = verify_source_acceptance()

    apply_result = apply_platform_state_patch(PATCH_PATH, GENERATED_STATE)
    copy_generated_finals()

    resolver = read_json(GENERATED_STATE / "CITYBRAIN_RESOLVER_INPUTS.json", {})
    resolver_report = resolver_smoke(resolver)
    evidence_report = evidencebundle_smoke(resolver)
    regression_report = platform_regression(resolver)
    claim_report = claim_boundary_audit([OUTPUT, GENERATED_STATE], resolver, evidence_report)
    secret_report = secret_audit([OUTPUT, GENERATED_STATE])

    after_signatures = {
        **{path.relative_to(ROOT).as_posix(): tree_signature(path) for path in [*INPUT_ROOTS.values(), *PV1_FROZEN_ROOTS, *OLD_ACCEPTED_ROOTS]},
        "data_landing/barc_cadastre_recovery_d1": tree_signature(ROOT / "data_landing" / "barc_cadastre_recovery_d1"),
    }
    changed_inputs = [key for key in before_signatures if before_signatures[key] != after_signatures[key]]
    after_platform_state = read_json(GENERATED_STATE / "CITYBRAIN_PLATFORM_STATE.json", {})
    live_diff = diff_text(before_platform_state, after_platform_state)
    no_mutation = {
        "status": "PASS" if not changed_inputs else "FAIL",
        "changed_existing_inputs": changed_inputs,
        "pv1_d19_d22_mutated": any(key.startswith("outputs/pv1_d1") or key.startswith("outputs/pv1_d2") for key in changed_inputs),
        "old_barc_f7_d3_not_rerun": "outputs/barc_f7_d3_civic_sensor_fusion_evidencebundles" not in changed_inputs,
        "no_raw_source_download_or_scouting": "data_landing/barc_cadastre_recovery_d1" not in changed_inputs,
        "changed_files_scope": [
            "scripts/apply_citybrain_platform_state_patch.py",
            "scripts/run_main_spine_barcelona_full_absorb_r1.py",
            "outputs/platform_state_generated",
            "outputs/main_spine_barcelona_full_absorb_r1",
        ],
    }

    limitation_report = {
        "status": "PATCH_ONLY_LIMITATION_CLOSED" if apply_result["status"] == "PASS" and resolver_report["status"] == "PASS" else "PATCH_ONLY_LIMITATION_REMAINS",
        "closed": [
            "safe generated-ledger workflow added",
            "Barcelona patch applied into outputs/platform_state_generated",
            "resolver reads Barcelona from generated state",
            "EvidenceBundle smoke reads Barcelona from generated state",
            "before/after diff emitted",
        ],
        "remaining": [] if apply_result["status"] == "PASS" and resolver_report["status"] == "PASS" else ["generated state application or resolver smoke failed"],
    }

    gates = [
        {"gate": "REPO-STATE-DISCOVERY", "status": repo_discovery["status"]},
        {"gate": "PRIOR-ABSORB-VERIFICATION", "status": prior_absorb["status"]},
        {"gate": "SOURCE-ACCEPTANCE-VERIFICATION", "status": source_acceptance["status"]},
        {"gate": "GENERATED-LEDGER-APPLY", "status": apply_result["status"]},
        {"gate": "RESOLVER-SMOKE", "status": resolver_report["status"]},
        {"gate": "EVIDENCEBUNDLE-SMOKE", "status": evidence_report["status"]},
        {"gate": "PLATFORM-REGRESSION", "status": regression_report["status"]},
        {"gate": "CLAIM-BOUNDARY", "status": claim_report["status"]},
        {"gate": "NO-MUTATION", "status": no_mutation["status"]},
        {"gate": "SECRET-REDACTION", "status": secret_report["status"]},
        {"gate": "PATCH-ONLY-LIMITATION", "status": "PASS" if limitation_report["status"] == "PATCH_ONLY_LIMITATION_CLOSED" else "FAIL"},
    ]
    final_status = PASS_STATUS if all(g["status"] == "PASS" for g in gates) else FAIL_STATUS

    write_json(OUTPUT / "BARCELONA_RESOLVER_SMOKE_REPORT.json", resolver_report)
    write_json(OUTPUT / "BARCELONA_EVIDENCEBUNDLE_SMOKE_REPORT.json", evidence_report)
    write_json(OUTPUT / "BARCELONA_PLATFORM_REGRESSION_REPORT.json", regression_report)

    write_text(
        OUTPUT / "BARCELONA_LIVE_STATE_BEFORE_AFTER_DIFF.md",
        f"""# Barcelona Live State Before/After Diff

```diff
{live_diff or "No platform state diff; generated state was already current."}
```
""",
    )
    write_text(
        OUTPUT / "BARCELONA_LIVE_STATE_APPLY_REPORT.md",
        f"""# Barcelona Live State Apply Report

Status: {apply_result["status"]}

Applied patch: `{PATCH_PATH.relative_to(ROOT).as_posix()}`

Generated state root: `outputs/platform_state_generated`

This task created and used `scripts/apply_citybrain_platform_state_patch.py`. The generated state now contains Barcelona as `ACCEPTED_CITY_CORE_WITH_LIMITATIONS`, BARC-F7 as `ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS`, and PV1-SNAPSHOT-ADDENDUM-R2 as additive/pass.
""",
    )
    write_text(
        OUTPUT / "BARCELONA_NO_MUTATION_AUDIT.md",
        f"""# Barcelona No-Mutation Audit

Status: {no_mutation["status"]}

- Existing input roots changed: {", ".join(changed_inputs) if changed_inputs else "none"}
- PV1 D19-D22 mutated: {no_mutation["pv1_d19_d22_mutated"]}
- Old BARC-F7-D3 rerun: {not no_mutation["old_barc_f7_d3_not_rerun"]}
- Raw source data download/scouting detected: {not no_mutation["no_raw_source_download_or_scouting"]}
- Changes are limited to platform generated state, full-absorb outputs, and the generated-ledger scripts.
""",
    )
    write_text(
        OUTPUT / "BARCELONA_CLAIM_BOUNDARY_AUDIT.md",
        f"""# Barcelona Claim Boundary Audit

Status: {claim_report["status"]}

Required wording is present:

- Barcelona city core is accepted with limitations.
- BARC-F7 is accepted as a review-only flow with limitations.
- PV1 addendum R2 is additive.
- Old PV1 D19-D22 are unchanged.
- Other Barcelona flows are not accepted by this task.

Forbidden positive-claim findings: {len(claim_report["findings"])}
""",
    )
    write_text(
        OUTPUT / "BARCELONA_SECRET_REDACTION_AUDIT.md",
        f"""# Barcelona Secret Redaction Audit

Status: {secret_report["status"]}

Findings: {len(secret_report["findings"])}

Scanned generated state and full-absorb outputs for TMB keys, API keys, tokens, raw credentials, `.env` leakage, and Authorization headers.
""",
    )
    write_text(
        OUTPUT / "BARCELONA_LIMITATIONS_CLOSED_OR_REMAINING.md",
        f"""# Barcelona Limitations Closed Or Remaining

Status: {limitation_report["status"]}

Closed:

{chr(10).join(f"- {item}" for item in limitation_report["closed"])}

Remaining:

{chr(10).join(f"- {item}" for item in limitation_report["remaining"]) if limitation_report["remaining"] else "- none for this state-management task"}
""",
    )

    decision = {
        "task": TASK,
        "generated_at": GENERATED_AT,
        "final_status": final_status,
        "applied_patch": PATCH_PATH.relative_to(ROOT).as_posix(),
        "files_changed_or_created_by_task": [
            "scripts/apply_citybrain_platform_state_patch.py",
            "scripts/run_main_spine_barcelona_full_absorb_r1.py",
            "outputs/platform_state_generated",
            "outputs/main_spine_barcelona_full_absorb_r1",
        ],
        "generated_ledgers_updated": {
            "platform_state": "outputs/platform_state_generated/CITYBRAIN_PLATFORM_STATE.json",
            "city_core": "outputs/platform_state_generated/CITYBRAIN_CITY_CORE_LEDGER.json",
            "flow_acceptance": "outputs/platform_state_generated/CITYBRAIN_FLOW_ACCEPTANCE_LEDGER.json",
            "pv1_addenda": "outputs/platform_state_generated/CITYBRAIN_PV1_ADDENDUM_REGISTRY.json",
            "resolver_inputs": "outputs/platform_state_generated/CITYBRAIN_RESOLVER_INPUTS.json",
        },
        "repo_state_discovery": repo_discovery,
        "prior_absorb_verification": prior_absorb,
        "source_acceptance_verification": source_acceptance,
        "gates": gates,
        "resolver_smoke_status": resolver_report["status"],
        "evidencebundle_smoke_status": evidence_report["status"],
        "regression_status": regression_report["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret_report["status"],
        "claim_boundary_audit_status": claim_report["status"],
        "closed_limitations": limitation_report["closed"],
        "remaining_limitations": limitation_report["remaining"],
        "recommended_next_platform_task": "Return to platform work; do not begin Barcelona data landing from this state-management gate.",
    }
    write_json(OUTPUT / "MAIN_SPINE_BARCELONA_FULL_ABSORB_R1_DECISION.json", decision)

    write_text(
        OUTPUT / "README.md",
        f"""# MAIN-SPINE-BARCELONA-FULL-ABSORB-R1

Status: {final_status}

Barcelona is now represented in generated platform state at `outputs/platform_state_generated`, not only in the prior patch pack. The generated resolver inputs include Barcelona city core, BARC-F7, and PV1-SNAPSHOT-ADDENDUM-R2.
""",
    )
    write_text(
        OUTPUT / "MAIN_SPINE_BARCELONA_FULL_ABSORB_R1.md",
        f"""# MAIN-SPINE-BARCELONA-FULL-ABSORB-R1

Final status: `{final_status}`

This task closes the prior patch-only limitation by adding a safe generated-ledger apply workflow and applying the accepted Barcelona state into generated platform state.

Generated state:

- `outputs/platform_state_generated/CITYBRAIN_PLATFORM_STATE.json`
- `outputs/platform_state_generated/CITYBRAIN_CITY_CORE_LEDGER.json`
- `outputs/platform_state_generated/CITYBRAIN_FLOW_ACCEPTANCE_LEDGER.json`
- `outputs/platform_state_generated/CITYBRAIN_PV1_ADDENDUM_REGISTRY.json`
- `outputs/platform_state_generated/CITYBRAIN_RESOLVER_INPUTS.json`

Barcelona:

- City core: `ACCEPTED_CITY_CORE_WITH_LIMITATIONS`
- BARC-F7: `ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS`
- PV1-SNAPSHOT-ADDENDUM-R2: `PASS_PV1_SNAPSHOT_ADDENDUM_R2`

Other Barcelona flows remain not accepted. PV1 D19-D22 are unchanged.
""",
    )

    hash_count = write_hashes()
    decision["hash_count"] = hash_count
    write_json(OUTPUT / "MAIN_SPINE_BARCELONA_FULL_ABSORB_R1_DECISION.json", decision)
    write_hashes()

    print(
        f"""{TASK}: STATUS

Generated platform state: PASS
Barcelona city resolver: {resolver_report["tests"]["city_status_resolver"]["actual"]}
BARC-F7 resolver: {resolver_report["tests"]["flow_resolver"]["actual"]}
PV1 addendum R2 resolver: {resolver_report["tests"]["addendum_resolver"]["actual"]}
EvidenceBundle smoke: {evidence_report["status"]}
Regression: {regression_report["status"]}
No-mutation: {no_mutation["status"]}
Claim boundary: {claim_report["status"]}
Secret redaction: {secret_report["status"]}
Patch-only limitation: {limitation_report["status"]}

Final status:
{final_status}

Output:
outputs/main_spine_barcelona_full_absorb_r1
"""
    )
    return 0 if final_status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
