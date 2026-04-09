import json


def test_version_command(run_cli):
    result = run_cli("version")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["version"].startswith("0.1")


def test_init_creates_config_and_db(run_cli, tmp_path):
    result = run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    cfg_path = tmp_path / ".pyramid-memory" / "config.toml"
    assert cfg_path.exists()
    assert "demo" in cfg_path.read_text()


def test_config_show_uninitialized(run_cli):
    result = run_cli("config", "show")
    payload = json.loads(result.stdout)
    assert payload["data"]["initialized"] is False


def test_config_show_after_init(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    result = run_cli("config", "show")
    payload = json.loads(result.stdout)
    assert payload["data"]["initialized"] is True
    assert payload["data"]["embedding_provider"] == "skip"
