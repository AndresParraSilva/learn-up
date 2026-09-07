#!/usr/bin/env python3
"""Reject release tags that do not match the portable manifest version."""

import json
import sys
from pathlib import Path

if __name__ == "__main__":
    version = json.loads(
        (Path(__file__).resolve().parents[1] / "plugin.json").read_text()
    )["version"]
    if len(sys.argv) != 2 or sys.argv[1] != f"v{version}":
        raise SystemExit(f"Expected release tag v{version}")
    print(f"Release tag matches {version}.")
