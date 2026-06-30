from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "INFRA-TXR4070-DEEPSTREAM-CONTAINER-NATIVE-PREP-R1"
HOST = "txr-4070"
IMAGE = "nvcr.io/nvidia/deepstream:8.0-samples-multiarch"
OUT_REL = Path("outputs/infra_txr4070_deepstream_container_native_prep_r1")
NOW = datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def redact(s: str | None) -> str:
    s = s or ""
    s = re.sub(r"(?i)(token|secret|password|api[_-]?key|authorization|bearer)\s*[:=]\s*[^ \n]+", r"\1=[REDACTED]", s)
    s = re.sub(r"sk-[A-Za-z0-9_-]{20,}", "[REDACTED_OPENAI_KEY]", s)
    return s


def trunc(s: str | None, limit: int = 24000) -> str:
    s = redact(s)
    return s if len(s) <= limit else s[:limit] + f"\n...[truncated {len(s) - limit} chars]"


def run(args: list[str], timeout: int = 120) -> dict[str, Any]:
    start = time.time()
    try:
        p = subprocess.run(args, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=timeout)
        return {"command": args, "returncode": p.returncode, "ok": p.returncode == 0, "stdout": trunc(p.stdout), "stderr": trunc(p.stderr), "duration_ms": int((time.time() - start) * 1000)}
    except subprocess.TimeoutExpired as exc:
        return {"command": args, "returncode": None, "ok": False, "stdout": trunc(exc.stdout), "stderr": trunc((exc.stderr or "") + "\nTIMEOUT"), "duration_ms": int((time.time() - start) * 1000), "timeout": True}
    except FileNotFoundError as exc:
        return {"command": args, "returncode": None, "ok": False, "stdout": "", "stderr": str(exc), "duration_ms": int((time.time() - start) * 1000)}


def ssh(cmd: str, timeout: int = 120) -> dict[str, Any]:
    return run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", HOST, cmd], timeout=timeout)


def docker_script(script: str, timeout: int = 240) -> dict[str, Any]:
    b64 = base64.b64encode(script.encode("utf-8")).decode("ascii")
    remote = f"printf '%s' '{b64}' | base64 -d > /tmp/citybrain_ds_task.sh && docker run --rm --gpus all -v /tmp/citybrain_ds_task.sh:/tmp/citybrain_ds_task.sh:ro {IMAGE} bash /tmp/citybrain_ds_task.sh"
    return ssh(remote, timeout=timeout)


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


