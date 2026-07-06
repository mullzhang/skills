---
name: fable-prompt-tuner
description: Rewrite a rough user request into a Claude Fable 5-ready prompt draft after consulting the current Claude Fable 5 prompting guide. Use when the user wants to prepare, organize, refine, or tune a prompt for Fable before deciding whether to run it.
---

# Fable Prompt Tuner

## Required Reference

Before drafting a prompt, open and read the current guidance at:

https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5

Use the live page for the Fable-specific prompting patterns. Do not rely on remembered guidance, and do not proceed as if the page was checked unless it was actually consulted during this skill run.

## Input

Use the following as the raw task request when present:

$ARGUMENTS

If no arguments are provided, use the current user message and relevant conversation context as the raw request.

## Workflow

1. Consult the required reference page.
2. Extract the user's task, desired outcome, context, constraints, and completion criteria from `$ARGUMENTS` or the current conversation.
3. Rewrite the request into a Fable-ready prompt draft using the current reference page.
4. Present the prompt to the user.
   - Return the prompt draft for the user to review or copy into their Fable run.
   - Do not send, execute, launch, or hand off the prompt to Fable.
   - Do not claim Fable has started, accepted, or run the task.

## Prompt Draft Constraints

- Treat the required reference page as guidance for drafting, not as task content for Fable.
  Do not include a sentence such as "follow the official Fable 5 prompting guide" or a URL to the guide in the generated prompt unless the user's target task itself requires that citation.
- Do not add instructions to use subagents, delegate subtasks, or run parallel agents unless the user explicitly asks for that behavior.
- Preserve the user's actual objective and practical constraints. Avoid adding scaffolding that describes how this skill was used to create the prompt.

## Output Shape

Respond exactly in this shape:

```text
Fable向けプロンプト案
[final prompt]
```
