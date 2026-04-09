import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "skipif_fastembed_unavailable: skip if fastembed is not installed"
    )


def pytest_collection_modifyitems(config, items):
    try:
        import fastembed  # noqa: F401

        available = True
    except ImportError:
        available = False
    if not available:
        skip = pytest.mark.skip(reason="fastembed not available")
        for item in items:
            if "skipif_fastembed_unavailable" in item.keywords:
                item.add_marker(skip)


@pytest.fixture
def run_cli(tmp_path, monkeypatch):
    """Run memory_cli.py with HOME redirected to tmp_path."""
    monkeypatch.setenv("HOME", str(tmp_path))

    def _run(*args: str):
        return subprocess.run(
            ["uv", "run", str(SCRIPTS / "memory_cli.py"), *args],
            capture_output=True,
            text=True,
            env={**os.environ, "HOME": str(tmp_path)},
        )

    return _run
