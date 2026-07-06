# skills

Personal AI agent skills by mullzhang.

## Install

Install all skills with APM:

```bash
apm install mullzhang/skills
```

Install a single skill:

```bash
apm install mullzhang/skills --skill github-issue-dupe-check
```

Update installed skills to the latest version:

```bash
apm update
```

Force a fresh fetch if the cached copy looks stale:

```bash
apm install mullzhang/skills --refresh
```

## Path Convention

APM installs each skill into the runtime's skills directory (for Claude Code: `~/.claude/skills/<skill-name>/`).

`<path-to-this-skill>` in SKILL.md examples means the installed skill directory, i.e. the directory containing that SKILL.md. Resolve it from the actual install location before running bundled scripts:

```bash
python ~/.claude/skills/github-issue-dupe-check/scripts/collect_issue_candidates.py ...
```

## Add a Skill

Place each skill directory directly under `skills/`:

```text
skills/<skill-name>/SKILL.md
```

Reference bundled scripts and references from SKILL.md as `<path-to-this-skill>/scripts/...` or `references/...`, never with an install-specific absolute path.
