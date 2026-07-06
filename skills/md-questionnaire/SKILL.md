---
name: md-questionnaire
description: Create a finite Markdown questionnaire file that contains grouped questions, recommended options, answer fields, and optional rationale fields, then read the completed file and continue from the user's answers. Use when the agent needs to ask multiple questions (roughly 4 or more) for requirements, specifications, acceptance criteria, product decisions, design choices, implementation tradeoffs, or any situation where conversational back-and-forth would fatigue the user or make the remaining question count unclear.
---

# Markdown Questionnaire

## Skill Purpose

Present multiple clarifying questions as one Markdown answer form instead of asking them one by one in chat. After the user fills in the file, read the answers and continue with specification work, implementation, or decision-making based on the completed form.

## Use Criteria

Use this skill when at least one condition is true:

- There are 4 or more questions to ask.
- The answers will become decisions that should be referenced later, such as requirements, acceptance criteria, design choices, or implementation direction.
- The user can decide faster when options, tradeoffs, and a recommended answer are shown together.
- Sequential chat questions would make the user unsure how many questions remain.

Do not use this skill for a single blocking question. Ask that directly.

## Workflow

1. Decide the minimum question set.
   - Ask only questions that materially change the next action.
   - Prefer a clear recommended option when one option is better.
   - Include "AIに任せる / 推奨案で進める" when the user does not need to decide personally.

2. Create a Markdown questionnaire file.
   - If the project has a relevant spec or work directory, place it there.
   - Otherwise use the current working directory.
   - Use a descriptive filename such as `requirements_questionnaire.md`, `acceptance_criteria_questionnaire.md`, or `<feature>_questionnaire.md`.

3. Make the first screen calming and finite.
   - State the purpose in 1-2 lines.
   - State the total number of questions.
   - State how to answer: "Enter a number or free-text answer after `回答:`. If unsure, choose the recommended option."
   - Use Japanese labels in the questionnaire itself: `概要`, `目的`, `質問数`, `回答方法`, `質問N`, `回答`, and `理由/補足（任意）`.

4. Structure each question for fast decision-making.
   - Group related questions under headings.
   - Show each option on one line.
   - Mark the recommended option and explain the reason briefly.
   - Provide a clear answer field immediately after the options.
   - Provide an optional rationale field only when it may help.

5. Hand off to the user.
   - Tell the user which file to fill in.
   - Do not continue asking the same questions conversationally.
   - If the user cannot edit files, paste the Markdown content in the response instead.

6. After the user says the file is completed, read it.
   - Extract every `回答:` field and any `理由/補足（任意）:` field.
   - Treat blank answers as "未回答".
   - If the recommended option was left in place only as an example, do not count it as an answer unless the user clearly selected it.

7. Continue with decisions.
   - Summarize the resolved decisions briefly.
   - Identify unanswered blockers only.
   - Make reasonable assumptions for non-blocking blanks and state them.
   - Ask follow-up questions only when proceeding would likely produce wrong work.

## Questionnaire Template

Use this structure and keep the questionnaire labels in Japanese:

```markdown
# <topic> 質問票

## 概要

- **目的:** <why these answers are needed>
- **質問数:** <n>問
- **回答方法:** `回答:` に番号または文章を記入してください。迷う場合は推奨案の番号で構いません。

---

## 質問1: <decision name>

<question text>

1. <option>（推奨度: ★ | <short reason>）
2. <option>（推奨度: ○ | <short reason>）
3. AIに任せる / 推奨案で進める

回答:

理由/補足（任意）:
```

For a concrete questionnaire example, read `references/sample_questionnaire.md` when needed.

## Question Design Rules

- Keep the whole questionnaire scannable. Prefer 5-10 focused questions over a long survey.
- Put the highest-impact decisions first.
- Use stable numbering so the user can answer quickly.
- Include concrete tradeoffs, not abstract preferences.
- Avoid asking for information that can be inferred from repository context, existing files, or prior messages.
- Avoid "Other" as a default escape hatch when a better option set exists. Use free-text only when the decision space is genuinely open.
- Prefer decisive recommendations over neutral option lists. The purpose is to reduce decision fatigue, not transfer all analysis to the user.

## Reading Completed Forms

When parsing a completed questionnaire:

1. Build a decision table with question title, answer, rationale, and impact.
2. Detect contradictions across answers and resolve them by asking the fewest possible follow-up questions.
3. Preserve user intent over the originally recommended option.
4. If answers are partial, proceed on non-blocking work and list assumptions.
5. Update or create downstream specification files only after confirming the answers are sufficient for that artifact.
