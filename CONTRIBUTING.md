# Contributing to learn-up

Thank you for helping make `learn-up` more reliable and easier to use.

## Before opening an issue

Search existing issues, then include:

- Agent host and version: Claude Code, Codex CLI/IDE/desktop, or another host.
- Operating system and version.
- Whether the skill was installed for the user or one project.
- The exact invocation and the phase where the problem occurred.
- The smallest useful error output, with secrets and private source content removed.
- Whether the issue reproduces with authoritative public material.

Do not upload proprietary study material, API keys, `.env` files, NotebookLM cookies, or generated
databases.

## Pull requests

Keep changes focused. For skill workflow changes:

1. Explain the user-visible problem with a reproducible example.
2. Preserve source grounding, explicit provider selection, and fail-loud validation.
3. Keep the canonical `SKILL.md` compatible with the core Agent Skills format; put host-specific
   policy in host metadata or the installer.
4. Update references instead of duplicating long guidance in `SKILL.md`.
5. Keep portable metadata in root `plugin.json`, Codex-only metadata in
   `.codex-plugin/plugin.json`, and synchronize shared release fields between them.
6. Validate the Agent Plugins manifest with `python3 scripts/validate_agent_plugin.py`.
7. Test the installer for both supported agents and validate the canonical skill folder with
   `uv run python scripts/quick_validate.py skills/learn-up`.
8. State which operating systems and agent hosts you actually tested.

Do not weaken a validator to make malformed content pass. Fix the content or the implementation
that generated it.
