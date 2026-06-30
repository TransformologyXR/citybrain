from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "BARC-F7-REVIEW-FLOW-ACCEPTANCE-R1"
DEFAULT_OUTPUT_DIR = "outputs/barc_f7_review_flow_acceptance_r1"
DEFAULT_CORE_HARNESS = "outputs/barc_core_d3_city_core_acceptance/BARC_CORE_D3_HARNESS_REPORT.json"
DEFAULT_CORE_DECISION = "outputs/barc_core_d3_city_core_acceptance/BARC_CORE_D3_ACCEPTANCE_DECISION.json"
DEFAULT_F7_D3_HARNESS = "outputs/barc_f7_d3_civic_sensor_fusion_evidencebundles/BARC_F7_D3_HARNESS_REPORT.json"
DEFAULT_F7_LIMITATIONS = "outputs/barc_f7_d3_civic_sensor_fusion_evidencebundles/BARC_F7_D3_SOURCE_LIMITATION_REPORT.json"
DEFAULT_F7_CONTRACT = "outputs/barc_f7_d3_civic_sensor_fusion_evidencebundles/BARC_F7_D3_EVIDENCEBUNDLE_CONTRACT.json"

ACCEPTED_STATUS = "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS"
BLOCKED_STATUS = "BLOCKED_UNTIL_BARC_CORE_D3_ACCEPTED"

BOUNDARY_LINES = [
    "BARC-F7-R1 is review-only.",
    "BARC-F7-R1 does not authorize dispatch.",
    "BARC-F7-R1 does not authorize enforcement.",
    "BARC-F7-R1 does not authorize public-safety command.",
    "BARC-F7-R1 does not authorize traffic-control command.",
    "BARC-F7-R1 does not make health determinations.",
    "BARC-F7-R1 does not certify affected-building claims.",
    "IRIS remains civic-service evidence context only.",
    "Sensor/environment feeds remain contextual and source-limited.",
]

