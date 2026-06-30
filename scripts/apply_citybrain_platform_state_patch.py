from __future__ import annotations

import argparse
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
DEFAULT_PATCH = ROOT / "outputs" / "main_spine_barcelona_absorb_r1" / "BARCELONA_PLATFORM_STATE_PATCH.json"
DEFAULT_OUTPUT = ROOT / "outputs" / "platform_state_generated"
TASK = "CITYBRAIN-PLATFORM-STATE-GENERATED-LEDGER-APPLY"
GENERATED_STATE_VERSION = "platform_state_generated_v1"

FORBIDDEN_TRANSITIONS = {
    "ACCEPTED_CITY_CORE_FULL",
    "ACCEPTED_ALL_FLOWS",
    "PRODUCTION_READY",
    "PUBLIC_SAFETY_ACCEPTED",
    "TRAFFIC_CONTROL_ACCEPTED",
}

FORBIDDEN_POSITIVE_CLAIMS = [
    "barcelona all flows accepted",
    "barcelona production ready",
    "f7 can dispatch",
    "f7 can respond",
    "f7 can control",
    "certified affected buildings",
    "public safety command",
    "enforcement recommendation",
    "health determination",
    "traffic control command",
    "d19-d22 updated",
    "d19-d22 mutated",
]

BARC_F1F6_ALLOWED_STATUSES = {
    "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
    "ACCEPTED_CONTEXT_FLOW_WITH_LIMITATIONS",
    "NOT_ACCEPTED_AFTER_GATE_WITH_LIMITATIONS",
    "BLOCKED_AFTER_GATE_BY_MISSING_REQUIRED_SOURCE",
    "BLOCKED_AFTER_GATE_BY_PRIVACY_OR_LICENSE",
    "BLOCKED_AFTER_GATE_BY_PLATFORM_INTERFACE",
}

PV1_FROZEN_ROOTS = [
    ROOT / "outputs" / "pv1_d19_guardrail_action_policy_contract",
    ROOT / "outputs" / "pv1_d20_guardrail_enforcement_harness",
    ROOT / "outputs" / "pv1_d21_composite_platform_v1_snapshot",
    ROOT / "outputs" / "pv1_d22_final_platform_v1_audit",
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


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "exists": path.exists(),
        "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
        "bytes": path.stat().st_size if path.exists() and path.is_file() else None,
    }


def index_by_lane(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("lane")): row for row in rows if isinstance(row, dict) and row.get("lane")}


def flow_id_from_catalog_row(row: dict[str, Any]) -> str:
    if row.get("lane"):
        return str(row["lane"])
    city = str(row.get("city", "")).upper()
    flow = str(row.get("flow", "")).replace(" ", "")
    if city == "BARCELONA":
        city = "BARC"
    if city == "CHICAGO":
        city = "CHI"
    if city == "LONDON":
        city = "LON"
    return f"{city}-{flow}".strip("-")


def status_is_accepted(status: str) -> bool:
    return status in {
        "ACCEPTED_FLOW",
        "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
        "ACCEPTED_MOUNTED_EXTENSION",
        "ACCEPTED_CITY_CORE_WITH_LIMITATIONS",
        "ACCEPTED_CITY_CORE_WITH_SOURCE_LIMITATIONS",
    }


def load_artifacts(root: Path) -> dict[str, Any]:
    return {
        "catalog": read_json(root / "outputs/flowx_data_route_catalog_r1/FLOWX_DATA_ROUTE_CATALOG_R1_CITY_FLOW_MATURITY_MATRIX.json", {}),
        "review_ledger": read_json(root / "outputs/flowx_review_flow_acceptance_d1/FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_ACCEPTED_REVIEW_FLOW_LEDGER.json", {}),
        "pv1_harness": read_json(root / "outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate/PV1_D19D20D21D22_HARNESS_REPORT.json", {}),
        "pv1_addendum_r1": read_json(root / "outputs/pv1_snapshot_addendum_r1/PV1_SNAPSHOT_ADDENDUM_R1_STATUS_UPDATE.json", {}),
        "barc_city_patch": read_json(root / "outputs/main_spine_barcelona_absorb_r1/BARCELONA_CITY_CORE_LEDGER_PATCH.json", {}),
        "barc_flow_patch": read_json(root / "outputs/main_spine_barcelona_absorb_r1/BARCELONA_FLOW_ACCEPTANCE_LEDGER_PATCH.json", {}),
        "barc_r2_patch": read_json(root / "outputs/main_spine_barcelona_absorb_r1/PV1_ADDENDUM_R2_REGISTRY_PATCH.json", {}),
        "barc_cadastre_harness": read_json(root / "outputs/barc_cadastre_recovery_d1/BARC_CADASTRE_RECOVERY_D1_HARNESS_REPORT.json", {}),
        "barc_core_harness": read_json(root / "outputs/barc_core_d3_city_core_acceptance/BARC_CORE_D3_HARNESS_REPORT.json", {}),
        "barc_f7_harness": read_json(root / "outputs/barc_f7_review_flow_acceptance_r1/BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_HARNESS_REPORT.json", {}),
        "barc_r2_harness": read_json(root / "outputs/pv1_snapshot_addendum_r2/PV1_SNAPSHOT_ADDENDUM_R2_HARNESS_REPORT.json", {}),
    }


