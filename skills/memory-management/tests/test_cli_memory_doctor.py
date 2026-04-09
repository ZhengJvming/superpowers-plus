import json

import pytest


@pytest.fixture
def initialized(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli


def test_doctor_reports_healthy(initialized):
    r = initialized("memory", "doctor")
    payload = json.loads(r.stdout)["data"]
    assert payload["db_ok"] is True
    assert payload["embedding_provider"] == "skip"


def test_export_returns_json(initialized):
    initialized(
        "node",
        "create",
        "--id",
        "n1",
        "--name",
        "x",
        "--type",
        "branch",
        "--level",
        "1",
        "--description",
        "x",
        "--origin",
        "user_stated",
    )
    r = initialized("memory", "export")
    payload = json.loads(r.stdout)["data"]
    assert "nodes" in payload
    assert len(payload["nodes"]) == 1
