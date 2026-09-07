#!/usr/bin/env python3
"""Validate this repository's marketplace and skill-only Codex package contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def contained(root: Path, value: str) -> Path:
    require(
        isinstance(value, str) and value.startswith("./") and "\\" not in value,
        "Expected ./ relative path",
    )
    path = (root / value).resolve()
    require(path.is_relative_to(root.resolve()), f"Path escapes root: {value}")
    require(path.exists(), f"Missing path: {value}")
    return path


def validate(root: Path = ROOT) -> None:
    marketplace = json.loads(
        (root / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
    )
    require(
        set(marketplace) == {"name", "interface", "plugins"},
        "Unexpected marketplace fields",
    )
    require(marketplace["name"] == "learn-up", "Unexpected marketplace name")
    require(
        marketplace["interface"] == {"displayName": "Learn Up"},
        "Invalid marketplace interface",
    )
    entries = marketplace["plugins"]
    require(
        isinstance(entries, list) and len(entries) == 1, "Expected exactly one plugin"
    )
    entry = entries[0]
    require(
        set(entry) == {"name", "source", "policy", "category"},
        "Unexpected entry fields",
    )
    require(
        entry["name"] == "learn-up" and entry["category"] == "Education",
        "Invalid plugin identity",
    )
    require(
        entry["policy"]
        == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "Invalid marketplace policy",
    )
    source = entry["source"]
    require(
        set(source) == {"source", "path"} and source["source"] == "local",
        "Expected local source",
    )
    package = contained(root, source["path"])
    require(source["path"] == "./plugins/learn-up", "Unexpected package location")
    manifest = json.loads(
        (package / ".codex-plugin/plugin.json").read_text(encoding="utf-8")
    )
    portable = json.loads((root / "plugin.json").read_text(encoding="utf-8"))
    fields = {
        "name",
        "version",
        "description",
        "author",
        "homepage",
        "repository",
        "license",
        "keywords",
    }
    require(
        set(manifest) == fields | {"skills", "interface"},
        "Unexpected skill-only plugin fields",
    )
    for field in fields:
        require(manifest[field] == portable[field], f"Shared metadata differs: {field}")
    require(manifest["name"] == entry["name"], "Plugin name mismatch")
    require(
        isinstance(manifest["version"], str)
        and SEMVER.fullmatch(manifest["version"]) is not None,
        "Invalid semver",
    )
    require(
        bool(manifest["description"].strip())
        and bool(manifest["author"]["name"].strip()),
        "Empty plugin metadata",
    )
    skills = contained(package, manifest["skills"])
    require(manifest["skills"] == "./skills/", "Unexpected skills path")
    require((skills / "learn-up/SKILL.md").is_file(), "Missing packaged SKILL.md")
    skill_root = skills / "learn-up"
    for reference in re.findall(
        r"`((?:references|assets)/[^`]+)`",
        (skill_root / "SKILL.md").read_text(encoding="utf-8"),
    ):
        contained(skill_root, "./" + reference)
    interface = manifest["interface"]
    for key in (
        "displayName",
        "shortDescription",
        "longDescription",
        "developerName",
        "category",
    ):
        require(
            isinstance(interface[key], str) and bool(interface[key].strip()),
            f"Empty interface.{key}",
        )
    require(
        interface["capabilities"] == ["Interactive", "Write"], "Unexpected capabilities"
    )
    prompts = interface["defaultPrompt"]
    require(
        isinstance(prompts, list)
        and 1 <= len(prompts) <= 3
        and all(isinstance(p, str) and 0 < len(p) <= 128 for p in prompts),
        "Invalid default prompts",
    )
    for key in ("composerIcon", "logo", "logoDark"):
        if key in interface:
            require(contained(package, interface[key]).is_file(), f"Invalid {key}")
    for value in interface.get("screenshots", []):
        require(contained(package, value).is_file(), "Invalid screenshot")
    require(
        not (root / ".codex-plugin").exists(), "Obsolete root Codex manifest remains"
    )
    readme = (root / "README.md").read_text(encoding="utf-8")
    for command in (
        "codex plugin marketplace add AndresParraSilva/learn-up",
        "codex plugin marketplace upgrade learn-up",
        "codex plugin add learn-up@learn-up",
        "## Migrating from an older Codex installation",
    ):
        require(command in readme, f"Missing documentation: {command}")
    require(
        "Install the learn-up plugin from\n" not in readme,
        "Obsolete direct installation instructions",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    validate(parser.parse_args().root)
    print("Marketplace and shared plugin metadata validation passed.")
