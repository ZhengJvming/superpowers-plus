from scripts.config import Config, load_config, save_config


def test_default_config_when_missing(tmp_path):
    cfg = load_config(tmp_path / "config.toml")
    assert cfg.embedding_provider == "skip"
    assert cfg.db_path.endswith("data.cozo")
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
