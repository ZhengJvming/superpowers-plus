import subprocess
from pathlib import Path

from scripts.run_memory_cli import build_launcher_command, run_with_fallback


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


def test_run_with_fallback_retries_on_default_index_403():
    calls = []

    def runner(cmd, *, env, capture_output, text, check):
        calls.append(env['UV_INDEX_URL'])
        if len(calls) == 1:
            return subprocess.CompletedProcess(
                cmd,
                1,
                stdout='',
                stderr='HTTP status client error (403 Forbidden) for url (...)',
            )
        return subprocess.CompletedProcess(cmd, 0, stdout='{"ok": true}\n', stderr='')

    code, stdout, stderr = run_with_fallback(
        ['uv', 'run', 'memory_cli.py'],
        {'UV_CACHE_DIR': '/tmp/cache'},
        base_environ={},
        runner=runner,
    )

    assert code == 0
    assert stdout == '{"ok": true}\n'
    assert stderr == ''
    assert calls == [
        'https://pypi.tuna.tsinghua.edu.cn/simple',
        'https://mirrors.aliyun.com/pypi/simple/',
    ]


def test_run_with_fallback_does_not_retry_explicit_index_override():
    calls = []

    def runner(cmd, *, env, capture_output, text, check):
        calls.append(env['UV_INDEX_URL'])
        return subprocess.CompletedProcess(cmd, 1, stdout='', stderr='403 Forbidden')

    code, _, _ = run_with_fallback(
        ['uv', 'run', 'memory_cli.py'],
        {'UV_CACHE_DIR': '/tmp/cache', 'UV_INDEX_URL': 'https://example.com/simple'},
        base_environ={'UV_INDEX_URL': 'https://example.com/simple'},
        runner=runner,
    )

    assert code == 1
    assert calls == ['https://example.com/simple']


def test_run_with_fallback_does_not_retry_non_mirror_failures():
    calls = []

    def runner(cmd, *, env, capture_output, text, check):
        calls.append(env['UV_INDEX_URL'])
        return subprocess.CompletedProcess(cmd, 1, stdout='', stderr='SyntaxError: invalid syntax')

    code, _, stderr = run_with_fallback(
        ['uv', 'run', 'memory_cli.py'],
        {'UV_CACHE_DIR': '/tmp/cache'},
        base_environ={},
        runner=runner,
    )

    assert code == 1
    assert 'SyntaxError' in stderr
    assert calls == ['https://pypi.tuna.tsinghua.edu.cn/simple']
