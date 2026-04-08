import json


def test_version_command(run_cli):
    result = run_cli("version")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["version"].startswith("0.1")
