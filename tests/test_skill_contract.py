from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills/learn-up"


def read_skill_file(relative_path: str) -> str:
    return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")


def test_about_reference_defines_initial_compatibility_version() -> None:
    about = read_skill_file("references/about.md")
    tech_stack = read_skill_file("references/tech-stack.md")

    assert "initial generated version to `1.0`" in about
    assert 'version = "1.0"' in about
    assert 'version = "1.0"' in tech_stack
    assert "content/` and `media/` directories" in about


def test_about_api_exposes_complete_configuration_and_sources() -> None:
    backend = read_skill_file("references/backend.md")
    frontend = read_skill_file("references/frontend.md")

    required_fields = {
        "app_version: str",
        "app_markdown: str",
        "intake_markdown: str",
        "sources_markdown: str",
        "content_changes_markdown: str",
    }
    assert "/api/t/{topic_slug}/about" in backend
    assert required_fields <= {line.strip() for line in backend.splitlines()}
    assert "every intake answer/configuration parameter" in frontend
    assert "every source entry" in frontend


def test_generated_agents_template_has_only_fillable_placeholders() -> None:
    template = read_skill_file("assets/agents.template.md")

    assert set(re.findall(r"<[^>]+>", template)) == {
        "<app_version>",
        "<faq_llm_backend>",
    }
    assert "Document **every app or content update**" in template
    assert "Increment `MINOR`" in template
    assert "Increment `MAJOR`" in template


def test_skill_requires_copying_and_validating_agents_template() -> None:
    skill = read_skill_file("SKILL.md")

    assert "copying `assets/agents.template.md`" in skill
    assert "fail if any angle-bracket template placeholder remains" in skill
    assert "`references/about.md`" in skill
