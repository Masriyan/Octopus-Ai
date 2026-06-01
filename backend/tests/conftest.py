import os
import sys
from pathlib import Path

import pytest

# Add the backend directory to the Python path for testing
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


@pytest.fixture(autouse=True)
def _isolated_workspace(tmp_path, monkeypatch):
    """Point the sandboxed File/Shell workspace at each test's tmp_path so the
    workspace jail allows the test's temp files."""
    monkeypatch.setenv("OCTOPUS_WORKSPACE_DIR", str(tmp_path))
    yield
