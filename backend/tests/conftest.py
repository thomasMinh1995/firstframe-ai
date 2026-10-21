import pytest


@pytest.fixture(autouse=True)
def local_dataset_directory(tmp_path, monkeypatch):
    """Tests must never put synthetic samples into the user's real dataset."""
    directory = tmp_path / "datasets"
    monkeypatch.setenv("DATASET_DIR", str(directory))
    return directory