def seed_city_ledger() -> dict[str, dict[str, Any]]:
    return {
        "NYC": {
            "city_id": "NYC",
            "city_name": "New York City",
            "core_status": "ACCEPTED_CITY_CORE_WITH_SOURCE_LIMITATIONS",
            "accepted_gate": "NYC_ACCEPTED_BASELINE_FROM_EXISTING_FLOW_LEDGERS",
            "limitations": ["source-governed", "review-only mounted flows remain non-operational"],
            "artifact_references": ["outputs/flowx_review_flow_acceptance_d1", "outputs/flowx_data_route_catalog_r1"],
        },
        "CHI": {
            "city_id": "CHI",
            "city_name": "Chicago",
            "core_status": "ACCEPTED_CITY_CORE_WITH_SOURCE_LIMITATIONS",
            "accepted_gate": "CHI_F1F7_D5_ACCEPTED_BASELINE",
            "limitations": ["source-governed", "review-only mounted flows remain non-operational"],
            "artifact_references": ["outputs/flowx_review_flow_acceptance_d1", "outputs/flowx_data_route_catalog_r1"],
        },
        "LON": {
            "city_id": "LON",
            "city_name": "London",
            "core_status": "ACCEPTED_CITY_CORE_WITH_LIMITATIONS",
            "accepted_gate": "LON_D13C_ACCEPTED_BASELINE",
            "limitations": ["London accepted core limitations carried forward"],
            "artifact_references": ["outputs/flowx_data_route_catalog_r1", "outputs/lon_d13c_london_final_prehero_closure"],
        },
    }


def normalize_flow_status(row: dict[str, Any]) -> str:
    maturity = str(row.get("maturity_status", "UNKNOWN"))
    if maturity == "ACCEPTED":
        return "ACCEPTED_FLOW"
    if maturity == "ACCEPTED_MOUNTED_EXTENSION":
        return "ACCEPTED_MOUNTED_EXTENSION"
    if row.get("public_closeout_status") == "CANDIDATE_ONLY_NOT_ACCEPTED":
        return "CANDIDATE_ONLY_NOT_ACCEPTED"
    if maturity in {"DATA_ROUTE_READY", "CANDIDATE_REVIEW_READY", "SOURCE_READY", "EVIDENCE_READY", "BLOCKED_BY_DATA"}:
        return "NOT_ACCEPTED_REQUIRES_FLOW_ACCEPTANCE_GATE"
    return maturity or "UNKNOWN"


