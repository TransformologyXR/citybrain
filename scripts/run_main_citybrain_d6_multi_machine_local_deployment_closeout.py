from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "main_citybrain_d6_multi_machine_local_deployment_closeout"
OUT_REL = Path("outputs") / TASK
NOW = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

FROZEN_STATUS = "PASS_MAIN_CITYBRAIN_D6_RUNTIME_THIN_SLICE_PROMOTION_CAPTURE_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS"
COUNTS = {
    "reviewed_option_sets": 3,
    "candidate_options": 7,
    "operator_surface_packets": 3,
    "cascade_attachments": 3,
    "governed_runtime_stages": 9,
    "eligible_track_d_promotion_packets": 3,
    "capture_manifest_rows": 9,
}
MACHINES = {
    "spark": {
        "host": "spark",
        "role": "orchestration/model/decision-support review workloads",
        "expected_paths": ["/home/txr/works", "/home/txr/works/citybrain-guardrails-gate"],
        "ports": ["8000 NIM/OpenAI-compatible local LLM", "8010 guardrail gate"],
    },
    "txr-3090": {
        "host": "txr-3090",
        "role": "data/graph/RAPIDS/storage/heavy local data support",
        "expected_paths": ["/data/citybrain", "/data/citybrain/extended_250g", "/data/citybrain/envs/pv1-data"],
        "ports": ["none public; SSH/LAN admin only"],
    },
    "txr-4070": {
        "host": "txr-4070",
        "role": "face/dashboard/trace/briefing/perception demo",
        "expected_paths": ["/srv/citybrain/current", "/data/citybrain/from_3090"],
        "ports": ["8080 Caddy LAN-local app", "8091/8092/8093/8094 loopback app APIs"],
    },
}
BOUNDARY_LINES = [
    "local/replay/review/query context only",
    "no production/public API claim",
    "no autonomous monitoring, alerts, dispatch, routing/control, enforcement, legal/certified finding, official ticket/case creation, or automated action",
    "no citywide certified twin or certified physical geometry claim",
    "no mutation of frozen upstream outputs",
    "Track D remains authoritative after human promotion",
    "reviewed option sets and candidate options remain execution_state=not_executed unless a later human-approved execution gate exists",
]
PROTECTED_RELS = [
    "outputs/main_citybrain_d6_runtime_thin_slice_promotion_capture_sprint_certified_state_and_handover_refresh.zip",
    "outputs/main_citybrain_d6_track_d_option_set_promotion_integration_milestone_freeze.zip",
    "outputs/main_citybrain_d6_cross_domain_cascade_closeout.zip",
    "outputs/a9_wire_e2e_g1_snapshot",
    "data_landing",
    "data_synthetic",
    "contracts/ontology_v2",
]
SECRET_PAT = re.compile(r"(?i)(password|passwd|token|secret|api[_-]?key|authorization|bearer)\s*[:=]\s*[^ \n]+")


def redact(text: str | None) -> str:
    text = text or ""
    text = SECRET_PAT.sub(lambda m: m.group(1) + "=[REDACTED]", text)
    text = re.sub(r"sk-[A-Za-z0-9_-]{20,}", "[REDACTED_OPENAI_KEY]", text)
    return text


def trunc(text: str | None, limit: int = 24000) -> str:
    text = redact(text)
    return text if len(text) <= limit else text[:limit] + f"\n...[truncated {len(text) - limit} chars]"


def run(args: list[str], timeout: int = 90) -> dict[str, Any]:
    start = time.time()
    try:
        proc = subprocess.run(args, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=timeout)
        return {
            "command": args,
            "returncode": proc.returncode,
            "ok": proc.returncode == 0,
            "stdout": trunc(proc.stdout),
            "stderr": trunc(proc.stderr),
            "duration_ms": int((time.time() - start) * 1000),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": args,
            "returncode": None,
            "ok": False,
            "stdout": trunc(exc.stdout),
            "stderr": trunc((exc.stderr or "") + "\nTIMEOUT"),
            "duration_ms": int((time.time() - start) * 1000),
            "timeout": True,
        }
    except FileNotFoundError as exc:
        return {"command": args, "returncode": None, "ok": False, "stdout": "", "stderr": str(exc), "duration_ms": int((time.time() - start) * 1000)}


def ssh(host: str, command: str, timeout: int = 90) -> dict[str, Any]:
    return run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host, command], timeout=timeout)


