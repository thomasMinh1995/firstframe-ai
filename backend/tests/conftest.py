import os

import pytest

# Set before test collection: application modules can call load_dotenv on import.
os.environ["PYTHON_DOTENV_DISABLED"] = "1"


@pytest.fixture(autouse=True)
def local_dataset_directory(tmp_path, monkeypatch):
    """Tests must never put synthetic samples into the user's real dataset."""
    directory = tmp_path / "datasets"
    monkeypatch.setenv("DATASET_DIR", str(directory))
    return directory


@pytest.fixture(autouse=True)
def local_project_directory(tmp_path, monkeypatch, local_dataset_directory):
    """Default project/scene-image stores stay temporary; individual tests may override."""
    from app.api.routes import projects
    from app.application.project_store import ProjectStore

    monkeypatch.setattr(projects, "get_project_store", lambda: ProjectStore(tmp_path / "projects.sqlite3"))
