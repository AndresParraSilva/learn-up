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


def test_skill_routes_transfer_runs_to_canonical_assets() -> None:
    skill = read_skill_file("SKILL.md")
    reference = read_skill_file("references/topic-transfer.md")

    assert "**TRANSFER** run" in skill
    assert "`references/topic-transfer.md`" in skill
    assert "`assets/topic_transfer/`" in skill
    assert "**verbatim**" in skill
    assert "manifest.yaml" in reference
    assert "learn-up-topic-transfer/1" in reference
    assert "`.md`, `.yaml`, and `.mp4`" in reference


def test_transfer_trust_and_version_rules_are_documented() -> None:
    warning = "Import learn-up topics only from people and sources you trust"
    about = read_skill_file("references/about.md")
    transfer = read_skill_file("references/topic-transfer.md")
    template = read_skill_file("assets/agents.template.md")

    assert warning in about
    assert warning in transfer
    assert warning in template
    assert "Different major: reject" in transfer
    assert "incoming minor greater than destination minor" in transfer
    assert "source-app snapshot only; never overwrite" in transfer
    assert "destination's root `ABOUT.md`" in transfer
    assert "merge well-formed unique Q&A" in template


def test_topic_transfer_assets_are_complete() -> None:
    expected = {
        "assets/topic_transfer/__init__.py",
        "assets/topic_transfer/core.py",
        "assets/topic_transfer/faq.py",
        "assets/topic_transfer/manifest.py",
        "assets/topic_transfer/types.py",
        "assets/manage_topic_transfer.py",
        "assets/topic_transfer_router.py",
        "assets/topicTransfer.ts",
        "assets/TopicTransferPanel.tsx",
        "assets/test_topic_transfer_contract.py",
    }

    assert all((SKILL_ROOT / relative).is_file() for relative in expected)


def test_generated_frontend_uses_canonical_logo() -> None:
    skill = read_skill_file("SKILL.md")
    frontend = read_skill_file("references/frontend.md")
    styles = read_skill_file("assets/index.css")
    agents_template = read_skill_file("assets/agents.template.md")
    logo = SKILL_ROOT / "assets/learn-up-logo.webp"

    logo_bytes = logo.read_bytes()
    assert logo_bytes.startswith(b"RIFF")
    assert logo_bytes[8:12] == b"WEBP"
    assert (
        "`assets/learn-up-logo.webp` → `frontend/public/learn-up-logo.webp` **verbatim**"
        in skill
    )
    assert (
        "assets/learn-up-logo.webp      → frontend/public/learn-up-logo.webp"
        in frontend
    )
    assert 'className="home-logo" src="/learn-up-logo.webp" alt="learn-up"' in frontend
    assert (
        'className="topbar__mark" to="/" aria-label="Back to topic picker"' in frontend
    )
    assert 'className="topbar__logo" src="/learn-up-logo.webp" alt=""' in frontend
    assert ".home-logo {" in styles
    assert ".topbar__logo {" in styles
    assert "`TopBar` home link" in agents_template


def test_selection_ask_panel_stays_inside_visual_viewport() -> None:
    component = read_skill_file("assets/SelectionAsk.tsx")
    frontend = read_skill_file("references/frontend.md")
    styles = read_skill_file("assets/index.css")

    assert "useLayoutEffect" in component
    assert "trigger.bottom + PANEL_GAP" in component
    assert "trigger.top - panelHeight - PANEL_GAP" in component
    assert "window.visualViewport" in component
    assert "new ResizeObserver(positionPanel)" in component
    assert 'window.addEventListener("resize", positionPanel)' in component
    assert 'visibility: panelLayout ? "visible" : "hidden"' in component
    assert "max-height: calc(100dvh - 1.5rem);" in styles
    assert "overflow-y: auto;" in styles
    assert "keeps it within the visual viewport" in frontend
    assert "action buttons remain reachable" in frontend


def test_drill_and_mock_question_labels_are_one_based() -> None:
    frontend = read_skill_file("references/frontend.md")
    agents_template = read_skill_file("assets/agents.template.md")

    assert "Number every learner-facing question from 1, never 0" in frontend
    assert "Question {currentIndex + 1} of {questions.length}" in frontend
    assert "`{index + 1}` inside every `.progress-nav__item`" in frontend
    assert "drill, mock, strategy-drill, and review question headings" in frontend
    assert (
        "never expose a raw array index or raw `position` as the visible ordinal"
        in frontend
    )
    assert (
        "Number learner-facing drill, mock, strategy-drill, and review questions from 1"
        in (agents_template)
    )
