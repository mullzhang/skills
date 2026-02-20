---
name: test-only-dead-code-detector
description: Detect Python dead-code candidates that are referenced only from tests by running Vulture twice and diffing results (production paths vs production+test paths). Use when auditing cleanup targets, reviewing unused-code reports, or validating whether symbols are reachable only through tests.
---

# Test Only Dead Code Detector

Run `vulture` in two passes and compare findings to isolate test-only references.

## Workflow

1. Select production paths and test paths.
2. Run `scripts/find_test_only_dead_code.py` from repository root.
3. Prioritize `TEST-ONLY CANDIDATES` as "used only by tests" cleanup targets.
4. Treat `UNUSED EVEN WITH TESTS` as stronger dead-code candidates.
5. Apply allowlists for dynamic patterns when needed.

## Quick Start

```bash
python ~/.agent/skills/test-only-dead-code-detector/scripts/find_test_only_dead_code.py \
  --vulture-bin ./.venv/bin/vulture \
  --prod-path src \
  --prod-path experiments \
  --test-path tests \
  --config pyproject.toml \
  --min-confidence 60 \
  --exclude "*/conftest.py,*/__init__.py"
```

## Interpretation

- `TEST-ONLY CANDIDATES`
  - Reported in production-only scan, but disappears when tests are included.
  - Candidate code used only by tests.
- `UNUSED EVEN WITH TESTS`
  - Reported even when tests are included.
  - Candidate code unused across production and tests.
- `ONLY IN WITH-TESTS SCAN`
  - Appears only when test files are included.
  - Usually dead code inside test files.

## Script Options

- `--prod-path`: Add a production path (repeatable). Default: `src`.
- `--test-path`: Add a test path (repeatable). Default: `tests`.
- `--config`: Pass `pyproject.toml` or another vulture config.
- `--exclude`, `--ignore-names`, `--ignore-decorators`, `--min-confidence`, `--sort-by-size`: Forwarded to both runs.
- `--json-output`: Write machine-readable report.
- `--fail-on-test-only`: Exit `1` if test-only candidates are found.
- `--fail-on-unused-with-tests`: Exit `1` if findings remain unused with tests included.

## CI Example

```bash
python ~/.agent/skills/test-only-dead-code-detector/scripts/find_test_only_dead_code.py \
  --vulture-bin ./.venv/bin/vulture \
  --prod-path src \
  --test-path tests \
  --config pyproject.toml \
  --fail-on-test-only
```