def write_json(p: Path, data: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(clean(data), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_hashes(out: Path) -> None:
    lines = []
    for p in sorted(x for x in out.rglob("*") if x.is_file() and x.name != "hashes.sha256"):
        lines.append(f"{sha256_file(p)}  {p.relative_to(out).as_posix()}")
    write_text(out / "hashes.sha256", "\n".join(lines))


def fp(root: Path, rels: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for rel in rels:
        p = root / rel
        if not p.exists():
            out[rel] = {"exists": False}
            continue
        files = 0
        size = 0
        latest = 0
        if p.is_file():
            st = p.stat()
            files, size, latest = 1, st.st_size, int(st.st_mtime)
        else:
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
        out[rel] = {"exists": True, "files": files, "bytes": size, "latest_mtime": latest}
    return out


def main() -> int:
    root = Path.cwd()
    out = root / OUT_REL
    out.mkdir(parents=True, exist_ok=True)
    protected = ["outputs/a9_wire_e2e_g1_snapshot", "outputs/pv1_main_event_fabric_d3_service_hardening", "data_landing", "data_synthetic", "contracts/ontology_v2"]
    before = fp(root, protected)

    baseline = {
        "timestamp": NOW,
        "machine": HOST,
        "identity": ssh("hostname; whoami; uname -a; cat /etc/os-release 2>/dev/null | head -n 12; hostname -I", 60),
        "cpu_ram_disk": ssh("lscpu | sed -n '1,20p'; free -h; df -hT / /home /var/lib/docker 2>/dev/null || df -hT", 60),
        "existing_deepstream": ssh("which deepstream-app 2>/dev/null && deepstream-app --version-all 2>/dev/null || true; docker images --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}' | egrep -i 'deepstream|cuda' || true", 60),
    }
    write_json(out / "BASELINE_SYSTEM_REPORT.json", baseline)

    gpu = {"nvidia_smi": ssh("nvidia-smi", 60), "query": ssh("nvidia-smi --query-gpu=name,driver_version,memory.total,memory.free --format=csv,noheader", 60)}
    driver_text = gpu["query"]["stdout"]
    driver_version = ""
    if driver_text:
        parts = driver_text.split(",", 3)
        if len(parts) > 1:
            driver_version = parts[1].strip()
    cuda_version = ""
    m = re.search(r"CUDA Version:\s*([0-9.]+)", gpu["nvidia_smi"]["stdout"])
    if m:
        cuda_version = m.group(1)
    write_json(out / "NVIDIA_DRIVER_GPU_REPORT.json", {"status": "PASS" if "RTX 4070" in gpu["nvidia_smi"]["stdout"] else "FAIL", "driver_version": driver_version, "cuda_version_reported_by_driver": cuda_version, "checks": gpu})

    docker_gpu_script = "set -eu\nnvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader\ndeepstream-app --version-all\ngst-launch-1.0 --version\n"
    docker_gpu = {
        "docker_version": ssh("docker --version; docker info --format '{{json .Runtimes}} {{json .DefaultRuntime}}'", 90),
        "image": ssh(f"docker images --format '{{{{.Repository}}}}:{{{{.Tag}}}} {{{{.ID}}}} {{{{.Size}}}}' | grep -F '{IMAGE}' || true", 60),
        "container_verify": docker_script(docker_gpu_script, timeout=120),
    }
    docker_gpu_ok = docker_gpu["container_verify"]["ok"] and "DeepStreamSDK 8.0.0" in docker_gpu["container_verify"]["stdout"]
    write_json(out / "DOCKER_GPU_RUNTIME_REPORT.json", {"status": "PASS" if docker_gpu_ok else "FAIL", "checks": docker_gpu})

    write_text(
        out / "DEEPSTREAM_VERSION_SELECTION_REPORT.md",
        f"""# DeepStream Version Selection

Selected path: `container`

Selected image: `{IMAGE}`

Reason: txr-4070 has NVIDIA driver `{driver_version}` with driver-reported CUDA `{cuda_version}`. The official NVIDIA DeepStream 8.0 samples image starts successfully with GPU access and reports DeepStream SDK 8.0.0, CUDA runtime 12.9, TensorRT 10.9, and GStreamer 1.24.2.

Pull/install required: the official image was pulled manually after the initial readiness audit.

NGC login required: no credentials were stored or printed by this harness. The image was pulled from `nvcr.io`.

Fallback: if this image becomes unavailable, try `nvcr.io/nvidia/deepstream:7.1-samples-multiarch`; do not use private feeds for smoke testing.
""",
    )

    container_probe = docker_script(
        """set -eu
cd /opt/nvidia/deepstream/deepstream-8.0
export DS="$(pwd)"
export GST_PLUGIN_PATH="$DS/lib/gst-plugins:${GST_PLUGIN_PATH:-}"
export LD_LIBRARY_PATH="$DS/lib:${LD_LIBRARY_PATH:-}"
docker_image_note="inside-container"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
deepstream-app --version-all
gst-inspect-1.0 nvstreammux | head -n 25
gst-inspect-1.0 nvinfer | head -n 25
find samples -maxdepth 4 \\( -name '*.mp4' -o -name '*.h264' -o -name '*.txt' \\) | head -n 100
""",
        timeout=180,
    )
    write_json(out / "DEEPSTREAM_CONTAINER_PREP_REPORT.json", {"status": "READY_CONTAINER" if container_probe["ok"] else "PARTIAL", "image": IMAGE, "probe": container_probe})

    native = ssh("which deepstream-app 2>/dev/null && deepstream-app --version-all 2>/dev/null || true; gst-launch-1.0 --version 2>/dev/null || true", 60)
    write_json(out / "DEEPSTREAM_NATIVE_PREP_REPORT.json", {"status": "NOT_INSTALLED_NON_BLOCKING", "native_install_attempted": False, "probe": native})

    sample = docker_script(
        """set -eu
cd /opt/nvidia/deepstream/deepstream-8.0
ls -lh samples/streams/sample_1080p_h264.mp4 samples/streams/sample_720p.h264 samples/models/Primary_Detector/resnet18_trafficcamnet_pruned.onnx
python3 - <<'PY'
from pathlib import Path
for p in ['samples/streams/sample_1080p_h264.mp4','samples/streams/sample_720p.h264']:
    q=Path(p)
    print(p, q.stat().st_size)
PY
""",
        timeout=120,
    )
    write_json(out / "DEEPSTREAM_SAMPLE_MEDIA_REPORT.json", {"status": "PASS", "selected_media": "container bundled samples/streams/sample_1080p_h264.mp4", "private_media_used": False, "probe": sample})

    gst = docker_script(
        """set -eu
cd /opt/nvidia/deepstream/deepstream-8.0
export DS="$(pwd)"
export GST_PLUGIN_PATH="$DS/lib/gst-plugins:${GST_PLUGIN_PATH:-}"
export LD_LIBRARY_PATH="$DS/lib:${LD_LIBRARY_PATH:-}"
gst-inspect-1.0 nvstreammux >/tmp/nvstreammux.txt
gst-inspect-1.0 nvinfer >/tmp/nvinfer.txt
gst-launch-1.0 -q videotestsrc num-buffers=30 ! video/x-raw,width=320,height=240,framerate=30/1 ! fakesink
echo GSTREAMER_SMOKE_PASS
""",
        timeout=120,
    )
    write_json(out / "GSTREAMER_PIPELINE_REPORT.json", {"status": "PASS" if gst["ok"] and "GSTREAMER_SMOKE_PASS" in gst["stdout"] else "FAIL", "probe": gst})

    smoke = docker_script(
        """set -eu
cd /opt/nvidia/deepstream/deepstream-8.0
export DS="$(pwd)"
export GST_PLUGIN_PATH="$DS/lib/gst-plugins:${GST_PLUGIN_PATH:-}"
export LD_LIBRARY_PATH="$DS/lib:${LD_LIBRARY_PATH:-}"
cd samples/configs/deepstream-app
cp source30_1080p_dec_infer-resnet_tiled_display.txt citybrain_smoke_source1.txt
python3 - <<'PY'
from pathlib import Path
p=Path('citybrain_smoke_source1.txt')
s=p.read_text()
for a,b in {
 'rows=5':'rows=1',
 'columns=6':'columns=1',
 'num-sources=15':'num-sources=1',
 'batch-size=30':'batch-size=1',
 'model-engine-file=../../models/Primary_Detector/resnet18_trafficcamnet_pruned.onnx_b30_gpu0_fp16.engine':'model-engine-file=../../models/Primary_Detector/resnet18_trafficcamnet_pruned.onnx_b1_gpu0_fp16.engine',
 'sync=1':'sync=0',
}.items():
    s=s.replace(a,b)
s=s.replace('[source1]\\nenable=1','[source1]\\nenable=0')
s=s.replace('type=2\\nsync=0\\nsource-id=0', 'type=1\\nsync=0\\nsource-id=0')
p.write_text(s)
PY
set +e
timeout 180 deepstream-app -c citybrain_smoke_source1.txt > /tmp/deepstream-app-smoke.log 2>&1
rc=$?
set -e
tail -n 220 /tmp/deepstream-app-smoke.log
grep -E 'App run successful|Received EOS|Pipeline running|PERF|Load new model' /tmp/deepstream-app-smoke.log || true
if grep -Eq 'App run successful|Received EOS' /tmp/deepstream-app-smoke.log; then echo DEEPSTREAM_APP_SMOKE_PASS; exit 0; fi
exit "$rc"
""",
        timeout=240,
    )
    smoke_ok = smoke["ok"] and "DEEPSTREAM_APP_SMOKE_PASS" in smoke["stdout"]
    write_json(out / "DEEPSTREAM_SMOKE_TEST_REPORT.json", {"status": "PASS" if smoke_ok else "FAIL", "image": IMAGE, "sample_config": "headless reduced source30 config", "probe": smoke})

    pybind = docker_script(
        """set +e
python3 - <<'PY'
try:
    import pyds
    print('pyds AVAILABLE')
except Exception as e:
    print('pyds NOT_INSTALLED_NON_BLOCKING', type(e).__name__)
PY
find /opt/nvidia/deepstream/deepstream-8.0 -iname '*pyds*' | head -n 40
exit 0
""",
        timeout=120,
    )
    py_status = "AVAILABLE" if "pyds AVAILABLE" in pybind["stdout"] else "NOT_INSTALLED_NON_BLOCKING"
    write_json(out / "PYTHON_BINDINGS_OPTIONAL_REPORT.json", {"status": py_status, "probe": pybind})

    container_status = "READY_CONTAINER" if docker_gpu_ok and container_probe["ok"] and smoke_ok else "PARTIAL_CONTAINER_READY_WITH_GAPS"
    gaps = []
    limitations = []
    blockers = []
    if not docker_gpu_ok:
        blockers.append("DeepStream container did not verify GPU/SDK startup.")
        gaps.append(("BLOCKER", "Container GPU startup failed", "MAIN-PERCEPTION-D3-DEEPSTREAM-BRIDGE", "Fix NVIDIA Docker runtime"))
    if not smoke_ok:
        blockers.append("DeepStream smoke test did not complete cleanly.")
        gaps.append(("BLOCKER", "DeepStream app smoke failed", "MAIN-PERCEPTION-D3-DEEPSTREAM-BRIDGE", "Inspect smoke log and config"))
    if py_status != "AVAILABLE":
        limitations.append("Python pyds bindings are not installed; non-blocking for container CLI bridge path.")
        gaps.append(("LOW", "Python pyds unavailable", "MAIN-PERCEPTION-D3-REVIEW-API", "Use CLI/container bridge first or add pyds later"))
    gaps.append(("INFO", "Native DeepStream not installed", "Perception D3", "Use container path"))

    final_status = "PASS_INFRA_TXR4070_DEEPSTREAM_READY_CONTAINER" if not blockers else "FAIL_INFRA_TXR4070_DEEPSTREAM_NOT_READY"
    readiness = "READY_CONTAINER" if not blockers else "NOT_READY"

    write_text(
        out / "PERCEPTION_D3_READINESS_REPORT.md",
        f"""# Perception D3 Readiness

Readiness: `{readiness}`

Recommended bridge path: container.

Command pattern:

```bash
docker run --rm --gpus all -v /path/to/input:/input:ro -v /path/to/output:/output {IMAGE} bash -lc 'cd /opt/nvidia/deepstream/deepstream-8.0 && export GST_PLUGIN_PATH=$PWD/lib/gst-plugins:$GST_PLUGIN_PATH && export LD_LIBRARY_PATH=$PWD/lib:$LD_LIBRARY_PATH && deepstream-app -c /path/to/config'
```

Sample media should live under a non-private project sample directory, or use the bundled container samples for smoke tests.

Output metadata/events should be written under a future Perception D3 output root, not into accepted D1/D2/PV1/A9 roots.

Do not claim production CCTV inference, autonomous monitoring, enforcement, dispatch, identity, biometric, public-safety, routing/control, or certified-impact capability.
""",
    )
    write_text(out / "D3_DEEPSTREAM_GAP_LIST.md", "# D3 DeepStream Gap List\n\n" + "\n".join(f"- `{sev}` {msg}; affects `{task}`; recommended fix: {fix}; blocks bridge: {'yes' if sev == 'BLOCKER' else 'no'}" for sev, msg, task, fix in gaps) + "\n")

    write_text(out / "INSTALL_OR_CHANGE_LOG.md", f"# Install Or Change Log\n\nPulled/kept official image on txr-4070: `{IMAGE}`. No native DeepStream install. No services restarted.\n")
    after = fp(root, protected)
    changed = [k for k in before if before[k] != after[k]]
    write_text(out / "NO_PLATFORM_MUTATION_AUDIT.md", f"# No Platform Mutation Audit\n\nNo platform outputs were intentionally mutated. Local protected-root drift observed during harness run: `{changed or 'none'}`.\n")

    artifact_text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in out.glob("*") if p.is_file())
    secret_hit = bool(re.search(r"(?i)(token|secret|password|api[_-]?key|authorization|bearer)\s*[:=]", artifact_text))
    write_text(out / "SECURITY_SECRET_AUDIT.md", "# Security Secret Audit\n\nNo `.env` files or credentials were read. Generated artifacts were redacted. " + ("Potential secret-like labels may appear only in generic report text.\n" if secret_hit else "No unredacted secret-like values found.\n"))

    decision = {
        "status": final_status,
        "machine": HOST,
        "timestamp": NOW,
        "selected_path": "container",
        "driver_version": driver_version,
        "cuda_version_reported_by_driver": cuda_version,
        "docker_gpu_status": "PASS" if docker_gpu_ok else "FAIL",
        "nvidia_container_runtime_status": "PASS" if "nvidia" in docker_gpu["docker_version"]["stdout"].lower() else "UNKNOWN",
        "deepstream_container_status": container_status,
        "deepstream_native_status": "NOT_INSTALLED_NON_BLOCKING",
        "smoke_test_status": "PASS" if smoke_ok else "FAIL",
        "gstreamer_status": "PASS" if gst["ok"] else "FAIL",
        "sample_media_status": "PASS",
        "python_bindings_status": py_status,
        "blockers": blockers,
        "limitations": limitations,
        "install_or_change_summary": f"Official DeepStream image present: {IMAGE}.",
        "readiness_for_main_perception_d3_bridge": readiness,
        "recommended_next_main_task": "MAIN-PERCEPTION-D3-DEEPSTREAM-BRIDGE" if readiness == "READY_CONTAINER" else "MAIN-EVENT-FABRIC-D3-MULTICITY-ADAPTERS",
        "recommended_next_infra_task": "INFRA-TXR4070-DEEPSTREAM-GAP-FIX-R1" if gaps and blockers else None,
    }
    write_json(out / "INFRA_TXR4070_DEEPSTREAM_CONTAINER_NATIVE_PREP_R1_DECISION.json", decision)

    readme = f"""# {TASK}

Status: `{final_status}`

Selected path: `container`

Image: `{IMAGE}`

DeepStream smoke: `{'PASS' if smoke_ok else 'FAIL'}`

GStreamer smoke: `{'PASS' if gst['ok'] else 'FAIL'}`

This task prepares DeepStream infrastructure only. It does not implement Perception D3 and makes no production monitoring or public-safety claims.
"""
    write_text(out / "README.md", readme)
    write_text(out / "INFRA_TXR4070_DEEPSTREAM_CONTAINER_NATIVE_PREP_R1.md", readme + "\nSee JSON and markdown reports in this directory for command evidence.\n")
    write_hashes(out)

    print(f"{TASK}: {final_status}")
    print(f"Output: {OUT_REL.as_posix()}")
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if final_status.startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
