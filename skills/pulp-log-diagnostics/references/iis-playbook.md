# IIS Playbook (Solver-Agnostic)

Use this playbook when the diagnostic status is `infeasible` and LP/MPS artifacts exist.

## 1. Preconditions

1. Ensure infeasibility is from solver final status section.
2. Ensure at least one artifact exists: `.mps` preferred, `.lp` fallback.
3. Run on an environment with IIS-capable solver.
4. Ask the user which solver to use before IIS execution.

## 2. Artifact Priority

1. Prefer `.mps` for portability across solvers.
2. Prefer `.lp` when you need readable constraint names from IIS output.
3. Keep IIS outputs in the same run directory as logs and model artifacts.

## 3. Solver Choice

- User-selected solver is the primary decision.
- Built-in options:
  1. HiGHS (highspy)
  2. Gurobi
  3. CPLEX
- If the user selects another solver, create solver-specific IIS code for that run and execute via `--custom-runner`.

## 4. Command Templates

Replace `<MODEL_MPS_OR_LP>` with model path.

### 4.1 Unified Runner (Recommended)

```bash
# Ask user first: highs / gurobi / cplex / other
python <path-to-this-skill>/scripts/run_iis.py \
  --model <MODEL_MPS_OR_LP> \
  --solver highs
```

### 4.2 HiGHS (Python API via highspy)

```bash
python <path-to-this-skill>/scripts/run_iis.py \
  --model <MODEL_MPS_OR_LP> \
  --solver highs \
  --highs-iis-strategy irreducible
```

Expected output:

- `<MODEL_MPS_OR_LP without ext>.iis.lp`
- IIS execution report (stdout and optional JSON)

### 4.3 Gurobi (Python API)

```bash
python <path-to-this-skill>/scripts/run_iis.py \
  --model <MODEL_MPS_OR_LP> \
  --solver gurobi
```

Expected output:

- `<MODEL_MPS_OR_LP without ext>.iis.ilp`
- IIS execution report (stdout and optional JSON)

### 4.4 CPLEX (CLI)

```bash
python <path-to-this-skill>/scripts/run_iis.py \
  --model <MODEL_MPS_OR_LP> \
  --solver cplex
```

Expected output:

- `<MODEL_MPS_OR_LP without ext>.conflict.clp`
- CPLEX conflict refiner log/summary

### 4.5 Other Solver (Per-Run Custom Code)

```bash
# 1) create custom runner code for selected solver
# 2) execute via unified runner
python <path-to-this-skill>/scripts/run_iis.py \
  --model <MODEL_MPS_OR_LP> \
  --solver <custom_solver> \
  --custom-runner /tmp/pulp_iis_custom_<custom_solver>_runner.py
```

Custom runner contract:

- Provide `run_custom_iis(*, model_path: str, output_path: str, solver: str) -> dict`.
- Return fields compatible with `IISRunReport` (`run_status`, `model_status`, `iis_output_path`, `iis_output_exists`, `command`, `iis_summary`, `notes`).

## 5. How to Use IIS Result

1. Extract only conflict constraints from IIS output.
2. Map each constraint name to business rule category.
3. Group by pattern: fixed assignment clashes, capacity hard limits, exclusivity rules.
4. Validate by disabling one suspected block at a time and re-solving.

## 6. Fallback if IIS Is Unavailable

1. Stage constraints: enable blocks incrementally to find first infeasible boundary.
2. Add slack variables with high penalties and inspect top violated constraints.
3. Compare infeasible run artifacts against nearest feasible run (`constraints_active.csv`, model size, fixed bounds).
4. Keep one-factor-at-a-time reruns to avoid mixed-cause diagnosis.

## 7. Output Checklist

1. Solver status and evidence line(s)
2. IIS artifact path(s)
3. Conflict constraint list
4. Top 3 remediation hypotheses
5. Re-run plan with minimal parameter/model changes
