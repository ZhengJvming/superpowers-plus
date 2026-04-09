"""JSON-backed session scratchpad."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

try:
    from .models import ScratchEntry
except ImportError:
    from models import ScratchEntry


class ScratchpadStore:
    def __init__(self, path: Path):
        self._path = path

    def _read(self) -> list[dict]:
        if not self._path.exists():
            return []
        text = self._path.read_text()
        if not text.strip():
            return []
        return json.loads(text)

    def _write_all(self, entries: list[dict]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(entries, ensure_ascii=False, indent=2))

    def write(self, entry: ScratchEntry) -> None:
        entries = [item for item in self._read() if item["key"] != entry.key]
        entries.append(entry.to_dict())
        self._write_all(entries)

    def list_all(self, *, category: Optional[str] = None) -> list[ScratchEntry]:
        entries = self._read()
        if category is not None:
            entries = [item for item in entries if item.get("category") == category]
        return [ScratchEntry.from_dict(item) for item in entries]

    def delete(self, key: str) -> None:
        entries = [item for item in self._read() if item["key"] != key]
        self._write_all(entries)

    def clear(self, *, ttl: Optional[str] = None) -> None:
        if ttl is None:
            self._write_all([])
            return
        entries = [item for item in self._read() if item.get("ttl") != ttl]
        self._write_all(entries)
