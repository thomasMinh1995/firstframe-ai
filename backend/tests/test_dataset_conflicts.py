import copy
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

from test_dataset_bundle import encoded, post, receiver
from test_dataset_corrections import corrected_plan, detail, save_outputs
from test_dataset_review import annotate
from test_demo import prohibit_live_work

from app.application.dataset_review import ReviewStore, fingerprint

pytest_plugins = ["test_dataset_bundle"]


def apply(client, raw, choices):
    body = b'{"bundle":' + raw + b',"resolutions":' + json.dumps(choices).encode() + b"}"
    return post(client, "import", body)


def choose(report, choice="incoming"):
    return {
        item["run_id"]: {"choice": choice, "local_token": item["local_token"]}
        for item in report["conflicts"]
    }


def branches(client, sample):
    return client.get(f"/api/datasets/samples/{sample['run_id']}/branches").json()


def restore_branch(client, sample, branch, token):
    return client.post(
        f"/api/datasets/samples/{sample['run_id']}/branches/{branch}/restore",
        json={"local_token": token},
    )


def test_mixed_choices_compare_preserve_branches_and_restore(portable, tmp_path, monkeypatch):
    raw, package, _, _ = portable
    client, _ = receiver(tmp_path, monkeypatch)
    assert post(client, "import", raw).status_code == 200
    analysis = detail(client, "analyze")
    assert annotate(client, analysis, feedback="Giữ góp ý local").status_code == 200
    plan = detail(client, "plan")
    output = corrected_plan(plan)
    output["story_plan"]["working_title"]["title"] = "Bản local muốn giữ trong lịch sử"
    plan = save_outputs(client, plan, {"0": output}).json()
    local_plan = copy.deepcopy(plan)
    local_history = client.get(f"/api/datasets/samples/{plan['run_id']}/history").json()
    prohibit_live_work(monkeypatch)
    report = post(client, "preview", raw).json()
    assert len(report["conflicts"]) == 2
    comparison = client.post(
        f"/api/datasets/bundle/compare?run_id={plan['run_id']}", content=raw
    ).json()
    assert any("corrected_outputs" in item["path"] for item in comparison["changes"])
    choices = choose(report)
    choices[analysis["run_id"]]["choice"] = "local"
    response = apply(client, raw, choices)
    assert response.status_code == 200, response.text
    assert response.json()["kept_local_count"] == response.json()["used_incoming_count"] == 1
    assert detail(client, "analyze")["review"]["feedback"] == "Giữ góp ý local"
    selected = detail(client, "plan")
    original_plan = next(
        entry for entry in package["samples"] if entry["recording"]["operation"] == "plan"
    )
    assert selected["corrected_outputs"] == original_plan["review"]["corrected_outputs"]
    assert selected["review"]["revision"] > local_plan["review"]["revision"]
    stored = branches(client, selected)
    assert len(stored["branches"]) == 2
    local_branch = next(branch for branch in stored["branches"] if branch["source"] == "local")
    assert local_branch["history_count"] == local_history["current_version"]
    result = restore_branch(client, selected, local_branch["branch_id"], stored["local_token"])
    assert result.status_code == 200, result.text
    restored = result.json()
    assert restored["corrected_outputs"] == local_plan["corrected_outputs"]
    assert (
        restored["review"]["status"] == "unreviewed" and not restored["review"]["use_for_training"]
    )
    assert (
        client.get(f"/api/datasets/samples/{plan['run_id']}/history").json()["current_version"]
        == local_history["current_version"] + 1
    )
    assert (
        restore_branch(
            client, selected, local_branch["branch_id"], stored["local_token"]
        ).status_code
        == 409
    )


def test_different_originals_are_not_overwritten_and_archives_are_portable(
    portable, tmp_path, monkeypatch
):
    raw, package, _, _ = portable
    client, directory = receiver(tmp_path, monkeypatch)
    assert post(client, "import", raw).status_code == 200
    before = detail(client, "plan")
    alternate = copy.deepcopy(package)
    entry = next(item for item in alternate["samples"] if item["recording"]["operation"] == "plan")
    entry["recording"]["steps"][0]["request"]["input_text"] += " Different source context"
    entry["fingerprint"] = fingerprint(entry["recording"])
    alternate_raw = encoded(alternate)
    report = post(client, "preview", alternate_raw).json()
    assert report["conflicts"][0]["originals_differ"]
    response = apply(client, alternate_raw, choose(report))
    assert response.status_code == 200, response.text
    selected = detail(client, "plan")
    assert (
        selected["recording"] == entry["recording"]
        and selected["fingerprint"] != before["fingerprint"]
    )
    with sqlite3.connect(directory / "reviews.sqlite3") as connection:
        untouched = json.loads(
            connection.execute(
                "SELECT data FROM imported_samples WHERE run_id=?", (before["run_id"],)
            ).fetchone()[0]
        )
    assert untouched == before["recording"]
    repeated = post(client, "preview", alternate_raw).json()
    assert repeated["conflicts"] == [] and repeated["unchanged_count"] == 3
    assert post(client, "import", alternate_raw).status_code == 200
    assert detail(client, "plan") == selected
    stored = branches(client, selected)
    assert {branch["fingerprint"] for branch in stored["branches"]} == {
        before["fingerprint"],
        selected["fingerprint"],
    }
    exported = client.get("/api/datasets/bundle")
    assert exported.status_code == 200, exported.text
    assert exported.json()["schema_version"] == 2
    exported_plan = next(
        item for item in exported.json()["samples"] if item["recording"]["operation"] == "plan"
    )
    assert len(exported_plan["branches"]) == 2
    # A third machine keeps both branches and can restore the original source.
    monkeypatch.setenv("DATASET_DIR", str(tmp_path / "third-machine"))
    assert post(client, "import", exported.content).status_code == 200
    third = detail(client, "plan")
    saved = branches(client, third)
    assert len(saved["branches"]) == 2
    old = next(
        branch for branch in saved["branches"] if branch["fingerprint"] == before["fingerprint"]
    )
    restored = restore_branch(client, third, old["branch_id"], saved["local_token"])
    assert restored.status_code == 200, restored.text
    assert restored.json()["recording"] == before["recording"]
    assert restored.json()["review"]["revision"] > third["review"]["revision"]


