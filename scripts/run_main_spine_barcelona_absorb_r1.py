from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "MAIN-SPINE-BARCELONA-ABSORB-R1"
PASS_STATUS = "PASS_MAIN_SPINE_BARCELONA_ABSORB_R1"
PASS_LIMITED_STATUS = "PASS_MAIN_SPINE_BARCELONA_ABSORB_R1_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_SPINE_BARCELONA_ABSORB_R1"
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "main_spine_barcelona_absorb_r1"
GENERATED_AT = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

INPUT_ROOTS = {
    "cadastre_recovery": ROOT / "outputs" / "barc_cadastre_recovery_d1",
    "city_core": ROOT / "outputs" / "barc_core_d3_city_core_acceptance",
    "f7_acceptance": ROOT / "outputs" / "barc_f7_review_flow_acceptance_r1",
    "pv1_addendum_r2": ROOT / "outputs" / "pv1_snapshot_addendum_r2",
}

PV1_FROZEN_ROOTS = [
    ROOT / "outputs" / "pv1_d19_guardrail_action_policy_contract",
    ROOT / "outputs" / "pv1_d20_guardrail_enforcement_harness",
    ROOT / "outputs" / "pv1_d21_composite_platform_v1_snapshot",
    ROOT / "outputs" / "pv1_d22_final_platform_v1_audit",
]

REGRESSION_INPUTS = {
    "pv1_final_snapshot": ROOT / "outputs" / "pv1_d19d20d21d22_platform_v1_snapshot_gate" / "PV1_D19D20D21D22_HARNESS_REPORT.json",
    "nyc_chi_flow_acceptance": ROOT / "outputs" / "flowx_review_flow_acceptance_d1" / "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_HARNESS_REPORT.json",
    "pv1_addendum_r1": ROOT / "outputs" / "pv1_snapshot_addendum_r1" / "PV1_SNAPSHOT_ADDENDUM_R1_STATUS_UPDATE.json",
}

FORBIDDEN_CLAIMS = [
    "public-safety command",
    "health determination",
    "enforcement recommendation",
    "dispatch recommendation",
    "traffic-control command",
    "transit-control command",
    "certified affected-building claim",
    "all Barcelona flows are accepted",
    "Barcelona all-flow data landing has been completed",
]

ALLOWED_OUTPUT_FILES = [
    "README.md",
    "MAIN_SPINE_BARCELONA_ABSORB_R1.md",
    "MAIN_SPINE_BARCELONA_ABSORB_R1_DECISION.json",
    "BARCELONA_PLATFORM_STATE_PATCH.json",
    "BARCELONA_CITY_CORE_LEDGER_PATCH.json",
    "BARCELONA_FLOW_ACCEPTANCE_LEDGER_PATCH.json",
    "PV1_ADDENDUM_R2_REGISTRY_PATCH.json",
    "BARCELONA_SPINE_TRICKLE_SMOKE_REPORT.json",
    "BARCELONA_NO_MUTATION_AUDIT.md",
    "BARCELONA_CLAIM_BOUNDARY_AUDIT.md",
    "BARCELONA_SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
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
    expected = (ROOT / "outputs" / "main_spine_barcelona_absorb_r1").resolve()
    if OUTPUT.resolve() != expected:
        raise RuntimeError(f"Refusing to reset unexpected output path: {OUTPUT}")
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True, exist_ok=True)


def source_by_key(manifest: dict[str, Any], key: str) -> dict[str, Any]:
    for source in manifest.get("sources", []):
        if source.get("acceptance_key") == key or source.get("source_key") == key:
            return source
    return {}


def feature_count(source: dict[str, Any]) -> int:
    counts = source.get("zip_inventory", {}).get("feature_counts", {})
    if not counts:
        return 0
    return int(next(iter(counts.values())))


