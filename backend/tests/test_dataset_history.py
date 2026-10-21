import copy
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

from test_dataset_corrections import corrected_plan, detail, save_outputs
from test_dataset_review import annotate
from test_demo import prohibit_live_work

from app.application.dataset_review import ReviewStore

pytest_plugins = ["test_demo"]


def history(client, sample):
    return client.get(f"/api/datasets/samples/{sample['run_id']}/history").json()


def restore(client, sample, version):
    return client.post(
        f"/api/datasets/samples/{sample['run_id']}/restore",
        json={
            "revision": sample["review"]["revision"],
            "fingerprint": sample["fingerprint"],
            "version": version,
        },
    )


def diff(client, sample, before, after):
    return client.get(
        f"/api/datasets/samples/{sample['run_id']}/diff",
        params={"from_version": before, "to_version": after},
    )


def test_history_diff_restore_and_original_are_durable_without_ai(demo_exports, monkeypatch):
    client, _, store = demo_exports
    sample = detail(client, "plan")
    original_files = {path: path.read_bytes() for path in store.directory.glob("runs/*.json")}
    assert history(client, sample)["current_version"] == 0
    assert not ReviewStore().path.exists()
    first = corrected_plan(sample)
    edited = save_outputs(client, sample, {"0": first}).json()
    second = copy.deepcopy(first)
    second["story_plan"]["working_title"]["title"] = "Phiên bản hai"
    edited = save_outputs(client, edited, {"0": second}).json()
    assert (
        annotate(
            client,
            edited,
            status="approved",
            use_for_demo=True,
            use_for_training=True,
            feedback="Góp ý được giữ",
        ).status_code
        == 200
    )
    approved = detail(client, "plan")
    versions = history(client, approved)
    assert [version["version"] for version in versions["versions"]] == [0, 1, 2]
    assert all("corrected_outputs" not in version for version in versions["versions"])
    (change,) = diff(client, sample, 1, 2).json()["changes"]
    assert change == {
        "path": "steps[0].output.story_plan.working_title.title",
        "before_exists": True,
        "after_exists": True,
        "before": "Bản đã biên tập",
        "after": "Phiên bản hai",
    }
    assert diff(client, sample, 1, 1).json()["changes"] == []
    prohibit_live_work(monkeypatch)
    restored = restore(client, approved, 1).json()
    assert restored["corrected_outputs"] == {"0": first}
    assert restored["review"]["status"] == "unreviewed"
    assert restored["review"]["feedback"] == "Góp ý được giữ"
    assert not restored["review"]["use_for_demo"] and not restored["review"]["use_for_training"]
    assert client.get("/api/datasets/training.jsonl").text == ""
    assert history(client, restored)["versions"][-1]["restored_from"] == 1
    assert history(client, restored)["current_version"] == 3
    assert diff(client, sample, 1, 3).json()["changes"] == []
    assert restore(client, approved, 2).status_code == 409
    original = restore(client, restored, 0).json()
    assert original["corrected_outputs"] == {}
    assert history(client, original)["current_version"] == 4
    assert diff(client, sample, 0, 4).json()["changes"] == []
    assert restore(client, original, 2).json()["corrected_outputs"] == {"0": second}
    assert [version["version"] for version in history(client, original)["versions"]] == list(
        range(6)
    )
    assert {path: path.read_bytes() for path in original_files} == original_files


def test_noop_saves_and_review_edits_do_not_create_output_versions(demo_exports):
    client, _, store = demo_exports
    sample = detail(client, "plan")
    edited = save_outputs(client, sample, {"0": corrected_plan(sample)}).json()
    assert save_outputs(client, edited, edited["corrected_outputs"]).status_code == 200
    assert annotate(client, edited, feedback="Góp ý thêm").status_code == 200
    assert history(client, edited)["current_version"] == 1
    store.export()
    assert history(client, edited)["current_version"] == 1
    assert diff(client, edited, 0, 1).json()["changes"]


def test_pre_history_correction_is_preserved_and_restorable(demo_exports):
    client, _, _ = demo_exports
    sample = detail(client, "plan")
    assert annotate(client, sample, feedback="Từ phiên bản cũ").status_code == 200
    legacy = corrected_plan(sample)
    with sqlite3.connect(ReviewStore().path) as connection:
        connection.execute("DROP TABLE output_versions")
        row = connection.execute(
            "SELECT data FROM reviews WHERE run_id=?", (sample["run_id"],)
        ).fetchone()
        data = json.loads(row[0])
        data["corrected_outputs"] = {"0": legacy}
        connection.execute(
            "UPDATE reviews SET data=? WHERE run_id=?", (json.dumps(data), sample["run_id"])
        )
    sample = detail(client, "plan")
    before = ReviewStore().path.read_bytes()
    assert history(client, sample)["versions"][1]["action"] == "imported"
    assert ReviewStore().path.read_bytes() == before
    restored = restore(client, sample, 0).json()
    assert restored["corrected_outputs"] == {}
    assert [item["action"] for item in history(client, restored)["versions"]] == [
        "original",
        "imported",
        "restore",
    ]
    assert restore(client, restored, 1).json()["corrected_outputs"] == {"0": legacy}


def test_diff_additions_removals_nulls_and_fingerprint_isolation(demo_exports):
    client, _, store = demo_exports
    sample = detail(client, "plan")
    output = copy.deepcopy(sample["recording"]["steps"][0]["output"])
    output["story_plan"]["characters"]["supporting_characters"].append("Người hàng xóm")
    output["story_plan"]["ending"]["final_image"] = None
    edited = save_outputs(client, sample, {"0": output}).json()
    changes = diff(client, sample, 0, 1).json()["changes"]
    addition = next(item for item in changes if "supporting_characters" in item["path"])
    assert not addition["before_exists"] and addition["after_exists"]
    null_change = next(item for item in changes if "final_image" in item["path"])
    assert null_change["after_exists"] and null_change["after"] is None
    reverse = diff(client, sample, 1, 0).json()["changes"]
    assert any(not item["after_exists"] for item in reverse)
    assert restore(client, edited, 999).status_code == 404
    assert diff(client, edited, 999, 0).status_code == 404
    assert diff(client, edited, -1, 0).status_code == 422
    assert client.get("/api/datasets/samples/missing/history").status_code == 404
    other = detail(client, "analyze")
    assert restore(client, other, 1).status_code == 404
    path = store.directory / "runs" / f"{sample['run_id']}.json"
    source = json.loads(path.read_text())
    source["steps"][0]["request"]["input_text"] += " changed"
    path.write_text(json.dumps(source))
    assert history(client, edited)["current_version"] == 0
    assert restore(client, edited, 1).status_code == 409
    assert diff(client, edited, 0, 1).status_code == 404


def test_concurrent_edits_create_one_version_and_failed_commit_rolls_back_history(demo_exports):
    client, _, _ = demo_exports
    sample = detail(client, "plan")
    output = corrected_plan(sample)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: save_outputs(client, sample, {"0": output}), range(2)))
    assert sorted(response.status_code for response in responses) == [200, 409]
    assert history(client, sample)["current_version"] == 1
    current = detail(client, "plan")
    with sqlite3.connect(ReviewStore().path) as connection:
        connection.execute(
            "CREATE TRIGGER reject_review BEFORE UPDATE ON reviews BEGIN "
            "SELECT RAISE(ABORT, 'test rollback'); END"
        )
    assert restore(client, current, 0).status_code == 503
    assert history(client, current)["current_version"] == 1
    assert detail(client, "plan")["corrected_outputs"] == {"0": output}
