import copy
import json

import pytest
from test_dataset_bundle import encoded, post, receiver
from test_dataset_conflicts import apply, branches, choose, restore_branch
from test_dataset_corrections import corrected_plan, detail, save_outputs
from test_dataset_history import restore
from test_dataset_review import annotate

from app.application.dataset_branches import (
    ConflictChoice,
)
from app.application.dataset_branches import (
    restore_branch as restore_stored_branch,
)
from app.application.dataset_bundle import import_bundle, validate_bundle
from app.application.dataset_review import ReviewStore, fingerprint

pytest_plugins = ["test_dataset_bundle"]


@pytest.mark.parametrize("switch", ["import", "restore"])
@pytest.mark.parametrize("action", ["output", "review", "restore"])
def test_source_switch_during_save_rejects_stale_write_and_preserves_history(
    portable, tmp_path, monkeypatch, switch, action
):
    raw, package, _, _ = portable
    client, directory = receiver(tmp_path, monkeypatch)
    assert post(client, "import", raw).status_code == 200
    alternate = copy.deepcopy(package)
    entry = next(item for item in alternate["samples"] if item["recording"]["operation"] == "plan")
    entry["recording"]["steps"][0]["request"]["input_text"] += " Different source context"
    entry["fingerprint"] = fingerprint(entry["recording"])
    alternate_raw = encoded(alternate)
    if switch == "restore":
        report = post(client, "preview", alternate_raw).json()
        assert apply(client, alternate_raw, choose(report)).status_code == 200

    before = detail(client, "plan")
    saved_output = corrected_plan(before)
    saved_output["story_plan"]["working_title"]["title"] = "Saved before switching source"
    before = save_outputs(client, before, {"0": saved_output}).json()
    old_history = client.get(f"/api/datasets/samples/{before['run_id']}/history").json()
    if switch == "import":
        report = post(client, "preview", alternate_raw).json()
        choices = {
            key: ConflictChoice.model_validate(value) for key, value in choose(report).items()
        }
        bundle = validate_bundle(json.loads(alternate_raw))

        def switch_source():
            import_bundle(bundle, choices)
    else:
        saved = branches(client, before)
        target = next(
            item for item in saved["branches"] if item["fingerprint"] != before["fingerprint"]
        )

        def switch_source():
            restore_stored_branch(before["run_id"], target["branch_id"], saved["local_token"])

    real_save = ReviewStore.save
    snapshot = None

    def switch_then_save(self, run_id, update, **kwargs):
        nonlocal snapshot
        # Force the switch after the route validates its source, before the write lock.
        switch_source()
        snapshot = (directory / "reviews.sqlite3").read_bytes()
        return real_save(self, run_id, update, **kwargs)

    monkeypatch.setattr(ReviewStore, "save", switch_then_save)
    if action == "output":
        wanted = copy.deepcopy(saved_output)
        wanted["story_plan"]["working_title"]["title"] = "Stale edit must not be saved"
        response = save_outputs(client, before, {"0": wanted})
    elif action == "review":
        response = annotate(client, before, feedback="Stale feedback must not be saved")
    else:
        response = restore(client, before, 0)
    assert response.status_code == 409, response.text
    assert (directory / "reviews.sqlite3").read_bytes() == snapshot
    monkeypatch.setattr(ReviewStore, "save", real_save)

    current = detail(client, "plan")
    assert current["fingerprint"] != before["fingerprint"]
    saved = branches(client, current)
    old = next(
        item
        for item in saved["branches"]
        if item["fingerprint"] == before["fingerprint"]
        and item["history_count"] == old_history["current_version"]
    )
    restored = restore_branch(client, current, old["branch_id"], saved["local_token"])
    assert restored.status_code == 200, restored.text
    assert restored.json()["recording"] == before["recording"]
    assert restored.json()["corrected_outputs"] == {"0": saved_output}
    history = ReviewStore().history(before["run_id"], before["fingerprint"])
    assert history[-2].version == old_history["current_version"]
    assert history[-2].corrected_outputs == {"0": saved_output}
    # Retrying after reload is safe and creates a visible, recoverable version.
    wanted = copy.deepcopy(saved_output)
    wanted["story_plan"]["working_title"]["title"] = "Edit retried after reload"
    retry = save_outputs(client, restored.json(), {"0": wanted})
    assert retry.status_code == 200, retry.text
    assert retry.json()["corrected_outputs"] == {"0": wanted}


def test_history_beyond_1000_survives_edits_restores_and_portable_archives(
    portable, tmp_path, monkeypatch
):
    _, package, _, _ = portable
    entry = next(item for item in package["samples"] if item["recording"]["operation"] == "plan")
    last = entry["history"][-1]
    entry["history"] = [entry["history"][0]] + [
        {**copy.deepcopy(last), "version": index, "action": "edit", "restored_from": None}
        for index in range(1, 1000)
    ]
    raw = encoded(package)
    client, _ = receiver(tmp_path, monkeypatch)
    assert post(client, "import", raw).status_code == 200
    sample = detail(client, "plan")
    output = corrected_plan(sample)
    output["story_plan"]["working_title"]["title"] = "Version 1000"
    response = save_outputs(client, sample, {"0": output})
    assert response.status_code == 200, response.text
    response = restore(client, response.json(), 1)
    assert response.status_code == 200, response.text
    assert annotate(client, response.json(), status="approved").status_code == 200
    history = ReviewStore().history(sample["run_id"], sample["fingerprint"])
    assert len(history) == 1002
    assert history[1000].corrected_outputs == {"0": output}
    assert history[1001].restored_from == 1
    assert branches(client, sample)["branches"] == []
    exported = client.get("/api/datasets/bundle")
    assert exported.status_code == 200, exported.text
    exported_entry = next(
        item for item in exported.json()["samples"] if item["recording"]["operation"] == "plan"
    )
    assert exported_entry["history"] == [version.model_dump() for version in history]

    report = post(client, "preview", raw).json()
    assert apply(client, raw, choose(report)).status_code == 200
    saved = branches(client, sample)
    target = next(item for item in saved["branches"] if item["history_count"] == 1001)
    response = restore_branch(client, sample, target["branch_id"], saved["local_token"])
    assert response.status_code == 200, response.text
    assert annotate(client, response.json(), status="approved").status_code == 200
    exported = client.get("/api/datasets/bundle")
    assert exported.status_code == 200, exported.text
    assert exported.json()["schema_version"] == 2
    expected = next(
        item for item in exported.json()["samples"] if item["recording"]["operation"] == "plan"
    )
    assert len(expected["history"]) == 1003
    assert any(len(branch["history"]) == 1002 for branch in expected["branches"])

    monkeypatch.setenv("DATASET_DIR", str(tmp_path / "third-machine"))
    assert post(client, "import", exported.content).status_code == 200
    again = client.get("/api/datasets/bundle")
    assert again.status_code == 200, again.text
    received = next(
        item for item in again.json()["samples"] if item["recording"]["operation"] == "plan"
    )
    assert received == expected
    saved = branches(client, sample)
    target = next(item for item in saved["branches"] if item["history_count"] == 1001)
    response = restore_branch(client, sample, target["branch_id"], saved["local_token"])
    assert response.status_code == 200, response.text
    assert len(ReviewStore().history(sample["run_id"], sample["fingerprint"])) == 1003
