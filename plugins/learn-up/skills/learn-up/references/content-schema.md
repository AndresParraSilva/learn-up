# Phases 3–4 — Content schema

## Contents

- Syllabus structure and validation
- Lesson Markdown and video placeholders
- Explained question YAML
- Optional labs, assessments, and strategy content
- Coverage rules

All content is version-controlled YAML/Markdown under `content/<topic_slug>/`, seeded into DuckDB
by `app/content/seed.py` and checked by `app/content/validate.py`. Every lesson, question, and lab
is tagged with an `objective` code from that topic's `syllabus.yaml`. Off-syllabus content is not
allowed; the validator fails loudly on gaps and dangling tags.

**Author every piece of narrative text in this topic's `content_language`** (from
`sources/<topic_slug>/INTAKE.md`, Phase 1): domain/objective names and `topics:` lists in
`syllabus.yaml`, lesson bodies and "Why It Matters" sections, question stems/choices/explanations,
lab scenarios/tasks/expected results, and mock/changelog prose. Structural keys (`code`, `objective`,
`type`, `kind`, `external_id`, etc.) and file/directory names stay in plain ASCII regardless of
language, for filesystem and URL safety. The one exception is the mandatory Gemini Notebook
placeholder line below — keep it verbatim in English even in a non-English topic; see Phase 1's
language question for why.

`notebooklm_output_language` is separate from `content_language`: it is the exact locale code
selected from `notebooklm language list --json` for generated artifacts. Preserve regional choices
such as `es_419`; do not derive or guess this code from the human-readable content language.

```
content/<topic_slug>/
  syllabus.yaml                       # domains + objectives (the "blueprint")
  CHANGELOG.md                        # version + dated entries
  lessons/<objective>/<slug>.md
  questions/<objective>.yaml
  labs/<objective>/<slug>.yaml        # only if labs enabled
  mocks/<code>.yaml                   # only if mock/assessment enabled
  strategy/lessons/<topic>.md         # only if strategy enabled (cert topics)
  strategy/questions.yaml             # only if strategy enabled
```

---

## Phase 3 — `syllabus.yaml`

The source of truth for this topic's taxonomy. **Small topic → 1 domain**; **bigger → up to 10
domains** (e.g. `"1"`, `"2"`, etc.). Each domain has objectives (subdomains). `domains[].objectives[].code` (e.g. `"1.3"`) is
the natural key every other file references. Weights must sum to 100.

```yaml
topic_slug: ancient-rome
topic_name: Ancient Rome — Republic to Empire
content_language: English
notebooklm_output_language: en # exact code from `notebooklm language list --json`
syllabus_version: v1 # bump on taxonomy changes; stamped onto content
objective_summary: >
  A general-understanding path through Roman history, society, and legacy.
# Assessment facts. For a real certification, use the exam's published numbers.
# For a non-exam topic, this is an optional comprehensive self-assessment.
assessment:
  enabled: true
  question_count: 50
  minutes: 60
  scoring: percent # "percent" (pass_pct) or "scaled" (pass_score_scaled/max_score_scaled)
  pass_pct: 75
  penalty_for_wrong_answers: false
modules:
  labs: false
  strategy: false # true only for real certification exams
domains:
  - code: "1"
    name: The Roman Republic
    weight_pct: 40
    objectives:
      - code: "1.1"
        title: Founding myths and the early Republic
        topics:
          - Monarchy to Republic
          - The Struggle of the Orders
          - Consuls, Senate, assemblies
      - code: "1.2"
        title: Republican expansion and the Punic Wars
        topics: [Carthage, Hannibal, provincialization]
  - code: "2"
    name: The Roman Empire
    weight_pct: 60
    objectives:
      - code: "2.1"
        title: Augustus and the Principate
        topics: [Second Triumvirate, Pax Romana, imperial cult]
```

Rules the seeder enforces (fail loudly otherwise): domain `weight_pct` sums to 100; every domain has
`code`/`name`/`weight_pct`/`objectives`; every objective has `code`/`title`/`topics`; codes unique.

**Confirm the domain/objective outline with the user before authoring lessons.**

---

## Phase 4 — Lessons: `lessons/<objective>/<slug>.md`

Markdown with YAML frontmatter. The body is everything up to a `## Why It Matters` H2; the
"why it matters" section (the mental model / how to reason about it) is everything after.

**The very first line of the body is the mandatory Gemini Notebook video placeholder.** Replace
`<this document name>` with the `sources/<topic_slug>/` filename that best covers this lesson, and
`<topic_slug>`/`<slug>` with this lesson's own values (the same ones in its file path
`content/<topic_slug>/lessons/<objective>/<slug>.md`).

