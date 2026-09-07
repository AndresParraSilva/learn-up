from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.sync_codex_plugin import synchronize
from scripts.validate_marketplace import ROOT, validate


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    for directory in ("skills", "plugins", ".agents"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    for name in ("plugin.json", "README.md"):
        shutil.copy2(ROOT / name, tmp_path / name)
    return tmp_path


def test_repository_contract() -> None:
    validate()
    synchronize(check=True)


@pytest.mark.parametrize("change", ["changed", "missing", "extra", "mode"])
def test_sync_detects_and_repairs_drift(repository: Path, change: str) -> None:
    target = repository / "plugins/learn-up/skills/learn-up/SKILL.md"
    if change == "changed":
        target.write_text("stale", encoding="utf-8")
    elif change == "missing":
        target.unlink()
    elif change == "extra":
        target.with_name("unexpected.txt").write_text("extra", encoding="utf-8")
    else:
        import os

        if os.name == "nt":
            pytest.skip("POSIX executable bits")
        target.chmod(target.stat().st_mode ^ 0o111)
    with pytest.raises(ValueError, match="Stale|Missing SKILL.md"):
        synchronize(repository, check=True)
    synchronize(repository)
    synchronize(repository, check=True)


def test_sync_excludes_transient_files(repository: Path) -> None:
    source = repository / "skills/learn-up"
    (source / "__pycache__").mkdir(exist_ok=True)
    (source / "__pycache__/temporary.pyc").write_bytes(b"cache")
    synchronize(repository)
    assert not (repository / "plugins/learn-up/skills/learn-up/__pycache__").exists()


@pytest.mark.parametrize(
    "change", ["escape", "missing", "duplicate", "policy", "version", "semver", "asset"]
)
def test_validator_rejects_broken_package(repository: Path, change: str) -> None:
    path = repository / ".agents/plugins/marketplace.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if change in {"escape", "missing"}:
        payload["plugins"][0]["source"]["path"] = (
            "./../" if change == "escape" else "./missing"
        )
    elif change == "duplicate":
        payload["plugins"].append(payload["plugins"][0])
    elif change == "policy":
        payload["plugins"][0]["policy"]["authentication"] = "INVALID"
    else:
        manifest_path = repository / "plugins/learn-up/.codex-plugin/plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if change == "asset":
            manifest["interface"]["logo"] = "./missing.png"
        else:
            manifest["version"] = "9.0.0" if change == "version" else "01.0.0"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        if change == "semver":
            portable_path = repository / "plugin.json"
            portable = json.loads(portable_path.read_text(encoding="utf-8"))
            portable["version"] = manifest["version"]
            portable_path.write_text(json.dumps(portable), encoding="utf-8")
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        validate(repository)
