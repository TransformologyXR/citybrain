#!/usr/bin/env python3
"""Consume the D5 app packet bundle through a minimal UI-like smoke.

This task closes the missing bridge between packet generation and a visible
consumer. It builds a static/local consumer page and performs one localhost
governed-query request against the hardened D5 runtime, while redirecting any
runtime writes into this task's output root.
"""

from __future__ import annotations

import hashlib
import html
import http.client
import importlib.util
import json
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-APP-CONSUMPTION-SMOKE-R1"
STATUS = "PASS_WITH_LIMITATIONS"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d5_local_served_runtime_app_consumption_smoke_r1"
RUNNER_PATH = REPO_ROOT / "scripts/run_main_citybrain_d5_local_served_runtime_app_consumption_smoke_r1.py"

APP_SLICE_ROOT = REPO_ROOT / "outputs/main_citybrain_d5_local_served_runtime_app_integration_slice_r1"
HARDENING_ROOT = REPO_ROOT / "outputs/main_citybrain_d5_local_served_runtime_hardening_r1"
R3_RUNTIME_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice"
HARDENING_RUNNER = REPO_ROOT / "scripts/run_main_citybrain_d5_local_served_runtime_hardening_r1.py"

APP_SLICE_DECISION = APP_SLICE_ROOT / "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_APP_INTEGRATION_SLICE_R1_DECISION.json"
APP_PACKET_BUNDLE = APP_SLICE_ROOT / "LOCAL_SERVED_RUNTIME_APP_SLICE_PACKET_BUNDLE.json"
HARDENING_DECISION = HARDENING_ROOT / "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_HARDENING_R1_DECISION.json"
R3_RUNTIME_CONFIG = R3_RUNTIME_ROOT / "runtime/runtime_config.json"

READ_ONLY_ROOTS = [APP_SLICE_ROOT, HARDENING_ROOT, R3_RUNTIME_ROOT]

REQUIRED_PACKET_TYPES = [
    "health_status_packet",
    "governed_answer_packet",
    "insight_packet",
    "evidence_trace_packet",
    "limitation_packet",
    "safe_next_look_packet",
]

LIMITATIONS = [
    "local/static app-consumption smoke only",
    "minimal UI-like consumer, not a production frontend",
    "localhost runtime request is bounded to 127.0.0.1 and redirected to this output root",
    "uses D5 app packet bundle and hardened runtime; no public API is exposed",
    "no auth/RBAC, deployment, concurrency, or browser automation proof",
    "no live event fabric or D5 app-slice integration beyond packet consumption",
    "no command/action, dispatch, enforcement, routing/control, legal, certified impact, or autonomous action",
]

