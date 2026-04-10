import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

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
    assert payload["embedding_model"] == ""
    assert payload["embedding_dim"] == 384
    assert payload["embedding_api_base"] == ""
    assert payload["embedding_api_key_configured"] is False
    assert payload["embedding_ok"] is True


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


def test_doctor_reports_openai_embedding_details(run_cli, monkeypatch):
    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, _format, *_args):
            return

        def do_POST(self):
            _ = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"data": [{"index": 0, "embedding": [0.1, 0.2]}]}).encode("utf-8"))

    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setenv("OPENAI_API_KEY", "demo-key")
        api_base = f"http://127.0.0.1:{server.server_port}/v1"
        init_result = run_cli(
            "init",
            "--project",
            "demo",
            "--embedding",
            "openai_compatible",
            "--embedding-model",
            "text-embedding-3-small",
            "--embedding-api-base",
            api_base,
            "--embedding-api-key-env",
            "OPENAI_API_KEY",
            "--non-interactive",
        )
        assert init_result.returncode == 0, init_result.stderr
        doctor = run_cli("memory", "doctor")
        payload = json.loads(doctor.stdout)["data"]
        assert payload["embedding_provider"] == "openai_compatible"
        assert payload["embedding_model"] == "text-embedding-3-small"
        assert payload["embedding_api_base"] == api_base
        assert payload["embedding_api_key_configured"] is True
        assert payload["embedding_ok"] is True
    finally:
        server.shutdown()
        server.server_close()
