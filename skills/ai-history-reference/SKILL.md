---
name: ai-history-reference
description: Search and read locally archived AI conversation histories from ChatGPT Chat Markdown exports and SpecStory Markdown exports for Codex or Work. Use whenever the user asks to reference, find, continue from, compare with, or summarize a previous ChatGPT, Work, Codex, or SpecStory conversation, including requests that identify a conversation by title, URL, topic, project, conversation ID, or session ID.
---

# AI History Reference

Search only the central local archives below. Resolve the archive root from `AI_HISTORY_ROOT`; when it is unset, use `~/ai-history`. Do not depend on files inside individual project directories.

- ChatGPT Chat exports: `<history-root>/chatgpt-chat/`
- SpecStory exports for Codex and Work: `<history-root>/specstory/`

Treat archived conversations as records of past discussion, not as authoritative evidence for facts that may have changed.

## Workflow

1. Identify any source hint, title, URL, conversation ID, session ID, project name, date, or topic in the request.
2. Run `scripts/find_history.py` against both archives unless the user limits the source.
3. Prefer matches in this order:
   - exact conversation ID or session ID;
   - exact URL;
   - exact title;
   - title or filename containing the requested text;
   - body text containing the requested text.
4. If one clear candidate remains, read that Markdown file.
5. If the file is large, inspect its metadata and heading structure first, then read the relevant `Prompt`/`Response` sections. Do not load an entire long transcript when a narrower section answers the request.
6. If multiple plausible candidates remain and they could lead to different conclusions, show their titles, dates, sources, and absolute paths, then ask the user which one to use.
7. Use the selected history as context for the current task. Distinguish past decisions and assumptions from current verified facts.
8. End every answer that used a history with a localized `Referenced histories` section.

## Search

Run a title or topic search:

```bash
python <skill-dir>/scripts/find_history.py "previous architecture discussion"
```

Search only ChatGPT Chat exports:

```bash
python <skill-dir>/scripts/find_history.py "previous architecture discussion" --source chatgpt
```

Search only SpecStory exports:

```bash
python <skill-dir>/scripts/find_history.py "deployment investigation" --source specstory
```

Search by conversation or session ID:

```bash
python <skill-dir>/scripts/find_history.py --id "<conversation-or-session-id>"
```

The script returns JSON with ranked candidates, metadata, missing archive roots, and absolute paths. Use `rg -n` and `sed -n` to inspect relevant sections of the selected Markdown.

ChatGPT browser exports may use this structure:

```markdown
# Conversation title

**Created:** ...
**Updated:** ...
**Exported:** ...
**Link:** [https://chatgpt.com/.../c/<conversation-id>](...)

## Prompt:
...

## Response:
...
```

Do not require YAML frontmatter. Extract the ChatGPT conversation ID from `**Link:**` when present.

## Missing or Ambiguous History

Never invent, reconstruct, or silently substitute a missing history. Respond in the user's language.

If a requested ChatGPT Chat history is absent:

1. State that the requested history was not found in the local archive.
2. Ask the user to open the conversation in ChatGPT and export it as Markdown with their browser extension.
3. Give `<history-root>/chatgpt-chat/` as the required destination.
4. Ask the user to repeat the request after exporting.
5. Report that no history was referenced.

If a requested Codex or Work history is absent:

1. State that the requested history was not found in the SpecStory archive.
2. Ask the user to locate the session with SpecStory and export it as Markdown.
3. Give `<history-root>/specstory/` as the required destination.
4. Ask the user to repeat the request after exporting.
5. Report that no history was referenced.

Offer these commands when useful:

```bash
specstory list codex --json
specstory sync codex -s <session-id> \
  --output-dir ~/ai-history/specstory \
  --no-cloud-sync
```

Explain that SpecStory has no dedicated `work` provider. A Work session is available through this route only when SpecStory recognizes it as a Codex-compatible session. Do not run browser exports or `specstory sync` automatically unless the user explicitly asks.

If `AI_HISTORY_ROOT` is configured, substitute its resolved value for `~/ai-history` in commands shown to the user.

If the source is unclear and neither archive contains the requested history, explain both export routes concisely.

## Reporting Sources

List every history whose content materially informed the answer. Use absolute, clickable local file links when the interface supports them. Localize the labels to the user's language.

Format each item as a Markdown link whose target is the absolute `path` returned by `find_history.py`, followed by the source, conversation or session ID, and relevant timestamps.

For SpecStory, report the session ID and timestamp when available. Do not list files that were merely searched but whose content did not inform the answer.

If no history was used, report `Referenced histories: none` in the user's language whenever the user explicitly requested a history reference.

## Safety

- Read only Markdown files under the two configured archive roots.
- Do not modify, move, rename, delete, or sync archive files as part of reference lookup.
- Do not access ChatGPT session cookies, private web APIs, or browser storage.
- Do not upload histories to SpecStory Cloud or any other service.
- Avoid exposing unrelated content from neighboring conversations.
- Re-verify laws, prices, product behavior, schedules, external service specifications, and other time-sensitive claims before presenting them as current.
