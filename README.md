# learn-up

<img src="skills/learn-up/assets/favicon-512.png" alt="learn-up icon" width="200" />

Turn material you trust into a personal study web app—with lessons, explained quizzes, practical
exercises, spaced repetition, progress tracking, and optional Gemini Notebook video summaries.

`learn-up` is an Agent Skill for Claude Code and Codex. You tell it what you want to learn, answer
a short interview, and point it at your material. The skill gathers any missing authoritative
sources, proposes a syllabus for your approval, and builds a local app around that syllabus.

> [!IMPORTANT]
> `learn-up` can structure and explain source material; it cannot make weak material reliable.
> Results depend on the authority, completeness, and freshness of the sources you provide. Review
> generated content before relying on it for an exam, professional decision, or safety-critical use.

## What it builds

- A local React + FastAPI study app, with no external database to configure.
- A syllabus mapped to explicit objectives, so lessons and questions stay on scope.
- Lessons in the language you choose, even when the strongest sources are in another language.
- Quizzes that explain every option—not only the correct answer.
- Optional hands-on labs, mock exams, exam strategy, badges, and readiness tracking.
- Select-to-ask Q&A powered by your existing Claude or Codex login, or by an OpenHands-compatible
  hosted/local model.
- Optional Gemini Notebook video summaries, generated one lesson at a time.
- Multiple independent subjects in the same app.
- A complete per-topic About page showing app version, questionnaire/configuration answers, source
  provenance, and app/content change history.

## Real uses

These are projects the author has used `learn-up` for, not benchmark claims.

| Topic                 | What it demonstrated                                                                                                                                                                                     |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SnowPro Core COF-C03  | Certification-blueprint coverage, mock questions, and study strategy. Results were mixed when the supplied preparation material was uneven—an important limitation, not something the skill should hide. |
| OpenHands             | Turning changing technical documentation into structured lessons and labs.                                                                                                                               |
| GitHub Actions        | Practical, workflow-oriented learning with exercises and explained questions.                                                                                                                            |
| Armonía y Composición | Multilingual learning: authoritative material and authored lessons do not have to use the same language.                                                                                                 |

## Before you start

You do not need to write the app yourself, but this is not a one-click consumer course generator.
You need:

