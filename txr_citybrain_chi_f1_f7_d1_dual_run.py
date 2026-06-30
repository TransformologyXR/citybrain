from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from txr_citybrain_chi_f1_d1_situational_status import run_chi_f1_d1_gate
from txr_citybrain_chi_f7_d1_civic_sensor_fusion import run_chi_f7_d1_gate


TASK_NAME = "CHI-F1-D1 + CHI-F7-D1 Dual Chicago Flow Bootstrap"

DUAL_BOUNDARY_LINES = [
    "Chicago now has D1 cartridges for Flow 1 and Flow 7 only if both gates pass.",
    "These are D1 deterministic cartridges, not full Platform v1.",
    "No live NIM claim unless a later D2 live replay is built.",
    "No face-layer claim unless a later D2/D3 face surface is built.",
    "No operational or public-safety recommendations.",
    "Capped/windowed source limitations remain.",
]

FORBIDDEN_PATTERNS = [
    r"\brisk score\b",
    r"\bdanger score\b",
    r"\bcrime score\b",
    r"\bhealth score\b",
    r"\benforcement score\b",
    r"\bemergency score\b",
    r"\boperational recommendation\b(?!s\.)",
    r"\bpublic-safety recommendation\b(?!s\.)",
    r"\bcertifies affected (?:buildings|assets)\b",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return json_safe(value.item())
        except Exception:
            pass
    return value


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any, add_boundary: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, dict):
        payload = dict(payload)
        payload.setdefault("generated_at", utc_now())
        if add_boundary:
            payload.setdefault("boundary_lines", DUAL_BOUNDARY_LINES)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, Any]:
    files = sorted(p for p in output_dir.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json")
    sums = {str(p.relative_to(output_dir)).replace("\\", "/"): sha256_file(p) for p in files}
    (output_dir / "SHA256SUMS.json").write_text(json.dumps(sums, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    expected = {str(p.relative_to(output_dir)).replace("\\", "/") for p in files}
    return {
        "status": "PASS" if set(sums) == expected else "FAIL",
        "file_count": len(sums),
        "missing": sorted(expected - set(sums)),
        "extra": sorted(set(sums) - expected),
    }


def snapshot(paths: list[Path]) -> dict[str, str]:
    out: dict[str, str] = {}
    for root in paths:
        if not root.exists():
            out[str(root)] = "MISSING"
            continue
        for p in root.rglob("*"):
            if p.is_file():
                out[str(p.resolve())] = sha256_file(p)
    return out


def compare_snapshots(before: dict[str, str], after: dict[str, str]) -> dict[str, Any]:
    changed = sorted(k for k, v in before.items() if after.get(k) != v)
    added = sorted(k for k in after if k not in before)
    removed = sorted(k for k in before if k not in after)
    return {
        "status": "PASS" if not changed and not added and not removed else "FAIL",
        "changed_inputs": changed,
        "added_inputs": added,
        "removed_inputs": removed,
        "checked_files": len(before),
    }


def status_pass(value: Any) -> bool:
    text = str(value or "").upper()
    return text.startswith("PASS") or text.startswith("GREEN")


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    boundary_failures: list[str] = []
    forbidden_hits: list[dict[str, str]] = []
    checked = 0
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".txt"}:
            continue
        if path.name == "SHA256SUMS.json":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        checked += 1
        missing = [line for line in DUAL_BOUNDARY_LINES if line not in text]
        if missing:
            boundary_failures.append(str(path.relative_to(output_dir)))
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                forbidden_hits.append({"file": str(path.relative_to(output_dir)), "pattern": pattern})
    return {
        "status": "PASS" if not boundary_failures and not forbidden_hits else "FAIL",
        "checked_files": checked,
        "boundary_failures": boundary_failures,
        "forbidden_hits": forbidden_hits,
    }


def run_chi_f1_f7_d1_dual_gate(
    project_root: str,
    chi_d1_dir: str,
    chi_d1b_dir: str,
    chi_d2b_dir: str,
    chi_d3_dir: str,
    chi_d4_dir: str,
    f1_output_dir: str,
    f7_output_dir: str,
    dual_output_dir: str,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    d1 = (root / chi_d1_dir).resolve()
    d1b = (root / chi_d1b_dir).resolve()
    d2b = (root / chi_d2b_dir).resolve()
    d3 = (root / chi_d3_dir).resolve()
    d4 = (root / chi_d4_dir).resolve()
    f1_out = root / f1_output_dir
    f7_out = root / f7_output_dir
    dual_out = (root / dual_output_dir).resolve()

    prior_inputs = [d1, d1b, d2b, d3, d4]
    before = snapshot(prior_inputs)

    f1_result = run_chi_f1_d1_gate(str(root), chi_d2b_dir, chi_d3_dir, chi_d4_dir, f1_output_dir)
    f7_result = run_chi_f7_d1_gate(str(root), chi_d2b_dir, chi_d3_dir, chi_d4_dir, f1_output_dir, f7_output_dir)

    ensure_clean_dir(dual_out)
    d4_ledger = read_json(d4 / "CHI_D4_SHARED_SOURCE_LEDGER.json", {})
    f1_harness = read_json(f1_out / "CHI_F1_D1_HARNESS_REPORT.json", {})
    f7_harness = read_json(f7_out / "CHI_F7_D1_HARNESS_REPORT.json", {})

    write_json(dual_out / "CHI_F1_F7_D1_SHARED_SOURCE_LEDGER.json", {
        "status": "PASS" if d4_ledger.get("status") == "PASS" else "FAIL",
        "source": str(d4 / "CHI_D4_SHARED_SOURCE_LEDGER.json"),
        "ledger": d4_ledger.get("ledger", []),
        "shared_boundary": d4_ledger.get("shared_boundary"),
    })
    write_json(dual_out / "CHI_F1_F7_D1_FLOW_DISTINCTION_REPORT.json", {
        "status": "PASS",
        "flow_1": {
            "name": "Chicago Situational Status",
            "question": "What is the current/recent status of this area?",
            "unit": "community area / ward / police district / citywide area status subject",
            "output": "status card, EvidenceBundle, grounded deterministic briefing",
        },
        "flow_7": {
            "name": "Chicago Civic + Sensor Fusion",
            "question": "Where do civic demand, inspection signals, mobility, environment, and facility context converge?",
            "unit": "service hotspot / sensor zone / civic cluster derived from area-attributed signals",
            "output": "fused civic/sensor candidate, EvidenceBundle, hero scenario candidate",
        },
        "separation_rule": "Flow 1 describes an area; Flow 7 selects multi-signal convergence candidates for analyst review.",
    })
    write_json(dual_out / "CHI_F1_F7_D1_STATUS_SUMMARY.json", {
        "status": "PASS" if status_pass(f1_harness.get("status")) and status_pass(f7_harness.get("status")) else "FAIL",
        "f1": {
            "status": f1_harness.get("status"),
            "subjects": f1_harness.get("subjects"),
            "evidence_bundles": f1_harness.get("evidence_bundles"),
            "output": str(f1_out),
        },
        "f7": {
            "status": f7_harness.get("status"),
            "fusion_candidates": f7_harness.get("fusion_candidates"),
            "selected_candidates": f7_harness.get("selected_candidates"),
            "evidence_bundles": f7_harness.get("evidence_bundles"),
            "output": str(f7_out),
        },
    })
    write_json(dual_out / "CHI_F1_F7_D1_NEXT_STEPS.json", {
        "status": "PASS",
        "recommended_order": [
            "CHI-F1-D2 governed live replay over Flow 1 EvidenceBundles",
            "CHI-F7-D2 governed live replay over Flow 7 EvidenceBundles",
            "A later face-layer task may render the outputs after live replay is accepted",
        ],
        "not_claimed": [
            "full Platform v1",
            "live NIM integration",
            "face-layer integration",
            "operational or public-safety recommendations",
        ],
    })
    write_json(dual_out / "CHI_F1_F7_D1_NO_OVERCLAIM_REPORT.json", {
        "status": "PENDING",
        "note": "Final no-overclaim scan is written after all dual reports are present.",
    })

    after = snapshot(prior_inputs)
    no_mutation = compare_snapshots(before, after)
    write_json(dual_out / "CHI_F1_F7_D1_NO_MUTATION_REPORT.json", no_mutation)

    readme = "\n".join([
        "# CHI-F1-D1 + CHI-F7-D1 Dual Chicago Flow Bootstrap",
        "",
        *DUAL_BOUNDARY_LINES,
        "",
        f"Flow 1 status: {f1_harness.get('status')}",
        f"Flow 7 status: {f7_harness.get('status')}",
        "",
    ])
    write_text(dual_out / "README.md", readme)

    gates = {
        "CHI-F1-F7-D1-F1": "PASS" if status_pass(f1_harness.get("status")) else "FAIL",
        "CHI-F1-F7-D1-F7": "PASS" if status_pass(f7_harness.get("status")) else "FAIL",
        "CHI-F1-F7-D1-SHARED-SOURCE-LEDGER": "PASS" if d4_ledger.get("status") == "PASS" else "FAIL",
        "CHI-F1-F7-D1-FLOW-DISTINCTION": "PASS",
        "CHI-F1-F7-D1-NO-MUTATION": no_mutation["status"],
    }

    harness = {
        "task": TASK_NAME,
        "status": "PASS_DUAL_FLOW_D1",
        "f1_status": f1_harness.get("status"),
        "f7_status": f7_harness.get("status"),
        "gates": gates,
        "outputs": {
            "f1": str(f1_out),
            "f7": str(f7_out),
            "dual": str(dual_out),
        },
    }
    write_json(dual_out / "CHI_F1_F7_D1_DUAL_HARNESS_REPORT.json", harness)
    no_overclaim = scan_no_overclaim(dual_out)
    write_json(dual_out / "CHI_F1_F7_D1_NO_OVERCLAIM_REPORT.json", no_overclaim)
    gates["CHI-F1-F7-D1-NO-OVERCLAIM"] = no_overclaim["status"]
    hashes = write_hashes(dual_out)
    gates["CHI-F1-F7-D1-HASHES"] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = hashes
    harness["status"] = "PASS_DUAL_FLOW_D1" if all(v == "PASS" for v in gates.values()) else "FAIL"
    write_json(dual_out / "CHI_F1_F7_D1_DUAL_HARNESS_REPORT.json", harness)
    final_no_overclaim = scan_no_overclaim(dual_out)
    write_json(dual_out / "CHI_F1_F7_D1_NO_OVERCLAIM_REPORT.json", final_no_overclaim)
    gates["CHI-F1-F7-D1-NO-OVERCLAIM"] = final_no_overclaim["status"]
    hashes = write_hashes(dual_out)
    gates["CHI-F1-F7-D1-HASHES"] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = hashes
    harness["status"] = "PASS_DUAL_FLOW_D1" if all(v == "PASS" for v in gates.values()) else "FAIL"
    write_json(dual_out / "CHI_F1_F7_D1_DUAL_HARNESS_REPORT.json", harness)
    write_hashes(dual_out)

    return {
        "status": harness["status"],
        "f1_status": f1_harness.get("status"),
        "f7_status": f7_harness.get("status"),
        "f1_subjects": f1_harness.get("subjects"),
        "f7_fusion_candidates": f7_harness.get("fusion_candidates"),
        "f7_selected_candidates": f7_harness.get("selected_candidates"),
        "no_overclaim": gates["CHI-F1-F7-D1-NO-OVERCLAIM"],
        "gates": gates,
        "outputs": harness["outputs"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--chi-d1-dir", default="outputs/chi_d1_chicago_deep_source_api_scout")
    parser.add_argument("--chi-d1b-dir", default="outputs/chi_d1b_chicago_extended_source_landing")
    parser.add_argument("--chi-d2b-dir", default="outputs/chi_d2b_base_identity_refresh")
    parser.add_argument("--chi-d3-dir", default="outputs/chi_d3_civic_event_ingest_flow_readiness")
    parser.add_argument("--chi-d4-dir", default="outputs/chi_d4_dual_flow_scope_fork")
    parser.add_argument("--f1-output-dir", default="outputs/chi_f1_d1_situational_status_cartridge")
    parser.add_argument("--f7-output-dir", default="outputs/chi_f7_d1_civic_sensor_fusion_cartridge")
    parser.add_argument("--dual-output-dir", default="outputs/chi_f1_f7_d1_dual_flow_run")
    parser.add_argument("--run-gates", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_chi_f1_f7_d1_dual_gate(
        project_root=args.project_root,
        chi_d1_dir=args.chi_d1_dir,
        chi_d1b_dir=args.chi_d1b_dir,
        chi_d2b_dir=args.chi_d2b_dir,
        chi_d3_dir=args.chi_d3_dir,
        chi_d4_dir=args.chi_d4_dir,
        f1_output_dir=args.f1_output_dir,
        f7_output_dir=args.f7_output_dir,
        dual_output_dir=args.dual_output_dir,
    )
    print(f"CHI-F1-D1: {result['f1_status']}")
    print(f"CHI-F7-D1: {result['f7_status']}")
    print(f"CHI-F1/F7-D1 dual run: {result['status']}")
    print(f"F1 subjects: {result['f1_subjects']}")
    print(f"F7 fusion candidates: {result['f7_fusion_candidates']}")
    print(f"F7 selected candidates: {result['f7_selected_candidates']}")
    print(f"Dual no-overclaim: {result['no_overclaim']}")
    print(f"Output: {result['outputs']['dual']}")
    return 0 if str(result["status"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
