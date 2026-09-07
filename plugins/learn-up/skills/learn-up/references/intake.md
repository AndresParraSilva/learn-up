# Phase 1 — Intake

## Contents

- Exported-topic intake
- Cross-host interview behavior
- Learner, objective, material, language, and backend questions
- Optional module selection
- Certification facts and intake record

## Exported-topic intake

For a ZIP-path or archive-URL invocation, first stage and inspect the export through
`references/topic-transfer.md`. Its existing topic configuration replaces the topic interview.
Skip questions 1–6 below and all topic, deadline, certification, module-selection, exam-fact,
and sizing follow-ups. Do not ask the recipient to confirm the syllabus or choose a topic name.
Use the archive's manifest for identity, its syllabus for runtime topic settings, and its intake
for the source author's recorded knowledge level, objective, and constraints. Keep the exact
content language and `notebooklm_output_language`; do not query NotebookLM just to reselect them.
Missing, malformed, or inconsistent required topic data fails validation rather than triggering
new answers or silent defaults.

For a new app, ask question 7 only if the recipient has not already selected the FAQ backend.
Resolve any other missing destination app configuration without reopening topic questions.
An exported backend preference describes the source app and does not authorize using that provider
for the recipient. For an existing app, retain its backend and other app settings without asking
again. Do not copy credentials, account/profile state, or provider configuration from an archive.

Preserve imported `sources/<topic_slug>/INTAKE.md` verbatim as source configuration provenance.
Do not fill it with `Not applicable`, attribute the original answers to the recipient, or overwrite
its backend row. Record recipient answers and supplied app constraints in root `ABOUT.md` under
`## Destination configuration`, including the actual `faq_llm_backend` and that topic configuration
was imported. About already renders this file; no extra API field is needed. A difference between
the historical imported backend and the destination backend is expected, not an intake validation
error. All remaining interview and intake-writing instructions below apply to authored topics.

## Cross-host interview behavior

Run a short structured interview. Prefer the host's interactive selection/question UI when one is
available. Respect that UI's per-call limits and issue independent question groups together when
the host supports parallel calls. If there is no interactive UI, ask the same questions directly
in chat in one compact, numbered message. The user should experience one interview, not a main
interview followed by a separate, later "oh, one more thing" ask.
Goal: learn enough to size and shape the app. Do not author anything yet.

## Questions to ask

Ask these, grouped for the available interaction surface:

1. **Current knowledge** (`header: "Level"`, single-select)
   - Options: `New to it` / `Some background` / `Strong, filling gaps`.
   - Drives lesson depth: novices get more foundational lessons and explicit prerequisites;
     strong learners get denser lessons and harder questions.

2. **Objective** (`header: "Goal"`, single-select with an "Other" escape, or just capture free text)
   - Offer common shapes: `Pass a certification exam` / `Practical skill / build things` /
     `General understanding` / `Interview prep`. The user's free-text via "Other" is captured verbatim.
   - If they pick "certification exam", you'll enable the exam modules (below) and must capture the
     **real** exam facts.

3. **Hands-on practice?** (`header: "Labs"`, single-select)
   - `Yes — include exercises` / `No — reading + quizzes only`.
   - "Yes" enables the **labs** module (guided self-check exercises).

4. **Existing material?** (`header: "Material"`, single-select)
   - `I'll add files now` / `Just search the web` / `I have URLs to share`.
   - If they'll add files, tell them the exact path: `sources/<topic_slug>/`. Wait for confirmation
     that they've dropped files (or given URLs) before Phase 2 finishes.

5. **Content language** (`header: "Language"`, single-select with an "Other" escape for free text)
   - Options: `English` / whatever language is obviously implied by the conversation so far (e.g. if
     the user has been writing to you in Spanish, offer `Spanish` as the second option) / `Other`.
   - Default to `English` if there's no signal either way — don't make the user think about this
     unnecessarily when it's obviously going to be English.
   - This sets the language of **every authored artifact for this topic only**: `syllabus.yaml`
     titles/topics, lesson bodies, question stems/choices/explanations, lab scenarios/tasks, mock
     content, and the language you search for sources in (Phase 2). It does **not** change the app's
     UI chrome (nav labels, buttons, page titles) — that stays exactly as already built (English, per
     `references/frontend.md`, unless a prior topic in this same repo already changed it). On an
     ADD-TOPIC run into an existing repo, see `references/multi-topic.md`'s "Content language across
     topics" section for what this means when topics don't share a language.
   - The mandatory Gemini Notebook video placeholder text (Phase 4) is exempt from translation — keep
     it verbatim in English regardless of content language. It's a fixed instruction/prompt string fed
     to both the learner and Gemini Notebook, not narrative content, and golden rule 4 requires the
     exact text.

