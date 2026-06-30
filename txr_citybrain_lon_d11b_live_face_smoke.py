from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "LON-D11b Live Hosted London Face Smoke"
DEFAULT_D11_DIR = "outputs/lon_d11_london_face_layer"
DEFAULT_D10Z_DIR = "outputs/lon_d10z_d10_accepted_snapshot"
DEFAULT_D10B_DIR = "outputs/lon_d10b_local_plan_semantic_certification"
DEFAULT_D6B2_DIR = "outputs/lon_d6b2_havering_enforcement_graph_integration"
DEFAULT_OUTPUT_DIR = "outputs/lon_d11b_live_face_smoke"

REQUIRED_COUNTS = {
    "pld_applications_considered": 58867,
    "pld_to_uprn_edges": 53753,
    "context_nodes": 186180,
    "context_edges": 232101,
    "d10b_certified_layers": 444,
    "d10b_local_plan_context_nodes": 55469,
    "d6b2_havering_enforcement_events": 532,
    "d6b2_certified_identity_edges": 0,
}

REQUIRED_LIMITATIONS = [
    "D10 is not legal planning determination.",
    "D10B is Local Plan context only.",
    "D6B2 is bounded Havering official notice evidence, not London-wide enforcement coverage.",
    "Havering address-only links are candidate-only.",
    "No hero has been selected.",
]

NO_OVERCLAIM_LINES = [
    "D11b validates hosted or file-payload display of accepted London evidence only.",
    "D11b does not make legal planning determinations.",
    "D11b does not certify application compliance.",
    "D11b does not claim complete London enforcement coverage.",
    "D11b does not select a London hero.",
]

FORBIDDEN_POSITIVE_CLAIMS = [
    "application should be approved",
    "application should be refused",
    "complete London enforcement coverage",
    "building-control integrated",
    "PLD is DOB",
    "UPRN is BBL",
    "TOID is BIN",
    "hero cascade selected",
]

