"""Verify that published Qwen evidence still corresponds to current requests.

This replays recorded outputs, not a fresh model-quality test.
"""
import hashlib
import json
from pathlib import Path

import pytest

from app.application.ai_provider import ProviderMetadata, StructuredResult, strict_json_instructions
from app.application.workflow import create_story_generation_service
from app.core.artifacts import Constraint

ROOT = Path(__file__).resolve().parents[2] / "demo/evaluations"
CASES = {case["id"]: case for case in json.loads(
    (ROOT / "reference-isolation-cases.json").read_text()
)}
EVIDENCE = json.loads((ROOT / "reference-isolation-results.json").read_text())


@pytest.mark.parametrize("record", EVIDENCE["runs"],
                         ids=lambda row: row["model"] + "/" + row["case_id"])
def test_published_evidence_matches_current_requests(record):
    class RecordedProvider:
        metadata = ProviderMetadata("ollama", record["model"], EVIDENCE["parameters"])

        def __init__(self):
            self.index = 0

        def request_structured(self, request):
            saved = record["steps"][self.index]
            self.index += 1
            assert request.stage == saved["stage"]
            assert hashlib.sha256(request.input_text.encode()).hexdigest() == saved["input_sha256"]
            assert hashlib.sha256(strict_json_instructions(request).encode()).hexdigest() == (
                saved["instructions_sha256"]
            )
            return StructuredResult(
                output=request.response_model.model_validate(saved["output"]),
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
