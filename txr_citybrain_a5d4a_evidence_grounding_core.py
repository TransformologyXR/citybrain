"""
A5-D4A EvidenceBundle v1 and grounded narration core.

This is the minimal governed evidence layer used by A5-D4B. It keeps truth in
deterministic A5-D1 retrieval, normalizes the result into EvidenceBundle v1, and
checks narration against the deterministic evidence with the A5 grounding gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from txr_citybrain_a5_narration_grounded_gate import run_grounding_gate
from txr_citybrain_a5d1_operator_query import BOUNDARY_STATEMENT, DistrictGraph


ROOT = Path(__file__).resolve().parent
DEFAULT_A4D2_DIR = ROOT / "outputs" / "a5_dob_district_enrichment"
DEFAULT_A5D1_DIR = ROOT / "outputs" / "a5d1_operator_query"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "a5d4a_evidence_grounding_core"

HERO_BBL = "1010607502"
SECOND_SUBJECT_BBL = "1010600029"
EVIDENCE_SCHEMA_VERSION = "EvidenceBundle.v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_payload(value: Any) -> str:
    return sha256_text(canonical_json(value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def hash_tree(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(p for p in root.rglob("*") if p.is_file())
    }


def output_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json")
    }


def sorted_records(records: list[dict[str, Any]], *keys: str) -> list[dict[str, Any]]:
    def key(record: dict[str, Any]) -> tuple[str, ...]:
        return tuple(str(record.get(k) or "") for k in keys)

    return sorted(records, key=key)


def role_counts(linked_parties_by_role: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    return {role: len(values) for role, values in sorted(linked_parties_by_role.items())}


def normalize_to_evidence_bundle(query_result: dict[str, Any], subject_label: str) -> dict[str, Any]:
    evidence = query_result["evidence_bundle"]
    parcel = evidence.get("parcel") or {}
    bbl = str((query_result.get("input") or {}).get("bbl") or parcel.get("canonical_id", "").rsplit(":", 1)[-1])
    subject_id = parcel.get("canonical_id") or f"parcel:us-nyc:bbl:{bbl}"
    entities = sorted_records(evidence.get("entities", []), "canonical_id", "entity_type")
    edges = sorted_records(evidence.get("edges", []), "edge_id", "src", "dst", "relation")
    linked_buildings = sorted_records(evidence.get("linked_buildings", []), "canonical_id")
    linked_permits = sorted_records(evidence.get("linked_permits", []), "canonical_id")
    linked_complaints = sorted_records(evidence.get("linked_complaints", []), "canonical_id")
    linked_parties_by_role = evidence.get("linked_parties_by_role", {})
    normalized = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "bundle_id": f"evidence_bundle:v1:{subject_id}",
        "subject_label": subject_label,
        "subject": {
            "subject_type": "parcel",
            "subject_id": subject_id,
            "bbl": bbl,
        },
        "tool_name": "citybrain_operator_query",
        "query_type": "parcel_profile",
        "query": {
            "query_type": "parcel_profile",
            "bbl": bbl,
        },
        "boundary_statement": BOUNDARY_STATEMENT,
        "deterministic_plan": evidence.get("deterministic_plan", []),
        "counts": evidence.get("counts", {}),
        "answer_facts": evidence.get("answer_facts", []),
        "confidence_summary": evidence.get("confidence_summary", []),
        "provenance_summary": evidence.get("provenance_summary", []),
        "entities": entities,
        "edges": edges,
        "parcel": parcel,
        "linked_buildings": linked_buildings,
        "linked_permits": linked_permits,
        "linked_complaints": linked_complaints,
        "linked_parties_by_role": linked_parties_by_role,
        "party_role_counts": role_counts(linked_parties_by_role),
        "source_query_result_hash": sha256_payload(query_result),
        "truth_policy": "Counts and graph facts are computed by deterministic retrieval over canonical a4-D2 artifacts. Narration may only restate this EvidenceBundle.",
    }
    normalized["flattened_value_hash"] = sha256_payload(flatten_values(normalized))
    normalized["normalized_hash"] = sha256_payload(normalized)
    return normalized


def flatten_values(value: Any) -> list[str]:
    values: list[str] = []
    if isinstance(value, dict):
        for key, val in value.items():
            values.append(str(key))
            values.extend(flatten_values(val))
    elif isinstance(value, list):
        for item in value:
            values.extend(flatten_values(item))
    elif value is None:
        return values
    else:
        values.append(str(value))
    return values


def deterministic_narration(bundle: dict[str, Any]) -> str:
    counts = bundle.get("counts", {})
    source_rows = counts.get("source_rows", {})
    subject = bundle.get("subject", {})
    subject_id = subject.get("subject_id")
    bbl = subject.get("bbl")
    role_counts_text = ", ".join(f"{role} {count}" for role, count in sorted(bundle.get("party_role_counts", {}).items())) or "none"
    return (
        f"operational briefing. parcel {bbl} resolves to {subject_id}. "
        f"The deterministic evidence links {counts.get('linked_buildings', 0)} building, "
        f"{counts.get('linked_permits', 0)} permits, {counts.get('linked_dob_complaints', 0)} DOB complaint events, "
        f"and {counts.get('linked_parties', 0)} parties. "
        f"Source rows are DOB Permit Issuance {source_rows.get('dob_permit_issuance', 0)}, "
        f"DOB NOW filings {source_rows.get('dob_now_filings', 0)}, and DOB complaints {source_rows.get('dob_complaints', 0)}. "
        f"Party role counts are {role_counts_text}. "
        f"EvidenceBundle normalized hash {bundle.get('normalized_hash')}. "
        f"{BOUNDARY_STATEMENT}"
    )


def query_parcel_evidence(a4d2_dir: Path, bbl: str, subject_label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    graph = DistrictGraph(a4d2_dir)
    query = {"query_type": "parcel_profile", "bbl": bbl}
    query_result = graph.query(query, f"a5d4a_{subject_label}_parcel_profile")
    bundle = normalize_to_evidence_bundle(query_result, subject_label)
    return query_result, bundle


def gate(gate_id: str, name: str, passed: bool, details: list[str] | None = None, checked: int = 1) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "checked": checked,
        "failed": 0 if passed else 1,
        "details": details or [],
    }


def write_bundle_set(
    output_dir: Path,
    subject_label: str,
    bbl: str,
    a4d2_dir: Path,
) -> dict[str, Any]:
    raw_result, bundle = query_parcel_evidence(a4d2_dir, bbl, subject_label)
    bundle_path = output_dir / "evidence_bundles" / f"{subject_label}_parcel_{bbl}.json"
    raw_path = output_dir / "raw_query_results" / f"{subject_label}_parcel_{bbl}.json"
    narration_path = output_dir / "narrations" / f"{subject_label}_parcel_{bbl}.md"
    grounding_path = output_dir / "grounding_reports" / f"{subject_label}_parcel_{bbl}.json"
    write_json(raw_path, raw_result)
    write_json(bundle_path, bundle)
    narration = deterministic_narration(bundle)
    write_text(narration_path, narration + "\n")
    grounding = run_grounding_gate(str(bundle_path), str(narration_path), str(grounding_path))
    return {
        "subject_label": subject_label,
        "bbl": bbl,
        "subject_id": bundle["subject"]["subject_id"],
        "evidence_bundle": str(bundle_path),
        "raw_query_result": str(raw_path),
        "narration": str(narration_path),
        "grounding_report": str(grounding_path),
        "normalized_hash": bundle["normalized_hash"],
        "grounding_status": grounding["status"],
        "counts": bundle["counts"],
    }


def build_readme(report: dict[str, Any]) -> str:
    hero = report["evidence_bundles"]["hero"]
    second = report["evidence_bundles"]["second_subject"]
    return "\n".join(
        [
            "# A5-D4A EvidenceBundle v1 + Grounded Narration",
            "",
            f"Status: {report['status']}.",
            "",
            "a5 = Action Core / NeMo+NIM / DGX Spark.",
            "a5-D4A = EvidenceBundle v1 + grounded narration.",
            "a4-D2 = DOB district enrichment.",
            "",
            BOUNDARY_STATEMENT,
            "",
            "## Evidence Bundles",
            "",
            f"- Hero parcel `{hero['bbl']}` hash `{hero['normalized_hash']}` grounding `{hero['grounding_status']}`.",
            f"- Second subject `{second['bbl']}` hash `{second['normalized_hash']}` grounding `{second['grounding_status']}`.",
            "",
            "Narration is deterministic by default and grounded against the EvidenceBundle. Counts and graph facts remain owned by code.",
            "",
        ]
    )


def run_a5d4a_gate(
    a5d1_dir: str = str(DEFAULT_A5D1_DIR),
    a4d2_dir: str = str(DEFAULT_A4D2_DIR),
    output_dir: str = str(DEFAULT_OUTPUT_DIR),
) -> dict[str, Any]:
    a5d1_path = Path(a5d1_dir)
    a4d2_path = Path(a4d2_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    gates: list[dict[str, Any]] = []

    harness_path = a5d1_path / "a5d1_harness_report.json"
    precond_details = []
    a5d1_status = "FAIL"
    if harness_path.exists():
        a5d1_report = read_json(harness_path)
        a5d1_status = "PASS" if a5d1_report.get("status") == "PASS" and a5d1_report.get("exit_code") == 0 else "FAIL"
    else:
        precond_details.append(f"Missing A5-D1 harness report: {harness_path}")
    if not a4d2_path.exists():
        precond_details.append(f"Missing a4-D2 input: {a4d2_path}")
    gates.append(gate("A5D4A-PRECOND", "A5-D1 and a4-D2 inputs are available and green", a5d1_status == "PASS" and not precond_details, precond_details))

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": EVIDENCE_SCHEMA_VERSION,
        "type": "object",
        "required": ["schema_version", "bundle_id", "subject", "tool_name", "query_type", "boundary_statement", "counts", "entities", "edges", "normalized_hash"],
        "properties": {
            "schema_version": {"const": EVIDENCE_SCHEMA_VERSION},
            "bundle_id": {"type": "string"},
            "subject": {"type": "object"},
            "tool_name": {"const": "citybrain_operator_query"},
            "query_type": {"const": "parcel_profile"},
            "boundary_statement": {"const": BOUNDARY_STATEMENT},
            "normalized_hash": {"type": "string"},
        },
    }
    write_json(out / "EVIDENCE_BUNDLE_V1_SCHEMA.json", schema)

    hero = write_bundle_set(out, "hero", HERO_BBL, a4d2_path)
    second = write_bundle_set(out, "second_subject", SECOND_SUBJECT_BBL, a4d2_path)
    gates.append(gate("A5D4A-HERO-EVIDENCE", "Hero EvidenceBundle v1 exists with normalized hash", Path(hero["evidence_bundle"]).exists() and bool(hero["normalized_hash"])))
    gates.append(gate("A5D4A-SECOND-SUBJECT-EVIDENCE", "Second-subject EvidenceBundle v1 exists with normalized hash", Path(second["evidence_bundle"]).exists() and bool(second["normalized_hash"])))
    gates.append(gate("A5D4A-HERO-GROUNDED", "Hero deterministic narration passes grounding gate", hero["grounding_status"] == "PASS"))
    gates.append(gate("A5D4A-SECOND-SUBJECT-GROUNDED", "Second-subject deterministic narration passes grounding gate", second["grounding_status"] == "PASS"))
    gates.append(gate("A5D4A-BOUNDARY", "Boundary statement is preserved in evidence and narration", all(BOUNDARY_STATEMENT in Path(path).read_text(encoding="utf-8") for path in (hero["evidence_bundle"], hero["narration"], second["evidence_bundle"], second["narration"])), checked=4))

    checks = {item["gate_id"]: item["passed"] for item in gates}
    status = "PASS" if all(checks.values()) else "FAIL"
    report = {
        "task": "A5-D4A EvidenceBundle v1 + grounded narration",
        "status": status,
        "exit_code": 0 if status == "PASS" else 1,
        "generated_at": utc_now(),
        "boundary_statement": BOUNDARY_STATEMENT,
        "inputs": {
            "a5d1_dir": str(a5d1_path),
            "a4d2_dir": str(a4d2_path),
        },
        "evidence_bundles": {
            "hero": hero,
            "second_subject": second,
        },
        "gates": gates,
        "checks": checks,
    }
    write_json(out / "A5D4A_HARNESS_REPORT.json", report)
    manifest = {
        "task": report["task"],
        "status": status,
        "boundary_statement": BOUNDARY_STATEMENT,
        "schema": "EVIDENCE_BUNDLE_V1_SCHEMA.json",
        "evidence_bundles": report["evidence_bundles"],
        "naming": {
            "a5": "Action Core / NeMo+NIM / DGX Spark",
            "a5-D4A": "EvidenceBundle v1 + grounded narration",
            "a4-D2": "DOB district enrichment",
        },
    }
    write_json(out / "A5D4A_MANIFEST.json", manifest)
    write_text(out / "README.md", build_readme(report))
    write_json(out / "SHA256SUMS.json", output_hashes(out))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build A5-D4A EvidenceBundle v1 + grounded narration outputs.")
    parser.add_argument("--a5d1-dir", default=str(DEFAULT_A5D1_DIR))
    parser.add_argument("--a4d2-dir", default=str(DEFAULT_A4D2_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args(argv)
    report = run_a5d4a_gate(args.a5d1_dir, args.a4d2_dir, args.output_dir)
    print(f"A5-D4A EvidenceBundle v1 + Grounded Narration: {report['status']}")
    print(f"Output: {args.output_dir}")
    return int(report.get("exit_code", 1))


if __name__ == "__main__":
    raise SystemExit(main())
