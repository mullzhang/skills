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
4. If `status` is `infeasible`, ask the user which IIS solver to use **before** running IIS.
5. If solver is `highs` / `gurobi` / `cplex`, run `scripts/run_iis.py` with `--solver`.
6. If solver is other than built-ins, create a solver-specific custom runner script **for that run**, then execute `scripts/run_iis.py --solver <custom_solver> --custom-runner <path>`.
7. Open `references/diagnostic-rules.md` only when deeper interpretation is needed.
8. Open `references/iis-playbook.md` when you need solver-specific IIS execution details.

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

Run IIS after user solver selection:

```bash
# Ask user first
python <path-to-this-skill>/scripts/run_iis.py \
  --model path/to/model.lp \
  --solver highs \
  --highs-iis-strategy irreducible \
  --json-output /tmp/pulp_iis_report.json
```

Custom solver flow (per-run):

```bash
# 1) create custom runner code for the selected solver
# 2) execute via unified runner
python <path-to-this-skill>/scripts/run_iis.py \
  --model path/to/model.lp \
  --solver xpress \
  --custom-runner /tmp/pulp_iis_custom_xpress_runner.py \
  --json-output /tmp/pulp_iis_report_xpress.json
```

If `--solver` is omitted in an interactive shell, `run_iis.py` prompts for solver selection.

## Inputs and Outputs

- Input: plain text logs (`.log`, `.txt`, captured stdout/stderr), via one or more `--log`.
- Input: optional `--lp` path.
- Input: optional `--mps` path.
- Output: human-readable summary to stdout.
- Output: optional JSON report for automation with `--json-output`.

### IIS-related output fields (`analyze_pulp_logs.py`)

- `iis_plan.applicability`: `not_required` / `recommended` / `blocked`
- `iis_plan.reason`: why IIS is required or blocked
- `iis_plan.recommended_solver`: selected IIS solver or `user_select_required`
- `iis_plan.detected_iis_solvers`: IIS-capable solvers detected in current environment
- `iis_plan.artifact_for_iis`: LP/MPS artifact path used for IIS
- `iis_plan.commands`: command templates only for detected IIS-capable solvers
- `iis_plan.expected_outputs`: required artifacts from IIS run
- `iis_plan.fallback_actions`: project-agnostic fallback actions when IIS is unavailable

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
- For `infeasible`, prioritize IIS-capable solver execution over broad trial-and-error.
- Before IIS execution, always ask the user which solver to use.
- If user selects a non-built-in solver, create custom solver code for that run and execute it via `--custom-runner`.

## Scripts

- `scripts/analyze_pulp_logs.py`
  - Accept `--log`, `--lp`, `--mps` as optional inputs, but fail when all are omitted.
  - Parse logs from PuLP/CBC/HiGHS/Gurobi/CPLEX style outputs.
  - Detect statuses (`optimal`, `infeasible`, `unbounded`, `time_limit`, `error`, `unknown`) with explicit status-line precedence.
  - Extract objective/primal/dual bounds, gap, solve time, node count, LP iterations, rows/columns/nonzero counts when available.
  - Detect known failure patterns such as LP variable-name overflow and missing solver binaries.
  - Build `iis_plan` for infeasible cases using LP/MPS artifacts and detected IIS-capable solvers.

- `scripts/run_iis.py`
  - Execute IIS/conflict analysis using `highs`, `gurobi`, or `cplex`.
  - Accept arbitrary solver names and delegate to custom per-run runner with `--custom-runner`.
  - Require explicit `--solver` in non-interactive mode.
  - Prompt solver selection when `--solver` is omitted in interactive mode.
  - Support HiGHS IIS options (`--highs-iis-strategy`, `--highs-solve-relaxation`).
  - Emit a structured execution report and optional JSON.
