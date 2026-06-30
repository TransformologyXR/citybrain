from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
from pathlib import Path
from typing import Any, Iterable


GENERATION_VERSION = "PV1-SDF-D1-D6-v1"
GENERATION_SEED = 12345
GENERATED_AT_UTC = "2026-06-27T12:00:00+00:00"
PACK_ID = "sdf_chi_near_west_side_v1"
PACK_LABEL = "SDF-CHI-NEAR-WEST-SIDE-v1"
SAFE_ID_SCOPE = "chi_near_west_side_v1"
CLAIM_LABEL = "[S]"

REQUIRED_SYNTHETIC_METADATA_FIELDS = [
    "claim_label",
    "synthetic",
    "source_basis",
    "donor_city",
    "donor_artifact",
    "generation_version",
    "random_seed",
    "generated_at_utc",
    "validation_status",
    "not_real_world_observation",
]

SYNTHETIC_ENTITY_TYPES = [
    "SyntheticArea",
    "SyntheticAddressableLocation",
    "SyntheticParcel",
    "SyntheticBuilding",
    "SyntheticRoadSegment",
    "SyntheticTransitNode",
    "SyntheticFacility",
    "SyntheticSensor",
    "SyntheticOrganization",
    "SyntheticEvent",
    "SyntheticObservation",
    "SyntheticActionProposal",
]

DIRTY_VARIANT_TYPES = [
    "missing_id",
    "duplicate_record",
    "conflicting_timestamp",
    "geometry_jitter",
    "address_truncation",
    "case_mismatch",
    "schema_drift",
    "wrong_area_label",
    "late_arrival",
    "out_of_order_event",
    "stale_status",
    "partial_join_key",
    "fuzzy_name_variant",
]

ALLOWED_ACTION_PROPOSAL_TYPES = [
    "analyst_review",
    "field_review_candidate",
    "data_quality_review",
    "source_followup",
    "simulation_run_request",
]

FORBIDDEN_ACTION_PROPOSAL_TYPES = [
    "dispatch_emergency_unit",
    "enforce_violation",
    "police_action",
    "health_order",
    "public_safety_instruction",
    "traffic_control_order",
]


def project_path(project_root: str | Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return Path(project_root).resolve() / path


def clean_value(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            return clean_value(value.item())
        except Exception:
            pass
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {str(k): clean_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_value(v) for v in value]
    return value


def read_json(path: str | Path, default: Any = None) -> Any:
    path = Path(path)
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\bNaN\b", "null", text)
    return json.loads(text)


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_value(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(clean_value(row), sort_keys=True, ensure_ascii=False) + "\n")
            count += 1
    return count


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def reset_dir(path: str | Path, project_root: str | Path, required_token: str = "pv1_sdf") -> Path:
    path = Path(path)
    resolved = path.resolve()
    root = Path(project_root).resolve()
    if path.exists():
        resolved_text = str(resolved).lower()
        root_text = str(root).lower()
        token = required_token.lower()
        if not resolved_text.startswith(root_text) or token not in resolved_text:
            raise ValueError(f"refusing to remove unexpected directory: {resolved}")
        shutil.rmtree(resolved)
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_dirs(*paths: str | Path) -> None:
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def synthetic_metadata(
    source_basis: str,
    donor_city: str = "chicago",
    donor_artifact: str = "CHI-F1F7-D5 + CHI-D3B aggregate donor distributions",
    validation_status: str = "PASS",
) -> dict[str, Any]:
    return {
        "claim_label": CLAIM_LABEL,
        "synthetic": True,
        "source_basis": source_basis,
        "donor_city": donor_city,
        "donor_artifact": donor_artifact,
        "generation_version": GENERATION_VERSION,
        "random_seed": GENERATION_SEED,
        "generated_at_utc": GENERATED_AT_UTC,
        "validation_status": validation_status,
        "not_real_world_observation": True,
    }


def with_metadata(row: dict[str, Any], source_basis: str, donor_city: str = "chicago", donor_artifact: str | None = None) -> dict[str, Any]:
    merged = dict(row)
    merged.update(
        synthetic_metadata(
            source_basis=source_basis,
            donor_city=donor_city,
            donor_artifact=donor_artifact or "CHI-F1F7-D5 + CHI-D3B aggregate donor distributions",
        )
    )
    return merged


def synthetic_id(entity: str, number: int | str) -> str:
    return f"synthetic:{entity}:{SAFE_ID_SCOPE}:{number}"


def source_record_id(prefix: str, number: int) -> str:
    return f"SYN-{prefix}-{number:06d}"


def required_metadata_present(row: dict[str, Any]) -> bool:
    return all(row.get(field) is not None for field in REQUIRED_SYNTHETIC_METADATA_FIELDS) and row.get("claim_label") == CLAIM_LABEL


def status_is_pass(value: Any) -> bool:
    text = str(value or "").upper()
    return text.startswith("PASS") or text.startswith("GREEN")


def gate(gate_id: str, ok: bool, **details: Any) -> dict[str, Any]:
    payload = {"gate": gate_id, "status": "PASS" if ok else "FAIL"}
    payload.update(details)
    return payload


def all_gates_pass(gates: Iterable[dict[str, Any]], allowed: set[str] | None = None) -> bool:
    allowed = allowed or {"PASS"}
    return all(g.get("status") in allowed for g in gates)


def safe_json_dumps(value: Any) -> str:
    return json.dumps(clean_value(value), sort_keys=True, ensure_ascii=False)


def parse_json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    try:
        loaded = json.loads(str(value))
        return loaded if isinstance(loaded, list) else [loaded]
    except Exception:
        return []


def no_overclaim_scan(paths: Iterable[str | Path]) -> dict[str, Any]:
    patterns = [
        r"\bsynthetic data is real observed data\b",
        r"\bplatform v1 is complete\b",
        r"\bautonomous public-safety response\b",
        r"\bemergency dispatch recommendation\b",
        r"\bpolicing recommendation is\b",
        r"\benforcement action is approved\b",
        r"\bhealth determination is\b",
        r"\bcertified affected building\b",
        r"\breal-time city operational instruction\b",
        r"\bsynthetic records are official city records\b",
    ]
    findings: list[dict[str, Any]] = []
    checked = 0
    for root in paths:
        root = Path(root)
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt"}:
                continue
            checked += 1
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            for pattern in patterns:
                if re.search(pattern, text):
                    findings.append({"path": str(path), "pattern": pattern})
    return {
        "status": "PASS" if not findings else "FAIL",
        "checked_files": checked,
        "findings": findings,
        "policy": "Synthetic outputs stay labelled [S], review-only, and bounded to development, validation, replay, demonstration, and adversarial testing.",
    }


def write_stage_readme(path: str | Path, title: str, lines: list[str]) -> None:
    body = [f"# {title}", "", f"Generated by {GENERATION_VERSION} for {PACK_LABEL}.", ""]
    body.extend(lines)
    write_text(path, "\n".join(body))


def file_inventory(root: str | Path) -> list[dict[str, Any]]:
    root = Path(root)
    rows: list[dict[str, Any]] = []
    if not root.exists():
        return rows
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rows.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size})
    return rows
