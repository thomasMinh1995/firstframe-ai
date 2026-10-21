"""Replay saved review inputs on local Qwen; never open the project database."""

import argparse
import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from app.application.dataset import capture_workflow, get_dataset_store
from app.application.workflow import create_story_generation_service
from app.core.artifacts import PlanSection
from app.infrastructure.ollama_provider import OllamaProvider, OllamaProviderConfig


def replay(source: Path, destination: Path) -> None:
    cases = [json.loads(line) for line in source.read_text().splitlines() if line.strip()]
    # Exclusive creation preserves earlier evidence, including failed runs.
    with (
        destination.open("x", encoding="utf-8") as output,
        tempfile.TemporaryDirectory() as directory,
    ):
        previous = os.environ.get("DATASET_DIR")
        os.environ["DATASET_DIR"] = directory
        try:
            for case in cases:
                data = case["input"]
                draft = data["draft"]
                try:
                    with capture_workflow(case["operation"], data) as recording:
                        service = create_story_generation_service(
                            OllamaProvider(OllamaProviderConfig("qwen2.5:3b"))
                        )
                        result = service.review(
                            data["idea"],
                            draft["title"],
                            draft["logline"],
                            tuple(
                                PlanSection(str(i), s["title"], s.get("purpose", ""), s["content"])
                                for i, s in enumerate(draft["sections"])
                            ),
                            json.dumps(
                                {
                                    "idea": data["idea"],
                                    "constraints": data["constraints"],
                                    "clarifications": data.get("clarifications", []),
                                },
                                ensure_ascii=False,
                            ),
                            response_language=data["response_language"],
                        )
                        recording.complete(
                            {
                                "passed": result.passed,
                                "fidelity": result.fidelity,
                                "findings": [asdict(f) for f in result.findings],
                            }
                        )
                finally:
                    # Rewrite only the new file opened above, not a prior result file.
                    output.seek(0)
                    output.truncate()
                    output.write(
                        "".join(
                            json.dumps(r, ensure_ascii=False) + "\n"
                            for r in get_dataset_store().records()
                        )
                    )
                    output.flush()
        finally:
            if previous is None:
                os.environ.pop("DATASET_DIR", None)
            else:
                os.environ["DATASET_DIR"] = previous


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    replay(args.dataset, args.output)
