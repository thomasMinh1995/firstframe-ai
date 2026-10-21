"""Verify historical Qwen inputs and output schemas; prompts may evolve.

This replays recorded outputs, not a fresh model-quality test.
"""
import hashlib
import json
from pathlib import Path

import pytest

from app.application.ai_provider import ProviderMetadata, StructuredResult
from app.application.workflow import (
    _EvaluationOutput,
    _GroundedEvaluationOutput,
    create_story_generation_service,
)
from app.core.artifacts import Constraint

ROOT = Path(__file__).resolve().parents[2] / "demo/evaluations"
CASES = {case["id"]: case for case in json.loads(
    (ROOT / "reference-isolation-cases.json").read_text()
)}
EVIDENCE = json.loads((ROOT / "reference-isolation-results.json").read_text())


@pytest.mark.parametrize("record", EVIDENCE["runs"],
                         ids=lambda row: row["model"] + "/" + row["case_id"])
def test_historical_evidence_inputs_and_schemas(record):
    class RecordedProvider:
        metadata = ProviderMetadata("ollama", record["model"], EVIDENCE["parameters"])

        def __init__(self):
            self.index = 0

        def request_structured(self, request):
            saved = record["steps"][self.index]
            self.index += 1
            assert request.stage == saved["stage"]
            if request.stage == "planning":
                assert hashlib.sha256(request.input_text.encode()).hexdigest() == saved["input_sha256"]
            # Prompt hashes describe the PR20 run, not the current prompt revision.
            output = saved["output"]
            if request.stage == "evaluation":
                # Archived feedback predates grounding; only validate its historical schema.
                archived = _EvaluationOutput.model_validate(output)
                output = _GroundedEvaluationOutput(
                    strengths=[], weaknesses=[], rubric_scores=archived.rubric_scores,
                    passed=archived.passed,
                ).model_dump()
            return StructuredResult(
                output=request.response_model.model_validate(output),
                model=record["model"],
            )

    case = CASES[record["case_id"]]
    provider = RecordedProvider()
    create_story_generation_service(provider).plan(
        case["idea"], tuple(tuple(pair) for pair in case["answers"]),
        tuple(Constraint(name=str(i), value=value) for i, value in enumerate(case["constraints"])),
        response_language=case["language"],
    )
    assert provider.index == len(record["steps"]) == 2
