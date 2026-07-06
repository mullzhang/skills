---
name: grill-me
description: Stress-test plans, designs, technical decisions, requirements, and product direction by asking pointed follow-up questions until the assumptions, tradeoffs, risks, and decision dependencies are clear. Use when the user says "grill me", "dig", "深掘りして", "徹底的に質問して", "穴を突いて", "詰めて", asks to pressure-test a plan or design, or wants rigorous questioning before proceeding. If the user asks for md, Markdown, 質問票, or まとめて回答したい, combine this questioning strategy with md-questionnaire and present the questions as a Markdown answer form. If the user does not specify chat vs Markdown/questionnaire format, ask which format they want before starting.
---

# Grill Me

## Purpose

Interrogate a plan, design, or decision until the weak assumptions and unresolved dependencies are visible. Prefer depth over breadth: follow one thread until it stops producing useful clarification, then move to the next.

## Format Selection

Before asking substantive questions, decide the answer format.

- If the user explicitly asks for `md`, `Markdown`, `質問票`, `まとめて回答したい`, or similar async/batch wording, use Markdown questionnaire mode.
- If the user explicitly asks for chat, one-by-one questions, live discussion, or similar wording, use chat mode.
- If the user requests grill-me/deep questioning but does not specify a format, ask one format-selection question and wait.

Format-selection question:

```markdown
質問形式を選んでください。

1. チャットで1問ずつ深掘りする
2. Markdown質問票にしてまとめて回答する

**推奨:** 1 — 不明点に応じて次の質問を変えられるため、設計の穴を深く掘りやすいです。まとまった時間が取りにくい場合は2が向いています。
```

Do not begin the interrogation until the format is chosen, unless the user's request already chooses it.

## Shared Rules

- Inspect relevant files, code, specs, or prior context before asking. Do not ask what can be discovered.
- Ask questions that materially change the plan, design, implementation, or risk profile.
- Challenge vague answers. When an answer hides a tradeoff, ask for the missing constraint.
- Surface the decision dependency behind each question.
- Include a recommended answer or direction when there is a defensible default.
- Stop when additional questions are unlikely to change the outcome, then offer a summary.

## Chat Mode

Use this mode for live deep-dives.

Ask exactly one substantive question at a time.

Question format:

```markdown
### Q<番号>: <質問文>

<なぜこの質問が重要か>

- **A** — <選択肢>
- **B** — <選択肢>
- **C** — <選択肢>

**推奨: <A/B/C>** — <理由>
```

After the user answers:

1. Test whether the answer resolves the dependency.
2. If it is vague, contradictory, or strategically weak, ask one sharper follow-up on the same thread.
3. If the thread is resolved, move to the next highest-impact unresolved thread.

## Markdown Questionnaire Mode

Use this mode when the user wants to answer in `md`, a `質問票`, or all at once.

Question formatting (Japanese labels, numbered options with a recommendation, `回答:` and `理由/補足（任意）:` fields) follows the `md-questionnaire` skill. If it is available, read and follow its `SKILL.md` before creating the questionnaire file. If it is not, the round template below already follows the same conventions, so use it as-is.

Rules for questionnaire content:

1. Keep each round finite. Prefer 5-10 questions for one round.
2. Group questions by decision area, such as goal, user, scope, constraints, risk, implementation, rollout, or success criteria.
3. Include recommended answers, but preserve room for free-text where the decision space is open.
4. Tell the user which file to fill in and do not continue asking the same questions conversationally.

### Single-File Round Log

This round log is what grill-me adds on top of md-questionnaire's answer-form conventions. Use one Markdown file per grill-me session, not one file per round. Name it descriptively, such as `grill_me_questionnaire.md` or `<topic>_grill_me.md`.

For each new round:

- Append a new section to the same file.
- Do not overwrite or rewrite completed answers from earlier rounds.
- Number rounds explicitly with headings such as `## ラウンド1: 初期仮説の確認` and `## ラウンド2: 残った曖昧さの深掘り`.
- Number questions with round-qualified IDs such as `R1-Q1`, `R1-Q2`, `R2-Q1`.
- Add a short `このラウンドの目的` field explaining why this round exists.
- For round 2 and later, add a `前ラウンドからの接続` field that names the prior answer, contradiction, risk, or unresolved dependency that produced the new questions.
- Add a compact `深掘り経路` table when it helps trace the line of questioning.

Round section template:

```markdown
## ラウンド<N>: <focus>

- **このラウンドの目的:** <why this round exists>
- **前ラウンドからの接続:** <Round 1 answer, unresolved assumption, contradiction, or risk that led here>
- **質問数:** <n>問
- **回答方法:** `回答:` に番号または文章を記入してください。迷う場合は推奨案の番号で構いません。

### 深掘り経路

| 起点 | 残った論点 | 今回の質問 |
| --- | --- | --- |
| R1-Q2 | <unresolved issue> | R2-Q1 |

### R<N>-Q1: <decision name>

<question text>

1. <option>（推奨度: ★ | <short reason>）
2. <option>（推奨度: ○ | <short reason>）
3. AIに任せる / 推奨案で進める

回答:

理由/補足（任意）:
```

For a concrete single-file, multi-round questionnaire example, read `references/sample_questionnaire.md` when needed.

For deep uncertainty, use rounds instead of one huge questionnaire:

- Round 1: expose the core assumptions and constraints.
- Read the completed answers in the same file.
- Round 2: append only follow-up questions that depend on Round 1 answers.

## Summary

When the interrogation is complete, summarize in this format:

```markdown
## まとめ

### 決まったこと
- ...

### 残っているリスク
- ...

### 次の一手
- ...
```