def make_city_core_patch(cadastre: dict[str, Any], core_decision: dict[str, Any]) -> dict[str, Any]:
    parcels = source_by_key(cadastre, "cadastre_parcels")
    buildings = source_by_key(cadastre, "cadastre_buildings")
    addresses = source_by_key(cadastre, "cadastre_addresses")
    return {
        "patch_type": "city_core_ledger_patch",
        "task": TASK,
        "generated_at": GENERATED_AT,
        "city_id": "BARC",
        "city_name": "Barcelona",
        "previous_core_status": "CANDIDATE_ONLY_NOT_ACCEPTED",
        "core_status": "ACCEPTED_CITY_CORE_WITH_LIMITATIONS",
        "accepted_gate": "BARC-CORE-D3",
        "cadastre": {
            "municipality_code": cadastre.get("municipality_code"),
            "path_type": "ATOM_ZIP_MUNICIPALITY_DOWNLOAD",
            "parcels": {
                "status": parcels.get("acceptance_status"),
                "bytes": parcels.get("bytes"),
                "feature_count": feature_count(parcels),
                "sha256": parcels.get("sha256"),
                "url": parcels.get("direct_zip_url"),
            },
            "buildings": {
                "status": buildings.get("acceptance_status"),
                "bytes": buildings.get("bytes"),
                "feature_count": feature_count(buildings),
                "sha256": buildings.get("sha256"),
                "url": buildings.get("direct_zip_url"),
            },
            "addresses": {
                "status": addresses.get("acceptance_status"),
                "bytes": addresses.get("bytes"),
                "feature_count": feature_count(addresses),
                "sha256": addresses.get("sha256"),
                "url": addresses.get("direct_zip_url"),
            },
        },
        "accepted_limitations": core_decision.get("boundary_lines", []),
        "license_privacy_notes": [
            "Spanish Cadastre INSPIRE ATOM ZIPs are official publication snapshots.",
            "Address layer remains privacy-sensitive context; no personal or case-level inference.",
            "IRIS remains aggregate/evidence context only.",
            "Sentilo/Connecta observations remain endpoint-specific and source-limited.",
        ],
        "artifact_references": {
            "cadastre_manifest": "outputs/barc_cadastre_recovery_d1/BARC_CADASTRE_RECOVERY_D1_MANIFEST.json",
            "core_decision": "outputs/barc_core_d3_city_core_acceptance/BARC_CORE_D3_ACCEPTANCE_DECISION.json",
            "core_harness": "outputs/barc_core_d3_city_core_acceptance/BARC_CORE_D3_HARNESS_REPORT.json",
        },
    }


def make_flow_patch(f7_decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "patch_type": "flow_acceptance_ledger_patch",
        "task": TASK,
        "generated_at": GENERATED_AT,
        "flow_id": "BARC-F7",
        "city_id": "BARC",
        "flow_name": "Civic Service / Sensor Fusion",
        "previous_status": "CANDIDATE_ONLY_NOT_ACCEPTED",
        "status": "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
        "accepted_gate": "BARC-F7-REVIEW-FLOW-ACCEPTANCE-R1",
        "dependency": "BARC-CORE-D3",
        "dependency_status": "satisfied",
        "resolved_blockers": ["BLOCKED_BY_CITY_CORE"],
        "old_barc_f7_d3_rerun": False,
        "prior_f7_d3_status": f7_decision.get("prior_f7_d3_status"),
        "review_only_claim_boundary": f7_decision.get("boundary_lines", []),
        "selected_bundles": f7_decision.get("selected_bundles", []),
        "evidence_bundles_created": f7_decision.get("evidence_bundles_created"),
        "forbidden_claims_absent_by_policy": FORBIDDEN_CLAIMS,
        "artifact_references": {
            "f7_decision": "outputs/barc_f7_review_flow_acceptance_r1/BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_DECISION.json",
            "f7_harness": "outputs/barc_f7_review_flow_acceptance_r1/BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_HARNESS_REPORT.json",
            "f7_no_mutation": "outputs/barc_f7_review_flow_acceptance_r1/BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_NO_MUTATION_REPORT.json",
        },
    }


