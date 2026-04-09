import json
from pathlib import Path

from scripts.config import default_config_path, resolve_workspace_root


def test_init_uses_workspace_local_storage_by_default(run_cli, tmp_path):
    workspace = tmp_path / 'repo'
    workspace.mkdir()

    result = run_cli('init', '--project', 'demo', '--embedding', 'skip', '--non-interactive', cwd=workspace)
    assert result.returncode == 0, result.stderr

    cfg_path = workspace / '.superpowers' / 'pyramid-memory' / 'config.toml'
    db_path = workspace / '.superpowers' / 'pyramid-memory' / 'data.cozo'
    assert cfg_path.exists()
    assert db_path.exists()

    payload = json.loads(result.stdout)
    assert payload['data']['db_path'] == str(db_path)


def test_commands_from_nested_directory_reuse_parent_workspace(run_cli, tmp_path):
    workspace = tmp_path / 'repo'
    nested = workspace / 'src' / 'feature'
    nested.mkdir(parents=True)

    init_result = run_cli('init', '--project', 'demo', '--embedding', 'skip', '--non-interactive', cwd=workspace)
    assert init_result.returncode == 0, init_result.stderr

    result = run_cli('config', 'show', cwd=nested)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    assert payload['data']['initialized'] is True
    assert payload['data']['default_project'] == 'demo'
    assert payload['data']['db_path'] == str(workspace / '.superpowers' / 'pyramid-memory' / 'data.cozo')


def test_explicit_workspace_root_overrides_cwd(run_cli, tmp_path):
    workspace = tmp_path / 'repo'
    other = tmp_path / 'other'
    nested = other / 'deep'
    workspace.mkdir()
    nested.mkdir(parents=True)

    result = run_cli(
        '--workspace-root',
        str(workspace),
        'init',
        '--project',
        'demo',
        '--embedding',
        'skip',
        '--non-interactive',
        cwd=nested,
    )
    assert result.returncode == 0, result.stderr

    cfg_path = workspace / '.superpowers' / 'pyramid-memory' / 'config.toml'
    assert cfg_path.exists()
    assert not (nested / '.superpowers' / 'pyramid-memory' / 'config.toml').exists()


def test_resolve_workspace_root_prefers_existing_superpowers_config(tmp_path):
    workspace = tmp_path / 'repo'
    nested = workspace / 'a' / 'b'
    cfg_path = workspace / '.superpowers' / 'pyramid-memory' / 'config.toml'
    cfg_path.parent.mkdir(parents=True)
    cfg_path.write_text('[meta]\ninitialized = true\n')
    nested.mkdir(parents=True)

    assert resolve_workspace_root(nested) == workspace.resolve()
    assert default_config_path(cwd=nested) == cfg_path.resolve()
