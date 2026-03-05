---
name: pulp-log-diagnostics
description: Parse PuLP and solver logs (CBC, HiGHS, Gurobi, CPLEX) to diagnose infeasible/unbounded/time-limit/execution failures, extract key metrics, and propose prioritized next debugging actions. Use when given optimization run logs, solver stdout/stderr, or LP/MPS export errors and you need root-cause clues that generalize across optimization problems.
---

# Pulp Log Diagnostics

Use this skill to convert raw solver logs into a structured diagnosis.

## Workflow

1. Collect one or more log files from a failed or slow run.
2. Run `scripts/analyze_pulp_logs.py` to extract status, metrics, and suspicious lines.
3. Read `Diagnosis` and `Next Actions` first.
4. Open `references/diagnostic-rules.md` only when deeper interpretation is needed.

## Quick Start

```bash
python .agent/skills/pulp-log-diagnostics/scripts/analyze_pulp_logs.py \
  --log path/to/pulp_or_solver.log
```

Use multiple logs when the application and solver logs are separated:

```bash
python .agent/skills/pulp-log-diagnostics/scripts/analyze_pulp_logs.py \
  --log logs/app.log \
  --log logs/solver.log \
  --json-output /tmp/pulp_diagnosis.json
```

## Inputs and Outputs

- Input: plain text logs (`.log`, `.txt`, captured stdout/stderr).
- Input: optional `--lp` or `--mps` path for context in the final report.
- Output: human-readable summary to stdout.
- Output: optional JSON report for automation with `--json-output`.

## Rules for Use

- Keep analysis problem-agnostic: reason from status codes, solver messages, and model-health indicators.
- Prefer evidence-first conclusions: cite matched log lines before making recommendations.
- Prioritize high-impact causes:
  1. Execution/setup failures
  2. Infeasible/unbounded model issues
  3. Numerical instability
  4. Performance bottlenecks
- Suggest concrete next actions with expected payoff and effort.

## Script

- `scripts/analyze_pulp_logs.py`
  - Parse logs from PuLP/CBC/HiGHS/Gurobi/CPLEX style outputs.
  - Detect statuses (`optimal`, `infeasible`, `unbounded`, `time_limit`, `error`, `unknown`).
  - Extract objective, gap, solve time, node count, rows/columns statistics when available.
  - Detect known failure patterns such as LP variable-name overflow and missing solver binaries.
