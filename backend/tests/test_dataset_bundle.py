import copy
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient
from test_dataset_corrections import corrected_plan, detail, save_outputs
from test_dataset_history import restore
from test_dataset_review import annotate
from test_demo import add_review, prohibit_live_work

from app.application.dataset_bundle import checksum
from app.application.dataset_review import ReviewStore, ReviewUpdate, fingerprint
from app.main import create_app

pytest_plugins = ["test_demo"]


def approve_all(client):
    for sample in client.get("/api/datasets/samples").json():
        assert (
            annotate(
                client,
                sample,
                status="approved",
                feedback="Đã duyệt; giữ kết mở.",
                use_for_demo=True,
                use_for_training=True,
            ).status_code
            == 200
        )


@pytest.fixture
def portable(demo_exports):
    client, project, store = demo_exports
    add_review(client, project)
    sample = detail(client, "plan")
    output = corrected_plan(sample)
    sample = save_outputs(client, sample, {"0": output}).json()
    output = copy.deepcopy(output)
    output["story_plan"]["working_title"]["title"] = "Bản thứ hai"
    sample = save_outputs(client, sample, {"0": output}).json()
    assert restore(client, sample, 1).status_code == 200
    approve_all(client)
    response = client.get("/api/datasets/bundle")
    assert response.status_code == 200, response.text
    assert "attachment" in response.headers["content-disposition"]
    scenario = client.get("/api/demo/scenarios?curated=true").json()[0]
    scenario = client.get(f"/api/demo/scenarios/{scenario['id']}?curated=true").json()
    return response.content, response.json(), scenario, store


def receiver(tmp_path, monkeypatch):
    directory = tmp_path / "receiving"
    monkeypatch.setenv("DATASET_DIR", str(directory))
    monkeypatch.setenv("DEMO_DATASET_DIR", str(tmp_path / "no-files"))
    return TestClient(create_app()), directory


def post(client, operation, data):
    return client.post(
        f"/api/datasets/bundle/{operation}",
        content=data,
        headers={"Content-Type": "application/json"},
    )


def encoded(value):
    value["sha256"] = checksum(value)
    return json.dumps(value, ensure_ascii=False).encode()


def test_round_trip_approved_reviews_history_and_demo_without_providers(
    portable, tmp_path, monkeypatch
):
    raw, package, expected_scenario, source = portable
    source_files = {
        path: path.read_bytes() for path in source.directory.rglob("*") if path.is_file()
    }
    client, directory = receiver(tmp_path, monkeypatch)
    prohibit_live_work(monkeypatch)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AI_PROVIDER", "disabled-for-portability-test")
    response = post(client, "preview", raw)
    assert response.status_code == 200, response.text
    assert response.json()["new_count"] == 3
    assert response.json()["history_count"] == 3
    assert response.json()["demo_count"] == 1
    assert not directory.exists()
    imported = post(client, "import", raw)
    assert imported.status_code == 200, imported.text
    assert imported.json()["conflicts"] == []
    assert [path.name for path in directory.iterdir()] == ["reviews.sqlite3"]
    assert len(client.get("/api/datasets/samples").json()) == 3
    (scenario,) = client.get("/api/demo/scenarios?curated=true").json()
    assert (
        client.get(f"/api/demo/scenarios/{scenario['id']}?curated=true").json() == expected_scenario
    )
    for entry in package["samples"]:
        run_id = entry["recording"]["run_id"]
        sample = client.get(f"/api/datasets/samples/{run_id}").json()
        assert sample["recording"] == entry["recording"]
        assert sample["review"]["feedback"] == entry["review"]["feedback"]
        assert sample["corrected_outputs"] == entry["review"]["corrected_outputs"]
        history = client.get(f"/api/datasets/samples/{run_id}/history").json()
        assert history["current_version"] == entry["history"][-1]["version"]
    rows = [
        json.loads(line) for line in client.get("/api/datasets/training.jsonl").text.splitlines()
    ]
    assert any(row["output_source"] == "human_corrected" for row in rows)
    exported = client.get("/api/datasets/bundle").json()
    assert exported["samples"] == package["samples"]
    duplicate = post(client, "import", raw)
    assert duplicate.status_code == 200
    assert duplicate.json()["new_count"] == 0 and duplicate.json()["unchanged_count"] == 3
    assert client.get("/api/datasets/bundle").json()["samples"] == package["samples"]
    assert {path: path.read_bytes() for path in source_files} == source_files
    plan = detail(client, "plan")
    restored = restore(client, plan, 2)
    assert restored.status_code == 200
    assert restored.json()["review"]["status"] == "unreviewed"
    assert (
        client.get(f"/api/datasets/samples/{plan['run_id']}/history").json()["current_version"] == 4
    )


def test_only_approved_samples_are_exported_and_missing_dependencies_are_reported(demo_exports):
    client, _, _ = demo_exports
    assert client.get("/api/datasets/bundle").status_code == 422
    sample = detail(client, "plan")
    assert annotate(client, sample, status="approved", use_for_demo=True).status_code == 200
    response = client.get("/api/datasets/bundle")
    assert response.status_code == 200
    assert len(response.json()["samples"]) == 1
    preview = post(client, "preview", response.content).json()
    assert preview["demo_count"] == 0 and preview["unchanged_count"] == 1


