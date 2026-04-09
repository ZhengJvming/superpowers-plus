from pathlib import Path

from scripts.run_memory_cli import build_launcher_command


def test_build_launcher_command_uses_detected_workspace_root(tmp_path):
    workspace = tmp_path / 'repo'
    nested = workspace / 'src' / 'feature'
    (workspace / '.git').mkdir(parents=True)
    nested.mkdir(parents=True)

    cmd, env = build_launcher_command(['memory', 'context', '--node', 'leaf-1'], cwd=nested, environ={'PATH': '/usr/bin'})

    assert cmd[:4] == ['uv', 'run', str(Path(cmd[2]).resolve()), '--workspace-root']
    assert Path(cmd[2]).name == 'memory_cli.py'
    assert Path(cmd[4]) == workspace.resolve()
    assert cmd[5:] == ['memory', 'context', '--node', 'leaf-1']
    assert env['UV_CACHE_DIR'] == str((workspace / '.superpowers' / 'uv-cache').resolve())


def test_build_launcher_command_respects_explicit_workspace_root(tmp_path):
    workspace = tmp_path / 'repo'
    other = tmp_path / 'other'
    workspace.mkdir()
    other.mkdir()

    cmd, env = build_launcher_command(
        ['--workspace-root', str(workspace), 'config', 'show'],
        cwd=other,
        environ={'PATH': '/usr/bin'},
    )

    assert Path(cmd[4]) == workspace.resolve()
    assert cmd[5:] == ['config', 'show']
    assert env['UV_CACHE_DIR'] == str((workspace / '.superpowers' / 'uv-cache').resolve())
