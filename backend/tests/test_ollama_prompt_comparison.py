import json
from pathlib import Path

import httpx
import pytest

from app.application.ai_provider import StructuredRequest, strict_json_instructions
from app.application.workflow import _ReasoningOutput
from scripts.compare_ollama_prompts import compare, indicators


@pytest.mark.parametrize("invalid_first", [False, True])
def test_paired_replay_preserves_input_schema_seed_and_raw_evidence(
    tmp_path, monkeypatch, invalid_first
):
    output = {"summary": "Mẹ chờ trong bếp.", "notes": [], "missing_information": []}
    request = StructuredRequest(
        "Old instructions", "Target response language: Vietnamese\nMẹ chờ.", _ReasoningOutput
    )
    source = tmp_path / "record.json"
    source.write_text(
        json.dumps(
            {
                "status": "completed",
                "run_id": "synthetic-eval",
                "operation": "analyze",
                "steps": [
                    {
                        "stage": "reasoning",
                        "output": output,
                        "request": {
                            "input_text": request.input_text,
                            "effective_instructions": strict_json_instructions(request),
                            "response_schema": _ReasoningOutput.model_json_schema(),
                        },
                    }
                ],
            }
        )
    )
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs["json"])
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "done": True,
                "model": "qwen2.5:3b",
                "message": {
                    "content": "not-json"
                    if invalid_first and len(calls) == 1
                    else json.dumps(output)
                },
            },
        )

    monkeypatch.setattr("scripts.compare_ollama_prompts.httpx.post", post)
    destination = tmp_path / "comparison.json"
    report = compare(source, destination, [42, 73], "http://127.0.0.1:11434")
    assert len(calls) == 4
    assert sum(run["status"] == "failed" for run in report["runs"]) == int(invalid_first)
    assert [run["variant"] for run in report["runs"]] == ["before", "after", "after", "before"]
    assert all(body["messages"][1]["content"] == request.input_text for body in calls)
    assert all(body["format"] == _ReasoningOutput.model_json_schema() for body in calls)
    assert [body["options"]["seed"] for body in calls] == [42, 42, 73, 73]
    assert all(run["raw_output"] and run["actual_model"] == "qwen2.5:3b" for run in report["runs"])
    assert len({run["input_sha256"] for run in report["runs"]}) == 1
    assert json.loads(destination.read_text()) == report
    with pytest.raises(ValueError, match="already exists"):
        compare(source, destination, [42], "http://127.0.0.1:11434")


def test_repetition_screening_ignores_json_keys_and_section_anchors():
    assert indicators({"story": ["[Middle] Mẹ im lặng."]})["english_marker_hits"] == 0
    repeated = indicators(["Mẹ đặt bát xuống bàn.", "Mẹ đặt bát xuống bàn."])
    assert repeated["repeated_4gram_fraction"] == 0.5


@pytest.mark.parametrize("experimental", [False, True])
def test_six_critic_scenarios_replay_both_variants_without_losing_author_or_draft(
    tmp_path, monkeypatch, experimental
):
    from app.application.workflow import _EvaluationOutput

    source = Path(__file__).resolve().parents[2] / "demo/evaluations/critic-cases-2026-10-21.jsonl"
    fixtures = [json.loads(line) for line in source.read_text().splitlines()]
    output = _EvaluationOutput(
        passed=True,
        rubric_scores=dict.fromkeys(
            [
                "story_clarity",
                "character",
                "conflict",
                "emotional_impact",
                "ending",
                "production_feasibility",
            ],
            4,
        ),
        strengths=["[Beginning] Tình huống rõ."],
        weaknesses=[],
        suggestions=[],
    )
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs["json"])
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "done": True,
                "model": "qwen2.5:3b",
                "message": {"content": output.model_dump_json()},
            },
        )

    monkeypatch.setattr("scripts.compare_ollama_prompts.httpx.post", post)
    report = compare(
        source,
        tmp_path / "result.json",
        [42],
        "http://127.0.0.1:11434",
        ["evaluation"],
        experimental_critic=experimental,
    )
    assert len(fixtures) == 6
    assert len(calls) == len(report["runs"]) == 12
    for fixture, before, after in zip(
        fixtures, report["runs"][::2], report["runs"][1::2], strict=True
    ):
        original = fixture["steps"][0]["request"]["input_text"]
        assert before["input_text"] == original
        assert before["response_schema"] == after["response_schema"]
        for marker in ("Creator intent and decisions:\n", "Current draft (JSON data):\n"):
            value, _ = json.JSONDecoder().raw_decode(original.split(marker, 1)[1])
            assert json.dumps(value, ensure_ascii=False) in after["input_text"]
        assert fixture["expected_behavior"] not in after["input_text"]
        assert (after["instructions"] != before["instructions"]) is experimental
        if not experimental:
            assert after["input_text"] == before["input_text"]
        assert before["feedback_pairs_valid"] is True
        assert after["feedback_pairs_valid"] is True