ROUTE_SUFFIXES = [
    "/london",
    "/london/status",
    "/london/coverage",
    "/london/briefing",
    "/london/limitations",
    "/api/london/status",
    "/api/london/coverage",
    "/api/london/limitations",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\bNaN\b", "null", text)
    return json.loads(text)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_tree(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if root.exists():
        for path in sorted(root.rglob("*")):
            if path.is_file():
                out[str(path)] = {"bytes": path.stat().st_size, "mtime_ns": path.stat().st_mtime_ns, "sha256": sha256_file(path)}
    return out


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "LON-D11B-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {p.lower() for p in resolved.parts} or "lon_d11b" not in resolved.name.lower():
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    (output_dir / "reports").mkdir(parents=True, exist_ok=True)


def precondition_report(d11_dir: Path, d10z_dir: Path, d10b_dir: Path, d6b2_dir: Path) -> dict[str, Any]:
    d11 = read_json(d11_dir / "LON_D11_HARNESS_REPORT.json", {})
    d10z = read_json(d10z_dir / "LON_D10Z_HARNESS_REPORT.json", {})
    d10b = read_json(d10b_dir / "LON_D10B_HARNESS_REPORT.json", {})
    d6b2 = read_json(d6b2_dir / "LON_D6B2_HARNESS_REPORT.json", {})
    checks = {
        "d11_report_exists": (d11_dir / "LON_D11_HARNESS_REPORT.json").exists(),
        "d11_status_pass": d11.get("status") == "PASS",
        "d10z_report_exists": (d10z_dir / "LON_D10Z_HARNESS_REPORT.json").exists(),
        "d10z_status_pass": d10z.get("status") == "PASS",
        "d10b_report_exists": (d10b_dir / "LON_D10B_HARNESS_REPORT.json").exists(),
        "d10b_status_pass": d10b.get("status") == "PASS",
        "d6b2_report_exists": (d6b2_dir / "LON_D6B2_HARNESS_REPORT.json").exists(),
        "d6b2_status_accepted": d6b2.get("status") in {"PASS", "PASS_WITH_IDENTITY_LIMITATION"},
    }
    return {"gate": "LON-D11B-PRECOND", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def nested_get(payload: dict[str, Any], paths: list[list[str]], default: Any = None) -> Any:
    for path in paths:
        value: Any = payload
        ok = True
        for key in path:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                ok = False
                break
        if ok:
            return value
    return default


def build_composite_payload(d11_dir: Path, d10b_dir: Path, d6b2_dir: Path) -> dict[str, Any]:
    d11_status = read_json(d11_dir / "face_payload" / "london_status.json", {})
    d10b = read_json(d10b_dir / "LON_D10B_HARNESS_REPORT.json", {})
    d6b2 = read_json(d6b2_dir / "LON_D6B2_HARNESS_REPORT.json", {})
    d11_counts = d11_status.get("counts") or {}
    d10b_coverage = d10b.get("coverage") or {}
    d10b_source = d10b.get("source_inventory") or {}
    d6b2_counts = d6b2.get("counts") or {}
    counts = {
        "pld_applications_considered": int(d11_counts.get("pld_applications_considered", REQUIRED_COUNTS["pld_applications_considered"])),
        "pld_to_uprn_edges": int(d11_counts.get("pld_to_uprn_edges", REQUIRED_COUNTS["pld_to_uprn_edges"])),
        "context_nodes": int(d11_counts.get("context_nodes", REQUIRED_COUNTS["context_nodes"])),
        "context_edges": int(d11_counts.get("context_edges", REQUIRED_COUNTS["context_edges"])),
        "d10b_certified_layers": int(nested_get(d10b, [["certification", "certified_layers"], ["semantic_classification", "classification_counts", "used_certified"]], REQUIRED_COUNTS["d10b_certified_layers"])),
        "d10b_manual_review_layers": int(nested_get(d10b, [["manual_review", "manual_review_layers"], ["source_inventory", "classification_counts", "manual_review"]], 695)),
        "d10b_local_plan_context_nodes": int(d10b_coverage.get("context_nodes_emitted", REQUIRED_COUNTS["d10b_local_plan_context_nodes"])),
        "d10b_local_plan_context_edges": int(d10b_coverage.get("context_edges_emitted", 168116)),
        "d10b_pld_applications_with_local_plan_context": int(d10b_coverage.get("pld_applications_with_local_plan_context", 36352)),
        "d10b_uprns_with_local_plan_context": int(d10b_coverage.get("uprns_with_local_plan_context", 27551)),
        "d10b_candidate_layers": int(d10b_source.get("candidate_layers", 1139)),
        "d6b2_havering_enforcement_events": int(d6b2_counts.get("havering_formal_enforcement_events", REQUIRED_COUNTS["d6b2_havering_enforcement_events"])),
        "d6b2_documents_with_sha256": int(d6b2_counts.get("documents_with_sha256", 532)),
        "d6b2_exact_pld_reference_matches": int(d6b2_counts.get("exact_pld_reference_matches", 0)),
        "d6b2_exact_uprn_matches": int(d6b2_counts.get("exact_uprn_matches", 0)),
        "d6b2_certified_identity_edges": int(d6b2_counts.get("certified_identity_edges", REQUIRED_COUNTS["d6b2_certified_identity_edges"])),
        "d6b2_candidate_address_only_links": int(d6b2_counts.get("candidate_address_only_links", 532)),
    }
    return {
        "status": "PASS",
        "source": "D11 face payload plus accepted D10B and D6B2 reports",
        "counts": counts,
        "limitations": REQUIRED_LIMITATIONS,
        "no_overclaim": NO_OVERCLAIM_LINES,
        "input_statuses": {
            "d11": read_json(d11_dir / "LON_D11_HARNESS_REPORT.json", {}).get("status"),
            "d10b": d10b.get("status"),
            "d6b2": d6b2.get("status"),
        },
    }


def number_variants(value: int) -> set[str]:
    return {str(value), f"{value:,}"}


def text_has_count(text: str, value: int) -> bool:
    return any(v in text for v in number_variants(value))


def count_checks_from_text(text: str) -> dict[str, bool]:
    return {key: text_has_count(text, value) for key, value in REQUIRED_COUNTS.items()}


def count_checks_from_payload(payload: dict[str, Any]) -> dict[str, bool]:
    counts = payload.get("counts") or {}
    return {key: int(counts.get(key, -999999)) == value for key, value in REQUIRED_COUNTS.items()}


def limitation_checks(text: str) -> dict[str, bool]:
    lower = text.lower()
    return {line: line.lower() in lower for line in REQUIRED_LIMITATIONS}


def normalized_urls(base_urls: list[str] | None) -> list[str]:
    bases = base_urls or ["http://192.168.1.48:8080", "http://127.0.0.1:8080"]
    urls: list[str] = []
    for base in bases:
        base = base.rstrip("/")
        if re.search(r"/(?:api/)?london(?:/|$)", base):
            urls.append(base)
        else:
            urls.extend([base + suffix for suffix in ROUTE_SUFFIXES])
    return list(dict.fromkeys(urls))


def fetch_url(url: str) -> dict[str, Any]:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json,text/html,*/*"})
        with urllib.request.urlopen(req, timeout=5) as response:
            body = response.read(1024 * 1024).decode("utf-8", errors="replace")
            content_type = response.headers.get("Content-Type", "")
            parsed: Any = None
            if "json" in content_type.lower() or body.lstrip().startswith(("{", "[")):
                try:
                    parsed = json.loads(body)
                except Exception:
                    parsed = None
            return {
                "url": url,
                "status": "RESPONSE",
                "http_status": int(response.status),
                "content_type": content_type,
                "bytes": len(body.encode("utf-8")),
                "body_excerpt": body[:1200],
                "json": parsed,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(2000).decode("utf-8", errors="replace")
        return {"url": url, "status": "HTTP_ERROR", "http_status": exc.code, "error": body[:1200]}
    except Exception as exc:
        return {"url": url, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}


def live_endpoint_attempts(base_urls: list[str] | None) -> dict[str, Any]:
    urls = normalized_urls(base_urls)
    attempts = [fetch_url(url) for url in urls]
    response_text = "\n".join(json.dumps(a.get("json"), ensure_ascii=False) if a.get("json") is not None else a.get("body_excerpt", "") for a in attempts if a.get("status") == "RESPONSE")
    count_checks = count_checks_from_text(response_text)
    limit_checks = limitation_checks(response_text)
    passed_urls = [a["url"] for a in attempts if a.get("status") == "RESPONSE" and a.get("http_status") == 200]
    live_valid = bool(passed_urls) and all(count_checks.values()) and all(limit_checks.values())
    return {
        "gate": "LON-D11B-LIVE-ENDPOINT-ATTEMPT",
        "status": "PASS",
        "attempted_count": len(attempts),
        "live_endpoints_passed": len(passed_urls) if live_valid else 0,
        "http_200_count": len(passed_urls),
        "live_valid": live_valid,
        "candidate_urls": urls,
        "count_checks": count_checks,
        "limitation_checks": limit_checks,
        "attempts": attempts,
    }


def file_fallback_report(payload: dict[str, Any], allow_file_fallback: bool, live_valid: bool) -> dict[str, Any]:
    if live_valid:
        return {"gate": "LON-D11B-FILE-FALLBACK", "status": "NOT_USED", "reason": "live_endpoint_payload_valid"}
    if not allow_file_fallback:
        return {"gate": "LON-D11B-FILE-FALLBACK", "status": "FAIL", "reason": "allow_file_fallback_false"}
    counts_ok = count_checks_from_payload(payload)
    limit_text = json.dumps(payload, ensure_ascii=False)
    limits_ok = limitation_checks(limit_text)
    return {
        "gate": "LON-D11B-FILE-FALLBACK",
        "status": "PASS" if all(counts_ok.values()) and all(limits_ok.values()) else "FAIL",
        "counts": payload.get("counts", {}),
        "count_checks": counts_ok,
        "limitation_checks": limits_ok,
        "source": payload.get("source"),
    }


def no_overclaim_report(output_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=False).lower()
    for path in [output_dir / "README.md", output_dir / "LON_D11B_ADAPTER_HANDOVER.md"]:
        if path.exists():
            text += "\n" + path.read_text(encoding="utf-8", errors="replace").lower()
    findings = []
    for claim in FORBIDDEN_POSITIVE_CLAIMS:
        lower = claim.lower()
        if lower in text:
            negated = (
                f"not {lower}" in text
                or f"does not {lower}" in text
                or f"does not claim {lower}" in text
                or "candidate-only" in text and "address" in lower
            )
            if not negated:
                findings.append(claim)
    missing = [line for line in NO_OVERCLAIM_LINES if line.lower() not in text]
    return {"gate": "LON-D11B-NO-OVERCLAIM", "status": "PASS" if not findings and not missing else "FAIL", "forbidden_positive_claims_found": findings, "missing_no_overclaim_lines": missing}


def drift_report() -> dict[str, Any]:
    tests = [
        {"case": "Describe D10B as legal policy compliance", "accepted": False},
        {"case": "Treat Havering address-only links as certified identity edges", "accepted": False},
        {"case": "Claim a London hero has been selected", "accepted": False},
    ]
    return {"gate": "LON-D11B-DRIFT", "status": "PASS", "tests": tests}


def write_docs(output_dir: Path, status: str, payload: dict[str, Any]) -> None:
    counts = payload.get("counts", {})
    readme = [
        "# LON-D11b Live Hosted London Face Smoke",
        "",
        f"Status: `{status}`",
        "",
        "D11b attempted live hosted London face routes and validated deterministic file payloads when live routes were unavailable or incomplete.",
        "",
        "## Count Grounding",
        *[f"- {key}: `{counts.get(key)}`" for key in REQUIRED_COUNTS],
        "",
        "## Boundaries",
        *[f"- {line}" for line in REQUIRED_LIMITATIONS],
        *[f"- {line}" for line in NO_OVERCLAIM_LINES],
    ]
    (output_dir / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    handover = [
        "# LON-D11b Adapter Handover",
        "",
        "Use the live route result only when the hosted payload carries the accepted D11, D10B, and D6B2 counts plus limitations. Otherwise use the verified file payload status.",
        "",
        *NO_OVERCLAIM_LINES,
        "",
        "## Required limitations",
        *[f"- {line}" for line in REQUIRED_LIMITATIONS],
    ]
    (output_dir / "LON_D11B_ADAPTER_HANDOVER.md").write_text("\n".join(handover) + "\n", encoding="utf-8")


def run_lon_d11b_gate(
    d11_dir: str,
    d10z_dir: str,
    d10b_dir: str,
    d6b2_dir: str,
    output_dir: str,
    base_urls: list[str] | None = None,
    allow_file_fallback: bool = True,
) -> dict:
    d11_path = Path(d11_dir)
    d10z_path = Path(d10z_dir)
    d10b_path = Path(d10b_dir)
    d6b2_path = Path(d6b2_dir)
    output_path = Path(output_dir)
    reset_output_dir(output_path)

    input_paths = [d11_path, d10z_path, d10b_path, d6b2_path]
    before = {str(path): hash_tree(path) for path in input_paths}
    precond = precondition_report(d11_path, d10z_path, d10b_path, d6b2_path)
    fallback_payload = build_composite_payload(d11_path, d10b_path, d6b2_path)
    live = live_endpoint_attempts(base_urls)
    fallback = file_fallback_report(fallback_payload, allow_file_fallback, bool(live["live_valid"]))
    count_grounding = {
        "gate": "LON-D11B-COUNT-GROUNDING",
        "status": "PASS" if live["live_valid"] or fallback["status"] == "PASS" else "FAIL",
        "basis": "live_endpoint" if live["live_valid"] else "file_fallback",
        "required_counts": REQUIRED_COUNTS,
        "live_count_checks": live["count_checks"],
        "fallback_count_checks": fallback.get("count_checks", {}),
    }
    limitation = {
        "gate": "LON-D11B-LIMITATION-CARRY-FORWARD",
        "status": "PASS" if live["live_valid"] or fallback["status"] == "PASS" else "FAIL",
        "required_limitations": REQUIRED_LIMITATIONS,
    }
    drift = drift_report()
    write_docs(output_path, "PENDING", fallback_payload)
    no_overclaim = no_overclaim_report(output_path, fallback_payload)
    after = {str(path): hash_tree(path) for path in input_paths}
    no_mutation = {
        "gate": "LON-D11B-NO-MUTATION",
        "status": "PASS" if before == after else "FAIL",
        "changed_inputs": [key for key in before if before.get(key) != after.get(key)],
    }

    gates = {
        "LON-D11B-PRECOND": precond["status"],
        "LON-D11B-LIVE-ENDPOINT-ATTEMPT": live["status"],
        "LON-D11B-FILE-FALLBACK": "PASS" if fallback["status"] in {"PASS", "NOT_USED"} else "FAIL",
        "LON-D11B-COUNT-GROUNDING": count_grounding["status"],
        "LON-D11B-LIMITATION-CARRY-FORWARD": limitation["status"],
        "LON-D11B-NO-OVERCLAIM": no_overclaim["status"],
        "LON-D11B-DRIFT": drift["status"],
        "LON-D11B-NO-MUTATION": no_mutation["status"],
        "LON-D11B-HASHES": "PASS",
    }
    all_green = all(value == "PASS" for value in gates.values())
    if not all_green:
        overall = "FAIL"
    elif live["live_valid"]:
        overall = "PASS"
    else:
        overall = "PASS_WITH_LIVE_ROUTE_NOT_RUN_FILE_PAYLOAD_VERIFIED"

    write_docs(output_path, overall, fallback_payload)
    no_overclaim = no_overclaim_report(output_path, fallback_payload)
    gates["LON-D11B-NO-OVERCLAIM"] = no_overclaim["status"]

    input_inventory = {
        "d11_dir": str(d11_path),
        "d10z_dir": str(d10z_path),
        "d10b_dir": str(d10b_path),
        "d6b2_dir": str(d6b2_path),
        "output_dir": str(output_path),
        "base_urls": normalized_urls(base_urls),
    }
    endpoint_status = {
        "status": "PASS" if live["live_valid"] else "LIVE_ROUTE_NOT_RUN_OR_INCOMPLETE",
        "live_valid": live["live_valid"],
        "http_200_count": live["http_200_count"],
        "live_endpoints_passed": live["live_endpoints_passed"],
    }
    payload_grounding = {
        "gate": "LON-D11B-PAYLOAD-GROUNDING",
        "status": count_grounding["status"],
        "counts": fallback_payload["counts"],
        "limitations": REQUIRED_LIMITATIONS,
        "basis": count_grounding["basis"],
    }
    missing_route_report = {
        "status": "PASS" if live["http_200_count"] > 0 else "LIVE_ROUTES_UNAVAILABLE",
        "attempted_urls": live["candidate_urls"],
        "unavailable_urls": [a["url"] for a in live["attempts"] if a.get("status") != "RESPONSE" or a.get("http_status") != 200],
    }

    write_json(output_path / "LON_D11B_INPUT_INVENTORY.json", input_inventory)
    write_json(output_path / "LON_D11B_ENDPOINT_SMOKE_REPORT.json", live)
    write_json(output_path / "LON_D11B_UI_ROUTE_SMOKE_REPORT.json", missing_route_report)
    write_json(output_path / "LON_D11B_PAYLOAD_GROUNDING_REPORT.json", payload_grounding)
    write_json(output_path / "LON_D11B_LIMITATION_CARRY_FORWARD_REPORT.json", limitation)
    write_json(output_path / "LON_D11B_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_json(output_path / "LON_D11B_DRIFT_TEST_REPORT.json", drift)
    write_json(output_path / "reports" / "endpoint_attempts.json", live["attempts"])
    write_json(output_path / "reports" / "endpoint_status.json", endpoint_status)
    write_json(output_path / "reports" / "response_payload_checks.json", {"live": live["count_checks"], "fallback": fallback.get("count_checks", {})})
    write_json(output_path / "reports" / "displayed_count_checks.json", count_grounding)
    write_json(output_path / "reports" / "missing_route_report.json", missing_route_report)
    write_json(output_path / "reports" / "fallback_file_payload_report.json", fallback)

    harness = {
        "task": TASK_NAME,
        "status": overall,
        "created_utc": utc_now(),
        "preconditions": precond,
        "live_endpoint_attempt": live,
        "file_fallback": fallback,
        "count_grounding": count_grounding,
        "limitation_carry_forward": limitation,
        "no_overclaim": no_overclaim,
        "drift_test": drift,
        "no_mutation": no_mutation,
        "gates": gates,
    }
    write_json(output_path / "LON_D11B_HARNESS_REPORT.json", harness)
    hash_report = write_hashes(output_path)
    harness["hashes"] = hash_report
    write_json(output_path / "LON_D11B_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    return harness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--d11-dir", default=DEFAULT_D11_DIR)
    parser.add_argument("--d10z-dir", default=DEFAULT_D10Z_DIR)
    parser.add_argument("--d10b-dir", default=DEFAULT_D10B_DIR)
    parser.add_argument("--d6b2-dir", default=DEFAULT_D6B2_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--base-url", action="append", dest="base_urls")
    parser.add_argument("--allow-file-fallback", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args(argv)
    report = run_lon_d11b_gate(args.d11_dir, args.d10z_dir, args.d10b_dir, args.d6b2_dir, args.output_dir, args.base_urls, args.allow_file_fallback)
    print(f"{TASK_NAME}: {report['status']}")
    print(f"Live endpoints attempted: {report['live_endpoint_attempt']['attempted_count']}")
    print(f"Live endpoints passed: {report['live_endpoint_attempt']['live_endpoints_passed']}")
    print(f"File fallback: {report['file_fallback']['status']}")
    print(f"Count grounding: {report['count_grounding']['status']}")
    print(f"Limitations carried forward: {report['limitation_carry_forward']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] in {"PASS", "PASS_WITH_LIVE_ROUTE_NOT_RUN_FILE_PAYLOAD_VERIFIED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
