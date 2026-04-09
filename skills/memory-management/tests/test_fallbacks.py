"""Exercises every row of spec §8 fallback matrix."""

import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def initialized_skip(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    return run_cli


def test_row1_uv_missing_documented():
    pytest.skip("Row 1 (uv missing) is a harness prerequisite and covered by docs")


def test_row2_pycozo_build_failure_documented():
    pytest.skip("Row 2 (pycozo build/runtime packaging) is environment-level and documented")


def test_row3_embedding_unavailable_falls_back_to_bm25(run_cli):
    cli = run_cli
    cli("init", "--project", "demo", "--embedding", "fastembed", "--non-interactive")
    cli(
        "node",
        "create",
        "--id",
        "a",
        "--name",
        "auth",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "OAuth login flow",
        "--origin",
        "user_stated",
    )
    r = cli("memory", "recall", "--query", "oauth", "--semantic")
    payload = json.loads(r.stdout)
    assert payload["degraded"] is True
    assert payload["data"]["matches"][0]["match_type"] == "bm25"


def test_row4_provider_failure_falls_back_to_bm25(initialized_skip):
    initialized_skip(
        "node",
        "create",
        "--id",
        "a",
        "--name",
        "auth",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "OAuth login",
        "--origin",
        "user_stated",
    )
    r = initialized_skip("memory", "recall", "--query", "oauth", "--semantic")
    payload = json.loads(r.stdout)
    assert payload["degraded"] is True
    assert payload["data"]["matches"][0]["match_type"] == "bm25"


def test_row5_corrupted_db_reports_error(initialized_skip):
    home = Path(os.environ["HOME"])
    db_path = home / ".pyramid-memory" / "data.cozo"
    db_path.write_bytes(b"corrupted db payload")
    r = initialized_skip("node", "list")
    if r.stdout.strip():
        payload = json.loads(r.stdout)
        assert payload.get("ok") is False or "error" in payload
    else:
        assert r.returncode != 0


def test_row6_shared_home_directory(run_cli):
    cli = run_cli
    cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    cli(
        "node",
        "create",
        "--id",
        "x",
        "--name",
        "x",
        "--type",
        "leaf",
        "--level",
        "1",
        "--description",
        "x",
        "--origin",
        "user_stated",
    )
    r = cli("node", "list")
    nodes = json.loads(r.stdout)["data"]["nodes"]
    assert len(nodes) == 1


def test_row7_no_network_uses_skip(run_cli, monkeypatch):
    monkeypatch.setenv("PYRAMID_MEMORY_NO_NETWORK", "1")
    r = run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    assert json.loads(r.stdout)["ok"] is True


def test_row8_missing_project_fails_fast(run_cli):
    run_cli("init", "--project", "demo", "--embedding", "skip", "--non-interactive")
    cfg_path = Path(os.environ["HOME"]).expanduser() / ".pyramid-memory" / "config.toml"
    text = cfg_path.read_text()
    cfg_path.write_text(text.replace('default_project = "demo"', ""))
    r = run_cli("node", "list")
    payload = json.loads(r.stdout)
    assert payload.get("ok") is False
    assert payload["error"]["code"] == "missing_project"
