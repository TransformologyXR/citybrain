"""Run ASK v1.1 real-corpus eval R2 mapping expansion."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.ask_v11.real_corpus_eval import (  # noqa: E402
    run_real_corpus_eval_r2_mapping_expansion,
    write_real_corpus_eval_r2_report,
)


def main() -> int:
    report = run_real_corpus_eval_r2_mapping_expansion()
    paths = write_real_corpus_eval_r2_report(
        report, ROOT / "outputs" / "ask_v11_real_corpus_eval_r2"
    )
    print(f"final_decision={report.final_decision}")
    print(f"json={paths['json']}")
    print(f"summary={paths['summary']}")
    print(f"failures={paths['failures']}")
    print(f"mapping_changes={paths['mapping_changes']}")
    return 0 if report.status in {"PASS", "PASS_WITH_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
