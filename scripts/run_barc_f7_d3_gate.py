from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    script = project_root / "txr_citybrain_barc_f7_d3_civic_sensor_fusion_evidencebundles.py"
    return subprocess.call([sys.executable, str(script), "--project-root", str(project_root), *sys.argv[1:]], cwd=project_root)


if __name__ == "__main__":
    raise SystemExit(main())
