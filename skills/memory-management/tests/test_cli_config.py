import json

import pytest


@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli


def test_config_set_embedding_model(initialized):
    result = initialized("config", "set", "--key", "embedding.model", "--value", "text-embedding-3-small")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["updated"]["embedding.model"] == "text-embedding-3-small"

    shown = initialized("config", "show")
    shown_payload = json.loads(shown.stdout)
    assert shown_payload["data"]["embedding_model"] == "text-embedding-3-small"


def test_config_set_embedding_dim_warns_reindex(initialized):
    result = initialized("config", "set", "--key", "embedding.dim", "--value", "512")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["updated"]["embedding.dim"] == 512
    assert any("reindex" in warning.lower() or "reinit" in warning.lower() for warning in payload["warnings"])

    shown = initialized("config", "show")
    shown_payload = json.loads(shown.stdout)
    assert shown_payload["data"]["embedding_dim"] == 512


def test_config_set_embedding_api_fields(initialized):
    initialized(
        "config",
        "set",
        "--key",
        "embedding.api_base",
        "--value",
        "https://api.openai.com/v1",
    )
    initialized("config", "set", "--key", "embedding.api_key_env", "--value", "OPENAI_API_KEY")
    shown = initialized("config", "show")
    payload = json.loads(shown.stdout)["data"]
    assert payload["embedding_api_base"] == "https://api.openai.com/v1"
    assert payload["embedding_api_key_env"] == "OPENAI_API_KEY"
