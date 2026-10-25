import copy
import json

from test_dataset_review import annotate
from test_demo import prohibit_live_work

pytest_plugins = ["test_demo"]


def save_outputs(client, sample, outputs):
    return client.put(
        f"/api/datasets/samples/{sample['run_id']}/output",
        json={
            "revision": sample["review"]["revision"],
            "fingerprint": sample["fingerprint"],
            "corrected_outputs": outputs,
        },
    )


def detail(client, operation):
    sample = next(
        item
        for item in client.get("/api/datasets/samples").json()
        if item["operation"] == operation
    )
    return client.get(f"/api/datasets/samples/{sample['run_id']}").json()


def corrected_plan(sample):
    output = copy.deepcopy(sample["recording"]["steps"][0]["output"])
    output["story_plan"]["working_title"]["title"] = "Bản đã biên tập"
    output["story_plan"]["ending"]["resolution"] = "Mẹ úp chiếc bát thứ hai xuống."
    return output


def test_corrections_keep_original_reset_approval_and_export_human_target(
    demo_exports, monkeypatch
):
    client, _, store = demo_exports
    sample = detail(client, "plan")
    assert (
        annotate(
            client, sample, status="approved", use_for_demo=True, use_for_training=True
        ).status_code
        == 200
    )
    sample = detail(client, "plan")
    before = {path: path.read_bytes() for path in store.directory.glob("runs/*.json")}
    prohibit_live_work(monkeypatch)
    output = corrected_plan(sample)
    response = save_outputs(client, sample, {"0": output})
    assert response.status_code == 200
    updated = response.json()
    assert updated["review"]["status"] == "unreviewed"
    assert not updated["review"]["use_for_demo"] and not updated["review"]["use_for_training"]
    assert updated["recording"] == sample["recording"]
    assert updated["corrected_outputs"] == {"0": output}
    assert {path: path.read_bytes() for path in before} == before
    assert client.get("/api/datasets/training.jsonl").text == ""
    assert annotate(client, updated, status="approved", use_for_training=True).status_code == 200
    (row,) = [
        json.loads(line) for line in client.get("/api/datasets/training.jsonl").text.splitlines()
    ]
    assert row["output_source"] == "human_corrected"
    assert row["original_output"] == sample["recording"]["steps"][0]["output"]
    assert row["corrected_output"] == output
    assert json.loads(row["messages"][2]["content"]) == output
    assert row["messages"][1]["content"] == sample["recording"]["steps"][0]["request"]["input_text"]
    assert row["provider"] == "fake" and row["model"] == "fake-model"
    assert save_outputs(client, sample, {}).status_code == 409


def test_demo_uses_only_approved_edits_and_hides_stale_feedback(demo_exports):
    client, _, _ = demo_exports
    plan = detail(client, "plan")
    changed = save_outputs(client, plan, {"0": corrected_plan(plan)}).json()
    summary = client.get("/api/demo/scenarios").json()[0]
    original = client.get(f"/api/demo/scenarios/{summary['id']}").json()
    assert original["steps"][3]["draft"]["title"] != "Bản đã biên tập"
    assert annotate(client, changed, status="approved", use_for_demo=True).status_code == 200
    analysis = detail(client, "analyze")
    assert annotate(client, analysis, status="approved", use_for_demo=True).status_code == 200
    summary = client.get("/api/demo/scenarios?curated=true").json()[0]
    scenario = client.get(f"/api/demo/scenarios/{summary['id']}?curated=true").json()
    assert scenario["steps"][3]["draft"]["title"] == "Bản đã biên tập"
    assert "Mẹ úp chiếc bát" in str(scenario["steps"][3]["draft"])
    assert scenario["steps"][4]["feedback"] is None
    assert "ẩn" in scenario["steps"][4]["description"]