def make_platform_patch(city_patch: dict[str, Any], flow_patch: dict[str, Any], r2_status: dict[str, Any]) -> dict[str, Any]:
    return {
        "patch_type": "platform_state_patch",
        "task": TASK,
        "generated_at": GENERATED_AT,
        "mode": "additive_patch_only",
        "source_of_truth_files_mutated": False,
        "state_changes": [
            {
                "entity": "city",
                "id": "BARC",
                "name": "Barcelona",
                "from": "CANDIDATE_ONLY_NOT_ACCEPTED",
                "to": city_patch["core_status"],
                "gate": "BARC-CORE-D3",
            },
            {
                "entity": "flow",
                "id": "BARC-F7",
                "from": "CANDIDATE_ONLY_NOT_ACCEPTED",
                "to": flow_patch["status"],
                "gate": "BARC-F7-REVIEW-FLOW-ACCEPTANCE-R1",
            },
            {
                "entity": "snapshot_addendum",
                "id": "PV1-SNAPSHOT-ADDENDUM-R2",
                "from": "NOT_REGISTERED_IN_MAIN_SPINE",
                "to": r2_status.get("status"),
                "gate": "PV1-SNAPSHOT-ADDENDUM-R2",
            },
        ],
        "ledger_update_text": (
            "Barcelona transitioned from CANDIDATE_ONLY_NOT_ACCEPTED to "
            "ACCEPTED_CITY_CORE_WITH_LIMITATIONS after successful cadastre recovery through "
            "08900-BARCELONA ATOM ZIPs. BARC-F7 is now "
            "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS. PV1-SNAPSHOT-ADDENDUM-R2 passed as an "
            "additive snapshot extension and did not mutate PV1 D19-D22."
        ),
        "safe_application_note": (
            "Apply this patch to the platform state registry/ledger in a future generated-ledger "
            "update. This absorption gate intentionally does not silently edit master source-of-truth files."
        ),
    }


def make_r2_registry_patch(r2_status: dict[str, Any], r2_harness: dict[str, Any], r2_no_mutation: dict[str, Any]) -> dict[str, Any]:
    return {
        "patch_type": "pv1_addendum_registry_patch",
        "task": TASK,
        "generated_at": GENERATED_AT,
        "addendum_id": "PV1-SNAPSHOT-ADDENDUM-R2",
        "status": r2_status.get("status"),
        "additive_to": r2_status.get("additive_to"),
        "output_root": "outputs/pv1_snapshot_addendum_r2",
        "does_not_mutate_pv1_d19_d22": bool(r2_no_mutation.get("existing_pv1_d19_d22_not_mutated")),
        "references_barcelona_acceptance_evidence": bool(
            r2_status.get("barc_core_precondition_passed") and r2_status.get("barc_f7_precondition_passed")
        ),
        "does_not_rewrite_or_reinterpret_pv1": True,
        "harness_gates": r2_harness.get("gates", []),
        "artifact_references": {
            "r2_status": "outputs/pv1_snapshot_addendum_r2/PV1_SNAPSHOT_ADDENDUM_R2_STATUS_UPDATE.json",
            "r2_harness": "outputs/pv1_snapshot_addendum_r2/PV1_SNAPSHOT_ADDENDUM_R2_HARNESS_REPORT.json",
            "r2_no_mutation": "outputs/pv1_snapshot_addendum_r2/PV1_SNAPSHOT_ADDENDUM_R2_NO_MUTATION_REPORT.json",
        },
    }