def seed_flow_ledger(artifacts: dict[str, Any]) -> dict[str, dict[str, Any]]:
    flow_ledger: dict[str, dict[str, Any]] = {}
    for row in artifacts["catalog"].get("lanes", []):
        if not isinstance(row, dict):
            continue
        flow_id = flow_id_from_catalog_row(row)
        if not flow_id or flow_id == "-":
            continue
        status = normalize_flow_status(row)
        city_raw = str(row.get("city", "")).lower()
        city_id = {"nyc": "NYC", "chicago": "CHI", "london": "LON", "barcelona": "BARC", "singapore": "SG"}.get(city_raw, str(row.get("city", "")).upper())
        flow_ledger[flow_id] = {
            "flow_id": flow_id,
            "city_id": city_id,
            "flow": row.get("flow") or row.get("flow_family"),
            "flow_name": row.get("flow_name") or row.get("flow"),
            "status": status,
            "accepted_gate": row.get("evidence"),
            "blockers": row.get("blockers", []),
            "blocker_status": "ACTIVE" if row.get("blockers") else "NONE",
            "claim_boundary": row.get("boundary") or "; ".join(row.get("limitations", [])),
            "route_endpoint": row.get("route_endpoint"),
            "artifact_references": row.get("d4_payload_refs", []),
            "source_lineage_refs": row.get("source_lineage_refs", []),
            "limitations": row.get("limitations", []),
        }
    for lane in artifacts["review_ledger"].get("lanes", []):
        flow_id = str(lane["lane"])
        city_id = "NYC" if flow_id.startswith("NYC-") else "CHI" if flow_id.startswith("CHI-") else "UNKNOWN"
        flow_ledger[flow_id] = {
            **flow_ledger.get(flow_id, {}),
            "flow_id": flow_id,
            "city_id": city_id,
            "status": lane.get("post_pv1_decision"),
            "accepted_gate": "FLOWX-REVIEW-FLOW-ACCEPTANCE-D1",
            "blockers": [],
            "blocker_status": "RESOLVED_BY_REVIEW_FLOW_ACCEPTANCE_POLICY",
            "claim_boundary": "review-only accepted flow with limitations",
            "route_endpoint": lane.get("route_endpoint"),
            "limitations": lane.get("limitations", []),
        }
    return flow_ledger


def seed_addendum_registry(artifacts: dict[str, Any]) -> dict[str, dict[str, Any]]:
    addenda: dict[str, dict[str, Any]] = {}
    if artifacts["pv1_addendum_r1"].get("status"):
        addenda["PV1-SNAPSHOT-ADDENDUM-R1"] = {
            "addendum_id": "PV1-SNAPSHOT-ADDENDUM-R1",
            "status": artifacts["pv1_addendum_r1"]["status"],
            "relationship_to_d19_d22": "additive, no mutation",
            "artifact_references": ["outputs/pv1_snapshot_addendum_r1"],
        }
    return addenda


