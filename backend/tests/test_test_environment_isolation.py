"""Exercise pytest startup against fake env files, never the repository's env."""
import os
from pathlib import Path
import shutil
import subprocess
import sys


def test_pytest_disables_dotenv_before_collection_and_isolates_sqlite(tmp_path):
    suite = tmp_path / "suite"
    suite.mkdir()
    shutil.copyfile(Path(__file__).with_name("conftest.py"), suite / "conftest.py")
    (suite / ".env").write_text("FIRSTFRAME_TEST_ENV_SENTINEL=loaded-from-file\n")
    (suite / "test_probe.py").write_text('''
import os
from pathlib import Path
from dotenv import load_dotenv

# Simulate a module loading dotenv during collection, before autouse fixtures.
load_dotenv(Path(__file__).with_name(".env"))

def test_dotenv_was_disabled_before_collection():
    assert "FIRSTFRAME_TEST_ENV_SENTINEL" not in os.environ

def test_project_and_dataset_storage_are_temporary(tmp_path):
    from app.api.routes.projects import get_project_store
    from app.application.dataset import get_dataset_store
    store = get_project_store()
    assert store.path.parent == tmp_path
    assert get_dataset_store().directory == tmp_path / "datasets"
    assert store.list() == []
    assert store.path.is_file()
''')
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "--confcutdir", str(suite), "--basetemp", str(tmp_path / "pytest"), str(suite)],
        cwd=suite,
        env={"PATH": os.environ["PATH"], "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
             "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