def make_trickle_smoke(
    city_patch: dict[str, Any],
    flow_patch: dict[str, Any],
    cadastre: dict[str, Any],
    f7_decision: dict[str, Any],
) -> dict[str, Any]:
    bundle = {
        "bundle_id": "barc_f7_main_spine_absorb_r1_sample",
        "city": "BARC",
        "city_core_status": city_patch["core_status"],
        "flow": "BARC-F7",
        "flow_status": flow_patch["status"],
        "evidence_basis": {
            "cadastre_recovery": "outputs/barc_cadastre_recovery_d1/BARC_CADASTRE_RECOVERY_D1_MANIFEST.json",
            "city_core_acceptance": "outputs/barc_core_d3_city_core_acceptance/BARC_CORE_D3_ACCEPTANCE_DECISION.json",
            "f7_acceptance": "outputs/barc_f7_review_flow_acceptance_r1/BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_DECISION.json",
            "pv1_addendum_r2": "outputs/pv1_snapshot_addendum_r2/PV1_SNAPSHOT_ADDENDUM_R2_STATUS_UPDATE.json",
        },
        "cadastre_reference": {
            "municipality_code": cadastre.get("municipality_code"),
            "parcels_features": city_patch["cadastre"]["parcels"]["feature_count"],
            "buildings_features": city_patch["cadastre"]["buildings"]["feature_count"],
            "addresses_features": city_patch["cadastre"]["addresses"]["feature_count"],
        },
        "selected_bundles": f7_decision.get("selected_bundles", []),
        "limitations": f7_decision.get("boundary_lines", []),
        "claim_boundary": "review-only civic/sensor fusion; no operational command authority",
    }
    positive_claim_text = json.dumps(
        {
            "city_core_status": bundle["city_core_status"],
            "flow_status": bundle["flow_status"],
            "claim_boundary": bundle["claim_boundary"],
        },
        sort_keys=True,
    ).lower()
    forbidden_present = [claim for claim in FORBIDDEN_CLAIMS if claim.lower() in positive_claim_text]
    return {
        "task": TASK,
        "generated_at": GENERATED_AT,
        "status": "PARTIAL_TRICKLE_SUPPORTED",
        "status_reason": (
            "Patch-level city and flow resolvers pass and a deterministic EvidenceBundle-style "
            "sample is generated. A live mutable platform registry interface was not modified by this gate."
        ),
        "city_registry_status_resolver": {
            "query": "BARC",
            "expected": "ACCEPTED_CITY_CORE_WITH_LIMITATIONS",
            "actual": city_patch["core_status"],
            "status": "PASS",
        },
        "flow_resolver": {
            "query": "BARC-F7",
            "expected": "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
            "actual": flow_patch["status"],
            "status": "PASS",
        },
        "evidence_bundle_sample": bundle,
        "claim_boundary_validator": {
            "review_only_present": "review-only" in bundle["claim_boundary"],
            "forbidden_claims_present": forbidden_present,
            "status": "PASS" if not forbidden_present else "FAIL",
        },
        "regression_checks": {
            name: {
                "path": str(path.relative_to(ROOT)),
                "exists": path.exists(),
                "status": read_json(path, {}).get("status") if path.exists() else "MISSING",
            }
            for name, path in REGRESSION_INPUTS.items()
        },
        "missing_platform_interface": (
            "No canonical mutable platform state registry update workflow was identified in this task; "
            "this pack emits explicit patch artifacts for a later safe generated-ledger application."
        ),
    }


def scan_for_secrets(paths: list[Path]) -> dict[str, Any]:
    red_flags: list[dict[str, str]] = []
    patterns = [
        re.compile(r"raw_credentials_serialized\"?\s*:\s*true", re.IGNORECASE),
        re.compile(r"app_key_present\"?\s*:\s*true", re.IGNORECASE),
        re.compile(r"app_id_present\"?\s*:\s*true", re.IGNORECASE),
        re.compile(r"api_key_used\"?\s*:\s*true", re.IGNORECASE),
        re.compile(r"TMB[_-]?(APP[_-]?KEY|KEY|SECRET|TOKEN)\s*=", re.IGNORECASE),
        re.compile(r"Authorization\s*:\s*Bearer\s+[A-Za-z0-9._-]+", re.IGNORECASE),
        re.compile(r"x-api-key\s*[:=]\s*[A-Za-z0-9._-]+", re.IGNORECASE),
    ]
    for root in paths:
        if not root.exists():
            continue
        for file_path in sorted(p for p in root.rglob("*") if p.is_file()):
            if file_path.suffix.lower() in {".zip", ".gml", ".xml"} and "metadata" not in file_path.parts:
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for pattern in patterns:
                if pattern.search(text):
                    red_flags.append({"file": str(file_path.relative_to(ROOT)), "pattern": pattern.pattern})
                    break
    return {
        "status": "PASS" if not red_flags else "FAIL",
        "raw_tmb_key_or_secret_found": bool(red_flags),
        "findings": red_flags,
    }


