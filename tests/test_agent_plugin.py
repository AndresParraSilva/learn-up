from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.validate_agent_plugin import ALLOWED_FIELDS, SCHEMA_URI, validate_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
PORTABLE_MANIFEST = REPO_ROOT / "plugin.json"
CODEX_MANIFEST = REPO_ROOT / ".codex-plugin/plugin.json"


def load_manifest(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_portable_manifest_conforms_to_agent_plugins_1_0_0() -> None:
    manifest = load_manifest(PORTABLE_MANIFEST)

    assert manifest["$schema"] == SCHEMA_URI
    assert set(manifest) <= ALLOWED_FIELDS
    assert validate_manifest(manifest) == []


def test_portable_and_codex_manifests_share_release_metadata() -> None:
    portable = load_manifest(PORTABLE_MANIFEST)
    codex = load_manifest(CODEX_MANIFEST)

    shared_fields = {
        "name",
        "version",
        "description",
        "author",
        "homepage",
        "repository",
        "license",
        "keywords",
    }
    assert {field: portable[field] for field in shared_fields} == {
        field: codex[field] for field in shared_fields
    }
    assert {"skills", "interface"} <= set(codex)
    assert {"skills", "interface"}.isdisjoint(portable)


def test_portable_skill_uses_fixed_agent_plugins_discovery_layout() -> None:
    skill_root = REPO_ROOT / "skills/learn-up"
    skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")

    assert skill_root.is_dir()
    assert skill.startswith("---\nname: learn-up\ndescription:")
    assert skill.count("\n---\n") >= 1


@pytest.mark.parametrize(
    "name",
    ["", "Learn-Up", "-learn-up", "learn-up-", "learn--up", "learn..up"],
)
def test_validator_rejects_invalid_plugin_names(name: str) -> None:
    assert validate_manifest({"$schema": SCHEMA_URI, "name": name})


def test_validator_rejects_closed_schema_violations() -> None:
    manifest = load_manifest(PORTABLE_MANIFEST)
    manifest["skills"] = "./skills"

    assert validate_manifest(manifest) == ["unknown top-level fields: skills"]


def test_offline_validator_cli_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/validate_agent_plugin.py")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Agent Plugins 1.0.0 validation passed" in result.stdout
    assert result.stderr == ""
