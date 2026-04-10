import json
from pathlib import Path


def _init_workspace(run_cli, workspace: Path, project: str) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    result = run_cli(
        "--workspace-root",
        str(workspace),
        "init",
        "--project",
        project,
        "--embedding",
        "skip",
        "--non-interactive",
        cwd=workspace,
    )
    assert result.returncode == 0, result.stderr


def test_memory_discover_finds_initialized_siblings(run_cli, tmp_path):
    parent = tmp_path / "code"
    user = parent / "user-service"
    payment = parent / "payment-service"
    notify = parent / "notification-service"

    _init_workspace(run_cli, user, "user-svc")
    _init_workspace(run_cli, payment, "payment-svc")
    _init_workspace(run_cli, notify, "notify-svc")

    result = run_cli("--workspace-root", str(user), "memory", "discover", cwd=user)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)["data"]
    assert payload["current"]["path"] == str(user.resolve())
    assert payload["current"]["project"] == "user-svc"
    siblings = {item["path"]: item for item in payload["siblings"]}
    assert str(payment.resolve()) in siblings
    assert str(notify.resolve()) in siblings
    assert siblings[str(payment.resolve())]["project"] == "payment-svc"
    assert siblings[str(notify.resolve())]["project"] == "notify-svc"


def test_memory_discover_prefers_configured_related_workspaces(run_cli, tmp_path):
    parent = tmp_path / "code"
    user = parent / "user-service"
    payment = parent / "payment-service"
    notify = parent / "notification-service"
    external = parent / "external-service"

    _init_workspace(run_cli, user, "user-svc")
    _init_workspace(run_cli, payment, "payment-svc")
    _init_workspace(run_cli, notify, "notify-svc")
    external.mkdir(parents=True, exist_ok=True)

    set_result = run_cli(
        "--workspace-root",
        str(user),
        "config",
        "set",
        "--key",
        "workspaces.related",
        "--value",
        "../external-service,../notification-service,../payment-service",
        cwd=user,
    )
    assert set_result.returncode == 0, set_result.stderr

    result = run_cli("--workspace-root", str(user), "memory", "discover", cwd=user)
    assert result.returncode == 0, result.stderr
    siblings = json.loads(result.stdout)["data"]["siblings"]
    assert siblings[0]["path"] == str(external.resolve())
    assert siblings[0]["initialized"] is False
    assert siblings[1]["path"] == str(notify.resolve())
    assert siblings[2]["path"] == str(payment.resolve())
