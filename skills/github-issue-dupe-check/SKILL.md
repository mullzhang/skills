---
name: github-issue-dupe-check
description: Use before opening a GitHub issue to search for likely duplicates with gh, inspect candidate issues, and classify them as duplicate, related, or distinct. Use when drafting GitHub issues, checking whether a bug report already exists, responding to duplicate-bot comments, or deciding whether to comment on an existing issue instead of filing a new one.
---

# GitHub Issue Duplicate Check

Use this skill before opening a GitHub issue, or when a duplicate bot flags an issue after creation.

## Workflow

1. Identify the target repository (`owner/name`) and the draft issue title/body.
2. Search with both symptom language and implementation/internal terms. Do not rely on one query.
3. Run the candidate collector script: pass `--draft` when a draft file exists, or `--title`/`--body` otherwise.
4. Inspect likely candidates with `gh issue view`, including closed issues.
5. Classify each candidate as:
   - `duplicate`: same user-visible bug or likely same root cause; one issue should be closed.
   - `related`: overlapping area, but likely a separate fix or tracking item.
   - `distinct`: not materially related.
6. Recommend one action:
   - Open a new issue.
   - Comment on an existing issue instead.
   - Keep both issues but cross-link them.
   - Close the newer issue as duplicate after preserving useful diagnostics.

## Candidate Collection

Use the bundled script in this skill's `scripts/` directory (the directory containing this SKILL.md, wherever the skill is installed). It can run from any working directory:

```bash
python <path-to-this-skill>/scripts/collect_issue_candidates.py \
  --repo openai/codex \
  --draft path/to/issue-draft.md \
  --output /tmp/issue-dupe-candidates.json
```

If there is no draft file:

```bash
python <path-to-this-skill>/scripts/collect_issue_candidates.py \
  --repo openai/codex \
  --title "TUI $ autocomplete shows inaccessible App Directory entries" \
  --body "Typing $ shows irrelevant [App] suggestions from codex_app_directory..." \
  --output /tmp/issue-dupe-candidates.json
```

Then read the JSON and inspect the highest-signal candidates:

```bash
gh issue view 24145 --repo openai/codex --json number,title,state,url,body,comments
```

## Search Strategy

Always search at least these categories:

- User-visible symptom terms: words a reporter would use without knowing the root cause.
- UI surface terms: menu, autocomplete, slash menu, dollar sign, mention, composer.
- Internal terms from diagnostics: filenames, config keys, cache paths, error codes, class/function names.
- Exact odd strings: product names, localized text, unique error messages.

For large repositories, broad symptom queries often beat precise internal queries. In the Codex App Directory case, `codex_app_directory` missed the older issue, while `dollar sign menu bloated` found it.

## Judgment Rules

- Prefer `duplicate` when the same maintainer change would likely fix both reports.
- Prefer `related` when symptoms share a UI surface but involve different providers, commands, or lifecycle phases.
- Do not close a more diagnostic issue until its useful evidence is moved to the older issue.
- If a bot suggests a duplicate, verify manually before closing.
- When closing as duplicate, comment on the older issue first with the extra diagnostics, then close the newer issue.

## Comment Templates

Additional diagnostics on the older issue:

````markdown
I believe #NEW is a duplicate of this issue, but it includes additional diagnostics that may help narrow this down.

In my repro, the unexpected entries are present in:

```text
PATH_OR_CACHE
```

with entries like:

```json
{
  "key": "value"
}
```

This suggests SOURCE is being included in SURFACE.
````

Closing the newer issue:

```markdown
Closing this as a duplicate of #OLD. I added the relevant diagnostics there.
```

## Script Output

The collector writes JSON with:

- `repo`
- `queries`
- `candidates`
- `matchedQueries` per candidate
- issue details from `gh issue view` when available

Use that output as evidence, not as final judgment. The agent must still read and classify likely matches.