def test_choices_are_required_and_rechecked_after_comparison(portable, tmp_path, monkeypatch):
    raw, _, _, _ = portable
    client, directory = receiver(tmp_path, monkeypatch)
    assert post(client, "import", raw).status_code == 200
    plan = detail(client, "plan")
    assert annotate(client, plan, feedback="First local change").status_code == 200
    report = post(client, "preview", raw).json()
    assert apply(client, raw, {}).status_code == 409
    choices = choose(report)
    plan = detail(client, "plan")
    assert annotate(client, plan, feedback="After comparison").status_code == 200
    snapshot = (directory / "reviews.sqlite3").read_bytes()
    assert apply(client, raw, choices).status_code == 409
    assert (directory / "reviews.sqlite3").read_bytes() == snapshot
    choices["not-in-package"] = {"choice": "incoming", "local_token": "0" * 64}
    assert apply(client, raw, choices).status_code == 409
    assert detail(client, "plan")["review"]["feedback"] == "After comparison"


def test_atomic_failure_does_not_lose_active_history_or_create_archives(
    portable, tmp_path, monkeypatch
):
    raw, _, _, _ = portable
    client, directory = receiver(tmp_path, monkeypatch)
    assert post(client, "import", raw).status_code == 200
    plan = detail(client, "plan")
    plan = save_outputs(
        client, plan, {"0": corrected_plan(plan), "1": plan["recording"]["steps"][1]["output"]}
    ).json()
    # Ensure an actual difference even if the first correction matched the package.
    assert annotate(client, plan, feedback="Local feedback").status_code == 200
    before = detail(client, "plan")
    report = post(client, "preview", raw).json()
    with sqlite3.connect(ReviewStore().path) as connection:
        connection.execute(
            "CREATE TRIGGER reject_switch BEFORE UPDATE ON reviews BEGIN SELECT RAISE(ABORT, 'test'); END"
        )
    assert apply(client, raw, choose(report)).status_code == 503
    assert detail(client, "plan") == before
    with sqlite3.connect(directory / "reviews.sqlite3") as connection:
        assert (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name='dataset_branches'"
            ).fetchone()
            is None
        )


def test_concurrent_choices_do_not_replace_newer_local_state(portable, tmp_path, monkeypatch):
    raw, _, _, _ = portable
    client, _ = receiver(tmp_path, monkeypatch)
    assert post(client, "import", raw).status_code == 200
    plan = detail(client, "plan")
    assert annotate(client, plan, feedback="Local concurrent").status_code == 200
    report = post(client, "preview", raw).json()
    choices = choose(report)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: apply(client, raw, choices), range(2)))
    assert sorted(result.status_code for result in results) == [200, 409]
    assert len(branches(client, plan)["branches"]) == 2


def test_local_json_original_is_preserved_when_incoming_source_is_selected(
    portable, tmp_path, monkeypatch
):
    raw, package, _, _ = portable
    client, _ = receiver(tmp_path, monkeypatch)
    folder = tmp_path / "no-files"
    folder.mkdir()
    local = copy.deepcopy(
        next(
            item["recording"]
            for item in package["samples"]
            if item["recording"]["operation"] == "plan"
        )
    )
    local["steps"][0]["request"]["input_text"] += " local original file"
    path = folder / "local-plan.json"
    path.write_text(json.dumps(local, ensure_ascii=False))
    original_bytes = path.read_bytes()
    sample = detail(client, "plan")
    assert annotate(client, sample, feedback="Local annotation").status_code == 200
    report = post(client, "preview", raw).json()
    assert report["conflicts"][0]["originals_differ"]
    assert apply(client, raw, choose(report)).status_code == 200
    assert path.read_bytes() == original_bytes
    assert detail(client, "plan")["recording"] != local
    assert any(
        branch["fingerprint"] == fingerprint(local)
        for branch in branches(client, sample)["branches"]
    )


def test_package_branch_tampering_is_rejected(portable, tmp_path, monkeypatch):
    raw, _, _, _ = portable
    client, _ = receiver(tmp_path, monkeypatch)
    assert post(client, "import", raw).status_code == 200
    sample = detail(client, "plan")
    assert annotate(client, sample, feedback="Different local review").status_code == 200
    report = post(client, "preview", raw).json()
    assert apply(client, raw, choose(report)).status_code == 200
    package = client.get("/api/datasets/bundle").json()
    assert package["schema_version"] == 2
    entry = next(item for item in package["samples"] if item.get("branches"))
    entry["branches"][0]["branch_id"] = "0" * 64
    assert post(client, "preview", encoded(package)).status_code == 422
