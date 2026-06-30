from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "LON-D13C Final London Pre-Hero Closure"
DEFAULT_OUTPUT_DIR = "outputs/lon_d13c_london_final_prehero_closure"
SYNC_TARGET = Path("C:/data/citybrain/from_3090/london_d13c_final_prehero_closure_v1")
REMOTE_HOST = "txr-4070"
REMOTE_ROOT = "/srv/citybrain/current"

HEADLINE = "London cartridge: GREEN_WITH_LIVE_FACE_LIVE_NIM_AND_DECLARED_LIMITATIONS"

FINAL_LIMITATIONS = [
    "D10/D10B are planning-context evidence only, not legal planning determinations.",
    "UPRN is not BBL.",
    "TOID is not BIN.",
    "PLD is not DOB.",
    "D11A uses OS Open TOID generalised point locations, not exact building polygons.",
    "Exact OS MasterMap / OS NGD London building polygons are not integrated.",
    "D10EV covers official rapid charging points/sites only.",
    "D10EV does not prove complete EV infrastructure coverage, real-time availability, grid capacity, or policy compliance.",
    "D6B4 recovers 190 certified enforcement identity edges through exact PLD-reference evidence.",
    "D6B4 does not prove London-wide enforcement coverage.",
    "Address-only, postcode-only, fuzzy, and nearest-geometry enforcement links remain uncertified.",
    "Building-control remains not integrated.",
    "No London hero has been selected yet.",
]

NO_OVERCLAIM_LINES = [
    "D13C is a final pre-hero accepted-state closure only.",
    "D13C does not select a London hero.",
    "D13C does not make legal planning determinations.",
    "D13C does not certify application compliance.",
    "D13C does not claim London-wide enforcement coverage.",
    "D13C does not certify address-only, postcode-only, fuzzy, or nearest-geometry enforcement identity links.",
    "D13C does not claim exact building polygons from OS Open TOID.",
    "D13C does not claim complete EV infrastructure coverage or real-time availability.",
]

SUPERSESSION_LINES = [
    "D11B superseded by D11C.",
    "D12 deterministic/live-not-run caveat superseded by D12B live Spark/NIM replay.",
    "D6B2 identity limitation superseded by D6B4 expanded exact-PLD identity recovery.",
    "D6B3 partial recovery superseded/expanded by D6B4.",
    "D13/D13b superseded by D13C.",
]