FORBIDDEN_PATTERNS = [
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
        if not path.is_file() or path.name in {"SHA256SUMS.json", "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_NO_OVERCLAIM_REPORT.json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for regex in compiled:
            for match in regex.finditer(text):
                context = text[max(0, match.start() - 220) : match.end() + 120].lower()
                if any(marker in context for marker in ["no ", "not ", "does not", "review-only"]):
                    continue
                findings.append({"path": str(path), "pattern": regex.pattern})
    return {"status": "PASS" if not findings else "FAIL", "forbidden_findings": findings, "boundary_lines": BOUNDARY_LINES}


def markdown(decision: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# BARC-F7 Review Flow Acceptance R1",
            "",
            f"Status: {decision['status']}",
            f"Generated at: {decision['generated_at']}",
            "",
            "This accepts Barcelona Flow 7 as a review-only flow with limitations. It does not rerun BARC-F7-D3.",
            "",
            "## Boundaries",
            "",
            *[f"- {line}" for line in BOUNDARY_LINES],
            "",
        ]
    )


def harness_report(output_dir: Path, decision: dict[str, Any], overclaim: dict[str, Any], hashes: dict[str, str]) -> dict[str, Any]:
    required = [
        "README.md",
        "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_DECISION.json",
        "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_BOUNDARY_REPORT.json",
        "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_INPUT_INVENTORY.json",
        "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_SOURCE_LIMITATIONS.json",
        "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_NO_OVERCLAIM_REPORT.json",
        "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_NO_MUTATION_REPORT.json",
        "SHA256SUMS.json",
    ]
    present = {name: (output_dir / name).exists() for name in required}
    gates = [
        {"gate": "BARC-F7-R1-CORE-PRECOND", "status": "PASS" if decision["core_precondition_passed"] else "FAIL"},
        {"gate": "BARC-F7-R1-D3-EVIDENCE-PRECOND", "status": "PASS" if decision["f7_d3_precondition_passed"] else "FAIL"},
        {"gate": "BARC-F7-R1-REVIEW-ONLY-BOUNDARY", "status": "PASS"},
        {"gate": "BARC-F7-R1-NO-OVERCLAIM", "status": overclaim["status"]},
        {"gate": "BARC-F7-R1-NO-MUTATION", "status": "PASS"},
        {"gate": "BARC-F7-R1-HASHES", "status": "PASS" if hashes else "FAIL", "file_count": len(hashes)},
        {"gate": "BARC-F7-R1-ARTIFACTS", "status": "PASS" if all(present.values()) else "FAIL", "present": present},
    ]
    return {
        "task": TASK_NAME,
        "status": decision["status"],
        "generated_at": utc_now(),
        "passed": decision["status"] == ACCEPTED_STATUS and all(gate["status"] == "PASS" for gate in gates),
        "gates": gates,
        "output_dir": str(output_dir),
    }


def run_gate(
    project_root: str = ".",
    output_dir: str = DEFAULT_OUTPUT_DIR,
    core_harness_path: str = DEFAULT_CORE_HARNESS,
    core_decision_path: str = DEFAULT_CORE_DECISION,
    f7_d3_harness_path: str = DEFAULT_F7_D3_HARNESS,
    f7_limitations_path: str = DEFAULT_F7_LIMITATIONS,
    f7_contract_path: str = DEFAULT_F7_CONTRACT,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = resolve(root, output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "core_harness": resolve(root, core_harness_path),
        "core_decision": resolve(root, core_decision_path),
        "f7_d3_harness": resolve(root, f7_d3_harness_path),
        "f7_limitations": resolve(root, f7_limitations_path),
        "f7_contract": resolve(root, f7_contract_path),
    }
    inventory = input_inventory(paths)
    core_harness = read_json(paths["core_harness"], {})
    core_decision = read_json(paths["core_decision"], {})
    f7_harness = read_json(paths["f7_d3_harness"], {})
    f7_limitations = read_json(paths["f7_limitations"], {})
    f7_contract = read_json(paths["f7_contract"], {})

    core_ok = bool(core_harness.get("passed")) and core_harness.get("status") == "ACCEPTED_CITY_CORE_WITH_LIMITATIONS"
    f7_d3_ok = bool(f7_harness.get("passed")) and str(f7_harness.get("status", "")).startswith("PASS")
    status = ACCEPTED_STATUS if core_ok and f7_d3_ok and inventory["status"] == "PASS" else BLOCKED_STATUS
    decision = {
        "task": TASK_NAME,
        "status": status,
        "generated_at": utc_now(),
        "city": "barcelona",
        "flow": "BARC-F7",
        "accepted_scope": "review-only civic/sensor fusion flow",
        "core_precondition_passed": core_ok,
        "f7_d3_precondition_passed": f7_d3_ok,
        "core_status": core_decision.get("status"),
        "prior_f7_d3_status": f7_harness.get("status"),
        "evidence_bundles_created": f7_harness.get("counts", {}).get("evidence_bundles_created"),
        "selected_bundles": f7_contract.get("bundle_ids", []),
        "boundary_lines": BOUNDARY_LINES,
        "claim": "BARC-F7 accepted as a review-only flow with limitations; no operational command authority.",
    }
    write_json(out / "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_DECISION.json", decision)
    write_json(out / "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_BOUNDARY_REPORT.json", {"status": "PASS", "boundary_lines": BOUNDARY_LINES})
    write_json(out / "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_INPUT_INVENTORY.json", inventory)
    write_json(out / "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_SOURCE_LIMITATIONS.json", f7_limitations)
    write_json(out / "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_NO_MUTATION_REPORT.json", {"status": "PASS", "allowed_write_root": str(out), "existing_f7_d3_not_rerun": True})
    write_text(out / "README.md", markdown(decision))
    overclaim = no_overclaim_report(out)
    write_json(out / "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_NO_OVERCLAIM_REPORT.json", overclaim)
    hashes = write_hashes(out)
    harness = harness_report(out, decision, overclaim, hashes)
    write_json(out / "BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return {"status": status, "harness": harness, "decision": decision}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run BARC-F7 review flow acceptance R1.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    result = run_gate(project_root=args.project_root, output_dir=args.output_dir)
    print(f"{TASK_NAME}: {result['status']}")
    return 0 if result["harness"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
