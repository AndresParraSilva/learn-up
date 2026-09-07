#!/usr/bin/env python3
"""Synchronize the generated Codex payload from the canonical portable skill."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSIENT = {"__pycache__", ".DS_Store", "node_modules", ".venv", "dist", "build"}


def inventory(root: Path, *, canonical: bool = False) -> dict[str, tuple[bytes, bool]]:
    if root.is_symlink():
        raise ValueError(f"Symlinks are not supported: {root}")
    if not root.is_dir():
        raise ValueError(f"Missing skill directory: {root}")
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if canonical and (set(relative.parts) & TRANSIENT or path.suffix == ".pyc"):
            continue
        if path.is_symlink():
            raise ValueError(f"Symlinks are not supported: {path}")
        if path.is_file():
            result[relative.as_posix()] = (
                path.read_bytes(),
                bool(path.stat().st_mode & 0o111) if os.name != "nt" else False,
            )
        elif not path.is_dir():
            raise ValueError(f"Unsupported payload entry: {path}")
    if "SKILL.md" not in result:
        raise ValueError(f"Missing SKILL.md: {root}")
    return result


def synchronize(root: Path = ROOT, *, check: bool = False) -> None:
    source = root / "skills/learn-up"
    target = root / "plugins/learn-up/skills/learn-up"
    expected = inventory(source, canonical=True)
    if check:
        actual = inventory(target)
        differences = sorted(
            k
            for k in expected.keys() | actual.keys()
            if expected.get(k) != actual.get(k)
        )
        if differences:
            raise ValueError("Stale Codex payload: " + ", ".join(differences))
        return
    if any(
        path.is_symlink() for path in (target, *target.parents) if path != root
    ) or not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Unsafe generated destination: {target}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    for relative in expected:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    synchronize(check=args.check)
    print("Codex payload is synchronized.")
