from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path


class LockTimeout(Exception):
    pass


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    except OSError:
        return False
    return True


@contextmanager
def file_lock(path: Path, timeout: float = 5.0, poll: float = 0.05):
    path = Path(path)
    deadline = time.monotonic() + timeout
    my_pid = os.getpid()

    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(my_pid).encode())
            os.close(fd)
            break
        except FileExistsError:
            try:
                holder = int(path.read_text().strip())
                if not _pid_alive(holder):
                    path.unlink(missing_ok=True)
                    continue
            except (ValueError, FileNotFoundError):
                path.unlink(missing_ok=True)
                continue

            if time.monotonic() > deadline:
                raise LockTimeout(f"could not acquire {path} within {timeout}s")
            time.sleep(poll)

    try:
        yield
    finally:
        try:
            if path.read_text().strip() == str(my_pid):
                path.unlink(missing_ok=True)
        except FileNotFoundError:
            pass
