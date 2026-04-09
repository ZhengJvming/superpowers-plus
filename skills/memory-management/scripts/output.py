from __future__ import annotations

import json
import sys
from typing import Any


def emit(data: Any = None, *, warnings: list[str] | None = None, degraded: bool = False, ok: bool = True) -> None:
    print(
        json.dumps(
            {
                "ok": ok,
                "data": data if data is not None else {},
                "warnings": warnings or [],
                "degraded": degraded,
            }
        )
    )


def emit_error(message: str, *, code: str = "error") -> None:
    print(
        json.dumps(
            {
                "ok": False,
                "error": {"code": code, "message": message},
                "warnings": [],
                "degraded": False,
            }
        )
    )
    sys.exit(1)
