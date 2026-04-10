import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


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
    cfg_path = tmp_path / ".superpowers" / "pyramid-memory" / "config.toml"
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
    assert payload["data"]["embedding_model"] == ""
    assert payload["data"]["embedding_dim"] == 384
    assert payload["data"]["embedding_api_base"] == ""
    assert payload["data"]["embedding_api_key_env"] == ""


def test_init_openai_compatible_healthcheck(run_cli, monkeypatch):
    captured = {}

    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, _format, *_args):
            return

        def do_POST(self):
            body_len = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(body_len)
            captured["path"] = self.path
            captured["headers"] = dict(self.headers)
            captured["body"] = json.loads(body.decode("utf-8"))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps({"data": [{"index": 0, "embedding": [0.1, 0.2, 0.3]}]}).encode("utf-8")
            )

    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        monkeypatch.setenv("OPENAI_API_KEY", "demo-key")
        api_base = f"http://127.0.0.1:{server.server_port}/v1"
        result = run_cli(
            "init",
            "--project",
            "demo",
            "--embedding",
            "openai_compatible",
            "--embedding-model",
            "text-embedding-3-small",
            "--embedding-dim",
            "128",
            "--embedding-api-base",
            api_base,
            "--embedding-api-key-env",
            "OPENAI_API_KEY",
            "--non-interactive",
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)["data"]
        assert payload["embedding"] == "openai_compatible"
        assert captured["path"] == "/v1/embeddings"
        assert captured["body"]["dimensions"] == 128
        assert captured["body"]["model"] == "text-embedding-3-small"

        shown = run_cli("config", "show")
        shown_payload = json.loads(shown.stdout)["data"]
        assert shown_payload["embedding_provider"] == "openai_compatible"
        assert shown_payload["embedding_model"] == "text-embedding-3-small"
        assert shown_payload["embedding_dim"] == 128
        assert shown_payload["embedding_api_base"] == api_base
        assert shown_payload["embedding_api_key_env"] == "OPENAI_API_KEY"
    finally:
        server.shutdown()
        server.server_close()
