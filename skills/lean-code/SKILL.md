---
name: lean-code
description: For early development phases. Prevent excessive fallbacks, backward compatibility code, and duplication during code generation. Use when generating, modifying, or refactoring code.
---

# Lean Code Skill

## When to Use

Apply this skill whenever you generate, modify, or refactor code.

## Pre-Generation Checks (Mandatory Before Writing Code)

1. Does this code have external users? If not, no fallback is needed.
2. Is there a concrete reason to support older versions? If not, no compatibility code is needed.
3. Does this logic already exist somewhere in the codebase? If yes, reuse it.

## Disallowed Patterns

If you are about to write any of the following patterns, stop and remove them first.

```python
# NG: Fallback to a legacy format that does not exist
if hasattr(obj, 'new_method'):
    obj.new_method()
else:
    obj.old_method()  # old_method does not exist

# NG: Defensive default value "just in case"
value = config.get('key', some_complex_fallback_logic())

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

# OK: Raise an error when config is missing (do not hide issues)
value = config['key']

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
- Did I write the same logic twice?
- Is there code that can be removed without affecting current behavior? If yes, remove it.
