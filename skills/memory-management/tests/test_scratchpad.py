from scripts.models import ScratchEntry
from scripts.scratchpad import ScratchpadStore


def test_write_and_list(tmp_path):
    scratchpad = ScratchpadStore(tmp_path / "scratchpad.json")
    scratchpad.write(
        ScratchEntry(
            key="finding-1",
            value="API uses pagination",
            category="session_keep",
            ttl="session",
            created_at="t1",
        )
    )
    scratchpad.write(
        ScratchEntry(
            key="constraint-1",
            value="Must not use Redis",
            category="must_persist",
            ttl="persist",
            created_at="t2",
        )
    )
    entries = scratchpad.list_all()
    assert len(entries) == 2
    assert entries[0].key == "finding-1"


def test_list_by_category(tmp_path):
    scratchpad = ScratchpadStore(tmp_path / "scratchpad.json")
    scratchpad.write(ScratchEntry(key="a", value="x", category="session_keep", created_at="t"))
    scratchpad.write(ScratchEntry(key="b", value="y", category="must_persist", created_at="t"))
    assert len(scratchpad.list_all(category="must_persist")) == 1
    assert scratchpad.list_all(category="must_persist")[0].key == "b"


def test_write_overwrites_same_key(tmp_path):
    scratchpad = ScratchpadStore(tmp_path / "scratchpad.json")
    scratchpad.write(ScratchEntry(key="k", value="old", created_at="t1"))
    scratchpad.write(ScratchEntry(key="k", value="new", created_at="t2"))
    entries = scratchpad.list_all()
    assert len(entries) == 1
    assert entries[0].value == "new"


def test_delete(tmp_path):
    scratchpad = ScratchpadStore(tmp_path / "scratchpad.json")
    scratchpad.write(ScratchEntry(key="k", value="v", created_at="t"))
    scratchpad.delete("k")
    assert scratchpad.list_all() == []


def test_clear_session_only(tmp_path):
    scratchpad = ScratchpadStore(tmp_path / "scratchpad.json")
    scratchpad.write(ScratchEntry(key="s", value="x", ttl="session", created_at="t"))
    scratchpad.write(ScratchEntry(key="p", value="y", ttl="persist", created_at="t"))
    scratchpad.clear(ttl="session")
    entries = scratchpad.list_all()
    assert len(entries) == 1
    assert entries[0].key == "p"


def test_clear_all(tmp_path):
    scratchpad = ScratchpadStore(tmp_path / "scratchpad.json")
    scratchpad.write(ScratchEntry(key="a", value="x", created_at="t"))
    scratchpad.write(ScratchEntry(key="b", value="y", created_at="t"))
    scratchpad.clear()
    assert scratchpad.list_all() == []


def test_persistence_across_instances(tmp_path):
    path = tmp_path / "scratchpad.json"
    first = ScratchpadStore(path)
    first.write(ScratchEntry(key="k", value="v", created_at="t"))
    second = ScratchpadStore(path)
    assert len(second.list_all()) == 1


def test_empty_file_returns_empty_list(tmp_path):
    scratchpad = ScratchpadStore(tmp_path / "scratchpad.json")
    assert scratchpad.list_all() == []
