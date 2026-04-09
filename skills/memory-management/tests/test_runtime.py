from pathlib import Path

from scripts.runtime import build_runtime_env, memory_cli_script_path, resolve_runtime_paths


def test_resolve_runtime_paths_from_nested_git_workspace(tmp_path):
    workspace = tmp_path / 'repo'
    nested = workspace / 'src' / 'feature'
    (workspace / '.git').mkdir(parents=True)
    nested.mkdir(parents=True)

    paths = resolve_runtime_paths(start=nested)

    assert paths.workspace_root == workspace.resolve()
    assert paths.superpowers_dir == (workspace / '.superpowers').resolve()
    assert paths.memory_dir == (workspace / '.superpowers' / 'pyramid-memory').resolve()
    assert paths.uv_cache_dir == (workspace / '.superpowers' / 'uv-cache').resolve()
    assert paths.config_path == (workspace / '.superpowers' / 'pyramid-memory' / 'config.toml').resolve()
    assert paths.db_path == (workspace / '.superpowers' / 'pyramid-memory' / 'data.cozo').resolve()


def test_resolve_runtime_paths_prefers_explicit_root(tmp_path):
    workspace = tmp_path / 'repo'
    other = tmp_path / 'other' / 'deep'
    workspace.mkdir()
    other.mkdir(parents=True)

    paths = resolve_runtime_paths(start=other, explicit_root=workspace)

    assert paths.workspace_root == workspace.resolve()
    assert paths.uv_cache_dir == (workspace / '.superpowers' / 'uv-cache').resolve()


def test_build_runtime_env_sets_workspace_local_uv_defaults(tmp_path):
    workspace = tmp_path / 'repo'
    workspace.mkdir()

    env = build_runtime_env(workspace_root=workspace, base_env={'PATH': '/usr/bin'})

    assert env['PATH'] == '/usr/bin'
    assert env['UV_CACHE_DIR'] == str((workspace / '.superpowers' / 'uv-cache').resolve())
    assert env['UV_INDEX_URL'] == 'https://pypi.tuna.tsinghua.edu.cn/simple'
    assert env['UV_INDEX_STRATEGY'] == 'unsafe-best-match'


def test_memory_cli_script_path_points_to_sibling_script():
    path = memory_cli_script_path()
    assert path.name == 'memory_cli.py'
    assert path.exists()