```markdown
---
objective: "1.1"
title: Founding Myths and the Early Republic
---

[placeholder]Upload this document and the documents in /sources to Gemini Notebook and ask it to create a video summary with the prompt "Limit the topics to what's in 01-early-republic.pdf.", then put it here. There's no drag-and-drop: click Generate Video above to do this automatically, or if you generate the video yourself, either ask your LLM assistant to place it, or do it yourself — save the download as media/ancient-rome/founding-myths-and-the-early-republic.mp4, replace this entire placeholder block with a markdown video link to that file, then re-seed the content.[/placeholder]

Rome's traditional founding date of 753 BCE sits between myth and history...

## Why It Matters

When a question asks _why_ an institution existed, trace it back to the Struggle of the Orders...
```

- The placeholder is rendered by the frontend as a styled call-out (see `references/frontend.md`),
  and once a video exists it's replaced with a Markdown link to the `.mp4` — the Markdown renderer
  turns any `.mp4` link into a `<video controls>`. There's also a "Generate Gemini Notebook video" button rendered
  above the placeholder while it's unresolved — see `references/frontend.md`. There are four ways
  to resolve a placeholder (the button, MCP-driven on request, a terminal script, or fully manual)
  — user-paced, one lesson at a time, never bulk; see `references/notebooklm-automation.md` for all
  four and the `/media/<topic_slug>/<slug>.mp4` convention they all land on.
- **Keep the added manual-placement sentence in plain prose — no Markdown syntax inside the
  `[placeholder]…[/placeholder]` span.** The frontend's placeholder-detection plugin
  (`remarkVideoPlaceholder.ts`) flattens that span to a single plain-text node by walking the
  already-parsed Markdown AST and concatenating only `text`-type node values; a real Markdown link,
  inline code span, or emphasis run inside the placeholder gets parsed into its own node type first
  and then silently dropped (its `value`/`url` never gets pulled back out). So describe the target
  path and the replacement line in words, don't write literal `[text](url)` or backtick syntax
  inside the placeholder text itself.
- Author the lesson depth to the user's stated knowledge level (Phase 1). Use Markdown freely:
  headings, tables, fenced code, and `mermaid` diagrams (the renderer supports Mermaid) —
  **outside** the placeholder span, where normal parsing applies.
- **Use a Markdown bullet or numbered list whenever the prose enumerates items** (a set of options,
  steps, causes, examples, etc.) instead of running them together in a single paragraph — it's
  easier to scan and matches how the rest of the app's Markdown (tables, headings) is already
  structured. Don't force a list where the text isn't actually enumerating something.
- Keep every lesson traceable to a `sources/` file.

---

## Phase 4 — Questions: `questions/<objective>.yaml`

One file per objective; one YAML list of that objective's questions. **Target 3–5 per objective**
(the validator requires ≥3). Every choice — including distractors — needs an `explanation`.
`type: multi` needs 2+ correct choices. Ensure the correct answer isn't consistently the longest option.
Make distractors roughly equal in length to the correct answer, or occasionally longer.
**This is checked automatically, not just by eye:** `tests/test_question_quality.py` scans every
question across all topics' `questions/*.yaml` (+ `strategy/questions.yaml` if present) and fails the
suite if the correct choice is the longest option in more than 2/3 of questions — run `uv run pytest`
after authoring/regenerating a batch of questions, and if it fails, lengthen some distractors (or
shorten the odd correct answer) on the questions it flags rather than tuning by feel.

