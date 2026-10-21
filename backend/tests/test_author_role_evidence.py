"""Replay initial PR21 outputs against the validator, not current model quality."""
import hashlib
import json
from pathlib import Path

import pytest

from app.application.ai_provider import (
    MalformedProviderResponseError,
    ProviderMetadata,
    StructuredResult,
)
from app.application.workflow import create_story_generation_service
from app.core.artifacts import Constraint, PlanSection

ROOT = Path(__file__).resolve().parents[2] / "demo/evaluations"
CASES = {case["id"]: case for case in json.loads((ROOT / "author-role-cases.json").read_text())}
EVIDENCE = json.loads((ROOT / "author-role-results.json").read_text())


@pytest.mark.parametrize("record", EVIDENCE, ids=lambda row: row["case_id"])
def test_initial_pr21_evidence_still_rejects_invalid_quotes(record):
    class RecordedProvider:
        metadata = ProviderMetadata("ollama", record["model"], record["parameters"])

        def __init__(self):
            self.index = 0

        def request_structured(self, request):
            step = record["steps"][self.index]
            self.index += 1
            assert hashlib.sha256(request.input_text.encode()).hexdigest() == step["input_sha256"]
            # Recorded prompt hashes belong to commit 5095699; prompts now include creative choices.
            return StructuredResult(output=request.response_model.model_validate(step["output"]),
                                    model=record["model"])

    provider = RecordedProvider()
    service = create_story_generation_service(provider)
    case = CASES[record["case_id"]]

    def run():
        if case["operation"] == "plan":
            service.plan(case["idea"], (), tuple(Constraint(name=str(i), value=value)
                         for i, value in enumerate(case["constraints"])),
                         response_language=case["language"])
        else:
            service.review(case["idea"], case["title"], case["logline"],
                           tuple(PlanSection(section_id=str(i), **section)
                                 for i, section in enumerate(case["sections"])),
                           json.dumps({"idea": case["idea"], "constraints": case["constraints"],
                                       "clarifications": []}, ensure_ascii=False),
                           response_language=case["language"])

    if record["status"] == "failed":
        assert record["error"] == "MalformedProviderResponseError"
        with pytest.raises(MalformedProviderResponseError):
            run()
    else:
        run()
    assert provider.index == len(record["steps"])
