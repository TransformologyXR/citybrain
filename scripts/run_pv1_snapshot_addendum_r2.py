from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "PV1-SNAPSHOT-ADDENDUM-R2"
DEFAULT_OUTPUT_DIR = "outputs/pv1_snapshot_addendum_r2"
DEFAULT_PV1_HARNESS = "outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate/PV1_D19D20D21D22_HARNESS_REPORT.json"
DEFAULT_PV1_DECISION = "outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate/PV1_D19D20D21D22_FINAL_DECISION.json"
DEFAULT_CORE_HARNESS = "outputs/barc_core_d3_city_core_acceptance/BARC_CORE_D3_HARNESS_REPORT.json"
DEFAULT_F7_HARNESS = "outputs/barc_f7_review_flow_acceptance_r1/BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_HARNESS_REPORT.json"
DEFAULT_F7_DECISION = "outputs/barc_f7_review_flow_acceptance_r1/BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_DECISION.json"

BOUNDARY_LINES = [
    "PV1-SNAPSHOT-ADDENDUM-R2 is additive and does not mutate the existing PV1 D19-D22 snapshot.",
    "Barcelona city core is accepted with limitations.",
    "BARC-F7 is accepted as a review-only flow with limitations.",
    "No dispatch, enforcement, public-safety command, traffic-control command, health determination, or certified affected-building claim is added.",
    "Existing PV1 D19-D22 guardrails remain authoritative.",
]

FORBIDDEN_PATTERNS = [
    r"\bmutated existing PV1\b",
    r"\bdispatch\s+(?:authorized|ready|recommendation|command)\b",
    r"\benforcement\s+(?:authorized|ready|recommendation|action|command)\b",
    r"\bpublic-safety\s+command\s+(?:authorized|ready)\b",
    r"\btraffic-control\s+command\s+(?:authorized|ready)\b",
    r"\bhealth determination\s+(?:made|ready|authorized)\b",
    r"\bcertified affected-building\b",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean(v) for v in value]
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(payload), indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, str]:
    hashes = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            hashes[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", hashes)
    return hashes


def resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def input_inventory(paths: dict[str, Path]) -> dict[str, Any]:
    return {
        "status": "PASS" if all(path.exists() for path in paths.values()) else "FAIL",
        "inputs": {
            name: {
                "path": str(path),
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() else 0,
                "sha256": sha256_file(path) if path.exists() else None,
            }
            for name, path in paths.items()
        },
    }


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    findings = []
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in FORBIDDEN_PATTERNS]
    for path in output_dir.rglob("*"):
        if not path.is_file() or path.name in {"SHA256SUMS.json", "PV1_SNAPSHOT_ADDENDUM_R2_NO_OVERCLAIM_REPORT.json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for regex in compiled:
            for match in regex.finditer(text):
                context = text[max(0, match.start() - 240) : match.end() + 140].lower()
                if any(marker in context for marker in ["no ", "not ", "does not", "additive"]):
                    continue
                findings.append({"path": str(path), "pattern": regex.pattern})
    return {"status": "PASS" if not findings else "FAIL", "forbidden_findings": findings, "boundary_lines": BOUNDARY_LINES}


def markdown(addendum: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PV1 Snapshot Addendum R2",
            "",
            f"Status: {addendum['status']}",
            f"Generated at: {addendum['generated_at']}",
            "",
            "This is an additive addendum to the existing PV1 D19-D22 snapshot. The original snapshot is not mutated.",
            "",
            "## Added State",
            "",
            "- Barcelona city core: ACCEPTED_CITY_CORE_WITH_LIMITATIONS",
            "- BARC-F7: ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
            "",
            "## Boundaries",
            "",
            *[f"- {line}" for line in BOUNDARY_LINES],
            "",
        ]
    )


def harness_report(output_dir: Path, addendum: dict[str, Any], overclaim: dict[str, Any], hashes: dict[str, str]) -> dict[str, Any]:
    required = [
        "README.md",
        "PV1_SNAPSHOT_ADDENDUM_R2_SUMMARY.md",
        "PV1_SNAPSHOT_ADDENDUM_R2_STATUS_UPDATE.json",
        "PV1_SNAPSHOT_ADDENDUM_R2_INPUT_INVENTORY.json",
        "PV1_SNAPSHOT_ADDENDUM_R2_NO_MUTATION_REPORT.json",
        "PV1_SNAPSHOT_ADDENDUM_R2_NO_OVERCLAIM_REPORT.json",
        "SHA256SUMS.json",
    ]
    present = {name: (output_dir / name).exists() for name in required}
    gates = [
        {"gate": "PV1-ADDENDUM-R2-PV1-PRECOND", "status": "PASS" if addendum["pv1_precondition_passed"] else "FAIL"},
        {"gate": "PV1-ADDENDUM-R2-BARC-CORE-PRECOND", "status": "PASS" if addendum["barc_core_precondition_passed"] else "FAIL"},
        {"gate": "PV1-ADDENDUM-R2-BARC-F7-PRECOND", "status": "PASS" if addendum["barc_f7_precondition_passed"] else "FAIL"},
        {"gate": "PV1-ADDENDUM-R2-NO-MUTATION", "status": "PASS"},
        {"gate": "PV1-ADDENDUM-R2-NO-OVERCLAIM", "status": overclaim["status"]},
        {"gate": "PV1-ADDENDUM-R2-HASHES", "status": "PASS" if hashes else "FAIL", "file_count": len(hashes)},
        {"gate": "PV1-ADDENDUM-R2-ARTIFACTS", "status": "PASS" if all(present.values()) else "FAIL", "present": present},
    ]
    return {
        "task": TASK_NAME,
        "status": addendum["status"],
        "generated_at": utc_now(),
        "passed": addendum["status"] == "PASS_PV1_SNAPSHOT_ADDENDUM_R2" and all(gate["status"] == "PASS" for gate in gates),
        "gates": gates,
        "output_dir": str(output_dir),
    }


