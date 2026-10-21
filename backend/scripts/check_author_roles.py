"""Run synthetic role/outcome cases; keep project data out of published evidence."""
import argparse
import json
from pathlib import Path

from app.application.ai_provider import ProviderError
from app.application.workflow import create_story_generation_service
from app.core.artifacts import Constraint, PlanSection
from scripts.check_reference_isolation import ObservedProvider

CASES = Path(__file__).resolve().parents[2] / "demo/evaluations/author-role-cases.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = []
    for case in json.loads(CASES.read_text()):
        print(case["id"], flush=True)
        provider = ObservedProvider(args.model)
        service = create_story_generation_service(provider)
        record = {"model": args.model, "case_id": case["id"],
                  "parameters": provider.metadata.parameters, "steps": provider.steps}
        try:
            if case["operation"] == "plan":
                service.plan(case["idea"], (), tuple(
                    Constraint(name=str(i), value=value)
                    for i, value in enumerate(case["constraints"])
                ), response_language=case["language"])
            else:
                service.review(
                    case["idea"], case["title"], case["logline"],
                    tuple(PlanSection(section_id=str(i), **section)
                          for i, section in enumerate(case["sections"])),
                    json.dumps({"idea": case["idea"], "constraints": case["constraints"],
                                "clarifications": []}, ensure_ascii=False),
                    response_language=case["language"],
                )
            record["status"] = "completed"
        except (ProviderError, ValueError) as error:
            record.update(status="failed", error=type(error).__name__)
        records.append(record)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(records, ensure_ascii=False, indent=2))
    return int(any(record["status"] != "completed" for record in records))


if __name__ == "__main__":
    raise SystemExit(main())
