import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(ROOT))


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
