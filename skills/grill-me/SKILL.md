---
name: grill-me
description: Stress-test plans, designs, technical decisions, requirements, and product direction by asking pointed follow-up questions until assumptions, tradeoffs, risks, and decision dependencies are clear. Use when the user says "grill me," "dig deeper," "poke holes in this," or "pressure-test this," or otherwise requests rigorous questioning before proceeding. If the user asks for Markdown, a questionnaire, or a form they can answer all at once, combine this strategy with md-questionnaire. Ask which format they prefer when they do not specify chat or questionnaire mode.
---

# Grill Me

## Purpose

Interrogate a plan, design, or decision until weak assumptions and unresolved dependencies are visible.
Prefer depth over breadth: follow one thread until it stops producing useful clarification, then move to the next.

## Format Selection

Choose the answer format before asking substantive questions.

- If the user asks for Markdown, a questionnaire, or another asynchronous batch format, use Markdown questionnaire mode.
- If the user asks for chat, one-by-one questions, or live discussion, use chat mode.
- If the user requests deep questioning without specifying a format, ask one format-selection question and wait.

Use this format-selection question:

```markdown
Choose a question format:

1. Explore one question at a time in chat
2. Answer a Markdown questionnaire all at once

**Recommendation:** 1 — Each answer can shape the next question, which makes it easier to expose design gaps. Choose 2 when uninterrupted time is difficult to schedule.
```

Do not begin the interrogation until the format is chosen unless the user's request already chooses it.

## Shared Rules

- Inspect relevant files, code, specifications, and prior context before asking.
  Do not ask what can be discovered.
- Ask questions that materially change the plan, design, implementation, or risk profile.
- Challenge vague answers.
  When an answer hides a tradeoff, ask for the missing constraint.
- Surface the decision dependency behind each question.
- Include a recommended answer or direction when there is a defensible default.
- Stop when additional questions are unlikely to change the outcome, then offer a summary.

## Chat Mode

Use this mode for live deep dives.

Ask exactly one substantive question at a time.

Question format:

```markdown
### Q<number>: <question>

<why this question matters>

- **A** — <option>
- **B** — <option>
- **C** — <option>

**Recommendation: <A/B/C>** — <reason>
```

After the user answers:

1. Test whether the answer resolves the dependency.
2. If it is vague, contradictory, or strategically weak, ask one sharper follow-up on the same thread.
3. If the thread is resolved, move to the next highest-impact unresolved thread.

## Markdown Questionnaire Mode

Use this mode when the user wants to answer in Markdown, a questionnaire, or all at once.

Follow the `md-questionnaire` skill for labels, numbered options, recommendations, `Answer:`, and `Rationale / Notes (optional):` fields.
If that skill is available, read its `SKILL.md` before creating the questionnaire.
If it is unavailable, use the template below.

Questionnaire rules:

1. Keep each round finite.
   Prefer five to ten questions.
2. Group questions by decision area, such as goal, user, scope, constraints, risk, implementation, rollout, or success criteria.
3. Include recommended answers while preserving free-text space when the decision space is open.
4. Tell the user which file to fill in and do not repeat the same questions in chat.

### Single-File Round Log

Use one Markdown file per grill-me session, not one file per round.
Name it descriptively, such as `grill_me_questionnaire.md` or `<topic>_grill_me.md`.

For each round:

- Append a new section to the same file.
- Do not overwrite or rewrite completed answers from earlier rounds.
- Number rounds explicitly with headings such as `## Round 1: Test Initial Assumptions` and `## Round 2: Resolve Remaining Ambiguity`.
- Number questions with round-qualified identifiers such as `R1-Q1`, `R1-Q2`, and `R2-Q1`.
- Add a short `Round purpose` field.
- For round two and later, add a `Connection from the previous round` field that names the prior answer, contradiction, risk, or unresolved dependency that produced the new questions.
- Add a compact `Question path` table when it helps trace the line of questioning.

Round template:

```markdown
## Round <N>: <focus>

- **Round purpose:** <why this round exists>
- **Connection from the previous round:** <prior answer, unresolved assumption, contradiction, or risk that led here>
- **Questions:** <n>
- **How to answer:** Enter a number or free-text answer after `Answer:`. If unsure, choose the recommended option.

### Question Path

| Starting point | Unresolved issue | Current question |
| --- | --- | --- |
| R1-Q2 | <unresolved issue> | R2-Q1 |

### R<N>-Q1: <decision name>

<question text>

1. <option> (Recommended | <short reason>)
2. <option> (Alternative | <short reason>)
3. Let the agent decide / Use the recommendation

Answer:

Rationale / Notes (optional):
```

Read [references/sample_questionnaire.md](references/sample_questionnaire.md) when a concrete single-file, multi-round example is needed.

Use rounds instead of one large questionnaire when uncertainty is deep:

- Round 1 exposes core assumptions and constraints.
- Read the completed answers in the same file.
- Round 2 appends only follow-up questions that depend on Round 1 answers.

## Summary

When the interrogation is complete, summarize it in this format:

```markdown
## Summary

### Decisions
- ...

### Remaining Risks
- ...

### Next Action
- ...
```
