#!/usr/bin/env python3
"""Analyze PuLP and solver logs to extract actionable diagnostics."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class PatternRule:
    rule_id: str
    severity: str
    category: str
    regex: re.Pattern[str]
    diagnosis: str
    action: str
    exclude_regexes: tuple[re.Pattern[str], ...] = ()


@dataclass
class Evidence:
    rule_id: str
    severity: str
    category: str
    source: str
    line_no: int
    line: str
    diagnosis: str
    action: str


@dataclass
class Metrics:
    objective: float | None = None
    primal_bound: float | None = None
    dual_bound: float | None = None
    gap: str | None = None
    solve_time_seconds: float | None = None
    rows: int | None = None
    columns: int | None = None
    elements: int | None = None
    nodes: int | None = None
    lp_iterations: int | None = None


@dataclass
class IISPlan:
    applicability: str = "not_required"
    reason: str = ""
    recommended_solver: str | None = None
    detected_iis_solvers: list[str] = field(default_factory=list)
    artifact_for_iis: str | None = None
    commands: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    fallback_actions: list[str] = field(default_factory=list)


@dataclass
class Report:
    files: list[str] = field(default_factory=list)
    solver: str = "unknown"
    status: str = "unknown"
    metrics: Metrics = field(default_factory=Metrics)
    findings: list[Evidence] = field(default_factory=list)
    diagnosis: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    iis_plan: IISPlan | None = None


STATUS_PRIORITY = {
    "error": 0,
    "infeasible": 1,
    "unbounded": 2,
    "time_limit": 3,
    "not_solved": 4,
    "optimal": 5,
    "unknown": 6,
}


def _make_rules() -> list[PatternRule]:
    return [
        PatternRule(
            rule_id="lp_variable_name_too_long",
            severity="high",
            category="model_export",
            regex=re.compile(r"Variable names too long for Lp format", re.IGNORECASE),
            diagnosis="LP形式の変数名長制約に抵触してモデル出力が失敗している。",
            action="LPではなくMPSを優先保存し、LP保存時は短い変数名へ正規化する。",
        ),
        PatternRule(
            rule_id="solver_binary_not_found",
            severity="high",
            category="execution",
            regex=re.compile(r"(No executable found|cannot execute|not available|PulpSolverError)", re.IGNORECASE),
            diagnosis="ソルバー実行バイナリまたは呼び出し設定に問題がある。",
            action="solver path、環境変数、インストール状態、実行権限を確認する。",
        ),
        PatternRule(
            rule_id="memory_issue",
            severity="high",
            category="resource",
            regex=re.compile(r"(out of memory|std::bad_alloc|memory error)", re.IGNORECASE),
            diagnosis="メモリ不足で探索が継続できない。",
            action="モデル縮約、不要変数削減、time limit調整、計算資源増強を検討する。",
        ),
        PatternRule(
            rule_id="numerical_instability",
            severity="medium",
            category="numerical",
            regex=re.compile(r"(numerical|scaling|singular|ill[- ]conditioned|primal infeasible due to tolerance)", re.IGNORECASE),
            diagnosis="数値スケーリング不良または係数レンジ過大の兆候がある。",
            action="係数の桁レンジを縮小し、Big-Mを見直し、単位系を正規化する。",
        ),
        PatternRule(
            rule_id="infeasible_status",
            severity="high",
            category="feasibility",
            regex=re.compile(r"\b(infeasible|no feasible solution)\b", re.IGNORECASE),
            diagnosis="制約系が同時充足できず実行不能になっている可能性が高い。",
            action="LP/MPSを保存し、制約の衝突候補を絞り、IIS解析可能なソルバーで検証する。",
            exclude_regexes=(
                re.compile(r"primal infeasible due to tolerance", re.IGNORECASE),
            ),
        ),
        PatternRule(
            rule_id="unbounded_status",
            severity="high",
            category="modeling",
            regex=re.compile(r"\b(unbounded|dual infeasible)\b", re.IGNORECASE),
            diagnosis="目的方向に下限/上限が欠落している可能性がある。",
            action="目的に関与する変数の境界条件と符号を点検する。",
            exclude_regexes=(
                re.compile(r"=>\s*unbounded\b", re.IGNORECASE),  # HiGHS legend line
            ),
        ),
        PatternRule(
            rule_id="time_limit_reached",
            severity="medium",
            category="performance",
            regex=re.compile(r"\b(time limit|stopped on time|timelimit)\b", re.IGNORECASE),
            diagnosis="制限時間到達により最適化が途中停止している。",
            action="gap目標、探索パラメータ、Big-M、対称性、初期解の品質を見直す。",
        ),
    ]


def _iter_lines(paths: Iterable[Path], encoding: str) -> Iterable[tuple[str, int, str]]:
    for path in paths:
        try:
            with path.open("r", encoding=encoding, errors="replace") as handle:
                for idx, line in enumerate(handle, start=1):
                    yield str(path), idx, line.rstrip("\n")
        except OSError as exc:
            yield str(path), 0, f"[READ_ERROR] {exc}"


def _detect_solver(text: str) -> str:
    lowered = text.lower()
    if "highs" in lowered:
        return "HiGHS"
    if "gurobi" in lowered:
        return "Gurobi"
    if "cplex" in lowered:
        return "CPLEX"
    if "cbc" in lowered or "coin" in lowered:
        return "CBC"
    return "unknown"


def _update_status(current: str, candidate: str) -> str:
    if STATUS_PRIORITY[candidate] < STATUS_PRIORITY[current]:
        return candidate
    return current


def _is_status_noise_line(line: str) -> bool:
    lowered = line.lower()
    if "=>" in lowered and any(token in lowered for token in ("unbounded", "infeasible", "optimal", "feasible")):
        return True
    if lowered.strip().startswith("src:"):
        return True
    return False


def _map_status_from_text(text: str) -> str | None:
    lowered = text.lower()
    if re.search(r"time limit|stopped on time|timelimit", lowered):
        return "time_limit"
    if re.search(r"\binfeasible\b|no feasible solution", lowered):
        return "infeasible"
    if re.search(r"\bunbounded\b|dual infeasible", lowered):
        return "unbounded"
    if re.search(r"\boptimal\b", lowered):
        return "optimal"
    if re.search(r"not solved|undefined", lowered):
        return "not_solved"
    return None


def _detect_status_from_line(line: str, current: str) -> str:
    lowered = line.lower()
    if re.search(r"(traceback|exception|pulperror|\berror[:\s])", lowered):
        current = _update_status(current, "error")
    if _is_status_noise_line(line):
        return current
    candidate = _map_status_from_text(line)
    if candidate:
        current = _update_status(current, candidate)
    return current


def _extract_explicit_status(raw_lines: list[tuple[str, int, str]]) -> str | None:
    patterns = [
        re.compile(r"^\s*Status\s+(?P<value>.+)$", re.IGNORECASE),
        re.compile(r"^\s*Model status\s*:\s*(?P<value>.+)$", re.IGNORECASE),
        re.compile(r"^\s*Result\s*-\s*(?P<value>.+)$", re.IGNORECASE),
    ]
    explicit_status: str | None = None
    for _, _, line in raw_lines:
        stripped = line.strip()
        if not stripped or _is_status_noise_line(stripped):
            continue
        for pattern in patterns:
            matched = pattern.match(stripped)
            if not matched:
                continue
            candidate = _map_status_from_text(matched.group("value"))
            if candidate:
                explicit_status = candidate
    return explicit_status


def _safe_float(text: str) -> float | None:
    normalized = text.strip().lower()
    if normalized in {"inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _parse_metrics(line: str, metrics: Metrics) -> None:
    if metrics.rows is None or metrics.columns is None or metrics.elements is None:
        matched = re.search(
            r"MIP has\s+(\d+)\s+rows;\s+(\d+)\s+cols;\s+(\d+)\s+nonzeros",
            line,
            re.IGNORECASE,
        )
        if matched:
            metrics.rows = int(matched.group(1))
            metrics.columns = int(matched.group(2))
            metrics.elements = int(matched.group(3))
        else:
            matched = re.search(
                r"Problem .* has\s+(\d+)\s+rows,\s+(\d+)\s+columns\s+and\s+(\d+)\s+elements",
                line,
                re.IGNORECASE,
            )
            if matched:
                metrics.rows = int(matched.group(1))
                metrics.columns = int(matched.group(2))
                metrics.elements = int(matched.group(3))

    if metrics.objective is None:
        matched = re.search(r"Objective value\s*[:=]\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)", line)
        if matched:
            metrics.objective = _safe_float(matched.group(1))

    if metrics.primal_bound is None:
        matched = re.match(r"^\s*Primal bound\s+([^\s]+)", line, re.IGNORECASE)
        if matched:
            metrics.primal_bound = _safe_float(matched.group(1))
            if metrics.objective is None and metrics.primal_bound is not None:
                metrics.objective = metrics.primal_bound

    if metrics.dual_bound is None:
        matched = re.match(r"^\s*Dual bound\s+([^\s]+)", line, re.IGNORECASE)
        if matched:
            metrics.dual_bound = _safe_float(matched.group(1))

    if metrics.solve_time_seconds is None:
        matched = re.match(r"^\s*Timing\s+([-+]?\d+(?:\.\d+)?)\s*$", line, re.IGNORECASE)
        if matched:
            metrics.solve_time_seconds = _safe_float(matched.group(1))
        else:
            matched = re.search(
                r"(?:Wallclock|Total|Solve)\s*time(?:\s*\([^)]*\))?\s*[:=]\s*([-+]?\d+(?:\.\d+)?)",
                line,
                re.IGNORECASE,
            )
            if matched:
                metrics.solve_time_seconds = _safe_float(matched.group(1))
            else:
                matched = re.search(r"Time\s*\([^)]*seconds\)\s*:\s*([-+]?\d+(?:\.\d+)?)", line, re.IGNORECASE)
                if matched:
                    metrics.solve_time_seconds = _safe_float(matched.group(1))

    if metrics.gap is None:
        matched = re.match(r"^\s*Gap\s+(.+)$", line, re.IGNORECASE)
        if matched:
            value = matched.group(1).strip()
            if "|" not in value:  # Skip branch-and-bound table header rows.
                metrics.gap = value
        else:
            matched = re.search(r"(?:MIP\s+)?gap\s*[:=]\s*([\d.+\-eE%]+)", line, re.IGNORECASE)
            if matched:
                metrics.gap = matched.group(1)

    if metrics.nodes is None:
        matched = re.match(r"^\s*Nodes\s+(\d+)\s*$", line, re.IGNORECASE)
        if matched:
            metrics.nodes = int(matched.group(1))
        else:
            matched = re.search(r"Enumerated nodes\s*:\s*(\d+)", line, re.IGNORECASE)
            if matched:
                metrics.nodes = int(matched.group(1))

    if metrics.lp_iterations is None:
        matched = re.match(r"^\s*LP iterations\s+(\d+)\s*$", line, re.IGNORECASE)
        if matched:
            metrics.lp_iterations = int(matched.group(1))


def _collect_diagnosis(status: str, findings: list[Evidence]) -> tuple[list[str], list[str]]:
    diagnosis: list[str] = []
    actions: list[str] = []

    by_rule = {f.rule_id for f in findings}

    if "solver_binary_not_found" in by_rule:
        diagnosis.append("ソルバー実行環境の不整合があり、モデルの正否以前に実行基盤で失敗している。")
        actions.append("ソルバー起動コマンドを単体実行し、PATHとバージョン整合を確認する。")

    if "lp_variable_name_too_long" in by_rule:
        diagnosis.append("LP出力処理で変数名長制約により失敗している。")
        actions.append("`writeMPS(..., rename=1)`を優先し、LPは短縮名のデバッグ用途に限定する。")

    if status == "infeasible":
        diagnosis.append("制約の組み合わせに矛盾がある可能性が高い。")
        actions.append("必須制約を段階的に有効化して最小矛盾集合に近づける。")
        actions.append("可能ならMPSを外部ソルバーでIIS解析し、衝突制約を特定する。")

    if status == "unbounded":
        diagnosis.append("目的関数を改善し続けられるため、境界設定または符号に欠陥がある。")
        actions.append("目的に寄与する変数の上下限とフロー保存制約の欠落を点検する。")

    if status == "time_limit":
        diagnosis.append("探索空間が広く、現行パラメータでは収束前に打ち切られている。")
        actions.append("Big-Mの縮小、対称性削減、初期解投入、ギャップ許容値設定を優先する。")

    if "numerical_instability" in by_rule:
        diagnosis.append("数値不安定により求解品質と速度が悪化している可能性がある。")
        actions.append("係数レンジを2-3桁程度に正規化し、過大係数の制約を分解する。")

    if "memory_issue" in by_rule:
        diagnosis.append("モデル規模または探索戦略に対してメモリが不足している。")
        actions.append("変数削減、事前固定、タスク分割で問題規模を小さくする。")

    if not diagnosis:
        diagnosis.append("致命的エラーは検出されなかったが、追加ログが不足している可能性がある。")
        actions.append("solverの詳細ログを有効化し、LP/MPS/JSONを同時保存して再試行する。")

    dedup_actions: list[str] = []
    seen: set[str] = set()
    for action in actions:
        if action not in seen:
            dedup_actions.append(action)
            seen.add(action)

    return diagnosis, dedup_actions


def _detect_iis_solvers() -> list[str]:
    detected: list[str] = []

    # HiGHS IIS is available via highspy in Python API.
    try:
        import highspy  # type: ignore  # noqa: F401

        detected.append("highs")
    except Exception:
        if shutil.which("highs"):
            detected.append("highs")

    if shutil.which("gurobi_cl"):
        detected.append("gurobi")
    else:
        try:
            import gurobipy  # type: ignore  # noqa: F401

            detected.append("gurobi")
        except Exception:
            pass

    if shutil.which("cplex"):
        detected.append("cplex")
    else:
        try:
            import cplex  # type: ignore  # noqa: F401

            detected.append("cplex")
        except Exception:
            pass

    seen: set[str] = set()
    ordered_detected: list[str] = []
    for solver in detected:
        if solver not in seen:
            ordered_detected.append(solver)
            seen.add(solver)
    return ordered_detected


def _build_iis_plan(status: str, lp_path: Path | None, mps_path: Path | None) -> IISPlan:
    plan = IISPlan()

    if status != "infeasible":
        plan.reason = "statusがinfeasibleではないため、IIS解析は不要。"
        return plan

    artifact_path = mps_path or lp_path
    if artifact_path is None:
        plan.applicability = "blocked"
        plan.reason = "IIS解析に必要なLP/MPSが未指定。"
        plan.fallback_actions = [
            "LPまたはMPSを必ず保存して同一runディレクトリへ配置する。",
            "制約を段階的に有効化して、最小矛盾集合に近い条件を特定する。",
            "ハード制約にslack変数を追加してペナルティ最小化し、違反制約候補を抽出する。",
        ]
        return plan

    artifact = str(artifact_path)
    artifact_q = shlex.quote(artifact)
    stem = shlex.quote(str(artifact_path.with_suffix("")))
    run_iis_script = Path(__file__).resolve().parent / "run_iis.py"
    run_iis_script_q = shlex.quote(str(run_iis_script))

    plan.applicability = "recommended"
    plan.reason = "infeasibleが確定しており、IISで衝突制約を局所化できる可能性が高い。"
    plan.artifact_for_iis = artifact
    plan.detected_iis_solvers = _detect_iis_solvers()

    highs_cmd = (
        f"python {run_iis_script_q} --model {artifact_q} "
        "--solver highs --highs-iis-strategy irreducible"
    )
    gurobi_cmd = (
        f"python {run_iis_script_q} --model {artifact_q} --solver gurobi"
    )
    cplex_cmd = (
        "cplex -c "
        f"\"read {artifact_q}\" "
        "\"optimize\" "
        "\"conflict refiner\" "
        f"\"write {stem}.conflict.clp\" "
        "\"quit\""
    )

    preferred_order = ["highs", "gurobi", "cplex"]
    plan.recommended_solver = next(
        (solver for solver in preferred_order if solver in plan.detected_iis_solvers),
        "user_select_required",
    )

    plan.commands = [
        "# Ask user which solver to use before running IIS (highs/gurobi/cplex/other).",
        f"python {run_iis_script_q} --model {artifact_q}",
        (
            "# For other solvers, create a custom runner and execute: "
            f"python {run_iis_script_q} --model {artifact_q} --solver <custom_solver> "
            "--custom-runner /tmp/pulp_iis_custom_<custom_solver>_runner.py"
        ),
    ]
    plan.expected_outputs = []

    if "highs" in plan.detected_iis_solvers:
        plan.commands.extend(
            [
                "# HiGHS (highspy)",
                highs_cmd,
            ]
        )
        plan.expected_outputs.append(f"{artifact_path.with_suffix('.iis.lp')} (HiGHSでIIS抽出時)")

    if "gurobi" in plan.detected_iis_solvers:
        plan.commands.extend(
            [
                "# Gurobi Python API",
                gurobi_cmd,
            ]
        )
        plan.expected_outputs.append(f"{artifact_path.with_suffix('.iis.ilp')} (GurobiでIIS抽出時)")

    if "cplex" in plan.detected_iis_solvers:
        plan.commands.extend(
            [
                "# CPLEX CLI",
                cplex_cmd,
            ]
        )
        plan.expected_outputs.append(f"{artifact_path.with_suffix('')}.conflict.clp (CPLEX conflict refiner時)")

    plan.expected_outputs.append("IISに含まれる制約名リスト（業務制約への逆引き用）")
    plan.fallback_actions = [
        "IISソルバーが無い場合は、制約をブロック単位で段階有効化して矛盾発生点を特定する。",
        "同じrunの feasible ケースとの差分で constraints_active を比較し、追加・厳格化制約を優先調査する。",
        "slack付き実行可能化モデル（違反ペナルティ最小化）で上位違反制約を抽出する。",
    ]
    return plan


def analyze_logs(
    log_paths: list[Path],
    lp_path: Path | None,
    mps_path: Path | None,
    encoding: str,
    max_evidence_per_rule: int,
) -> Report:
    rules = _make_rules()
    report = Report(files=[str(p) for p in log_paths])

    raw_lines: list[tuple[str, int, str]] = list(_iter_lines(log_paths, encoding=encoding))
    all_text = "\n".join(line for _, _, line in raw_lines)
    report.solver = _detect_solver(all_text)

    evidence_counts: dict[str, int] = {}

    for source, line_no, line in raw_lines:
        report.status = _detect_status_from_line(line, report.status)
        _parse_metrics(line, report.metrics)

        for rule in rules:
            if evidence_counts.get(rule.rule_id, 0) >= max_evidence_per_rule:
                continue
            if not rule.regex.search(line):
                continue
            if any(exclude.search(line) for exclude in rule.exclude_regexes):
                continue

            report.findings.append(
                Evidence(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    category=rule.category,
                    source=source,
                    line_no=line_no,
                    line=line.strip(),
                    diagnosis=rule.diagnosis,
                    action=rule.action,
                )
            )
            evidence_counts[rule.rule_id] = evidence_counts.get(rule.rule_id, 0) + 1

    explicit_status = _extract_explicit_status(raw_lines)
    if explicit_status is not None:
        report.status = explicit_status

    if lp_path is not None:
        report.artifacts["lp"] = str(lp_path)
    if mps_path is not None:
        report.artifacts["mps"] = str(mps_path)

    report.diagnosis, report.next_actions = _collect_diagnosis(report.status, report.findings)
    report.iis_plan = _build_iis_plan(report.status, lp_path=lp_path, mps_path=mps_path)
    return report


def _report_to_dict(report: Report) -> dict[str, object]:
    return {
        "files": report.files,
        "solver": report.solver,
        "status": report.status,
        "metrics": asdict(report.metrics),
        "findings": [asdict(f) for f in report.findings],
        "diagnosis": report.diagnosis,
        "next_actions": report.next_actions,
        "artifacts": report.artifacts,
        "iis_plan": asdict(report.iis_plan) if report.iis_plan else None,
    }


def _print_report(report: Report) -> None:
    print("== PuLP Log Diagnostics ==")
    files_text = ", ".join(report.files) if report.files else "(none)"
    print(f"files: {files_text}")
    print(f"solver: {report.solver}")
    print(f"status: {report.status}")

    metrics_dict = asdict(report.metrics)
    useful_metrics = {k: v for k, v in metrics_dict.items() if v is not None}
    if useful_metrics:
        print("metrics:")
        for key, value in useful_metrics.items():
            print(f"  - {key}: {value}")

    if report.artifacts:
        print("artifacts:")
        for key, value in report.artifacts.items():
            print(f"  - {key}: {value}")

    if report.findings:
        print("findings:")
        for finding in report.findings:
            where = f"{finding.source}:{finding.line_no}" if finding.line_no else finding.source
            print(
                f"  - [{finding.severity}] {finding.rule_id} ({finding.category}) at {where}\n"
                f"    evidence: {finding.line[:180]}\n"
                f"    diagnosis: {finding.diagnosis}\n"
                f"    action: {finding.action}"
            )
    else:
        print("findings: none")

    print("diagnosis:")
    for item in report.diagnosis:
        print(f"  - {item}")

    print("next_actions:")
    for idx, item in enumerate(report.next_actions, start=1):
        print(f"  {idx}. {item}")

    if report.iis_plan:
        print("iis_plan:")
        print(f"  - applicability: {report.iis_plan.applicability}")
        print(f"  - reason: {report.iis_plan.reason}")
        if report.iis_plan.recommended_solver:
            print(f"  - recommended_solver: {report.iis_plan.recommended_solver}")
        detected = ", ".join(report.iis_plan.detected_iis_solvers) if report.iis_plan.detected_iis_solvers else "none"
        print(f"  - detected_iis_solvers: {detected}")
        if report.iis_plan.artifact_for_iis:
            print(f"  - artifact_for_iis: {report.iis_plan.artifact_for_iis}")
        for cmd in report.iis_plan.commands:
            print(f"  - command: {cmd}")
        for item in report.iis_plan.expected_outputs:
            print(f"  - expected_output: {item}")
        for item in report.iis_plan.fallback_actions:
            print(f"  - iis_fallback: {item}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze PuLP and solver logs for actionable diagnostics.")
    parser.add_argument(
        "--log",
        action="append",
        help="Path to a log file. Pass multiple times to analyze multiple logs.",
    )
    parser.add_argument("--lp", help="Optional LP artifact path.")
    parser.add_argument("--mps", help="Optional MPS artifact path.")
    parser.add_argument("--encoding", default="utf-8", help="Text encoding for log files (default: utf-8).")
    parser.add_argument(
        "--max-evidence-per-rule",
        type=int,
        default=3,
        help="Maximum evidence lines stored per matched rule (default: 3).",
    )
    parser.add_argument("--json-output", help="Optional path to write JSON report.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    log_paths = [Path(p) for p in args.log] if args.log else []
    lp_path = Path(args.lp) if args.lp else None
    mps_path = Path(args.mps) if args.mps else None

    if not log_paths and lp_path is None and mps_path is None:
        print("No input files provided. Specify at least one of --log/--lp/--mps.", file=sys.stderr)
        return 2

    missing_logs = [str(p) for p in log_paths if not p.exists()]
    missing_artifacts: list[str] = []
    if lp_path is not None and not lp_path.exists():
        missing_artifacts.append(f"lp: {lp_path}")
    if mps_path is not None and not mps_path.exists():
        missing_artifacts.append(f"mps: {mps_path}")

    if missing_logs or missing_artifacts:
        print("Missing specified input files:", file=sys.stderr)
        for path in missing_logs:
            print(f"  - log: {path}", file=sys.stderr)
        for artifact in missing_artifacts:
            print(f"  - {artifact}", file=sys.stderr)
        return 2

    report = analyze_logs(
        log_paths=log_paths,
        lp_path=lp_path,
        mps_path=mps_path,
        encoding=args.encoding,
        max_evidence_per_rule=max(1, args.max_evidence_per_rule),
    )

    _print_report(report)

    if args.json_output:
        output_path = Path(args.json_output)
        output_path.write_text(
            json.dumps(_report_to_dict(report), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"json_output: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
