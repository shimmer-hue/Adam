from __future__ import annotations

import json
import sys

from eden.observatory.frontend_assets import build_status


def main() -> int:
    status = build_status()
    if status.get("available") and not status.get("warning"):
        print(json.dumps({"ok": True, "frontend_build": status}, indent=2))
        return 0
    print(json.dumps({"ok": False, "frontend_build": status}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