**Every correct choice's `explanation` must start with the literal prefix `Correct — `** (em dash,
one space either side), e.g. `Correct — imperium was split between two annually elected consuls.`
Distractor explanations never get this prefix. This is an authoring convention the frontend depends
on: when showing a full rights-and-wrongs breakdown, it strips the prefix at display time for any
correct choice the learner did **not** select, leaving just the explanation sentence (see
`references/frontend.md`'s "Grading feedback" section) — add the prefix to a distractor and it will
permanently display as if correct; omit it from a genuine correct choice and the learner never sees
the "Correct — " affirmation on the choice(s) they actually got right.

```yaml
objective: "1.1"
questions:
  - external_id: "1.1-001" # stable id, never reuse/renumber once published
    type: single # single | multi
    difficulty: 2 # 1 (easy) – 5 (hard)
    is_mock_eligible: true # false = drill-only, excluded from the fixed assessment
    stem: |
      Which body held imperium in the early Republic?
    explanation: |
      Executive power (imperium) was vested in the annually elected consuls...
    choices:
      - text: The two consuls
        correct: true
        explanation: Correct — imperium was split between two annually elected consuls.
      - text: The Senate
        correct: false
        explanation: The Senate advised and controlled finances but held no imperium itself.
      - text: The Plebeian Council
        correct: false
        explanation: It passed plebiscites; it did not hold executive imperium.
```

---

## Phase 4 — Labs (only if enabled): `labs/<objective>/<slug>.yaml`

Guided self-check exercises. **No credentials are ever stored** — the app grades what the user
pastes back against structured checks. `expected_result` is human context; `self_check` is the
machine-graded list. Each `self_check` item becomes one text input, graded by `kind`:

| `kind`                         | Passes when…                                                                   | Needs `value`? |
| ------------------------------ | ------------------------------------------------------------------------------ | -------------- |
| `contains`                     | answer contains `value` (case-insensitive unless `case_sensitive: true`)       | yes            |
| `exact`                        | answer equals `value` exactly (case-insensitive unless `case_sensitive: true`) | yes            |
| `number_positive`              | answer parses as a number > 0                                                  | no             |
| `number_less_than_previous`    | answer is a number < the previous prompt's answer                              | no             |
| `number_greater_than_previous` | answer is a number > the previous prompt's answer                              | no             |

```yaml
objective: "2.1"
title: Trace an Aqueduct's Gradient
scenario: |
  You're modeling how Roman aqueducts moved water by gravity...
setup_sql: "" # optional; for code/tool topics put starter commands here
task: |
  Compute the drop over a 10 km run at a 0.15% gradient, then halve the gradient and recompute.
expected_result: |
  The gentler gradient yields a smaller drop for the same distance.
self_check:
  - prompt: Drop at 0.15% over 10 km (m)
    kind: number_positive
  - prompt: Drop at 0.075% over 10 km (m)
    kind: number_less_than_previous
```

For non-SQL topics, `setup_sql` may be empty or hold starter code/commands relevant to the craft;
it's shown to the learner as a code block, not executed.

---

## Phase 4 — Mock / assessment (only if enabled): `mocks/<code>.yaml`

A fixed, pre-assembled assessment (not randomly generated per attempt) so every attempt is
comparable. Question count per domain must match the `weight_pct` split in `syllabus.yaml`.

```yaml
code: full_mock_v1
syllabus_version: v1
questions:
  - "1.1-001"
  - "1.2-004"
  # ... external_ids totaling assessment.question_count, in presentation order
```

---

## Phase 4 — Strategy (only if enabled, cert topics): `strategy/…`

Exam-mechanics content (time management, process of elimination, multi-select strategy, gotchas,
scoring rules) — **not** subject knowledge, so it's tagged against a fixed `topic` list you define
in `app/constants.py` (`STRATEGY_TOPICS`) instead of a syllabus objective. Lives in its own tables,
never included in the mock, and doesn't feed mastery/readiness (but does feed the blended readiness
% at a small weight). Lesson frontmatter uses `topic` instead of `objective`; `strategy/questions.yaml`
is one flat list where each question carries a `topic`. Otherwise the schemas match lessons/questions.

---

## Coverage rule (the validator)

`app/content/validate.py` must fail loudly (non-zero exit) when, for the seeded topic(s):

- any objective has **< 1 lesson** or **< 3 questions**;
- if strategy enabled, any strategy `topic` has < 1 lesson or < `MIN_STRATEGY_QUESTIONS_PER_TOPIC`;
- any content file references an `objective`/`topic` not present in `syllabus.yaml`/`STRATEGY_TOPICS`;
- domain weights don't sum to 100, or exam facts don't match the encoded constants.

Also add a `content/<topic_slug>/CHANGELOG.md` with the `syllabus_version` and dated entries
(use today's date from Phase 0). The generated About page renders this file verbatim. Keep it
non-empty and document every later topic-content change here; follow `references/about.md` for the
separate app compatibility-version bump that accompanies every content change.

In addition to the coverage checks above, the validator must enforce the About data contract from
`references/about.md`: valid two-part app version, current version represented in root `ABOUT.md`,
and non-empty `INTAKE.md`, `SOURCES.md`, and `CHANGELOG.md` for every topic. Fail loudly rather than
rendering an incomplete About page.
It must also verify every canonical topic-transfer asset listed in
`references/topic-transfer.md` exists at its generated destination, the copied package exposes
`IMPLEMENTATION_ID = "learn-up-topic-transfer/1"`, and
`tests/test_topic_transfer_contract.py` is present. Fail rather than accepting a model-authored or
partially copied protocol implementation.