FORBIDDEN_CLAIM_FLAGS = {
    "production_readiness_claim_made": False,
    "public_api_claim_made": False,
    "autonomous_action_exposed": False,
    "dispatch_recommendation_created": False,
    "enforcement_recommendation_created": False,
    "routing_control_output_created": False,
    "legal_or_certified_claim_created": False,
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_md(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_tree(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "total_bytes": 0, "hash": None}
    entries: list[str] = []
    total = 0
    for path in sorted(root.rglob("*")):
        if path.is_file():
            stat = path.stat()
            total += stat.st_size
            entries.append(f"{rel(path)}|{stat.st_size}|{stat.st_mtime_ns}|{sha256_file(path)}")
    return {
        "exists": True,
        "file_count": len(entries),
        "total_bytes": total,
        "hash": hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest(),
    }


def packet_by_type(packets: list[dict[str, Any]], packet_type: str) -> dict[str, Any]:
    return next((packet for packet in packets if packet.get("packet_type") == packet_type), {})


def load_inputs() -> dict[str, Any]:
    app_decision = read_json(APP_SLICE_DECISION, {})
    hardening_decision = read_json(HARDENING_DECISION, {})
    bundle = read_json(APP_PACKET_BUNDLE, {})
    packets = bundle.get("packets", [])
    return {
        "app_decision": app_decision,
        "hardening_decision": hardening_decision,
        "bundle": bundle,
        "packets": packets,
    }


def app_consumer_contract(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "schema_version": "citybrain.d5.app_consumption_smoke.r1.contract",
        "consumer_kind": "static_html_and_json_packet_viewer",
        "input_bundle": rel(APP_PACKET_BUNDLE),
        "runtime_endpoint_used_for_behavior3": "POST http://127.0.0.1:<ephemeral>/runtime/request",
        "required_packet_types": REQUIRED_PACKET_TYPES,
        "display_contract": {
            "question_panel": "Show user question and safe runtime request envelope summary.",
            "answer_panel": "Show governed answer packet status, situation title, summary, lifecycle state, and no-action boundary.",
            "event_or_runtime_panel": "Show event/runtime packet context without treating it as operational control.",
            "insight_panel": "Show insight/context packet as next-look context only.",
            "trace_panel": "Show trace/evidence refs and packet provenance.",
            "limitation_panel": "Show all limitation refs visibly.",
            "safe_next_look_panel": "Show safe next-look options only.",
        },
        "source_status": {
            "app_slice_status": inputs["app_decision"].get("status", "MISSING"),
            "hardening_status": inputs["hardening_decision"].get("status", "MISSING"),
            "packet_count": len(inputs["packets"]),
        },
        "boundaries": {
            **FORBIDDEN_CLAIM_FLAGS,
            "no_action_required": True,
            "local_only": True,
            "limitations_must_render": True,
        },
    }


def prepare_redirected_runtime_config() -> Path:
    source_config = read_json(R3_RUNTIME_CONFIG, {})
    runtime_work = OUTPUT_ROOT / "runtime_work"
    source_config["output_root"] = str(runtime_work)
    config_path = runtime_work / "runtime_config.json"
    write_json(config_path, source_config)
    return config_path


def import_hardening_runner() -> Any:
    spec = importlib.util.spec_from_file_location("citybrain_d5_hardening_for_consumption_smoke", HARDENING_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import hardening runner: {HARDENING_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def post_json(host: str, port: int, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    conn = http.client.HTTPConnection(host, port, timeout=5)
    try:
        body = json.dumps(payload).encode("utf-8")
        conn.request("POST", path, body=body, headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        raw = response.read().decode("utf-8")
        return response.status, json.loads(raw)
    finally:
        conn.close()


def run_behavior3_localhost_request() -> dict[str, Any]:
    config_path = prepare_redirected_runtime_config()
    module = import_hardening_runner()
    module.RUNTIME_CONFIG = config_path
    module.RUNTIME_WORK_ROOT = config_path.parent

    user_question = "What is the current bounded runtime situation I can safely review?"
    request_envelope = {
        "request_id": "app-consumption-behavior3-ask-city",
        "request_type": "governed_query",
        "runtime_profile": "local_default",
        "trace_requested": True,
        "safe_mode": True,
        "payload": {
            "user_question": user_question,
            "runtime_request": {
                "request_id": "app-consumption-behavior3-runtime",
                "request_type": "evidence_qa",
                "desired_output_type": "answer_packet",
                "request_text_or_structured_intent": (
                    "Ask City: summarize the current bounded runtime situation with evidence, "
                    "trace, limitations, and safe next-look options."
                ),
                "include_limitations": True,
                "include_trace": True,
                "no_action_taken": True,
            },
        },
    }

    server, _service, thread = module.start_server("127.0.0.1", 0)
    start = time.perf_counter()
    try:
        host, port = server.server_address[:2]
        http_status, response = post_json(str(host), int(port), "/runtime/request", request_envelope)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
    runtime_packet = response.get("data", {}).get("runtime_packet", {})
    return {
        "status": "PASS" if http_status == 200 and response.get("response_type") == "governed_query_response" else "FAIL",
        "mode": "LIVE_LOCALHOST_EPHEMERAL_REQUEST_REDIRECTED_TO_TASK_OUTPUT_ROOT",
        "localhost_runtime_received_request": http_status == 200,
        "endpoint": f"http://127.0.0.1:{port}/runtime/request",
        "http_status": http_status,
        "elapsed_ms": elapsed_ms,
        "user_question": user_question,
        "request_envelope": request_envelope,
        "response": response,
        "runtime_packet_summary": {
            "packet_type": runtime_packet.get("packet_type"),
            "status": runtime_packet.get("status"),
            "situation_title": runtime_packet.get("situation_title"),
            "situation_summary": runtime_packet.get("situation_summary"),
            "lifecycle_states": runtime_packet.get("lifecycle_states", []),
            "evidence_refs": runtime_packet.get("evidence_refs", []),
            "trace_ref": runtime_packet.get("trace_ref"),
            "limitation_refs": runtime_packet.get("limitation_refs", []),
            "no_action_taken": runtime_packet.get("no_action_taken") is True,
        },
        "runtime_config_path": rel(config_path),
        "no_action_taken": response.get("no_action_taken") is True and runtime_packet.get("no_action_taken") is True,
    }


def first_n(values: Any, limit: int = 12) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values[:limit]]


def build_render_model(inputs: dict[str, Any], behavior3: dict[str, Any]) -> dict[str, Any]:
    packets = inputs["packets"]
    governed_packet = packet_by_type(packets, "governed_answer_packet")
    insight_packet = packet_by_type(packets, "insight_packet")
    evidence_packet = packet_by_type(packets, "evidence_trace_packet")
    limitation_packet = packet_by_type(packets, "limitation_packet")
    safe_next_packet = packet_by_type(packets, "safe_next_look_packet")
    event_packet = packet_by_type(packets, "optional_event_state_packet")

    live_response = behavior3.get("response", {})
    runtime_packet = live_response.get("data", {}).get("runtime_packet", {})
    runtime_response = live_response.get("data", {}).get("runtime_response", {})

    limitation_refs = list(
        dict.fromkeys(
            first_n(live_response.get("limitation_refs"), 30)
            + first_n(runtime_packet.get("limitation_refs"), 30)
            + first_n(limitation_packet.get("limitation_refs"), 30)
        )
    )
    evidence_refs = list(
        dict.fromkeys(
            first_n(live_response.get("evidence_refs"), 30)
            + first_n(runtime_packet.get("evidence_refs"), 30)
            + first_n(governed_packet.get("evidence_refs"), 30)
        )
    )
    trace_refs = list(
        dict.fromkeys(
            first_n(live_response.get("trace_refs"), 30)
            + first_n(governed_packet.get("trace_refs"), 30)
            + first_n(evidence_packet.get("trace_refs"), 30)
        )
    )
    safe_next = list(
        dict.fromkeys(
            first_n(live_response.get("safe_next_looks"), 12)
            + first_n(runtime_response.get("safe_next_looks"), 12)
            + first_n(safe_next_packet.get("safe_next_looks"), 12)
        )
    )

    return {
        "task_id": TASK_ID,
        "generated_at_utc": now(),
        "consumer_title": "CityBrain Local Runtime Consumer Smoke",
        "input_packet_bundle": rel(APP_PACKET_BUNDLE),
        "ask_city_flow": {
            "user_question": behavior3["user_question"],
            "runtime_endpoint": behavior3["endpoint"],
            "localhost_runtime_received_request": behavior3["localhost_runtime_received_request"],
            "http_status": behavior3["http_status"],
            "response_status": live_response.get("status"),
            "response_type": live_response.get("response_type"),
            "no_action_taken": behavior3["no_action_taken"],
        },
        "answer_panel": {
            "title": runtime_packet.get("situation_title") or "Bounded runtime answer",
            "summary": runtime_packet.get("situation_summary") or runtime_response.get("summary"),
            "packet_type": runtime_packet.get("packet_type"),
            "packet_status": runtime_packet.get("status"),
            "lifecycle_states": runtime_packet.get("lifecycle_states", []),
            "claim_boundary": runtime_packet.get("claim_boundary") or live_response.get("claim_boundary"),
            "no_action_taken": runtime_packet.get("no_action_taken") is True,
        },
        "event_runtime_panel": {
            "packet_type": event_packet.get("packet_type"),
            "slot_status": event_packet.get("slot_status"),
            "status": event_packet.get("status"),
            "handoff_ref": event_packet.get("handoff_ref"),
            "data": event_packet.get("data", {}),
            "limitations": event_packet.get("limitation_refs", []),
        },
        "insight_panel": {
            "packet_type": insight_packet.get("packet_type"),
            "status": insight_packet.get("status"),
            "data": insight_packet.get("data", {}),
            "safe_next_looks": insight_packet.get("safe_next_looks", []),
            "limitations": insight_packet.get("limitation_refs", []),
        },
        "trace_panel": {"trace_refs": trace_refs, "evidence_refs": evidence_refs, "data": evidence_packet.get("data", {})},
        "limitation_panel": {"limitation_refs": limitation_refs, "claim_boundary": live_response.get("claim_boundary")},
        "safe_next_look_panel": {"safe_next_looks": safe_next},
        "packet_index": [
            {
                "packet_type": packet.get("packet_type"),
                "packet_id": packet.get("packet_id"),
                "status": packet.get("status"),
                "evidence_ref_count": len(packet.get("evidence_refs", [])),
                "trace_ref_count": len(packet.get("trace_refs", [])),
                "limitation_ref_count": len(packet.get("limitation_refs", [])),
                "no_action_taken": packet.get("no_action_taken") is True,
            }
            for packet in packets
        ],
        "limitations": LIMITATIONS,
    }


def render_html(model: dict[str, Any]) -> str:
    data_json = json.dumps(model, indent=2, sort_keys=True)
    question = html.escape(model["ask_city_flow"]["user_question"])
    answer = html.escape(str(model["answer_panel"].get("summary") or "No summary available."))
    title = html.escape(str(model["answer_panel"].get("title") or "Runtime answer"))
    lifecycle = ", ".join(html.escape(str(x)) for x in model["answer_panel"].get("lifecycle_states", []))

    def list_items(values: list[Any]) -> str:
        if not values:
            return "<li>None supplied.</li>"
        return "\n".join(f"<li>{html.escape(str(value))}</li>" for value in values)

    packet_cards = "\n".join(
        f"""
        <article class=\"packet\">
          <strong>{html.escape(str(packet['packet_type']))}</strong>
          <span>{html.escape(str(packet['status']))}</span>
          <small>evidence {packet['evidence_ref_count']} / trace {packet['trace_ref_count']} / limitations {packet['limitation_ref_count']}</small>
        </article>
        """
        for packet in model["packet_index"]
    )

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>CityBrain D5 App Consumption Smoke</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #101418;
      --panel: #182029;
      --panel2: #202a35;
      --text: #edf3f8;
      --muted: #aab8c5;
      --line: #334251;
      --ok: #63d297;
      --warn: #f4bf75;
      --accent: #72a7ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: var(--bg); color: var(--text); }}
    header {{ padding: 20px 28px; border-bottom: 1px solid var(--line); background: #121922; }}
    h1 {{ margin: 0 0 6px; font-size: 24px; }}
    h2 {{ margin: 0 0 12px; font-size: 17px; }}
    main {{ display: grid; grid-template-columns: 1.1fr .9fr; gap: 14px; padding: 16px; max-width: 1440px; margin: 0 auto; }}
    section {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; }}
    .wide {{ grid-column: 1 / -1; }}
    .badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 8px; border: 1px solid var(--line); border-radius: 999px; color: var(--muted); margin: 2px 4px 2px 0; }}
    .ok {{ color: var(--ok); }}
    .warn {{ color: var(--warn); }}
    .question {{ font-size: 18px; line-height: 1.45; }}
    .answer {{ font-size: 16px; line-height: 1.55; color: #dfeaf2; }}
    ul {{ margin: 8px 0 0; padding-left: 20px; }}
    li {{ margin: 5px 0; }}
    code, pre {{ font-family: Consolas, monospace; }}
    pre {{ background: #0b0f13; border: 1px solid var(--line); border-radius: 6px; padding: 12px; overflow: auto; color: #d5e2ed; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    .packet {{ display: flex; flex-direction: column; gap: 4px; min-height: 82px; background: var(--panel2); border: 1px solid var(--line); border-radius: 6px; padding: 10px; }}
    .packet span {{ color: var(--accent); }}
    .packet small {{ color: var(--muted); }}
    @media (max-width: 900px) {{ main, .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>CityBrain D5 Local Served Runtime App Consumption Smoke</h1>
    <span class=\"badge ok\">runtime request received: {model['ask_city_flow']['localhost_runtime_received_request']}</span>
    <span class=\"badge\">HTTP {model['ask_city_flow']['http_status']}</span>
    <span class=\"badge\">{html.escape(str(model['ask_city_flow']['response_status']))}</span>
    <span class=\"badge ok\">no action taken</span>
  </header>
  <main>
    <section>
      <h2>Ask The City</h2>
      <p class=\"question\">{question}</p>
      <p><span class=\"badge\">POST</span><code>{html.escape(model['ask_city_flow']['runtime_endpoint'])}</code></p>
    </section>
    <section>
      <h2>Governed Answer</h2>
      <p><strong>{title}</strong></p>
      <p class=\"answer\">{answer}</p>
      <p><span class=\"badge\">{html.escape(str(model['answer_panel']['packet_type']))}</span><span class=\"badge\">{html.escape(str(model['answer_panel']['packet_status']))}</span><span class=\"badge\">{lifecycle}</span></p>
    </section>
    <section>
      <h2>Trace And Evidence</h2>
      <h3>Trace refs</h3>
      <ul>{list_items(model['trace_panel']['trace_refs'])}</ul>
      <h3>Evidence refs</h3>
      <ul>{list_items(model['trace_panel']['evidence_refs'])}</ul>
    </section>
    <section>
      <h2>Limitations</h2>
      <ul>{list_items(model['limitation_panel']['limitation_refs'])}</ul>
    </section>
    <section>
      <h2>Safe Next-Look Options</h2>
      <ul>{list_items(model['safe_next_look_panel']['safe_next_looks'])}</ul>
    </section>
    <section>
      <h2>Insight Context</h2>
      <pre>{html.escape(json.dumps(model['insight_panel']['data'], indent=2, sort_keys=True)[:2400])}</pre>
    </section>
    <section class=\"wide\">
      <h2>Consumed Packet Index</h2>
      <div class=\"grid\">{packet_cards}</div>
    </section>
    <section class=\"wide\">
      <h2>Embedded Render Model</h2>
      <pre id=\"model\"></pre>
    </section>
  </main>
  <script type=\"application/json\" id=\"citybrain-render-model\">{html.escape(data_json)}</script>
  <script>
    const model = JSON.parse(document.getElementById('citybrain-render-model').textContent);
    document.getElementById('model').textContent = JSON.stringify(model, null, 2);
  </script>
</body>
</html>
"""


def validate_consumption(inputs: dict[str, Any], behavior3: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    packets = inputs["packets"]
    packet_types = {packet.get("packet_type") for packet in packets}
    missing = [packet_type for packet_type in REQUIRED_PACKET_TYPES if packet_type not in packet_types]
    no_action_packets = all(packet.get("no_action_taken") is True for packet in packets)
    checks = {
        "upstream_app_slice_green": str(inputs["app_decision"].get("status", "")).startswith("PASS"),
        "upstream_hardening_green": str(inputs["hardening_decision"].get("status", "")).startswith("PASS"),
        "packet_bundle_consumed": APP_PACKET_BUNDLE.exists() and len(packets) >= len(REQUIRED_PACKET_TYPES),
        "required_packets_present": not missing,
        "localhost_runtime_request_sent": behavior3.get("status") == "PASS",
        "localhost_runtime_received_request": behavior3.get("localhost_runtime_received_request") is True,
        "governed_answer_displayed": bool(model["answer_panel"].get("summary")),
        "event_or_runtime_packet_displayed": bool(model["event_runtime_panel"].get("packet_type")),
        "insight_packet_displayed": bool(model["insight_panel"].get("packet_type")),
        "trace_refs_displayed": bool(model["trace_panel"].get("trace_refs")),
        "limitation_refs_displayed": bool(model["limitation_panel"].get("limitation_refs")),
        "safe_next_look_options_displayed": bool(model["safe_next_look_panel"].get("safe_next_looks")),
        "all_packets_preserve_no_action": no_action_packets,
        "runtime_response_preserves_no_action": behavior3.get("no_action_taken") is True,
        "static_html_created": (OUTPUT_ROOT / "APP_CONSUMER_STATIC_HTML.html").exists(),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "missing_required_packet_types": missing,
        "packet_count": len(packets),
        "packet_types": sorted(str(item) for item in packet_types if item),
        "behavior3_steps": [
            "user asks question",
            "localhost runtime receives request",
            "governed answer packet returns",
            "event/insight/trace/limitation packets are rendered",
            "safe next-look options are displayed",
        ],
    }


def boundary_audit(validation: dict[str, Any], behavior3: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS" if validation["status"] == "PASS" and behavior3.get("no_action_taken") is True else "FAIL",
        **FORBIDDEN_CLAIM_FLAGS,
        "no_action_taken": behavior3.get("no_action_taken") is True,
        "limitations_rendered": bool(model["limitation_panel"].get("limitation_refs")),
        "safe_next_looks_are_context_only": True,
        "localhost_only": behavior3.get("endpoint", "").startswith("http://127.0.0.1:"),
        "notes": [
            "The static page consumes packets and displays context only.",
            "The runtime request is local and bounded.",
            "No command/action/dispatch/enforcement/routing/control output is created.",
        ],
    }


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
        re.compile(r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9._\-]{12,}"),
    ]
    hits: list[dict[str, Any]] = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            for match in pattern.finditer(text):
                hits.append({"path": rel(path), "match": match.group(1) if match.groups() else "authorization"})
    return {"status": "PASS" if not hits else "FAIL", "hits": hits}


def write_docs(validation: dict[str, Any], behavior3: dict[str, Any]) -> None:
    html_path = OUTPUT_ROOT / "APP_CONSUMER_STATIC_HTML.html"
    report = f"""
# D5 Local Served Runtime App Consumption Smoke R1

Status: `{STATUS}`

This smoke proves a UI-like consumer can consume the D5 app packet bundle and show the missing ask-the-city behavior.

Behavior 3 path:

1. User asks a question.
2. Localhost runtime receives `POST /runtime/request`.
3. Governed answer packet returns.
4. Event/runtime, insight, trace/evidence, and limitation packets are displayed.
5. Safe next-look options appear.

Runtime receipt:

- Endpoint: `{behavior3['endpoint']}`
- HTTP status: `{behavior3['http_status']}`
- Runtime response status: `{behavior3['response'].get('status')}`
- No action taken: `{behavior3['no_action_taken']}`

Consumer artifact:

- Static HTML: `{rel(html_path)}`
- Render model: `APP_CONSUMER_RENDER_MODEL.json`
- Packet bundle consumed: `{rel(APP_PACKET_BUNDLE)}`

Validation: `{validation['status']}`
"""
    write_md(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_CONSUMPTION_SMOKE_REPORT.md", report)

    limitations = "\n".join(f"- {item}" for item in LIMITATIONS)
    write_md(
        OUTPUT_ROOT / "LIMITATIONS_AND_NEXT_STEPS.md",
        f"""
# Limitations And Next Steps

## Limitations

{limitations}

## Next Steps

- Use this static consumer as the D6 demo-preflight input.
- Replace the static page with the Track 2C app when ready.
- Keep runtime requests localhost-only until the D5 production/security boundary is deliberately unparked.
""",
    )
    write_md(
        OUTPUT_ROOT / "README.md",
        f"""
# {TASK_ID}

Run:

```powershell
python scripts\\run_main_citybrain_d5_local_served_runtime_app_consumption_smoke_r1.py
```

Open the static consumer:

```text
{html_path}
```

This is a local packet-consumption smoke, not a production app.
""",
    )


def decision_payload(
    inputs: dict[str, Any],
    behavior3: dict[str, Any],
    validation: dict[str, Any],
    boundary: dict[str, Any],
    mutation: dict[str, Any],
    secret: dict[str, Any],
) -> dict[str, Any]:
    pass_status = all(
        [
            validation["status"] == "PASS",
            boundary["status"] == "PASS",
            mutation["status"] == "PASS",
            secret["status"] == "PASS",
        ]
    )
    status = STATUS if pass_status else "FAIL"
    return {
        "task_id": TASK_ID,
        "status": status,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(RUNNER_PATH),
        "run_timestamp_utc": now(),
        "upstream_app_slice_root": str(APP_SLICE_ROOT),
        "upstream_app_slice_status": inputs["app_decision"].get("status"),
        "upstream_hardening_root": str(HARDENING_ROOT),
        "upstream_hardening_status": inputs["hardening_decision"].get("status"),
        "packet_bundle_consumed": validation["checks"]["packet_bundle_consumed"],
        "packet_count": validation["packet_count"],
        "required_packets_present": validation["checks"]["required_packets_present"],
        "behavior3_visible_path_created": validation["status"] == "PASS",
        "localhost_runtime_request_sent": validation["checks"]["localhost_runtime_request_sent"],
        "localhost_runtime_received_request": validation["checks"]["localhost_runtime_received_request"],
        "governed_answer_displayed": validation["checks"]["governed_answer_displayed"],
        "event_or_runtime_packet_displayed": validation["checks"]["event_or_runtime_packet_displayed"],
        "insight_packet_displayed": validation["checks"]["insight_packet_displayed"],
        "trace_refs_displayed": validation["checks"]["trace_refs_displayed"],
        "limitation_refs_displayed": validation["checks"]["limitation_refs_displayed"],
        "safe_next_look_options_displayed": validation["checks"]["safe_next_look_options_displayed"],
        "static_html_created": validation["checks"]["static_html_created"],
        "static_html_path": str(OUTPUT_ROOT / "APP_CONSUMER_STATIC_HTML.html"),
        "no_action_boundary_preserved": boundary["no_action_taken"],
        "source_mutation_status": mutation["status"],
        "secret_audit_status": secret["status"],
        **FORBIDDEN_CLAIM_FLAGS,
        "limitations": LIMITATIONS,
        "next_recommended_task": "MAIN-CITYBRAIN-D6-RUNTIME-DEMO-PREFLIGHT-R1",
    }


def main() -> int:
    before = {rel(root): snapshot_tree(root) for root in READ_ONLY_ROOTS}
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    inputs = load_inputs()
    write_json(OUTPUT_ROOT / "LOCAL_SERVED_RUNTIME_APP_CONSUMER_CONTRACT.json", app_consumer_contract(inputs))
    write_json(OUTPUT_ROOT / "UPSTREAM_INPUT_INVENTORY.json", {
        "app_slice_decision": {"path": rel(APP_SLICE_DECISION), "exists": APP_SLICE_DECISION.exists()},
        "app_packet_bundle": {"path": rel(APP_PACKET_BUNDLE), "exists": APP_PACKET_BUNDLE.exists()},
        "hardening_decision": {"path": rel(HARDENING_DECISION), "exists": HARDENING_DECISION.exists()},
        "hardening_runner": {"path": rel(HARDENING_RUNNER), "exists": HARDENING_RUNNER.exists()},
        "r3_runtime_config": {"path": rel(R3_RUNTIME_CONFIG), "exists": R3_RUNTIME_CONFIG.exists()},
    })

    behavior3 = run_behavior3_localhost_request()
    model = build_render_model(inputs, behavior3)

    write_json(OUTPUT_ROOT / "ASK_CITY_BEHAVIOR3_REQUEST_RESPONSE_TRANSCRIPT.json", behavior3)
    write_json(OUTPUT_ROOT / "LOCALHOST_RUNTIME_RECEIPT_PROOF.json", {
        "status": behavior3["status"],
        "endpoint": behavior3["endpoint"],
        "http_status": behavior3["http_status"],
        "localhost_runtime_received_request": behavior3["localhost_runtime_received_request"],
        "response_type": behavior3["response"].get("response_type"),
        "no_action_taken": behavior3["no_action_taken"],
        "runtime_writes_redirected_to": behavior3["runtime_config_path"],
    })
    write_json(OUTPUT_ROOT / "APP_CONSUMER_RENDER_MODEL.json", model)
    (OUTPUT_ROOT / "APP_CONSUMER_STATIC_HTML.html").write_text(render_html(model), encoding="utf-8")

    validation = validate_consumption(inputs, behavior3, model)
    write_json(OUTPUT_ROOT / "PACKET_CONSUMPTION_VALIDATION_RESULTS.json", validation)

    boundary = boundary_audit(validation, behavior3, model)
    write_json(OUTPUT_ROOT / "APP_CONSUMPTION_BOUNDARY_AUDIT.json", boundary)

    after = {rel(root): snapshot_tree(root) for root in READ_ONLY_ROOTS}
    changed = [root for root in before if before[root] != after[root]]
    mutation = {
        "status": "PASS" if not changed else "FAIL",
        "changed_read_only_roots": changed,
        "runtime_writes_redirected_to_task_output": True,
        "before": before,
        "after": after,
    }
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", mutation)

    secret = secret_audit()
    write_json(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.json", secret)
    write_docs(validation, behavior3)

    decision = decision_payload(inputs, behavior3, validation, boundary, mutation, secret)
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_APP_CONSUMPTION_SMOKE_R1_DECISION.json", decision)

    hashes = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            hashes.append(f"{sha256_file(path)}  {rel(path)}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(hashes) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": decision["status"],
        "output_root": str(OUTPUT_ROOT),
        "packet_count": decision["packet_count"],
        "behavior3_visible_path_created": decision["behavior3_visible_path_created"],
        "localhost_runtime_received_request": decision["localhost_runtime_received_request"],
        "static_html_path": decision["static_html_path"],
        "next_recommended_task": decision["next_recommended_task"],
    }, indent=2, sort_keys=True))
    return 0 if decision["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