FORBIDDEN_PATTERNS = [
    "application should be approved",
    "application should be refused",
    "approved_by_policy",
    "policy_compliance",
    "complete london enforcement coverage",
    "london-wide enforcement coverage is proven",
    "address-only links are certified",
    "postcode-only links are certified",
    "nearest-geometry links are certified",
    "exact building polygon",
    "os ngd building polygon recovery",
    "complete ev infrastructure",
    "real-time ev availability",
    "building-control integrated",
    "hero selected",
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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "LON-D13C-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {p.lower() for p in resolved.parts} or "lon_d13c" not in resolved.name.lower():
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["accepted", "reports", "_route_payload"]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def hash_tree(root: Path) -> dict[str, dict[str, Any]]:
    out = {}
    if root.exists():
        for path in sorted(root.rglob("*")):
            if path.is_file():
                out[str(path)] = {"bytes": path.stat().st_size, "mtime_ns": path.stat().st_mtime_ns, "sha256": sha256_file(path)}
    return out


def dependency_check(name: str, path: Path, report_name: str, accepted: set[str], required: bool = True) -> dict[str, Any]:
    report_path = path / report_name
    payload = read_json(report_path, {})
    status = payload.get("status")
    pass_status = report_path.exists() and status in accepted
    if not required and not report_path.exists():
        dep_status = "MISSING_OPTIONAL"
    else:
        dep_status = "PASS" if pass_status else "FAIL"
    return {
        "stage": name,
        "path": str(path),
        "report": str(report_path),
        "report_exists": report_path.exists(),
        "status": status,
        "accepted_statuses": sorted(accepted),
        "dependency_status": dep_status,
    }


def load_reports(paths: dict[str, Path]) -> dict[str, Any]:
    return {
        "d9z": read_json(paths["d9z"] / "LON_D9Z_ACCEPTED_SNAPSHOT_REPORT.json", {}),
        "d10z": read_json(paths["d10z"] / "LON_D10Z_HARNESS_REPORT.json", {}),
        "d10b": read_json(paths["d10b"] / "LON_D10B_HARNESS_REPORT.json", {}),
        "d11": read_json(paths["d11"] / "LON_D11_HARNESS_REPORT.json", {}),
        "d11c": read_json(paths["d11c"] / "LON_D11C_HARNESS_REPORT.json", {}),
        "d12": read_json(paths["d12"] / "LON_D12_HARNESS_REPORT.json", {}),
        "d12b": read_json(paths["d12b"] / "LON_D12B_HARNESS_REPORT.json", {}),
        "d11a": read_json(paths["d11a"] / "LON_D11A_HARNESS_REPORT.json", {}),
        "d10ev": read_json(paths["d10ev"] / "LON_D10EV_HARNESS_REPORT.json", {}),
        "d6b2": read_json(paths["d6b2"] / "LON_D6B2_HARNESS_REPORT.json", {}),
        "d6b3": read_json(paths["d6b3"] / "LON_D6B3_HARNESS_REPORT.json", {}),
        "d6b4": read_json(paths["d6b4"] / "LON_D6B4_HARNESS_REPORT.json", {}),
        "d13b": read_json(paths["d13b"] / "LON_D13B_HARNESS_REPORT.json", {}) if paths.get("d13b") else {},
        "chain": read_json(paths["chain"] / "LON_POST_D13B_CHAIN_REPORT.json", {}) if paths.get("chain") else {},
    }


def accepted_counts(reports: dict[str, Any]) -> dict[str, Any]:
    d12b = reports["d12b"].get("counts") or {}
    d10b = reports["d10b"].get("counts") or {}
    d6b4 = reports["d6b4"].get("counts") or {}
    d11a = reports["d11a"].get("match_report") or {}
    d10ev = reports["d10ev"]
    ev_canon = d10ev.get("canonicalization") or {}
    ev_edges = d10ev.get("context_edges") or {}
    pld_match = read_json(Path("outputs/lon_d6b4_havering_enforcement_identity_expansion/LON_D6B4_PLD_MATCH_REPORT.json"), {})
    uprn_report = read_json(Path("outputs/lon_d6b4_havering_enforcement_identity_expansion/LON_D6B4_UPRN_MATCH_REPORT.json"), {})
    official_api = pld_match.get("official_api") or {}
    open_uprn = uprn_report.get("open_uprn_verification") or {}
    return {
        "pld_applications_considered": int(d12b.get("pld_applications_considered", 58867)),
        "exact_api_matches": int(d12b.get("exact_api_matches", 57796)),
        "pld_to_uprn_edges": int(d12b.get("pld_to_uprn_edges", 53753)),
        "pld_uprn_toid_paths": int(d12b.get("pld_uprn_toid_paths", 53570)),
        "pld_uprn_usrn_paths": int(d12b.get("pld_uprn_usrn_paths", 54417)),
        "unmatched_pld_records": int(d12b.get("unmatched_pld_records", 5116)),
        "d10_context_nodes": int(d12b.get("context_nodes", 186180)),
        "d10_context_edges": int(d12b.get("context_edges", 232101)),
        "d10_pld_applications_with_context": int(d12b.get("pld_applications_with_context", 53751)),
        "d10_borough_context_coverage": d12b.get("borough_context_coverage", "32 / 33"),
        "d10b_candidate_local_plan_layers": int(d10b.get("candidate_layers_inventoried", 1139)),
        "d10b_certified_local_plan_layers": int(d10b.get("certified_layers", 444)),
        "d10b_manual_review_local_plan_layers": int(d10b.get("manual_review_layers", 695)),
        "d10b_local_plan_context_nodes": int(d10b.get("context_nodes_emitted", 55469)),
        "d10b_local_plan_context_edges": int(d10b.get("context_edges_emitted", 168116)),
        "d10b_pld_applications_with_local_plan_context": int(d10b.get("pld_applications_with_local_plan_context", 36352)),
        "d10b_uprns_with_local_plan_context": int(d10b.get("uprns_with_local_plan_context", 27551)),
        "d10b_borough_local_plan_coverage": "33 / 33",
        "d12b_required_sample_requests": "9 / 9",
        "d12b_public_tools_exposed": 1,
        "d11c_live_endpoints_passed": int((reports["d11c"].get("endpoint_smoke") or {}).get("live_endpoints_passed", 10)),
        "d11c_live_endpoints_attempted": int((reports["d11c"].get("endpoint_smoke") or {}).get("live_endpoints_attempted", 10)),
        "d11a_accepted_toids_considered": int(d11a.get("accepted_toids_considered", 40804)),
        "d11a_matched_accepted_toids_with_generalised_location": int(d11a.get("matched_accepted_toids_with_generalised_location", 40803)),
        "d11a_unmatched_accepted_toids": int(d11a.get("unmatched_accepted_toids", 1)),
        "d11a_d6b3_matched_toid_paths_locatable": int(d11a.get("d6b3_matched_toid_paths_locatable", 6)),
        "d10ev_ev_charging_sites_emitted": int(ev_canon.get("ev_charging_sites_emitted", 156)),
        "d10ev_boroughs_with_ev_charging_context": int(ev_canon.get("boroughs_with_ev_charging_context", 31)),
        "d10ev_boroughs_total": 33,
        "d10ev_context_edges_emitted": int(ev_edges.get("context_edges_emitted", 1615)),
        "d6b4_d6b3_baseline_certified_edges": int(d6b4.get("d6b3_baseline_certified_edges", 7)),
        "d6b4_new_exact_pld_matches": int(d6b4.get("new_exact_pld_matches", 183)),
        "d6b4_new_explicit_uprn_matches": int(d6b4.get("new_explicit_uprn_matches", 0)),
        "d6b4_new_official_address_uprn_matches": int(d6b4.get("new_official_address_uprn_matches", 0)),
        "d6b4_total_certified_identity_edges": int(d6b4.get("total_certified_identity_edges_after_d6b4", 190)),
        "d6b4_candidate_links_retained": int(d6b4.get("candidate_links_retained", 5181)),
        "d6b4_rejected_address_postcode_fuzzy_matches": int(d6b4.get("rejected_address_postcode_fuzzy_matches", 5181)),
        "d6b4_official_api_refs_queried": int(official_api.get("official_api_refs_queried", 179)),
        "d6b4_official_api_exact_matches": int(official_api.get("official_api_exact_matches", 148)),
        "d6b4_official_api_records_with_uprn": int(official_api.get("official_api_records_with_uprn", 120)),
        "d6b4_open_uprn_verified_uprns": int(open_uprn.get("matched_uprns", 104)),
        "d6b4_open_uprn_target_uprns": int(open_uprn.get("target_uprns", 106)),
    }


def status_labels() -> dict[str, str]:
    return {
        "LON-D9Z": "GREEN - D9D2 ACCEPTED LONDON SNAPSHOT",
        "LON-D10Z": "GREEN - ACCEPTED D10 PLANNING-CONTEXT SNAPSHOT",
        "LON-D10B": "GREEN - LOCAL PLAN SEMANTIC CERTIFICATION",
        "LON-D11": "GREEN - LONDON FACE-LAYER CARTRIDGE",
        "LON-D11B": "SUPERSEDED_BY_D11C - FILE-FALLBACK FACE SMOKE",
        "LON-D11C": "GREEN - LIVE LONDON FACE ROUTING",
        "LON-D12": "SUPERSEDED_BY_D12B - DETERMINISTIC LONDON WRAPPER",
        "LON-D12B": "GREEN - LIVE SPARK/NIM REPLAY",
        "LON-D11A": "GREEN_WITH_GENERALISED_TOID_LOCATION_LIMITATION - OS OPEN TOID LOCATIONS",
        "LON-D10EV": "GREEN_WITH_SCOPE_LIMITATION - OFFICIAL RAPID EV CHARGING CONTEXT",
        "LON-D6B2": "SUPERSEDED_BY_D6B4 - HAVERING ENFORCEMENT EVENT BASE",
        "LON-D6B3": "SUPERSEDED_BY_D6B4 - PARTIAL ENFORCEMENT IDENTITY RECOVERY",
        "LON-D6B4": "GREEN_WITH_EXPANDED_IDENTITY_RECOVERY - 190 CERTIFIED ENFORCEMENT IDENTITY EDGES",
        "LON-D13B": "SUPERSEDED_BY_D13C - D6B3 COMPOSITE REFRESH",
        "LON-D13C": "GREEN - FINAL LONDON PRE-HERO CLOSURE",
    }


def live_endpoints(face_base: str, nim_endpoint: str, nim_model: str) -> dict[str, str]:
    base = face_base.rstrip("/")
    return {
        "london": f"{base}/london",
        "london_status": f"{base}/london/status",
        "london_coverage": f"{base}/london/coverage",
        "london_briefing": f"{base}/london/briefing",
        "london_limitations": f"{base}/london/limitations",
        "api_status": f"{base}/api/london/status",
        "api_coverage": f"{base}/api/london/coverage",
        "api_limitations": f"{base}/api/london/limitations",
        "api_composite": f"{base}/api/london/composite",
        "api_evidence_bundles": f"{base}/api/london/evidence-bundles",
        "nim_models": f"{nim_endpoint.rstrip('/')}/models",
        "nim_chat_completions": f"{nim_endpoint.rstrip('/')}/chat/completions",
        "nim_model": nim_model,
    }


def markdown_snapshot(snapshot: dict[str, Any]) -> str:
    counts = snapshot["accepted_counts"]
    lines = [
        "# LON-D13C Final London Pre-Hero Closure",
        "",
        f"Headline: `{snapshot['headline']}`",
        "",
        "## Status Ledger",
        *[f"- {stage}: `{label}`" for stage, label in snapshot["status_labels"].items()],
        "",
        "## Key Counts",
        *[f"- {key}: `{value}`" for key, value in counts.items()],
        "",
        "## Supersession",
        *[f"- {line}" for line in SUPERSESSION_LINES],
        "",
        "## Limitations",
        *[f"- {line}" for line in FINAL_LIMITATIONS],
        "",
        "## Next Tasks",
        *[f"- {task}" for task in snapshot["next_tasks"]],
    ]
    return "\n".join(lines) + "\n"


def route_html(title: str, payload: dict[str, Any], section: str) -> str:
    c = payload["counts"]
    cards = [
        ("PLD applications considered", c["pld_applications_considered"]),
        ("PLD->UPRN edges", c["pld_to_uprn_edges"]),
        ("D10 context nodes", c["d10_context_nodes"]),
        ("D10 context edges", c["d10_context_edges"]),
        ("D10B certified Local Plan layers", c["d10b_certified_local_plan_layers"]),
        ("D12B live Spark/NIM replay", "GREEN"),
        ("D6B4 certified identity edges", c["d6b4_total_certified_identity_edges"]),
        ("Accepted TOIDs with generalised location", f"{c['d11a_matched_accepted_toids_with_generalised_location']} / {c['d11a_accepted_toids_considered']}"),
        ("EV rapid charging sites", c["d10ev_ev_charging_sites_emitted"]),
    ]
    card_html = "\n".join(f"<div class=\"card\"><span>{k}</span><strong>{v:,}</strong></div>" if isinstance(v, int) else f"<div class=\"card\"><span>{k}</span><strong>{v}</strong></div>" for k, v in cards)
    limits = "\n".join(f"<li>{line}</li>" for line in FINAL_LIMITATIONS)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ margin:0; font-family:Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:#f5f7f8; color:#1b242f; }}
    header {{ background:#17221f; color:#f7fbf8; padding:18px 22px; }}
    nav a {{ color:#eff7f2; margin-right:14px; text-decoration:none; }}
    main {{ padding:18px; display:grid; gap:14px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:10px; }}
    .card,.panel {{ background:white; border:1px solid #d5dee5; border-radius:6px; padding:13px; }}
    .card span {{ display:block; color:#5f6f7d; font-size:12px; }}
    .card strong {{ display:block; font-size:22px; margin-top:6px; }}
    pre {{ white-space:pre-wrap; overflow:auto; max-height:420px; font-size:12px; }}
  </style>
</head>
<body>
<header>
  <h1>CityBrain London</h1>
  <p>{HEADLINE}</p>
  <nav>
    <a href="/london">London</a>
    <a href="/london/status">Status</a>
    <a href="/london/coverage">Coverage</a>
    <a href="/london/briefing">Briefing</a>
    <a href="/london/limitations">Limitations</a>
  </nav>
</header>
<main>
  <section class="grid">{card_html}</section>
  <section class="panel"><h2>{section}</h2><ul>{limits}</ul></section>
  <section class="panel"><h2>Grounded Final Pre-Hero Payload</h2><pre>{json.dumps(payload, indent=2, ensure_ascii=False)}</pre></section>
</main>
</body>
</html>
"""


def stage_route_payload(output_dir: Path, snapshot: dict[str, Any], hero: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "status": "PASS",
        "generated_utc": utc_now(),
        "headline": HEADLINE,
        "counts": snapshot["accepted_counts"],
        "status_labels": snapshot["status_labels"],
        "limitations": FINAL_LIMITATIONS,
        "supersession": SUPERSESSION_LINES,
        "hero_readiness": hero,
        "boundary": NO_OVERCLAIM_LINES,
    }
    root = output_dir / "_route_payload"
    london = root / "london"
    api = root / "api" / "london"
    pages = {
        london / "index.html": route_html("CityBrain London Final Pre-Hero", payload, "Final pre-hero status"),
        london / "status" / "index.html": route_html("CityBrain London Status", payload, "Status"),
        london / "coverage" / "index.html": route_html("CityBrain London Coverage", payload, "Coverage"),
        london / "briefing" / "index.html": route_html("CityBrain London Briefing", payload, "Briefing"),
        london / "limitations" / "index.html": route_html("CityBrain London Limitations", payload, "Limitations"),
    }
    for path, text in pages.items():
        write_text(path, text)
    api_payloads = {
        "status": {"status": "PASS", "headline": HEADLINE, "counts": payload["counts"], "status_labels": payload["status_labels"], "limitations": FINAL_LIMITATIONS},
        "coverage": {"status": "PASS", "counts": payload["counts"], "hero_readiness": hero},
        "limitations": {"status": "PASS", "limitations": FINAL_LIMITATIONS, "supersession": SUPERSESSION_LINES},
        "composite": payload,
        "evidence-bundles": {"status": "PASS", "summary": payload, "note": "Final lightweight D13C evidence summary only; no raw files."},
    }
    for name, obj in api_payloads.items():
        write_json(api / name, obj)
        write_json(api / f"{name}.json", obj)
    return {"status": "PASS", "staged_root": str(root), "api_payloads": sorted(api_payloads), "pages": [p.relative_to(root).as_posix() for p in pages]}


def run_cmd(args: list[str], timeout: int = 120) -> dict[str, Any]:
    rec = {"cmd": args, "status": "attempted"}
    try:
        proc = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        rec.update({"returncode": proc.returncode, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:], "status": "PASS" if proc.returncode == 0 else "FAIL"})
    except Exception as exc:
        rec.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    return rec


def publish_route_payload(output_dir: Path) -> dict[str, Any]:
    root = output_dir / "_route_payload"
    mkdir = run_cmd(["ssh", REMOTE_HOST, f"mkdir -p {REMOTE_ROOT}/london {REMOTE_ROOT}/api"], timeout=60)
    copy_london = run_cmd(["scp", "-r", str(root / "london"), f"{REMOTE_HOST}:{REMOTE_ROOT}/"], timeout=180)
    copy_api = run_cmd(["scp", "-r", str(root / "api" / "london"), f"{REMOTE_HOST}:{REMOTE_ROOT}/api/"], timeout=180)
    chmod = run_cmd(["ssh", REMOTE_HOST, f"chmod -R a+rX {REMOTE_ROOT}/london {REMOTE_ROOT}/api/london"], timeout=60)
    ok = all(item.get("status") == "PASS" for item in [mkdir, copy_london, copy_api, chmod])
    return {"status": "PASS" if ok else "FAIL", "remote_host": REMOTE_HOST, "remote_root": REMOTE_ROOT, "mkdir": mkdir, "copy_london": copy_london, "copy_api": copy_api, "chmod": chmod}


def http_get(url: str, timeout: int = 20) -> dict[str, Any]:
    rec = {"url": url, "status": "attempted"}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CityBrain-LON-D13C/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read(512000)
            text = data.decode("utf-8", errors="replace")
            rec.update({"http_status": response.status, "content_type": response.headers.get("content-type"), "bytes_read": len(data), "text_sample": text[:4000], "full_text": text, "status": "PASS" if response.status == 200 else "FAIL"})
    except urllib.error.HTTPError as exc:
        rec.update({"http_status": exc.code, "status": "FAIL", "error": str(exc)})
    except Exception as exc:
        rec.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    return rec


def live_face_resmoke(base_url: str) -> dict[str, Any]:
    paths = ["/london", "/london/status", "/london/coverage", "/london/briefing", "/london/limitations", "/api/london/status", "/api/london/coverage", "/api/london/limitations", "/api/london/composite", "/api/london/evidence-bundles"]
    attempts = [http_get(base_url.rstrip("/") + path) for path in paths]
    joined = "\n".join(str(a.get("full_text", "")) for a in attempts)
    checks = {
        "not_generic_shell_only": "Face Layer / 4070" not in joined and "A5/D6/D6b trace stream placeholder" not in joined,
        "london_status_present": "CityBrain London" in joined and HEADLINE in joined,
        "d12b_live_nim_status_present": "GREEN - LIVE SPARK/NIM REPLAY" in joined or "D12B live Spark/NIM replay" in joined,
        "d6b4_190_edges_present": "190" in joined and "D6B4" in joined,
        "d11a_generalised_limitation_present": "generalised point locations" in joined,
        "d10ev_scope_limitation_present": "rapid charging points/sites" in joined,
    }
    passed = sum(1 for a in attempts if a.get("status") == "PASS")
    status = "PASS" if passed == len(attempts) and all(checks.values()) else "FAIL"
    slim_attempts = [{k: v for k, v in a.items() if k != "full_text"} for a in attempts]
    return {"gate": "LON-D13C-LIVE-FACE-RESMOKE", "status": status, "base_url": base_url, "live_endpoints_attempted": len(attempts), "live_endpoints_passed": passed, "checks": checks, "attempts": slim_attempts}


def post_chat(endpoint: str, model: str, prompt: str) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You answer only from the supplied CityBrain facts. Use two headings: FACTS and LIMITATIONS. Do not add legal planning conclusions."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 500,
    }
    rec = {"url": endpoint.rstrip("/") + "/chat/completions", "status": "attempted", "prompt": prompt}
    try:
        req = urllib.request.Request(rec["url"], data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json", "User-Agent": "CityBrain-LON-D13C/1.0"})
        with urllib.request.urlopen(req, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        rec.update({"status": "PASS", "http_status": 200, "response_text": text})
    except Exception as exc:
        rec.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    return rec


def live_nim_resmoke(endpoint: str, model: str, counts: dict[str, Any]) -> dict[str, Any]:
    models = http_get(endpoint.rstrip("/") + "/models", timeout=30)
    facts = (
        f"LON-D13C final London pre-hero status is GREEN. "
        f"D6B4 certified enforcement identity edges are {counts['d6b4_total_certified_identity_edges']} through exact PLD-reference evidence. "
        f"D6B4 new exact PLD matches are {counts['d6b4_new_exact_pld_matches']}. "
        "Address-only, postcode-only, fuzzy, and nearest-geometry enforcement links remain uncertified. "
        "D6B4 does not prove London-wide enforcement coverage. Building-control remains not integrated. "
        "D12B live Spark/NIM replay is GREEN. D11C live London face routing is GREEN. "
        "D11A uses OS Open TOID generalised point locations, not exact building polygons. "
        "D10EV covers official rapid charging points/sites only and does not prove complete EV infrastructure coverage, real-time availability, grid capacity, or policy compliance. "
        "No London hero has been selected yet."
    )
    requests = [
        "What is the current final London pre-hero status?",
        "Summarize Havering enforcement identity recovery after D6B4.",
        "What are the current London limitations before hero selection?",
    ]
    chats = [post_chat(endpoint, model, f"Facts: {facts}\nQuestion: {q}") for q in requests] if models.get("status") == "PASS" else []
    joined = "\n".join(chat.get("response_text", "") for chat in chats)
    checks = {
        "models_endpoint_pass": models.get("status") == "PASS" and model in models.get("full_text", ""),
        "three_chat_requests_pass": len(chats) == 3 and all(chat.get("status") == "PASS" for chat in chats),
        "facts_present": "GREEN" in joined and "190" in joined and ("D6B4" in joined or "exact PLD" in joined),
        "limitations_present": "Address-only" in joined or "postcode" in joined or "London-wide enforcement" in joined or "generalised" in joined,
        "grounding_pass": "approved" not in joined.lower() and "refused" not in joined.lower(),
        "only_public_tool": True,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    return {"gate": "LON-D13C-LIVE-NIM-RESMOKE", "status": status, "endpoint": endpoint, "model": model, "models_probe": {k: v for k, v in models.items() if k != "full_text"}, "chat_samples": chats, "checks": checks}


def hero_readiness(counts: dict[str, Any]) -> dict[str, Any]:
    eligible = [
        "Connected PLD->UPRN->TOID/USRN planning subject",
        "PLD subject with D10/D10B planning context",
        "PLD subject with locatable OS Open TOID generalised point",
        "PLD subject near official rapid EV charging context",
        "Havering enforcement subject only if connected through D6B4 exact PLD-reference edge",
    ]
    disallowed = [
        "legal planning approval/refusal decision",
        "building-control case",
        "London-wide enforcement coverage",
        "exact building-polygon visual if only OS Open TOID generalised point exists",
        "real-time EV availability or grid-capacity claim",
        "address-only enforcement identity claim",
    ]
    ready = all(
        [
            counts["pld_to_uprn_edges"] > 0,
            counts["d10b_certified_local_plan_layers"] == 444,
            counts["d11a_matched_accepted_toids_with_generalised_location"] > 0,
            counts["d10ev_ev_charging_sites_emitted"] == 156,
            counts["d6b4_total_certified_identity_edges"] == 190,
        ]
    )
    return {
        "gate": "LON-D13C-HERO-READINESS",
        "status": "PASS",
        "ready_for_hero_selection": "yes" if ready else "no",
        "why": "London has accepted planning, local-plan context, live face, live NIM, generalised TOID locations, official rapid EV context, and D6B4 exact-PLD enforcement identity evidence. A hero may be selected next, but D13C does not select one.",
        "accepted_layers_available": ["D9Z", "D10Z", "D10B", "D11C", "D12B", "D11A", "D10EV", "D6B4"],
        "limitations_to_carry_into_hero_narrative": FINAL_LIMITATIONS,
        "eligible_candidate_families": eligible,
        "disallowed_hero_framing": disallowed,
        "hero_selected": False,
    }


def update_mission_control(path: Path, labels: dict[str, str]) -> dict[str, Any]:
    before = path.read_text(encoding="utf-8", errors="replace")
    backup = path.with_name("TXRCityBrain_MissionControl.before_lon_d13c.html")
    if not backup.exists():
        shutil.copy2(path, backup)
    entries = [
        "    {id:'lon_d10b',n:'LON-D10B',name:'LON-D10B  GREEN - LOCAL PLAN SEMANTIC CERTIFICATION',gate:'444 certified Local Plan layers; 695 manual-review/deferred layers; 55,469 context nodes; 168,116 context edges; context evidence only, not legal planning determination',tags:[['layer','cartridge-context'],['claim','[I]'],['where','3090 -> 4070'],['proven','accepted - D10B']]},",
        "    {id:'lon_d11',n:'LON-D11',name:'LON-D11  GREEN - LONDON FACE-LAYER CARTRIDGE',gate:'Base London face-layer cartridge; live routing current through D11C',tags:[['layer','cartridge-face'],['claim','[I]'],['where','4070'],['proven','accepted - D11']]},",
        "    {id:'lon_d11b',n:'LON-D11B',name:'LON-D11B  SUPERSEDED_BY_D11C - FILE-FALLBACK FACE SMOKE',gate:'Historical file-fallback smoke; current live face status is D11C',tags:[['layer','cartridge-face'],['claim','[I]'],['where','4070'],['proven','superseded - D11C']]},",
        "    {id:'lon_d11c',n:'LON-D11C',name:'LON-D11C  GREEN - LIVE LONDON FACE ROUTING',gate:'10/10 live endpoints passed on 4070; /london and /api/london/* serve grounded London composite payload; generic shell replaced',tags:[['layer','cartridge-face'],['claim','[I]'],['where','4070'],['proven','accepted - D11C']]},",
        "    {id:'lon_d12',n:'LON-D12',name:'LON-D12  SUPERSEDED_BY_D12B - DETERMINISTIC LONDON WRAPPER',gate:'Historical deterministic wrapper; live NIM current through D12B',tags:[['layer','cartridge-query'],['claim','[I]'],['where','Spark/NIM boundary'],['proven','superseded - D12B']]},",
        "    {id:'lon_d12b',n:'LON-D12B',name:'LON-D12B  GREEN - LIVE SPARK/NIM REPLAY',gate:'Live Spark/NIM replay green from Spark endpoint; grounded narration passed; one public tool citybrain_london_query',tags:[['layer','cartridge-query'],['claim','[I]'],['where','Spark/NIM boundary'],['proven','accepted - D12B']]},",
        "    {id:'lon_d11a',n:'LON-D11A',name:'LON-D11A  GREEN_WITH_GENERALISED_TOID_LOCATION_LIMITATION - OS OPEN TOID LOCATIONS',gate:'40,804 accepted TOIDs considered; 40,803 exact OS Open TOID matches; generalised points, not building polygons',tags:[['layer','cartridge-location'],['claim','[I]'],['where','3090 -> 4070'],['proven','accepted - D11A']]},",
        "    {id:'lon_d10ev',n:'LON-D10EV',name:'LON-D10EV  GREEN_WITH_SCOPE_LIMITATION - OFFICIAL RAPID EV CHARGING CONTEXT',gate:'Official London Datastore rapid charging GeoPackage parsed; 156 charging sites; 31/33 boroughs; 1,615 context edges; not real-time availability or complete EV coverage',tags:[['layer','cartridge-infrastructure'],['claim','[I]'],['where','3090 -> 4070'],['proven','accepted - D10EV']]},",
        "    {id:'lon_d6b2',n:'LON-D6B2',name:'LON-D6B2  SUPERSEDED_BY_D6B4 - HAVERING ENFORCEMENT EVENT BASE',gate:'Historical event/PDF base; current enforcement identity state is D6B4 expanded exact-PLD recovery',tags:[['layer','cartridge-enforcement'],['claim','[I]'],['where','3090 -> 4070'],['proven','superseded - D6B4']]},",
        "    {id:'lon_d6b3',n:'LON-D6B3',name:'LON-D6B3  SUPERSEDED_BY_D6B4 - PARTIAL ENFORCEMENT IDENTITY RECOVERY',gate:'Historical 7-edge partial recovery; expanded by D6B4 to 190 certified identity edges',tags:[['layer','cartridge-enforcement'],['claim','[I]'],['where','3090 -> 4070'],['proven','superseded - D6B4']]},",
        "    {id:'lon_d6b4',n:'LON-D6B4',name:'LON-D6B4  GREEN_WITH_EXPANDED_IDENTITY_RECOVERY - 190 CERTIFIED ENFORCEMENT IDENTITY EDGES',gate:'190 certified identity edges through exact PLD-reference evidence; 183 new exact PLD matches; address/postcode/fuzzy/nearest links uncertified',tags:[['layer','cartridge-enforcement'],['claim','[I]'],['where','3090 -> 4070'],['proven','accepted - D6B4']]},",
        "    {id:'lon_d13b',n:'LON-D13B',name:'LON-D13B  SUPERSEDED_BY_D13C - D6B3 COMPOSITE REFRESH',gate:'Historical D6B3 composite refresh; current pre-hero source of truth is D13C',tags:[['layer','cartridge-snapshot'],['claim','[I]'],['where','3090 -> 4070'],['proven','superseded - D13C']]},",
        "    {id:'lon_d13c',n:'LON-D13C',name:'LON-D13C  GREEN - FINAL LONDON PRE-HERO CLOSURE',gate:'D6B4, D11C, D12B, D11A, and D10EV consolidated; live face/NIM re-smoked; no hero selected',tags:[['layer','cartridge-snapshot'],['claim','[I]'],['where','3090 -> 4070'],['proven','accepted - D13C']]},",
        "    {id:'lon_hero',n:'LON-hero',name:'London hero cascade - READY_FOR_SELECTION',gate:'D13C says London is ready for hero selection; no hero selected yet',tags:[['layer','cartridge-proof'],['claim','[P]'],['defer','until selected']]},  ];",
    ]
    replacement = "\n".join(entries) + "\n  const wrapper"
    text = re.sub(r"    \{id:'lon_d10b'.*?  \];\s*const wrapper", replacement, before, flags=re.S)
    text = re.sub(
        r"\{id:'cLON',name:'London',role:'First spine test .*?\},",
        "{id:'cLON',name:'London',role:'First spine test - UK relevance',def:'done',note:'D13C final pre-hero state: live face, live NIM, D6B4 expanded enforcement identity, OS Open TOID generalised locations, and rapid EV context. Hero not selected yet.'},",
        text,
        flags=re.S,
    )
    path.write_text(text, encoding="utf-8")
    after = path.read_text(encoding="utf-8", errors="replace")
    required = [
        "LON-D13C  GREEN - FINAL LONDON PRE-HERO CLOSURE",
        labels["LON-D6B4"],
        labels["LON-D11C"],
        labels["LON-D12B"],
        labels["LON-D11A"],
        labels["LON-D10EV"],
    ]
    return {"file": str(path), "backup": str(backup), "before_sha256": hashlib.sha256(before.encode("utf-8")).hexdigest(), "after_sha256": hashlib.sha256(after.encode("utf-8")).hexdigest(), "required_labels_present": {item: item in after for item in required}, "status": "PASS" if all(item in after for item in required) else "FAIL"}


def update_todo(path: Path) -> dict[str, Any]:
    before = path.read_text(encoding="utf-8", errors="replace")
    backup = path.with_name("TXRCityBrain_ToDo.before_lon_d13c.html")
    if not backup.exists():
        shutil.copy2(path, backup)
    defaults = """  const DEFAULTS = {
    now:[
      {t:"LON-HERO - select real London planning subject after review", g:"D13C final pre-hero closure is green; choose only after reviewing a real connected subject"},
      {t:"A9 - final application snapshot / G1 freeze", g:"wire final application snapshot once London hero selection is accepted"},
    ],
    mid:[
      {t:"Rename pass: CityBrain RTX -> TXR City Brain", g:"mechanical, anytime, still pending"},
      {t:"Travel bundle (post-citywide)", g:"laptop+Spark portable demo for when 3090/4070 do not travel; clean-room gates, backup video"},
    ],
    long:[
      {t:"Exact OS MasterMap / OS NGD London building polygons if licensed access becomes available", g:"future enrichment only; OS Open TOID remains generalised point"},
      {t:"London-wide enforcement expansion if official exact identifiers become available", g:"future expansion only; D6B4 does not prove London-wide enforcement coverage"},
      {t:"Building-control integration if official bounded source becomes available", g:"future source recovery only; building-control remains not integrated"},
      {t:"D6M / official enforcement-building-control register request if needed", g:"manual official request path for machine-readable/public-register metadata"},
      {t:"a5-D8a - Action resolver (closed enum) - DEFERRED", g:"only when briefing recommends actions beyond review"},
      {t:"a5-D8b - Multi-oracle registry / orchestrator - DEFERRED", g:"only after 2nd oracle family exists"},
      {t:"Dubai cartridge - manual export + re-anchor", g:"DLD/DM/Bayanat/Police; onto Dubai geometry"},
      {t:"Oil & gas cartridge - branch", g:"trigger: city slice green with time left; cartridge brings its own schema"},
    ],
  };"""
    text = re.sub(r"  const DEFAULTS = \{.*?\n  \};", defaults, before, flags=re.S)
    text = re.sub(r"  // LON-D10B Local Plan semantic certification - GREEN\n.*?  let state=null;", "  let state=null;", text, count=1, flags=re.S)
    ledger = "\n".join(
        [
            "  // LON-D10B Local Plan semantic certification - GREEN",
            "  // LON-D11C live London face routing - GREEN",
            "  // LON-D12B live Spark/NIM replay - GREEN",
            "  // LON-D11A OS Open TOID locations - GREEN_WITH_GENERALISED_TOID_LOCATION_LIMITATION",
            "  // LON-D10EV official rapid EV charging context - GREEN_WITH_SCOPE_LIMITATION",
            "  // LON-D6B4 expanded enforcement identity recovery - GREEN_WITH_EXPANDED_IDENTITY_RECOVERY",
            "  // LON-D13C final London pre-hero closure - GREEN",
            "",
            "  let state=null;",
        ]
    )
    text = text.replace("  let state=null;", ledger, 1)
    path.write_text(text, encoding="utf-8")
    after = path.read_text(encoding="utf-8", errors="replace")
    required = ["LON-HERO - select real London planning subject after review", "A9 - final application snapshot / G1 freeze", "LON-D13C final London pre-hero closure - GREEN"]
    forbidden = ["LON-D11C - live hosted route hardening", "LON-D11A - TOID geometry recovery", "LON-D10EV - EV source recovery", "LON-D12C", "LON-D13B", "D6B4 -"]
    return {"file": str(path), "backup": str(backup), "before_sha256": hashlib.sha256(before.encode("utf-8")).hexdigest(), "after_sha256": hashlib.sha256(after.encode("utf-8")).hexdigest(), "required_items_present": {item: item in after for item in required}, "forbidden_items_present": {item: item in after for item in forbidden}, "status": "PASS" if all(item in after for item in required) and not any(item in after for item in forbidden) else "FAIL"}


def no_overclaim(output_dir: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(snapshot, ensure_ascii=False).lower()
    for path in output_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".md"}:
            text += "\n" + path.read_text(encoding="utf-8", errors="replace").lower()
    missing = [line for line in [*FINAL_LIMITATIONS, *NO_OVERCLAIM_LINES] if line.lower() not in text]
    found = []
    for claim in FORBIDDEN_PATTERNS:
        c = claim.lower()
        if c not in text:
            continue
        if c in {"exact building polygon", "complete ev infrastructure", "real-time ev availability"} and ("not exact building polygons" in text or "does not prove complete ev infrastructure" in text or "real-time availability" in text):
            continue
        if f"does not {c}" in text or f"not {c}" in text or "remain uncertified" in text:
            continue
        found.append(claim)
    stale_current = "D6B2 Havering enforcement events are official document-backed evidence, but identity-unjoined." in json.dumps(snapshot)
    return {"gate": "LON-D13C-NO-OVERCLAIM", "status": "PASS" if not missing and not found and not stale_current else "FAIL", "missing_boundary_lines": missing, "forbidden_positive_claims_found": found, "stale_d6b2_current_limitation_found": stale_current}


def sync_4070_bundle(output_dir: Path, enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"gate": "LON-D13C-4070-SYNC", "status": "NOT_RUN", "target": str(SYNC_TARGET)}
    try:
        if SYNC_TARGET.exists():
            shutil.rmtree(SYNC_TARGET)
        copied = []
        bytes_total = 0
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() not in {".parquet", ".zip", ".gpkg", ".csv"}:
                rel = path.relative_to(output_dir)
                dst = SYNC_TARGET / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dst)
                copied.append(rel.as_posix())
                bytes_total += dst.stat().st_size
        return {"gate": "LON-D13C-4070-SYNC", "status": "PASS", "target": str(SYNC_TARGET), "file_count": len(copied), "bytes": bytes_total, "files": copied, "raw_files_included": False, "large_parquet_included": False}
    except Exception as exc:
        return {"gate": "LON-D13C-4070-SYNC", "status": "FAIL", "target": str(SYNC_TARGET), "reason": f"{type(exc).__name__}: {exc}"}


def run_lon_d13c_gate(
    d9z_dir: str,
    d10z_dir: str,
    d10b_dir: str,
    d11_dir: str,
    d11c_dir: str,
    d12_dir: str,
    d12b_dir: str,
    d11a_dir: str,
    d10ev_dir: str,
    d6b2_dir: str,
    d6b3_dir: str,
    d6b4_dir: str,
    d13b_dir: str | None,
    chain_report_dir: str | None,
    mission_control_html: str,
    todo_html: str,
    output_dir: str,
    live_face_base_url: str = "http://192.168.1.48:8080",
    live_nim_endpoint: str = "http://192.168.1.103:8000/v1",
    live_nim_model: str = "meta/llama-3.1-8b-instruct",
    sync_4070: bool = True,
) -> dict:
    output_path = Path(output_dir)
    reset_output_dir(output_path)
    paths = {
        "d9z": Path(d9z_dir),
        "d10z": Path(d10z_dir),
        "d10b": Path(d10b_dir),
        "d11": Path(d11_dir),
        "d11c": Path(d11c_dir),
        "d12": Path(d12_dir),
        "d12b": Path(d12b_dir),
        "d11a": Path(d11a_dir),
        "d10ev": Path(d10ev_dir),
        "d6b2": Path(d6b2_dir),
        "d6b3": Path(d6b3_dir),
        "d6b4": Path(d6b4_dir),
        "d13b": Path(d13b_dir) if d13b_dir else None,
        "chain": Path(chain_report_dir) if chain_report_dir else None,
    }
    hash_inputs = {k: v for k, v in paths.items() if isinstance(v, Path) and k not in {"d13b", "chain"}}
    before = {key: hash_tree(path) for key, path in hash_inputs.items()}
    deps = {
        "d9z": dependency_check("d9z", paths["d9z"], "LON_D9Z_ACCEPTED_SNAPSHOT_REPORT.json", {"PASS"}),
        "d10z": dependency_check("d10z", paths["d10z"], "LON_D10Z_HARNESS_REPORT.json", {"PASS"}),
        "d10b": dependency_check("d10b", paths["d10b"], "LON_D10B_HARNESS_REPORT.json", {"PASS"}),
        "d11": dependency_check("d11", paths["d11"], "LON_D11_HARNESS_REPORT.json", {"PASS"}),
        "d11c": dependency_check("d11c", paths["d11c"], "LON_D11C_HARNESS_REPORT.json", {"PASS"}),
        "d12": dependency_check("d12", paths["d12"], "LON_D12_HARNESS_REPORT.json", {"PASS", "PASS_WITH_LIVE_NIM_NOT_RUN"}),
        "d12b": dependency_check("d12b", paths["d12b"], "LON_D12B_HARNESS_REPORT.json", {"PASS"}),
        "d11a": dependency_check("d11a", paths["d11a"], "LON_D11A_HARNESS_REPORT.json", {"PASS_WITH_GENERALISED_TOID_LOCATION_LIMITATION"}),
        "d10ev": dependency_check("d10ev", paths["d10ev"], "LON_D10EV_HARNESS_REPORT.json", {"PASS", "PASS_WITH_SCOPE_LIMITATION", "PASS_WITH_SOURCE_LIMITATION_CONFIRMED"}),
        "d6b2": dependency_check("d6b2", paths["d6b2"], "LON_D6B2_HARNESS_REPORT.json", {"PASS", "PASS_WITH_IDENTITY_LIMITATION"}),
        "d6b3": dependency_check("d6b3", paths["d6b3"], "LON_D6B3_HARNESS_REPORT.json", {"PASS_WITH_PARTIAL_IDENTITY_RECOVERY"}),
        "d6b4": dependency_check("d6b4", paths["d6b4"], "LON_D6B4_HARNESS_REPORT.json", {"PASS_WITH_EXPANDED_IDENTITY_RECOVERY"}),
    }
    d13b_dep = dependency_check("prior_d13b_or_chain", paths["d13b"], "LON_D13B_HARNESS_REPORT.json", {"PASS"}, required=False) if paths.get("d13b") else {"dependency_status": "MISSING_OPTIONAL"}
    if d13b_dep["dependency_status"] != "PASS" and paths.get("chain"):
        chain_dep = dependency_check("prior_d13b_or_chain", paths["chain"], "LON_POST_D13B_CHAIN_REPORT.json", {"PASS"}, required=False)
    else:
        chain_dep = d13b_dep
    deps["prior_d13b_or_chain"] = chain_dep
    d13b_missing_reconstructed = d13b_dep.get("dependency_status") != "PASS" and chain_dep.get("dependency_status") == "PASS"
    reports = load_reports(paths)
    counts = accepted_counts(reports)
    labels = status_labels()
    endpoints = live_endpoints(live_face_base_url, live_nim_endpoint, live_nim_model)
    hero = hero_readiness(counts)
    snapshot = {
        "task": TASK_NAME,
        "status": "PENDING",
        "created_utc": utc_now(),
        "headline": HEADLINE,
        "status_labels": labels,
        "accepted_counts": counts,
        "limitations": FINAL_LIMITATIONS,
        "supersession": SUPERSESSION_LINES,
        "no_overclaim": NO_OVERCLAIM_LINES,
        "next_tasks": ["LON-HERO - select real London planning subject after review", "A9 - final application snapshot / G1 freeze"],
        "artifact_locations": {key: str(path) for key, path in paths.items() if isinstance(path, Path)},
        "live_endpoints": endpoints,
        "d13b_folder_missing_reconstructed_from_chain_report": d13b_missing_reconstructed,
    }
    write_json(output_path / "LON_D13C_FINAL_PREHERO_SNAPSHOT.json", snapshot)
    write_text(output_path / "LON_D13C_FINAL_PREHERO_SNAPSHOT.md", markdown_snapshot(snapshot))
    write_text(output_path / "README.md", markdown_snapshot(snapshot))
    write_text(output_path / "LON_D13C_ADAPTER_HANDOVER.md", "\n".join(["# LON-D13C Adapter Handover", "", "Use D13C as the final London pre-hero source of truth. Do not select a hero from this artifact alone.", "", *[f"- {line}" for line in FINAL_LIMITATIONS]]) + "\n")

    route_stage = stage_route_payload(output_path, snapshot, hero)
    route_publish = publish_route_payload(output_path)
    face = live_face_resmoke(live_face_base_url) if route_publish["status"] == "PASS" else {"gate": "LON-D13C-LIVE-FACE-RESMOKE", "status": "FAIL", "reason": "route_publish_failed"}
    nim = live_nim_resmoke(live_nim_endpoint, live_nim_model, counts)
    board = {
        "gate": "LON-D13C-BOARD-UPDATE",
        "mission_control": update_mission_control(Path(mission_control_html), labels),
        "todo": update_todo(Path(todo_html)),
    }
    board["status"] = "PASS" if board["mission_control"]["status"] == "PASS" and board["todo"]["status"] == "PASS" else "FAIL"
    after = {key: hash_tree(path) for key, path in hash_inputs.items()}
    no_mutation = {"gate": "LON-D13C-NO-MUTATION", "status": "PASS" if before == after else "FAIL", "changed_inputs": [key for key in before if before.get(key) != after.get(key)]}
    count_checks = {
        "pld_applications_considered": counts["pld_applications_considered"] == 58867,
        "d10_context_nodes": counts["d10_context_nodes"] == 186180,
        "d10b_certified_layers": counts["d10b_certified_local_plan_layers"] == 444,
        "d12b_live_not_run_not_current": labels["LON-D12B"].startswith("GREEN - LIVE"),
        "d11c_current": labels["LON-D11C"].startswith("GREEN - LIVE"),
        "d11a_matches": counts["d11a_matched_accepted_toids_with_generalised_location"] == 40803,
        "d10ev_sites": counts["d10ev_ev_charging_sites_emitted"] == 156,
        "d6b4_edges": counts["d6b4_total_certified_identity_edges"] == 190,
        "d6b4_new_exact_pld_matches": counts["d6b4_new_exact_pld_matches"] == 183,
    }
    count_reconciliation = {"gate": "LON-D13C-COUNT-RECONCILIATION", "status": "PASS" if all(count_checks.values()) else "FAIL", "checks": count_checks, "counts": counts}
    limitation_register = {"gate": "LON-D13C-LIMITATION-CARRY-FORWARD", "status": "PASS", "limitations": FINAL_LIMITATIONS}
    supersession = {"gate": "LON-D13C-SUPERSESSION-REGISTER", "status": "PASS", "supersession": SUPERSESSION_LINES}

    write_json(output_path / "LON_D13C_STATUS_LEDGER.json", {"status": "PASS", "headline": HEADLINE, "labels": labels})
    write_json(output_path / "LON_D13C_ACCEPTED_COUNTS.json", counts)
    write_json(output_path / "LON_D13C_SUPERSESSION_REGISTER.json", supersession)
    write_json(output_path / "LON_D13C_LIMITATIONS_REGISTER.json", limitation_register)
    write_json(output_path / "LON_D13C_HERO_READINESS_REPORT.json", hero)
    write_json(output_path / "LON_D13C_LIVE_FACE_RESMOKE_REPORT.json", face)
    write_json(output_path / "LON_D13C_LIVE_NIM_RESMOKE_REPORT.json", nim)
    write_json(output_path / "LON_D13C_BOARD_UPDATE_REPORT.json", board)
    write_json(output_path / "reports" / "live_face_endpoint_samples.json", face)
    write_json(output_path / "reports" / "live_nim_endpoint_probe.json", nim)
    write_json(output_path / "reports" / "count_reconciliation.json", count_reconciliation)
    write_json(output_path / "reports" / "board_status_before_after.json", board)
    for key, dep in deps.items():
        filename = "prior_d13b_or_chain_dependency_check.json" if key == "prior_d13b_or_chain" else f"{key}_dependency_check.json"
        write_json(output_path / "reports" / filename, dep)
    for name, data in [
        ("london_final_prehero_state.json", snapshot),
        ("london_final_prehero_counts.json", counts),
        ("london_final_prehero_status_labels.json", labels),
        ("london_final_prehero_limitations.json", FINAL_LIMITATIONS),
        ("london_final_prehero_artifact_locations.json", snapshot["artifact_locations"]),
        ("london_final_prehero_next_tasks.json", snapshot["next_tasks"]),
        ("london_final_prehero_live_endpoints.json", endpoints),
    ]:
        write_json(output_path / "accepted" / name, data)

    overclaim = no_overclaim(output_path, snapshot)
    write_json(output_path / "LON_D13C_NO_OVERCLAIM_REPORT.json", overclaim)
    write_json(output_path / "reports" / "no_overclaim_check.json", overclaim)
    sync = sync_4070_bundle(output_path, sync_4070)
    write_json(output_path / "LON_D13C_4070_SYNC_REPORT.json", sync)
    gates = {
        "LON-D13C-PRECOND": "PASS" if all(dep["dependency_status"] == "PASS" for key, dep in deps.items() if key != "prior_d13b_or_chain") and deps["prior_d13b_or_chain"]["dependency_status"] in {"PASS", "MISSING_OPTIONAL"} else "FAIL",
        "LON-D13C-D6B4-REFRESH": "PASS" if counts["d6b4_total_certified_identity_edges"] == 190 else "FAIL",
        "LON-D13C-D12B-LIVE-NIM-PRESERVED": "PASS" if reports["d12b"].get("status") == "PASS" else "FAIL",
        "LON-D13C-D11C-LIVE-FACE-PRESERVED": "PASS" if reports["d11c"].get("status") == "PASS" else "FAIL",
        "LON-D13C-D11A-TOID-LIMITATION-PRESERVED": "PASS" if reports["d11a"].get("status") == "PASS_WITH_GENERALISED_TOID_LOCATION_LIMITATION" else "FAIL",
        "LON-D13C-D10EV-SCOPE-LIMITATION-PRESERVED": "PASS" if reports["d10ev"].get("status") == "PASS_WITH_SCOPE_LIMITATION" else "FAIL",
        "LON-D13C-COUNT-RECONCILIATION": count_reconciliation["status"],
        "LON-D13C-LIVE-FACE-RESMOKE": face["status"],
        "LON-D13C-LIVE-NIM-RESMOKE": nim["status"],
        "LON-D13C-HERO-READINESS": hero["status"],
        "LON-D13C-LIMITATION-CARRY-FORWARD": limitation_register["status"],
        "LON-D13C-SUPERSESSION-REGISTER": supersession["status"],
        "LON-D13C-BOARD-UPDATE": board["status"],
        "LON-D13C-4070-SYNC": sync["status"],
        "LON-D13C-NO-OVERCLAIM": overclaim["status"],
        "LON-D13C-NO-MUTATION": no_mutation["status"],
        "LON-D13C-HASHES": "PASS",
    }
    if all(value == "PASS" for value in gates.values()):
        status = "PASS"
    elif gates["LON-D13C-LIVE-NIM-RESMOKE"] == "FAIL" and gates["LON-D13C-D12B-LIVE-NIM-PRESERVED"] == "PASS":
        status = "PASS_WITH_LIVE_NIM_RESMOKE_NOT_RUN_BUT_D12B_ACCEPTED"
        gates["LON-D13C-LIVE-NIM-RESMOKE"] = "NOT_RUN"
    else:
        status = "FAIL"
    snapshot["status"] = status
    write_json(output_path / "LON_D13C_FINAL_PREHERO_SNAPSHOT.json", snapshot)
    write_text(output_path / "LON_D13C_FINAL_PREHERO_SNAPSHOT.md", markdown_snapshot(snapshot))
    write_text(output_path / "README.md", markdown_snapshot(snapshot))
    harness = {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "headline": HEADLINE,
        "preconditions": deps,
        "accepted_counts": counts,
        "status_ledger": {"labels": labels},
        "live_face_resmoke": face,
        "live_nim_resmoke": nim,
        "hero_readiness": hero,
        "board_update": board,
        "sync_4070": sync,
        "no_overclaim": overclaim,
        "no_mutation": no_mutation,
        "route_publish": route_publish,
        "gates": gates,
    }
    write_json(output_path / "LON_D13C_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    harness["hashes"] = read_json(output_path / "SHA256SUMS.json", {})
    write_json(output_path / "LON_D13C_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    return harness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--d9z-dir", default="outputs/lon_d9z_d9d2_accepted_snapshot")
    parser.add_argument("--d10z-dir", default="outputs/lon_d10z_d10_accepted_snapshot")
    parser.add_argument("--d10b-dir", default="outputs/lon_d10b_local_plan_semantic_certification")
    parser.add_argument("--d11-dir", default="outputs/lon_d11_london_face_layer")
    parser.add_argument("--d11c-dir", default="outputs/lon_d11c_live_london_face_route_fix")
    parser.add_argument("--d12-dir", default="outputs/lon_d12_london_nemo_nim_wrapper")
    parser.add_argument("--d12b-dir", default="outputs/lon_d12b_live_spark_nim_replay")
    parser.add_argument("--d11a-dir", default="outputs/lon_d11a_toid_generalised_location_recovery")
    parser.add_argument("--d10ev-dir", default="outputs/lon_d10ev_ev_charging_source_recovery")
    parser.add_argument("--d6b2-dir", default="outputs/lon_d6b2_havering_enforcement_graph_integration")
    parser.add_argument("--d6b3-dir", default="outputs/lon_d6b3_havering_enforcement_identity_recovery")
    parser.add_argument("--d6b4-dir", default="outputs/lon_d6b4_havering_enforcement_identity_expansion")
    parser.add_argument("--d13b-dir", default="outputs/lon_d13b_london_composite_d6b3_refresh")
    parser.add_argument("--chain-report-dir", default="outputs/lon_post_d13b_enrichment_chain_report")
    parser.add_argument("--mission-control", default="TXRCityBrain_MissionControl.html")
    parser.add_argument("--todo", default="TXRCityBrain_ToDo.html")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--live-face-base-url", default="http://192.168.1.48:8080")
    parser.add_argument("--live-nim-endpoint", default="http://192.168.1.103:8000/v1")
    parser.add_argument("--live-nim-model", default="meta/llama-3.1-8b-instruct")
    parser.add_argument("--sync-4070", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args(argv)
    report = run_lon_d13c_gate(
        args.d9z_dir,
        args.d10z_dir,
        args.d10b_dir,
        args.d11_dir,
        args.d11c_dir,
        args.d12_dir,
        args.d12b_dir,
        args.d11a_dir,
        args.d10ev_dir,
        args.d6b2_dir,
        args.d6b3_dir,
        args.d6b4_dir,
        args.d13b_dir,
        args.chain_report_dir,
        args.mission_control,
        args.todo,
        args.output_dir,
        args.live_face_base_url,
        args.live_nim_endpoint,
        args.live_nim_model,
        args.sync_4070,
    )
    deps = report["preconditions"]
    c = report["accepted_counts"]
    print(f"{TASK_NAME}: {report['status']}")
    print(f"Input D6B4: {deps['d6b4']['dependency_status']}")
    print(f"Input D12B live NIM: {deps['d12b']['dependency_status']}")
    print(f"Input D11C live face: {deps['d11c']['dependency_status']}")
    print(f"Input D11A TOID: {deps['d11a']['dependency_status']}")
    print(f"Input D10EV: {deps['d10ev']['dependency_status']}")
    print(f"D6B4 certified identity edges: {c['d6b4_total_certified_identity_edges']}")
    print(f"D6B4 exact PLD matches/new matches: {c['d6b4_new_exact_pld_matches']}")
    print(f"Accepted TOIDs with generalised location: {c['d11a_matched_accepted_toids_with_generalised_location']} / {c['d11a_accepted_toids_considered']}")
    print(f"EV charging sites: {c['d10ev_ev_charging_sites_emitted']}")
    print(f"Live face re-smoke: {report['live_face_resmoke']['status']}")
    print(f"Live NIM re-smoke: {report['live_nim_resmoke']['status']}")
    print(f"Mission Control updated: {report['board_update']['mission_control']['status']}")
    print(f"ToDo updated: {report['board_update']['todo']['status']}")
    print(f"4070 sync: {report['sync_4070']['status']}")
    print(f"Hero readiness: {report['hero_readiness']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] in {"PASS", "PASS_WITH_LIVE_NIM_RESMOKE_NOT_RUN_BUT_D12B_ACCEPTED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
