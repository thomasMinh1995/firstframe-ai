import json
import sys

from test_generate_workflow import FakeProvider

from app.api.schemas.projects import ProjectResponse
from scripts import check_creative_choices


def test_runner_defers_choices_without_modifying_source_project(tmp_path, monkeypatch):
    source = tmp_path / "project.json"
    original = ProjectResponse(id="test", updated_at="2026-10-21", title="Workshop",
                               idea="Một người hướng dẫn giúp người mới làm gốm.").model_dump_json()
    source.write_text(original)
    output = tmp_path / "results.json"
    provider = FakeProvider()
    provider.steps = []
    monkeypatch.setattr(check_creative_choices, "ObservedProvider", lambda model: provider)
    monkeypatch.setattr(sys, "argv", ["check_creative_choices", "--project-json", str(source),
                                     "--output", str(output), "--models", "fake"])
    assert check_creative_choices.main() == 0
    assert source.read_text() == original
    assert json.loads(output.read_text())[0]["status"] == "completed"
    plan_request = next(r for r in provider.requests if r.stage == "planning")
    assert "Chưa quyết định" in plan_request.input_text
    assert "gợi ý của AI" in plan_request.input_text
