import copy
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from scripts import run_framing_gate_experiment as experiment
from scripts.summarize_framing_gate_experiment import summarize


def source():
    return {"cards": [{"id": "a", "text": "Một hành vi."},
                       {"id": "b", "text": "Lời dẫn thể hiện góc nhìn."}],
            "audience": "Người lớn", "language_policy": "Đã chốt", "publication_rules": []}


def output(stance="not_applicable", language="no_violation"):
    return {"themes": [
        {"topic_id": topic, "stance": stance if topic == "R1" else "not_applicable",
         "evidence": [{"card_id": "b", "quote": "góc nhìn"}]
         if topic == "R1" and stance in {"critical", "endorsing"} else []}
        for topic in ["R1", "R2", "R3"]],
        "language": {"status": language, "evidence": [{"card_id": "a", "quote": "hành vi"}]
                     if language == "clear_violation" else []}}


@pytest.mark.parametrize("stance,action", [("not_applicable", "allow"), ("critical", "allow"),
                                          ("endorsing", "block"), ("unclear", "warn")])
def test_policy_mapping_and_save_edit_are_independent(stance, action):
    current = source()
    result = experiment.decide(output(stance), experiment.digest(current), current)
    assert result["action"] == action
    assert result["can_publish"] == (action != "block")
    assert result["can_save"] and result["can_edit"]
    assert result["action"] == "allow" or experiment.warning(result)


def test_critical_does_not_override_language_policy():
    current = source()
    result = experiment.decide(output("critical", "clear_violation"),
                               experiment.digest(current), current)
    assert result["action"] == "block" and result["blocked_rules"] == ["R4"]


@pytest.mark.parametrize("field", ["cards", "audience", "language_policy", "publication_rules"])
def test_any_changed_snapshot_invalidates_old_decision(field):
    current = source()
    edited = copy.deepcopy(current)
    if field == "cards":
        edited[field][0]["text"] += " Bản mới."
    elif isinstance(edited[field], list):
        edited[field].append("Đã sửa")
    else:
        edited[field] += " Đã sửa"
    result = experiment.decide(output(), experiment.digest(current), edited)
    assert result["reason"] == "stale_snapshot" and not result["can_publish"]
    assert result["can_save"] and result["can_edit"]


@pytest.mark.parametrize("bad", [None, {}, {"themes": [], "language": {}}])
def test_invalid_assessment_is_held_without_blocking_save_edit(bad):
    current = source()
    result = experiment.decide(bad, experiment.digest(current), current)
    assert result["action"] == "review_required" and not result["can_publish"]
    assert result["can_save"] and result["can_edit"]


def test_fake_source_quote_cannot_authorize_a_block():
    current = source()
    bad = output("endorsing")
    bad["themes"][0]["evidence"][0]["quote"] = "Không có trong nguồn"
    assert experiment.decide(bad, experiment.digest(current), current)["action"] == "review_required"


def test_expected_labels_are_never_sent_to_model():
    case = {"input": source(), "expected_stances": {"R1": "endorsing"},
            "expected_action": "block", "grading_note": "PRIVATE_EXPECTATION"}
    request = experiment.request(case, "Prompt đã chốt")
    assert json.loads(request.input_text) == case["input"]
    assert "PRIVATE_EXPECTATION" not in request.input_text


def test_freeze_detects_artifact_change_and_does_not_overwrite(tmp_path):
    root = tmp_path / "run"
    experiment.freeze(root)
    manifest = experiment.verify_freeze(root)
    assert manifest["planned_calls"] == 60
    with pytest.raises(FileExistsError):
        experiment.freeze(root)
    with (root / "cases.json").open("a") as stream:
        stream.write(" ")
    with pytest.raises(ValueError, match="Frozen artifact changed"):
        experiment.verify_freeze(root)


def test_started_run_is_not_retried(tmp_path):
    root = tmp_path / "run"
    experiment.freeze(root)
    (root / "started.json").write_text("{}")
    with pytest.raises(ValueError, match="already started"):
        experiment.run(root)


def test_concurrent_claims_cannot_overwrite_run_marker(tmp_path):
    def claim():
        try:
            experiment.claim_run(tmp_path)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: claim(), range(2))) == [False, True]
    before = (tmp_path / "started.json").read_bytes()
    assert json.loads(before)["started_at"]
    assert claim() is False
    assert (tmp_path / "started.json").read_bytes() == before


@pytest.mark.parametrize("raw,json_valid", [
    ('{"themes":[{"topic_id":[],"stance":"critical"}]}', True),
    ('{"themes":[{"topic_id":{},"stance":"critical"}]}', True),
    ('[]', True), ('null', True), ('not-json', False),
])
def test_summary_keeps_invalid_attempts_without_crashing_or_repair(tmp_path, raw, json_valid):
    root = tmp_path / "run"
    experiment.freeze(root)
    frozen = json.loads((root / "cases.json").read_text())
    case = frozen["cases"][0]
    current = experiment.snapshot(case, frozen["rules"])
    row = {"label": "case-01-1", "case_id": "case-01", "split": "regression",
           "input": current, "snapshot": experiment.digest(current), "seconds": 0.01,
           "raw_output": raw, "gate": experiment.decide(None, experiment.digest(current), current)}
    experiment.write(root / "calls.json", [row])
    summary = summarize(root)["regression"]
    assert summary["attempts"] == 1 and summary["schema_valid"] == 0
    assert summary["json_valid"] == int(json_valid)
    assert summary["matrix"]["should_not_block"]["review_required"] == 1
    assert json.loads((root / "calls.json").read_text()) == [row]
