"""Run ASK v1.1 sealed eval and write closeout artifacts."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.ask_v11.eval import run_sealed_eval, write_eval_report  # noqa: E402


def main() -> int:
    report = run_sealed_eval()
    paths = write_eval_report(report, ROOT / "outputs" / "ask_v11_sealed_eval")
    print(f"final_decision={report.final_decision}")
    print(f"json={paths['json']}")
    print(f"markdown={paths['markdown']}")
    return 0 if report.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
