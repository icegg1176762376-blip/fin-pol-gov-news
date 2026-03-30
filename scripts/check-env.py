#!/usr/bin/env python3
"""
Check whether required API credentials are visible to the current Python process.

Loads a project `.env` file first if present, then reports which keys are set.
"""

import argparse
from pathlib import Path

from env_utils import env_status, load_dotenv


DEFAULT_KEYS = [
    "TAVILY_API_KEY",
    "BRAVE_API_KEY",
    "BRAVE_API_KEYS",
    "WEB_SEARCH_BACKEND",
    "RESEND_API_KEY",
    "RESEND_FROM",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check API credentials visible to the current Python process.")
    parser.add_argument("--env-file", type=Path, default=None, help="Optional path to a .env file")
    args = parser.parse_args()

    loaded = load_dotenv(args.env_file)
    if loaded:
        print(f"Loaded .env keys: {', '.join(sorted(loaded.keys()))}")
    else:
        print("Loaded .env keys: none")

    status = env_status(DEFAULT_KEYS)
    missing = []
    for key in DEFAULT_KEYS:
        is_set = status[key]
        print(f"{key}: {'SET' if is_set else 'MISSING'}")
        if not is_set:
            missing.append(key)

    return 0 if len(missing) < len(DEFAULT_KEYS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
