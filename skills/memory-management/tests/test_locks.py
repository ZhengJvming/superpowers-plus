import os

import pytest

from scripts.locks import LockTimeout, file_lock


def test_acquire_and_release(tmp_path):
    lock_path = tmp_path / ".lock"
    with file_lock(lock_path, timeout=1):
        assert lock_path.exists()
    assert not lock_path.exists()


def test_stale_pid_cleanup(tmp_path):
    lock_path = tmp_path / ".lock"
    lock_path.write_text("999999")
    with file_lock(lock_path, timeout=1):
        assert lock_path.read_text() == str(os.getpid())


def test_timeout_when_held(tmp_path):
    lock_path = tmp_path / ".lock"
    lock_path.write_text(str(os.getpid()))
    with pytest.raises(LockTimeout):
        with file_lock(lock_path, timeout=0.5):
            pass
