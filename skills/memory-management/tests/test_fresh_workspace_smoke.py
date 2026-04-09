import json
import os
import stat
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
LAUNCHER = SCRIPTS / "run_memory_cli.py"


def _write_fake_uv(bin_dir: Path) -> Path:
    uv_path = bin_dir / "uv"
    uv_path.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
workspace_root = Path(args[3])
memory_dir = workspace_root / ".superpowers" / "pyramid-memory"
uv_cache_dir = Path(os.environ["UV_CACHE_DIR"])

memory_dir.mkdir(parents=True, exist_ok=True)
uv_cache_dir.mkdir(parents=True, exist_ok=True)
(memory_dir / "config.toml").write_text("project = \\"demo\\"\\n")
(memory_dir / "data.cozo").write_text("")

manifest = {
    "argv": args,
    "cwd": os.getcwd(),
    "uv_cache_dir": os.environ.get("UV_CACHE_DIR"),
    "uv_index_url": os.environ.get("UV_INDEX_URL"),
    "uv_index_strategy": os.environ.get("UV_INDEX_STRATEGY"),
    "home": os.environ.get("HOME"),
}
(workspace_root / ".superpowers" / "launcher-smoke.json").write_text(json.dumps(manifest))
"""
    )
    uv_path.chmod(uv_path.stat().st_mode | stat.S_IXUSR)
    return uv_path


def test_fresh_workspace_launcher_uses_workspace_local_runtime(tmp_path):
    workspace = tmp_path / "workspace"
    nested = workspace / "src" / "feature"
    fake_home = tmp_path / "home"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_home.mkdir()
    (workspace / ".git").mkdir(parents=True)
    nested.mkdir(parents=True)
    _write_fake_uv(fake_bin)

    env = dict(os.environ)
    env.pop("UV_INDEX_URL", None)
    env.pop("UV_INDEX_STRATEGY", None)
    env.pop("UV_CACHE_DIR", None)
    env.update(
        {
            "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
            "HOME": str(fake_home),
        }
    )
    result = subprocess.run(
        [
            sys.executable,
            str(LAUNCHER),
            "init",
            "--project",
            "demo",
            "--embedding",
            "skip",
            "--non-interactive",
        ],
        cwd=nested,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    memory_dir = workspace / ".superpowers" / "pyramid-memory"
    uv_cache_dir = workspace / ".superpowers" / "uv-cache"
    manifest = json.loads((workspace / ".superpowers" / "launcher-smoke.json").read_text())

    assert (memory_dir / "config.toml").exists()
    assert (memory_dir / "data.cozo").exists()
    assert uv_cache_dir.exists()
    assert manifest["argv"][0] == "run"
    assert Path(manifest["argv"][1]).name == "memory_cli.py"
    assert manifest["argv"][2] == "--workspace-root"
    assert Path(manifest["argv"][3]) == workspace.resolve()
    assert manifest["cwd"] == str(nested.resolve())
    assert manifest["uv_cache_dir"] == str(uv_cache_dir.resolve())
    assert manifest["uv_index_url"] == "https://pypi.tuna.tsinghua.edu.cn/simple"
    assert manifest["uv_index_strategy"] == "unsafe-best-match"
    assert manifest["home"] == str(fake_home)
    assert not (fake_home / ".pyramid-memory").exists()