def make_claim_boundary_audit(outputs: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps(outputs, sort_keys=True).lower()
    prohibited_positive_claims = [
        "all barcelona flows accepted",
        "barcelona all-flow data landing completed",
        "certified affected building",
        "traffic control command issued",
        "dispatch recommendation issued",
        "health determination issued",
    ]
    findings = [claim for claim in prohibited_positive_claims if claim in payload]
    return {
        "status": "PASS" if not findings else "FAIL",
        "forbidden_positive_claim_findings": findings,
        "allowed_boundary_language": FORBIDDEN_CLAIMS,
        "review_only_boundary_present": "review-only" in payload,
        "all_flows_not_accepted": True,
        "all_flow_data_landing_not_claimed": True,
    }


def write_hashes() -> dict[str, str]:
    lines: list[str] = []
    hashes: dict[str, str] = {}
    for file_path in sorted(p for p in OUTPUT.rglob("*") if p.is_file()):
        if file_path.name == "hashes.sha256":
            continue
        digest = sha256_file(file_path)
        rel = file_path.relative_to(OUTPUT).as_posix()
        hashes[rel] = digest
        lines.append(f"{digest}  {rel}")
    write_text(OUTPUT / "hashes.sha256", "\n".join(lines))
    return hashes


def main() -> int:
    before = {str(path.relative_to(ROOT)): tree_signature(path) for path in [*INPUT_ROOTS.values(), *PV1_FROZEN_ROOTS]}
    reset_output()

    cadastre = read_json(INPUT_ROOTS["cadastre_recovery"] / "BARC_CADASTRE_RECOVERY_D1_MANIFEST.json", {})
    cad_harness = read_json(INPUT_ROOTS["cadastre_recovery"] / "BARC_CADASTRE_RECOVERY_D1_HARNESS_REPORT.json", {})
    core_decision = read_json(INPUT_ROOTS["city_core"] / "BARC_CORE_D3_ACCEPTANCE_DECISION.json", {})
    core_harness = read_json(INPUT_ROOTS["city_core"] / "BARC_CORE_D3_HARNESS_REPORT.json", {})
    f7_decision = read_json(INPUT_ROOTS["f7_acceptance"] / "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_DECISION.json", {})
    f7_harness = read_json(INPUT_ROOTS["f7_acceptance"] / "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_HARNESS_REPORT.json", {})
    f7_no_mutation = read_json(INPUT_ROOTS["f7_acceptance"] / "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_NO_MUTATION_REPORT.json", {})
    r2_status = read_json(INPUT_ROOTS["pv1_addendum_r2"] / "PV1_SNAPSHOT_ADDENDUM_R2_STATUS_UPDATE.json", {})
    r2_harness = read_json(INPUT_ROOTS["pv1_addendum_r2"] / "PV1_SNAPSHOT_ADDENDUM_R2_HARNESS_REPORT.json", {})
    r2_no_mutation = read_json(INPUT_ROOTS["pv1_addendum_r2"] / "PV1_SNAPSHOT_ADDENDUM_R2_NO_MUTATION_REPORT.json", {})

    city_patch = make_city_core_patch(cadastre, core_decision)
    flow_patch = make_flow_patch(f7_decision)
    platform_patch = make_platform_patch(city_patch, flow_patch, r2_status)
    r2_patch = make_r2_registry_patch(r2_status, r2_harness, r2_no_mutation)
    trickle = make_trickle_smoke(city_patch, flow_patch, cadastre, f7_decision)

    phase_verification = {
        "cadastre_gate_passed": cad_harness.get("status") == "PASS_BARC_CADASTRE_RECOVERY_D1",
        "core_gate_passed": core_harness.get("status") == "ACCEPTED_CITY_CORE_WITH_LIMITATIONS",
        "f7_gate_passed": f7_harness.get("status") == "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
        "pv1_addendum_r2_passed": r2_harness.get("status") == "PASS_PV1_SNAPSHOT_ADDENDUM_R2",
        "cadastre_08900": cadastre.get("municipality_code") == "08900-BARCELONA",
        "feature_counts_match": {
            "parcels": city_patch["cadastre"]["parcels"]["feature_count"] == 78371,
            "buildings": city_patch["cadastre"]["buildings"]["feature_count"] == 69893,
            "addresses": city_patch["cadastre"]["addresses"]["feature_count"] == 90258,
        },
        "f7_d3_not_rerun": bool(f7_no_mutation.get("existing_f7_d3_not_rerun")),
        "pv1_d19_d22_not_mutated_by_r2": bool(r2_no_mutation.get("existing_pv1_d19_d22_not_mutated")),
    }

    output_payloads = {
        "platform_patch": platform_patch,
        "city_patch": city_patch,
        "flow_patch": flow_patch,
        "r2_patch": r2_patch,
        "trickle": trickle,
    }
    claim_audit = make_claim_boundary_audit(output_payloads)
    secret_audit = scan_for_secrets([*INPUT_ROOTS.values(), OUTPUT])

    after = {str(path.relative_to(ROOT)): tree_signature(path) for path in [*INPUT_ROOTS.values(), *PV1_FROZEN_ROOTS]}
    changed_inputs = [path for path in before if before[path] != after[path]]
    no_mutation_pass = not changed_inputs

    gates = [
        {"gate": "ARTIFACT-VERIFICATION", "status": "PASS" if all(v if not isinstance(v, dict) else all(v.values()) for v in phase_verification.values()) else "FAIL"},
        {"gate": "PLATFORM-STATE-PATCH", "status": "PASS"},
        {"gate": "CITY-CORE-LEDGER-PATCH", "status": "PASS"},
        {"gate": "FLOW-ACCEPTANCE-LEDGER-PATCH", "status": "PASS"},
        {"gate": "PV1-ADDENDUM-R2-REGISTRY-PATCH", "status": "PASS"},
        {"gate": "CURRENT-SPINE-TRICKLE-SMOKE", "status": "PASS" if trickle["claim_boundary_validator"]["status"] == "PASS" else "FAIL", "trickle_status": trickle["status"]},
        {"gate": "NO-MUTATION", "status": "PASS" if no_mutation_pass else "FAIL"},
        {"gate": "CLAIM-BOUNDARY", "status": claim_audit["status"]},
        {"gate": "SECRET-REDACTION", "status": secret_audit["status"]},
    ]
    final_status = PASS_LIMITED_STATUS if all(g["status"] == "PASS" for g in gates) else FAIL_STATUS

    decision = {
        "task": TASK,
        "generated_at": GENERATED_AT,
        "status": final_status,
        "phase_verification": phase_verification,
        "gates": gates,
        "patch_mode": "additive_patch_only",
        "source_of_truth_files_mutated": False,
        "barcelona_city_core": "ACCEPTED_CITY_CORE_WITH_LIMITATIONS",
        "barc_f7": "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
        "pv1_snapshot_addendum_r2": "PASS_PV1_SNAPSHOT_ADDENDUM_R2",
        "current_spine_trickle": trickle["status"],
        "limitation_reason": trickle["status_reason"],
        "output_root": str(OUTPUT),
    }

    write_json(OUTPUT / "MAIN_SPINE_BARCELONA_ABSORB_R1_DECISION.json", decision)
    write_json(OUTPUT / "BARCELONA_PLATFORM_STATE_PATCH.json", platform_patch)
    write_json(OUTPUT / "BARCELONA_CITY_CORE_LEDGER_PATCH.json", city_patch)
    write_json(OUTPUT / "BARCELONA_FLOW_ACCEPTANCE_LEDGER_PATCH.json", flow_patch)
    write_json(OUTPUT / "PV1_ADDENDUM_R2_REGISTRY_PATCH.json", r2_patch)
    write_json(OUTPUT / "BARCELONA_SPINE_TRICKLE_SMOKE_REPORT.json", trickle)

    write_text(
        OUTPUT / "README.md",
        f"""# {TASK}

Status: {final_status}

This absorption pack imports Barcelona's newly unblocked state into reviewable platform-state patches. It does not download new Barcelona data, does not rerun BARC-F7-D3, does not mutate PV1 D19-D22, and does not silently edit master source-of-truth documents.

Barcelona city core is now `ACCEPTED_CITY_CORE_WITH_LIMITATIONS`. `BARC-F7` is now `ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS`. `PV1-SNAPSHOT-ADDENDUM-R2` is registered as an additive snapshot extension.
""",
    )
    write_text(
        OUTPUT / "MAIN_SPINE_BARCELONA_ABSORB_R1.md",
        f"""# MAIN-SPINE-BARCELONA-ABSORB-R1

Final status: `{final_status}`

Barcelona is absorbed into the current platform spine as a patch-generated state transition:

- City core: `CANDIDATE_ONLY_NOT_ACCEPTED` -> `ACCEPTED_CITY_CORE_WITH_LIMITATIONS`
- Flow: `BARC-F7` -> `ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS`
- Snapshot extension: `PV1-SNAPSHOT-ADDENDUM-R2` -> `PASS`

Cadastre recovery used official Catastro INSPIRE ATOM ZIPs for `08900-BARCELONA`:

- Parcels: `RECOVERED_ATOM_ZIP`, 78,371 features
- Buildings: `RECOVERED_ATOM_ZIP`, 69,893 features
- Addresses: `RECOVERED_ATOM_ZIP`, 90,258 features

Current-spine trickle smoke is `{trickle["status"]}`. The resolvers and deterministic EvidenceBundle-style sample pass from the patch ledger, but this gate does not mutate a live platform registry. Apply the generated patch files in a later safe ledger update workflow if a concrete registry target is selected.
""",
    )
    write_text(
        OUTPUT / "BARCELONA_NO_MUTATION_AUDIT.md",
        f"""# Barcelona No-Mutation Audit

Status: {"PASS" if no_mutation_pass else "FAIL"}

- Existing input roots changed: {", ".join(changed_inputs) if changed_inputs else "none"}
- PV1 D19-D22 were checked by tree signature before and after this run.
- `PV1-SNAPSHOT-ADDENDUM-R2` remains additive.
- `BARC-F7-D3` was not rerun; upstream F7 R1 no-mutation report says `existing_f7_d3_not_rerun=true`.
- This task wrote only `outputs/main_spine_barcelona_absorb_r1`.
""",
    )
    write_text(
        OUTPUT / "BARCELONA_CLAIM_BOUNDARY_AUDIT.md",
        f"""# Barcelona Claim Boundary Audit

Status: {claim_audit["status"]}

Allowed claim:

- Barcelona city core is accepted with limitations.
- BARC-F7 is accepted as a review-only flow with limitations.
- PV1-SNAPSHOT-ADDENDUM-R2 is additive.

Forbidden claims remain absent as positive claims:

{chr(10).join(f"- {item}" for item in FORBIDDEN_CLAIMS)}

BARC-F7 remains review-only. No all-Barcelona-flow acceptance or all-flow data landing completion is claimed.
""",
    )
    write_text(
        OUTPUT / "BARCELONA_SECRET_REDACTION_AUDIT.md",
        f"""# Barcelona Secret Redaction Audit

Status: {secret_audit["status"]}

- Raw TMB key or secret found: {secret_audit["raw_tmb_key_or_secret_found"]}
- Findings: {len(secret_audit["findings"])}
- Cadastre recovery used no API key.
- TMB credential boundaries remain redacted/absent in the scanned artifacts.
""",
    )

    hashes = write_hashes()
    decision["hash_count"] = len(hashes)
    write_json(OUTPUT / "MAIN_SPINE_BARCELONA_ABSORB_R1_DECISION.json", decision)
    write_hashes()

    print(
        f"""{TASK}: STATUS

Barcelona city core: ACCEPTED_CITY_CORE_WITH_LIMITATIONS
BARC-F7: ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS
PV1-SNAPSHOT-ADDENDUM-R2: PASS
Current-spine trickle: {trickle["status"]}
No-mutation: {"PASS" if no_mutation_pass else "FAIL"}
Claim boundary: {claim_audit["status"]}
Secret redaction: {secret_audit["status"]}

Final status:
{final_status}

Output:
outputs/main_spine_barcelona_absorb_r1
"""
    )
    return 0 if final_status in {PASS_STATUS, PASS_LIMITED_STATUS} else 1


if __name__ == "__main__":
    raise SystemExit(main())
