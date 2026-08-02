from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL_NAME = "learn-up"
HOST_DIRS = {
    "codex": {"user": Path(".agents/skills"), "project": Path(".agents/skills")},
    "claude-code": {"user": Path(".claude/skills"), "project": Path(".claude/skills")},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install learn-up without overwriting an existing copy unexpectedly."
    )
    parser.add_argument("--agent", choices=sorted(HOST_DIRS), required=True)
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument(
        "--project-dir",
        type=Path,
        help="Project root for --scope project (defaults to the current directory).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Update an existing install after moving it to a timestamped backup.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def destination(args: argparse.Namespace) -> Path:
    if args.scope == "user":
        if args.project_dir is not None:
            raise ValueError("--project-dir is only valid with --scope project")
        root = Path.home()
    else:
        root = (args.project_dir or Path.cwd()).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"Project directory does not exist: {root}")
    return root / HOST_DIRS[args.agent][args.scope] / SKILL_NAME


def add_claude_policy(skill_md: Path) -> None:
    content = skill_md.read_text(encoding="utf-8")
    marker = "\n---\n"
    end = content.find(marker, 4)
    if end == -1:
        raise ValueError(f"Could not locate YAML frontmatter in {skill_md}")
    frontmatter = content[:end]
    if "\ndisable-model-invocation:" not in frontmatter:
        frontmatter += "\ndisable-model-invocation: true"
    skill_md.write_text(frontmatter + content[end:], encoding="utf-8")


def install(args: argparse.Namespace) -> Path:
    source = Path(__file__).resolve().parents[1] / "skills" / SKILL_NAME
    if not (source / "SKILL.md").is_file():
        raise FileNotFoundError(f"Skill source is missing: {source / 'SKILL.md'}")

    target = destination(args)
    if args.dry_run:
        print(f"Would install {source} to {target}")
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if not args.force:
            raise FileExistsError(
                f"An installation already exists at {target}. Re-run with --force to update it."
            )
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = target.with_name(f"{SKILL_NAME}.backup-{stamp}")
        target.rename(backup)
        print(f"Previous installation preserved at {backup}")

    shutil.copytree(source, target)
    if args.agent == "claude-code":
        add_claude_policy(target / "SKILL.md")
    return target


def main() -> int:
    args = parse_args()
    try:
        target = install(args)
    except (FileExistsError, FileNotFoundError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if not args.dry_run:
        print(f"Installed learn-up at {target}")
    return 0