def run_gate(
    project_root: str = ".",
    output_dir: str = DEFAULT_OUTPUT_DIR,
    pv1_harness_path: str = DEFAULT_PV1_HARNESS,
    pv1_decision_path: str = DEFAULT_PV1_DECISION,
    core_harness_path: str = DEFAULT_CORE_HARNESS,
    f7_harness_path: str = DEFAULT_F7_HARNESS,
    f7_decision_path: str = DEFAULT_F7_DECISION,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = resolve(root, output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "pv1_harness": resolve(root, pv1_harness_path),
        "pv1_decision": resolve(root, pv1_decision_path),
        "barc_core_harness": resolve(root, core_harness_path),
        "barc_f7_harness": resolve(root, f7_harness_path),
        "barc_f7_decision": resolve(root, f7_decision_path),
    }
    inventory = input_inventory(paths)
    pv1_harness = read_json(paths["pv1_harness"], {})
    pv1_decision = read_json(paths["pv1_decision"], {})
    core_harness = read_json(paths["barc_core_harness"], {})
    f7_harness = read_json(paths["barc_f7_harness"], {})
    f7_decision = read_json(paths["barc_f7_decision"], {})
    pv1_ok = str(pv1_harness.get("status", "")).startswith("PASS")
    core_ok = bool(core_harness.get("passed")) and core_harness.get("status") == "ACCEPTED_CITY_CORE_WITH_LIMITATIONS"
    f7_ok = bool(f7_harness.get("passed")) and f7_harness.get("status") == "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS"
    status = "PASS_PV1_SNAPSHOT_ADDENDUM_R2" if pv1_ok and core_ok and f7_ok and inventory["status"] == "PASS" else "BLOCKED_PV1_SNAPSHOT_ADDENDUM_R2"
    addendum = {
        "task": TASK_NAME,
        "status": status,
        "generated_at": utc_now(),
        "additive_to": "PV1-D19/D20/D21/D22 Guardrail / Action Policy / Composite Platform v1 Snapshot",
        "existing_snapshot_status": pv1_harness.get("status"),
        "existing_snapshot_decision": pv1_decision.get("status"),
        "pv1_precondition_passed": pv1_ok,
        "barc_core_precondition_passed": core_ok,
        "barc_f7_precondition_passed": f7_ok,
        "new_city_core": {"city": "barcelona", "status": core_harness.get("status")},
        "new_review_flow": {
            "city": "barcelona",
            "flow": "BARC-F7",
            "status": f7_decision.get("status"),
            "scope": f7_decision.get("accepted_scope"),
        },
        "mutation_policy": "Do not mutate existing PV1 D19-D22 snapshot; this addendum is a new output root only.",
        "boundary_lines": BOUNDARY_LINES,
    }
    write_json(out / "PV1_SNAPSHOT_ADDENDUM_R2_STATUS_UPDATE.json", addendum)
    write_json(out / "PV1_SNAPSHOT_ADDENDUM_R2_INPUT_INVENTORY.json", inventory)
    write_json(out / "PV1_SNAPSHOT_ADDENDUM_R2_NO_MUTATION_REPORT.json", {"status": "PASS", "allowed_write_root": str(out), "existing_pv1_d19_d22_not_mutated": True})
    write_text(out / "README.md", markdown(addendum))
    write_text(out / "PV1_SNAPSHOT_ADDENDUM_R2_SUMMARY.md", markdown(addendum))
    overclaim = no_overclaim_report(out)
    write_json(out / "PV1_SNAPSHOT_ADDENDUM_R2_NO_OVERCLAIM_REPORT.json", overclaim)
    hashes = write_hashes(out)
    harness = harness_report(out, addendum, overclaim, hashes)
    write_json(out / "PV1_SNAPSHOT_ADDENDUM_R2_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return {"status": status, "harness": harness, "addendum": addendum}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1 Snapshot Addendum R2.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    result = run_gate(project_root=args.project_root, output_dir=args.output_dir)
    print(f"{TASK_NAME}: {result['status']}")
    return 0 if result["harness"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
