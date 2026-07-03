"""Emit ASK Flow v1.1 packet JSON Schema from the Pydantic models."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.ask_v11.packets import SCHEMA_MODELS  # noqa: E402


def build_schema() -> dict:
    schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "citybrain://ask-v11/packets",
        "title": "TXR CityBrain ASK Flow v1.1 packet contracts",
        "$defs": {},
    }
    for model in SCHEMA_MODELS:
        model_schema = model.model_json_schema(ref_template="#/$defs/{model}")
        schema["$defs"].update(model_schema.pop("$defs", {}))
        schema["$defs"][model.__name__] = model_schema
    return schema


def main() -> int:
    output = ROOT / "packages" / "contracts" / "ask_v11_packets.schema.json"
    output.write_text(json.dumps(build_schema(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
