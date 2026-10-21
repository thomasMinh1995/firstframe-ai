import json

from test_demo import add_review, prohibit_live_work

pytest_plugins = ["test_demo"]


def annotate(client, sample, **changes):
    return client.put(
        f"/api/datasets/samples/{sample['run_id']}/review",
        json={
            **sample["review"],
            "fingerprint": sample["fingerprint"],
            **changes,
        },
    )


def test_review_persists_without_mutating_exports_and_conflicts(demo_exports, monkeypatch):
    client, _, store = demo_exports
    before = {path: path.read_bytes() for path in store.directory.glob("runs/*.json")}
    prohibit_live_work(monkeypatch)
    sample = client.get("/api/datasets/samples").json()[0]
    response = annotate(
        client, sample, status="approved", feedback="Giữ đúng ý tác giả.", use_for_training=True
    )
    assert response.status_code == 200
    assert response.json()["revision"] == 1
    detail = client.get(f"/api/datasets/samples/{sample['run_id']}").json()
    assert detail["review"] == response.json()
    assert detail["recording"]["review_status"] == "unreviewed"
    assert {path: path.read_bytes() for path in before} == before
    assert annotate(client, sample, status="needs_revision").status_code == 409
    assert (
        annotate(client, detail, status="needs_revision", use_for_training=True).status_code == 422
    )
    assert (
        annotate(client, detail, status="needs_revision", use_for_training=False).status_code == 200
    )
    assert client.get("/api/datasets/training.jsonl").text == ""


def test_curated_demo_requires_approved_sources_and_excludes_unselected_review(
    demo_exports, monkeypatch
):
    client, project, _ = demo_exports
    add_review(client, project)
    prohibit_live_work(monkeypatch)
    samples = client.get("/api/datasets/samples").json()
    plan = next(sample for sample in samples if sample["operation"] == "plan")
    assert annotate(client, plan, status="approved", use_for_demo=True).status_code == 200
    assert client.get("/api/demo/scenarios?curated=true").json() == []
    analysis = next(sample for sample in samples if sample["operation"] == "analyze")
    assert annotate(client, analysis, status="approved", use_for_demo=True).status_code == 200
    (scenario,) = client.get("/api/demo/scenarios?curated=true").json()
    assert scenario["step_count"] == 5 and scenario["review_status"] == "approved"
    review = next(sample for sample in samples if sample["operation"] == "review")
    assert annotate(client, review, status="approved", use_for_demo=True).status_code == 200
    (scenario,) = client.get("/api/demo/scenarios?curated=true").json()
    assert scenario["step_count"] == 7
    updated = client.get(f"/api/datasets/samples/{review['run_id']}").json()
    assert annotate(client, updated, status="needs_revision", use_for_demo=False).status_code == 200
    assert client.get(f"/api/demo/scenarios/{scenario['id']}?curated=true").status_code == 404
    assert client.get("/api/demo/scenarios?curated=true").json()[0]["step_count"] == 5


def test_training_only_selected_approved_steps_with_provenance_and_feedback(demo_exports):
    client, _, store = demo_exports
    samples = client.get("/api/datasets/samples").json()
    sample = next(item for item in samples if item["operation"] == "plan")
    assert (
        annotate(
            client, sample, status="approved", use_for_training=True, feedback="Bản plan phù hợp"
        ).status_code
        == 200
    )
    # Rebuilding all automatic exports must not erase annotations.
    store.export()
    response = client.get("/api/datasets/training.jsonl")
    rows = [json.loads(line) for line in response.text.splitlines()]
    assert len(rows) == 4
    source = next(record for record in store.records() if record["run_id"] == sample["run_id"])
    for row, step in zip(rows, source["steps"], strict=True):
        assert row["provider"] == "fake" and row["model"] == "fake-model"
        assert row["project_id"] == source["project_id"]
        assert row["review"]["feedback"] == "Bản plan phù hợp"
        assert row["messages"][0]["content"] == step["request"]["effective_instructions"]
        assert json.loads(row["messages"][2]["content"]) == step["output"]
    assert "attachment" in response.headers["content-disposition"]


def test_changed_content_invalidates_annotation_and_stale_write(demo_exports):
    client, _, store = demo_exports
    sample = client.get("/api/datasets/samples").json()[0]
    assert annotate(client, sample, status="approved", use_for_training=True).status_code == 200
    path = store.directory / "runs" / f"{sample['run_id']}.json"
    record = json.loads(path.read_text())
    record["steps"][0]["request"]["input_text"] += "Changed context"
    path.write_text(json.dumps(record))
    updated = client.get(f"/api/datasets/samples/{sample['run_id']}").json()
    assert updated["review"]["status"] == "unreviewed"
    assert client.get("/api/datasets/training.jsonl").text == ""
    assert annotate(client, sample, status="approved").status_code == 409


def test_failed_and_conflicting_records_cannot_be_selected(demo_exports):
    client, _, store = demo_exports
    sample = client.get("/api/datasets/samples").json()[0]
    path = store.directory / "runs" / f"{sample['run_id']}.json"
    record = json.loads(path.read_text())
    record["status"] = "failed"
    path.write_text(json.dumps(record))
    failed = client.get(f"/api/datasets/samples/{sample['run_id']}").json()
    assert not failed["eligible"]
    assert annotate(client, failed, status="approved").status_code == 422
    assert (
        annotate(client, failed, status="needs_revision", feedback="Model trả lỗi").status_code
        == 200
    )
    record["input"]["idea"] = "Conflicting duplicate"
    (store.directory / "duplicate.json").write_text(json.dumps(record))
    assert client.get(f"/api/datasets/samples/{sample['run_id']}").status_code == 404


def test_embedded_approval_is_not_trusted_and_broken_envelopes_are_skipped(demo_exports):
    client, _, store = demo_exports
    sample = client.get("/api/datasets/samples").json()[0]
    path = store.directory / "runs" / f"{sample['run_id']}.json"
    record = json.loads(path.read_text())
    record["review_status"] = "approved"
    record["human_feedback"] = "Imported approval is not a local human review"
    path.write_text(json.dumps(record))
    detail = client.get(f"/api/datasets/samples/{sample['run_id']}").json()
    assert detail["review"]["status"] == "unreviewed"
    assert client.get("/api/demo/scenarios?curated=true").json() == []
    record["run_id"] = "broken-envelope"
    record["steps"] = ["not a step"]
    (store.directory / "broken.json").write_text(json.dumps(record))
    assert all(
        item["run_id"] != "broken-envelope" for item in client.get("/api/datasets/samples").json()
    )
