"""Exercise real planner/critic profiles without writing project data.

Run from backend with PYTHONPATH=. and --output /tmp/reference-isolation.json.
Schema success is not a fidelity score: inspect outputs against review_checks.
"""
import argparse
import json
import time
from pathlib import Path

from app.application.ai_provider import ProviderError, strict_json_instructions
from app.application.workflow import create_story_generation_service
from app.core.artifacts import Constraint
from app.infrastructure.ollama_provider import OllamaProvider, OllamaProviderConfig

CASES = Path(__file__).resolve().parents[2] / "demo/evaluations/reference-isolation-cases.json"


class ObservedProvider:
    def __init__(self, model):
        self.provider = OllamaProvider(OllamaProviderConfig(model=model))
        self.steps = []

    @property
    def metadata(self):
        return self.provider.metadata

    def request_structured(self, request):
        step = {"stage": request.stage, "instructions": strict_json_instructions(request),
                "input": request.input_text}
        self.steps.append(step)
        started = time.monotonic()
        try:
            result = self.provider.request_structured(request)
            step["output"] = result.output.model_dump(mode="json")
            return result
        except (ProviderError, ValueError) as error:
            step["error"] = type(error).__name__
            raise
        finally:
            step["seconds"] = round(time.monotonic() - started, 3)
            print(request.stage, step["seconds"], step.get("error", "completed"), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=["qwen2.5:3b", "qwen2.5:7b"])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = []
    for model in args.models:
        for case in json.loads(CASES.read_text()):
            print(model, case["id"], flush=True)
            provider = ObservedProvider(model)
            record = {"model": model, "parameters": provider.metadata.parameters,
                      "case": case, "steps": provider.steps}
            try:
                create_story_generation_service(provider).plan(
                    case["idea"], tuple(tuple(pair) for pair in case["answers"]),
                    tuple(Constraint(name=str(i), value=value)
                          for i, value in enumerate(case["constraints"])),
                    response_language=case["language"],
                )
                record["status"] = "completed"
            except (ProviderError, ValueError) as error:
                record["status"] = "failed"
                record["error"] = type(error).__name__
            records.append(record)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(records, ensure_ascii=False, indent=2))
    return int(any(record["status"] == "failed" for record in records))


if __name__ == "__main__":
    raise SystemExit(main())
