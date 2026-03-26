#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"


def _ensure_repo_python() -> None:
    if not VENV_PYTHON.exists():
        return
    current = Path(sys.executable).absolute()
    if current.parent == VENV_PYTHON.parent:
        return
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(ROOT / "app.py"), *sys.argv[1:]])


def main() -> int:
    _ensure_repo_python()
    try:
        from eden.app import main as eden_main
    except ModuleNotFoundError as exc:
        if exc.name == "eden":
            sys.stderr.write(
                "EDEN is not installed in the repo-local .venv.\n"
                "Rebuild it with /opt/homebrew/bin/python3.12 -m venv .venv\n"
                "then run .venv/bin/python -m pip install -e '.[dev,mlx]'.\n"
            )
            return 1
        raise
    return eden_main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
