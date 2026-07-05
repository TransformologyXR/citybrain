from __future__ import annotations


class TracePanel:
    def __init__(self, bundle: dict):
        self.bundle = bundle

    def stages(self) -> list[dict]:
        return self.bundle.get("trace", [])

    def summary(self) -> dict:
        stages = self.stages()
        return {
            "stage_count": len(stages),
            "single_synthesize_narration_boundary": sum(1 for stage in stages if stage.get("narration_permitted")) == 1,
            "execution_state": self.bundle["one_truth"].get("execution_state"),
        }
