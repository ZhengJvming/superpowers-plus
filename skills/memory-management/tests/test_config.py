from scripts.config import Config, default_config_path, load_config, save_config


def test_default_config_when_missing(tmp_path):
    cfg = load_config(tmp_path / "config.toml")
    assert cfg.embedding_provider == "skip"
    assert cfg.db_path == str(tmp_path / "data.cozo")
    assert cfg.initialized is False


def test_save_and_reload(tmp_path):
    path = tmp_path / "config.toml"
    cfg = Config(
        embedding_provider="fastembed",
        db_path=str(tmp_path / "data.cozo"),
        default_project="myapp",
        initialized=True,
    )
    save_config(path, cfg)
    cfg2 = load_config(path)
    assert cfg2.embedding_provider == "fastembed"
    assert cfg2.default_project == "myapp"
    assert cfg2.initialized is True


def test_default_config_path_uses_git_root(tmp_path):
    workspace = tmp_path / "repo"
    nested = workspace / "src" / "feature"
    (workspace / ".git").mkdir(parents=True)
    nested.mkdir(parents=True)

    assert default_config_path(cwd=nested) == (
        workspace / ".superpowers" / "pyramid-memory" / "config.toml"
    ).resolve()
