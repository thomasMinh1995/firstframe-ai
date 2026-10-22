"""Exercise an undecided author's local project without changing its saved content."""
import argparse
import json
from pathlib import Path

from app.api.schemas.projects import ProjectResponse
from app.application.ai_provider import ProviderError
from app.application.workflow import create_story_generation_service
from app.core.artifacts import Constraint
from scripts.check_reference_isolation import ObservedProvider


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--models", nargs="+", default=["qwen2.5:7b", "qwen2.5:3b"])
    args = parser.parse_args()
    project = ProjectResponse.model_validate_json(args.project_json.read_text())
    constraints = tuple(Constraint(name=str(i), value=v) for i, v in enumerate(project.constraints))
    records = []
    for model in args.models:
        print(model, flush=True)
        provider = ObservedProvider(model)
        service = create_story_generation_service(provider)
        record = {"model": model, "steps": provider.steps, "parameters": provider.metadata.parameters}
        try:
            analysis = service.analyze(project.idea, constraints, response_language=project.response_language)
            answers = tuple((q, "Chưa quyết định. Nếu đề xuất một lựa chọn, hãy ghi rõ đó là gợi ý của AI.")
                            for q in analysis.open_questions)
            result = service.plan(project.idea, answers, constraints, response_language=project.response_language)
            record["findings"] = [vars(item) for item in result.evaluation.findings]
            record["status"] = "completed"
        except (ProviderError, ValueError) as error:
            record.update(status="failed", error=type(error).__name__, detail=str(error))
        records.append(record)
        args.output.write_text(json.dumps(records, ensure_ascii=False, indent=2))
    return int(any(record["status"] == "failed" for record in records))


if __name__ == "__main__":
    raise SystemExit(main())
