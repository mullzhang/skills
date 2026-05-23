#!/usr/bin/env python3
"""Run IIS/conflict analysis on an LP/MPS model with a selected solver."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shlex
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import ModuleType


BUILTIN_SOLVERS = ("highs", "gurobi", "cplex")


@dataclass
class IISRunReport:
    solver: str
    model_path: str
    selected_via: str
    available_solvers: list[str]
    run_status: str
    model_status: str | None = None
    iis_output_path: str | None = None
    iis_output_exists: bool | None = None
    command: str | None = None
    iis_summary: dict[str, int | bool | str | None] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _normalize_solver_name(value: str) -> str:
    return value.strip().lower()


def _safe_solver_token(value: str) -> str:
    normalized = _normalize_solver_name(value)
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in normalized)
    return safe or "custom"


def detect_available_solvers() -> list[str]:
    available: list[str] = []

    if _module_available("highspy") or shutil.which("highs"):
        available.append("highs")

    if _module_available("gurobipy") or shutil.which("gurobi_cl"):
        available.append("gurobi")

    if _module_available("cplex") or shutil.which("cplex"):
        available.append("cplex")

    return available


def default_output_path(model_path: Path, solver: str) -> Path:
    solver_name = _normalize_solver_name(solver)
    if solver_name == "highs":
        return model_path.with_suffix(".iis.lp")
    if solver_name == "gurobi":
        return model_path.with_suffix(".iis.ilp")
    if solver_name == "cplex":
        return model_path.with_suffix(".conflict.clp")
    return model_path.with_suffix(f".{_safe_solver_token(solver_name)}.iis.txt")


def _prompt_solver_choice(available: list[str]) -> str:
    print("Select IIS solver before execution (ask user and choose one).")
    for idx, solver in enumerate(BUILTIN_SOLVERS, start=1):
        marker = "available" if solver in available else "not detected"
        print(f"  {idx}. {solver} ({marker})")
    print("  custom. any other solver name (requires custom runner script)")

    while True:
        answer = input("Enter solver name or number [1-3/custom]: ").strip()
        if not answer:
            continue
        lowered = _normalize_solver_name(answer)
        if lowered.isdigit():
            index = int(lowered)
            if 1 <= index <= len(BUILTIN_SOLVERS):
                return BUILTIN_SOLVERS[index - 1]
        if lowered == "custom":
            custom_name = input("Enter custom solver name: ").strip()
            if custom_name:
                return _normalize_solver_name(custom_name)
            continue
        return lowered


def _to_string(value: object) -> str:
    return str(value) if value is not None else "None"


def _resolve_highs_strategy(name: str) -> int:
    import highspy

    mapping = {
        "light": int(highspy.IisStrategy.kIisStrategyLight),
        "from_lp": int(highspy.IisStrategy.kIisStrategyFromLp),
        "irreducible": int(highspy.IisStrategy.kIisStrategyIrreducible),
        "col_priority": int(highspy.IisStrategy.kIisStrategyColPriority),
        "relaxation": int(highspy.IisStrategy.kIisStrategyRelaxation),
    }
    if name not in mapping:
        raise ValueError(f"Unsupported HiGHS IIS strategy: {name}")
    return mapping[name]


def run_highs_iis(
    model_path: Path,
    output_path: Path,
    *,
    iis_strategy: str,
    solve_relaxation: bool,
    log_file: Path | None,
    selected_via: str,
    available_solvers: list[str],
) -> IISRunReport:
    try:
        import highspy
    except ModuleNotFoundError:
        return IISRunReport(
            solver="highs",
            model_path=str(model_path),
            selected_via=selected_via,
            available_solvers=available_solvers,
            run_status="error",
            notes=["highspy is not installed in this environment."],
        )

    highs = highspy.Highs()
    highs.setOptionValue("output_flag", False)
    highs.setOptionValue("log_to_console", False)
    highs.setOptionValue("iis_strategy", _resolve_highs_strategy(iis_strategy))
    highs.setOptionValue("solve_relaxation", solve_relaxation)
    if log_file is not None:
        highs.setOptionValue("log_file", str(log_file))

    read_status = highs.readModel(str(model_path))
    if read_status != highspy.HighsStatus.kOk:
        return IISRunReport(
            solver="highs",
            model_path=str(model_path),
            selected_via=selected_via,
            available_solvers=available_solvers,
            run_status="error",
            notes=[f"Failed to read model: {_to_string(read_status)}"],
        )

    run_status = highs.run()
    model_status_enum = highs.getModelStatus()
    model_status = highs.modelStatusToString(model_status_enum)

    if model_status_enum != highspy.HighsModelStatus.kInfeasible:
        return IISRunReport(
            solver="highs",
            model_path=str(model_path),
            selected_via=selected_via,
            available_solvers=available_solvers,
            run_status="not_infeasible",
            model_status=model_status,
            notes=[
                f"HiGHS run status: {_to_string(run_status)}",
                "Model status is not Infeasible, so IIS was not written.",
            ],
        )

    iis_status, iis = highs.getIis()
    write_status = highs.writeIisModel(str(output_path))

    return IISRunReport(
        solver="highs",
        model_path=str(model_path),
        selected_via=selected_via,
        available_solvers=available_solvers,
        run_status="ok" if iis_status == highspy.HighsStatus.kOk else "error",
        model_status=model_status,
        iis_output_path=str(output_path),
        iis_output_exists=output_path.exists(),
        command=(
            "highspy.Highs(readModel/run/getIis/writeIisModel) "
            f"[iis_strategy={iis_strategy}, solve_relaxation={solve_relaxation}]"
        ),
        iis_summary={
            "highs_run_status": _to_string(run_status),
            "highs_iis_status": _to_string(iis_status),
            "highs_write_status": _to_string(write_status),
            "iis_valid": bool(iis.valid_),
            "row_index_count": len(iis.row_index_),
            "col_index_count": len(iis.col_index_),
            "row_bound_count": len(iis.row_bound_),
            "col_bound_count": len(iis.col_bound_),
        },
        notes=[],
    )


def run_gurobi_iis(
    model_path: Path,
    output_path: Path,
    *,
    selected_via: str,
    available_solvers: list[str],
) -> IISRunReport:
    try:
        import gurobipy as gp
    except ModuleNotFoundError:
        return IISRunReport(
            solver="gurobi",
            model_path=str(model_path),
            selected_via=selected_via,
            available_solvers=available_solvers,
            run_status="error",
            notes=["gurobipy is not installed in this environment."],
        )

    model = gp.read(str(model_path))
    model.optimize()

    if model.Status != gp.GRB.INFEASIBLE:
        return IISRunReport(
            solver="gurobi",
            model_path=str(model_path),
            selected_via=selected_via,
            available_solvers=available_solvers,
            run_status="not_infeasible",
            model_status=str(model.Status),
            notes=["Model status is not INFEASIBLE, so IIS was not written."],
        )

    model.computeIIS()
    model.write(str(output_path))

    iis_constr = sum(1 for c in model.getConstrs() if c.IISConstr)
    iis_var_lb = sum(1 for v in model.getVars() if v.IISLB)
    iis_var_ub = sum(1 for v in model.getVars() if v.IISUB)

    return IISRunReport(
        solver="gurobi",
        model_path=str(model_path),
        selected_via=selected_via,
        available_solvers=available_solvers,
        run_status="ok",
        model_status="INFEASIBLE",
        iis_output_path=str(output_path),
        iis_output_exists=output_path.exists(),
        command=(
            "python -c \"import gurobipy as gp; m=gp.read('<model>'); "
            "m.optimize(); m.computeIIS(); m.write('<output>')\""
        ),
        iis_summary={
            "iis_constraint_count": iis_constr,
            "iis_variable_lb_count": iis_var_lb,
            "iis_variable_ub_count": iis_var_ub,
        },
        notes=[],
    )


def run_cplex_iis(
    model_path: Path,
    output_path: Path,
    *,
    selected_via: str,
    available_solvers: list[str],
) -> IISRunReport:
    cplex_path = shutil.which("cplex")
    if cplex_path is None:
        return IISRunReport(
            solver="cplex",
            model_path=str(model_path),
            selected_via=selected_via,
            available_solvers=available_solvers,
            run_status="error",
            notes=["cplex CLI is not available in PATH."],
        )

    command = [
        cplex_path,
        "-c",
        f"read {model_path}",
        "optimize",
        "conflict refiner",
        f"write {output_path}",
        "quit",
    ]

    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    stdout_tail = "\n".join(completed.stdout.splitlines()[-20:])
    stderr_tail = "\n".join(completed.stderr.splitlines()[-20:])

    status = "ok" if completed.returncode == 0 else "error"
    notes: list[str] = []
    if stdout_tail:
        notes.append(f"stdout_tail:\n{stdout_tail}")
    if stderr_tail:
        notes.append(f"stderr_tail:\n{stderr_tail}")

    return IISRunReport(
        solver="cplex",
        model_path=str(model_path),
        selected_via=selected_via,
        available_solvers=available_solvers,
        run_status=status,
        iis_output_path=str(output_path),
        iis_output_exists=output_path.exists(),
        command=" ".join(shlex.quote(part) for part in command),
        iis_summary={
            "return_code": completed.returncode,
        },
        notes=notes,
    )


def _custom_runner_template_text(solver: str) -> str:
    return f'''#!/usr/bin/env python3
"""Custom IIS runner template for solver: {solver}."""

from __future__ import annotations


def run_custom_iis(*, model_path: str, output_path: str, solver: str) -> dict:
    """Return dict keys compatible with IISRunReport fields."""
    # TODO: Replace this template with actual IIS execution for your solver.
    # Example return payload:
    # return {{
    #   "run_status": "ok",
    #   "model_status": "INFEASIBLE",
    #   "iis_output_path": output_path,
    #   "iis_output_exists": True,
    #   "command": "<solver command>",
    #   "iis_summary": {{}},
    #   "notes": ["custom runner executed"],
    # }}
    raise NotImplementedError("Implement solver-specific IIS execution in run_custom_iis")
'''


def _write_custom_runner_template(path: Path, solver: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_custom_runner_template_text(solver), encoding="utf-8")
    try:
        path.chmod(0o755)
    except OSError:
        pass


def _load_module(module_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"custom_iis_runner_{module_path.stem}", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_custom_solver_iis(
    solver: str,
    model_path: Path,
    output_path: Path,
    *,
    custom_runner: Path | None,
    selected_via: str,
    available_solvers: list[str],
) -> IISRunReport:
    solver_name = _normalize_solver_name(solver)

    if custom_runner is None:
        template_path = Path("/tmp") / f"pulp_iis_custom_{_safe_solver_token(solver_name)}_runner.py"
        if not template_path.exists():
            _write_custom_runner_template(template_path, solver_name)
        return IISRunReport(
            solver=solver_name,
            model_path=str(model_path),
            selected_via=selected_via,
            available_solvers=available_solvers,
            run_status="error",
            iis_output_path=str(output_path),
            iis_output_exists=output_path.exists(),
            notes=[
                "Custom solver selected. Create solver-specific IIS code and rerun with --custom-runner.",
                f"Template generated: {template_path}",
                (
                    "Expected function signature: "
                    "run_custom_iis(*, model_path: str, output_path: str, solver: str) -> dict"
                ),
            ],
        )

    if not custom_runner.exists():
        return IISRunReport(
            solver=solver_name,
            model_path=str(model_path),
            selected_via=selected_via,
            available_solvers=available_solvers,
            run_status="error",
            notes=[f"Custom runner file not found: {custom_runner}"],
        )

    try:
        module = _load_module(custom_runner)
        func = getattr(module, "run_custom_iis", None)
        if func is None:
            raise AttributeError("Function run_custom_iis not found")

        result = func(model_path=str(model_path), output_path=str(output_path), solver=solver_name)

        if isinstance(result, IISRunReport):
            report = result
            report.solver = solver_name
            report.model_path = str(model_path)
            report.selected_via = selected_via
            report.available_solvers = available_solvers
            if report.iis_output_path is None:
                report.iis_output_path = str(output_path)
                report.iis_output_exists = output_path.exists()
            return report

        if not isinstance(result, dict):
            raise TypeError("run_custom_iis must return dict or IISRunReport")

        return IISRunReport(
            solver=solver_name,
            model_path=str(model_path),
            selected_via=selected_via,
            available_solvers=available_solvers,
            run_status=str(result.get("run_status", "error")),
            model_status=result.get("model_status"),
            iis_output_path=str(result.get("iis_output_path", output_path)),
            iis_output_exists=bool(result.get("iis_output_exists", output_path.exists())),
            command=result.get("command"),
            iis_summary=result.get("iis_summary", {}),
            notes=result.get("notes", []),
        )
    except Exception as exc:
        return IISRunReport(
            solver=solver_name,
            model_path=str(model_path),
            selected_via=selected_via,
            available_solvers=available_solvers,
            run_status="error",
            iis_output_path=str(output_path),
            iis_output_exists=output_path.exists(),
            notes=[f"Custom runner execution failed: {type(exc).__name__}: {exc}"],
        )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run IIS/conflict analysis for LP/MPS artifacts.")
    parser.add_argument("--model", required=True, help="Path to LP/MPS model file.")
    parser.add_argument(
        "--solver",
        help=(
            "IIS solver to use. Built-ins: highs/gurobi/cplex. "
            "Any other solver name is accepted with --custom-runner."
        ),
    )
    parser.add_argument("--output", help="Optional output path. Defaults depend on solver.")
    parser.add_argument(
        "--custom-runner",
        help=(
            "Path to Python file implementing "
            "run_custom_iis(*, model_path: str, output_path: str, solver: str) -> dict. "
            "Used for non-built-in solvers."
        ),
    )
    parser.add_argument(
        "--highs-iis-strategy",
        choices=("light", "from_lp", "irreducible", "col_priority", "relaxation"),
        default="irreducible",
        help="HiGHS IIS strategy (default: irreducible).",
    )
    parser.add_argument(
        "--highs-solve-relaxation",
        action="store_true",
        help="Enable HiGHS solve_relaxation before IIS extraction.",
    )
    parser.add_argument("--log-file", help="Optional solver log output path (mainly for HiGHS).")
    parser.add_argument("--json-output", help="Optional JSON output path for automation.")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Fail instead of prompting when --solver is omitted.",
    )
    parser.add_argument(
        "--list-solvers",
        action="store_true",
        help="List detected built-in solver availability and exit.",
    )
    return parser.parse_args(argv)


def _print_solver_list(available: list[str]) -> None:
    print("Detected built-in IIS solver availability:")
    for solver in BUILTIN_SOLVERS:
        marker = "yes" if solver in available else "no"
        print(f"  - {solver}: {marker}")
    print("  - other: supported via --custom-runner")


def _print_report(report: IISRunReport) -> None:
    print("== IIS Execution Report ==")
    print(f"solver: {report.solver}")
    print(f"selected_via: {report.selected_via}")
    print(f"model_path: {report.model_path}")
    print(f"run_status: {report.run_status}")
    if report.model_status is not None:
        print(f"model_status: {report.model_status}")
    if report.command is not None:
        print(f"command: {report.command}")
    if report.iis_output_path is not None:
        print(f"iis_output_path: {report.iis_output_path}")
        print(f"iis_output_exists: {report.iis_output_exists}")
    if report.iis_summary:
        print("iis_summary:")
        for key, value in report.iis_summary.items():
            print(f"  - {key}: {value}")
    if report.notes:
        print("notes:")
        for note in report.notes:
            print(f"  - {note}")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    model_path = Path(args.model)
    available = detect_available_solvers()

    if args.list_solvers:
        _print_solver_list(available)
        return 0

    if not model_path.exists():
        print(f"Model file not found: {model_path}", file=sys.stderr)
        return 2

    selected_via = "cli"
    solver = _normalize_solver_name(args.solver) if args.solver else None

    if solver is None:
        if args.non_interactive or not sys.stdin.isatty():
            print(
                "Solver is required in non-interactive mode. "
                "Ask the user which solver to use, then pass --solver.",
                file=sys.stderr,
            )
            _print_solver_list(available)
            return 2
        solver = _prompt_solver_choice(available)
        selected_via = "interactive_prompt"

    output_path = Path(args.output) if args.output else default_output_path(model_path, solver)
    log_file = Path(args.log_file) if args.log_file else None
    custom_runner = Path(args.custom_runner) if args.custom_runner else None

    if solver == "highs":
        report = run_highs_iis(
            model_path,
            output_path,
            iis_strategy=args.highs_iis_strategy,
            solve_relaxation=args.highs_solve_relaxation,
            log_file=log_file,
            selected_via=selected_via,
            available_solvers=available,
        )
    elif solver == "gurobi":
        report = run_gurobi_iis(
            model_path,
            output_path,
            selected_via=selected_via,
            available_solvers=available,
        )
    elif solver == "cplex":
        report = run_cplex_iis(
            model_path,
            output_path,
            selected_via=selected_via,
            available_solvers=available,
        )
    else:
        report = run_custom_solver_iis(
            solver,
            model_path,
            output_path,
            custom_runner=custom_runner,
            selected_via=selected_via,
            available_solvers=available,
        )

    _print_report(report)

    if args.json_output:
        json_path = Path(args.json_output)
        json_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"json_output: {json_path}")

    return 0 if report.run_status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
