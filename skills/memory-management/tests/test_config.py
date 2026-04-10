from scripts.config import Config, default_config_path, load_config, save_config


def test_default_config_when_missing(tmp_path):
    cfg = load_config(tmp_path / "config.toml")
    assert cfg.embedding_provider == "skip"
    assert cfg.embedding_model == ""
    assert cfg.embedding_dim == 384
    assert cfg.embedding_api_base == ""
    assert cfg.embedding_api_key_env == ""
    assert cfg.db_path == str(tmp_path / "data.cozo")
    assert cfg.initialized is False


def test_save_and_reload(tmp_path):
    path = tmp_path / "config.toml"
    cfg = Config(
        embedding_provider="fastembed",
        embedding_model="BAAI/bge-small-en-v1.5",
        embedding_dim=512,
        embedding_api_base="http://localhost:11434/v1",
        embedding_api_key_env="OLLAMA_API_KEY",
        db_path=str(tmp_path / "data.cozo"),
        default_project="myapp",
        initialized=True,
    )
    save_config(path, cfg)
    cfg2 = load_config(path)
    assert cfg2.embedding_provider == "fastembed"
    assert cfg2.embedding_model == "BAAI/bge-small-en-v1.5"
    assert cfg2.embedding_dim == 512
    assert cfg2.embedding_api_base == "http://localhost:11434/v1"
    assert cfg2.embedding_api_key_env == "OLLAMA_API_KEY"
    assert cfg2.default_project == "myapp"
    assert cfg2.initialized is True


def test_save_omits_empty_and_default_embedding_fields(tmp_path):
    path = tmp_path / "config.toml"
    cfg = Config(embedding_provider="skip", initialized=True)
    save_config(path, cfg)
    text = path.read_text()
    assert 'provider = "skip"' in text
    assert "model =" not in text
    assert "dim =" not in text
    assert "api_base =" not in text
    assert "api_key_env =" not in text


def test_load_reads_embedding_fields_from_toml(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        """
[embedding]
provider = "openai_compatible"
model = "text-embedding-3-small"
dim = 384
api_base = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"

[storage]
db_path = "/tmp/demo.cozo"

[meta]
initialized = true
""".strip()
        + "\n"
    )
    cfg = load_config(path)
    assert cfg.embedding_provider == "openai_compatible"
    assert cfg.embedding_model == "text-embedding-3-small"
    assert cfg.embedding_dim == 384
    assert cfg.embedding_api_base == "https://api.openai.com/v1"
    assert cfg.embedding_api_key_env == "OPENAI_API_KEY"


def test_default_config_path_uses_git_root(tmp_path):
    workspace = tmp_path / "repo"
    nested = workspace / "src" / "feature"
    (workspace / ".git").mkdir(parents=True)
    nested.mkdir(parents=True)

    assert default_config_path(cwd=nested) == (
        workspace / ".superpowers" / "pyramid-memory" / "config.toml"
    ).resolve()


def test_config_display_section(tmp_path):
    path = tmp_path / "config.toml"
    cfg = Config(initialized=True, default_project="demo", display_tree_format="mermaid")
    save_config(path, cfg)
    loaded = load_config(path)
    assert loaded.display_tree_format == "mermaid"


def test_config_display_defaults_to_ascii(tmp_path):
    path = tmp_path / "config.toml"
    cfg = Config(initialized=True)
    save_config(path, cfg)
    loaded = load_config(path)
    assert loaded.display_tree_format == "ascii"


def test_config_scan_section(tmp_path):
    path = tmp_path / "config.toml"
    cfg = Config(
        initialized=True,
        default_project="demo",
        scan_last_commit="abc123",
        scan_project_root="/home/user/project",
    )
    save_config(path, cfg)
    loaded = load_config(path)
    assert loaded.scan_last_commit == "abc123"
    assert loaded.scan_project_root == "/home/user/project"


def test_config_with_related_workspaces(tmp_path):
    path = tmp_path / "config.toml"
    cfg = Config(
        initialized=True,
        default_project="demo",
        related_workspaces=["../payment-service", "../notification-service"],
    )
    save_config(path, cfg)
    loaded = load_config(path)
    assert loaded.related_workspaces == ["../payment-service", "../notification-service"]
    text = path.read_text()
    assert "[workspaces]" in text
    assert 'related = ["../payment-service", "../notification-service"]' in text


def test_config_without_workspaces_section(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        """
[embedding]
provider = "skip"

[storage]
db_path = "/tmp/demo.cozo"

[meta]
initialized = true
default_project = "demo"
""".strip()
        + "\n"
    )
    cfg = load_config(path)
    assert cfg.default_project == "demo"
    assert cfg.related_workspaces == []
