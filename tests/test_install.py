from __future__ import annotations

import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

import learn_up_installer as install

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SKILL = REPO_ROOT / "skills" / install.SKILL_NAME


def args(
    *,
    agent: str = "codex",
    scope: str = "project",
    project_dir: Path | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> Namespace:
    return Namespace(
        agent=agent,
        scope=scope,
        project_dir=project_dir,
        force=force,
        dry_run=dry_run,
    )


def tree_snapshot(root: Path) -> dict[Path, bytes]:
    return {
        path.relative_to(root): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@pytest.mark.parametrize(
    ("agent", "relative_target"),
    [
        ("codex", Path(".agents/skills/learn-up")),
        ("claude-code", Path(".claude/skills/learn-up")),
    ],
)
def test_user_destination_uses_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    agent: str,
    relative_target: Path,
) -> None:
    fake_home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    assert (
        install.destination(args(agent=agent, scope="user"))
        == fake_home / relative_target
    )


def test_project_destination_uses_explicit_directory(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    target = install.destination(args(project_dir=project))

    assert target == project.resolve() / ".agents/skills/learn-up"


def test_project_destination_defaults_to_current_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    target = install.destination(args())

    assert target == project.resolve() / ".agents/skills/learn-up"


def test_user_scope_rejects_project_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="only valid with --scope project"):
        install.destination(args(scope="user", project_dir=tmp_path))


def test_project_scope_rejects_missing_directory(tmp_path: Path) -> None:
    missing = tmp_path / "missing"

    with pytest.raises(ValueError, match="Project directory does not exist"):
        install.destination(args(project_dir=missing))


@pytest.mark.parametrize("agent", ["codex", "claude-code"])
def test_dry_run_creates_no_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, agent: str
) -> None:
    fake_home = tmp_path / "home-that-does-not-exist"
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    target = install.install(args(agent=agent, scope="user", dry_run=True))

    assert target.is_relative_to(fake_home)
    assert not fake_home.exists()


def test_successful_codex_installation(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    target = install.install(args(project_dir=project))

    assert target == project / ".agents/skills/learn-up"
    assert tree_snapshot(target) == tree_snapshot(CANONICAL_SKILL)


def test_claude_installation_adds_manual_invocation_policy(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    target = install.install(args(agent="claude-code", project_dir=project))
    target_skill = (target / "SKILL.md").read_text(encoding="utf-8")

    assert "\ndisable-model-invocation: true\n---\n" in target_skill
    assert "\ndisable-model-invocation:" not in (
        CANONICAL_SKILL / "SKILL.md"
    ).read_text(encoding="utf-8")


def test_existing_installation_is_not_overwritten_without_force(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    target = install.install(args(project_dir=project))
    marker = target / "local-change.txt"
    marker.write_text("keep me", encoding="utf-8")

    with pytest.raises(FileExistsError, match="Re-run with --force"):
        install.install(args(project_dir=project))

    assert marker.read_text(encoding="utf-8") == "keep me"
    assert not list(target.parent.glob("learn-up.backup-*"))


def test_force_preserves_backup_and_installs_fresh_copy(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    target = install.install(args(project_dir=project))
    marker = target / "local-change.txt"
    marker.write_text("preserved in backup", encoding="utf-8")

    updated_target = install.install(args(project_dir=project, force=True))

    backups = list(target.parent.glob("learn-up.backup-*"))
    assert updated_target == target
    assert len(backups) == 1
    assert (backups[0] / marker.name).read_text(
        encoding="utf-8"
    ) == "preserved in backup"
    assert not (updated_target / marker.name).exists()
    assert tree_snapshot(updated_target) == tree_snapshot(CANONICAL_SKILL)


def test_claude_installation_does_not_modify_canonical_skill(tmp_path: Path) -> None:
    before = tree_snapshot(CANONICAL_SKILL)
    project = tmp_path / "project"
    project.mkdir()

    install.install(args(agent="claude-code", project_dir=project))

    assert tree_snapshot(CANONICAL_SKILL) == before


@pytest.mark.parametrize("agent", ["codex", "claude-code"])
def test_host_manifests_are_not_copied_into_skill_installations(
    tmp_path: Path, agent: str
) -> None:
    project = tmp_path / "project"
    project.mkdir()

    target = install.install(args(agent=agent, project_dir=project))

    assert not (target / "plugin.json").exists()
    assert not (target / ".codex-plugin").exists()


def test_missing_skill_source_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    monkeypatch.setattr(
        install,
        "__file__",
        str(fake_repo / "learn_up_installer/__init__.py"),
    )
    project = tmp_path / "project"
    project.mkdir()

    with pytest.raises(FileNotFoundError, match="Skill source is missing"):
        install.install(args(project_dir=project))


def test_malformed_skill_frontmatter_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake_repo = tmp_path / "repo"
    source = fake_repo / "skills/learn-up"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_text("not valid frontmatter\n", encoding="utf-8")
    monkeypatch.setattr(
        install,
        "__file__",
        str(fake_repo / "learn_up_installer/__init__.py"),
    )
    project = tmp_path / "project"
    project.mkdir()

    with pytest.raises(ValueError, match="Could not locate YAML frontmatter"):
        install.install(args(agent="claude-code", project_dir=project))


def test_main_returns_success_for_dry_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_home = tmp_path / "home-that-does-not-exist"
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.setattr(sys, "argv", ["install.py", "--agent", "codex", "--dry-run"])

    assert install.main() == 0
    captured = capsys.readouterr()
    assert "Would install" in captured.out
    assert captured.err == ""
    assert not fake_home.exists()


def test_main_returns_error_for_invalid_destination(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "missing"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "install.py",
            "--agent",
            "codex",
            "--scope",
            "project",
            "--project-dir",
            str(missing),
        ],
    )

    assert install.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Project directory does not exist" in captured.err


def test_cli_process_uses_zero_and_nonzero_exit_codes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    success = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "install.py"),
            "--agent",
            "codex",
            "--scope",
            "project",
            "--project-dir",
            str(project),
            "--dry-run",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    failure = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "install.py"),
            "--agent",
            "codex",
            "--scope",
            "project",
            "--project-dir",
            str(tmp_path / "missing"),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert success.returncode == 0
    assert "Would install" in success.stdout
    assert success.stderr == ""
    assert failure.returncode == 1
    assert failure.stdout == ""
    assert "Project directory does not exist" in failure.stderr