6. **NotebookLM output language** (`header: "Video locale"`, single-select)
   - This is the locale NotebookLM uses for generated narration and on-screen text. It is separate
     from the human-readable authoring language because regional variants matter.
   - Get the current supported choices from `notebooklm language list --json`, using the configured
     profile when this is an existing app. If the CLI is not installed yet, consult the current
     `notebooklm-py` CLI documentation. Never invent or normalize a locale code.
   - Offer the closest supported locale first, followed by relevant regional alternatives. Include
     the exact code in each label, such as `Español (Latinoamérica) — es_419`, `Español — es`, or
     `Español (México) — es_MX`. For English, use `English — en`.
   - Record the selected exact code as `notebooklm_output_language`.

7. **FAQ LLM backend** (`header: "Study Q&A"`, single-select)
   - Inspect which supported authenticated CLI is driving or available in the current environment.
   - Consider `claude`, `codex`, and `agy` (Antigravity). If exactly one is available,
     recommend its matching backend and confirm the user's choice; presence on PATH alone
     does not establish authentication.
   - When multiple CLIs are available, offer their matching choices (`Claude CLI`, `Codex CLI`,
     `Antigravity CLI`) plus `OpenHands or local model`. Prefer the authenticated CLI already in use.
   - If none is available, offer installing/authenticating a supported CLI or configuring
     OpenHands with a hosted or local LiteLLM-compatible provider.
   - Record the exact value as `faq_llm_backend`: `claude_cli`, `codex_cli`,
     `antigravity_cli`, or `openhands`.
   - Never auto-fallback at runtime. Provider changes can alter cost and privacy expectations.

## Module toggles (decide from the answers)

| Module                | Enable when                                             | Effect                                                                       |
| --------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------- |
| **mock / assessment** | goal is a real cert exam, OR user asks for a final test | a fixed, weighted, timed comprehensive assessment (`mocks/<code>.yaml`)      |
| **strategy**          | goal is a real cert exam                                | exam-taking meta content (time mgmt, elimination, gotchas) in its own tables |
| **labs**              | topic is practical / hands-on was "Yes"                 | guided self-check exercises per objective                                    |

If it's NOT a certification topic, keep **strategy** off and make the **mock** an optional
"comprehensive assessment" with sensible defaults (cover all domains, weighted; e.g. 40–60
questions, no scaled score — just percent-correct and a pass threshold you propose, default 75%).

## Capture exam facts (only if certification)

If the goal is a real exam, capture and later encode as constants (see `references/backend.md`):
question count, time limit, pass mark (raw %, or scaled score + max + pass), and whether wrong
answers are penalized. Use the exam's **actual** published numbers — ask the user or find them in
Phase 2. Do not invent them.

## Write it down

Create `sources/<topic_slug>/INTAKE.md` as the exhaustive, human-readable configuration record that
the generated About page renders. Record every question and answer from the interview, every
follow-up answer, and every configuration constraint the user supplied before or during the build.
Do not keep an answer only in chat or agent memory.

Use this minimum structure, adding rows rather than omitting information:

```markdown
# Intake — <Topic>

## Configuration

| Parameter                  | Value                                                  |
| -------------------------- | ------------------------------------------------------ |
| Topic                      | <topic>                                                |
| Topic slug                 | <topic_slug>                                           |
| Current knowledge          | <answer>                                               |
| Objective                  | <verbatim answer>                                      |
| Deadline                   | <answer or Not applicable>                             |
| Existing material          | <answer, paths, and/or URLs>                           |
| Content language           | <answer>                                               |
| NotebookLM output language | <exact locale code>                                    |
| FAQ LLM backend            | <claude_cli, codex_cli, antigravity_cli, or openhands> |
| Assessment enabled         | <true or false>                                        |
| Strategy enabled           | <true or false>                                        |
| Labs enabled               | <true or false>                                        |
| Topic sizing               | <small, medium, or large and the confirmed scope>      |

## Exam facts

<Every captured certification fact, or "Not applicable — not a certification topic.">

## Additional constraints and preferences

<Every other user-provided parameter or "None provided.">
```

Preserve free-form answers verbatim. Use `Not applicable` only when a question genuinely does not
apply; never use it to hide a question that was skipped. Do not record credentials, tokens, API
keys, or secret environment values. Record only the relevant environment-variable name and intended
configuration state when a feature requires a secret. This file is the contract the rest of the
build follows and must remain synchronized with the generated About page through
`references/about.md`'s endpoint.

## Sizing hint (feeds Phase 3)

Ask yourself, given the objective and knowledge level, roughly how many hours of study this is:

- **Small** (a focused subject, a single tool, one concept area) → **1 domain**, 3–6 subdomains.
- **Medium/Large** (a broad field, a certification, a language/framework) → **2–10 domains**, each
  with 3–8 subdomains. Never exceed 10 domains — consolidate instead.
  Confirm the size read with the user in Phase 3 before committing.