def validate_patch(patch: dict[str, Any], artifacts: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    state_changes = patch.get("state_changes", [])
    if not state_changes:
        errors.append("patch has no state_changes")
    for change in state_changes:
        target = str(change.get("to", ""))
        if target in FORBIDDEN_TRANSITIONS:
            errors.append(f"forbidden transition target: {target}")
    text = json.dumps(patch, sort_keys=True).lower()
    for phrase in FORBIDDEN_POSITIVE_CLAIMS:
        if phrase in text:
            errors.append(f"forbidden positive claim found in patch: {phrase}")
    expected = {
        "cadastre": artifacts["barc_cadastre_harness"].get("status") == "PASS_BARC_CADASTRE_RECOVERY_D1",
        "core": artifacts["barc_core_harness"].get("status") == "ACCEPTED_CITY_CORE_WITH_LIMITATIONS",
        "f7": artifacts["barc_f7_harness"].get("status") == "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
        "r2": artifacts["barc_r2_harness"].get("status") == "PASS_PV1_SNAPSHOT_ADDENDUM_R2",
    }
    for name, ok in expected.items():
        if not ok:
            errors.append(f"required source artifact not passed: {name}")
    return errors


def apply_barcelona(
    city_ledger: dict[str, dict[str, Any]],
    flow_ledger: dict[str, dict[str, Any]],
    addendum_registry: dict[str, dict[str, Any]],
    artifacts: dict[str, Any],
) -> None:
    city_patch = artifacts["barc_city_patch"]
    flow_patch = artifacts["barc_flow_patch"]
    r2_patch = artifacts["barc_r2_patch"]
    city_ledger["BARC"] = {
        "city_id": "BARC",
        "city_name": "Barcelona",
        "core_status": "ACCEPTED_CITY_CORE_WITH_LIMITATIONS",
        "accepted_gate": "BARC-CORE-D3",
        "source_dependency": "BARC-CADASTRE-RECOVERY-D1",
        "addendum_dependency": "PV1-SNAPSHOT-ADDENDUM-R2",
        "limitations": city_patch.get("accepted_limitations", []),
        "cadastre": city_patch.get("cadastre", {}),
        "license_privacy_notes": city_patch.get("license_privacy_notes", []),
        "artifact_references": city_patch.get("artifact_references", {}),
    }
    for flow_num in range(1, 7):
        flow_id = f"BARC-F{flow_num}"
        prior = flow_ledger.get(flow_id, {})
        blockers = [b for b in prior.get("blockers", []) if b != "BLOCKED_BY_CITY_CORE"]
        flow_ledger[flow_id] = {
            **prior,
            "flow_id": flow_id,
            "city_id": "BARC",
            "flow": f"F{flow_num}",
            "status": "NOT_ACCEPTED_REQUIRES_FLOW_ACCEPTANCE_GATE",
            "accepted_gate": None,
            "dependency": "BARC-CORE-D3",
            "dependency_status": "satisfied",
            "resolved_blockers": ["BLOCKED_BY_CITY_CORE"] if "BLOCKED_BY_CITY_CORE" in prior.get("blockers", []) else [],
            "blockers": [*blockers, "FLOW_ACCEPTANCE_GATE_NOT_RUN"],
            "blocker_status": "ACTIVE_NON_CITY_CORE_BLOCKER",
            "claim_boundary": "candidate/source context only; not accepted by Barcelona full absorb",
        }
    flow_ledger["BARC-F7"] = {
        **flow_ledger.get("BARC-F7", {}),
        "flow_id": "BARC-F7",
        "city_id": "BARC",
        "flow": "F7",
        "flow_name": "Civic Service / Sensor Fusion",
        "status": "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
        "accepted_gate": "BARC-F7-REVIEW-FLOW-ACCEPTANCE-R1",
        "dependency": "BARC-CORE-D3",
        "dependency_status": "satisfied",
        "old_blocker": "BLOCKED_BY_CITY_CORE",
        "blocker_status": "RESOLVED",
        "old_barc_f7_d3_rerun": False,
        "claim_boundary": "review-only",
        "limitations": flow_patch.get("review_only_claim_boundary", []),
        "selected_bundles": flow_patch.get("selected_bundles", []),
        "artifact_references": flow_patch.get("artifact_references", {}),
    }
    addendum_registry["PV1-SNAPSHOT-ADDENDUM-R2"] = {
        "addendum_id": "PV1-SNAPSHOT-ADDENDUM-R2",
        "status": "PASS_PV1_SNAPSHOT_ADDENDUM_R2",
        "relationship_to_d19_d22": "additive, no mutation",
        "includes_barcelona_city_core_acceptance": True,
        "includes_barcelona_f7_review_flow_acceptance": True,
        "does_not_rewrite_or_reinterpret_pv1": True,
        "artifact_references": r2_patch.get("artifact_references", {}),
    }


def validate_barc_f1f6_patch(patch: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not patch:
        return errors
    decisions = patch.get("flow_decisions", {})
    if not isinstance(decisions, dict):
        return ["flow patch missing flow_decisions object"]
    expected = {f"BARC-F{idx}" for idx in range(1, 7)}
    actual = set(decisions)
    missing = sorted(expected - actual)
    extra = sorted(flow_id for flow_id in actual if flow_id.startswith("BARC-F") and flow_id not in expected)
    if missing:
        errors.append(f"flow patch missing decisions: {', '.join(missing)}")
    if extra:
        errors.append(f"flow patch includes unsupported Barcelona closeout flows: {', '.join(extra)}")
    for flow_id in sorted(expected & actual):
        decision = decisions.get(flow_id, {})
        status = str(decision.get("final_decision") or decision.get("status") or "")
        if status not in BARC_F1F6_ALLOWED_STATUSES:
            errors.append(f"{flow_id} has unsupported final decision: {status}")
        if decision.get("dependency_status") != "satisfied":
            errors.append(f"{flow_id} does not preserve satisfied city-core dependency")
        if not decision.get("flow_acceptance_gate_run"):
            errors.append(f"{flow_id} does not mark flow_acceptance_gate_run")
        if "FLOW_ACCEPTANCE_GATE_NOT_RUN" not in decision.get("closed_blockers", []):
            errors.append(f"{flow_id} does not close FLOW_ACCEPTANCE_GATE_NOT_RUN")
    text = json.dumps(patch, sort_keys=True).lower()
    forbidden_exact = [
        "barcelona all flows accepted",
        "accepted_all_flows",
        "production_ready",
        "d19-d22 mutated",
        "d19-d22 updated",
    ]
    for phrase in forbidden_exact:
        if phrase in text:
            errors.append(f"forbidden closeout patch claim: {phrase}")
    return errors


def apply_barc_f1f6_closeout(
    flow_ledger: dict[str, dict[str, Any]],
    addendum_registry: dict[str, dict[str, Any]],
    patch: dict[str, Any],
) -> list[str]:
    errors = validate_barc_f1f6_patch(patch)
    if errors or not patch:
        return errors

    decisions = patch["flow_decisions"]
    for flow_id in [f"BARC-F{idx}" for idx in range(1, 7)]:
        decision = decisions[flow_id]
        final_status = decision.get("final_decision") or decision.get("status")
        prior = flow_ledger.get(flow_id, {})
        prior_resolved = list(prior.get("resolved_blockers", []))
        resolved = []
        for blocker in [*prior_resolved, "BLOCKED_BY_CITY_CORE", "FLOW_ACCEPTANCE_GATE_NOT_RUN"]:
            if blocker not in resolved:
                resolved.append(blocker)
        remaining_blockers = [
            blocker
            for blocker in prior.get("blockers", [])
            if blocker not in {"BLOCKED_BY_CITY_CORE", "FLOW_ACCEPTANCE_GATE_NOT_RUN"}
            and blocker not in set(decision.get("limitations_carried_forward", []))
        ]
        if str(final_status).startswith("ACCEPTED"):
            blocker_status = "RESOLVED_BY_FLOW_ACCEPTANCE_GATE_WITH_LIMITATIONS"
            remaining_blockers = []
        else:
            blocker_status = "GATE_RUN_NOT_ACCEPTED_WITH_LIMITATIONS"

        flow_ledger[flow_id] = {
            **prior,
            "flow_id": flow_id,
            "city_id": "BARC",
            "flow": decision.get("flow", prior.get("flow")),
            "flow_name": decision.get("flow_name", prior.get("flow_name")),
            "status": final_status,
            "final_decision": final_status,
            "accepted_gate": decision.get("gate_id") if str(final_status).startswith("ACCEPTED") else None,
            "gate_id": decision.get("gate_id"),
            "flow_acceptance_gate_run": True,
            "dependency": "BARC-CORE-D3",
            "dependency_status": "satisfied",
            "resolved_blockers": resolved,
            "closed_blockers": decision.get("closed_blockers", []),
            "blockers": remaining_blockers,
            "blocker_status": blocker_status,
            "limitations": decision.get("limitations", []),
            "claim_boundary": decision.get("claim_boundary"),
            "privacy_boundary": decision.get("privacy_boundary"),
            "artifact_references": decision.get("artifact_references", {}),
            "source_lineage_refs": decision.get("source_lineage_refs", []),
            "source_evidence_counts": decision.get("source_evidence_counts", {}),
            "evidencebundle_smoke": decision.get("evidencebundle_smoke", {}),
            "route_endpoint": decision.get("route_endpoint"),
        }

    addendum = patch.get("pv1_snapshot_addendum_r3", {})
    if addendum:
        addendum_registry["PV1-SNAPSHOT-ADDENDUM-R3"] = {
            "addendum_id": "PV1-SNAPSHOT-ADDENDUM-R3",
            "status": addendum.get("status", "PASS_PV1_SNAPSHOT_ADDENDUM_R3"),
            "relationship_to_d19_d22": "additive, no mutation",
            "relationship_to_r2": "additive, no mutation",
            "includes_barcelona_f1_f6_flow_gate_decisions": True,
            "does_not_create_blanket_flow_acceptance": True,
            "artifact_references": addendum.get("artifact_references", {}),
            "flow_decisions": addendum.get("flow_decisions", {}),
        }
    return []


def build_resolver_inputs(
    city_ledger: dict[str, dict[str, Any]],
    flow_ledger: dict[str, dict[str, Any]],
    addendum_registry: dict[str, dict[str, Any]],
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    aliases = {
        "barcelona": "BARC",
        "bcn": "BARC",
        "new york city": "NYC",
        "nyc": "NYC",
        "chicago": "CHI",
        "chi": "CHI",
        "london": "LON",
        "lon": "LON",
    }
    return {
        "state_version": GENERATED_STATE_VERSION,
        "cities_by_id": city_ledger,
        "city_aliases": aliases,
        "flows_by_id": flow_ledger,
        "pv1_snapshot": {
            "snapshot_id": "PV1-D19/D20/D21/D22",
            "status": artifacts["pv1_harness"].get("status"),
            "relationship": "frozen base snapshot",
            "artifact_references": ["outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate"],
        },
        "addenda_by_id": addendum_registry,
    }


def make_platform_state(
    city_ledger: dict[str, dict[str, Any]],
    flow_ledger: dict[str, dict[str, Any]],
    addendum_registry: dict[str, dict[str, Any]],
    resolver_inputs: dict[str, Any],
) -> dict[str, Any]:
    return {
        "state_version": GENERATED_STATE_VERSION,
        "state_root": "outputs/platform_state_generated",
        "source_mode": "generated_ledger_from_accepted_gate_artifacts",
        "city_count": len(city_ledger),
        "flow_count": len(flow_ledger),
        "pv1_addendum_count": len(addendum_registry),
        "barcelona": {
            "city_core_status": city_ledger["BARC"]["core_status"],
            "f1_f6_gate_status": "FLOW_GATES_RUN"
            if all(flow_ledger.get(f"BARC-F{idx}", {}).get("flow_acceptance_gate_run") for idx in range(1, 7))
            else "FLOW_GATES_NOT_RUN",
            "barc_f7_status": flow_ledger["BARC-F7"]["status"],
            "pv1_addendum_r2_status": addendum_registry["PV1-SNAPSHOT-ADDENDUM-R2"]["status"],
            "pv1_addendum_r3_status": addendum_registry.get("PV1-SNAPSHOT-ADDENDUM-R3", {}).get("status"),
            "blanket_flow_acceptance": False,
        },
        "resolver_inputs_path": "outputs/platform_state_generated/CITYBRAIN_RESOLVER_INPUTS.json",
        "ledgers": {
            "city_core": "outputs/platform_state_generated/CITYBRAIN_CITY_CORE_LEDGER.json",
            "flow_acceptance": "outputs/platform_state_generated/CITYBRAIN_FLOW_ACCEPTANCE_LEDGER.json",
            "pv1_addenda": "outputs/platform_state_generated/CITYBRAIN_PV1_ADDENDUM_REGISTRY.json",
        },
    }


def diff_json(before: Any, after: Any) -> str:
    before_text = json.dumps(clean(before or {}), indent=2, sort_keys=True).splitlines()
    after_text = json.dumps(clean(after or {}), indent=2, sort_keys=True).splitlines()
    return "\n".join(difflib.unified_diff(before_text, after_text, fromfile="before", tofile="after", lineterm=""))


def backup_previous(output_dir: Path) -> Path | None:
    state_file = output_dir / "CITYBRAIN_PLATFORM_STATE.json"
    if not state_file.exists():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = output_dir / "backups" / stamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    for name in [
        "CITYBRAIN_PLATFORM_STATE.json",
        "CITYBRAIN_CITY_CORE_LEDGER.json",
        "CITYBRAIN_FLOW_ACCEPTANCE_LEDGER.json",
        "CITYBRAIN_PV1_ADDENDUM_REGISTRY.json",
        "CITYBRAIN_RESOLVER_INPUTS.json",
        "CITYBRAIN_PLATFORM_STATE_APPLY_LOG.json",
    ]:
        src = output_dir / name
        if src.exists():
            shutil.copy2(src, backup_dir / name)
    return backup_dir


def apply_platform_state_patch(
    patch_path: Path = DEFAULT_PATCH,
    output_dir: Path = DEFAULT_OUTPUT,
    flow_patch_path: Path | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    before_signatures = {path.relative_to(ROOT).as_posix(): tree_signature(path) for path in PV1_FROZEN_ROOTS}
    before_state = read_json(output_dir / "CITYBRAIN_PLATFORM_STATE.json", {})
    backup_dir = backup_previous(output_dir)

    patch = read_json(patch_path, {})
    flow_patch = read_json(flow_patch_path, {}) if flow_patch_path and flow_patch_path.exists() else {}
    artifacts = load_artifacts(ROOT)
    validation_errors = validate_patch(patch, artifacts)
    flow_patch_errors: list[str] = []

    city_ledger = seed_city_ledger()
    flow_ledger = seed_flow_ledger(artifacts)
    addendum_registry = seed_addendum_registry(artifacts)
    if not validation_errors:
        apply_barcelona(city_ledger, flow_ledger, addendum_registry, artifacts)
    if not validation_errors and flow_patch:
        flow_patch_errors = apply_barc_f1f6_closeout(flow_ledger, addendum_registry, flow_patch)
    resolver_inputs = build_resolver_inputs(city_ledger, flow_ledger, addendum_registry, artifacts)
    platform_state = make_platform_state(city_ledger, flow_ledger, addendum_registry, resolver_inputs)

    write_json(output_dir / "CITYBRAIN_CITY_CORE_LEDGER.json", city_ledger)
    write_json(output_dir / "CITYBRAIN_FLOW_ACCEPTANCE_LEDGER.json", flow_ledger)
    write_json(output_dir / "CITYBRAIN_PV1_ADDENDUM_REGISTRY.json", addendum_registry)
    write_json(output_dir / "CITYBRAIN_RESOLVER_INPUTS.json", resolver_inputs)
    write_json(output_dir / "CITYBRAIN_PLATFORM_STATE.json", platform_state)

    after_signatures = {path.relative_to(ROOT).as_posix(): tree_signature(path) for path in PV1_FROZEN_ROOTS}
    mutated_pv1 = [key for key in before_signatures if before_signatures[key] != after_signatures[key]]
    after_state = read_json(output_dir / "CITYBRAIN_PLATFORM_STATE.json", {})
    before_after_diff = diff_json(before_state, after_state)

    apply_log = {
        "task": TASK,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "PASS" if not validation_errors and not flow_patch_errors and not mutated_pv1 else "FAIL",
        "patch_path": patch_path.relative_to(ROOT).as_posix(),
        "flow_patch_path": flow_patch_path.relative_to(ROOT).as_posix() if flow_patch_path else None,
        "flow_patch_applied": bool(flow_patch) and not flow_patch_errors,
        "output_dir": output_dir.relative_to(ROOT).as_posix(),
        "backup_dir": backup_dir.relative_to(ROOT).as_posix() if backup_dir else None,
        "validation_errors": validation_errors,
        "flow_patch_errors": flow_patch_errors,
        "allowed_transitions": {
            "BARC": "CANDIDATE_ONLY_NOT_ACCEPTED_OR_ABSENT_TO_ACCEPTED_CITY_CORE_WITH_LIMITATIONS",
            "BARC-F7": "CANDIDATE_OR_BLOCKED_TO_ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
            "PV1-SNAPSHOT-ADDENDUM-R2": "ADDITIVE_PASS_REGISTRATION",
        },
        "rejected_transition_classes": sorted(FORBIDDEN_TRANSITIONS),
        "pv1_d19_d22_mutated": bool(mutated_pv1),
        "mutated_pv1_roots": mutated_pv1,
        "before_after_diff_path": "outputs/platform_state_generated/CITYBRAIN_PLATFORM_STATE_BEFORE_AFTER.diff",
        "written_files": [
            "CITYBRAIN_PLATFORM_STATE.json",
            "CITYBRAIN_CITY_CORE_LEDGER.json",
            "CITYBRAIN_FLOW_ACCEPTANCE_LEDGER.json",
            "CITYBRAIN_PV1_ADDENDUM_REGISTRY.json",
            "CITYBRAIN_RESOLVER_INPUTS.json",
        ],
    }
    write_json(output_dir / "CITYBRAIN_PLATFORM_STATE_APPLY_LOG.json", apply_log)
    write_text(output_dir / "CITYBRAIN_PLATFORM_STATE_BEFORE_AFTER.diff", before_after_diff or "No platform-state JSON diff.")
    return {
        "status": apply_log["status"],
        "apply_log": apply_log,
        "platform_state": platform_state,
        "city_ledger": city_ledger,
        "flow_ledger": flow_ledger,
        "addendum_registry": addendum_registry,
        "resolver_inputs": resolver_inputs,
        "before_after_diff": before_after_diff,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a CityBrain generated platform-state patch.")
    parser.add_argument("--patch", default=str(DEFAULT_PATCH))
    parser.add_argument("--flow-patch", default=None)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    flow_patch = Path(args.flow_patch).resolve() if args.flow_patch else None
    result = apply_platform_state_patch(Path(args.patch).resolve(), Path(args.output).resolve(), flow_patch)
    print(json.dumps({"status": result["status"], "output_dir": str(Path(args.output).resolve())}, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