def test_invalid_packages_do_not_write(portable, tmp_path, monkeypatch):
    raw, package, _, _ = portable
    client, directory = receiver(tmp_path, monkeypatch)
    mutations = []
    bad = copy.deepcopy(package)
    bad["schema_version"] = 99
    mutations.append(encoded(bad))
    bad = copy.deepcopy(package)
    bad["samples"].append(copy.deepcopy(bad["samples"][0]))
    mutations.append(encoded(bad))
    bad = copy.deepcopy(package)
    bad["samples"][0]["review"]["status"] = "unreviewed"
    mutations.append(encoded(bad))
    bad = copy.deepcopy(package)
    bad["samples"][0]["fingerprint"] = "0" * 64
    mutations.append(encoded(bad))
    bad = copy.deepcopy(package)
    bad["samples"][0]["review"]["feedback"] = "tampered"
    mutations.append(json.dumps(bad).encode())
    plan_index = next(
        i for i, entry in enumerate(package["samples"]) if entry["recording"]["operation"] == "plan"
    )
    bad = copy.deepcopy(package)
    bad["samples"][plan_index]["history"][-1]["restored_from"] = 999
    mutations.append(encoded(bad))
    bad = copy.deepcopy(package)
    bad["samples"][plan_index]["history"][-1]["version"] = 9
    mutations.append(encoded(bad))
    bad = copy.deepcopy(package)
    bad["samples"][plan_index]["review"]["corrected_outputs"] = {}
    mutations.append(encoded(bad))
    bad = copy.deepcopy(package)
    bad["samples"][plan_index]["history"][1]["corrected_outputs"] = {"0": {"wrong": True}}
    mutations.append(encoded(bad))
    bad = copy.deepcopy(package)
    bad["samples"][0]["recording"]["status"] = "failed"
    bad["samples"][0]["fingerprint"] = fingerprint(bad["samples"][0]["recording"])
    mutations.append(encoded(bad))
    mutations.extend([b"not json", b"[]"])
    for data in mutations:
        response = post(client, "import", data)
        assert response.status_code == 422, response.text
        assert not directory.exists()
    monkeypatch.setattr("app.api.routes.dataset_transfer.MAX_BUNDLE_BYTES", 100)
    assert post(client, "preview", raw).status_code == 413
    assert not directory.exists()


def test_conflicts_preserve_local_data_and_reject_entire_package(portable, tmp_path, monkeypatch):
    raw, package, _, _ = portable
    client, directory = receiver(tmp_path, monkeypatch)
    assert post(client, "import", raw).status_code == 200
    plan = detail(client, "plan")
    assert annotate(client, plan, feedback="Local feedback must win").status_code == 200
    before = (directory / "reviews.sqlite3").read_bytes()
    updated = copy.deepcopy(package)
    extra = copy.deepcopy(
        next(entry for entry in package["samples"] if entry["recording"]["operation"] == "analyze")
    )
    extra["recording"]["run_id"] = "additional-approved-id"

    extra["fingerprint"] = fingerprint(extra["recording"])
    updated["samples"].append(extra)
    report = post(client, "preview", encoded(updated)).json()
    assert report["new_count"] == 1 and len(report["conflicts"]) == 1
    assert post(client, "import", encoded(updated)).status_code == 409
    assert (directory / "reviews.sqlite3").read_bytes() == before
    assert client.get("/api/datasets/samples/additional-approved-id").status_code == 404


def test_storage_failure_rolls_back_records_reviews_and_history(portable, tmp_path, monkeypatch):
    raw, _, _, _ = portable
    client, _directory = receiver(tmp_path, monkeypatch)

    ReviewStore().save("unrelated", ReviewUpdate(fingerprint="0" * 64))
    with sqlite3.connect(ReviewStore().path) as connection:
        connection.execute(
            "CREATE TRIGGER reject_bundle BEFORE INSERT ON reviews WHEN NEW.run_id != 'unrelated' BEGIN SELECT RAISE(ABORT, 'test'); END"
        )
    assert post(client, "import", raw).status_code == 503
    assert client.get("/api/datasets/samples").json() == []
    with sqlite3.connect(ReviewStore().path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM output_versions").fetchone()[0] == 0
        assert (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name='imported_samples'"
            ).fetchone()
            is None
        )


def test_raw_content_conflicts_and_concurrent_duplicate_imports(portable, tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    raw, package, _, _ = portable
    client, directory = receiver(tmp_path, monkeypatch)
    local = tmp_path / "no-files"
    local.mkdir()
    sample = copy.deepcopy(package["samples"][0]["recording"])
    sample["input"]["idea"] = "Different local source"
    path = local / "original.json"
    path.write_text(json.dumps(sample))
    assert post(client, "preview", raw).json()["conflicts"]
    assert post(client, "import", raw).status_code == 409
    assert not directory.exists()
    path.unlink()
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: post(client, "import", raw), range(2)))
    assert [response.status_code for response in responses] == [200, 200]
    assert sorted(response.json()["new_count"] for response in responses) == [0, 3]
    assert len(client.get("/api/datasets/samples").json()) == 3


def test_preview_is_rechecked_and_does_not_overwrite_later_review(portable, tmp_path, monkeypatch):
    raw, _, _, _ = portable
    client, _directory = receiver(tmp_path, monkeypatch)
    assert post(client, "import", raw).status_code == 200
    assert not post(client, "preview", raw).json()["conflicts"]
    sample = detail(client, "plan")
    assert annotate(client, sample, feedback="Changed after preview").status_code == 200
    assert post(client, "import", raw).status_code == 409
    assert detail(client, "plan")["review"]["feedback"] == "Changed after preview"