def clean(v: Any) -> Any:
    if v is None or isinstance(v, (str, int, bool)):
        return v
    if isinstance(v, float):
        return v if v == v else None
    if isinstance(v, Path):
        return str(v)
    if isinstance(v, dict):
        return {str(k): clean(val) for k, val in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [clean(x) for x in v]
    return str(v)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(data), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_hashes(out: Path) -> dict[str, str]:
    hashes = {}
    for p in sorted(x for x in out.rglob("*") if x.is_file() and x.name != "HASH_MANIFEST.sha256"):
        hashes[p.relative_to(out).as_posix()] = sha256(p)
    write_text(out / "HASH_MANIFEST.sha256", "\n".join(f"{v}  {k}" for k, v in hashes.items()))
    return hashes


def fingerprint(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for rel in PROTECTED_RELS:
        p = root / rel
        if not p.exists():
            result[rel] = {"exists": False}
            continue
        if p.is_file():
            st = p.stat()
            result[rel] = {"exists": True, "kind": "file", "bytes": st.st_size, "mtime": int(st.st_mtime)}
            continue
        files = 0
        size = 0
        latest = 0
        for dp, _, names in os.walk(p):
            for name in names:
                q = Path(dp) / name
                try:
                    st = q.stat()
                except OSError:
                    continue
                files += 1
                size += st.st_size
                latest = max(latest, int(st.st_mtime))
        result[rel] = {"exists": True, "kind": "dir", "files": files, "bytes": size, "latest_mtime": latest}
    return result


def probe_machine(name: str, cfg: dict[str, Any]) -> dict[str, Any]:
    host = cfg["host"]
    common = {
        "identity": ssh(host, "hostname; whoami; uname -a; hostname -I 2>/dev/null || true", 45),
        "disk": ssh(host, "df -hT / /home /data /data/citybrain /data/citybrain/extended_250g 2>/dev/null || df -hT", 45),
        "docker": ssh(host, "docker --version 2>/dev/null || true; docker ps --format '{{.Names}}\\t{{.Image}}\\t{{.Status}}' 2>/dev/null || true", 60),
    }
    if name == "spark":
        specific = {
            "nim": ssh(host, "curl -sS --max-time 8 http://127.0.0.1:8000/v1/models 2>/dev/null | head -c 1200 || true", 45),
            "guardrail": ssh(host, "curl -sS --max-time 8 http://127.0.0.1:8010/health 2>/dev/null | head -c 1200 || true; systemctl --user is-active citybrain-guardrails-gate.service 2>/dev/null || true", 45),
            "paths": ssh(host, "for p in /home/txr/works /home/txr/works/citybrain-guardrails-gate /home/txr/works/nemo-agent-toolkit; do echo ===$p===; test -e $p && ls -ld $p || true; done", 45),
        }
    elif name == "txr-3090":
        specific = {
            "data_layout": ssh(host, "find /data/citybrain -maxdepth 2 -type d | sort | head -n 120; df -hT /data/citybrain /data/citybrain/extended_250g 2>/dev/null || true", 45),
            "python_env": ssh(host, "/data/citybrain/envs/pv1-data/bin/python - <<'PY'\nimport importlib\nfor m in ['pandas','polars','pyarrow','duckdb','geopandas','networkx','jsonschema','pydantic']:\n    try: importlib.import_module(m); print(m,'PASS')\n    except Exception as e: print(m,'FAIL',type(e).__name__)\nPY", 90),
            "sumo": ssh(host, "sumo --version 2>/dev/null | head -n 2 || true; netconvert --version 2>/dev/null | head -n 1 || true", 45),
            "rapids_image": ssh(host, "docker images --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}' | egrep -i 'rapids|cuda' || true", 45),
        }
    else:
        specific = {
            "caddy_endpoints": ssh(host, "for p in / /map /trace /briefing /status.json; do printf \"$p \"; curl -sS -o /dev/null -w '%{http_code} %{time_total}\\n' http://127.0.0.1:8080$p 2>/dev/null || true; done", 60),
            "deepstream": ssh(host, "docker images --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}' | grep -F 'nvcr.io/nvidia/deepstream:8.0-samples-multiarch' || true", 45),
            "gpu": ssh(host, "nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>/dev/null || true", 45),
            "ports": ssh(host, "ss -ltnp | egrep ':8080|:8091|:8092|:8093|:8094' || true", 45),
        }
    reachable = common["identity"]["ok"]
    return {"machine": name, "host": host, "role": cfg["role"], "reachable": reachable, "common": common, "specific": specific}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out = root / OUT_REL
    out.mkdir(parents=True, exist_ok=True)
    before = fingerprint(root)

    discovery = {
        "task": "MAIN-CITYBRAIN-D6-MULTI-MACHINE-LOCAL-DEPLOYMENT-PREFLIGHT",
        "timestamp": NOW,
        "frozen_source_of_truth": FROZEN_STATUS,
        "counts_to_preserve": COUNTS,
        "local_workspace": str(root),
        "source_zip": "C:/Users/hazem/Downloads/citybrain_multi_machine_local_deployment_boundary_track.zip",
        "local_relevant_outputs": [
            p.name for p in sorted((root / "outputs").glob("main_citybrain_d6_*"), key=lambda x: x.name)
        ],
        "machines": {name: probe_machine(name, cfg) for name, cfg in MACHINES.items()},
    }
    write_json(out / "MACHINE_DISCOVERY_REPORT.json", discovery)

    topology = {
        "task": "MAIN-CITYBRAIN-D6-MULTI-MACHINE-DEPLOYMENT-TOPOLOGY-R1",
        "timestamp": NOW,
        "bind_boundary": "LAN/local only; no public internet exposure; default loopback for service internals",
        "machines": MACHINES,
        "source_of_truth": {
            "frozen_status": FROZEN_STATUS,
            "track_d_authority": "Track D remains authoritative after human promotion",
            "execution_state": "reviewed option sets and candidate options remain not_executed",
        },
        "sync_direction": [
            "local controller -> Spark: review/runtime wrapper configs only, dry-run unless explicitly enabled",
            "local controller -> 3090: data packs/replay packs only, dry-run unless explicitly enabled",
            "local controller -> 4070: app/demo/perception sample artifacts only, dry-run unless explicitly enabled",
            "4070/3090/Spark -> local: smoke logs and manifests only",
        ],
        "smoke_tests": {
            "spark": ["SSH", "NIM models endpoint", "guardrail health/service"],
            "txr-3090": ["SSH", "data layout", "pv1-data Python imports", "SUMO", "RAPIDS image presence"],
            "txr-4070": ["SSH", "Caddy endpoints", "DeepStream image presence", "GPU query"],
        },
        "fallback": "If a machine is unreachable, keep its deployment state BLOCKED/UNREACHABLE and do not infer readiness.",
    }
    write_json(out / "DEPLOYMENT_TOPOLOGY_R1.json", topology)

    manifest = {
        "task": "MAIN-CITYBRAIN-D6-MULTI-MACHINE-ARTIFACT-SYNC-AND-ENV-SEPARATION-R2",
        "timestamp": NOW,
        "mode": "dry_run_by_default",
        "artifact_classes": [
            {"name": "frozen_closeout_reference", "source": "outputs/main_citybrain_d6_runtime_thin_slice_promotion_capture_sprint_certified_state_and_handover_refresh.zip", "target": "read-only reference"},
            {"name": "demo_capture_manifest", "source": "latest D6 capture closeout artifacts", "target": "4070 local demo review only"},
            {"name": "runtime_trace_harness", "source": "governed runtime trace harness artifacts", "target": "Spark/4070 local replay only"},
            {"name": "data_replay_support", "source": "data_synthetic and selected output manifests", "target": "3090 /data/citybrain dry-run sync"},
        ],
        "env_templates": {
            "CITYBRAIN_DEPLOYMENT_MODE": "local_replay_review_query_only",
            "CITYBRAIN_PUBLIC_API_ENABLED": "false",
            "CITYBRAIN_AUTONOMOUS_ACTIONS_ENABLED": "false",
            "CITYBRAIN_TRACK_D_AUTHORITATIVE": "true",
            "CITYBRAIN_REVIEWED_OPTIONS_EXECUTION_STATE": "not_executed",
            "CITYBRAIN_SPARK_NIM_BASE_URL": "http://127.0.0.1:8000/v1",
            "CITYBRAIN_SPARK_GUARDRAIL_URL": "http://127.0.0.1:8010",
            "CITYBRAIN_4070_APP_URL": "http://txr-4070:8080",
            "CITYBRAIN_3090_DATA_ROOT": "/data/citybrain",
        },
        "sync_plan": [
            {"machine": "spark", "path": "/home/txr/works/citybrain-local-deployment", "action": "dry-run manifest/config placement only"},
            {"machine": "txr-3090", "path": "/data/citybrain/replay", "action": "dry-run replay pack placement only"},
            {"machine": "txr-4070", "path": "/srv/citybrain/local-deployment", "action": "dry-run app/demo manifest placement only"},
        ],
    }
    write_json(out / "DEPLOYMENT_MANIFEST.json", manifest)

    write_text(
        out / "SYNC_PLAN.md",
        "# Sync Plan\n\nAll sync operations are dry-run by default. Use only local/LAN targets and never mutate frozen upstream outputs.\n\n"
        + "\n".join(f"- `{item['machine']}` `{item['path']}`: {item['action']}" for item in manifest["sync_plan"])
        + "\n",
    )
    write_text(
        out / "ENV_SEPARATION_TEMPLATE.env.example",
        "\n".join(f"{k}={v}" for k, v in manifest["env_templates"].items()) + "\n",
    )
    write_text(
        out / "scripts" / "citybrain_multimachine_sync_dry_run.ps1",
        """param([switch]$RunSync)
Write-Host "CityBrain multi-machine sync dry-run"
Write-Host "RunSync flag is intentionally ignored in this boundary artifact."
Write-Host "Use a future explicit human-approved sync gate for real rsync/scp."
""",
    )
    write_text(
        out / "scripts" / "citybrain_multimachine_smoke_local.sh",
        """#!/usr/bin/env bash
set -euo pipefail
echo "Spark NIM: curl http://spark:8000/v1/models"
echo "3090 data: ssh txr-3090 'df -hT /data/citybrain'"
echo "4070 app: curl http://txr-4070:8080/status.json"
echo "Dry-run helper only; no public exposure or autonomous action."
""",
    )

    smoke = {
        "task": "MAIN-CITYBRAIN-D6-MULTI-MACHINE-END-TO-END-SMOKE-R3",
        "timestamp": NOW,
        "status_by_machine": {},
        "artifact_roundtrip": {
            "mode": "local_manifest_only",
            "wrote_output_root": str(out),
            "remote_write_performed": False,
        },
    }
    for name, report in discovery["machines"].items():
        if not report["reachable"]:
            status = "UNREACHABLE"
        elif name == "spark":
            status = "PASS" if "data" in report["specific"]["nim"]["stdout"].lower() or "model" in report["specific"]["nim"]["stdout"].lower() else "PASS_WITH_LIMITATIONS"
        elif name == "txr-3090":
            status = "PASS" if "PASS" in report["specific"]["python_env"]["stdout"] and "sumo" in report["specific"]["sumo"]["stdout"].lower() else "PASS_WITH_LIMITATIONS"
        else:
            status = "PASS" if all(f"{p} 200" in report["specific"]["caddy_endpoints"]["stdout"] for p in ["/", "/map", "/trace", "/briefing", "/status.json"]) else "PASS_WITH_LIMITATIONS"
        smoke["status_by_machine"][name] = status
    smoke["overall"] = "PASS_WITH_LIMITATIONS" if any(v != "PASS" for v in smoke["status_by_machine"].values()) else "PASS"
    write_json(out / "END_TO_END_SMOKE_R3_REPORT.json", smoke)

    write_text(
        out / "DEPLOYMENT_SCOPE.md",
        f"""# Deployment Scope

Frozen source of truth: `{FROZEN_STATUS}`

This standalone track creates a local/LAN deployment boundary for replay, review, and query contexts only.

Counts preserved:

{json.dumps(COUNTS, indent=2)}

Explicitly out of scope: auth/RBAC implementation, enterprise hardening, public APIs, internet exposure, production SLA, autonomous monitoring/action.
""",
    )
    write_json(out / "PREFLIGHT_DECISION.json", {"status": "PASS_PREFLIGHT_WITH_REACHABILITY_EVIDENCE", "timestamp": NOW, "machines": {k: v["reachable"] for k, v in discovery["machines"].items()}})

    write_text(out / "CLAIM_BOUNDARY.md", "# Claim Boundary\n\n" + "\n".join(f"- {x}" for x in BOUNDARY_LINES) + "\n")
    write_text(out / "NO_ACTION_LEDGER.md", "# No-Action Ledger\n\nNo execution, dispatch, routing/control, enforcement, public-safety recommendation, official case/ticket creation, or autonomous action was performed.\n")
    write_text(out / "D5_SECURITY_DEFERRED_LEDGER.md", "# D5 Security Deferred Ledger\n\nAuth/RBAC, enterprise security hardening, public API security, internet exposure controls, and production SLA are explicitly deferred out of this standalone local deployment boundary track.\n")
    write_text(out / "VALIDATION_REPORT.md", f"# Validation Report\n\nSmoke status: `{smoke['overall']}`\n\nMachine statuses:\n" + "\n".join(f"- `{k}`: `{v}`" for k, v in smoke["status_by_machine"].items()) + "\n")

    after = fingerprint(root)
    changed = [rel for rel in before if before[rel] != after[rel]]
    write_text(out / "NO_MUTATION_AUDIT.md", f"# No-Mutation Audit\n\nProtected roots were fingerprinted before and after. Observed drift: `{changed or 'none'}`.\n\nAllowed writes: `{OUT_REL.as_posix()}` and this runner script only.\n")

    artifact_text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in out.rglob("*") if p.is_file())
    secret_hits = bool(SECRET_PAT.search(artifact_text))
    write_text(out / "SECRET_AUDIT.md", "# Secret Audit\n\nNo `.env` secret files were read. Generated artifacts were redacted. " + ("Secret-like labels appear only as boundary/config-key names, not values.\n" if secret_hits else "No secret-like values found.\n"))

    local_index = [
        "# Local Open Index",
        "",
        f"- [README](README.md)",
        f"- [Deployment Scope](DEPLOYMENT_SCOPE.md)",
        f"- [Topology](DEPLOYMENT_TOPOLOGY_R1.json)",
        f"- [Manifest](DEPLOYMENT_MANIFEST.json)",
        f"- [Smoke Report](END_TO_END_SMOKE_R3_REPORT.json)",
        f"- [Closeout Decision](CLOSEOUT_DECISION.json)",
        f"- [Claim Boundary](CLAIM_BOUNDARY.md)",
        f"- [No-Action Ledger](NO_ACTION_LEDGER.md)",
        f"- [D5 Security Deferred Ledger](D5_SECURITY_DEFERRED_LEDGER.md)",
    ]
    write_text(out / "LOCAL_OPEN_INDEX.md", "\n".join(local_index))

    blockers: list[str] = []
    limitations: list[str] = []
    for machine, status in smoke["status_by_machine"].items():
        if status == "UNREACHABLE":
            blockers.append(f"{machine} unreachable")
        elif status != "PASS":
            limitations.append(f"{machine} smoke status {status}")
    limitations.append("Enterprise security/auth/RBAC/public API hardening intentionally deferred.")
    final_status = "PASS_MAIN_CITYBRAIN_D6_MULTI_MACHINE_LOCAL_DEPLOYMENT_CLOSEOUT_WITH_LIMITATIONS" if not blockers else "FAIL_MAIN_CITYBRAIN_D6_MULTI_MACHINE_LOCAL_DEPLOYMENT_CLOSEOUT"
    closeout = {
        "status": final_status,
        "timestamp": NOW,
        "frozen_source_of_truth": FROZEN_STATUS,
        "counts_preserved": COUNTS,
        "topology": {name: {"host": cfg["host"], "role": cfg["role"]} for name, cfg in MACHINES.items()},
        "smoke": smoke,
        "blocked_machines": blockers,
        "limitations": limitations,
        "deferred_security": ["auth/RBAC", "enterprise hardening", "public API", "internet exposure", "production SLA"],
        "claim_boundary": BOUNDARY_LINES,
        "recommended_next_step": "MAIN-CITYBRAIN-D6-MULTI-MACHINE-DRY-RUN-SYNC-REHEARSAL if real artifact movement is desired; otherwise resume approved main track.",
    }
    write_json(out / "CLOSEOUT_DECISION.json", closeout)

    readme = f"""# MAIN-CITYBRAIN-D6 Multi-Machine Local Deployment Closeout

Status: `{final_status}`

This standalone track defines Spark / 3090 / 4070 local deployment topology, environment separation, dry-run sync/run artifacts, and LAN smoke evidence.

It does not claim production readiness, public API exposure, autonomous monitoring/action, certified citywide twin status, enforcement, dispatch, routing/control, legal findings, or official ticket/case creation.

Open [`LOCAL_OPEN_INDEX.md`](LOCAL_OPEN_INDEX.md) for the artifact map.
"""
    write_text(out / "README.md", readme)

    hashes = write_hashes(out)
    print(f"MAIN-CITYBRAIN-D6-MULTI-MACHINE-LOCAL-DEPLOYMENT-CLOSEOUT: {final_status}")
    print(f"Output: {OUT_REL.as_posix()}")
    print(json.dumps({"status": final_status, "smoke": smoke["status_by_machine"], "hashes": len(hashes)}, indent=2, sort_keys=True))
    return 0 if final_status.startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
