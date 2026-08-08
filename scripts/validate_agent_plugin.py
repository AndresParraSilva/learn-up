#!/usr/bin/env python3
"""Validate the portable Agent Plugins 1.0.0 manifest without network access."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_URI = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
ALLOWED_FIELDS = {
    "$schema",
    "name",
    "version",
    "description",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
    "extensions",
}
AUTHOR_FIELDS = {"name", "email", "url"}
NAME_RE = re.compile(r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")


def validate_manifest(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["plugin.json must contain a JSON object"]

    errors: list[str] = []
    unknown_fields = sorted(set(payload) - ALLOWED_FIELDS)
    if unknown_fields:
        errors.append(f"unknown top-level fields: {', '.join(unknown_fields)}")

    if payload.get("$schema") != SCHEMA_URI:
        errors.append(f"$schema must be {SCHEMA_URI}")

    name = payload.get("name")
    if not isinstance(name, str):
        errors.append("name must be a string")
    elif not 1 <= len(name) <= 64 or NAME_RE.fullmatch(name) is None:
        errors.append("name does not satisfy Agent Plugins 1.0.0 constraints")

    for field in (
        "version",
        "description",
        "homepage",
        "repository",
        "license",
    ):
        if field in payload and not isinstance(payload[field], str):
            errors.append(f"{field} must be a string")

    if "author" in payload:
        author = payload["author"]
        if not isinstance(author, dict):
            errors.append("author must be an object")
        else:
            unknown_author_fields = sorted(set(author) - AUTHOR_FIELDS)
            if unknown_author_fields:
                errors.append(
                    f"unknown author fields: {', '.join(unknown_author_fields)}"
                )
            for field, value in author.items():
                if field in AUTHOR_FIELDS and not isinstance(value, str):
                    errors.append(f"author.{field} must be a string")

    if "keywords" in payload:
        keywords = payload["keywords"]
        if not isinstance(keywords, list) or not all(
            isinstance(keyword, str) for keyword in keywords
        ):
            errors.append("keywords must be an array of strings")

    if "extensions" in payload:
        extensions = payload["extensions"]
        if not isinstance(extensions, dict) or not all(
            isinstance(value, dict) for value in extensions.values()
        ):
            errors.append("extensions must be an object whose values are objects")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate an Agent Plugins 1.0.0 plugin.json manifest."
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "plugin.json",
    )
    return parser.parse_args()


def main() -> int:
    manifest_path = parse_args().manifest
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"Agent plugin validation failed: {exc}", file=sys.stderr)
        return 1

    errors = validate_manifest(payload)
    if errors:
        print("Agent plugin validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Agent Plugins 1.0.0 validation passed: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