def test_reasoning_and_evaluation_edits_replay_and_survive_reexport(demo_exports):
    client, _, store = demo_exports
    analysis = detail(client, "analyze")
    output = copy.deepcopy(analysis["recording"]["steps"][0]["output"])
    output["summary"] = "Phân tích đã được người sửa."
    output["notes"] = [{"label": "Điều cần giữ", "content": "Giữ kết mở"}]
    edited = save_outputs(client, analysis, {"0": output}).json()
    assert annotate(client, edited, status="approved", use_for_demo=True).status_code == 200
    plan = detail(client, "plan")
    feedback = copy.deepcopy(plan["recording"]["steps"][1]["output"])
    feedback["reviews"][0].update(comparison="mismatch", suggestion="Góp ý đã chỉnh")
    edited = save_outputs(client, plan, {"1": feedback}).json()
    assert (
        annotate(
            client, edited, status="approved", use_for_demo=True, use_for_training=True
        ).status_code
        == 200
    )
    store.export()
    summary = client.get("/api/demo/scenarios?curated=true").json()[0]
    scenario = client.get(f"/api/demo/scenarios/{summary['id']}?curated=true").json()
    assert scenario["steps"][1]["analysis"]["summary"] == output["summary"]
    assert any(
        note["content"] == "Giữ kết mở" for note in scenario["steps"][1]["analysis"]["notes"]
    )
    assert any(
        item["message"].endswith("Góp ý đã chỉnh") for item in scenario["steps"][4]["feedback"]["findings"]
    )
    rows = [
        json.loads(line) for line in client.get("/api/datasets/training.jsonl").text.splitlines()
    ]
    assert [row["output_source"] for row in rows] == ["model", "human_corrected"]


def test_invalid_edits_restoration_and_stale_fingerprints(demo_exports):
    client, _, store = demo_exports
    sample = detail(client, "plan")
    for edits in [{"99": {}}, {"-1": {}}, {"00": {}}, {"0": {"wrong": "shape"}}]:
        assert save_outputs(client, sample, edits).status_code == 422
    feedback = copy.deepcopy(sample["recording"]["steps"][1]["output"])
    feedback["reviews"][0]["card_id"] = "invented-card"
    assert save_outputs(client, sample, {"1": feedback}).status_code == 422
    edited = save_outputs(client, sample, {"0": corrected_plan(sample)}).json()
    assert annotate(client, edited, status="approved", use_for_training=True).status_code == 200
    approved = detail(client, "plan")
    unchanged = save_outputs(client, approved, approved["corrected_outputs"]).json()
    assert unchanged["review"] == approved["review"]
    restored = save_outputs(client, approved, {}).json()
    assert restored["corrected_outputs"] == {} and restored["review"]["status"] == "unreviewed"
    path = store.directory / "runs" / f"{sample['run_id']}.json"
    original = json.loads(path.read_text())
    original["steps"][0]["request"]["input_text"] += " changed"
    path.write_text(json.dumps(original))
    assert save_outputs(client, restored, {}).status_code == 409
    assert detail(client, "plan")["corrected_outputs"] == {}


def test_legacy_generate_and_review_rounds_support_editorial_outputs(demo_exports):
    from test_demo import add_review

    client, project, _ = demo_exports
    add_review(client, project)
    sample = detail(client, "review")
    evaluation = copy.deepcopy(sample["recording"]["steps"][0]["output"])
    evaluation["reviews"][0]["observation"] = "Phản hồi lượt sửa đã được biên tập"
    invented = copy.deepcopy(evaluation)
    invented["reviews"][0]["card_id"] = "invented-card"
    assert save_outputs(client, sample, {"0": invented}).status_code == 422
    scored = copy.deepcopy(evaluation)
    scored["rubric_scores"] = dict.fromkeys(["story_clarity", "character", "conflict", "emotional_impact",
                                          "ending", "production_feasibility"], 4)
    assert save_outputs(client, sample, {"0": scored}).status_code == 422
    edited = save_outputs(client, sample, {"0": evaluation}).json()
    assert annotate(client, edited, status="approved").status_code == 200
    response = client.post("/api/generate", json={"idea": "A mother waits by the window."})
    assert response.status_code == 200
    sample = detail(client, "generate")
    output = copy.deepcopy(sample["recording"]["steps"][1]["output"])
    output["story_plan"]["working_title"]["title"] = "Legacy đã sửa"
    edited = save_outputs(client, sample, {"1": output}).json()
    assert annotate(client, edited, status="approved", use_for_training=True).status_code == 200
    summaries = client.get("/api/demo/scenarios").json()
    legacy = next(item for item in summaries if item["title"] == "Legacy đã sửa")
    assert legacy["step_count"] == 5
    project_summary = next(item for item in summaries if item["id"] != legacy["id"])
    scenario = client.get(f"/api/demo/scenarios/{project_summary['id']}").json()
    assert any(
        evaluation["reviews"][0]["observation"] in item["message"]
        for item in scenario["steps"][-1]["feedback"]["findings"]
    )
    rows = [
        json.loads(line) for line in client.get("/api/datasets/training.jsonl").text.splitlines()
    ]
    assert [row["stage"] for row in rows] == ["reasoning", "planning"]