- Claude Code or Codex with permission to create files and run local commands.
- Python 3.12+, [`uv`](https://docs.astral.sh/uv/), Node.js, and npm for the generated app.
- Basic terminal comfort, especially when reviewing commands or resolving a local dependency.

Git and Python 3.10+ are needed only if you use the manual installer.

Gemini Notebook videos are optional. Their automated path uses an unofficial third-party client
for undocumented Google APIs and may break when Google changes them. The rest of the study app does
not depend on video generation.

## 60-second install

Paste the appropriate request into your coding agent.

### Codex

```text
Install the learn-up plugin from
https://github.com/AndresParraSilva/learn-up
for my user account. Preserve any existing installation as a backup, then verify that I can invoke
it with $learn-up.
```

### Claude Code

```text
Install the learn-up skill from
https://github.com/AndresParraSilva/learn-up/tree/main/skills/learn-up
as a user-level skill. Preserve any existing installation as a backup, then verify that I can
invoke it with /learn-up.
```

The Codex package is defined by `.codex-plugin/plugin.json`. Claude Code installs the shared
`skills/learn-up` folder directly.

### Manual or reproducible installation

Use the included installer when conversational installation is unavailable or when you want a
repeatable command for testing or CI:

```bash
git clone https://github.com/AndresParraSilva/learn-up.git
cd learn-up
# Codex
python install.py --agent codex

# Claude Code
python install.py --agent claude-code
```

On systems where Python is named `python3`, use that command instead. The installer copies only the
`learn-up` skill to your personal skills directory. If a previous installation exists, it stops
instead of overwriting it; add `--force` to update while preserving a timestamped backup.

To install only for one project:

```bash
python install.py --agent codex --scope project --project-dir /path/to/project
python install.py --agent claude-code --scope project --project-dir /path/to/project
```

## Create your first study app

Open the directory where you want the app to be created, start your coding agent, and enter one of
these prompts **inside the agent**, not in your shell:

### Codex

```text
$learn-up GitHub Actions
```

### Claude Code

```text
/learn-up GitHub Actions
```

Then:

1. Answer the short interview about your level, goal, materials, language, and preferred Q&A agent.
2. Review and approve the proposed syllabus.
3. Let the skill build, seed, validate, and smoke-test the app.
4. Open the local URLs it reports.

Try a more specific first prompt when you already know the outcome:

```text
Build a learn-up topic for SnowPro Core COF-C03. I have official exam material and want English
lessons, hands-on labs where relevant, and a certification-style mock exam.
```

## How source quality is handled

`learn-up` prefers official documentation, standards, primary sources, canonical texts, and
reputable references. It records source URLs, authority, freshness, language, and limitations in a
topic-level `SOURCES.md` file, including whether each source came from you or was gathered by the
agent. The generated About page renders that complete index alongside every intake answer. If an
objective lacks solid material, the correct behavior is to stop and tell you—not fill the gap from
model memory.

Generated apps start at compatibility version `1.0`. Backward-compatible app/content updates bump
the minor version; a change that prevents an existing `content/` and `media/` pair from being copied
into the updated app unchanged bumps the major version. The generated `AGENTS.md` makes About-page
documentation and this compatibility check mandatory for later maintenance.

For certification topics, use the current official exam guide or blueprint as the source of truth
for scope. Treat dumps, old prep books, and community question banks as secondary evidence.

## Compatibility

| Host                      | Status                                                | Invocation                     | Notes                                                                                                                               |
| ------------------------- | ----------------------------------------------------- | ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| Claude Code               | Supported                                             | `/learn-up <topic>`            | Installer adds Claude's manual-invocation flag to the installed copy.                                                               |
| Codex CLI / IDE / desktop | Supported                                             | `$learn-up <topic>`            | Uses the open Agent Skills layout and Codex UI metadata.                                                                            |
| Other Agent Skills hosts  | Expected, not verified                                | Host-specific                  | Requires filesystem editing, shell execution, and web access; install `skills/learn-up` using the host's documented skill location. |
| ChatGPT Work on the web   | Plugin package ready; marketplace publication pending | `@learn-up` after installation | The repository includes a valid Codex plugin manifest, but public marketplace listing is a separate release step.                   |

The canonical skill follows the shared Agent Skills structure and keeps host-specific policy out of
`SKILL.md`. See the current [Claude Code skill documentation](https://code.claude.com/docs/en/skills)
and [Codex skill documentation](https://learn.chatgpt.com/docs/build-skills) for host behavior.

## What the skill contains

```text
.codex-plugin/plugin.json     Codex plugin manifest
skills/learn-up/
├── SKILL.md                  Core phased workflow
├── agents/openai.yaml        Codex/ChatGPT display and invocation policy
├── references/               Intake, sources, schema, backend, frontend, and video guidance
└── assets/                   Reusable app components, styles, icons, and scripts
```

Detailed files load only when the agent reaches the relevant phase, keeping the initial context
smaller despite the skill's breadth.

## Safety and privacy

- Review the skill before installing it, as you should with any agent workflow that can create
  files and run commands.
- Study sources remain local unless you choose a feature that sends them to an LLM provider or
  Gemini Notebook.
- Do not commit `.env` files, API keys, generated databases, videos, or NotebookLM session cookies.
- The app is designed for one local user. Do not expose it publicly without adding authentication,
  authorization, hardening, and a production deployment design.

See [SECURITY.md](SECURITY.md) for reporting and operational details.

## Contributing

Issues and focused pull requests are welcome. The most useful contributions are clean-install
reports on additional operating systems and agent hosts, source-quality safeguards, and reproducible
bug reports. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
