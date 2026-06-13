---
name: lean-code
description: For early development phases. Prevent inferred compatibility behavior, excessive fallbacks, default-value fallbacks, aliases, and duplication. Use before generating, modifying, or refactoring code, specs, or workflow files.
---

# Lean Code Skill

## When to Use

Apply this skill whenever you generate, modify, or refactor code, specs, configuration, or workflow files.

## Core Rule

Compatibility is opt-in only.

Do not infer compatibility requirements. Unless backward compatibility, aliases, migration shims, silent fallbacks, or default-value fallbacks are explicitly required by the user or by an existing repository contract, do not consider compatibility and do not implement compatibility behavior.

If compatibility risk seems plausible but is not explicitly required, do not add a fallback. Surface the uncertainty briefly and proceed with the clean current-state implementation.

## Pre-Generation Checks (Mandatory Before Writing Code)

1. Is compatibility explicitly required by the user, a public API contract, a persisted-data migration requirement, repository docs, or existing tests? If not, do not consider compatibility.
2. Are you about to add an alias, shim, fallback, or default value to handle an old or guessed case? If compatibility was not explicitly required, remove it.
3. Does this logic already exist somewhere in the codebase? If yes, reuse it.

## Disallowed Patterns

If you are about to write any of the following patterns, stop and remove them first.

```python
# NG: Fallback to a legacy format that does not exist
if hasattr(obj, 'new_method'):
    obj.new_method()
else:
    obj.old_method()  # old_method does not exist

# NG: Alias for guessed compatibility
value = config.get('new_name') or config.get('old_name')

# NG: Defensive default value "just in case"
value = config.get('key', some_complex_fallback_logic())

# NG: Environment fallback that hides missing configuration
token = os.getenv('API_TOKEN', 'dev-token')

# NG: Same validation duplicated in two places
def create_user(name):
    if not name or len(name) > 100:  # Use validate_name()
        raise ValueError()

# NG: Optional arguments nobody uses
def process(data, legacy_mode=False, compat_version=None):
    ...
```

## Recommended Patterns

```python
# OK: Write directly
obj.new_method()

# OK: Use the current required name directly
value = config['new_name']

# OK: Raise an error when config is missing (do not hide issues)
value = config['key']

# OK: Require explicit configuration
token = os.environ['API_TOKEN']

# OK: Keep validation in one place
def validate_name(name):
    if not name or len(name) > 100:
        raise ValueError()

# OK: Keep only arguments needed now
def process(data):
    ...
```

## Post-Generation Self-Review

Before outputting code, ask yourself:

- Is there defensive logic that starts with "if ..."? Is that scenario actually possible now?
- Did I add compatibility behavior without an explicit compatibility requirement? If yes, remove it.
- Did I infer external users, persisted data needs, or old behavior from incomplete information? If yes, remove that assumption.
- Did I write the same logic twice?
- Is there code that can be removed without affecting current behavior? If yes, remove it.
