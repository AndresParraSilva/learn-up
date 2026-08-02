from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts/quick_validate.py"


def run_validator(skill_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(skill_dir)],
        text=True,
        capture_output=True,
        check=False,
    )


def write_skill(skill_dir: Path, content: str) -> None:
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


def test_canonical_skill_is_valid() -> None:
    result = run_validator(REPO_ROOT / "skills/learn-up")

    assert result.returncode == 0
    assert result.stdout == "Skill is valid!\n"
    assert result.stderr == ""


def test_missing_skill_file_is_rejected(tmp_path: Path) -> None:
    skill_dir = tmp_path / "missing-skill"
    skill_dir.mkdir()

    result = run_validator(skill_dir)

    assert result.returncode == 1
    assert result.stdout == "SKILL.md not found\n"


def test_malformed_frontmatter_is_rejected(tmp_path: Path) -> None:
    skill_dir = tmp_path / "malformed-skill"
    write_skill(skill_dir, "---\nname: malformed\ndescription: [\n---\n")

    result = run_validator(skill_dir)

    assert result.returncode == 1
    assert result.stdout.startswith("Invalid YAML in frontmatter:")


def test_invalid_skill_name_is_rejected(tmp_path: Path) -> None:
    skill_dir = tmp_path / "invalid-name"
    write_skill(
        skill_dir,
        "---\nname: Invalid_Name\ndescription: Example skill.\n---\n",
    )

    result = run_validator(skill_dir)

    assert result.returncode == 1
    assert "should be hyphen-case" in result.stdout
