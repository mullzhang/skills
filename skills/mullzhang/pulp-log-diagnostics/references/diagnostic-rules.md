# PuLP Log Diagnostic Rules

Use this reference when the automated report needs deeper interpretation.

## 1. Triage Order

Follow this order to reduce wasted investigation time:

1. Execution failures
2. Feasibility failures (`infeasible`)
3. Boundedness failures (`unbounded`)
4. Numerical quality warnings
5. Performance degradation (time limit, large gap)

## 2. Status Interpretation

Prefer explicit solver status rows (for example, `Status ...` in final report sections) over loose keyword matches.

Do not treat legend/help lines such as `U => Unbounded` as status evidence; these lines only describe symbols.

`optimal` means a solver-accepted solution was found under current settings, not that the model is semantically correct.

`infeasible` usually means a hard contradiction across constraints or fixed bounds. In mixed-integer models, check strict combinational rules first (mutual exclusivity, fixed assignments, capacity hard limits).

`unbounded` usually means missing bound constraints, sign mistakes in objective coefficients, or flow-balance omissions.

`time_limit` means no proof of optimality inside the configured budget. It may still produce an incumbent solution that is usable with a known gap.

`error` means the run failed before valid optimization results were produced (configuration, binary, export, file I/O, memory).

If application-side run summaries conflict with solver logs, prioritize the solver's final status section.

## 3. High-Value Pattern Clues

### 3.1 LP export failure due to variable name length

Symptom example: `Variable names too long for Lp format`.

Interpretation: writer limitation, not necessarily model infeasibility.

Action: keep `MPS` output as canonical artifact and shorten names only for human-readable LP debugging.

### 3.2 Solver not found or not executable

Symptom examples: `No executable found`, `PulpSolverError`, permission errors.

Interpretation: environment or solver invocation issue.

Action: verify binary path, executable permission, runtime dependencies, and version compatibility.

### 3.3 Infeasible without clear conflict message

Symptom examples: `Problem is infeasible`, `No feasible solution`.

Interpretation: global contradiction may be caused by a small subset of constraints.

Action: run with artifact export (`LP/MPS/JSON`), isolate by staged constraint activation, and use IIS-capable solver when possible.

### 3.4 Unbounded or dual infeasible

Symptom examples: `Unbounded`, `Dual infeasible`.

Interpretation: objective direction can improve indefinitely.

Action: inspect variable bounds and conservation constraints linked to objective terms.

### 3.5 Numerical instability

Symptom examples: `scaling`, `ill-conditioned`, large primal/dual tolerance issues.

Interpretation: coefficient scales are too wide or Big-M is too large.

Action: normalize units, tighten bounds, reduce Big-M by deriving data-based upper bounds.

### 3.6 Time limit and large gap

Symptom examples: `Stopped on time`, gap remains high.

Interpretation: branch-and-bound tree is too large or relaxation is weak.

Action: reduce symmetry, tighten formulations, improve incumbents, and set practical gap targets.

## 4. General Recommendations

Always store logs and model artifacts in the same run-specific directory so analysis can be replayed.

Treat recommendations as hypotheses. Confirm with targeted reruns that change one factor at a time.

Prefer reproducibility over ad-hoc debugging: fix random seeds, solver version, and key parameters in logs.
