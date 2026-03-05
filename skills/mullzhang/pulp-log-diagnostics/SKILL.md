---
name: pulp-log-diagnostics
description: Parse PuLP and solver logs (CBC, HiGHS, Gurobi, CPLEX) to diagnose infeasible/unbounded/time-limit/execution failures, extract key metrics, and propose prioritized next debugging actions. Use when given optimization run logs, solver stdout/stderr, or LP/MPS export errors and you need root-cause clues that generalize across optimization problems. When LP/MPS/log artifacts exist, include all of them in the analysis.
---

# Pulp Log Diagnostics

Use this skill to convert raw solver logs into a structured diagnosis.

## Workflow

1. Collect available artifacts from a failed or slow run: logs, `.lp`, and `.mps`.
2. Run `scripts/analyze_pulp_logs.py` with available flags and include every existing artifact (`--log`, `--lp`, `--mps`) in the same run.
3. Read `Diagnosis` and `Next Actions` first.
4. Open `references/diagnostic-rules.md` only when deeper interpretation is needed.

## Quick Start

```bash
python <path-to-this-skill>/scripts/analyze_pulp_logs.py \
  --log path/to/pulp_or_solver.log \
  --lp path/to/model.lp \
  --mps path/to/model.mps
```

Use multiple logs when the application and solver logs are separated:

```bash
python <path-to-this-skill>/scripts/analyze_pulp_logs.py \
  --log logs/app.log \
  --log logs/solver.log \
  --lp artifacts/model.lp \
  --mps artifacts/model.mps \
  --json-output /tmp/pulp_diagnosis.json
```

## Inputs and Outputs

- Input: plain text logs (`.log`, `.txt`, captured stdout/stderr), via one or more `--log`.
- Input: optional `--lp` path.
- Input: optional `--mps` path.
- Output: human-readable summary to stdout.
- Output: optional JSON report for automation with `--json-output`.

## Rules for Use

- Keep analysis problem-agnostic: reason from status codes, solver messages, and model-health indicators.
- If logs/LP/MPS artifacts exist in the target directory, include all of them in analysis.
- Stop early only when no input artifact is provided at all.
- Prefer evidence-first conclusions: cite matched log lines before making recommendations.
- When a final solver `Status` line exists, treat it as the primary status signal.
- Ignore solver legend lines (for example `U => Unbounded`) as status evidence.
- If application summary and solver log disagree, prioritize solver log's final status section.
- Prioritize high-impact causes:
  1. Execution/setup failures
  2. Infeasible/unbounded model issues
  3. Numerical instability
  4. Performance bottlenecks
- Suggest concrete next actions with expected payoff and effort.

## Script

- `scripts/analyze_pulp_logs.py`
  - Accept `--log`, `--lp`, `--mps` as optional inputs, but fail when all are omitted.
  - Parse logs from PuLP/CBC/HiGHS/Gurobi/CPLEX style outputs.
  - Detect statuses (`optimal`, `infeasible`, `unbounded`, `time_limit`, `error`, `unknown`) with explicit status-line precedence.
  - Extract objective/primal/dual bounds, gap, solve time, node count, LP iterations, rows/columns/nonzero counts when available.
  - Detect known failure patterns such as LP variable-name overflow and missing solver binaries.
