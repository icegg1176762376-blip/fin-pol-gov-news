#!/usr/bin/env python3
"""
Lightweight environment helpers for local scripts.

Loads a project-level `.env` file into `os.environ` without overriding values
that are already set by the parent process.
"""

import os
from pathlib import Path
from typing import Dict, Iterable


def _parse_env_line(line: str):
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None, None

    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()

    if not key:
        return None, None

    if value and len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]

    return key, value


def find_project_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current] + list(current.parents):
        if (candidate / "pyproject.toml").exists() or (candidate / ".git").exists():
            return candidate
    return start.resolve()


def load_dotenv(dotenv_path: Path = None, override: bool = False) -> Dict[str, str]:
    base_dir = find_project_root(Path(__file__).resolve().parent)
    path = dotenv_path or (base_dir / ".env")
    loaded: Dict[str, str] = {}

    if not path.exists():
        return loaded

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        key, value = _parse_env_line(raw_line)
        if not key:
            continue
        if override or key not in os.environ:
            os.environ[key] = value
        loaded[key] = os.environ.get(key, value)

    return loaded


def env_status(keys: Iterable[str]) -> Dict[str, bool]:
    return {key: bool(os.getenv(key)) for key in keys}
