#!/usr/bin/env python3
"""Analyze PuLP and solver logs to extract actionable diagnostics."""

from __future__ import annotations

import argparse
import json
import re
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
    gap: str | None = None
    solve_time_seconds: float | None = None
    rows: int | None = None
    columns: int | None = None
    elements: int | None = None
    nodes: int | None = None


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
            regex=re.compile(r"(infeasible|no feasible solution)", re.IGNORECASE),
            diagnosis="制約系が同時充足できず実行不能になっている可能性が高い。",
            action="LP/MPSを保存し、制約の衝突候補を絞り、IIS解析可能なソルバーで検証する。",
        ),
        PatternRule(
            rule_id="unbounded_status",
            severity="high",
            category="modeling",
            regex=re.compile(r"(unbounded|dual infeasible)", re.IGNORECASE),
            diagnosis="目的方向に下限/上限が欠落している可能性がある。",
            action="目的に関与する変数の境界条件と符号を点検する。",
        ),
        PatternRule(
            rule_id="time_limit_reached",
            severity="medium",
            category="performance",
            regex=re.compile(r"(time limit|stopped on time|timelimit)", re.IGNORECASE),
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


def _detect_status(line: str, current: str) -> str:
    lowered = line.lower()
    if re.search(r"(traceback|exception|pulperror|\berror[:\s])", lowered):
        current = _update_status(current, "error")
    if re.search(r"\boptimal\b", lowered):
        current = _update_status(current, "optimal")
    if re.search(r"\binfeasible\b|no feasible solution", lowered):
        current = _update_status(current, "infeasible")
    if re.search(r"\bunbounded\b|dual infeasible", lowered):
        current = _update_status(current, "unbounded")
    if re.search(r"time limit|stopped on time|timelimit", lowered):
        current = _update_status(current, "time_limit")
    if re.search(r"not solved|undefined", lowered):
        current = _update_status(current, "not_solved")
    return current


def _safe_float(text: str) -> float | None:
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _parse_metrics(line: str, metrics: Metrics) -> None:
    if metrics.objective is None:
        matched = re.search(r"Objective value\s*[:=]\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)", line)
        if matched:
            metrics.objective = _safe_float(matched.group(1))

    if metrics.solve_time_seconds is None:
        matched = re.search(r"(?:Wallclock|Total|Solve)\s*time(?:\s*\([^)]*\))?\s*[:=]\s*([-+]?\d+(?:\.\d+)?)", line, re.IGNORECASE)
        if matched:
            metrics.solve_time_seconds = _safe_float(matched.group(1))
        else:
            matched = re.search(r"Time\s*\([^)]*seconds\)\s*:\s*([-+]?\d+(?:\.\d+)?)", line, re.IGNORECASE)
            if matched:
                metrics.solve_time_seconds = _safe_float(matched.group(1))

    if metrics.gap is None:
        matched = re.search(r"(?:MIP\s+)?gap\s*[:=]\s*([\d.+\-eE%]+)", line, re.IGNORECASE)
        if matched:
            metrics.gap = matched.group(1)

    if metrics.nodes is None:
        matched = re.search(r"Enumerated nodes\s*:\s*(\d+)", line, re.IGNORECASE)
        if matched:
            metrics.nodes = int(matched.group(1))

    if metrics.rows is None or metrics.columns is None or metrics.elements is None:
        matched = re.search(
            r"Problem .* has\s+(\d+)\s+rows,\s+(\d+)\s+columns\s+and\s+(\d+)\s+elements",
            line,
            re.IGNORECASE,
        )
        if matched:
            metrics.rows = int(matched.group(1))
            metrics.columns = int(matched.group(2))
            metrics.elements = int(matched.group(3))


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
        report.status = _detect_status(line, report.status)
        _parse_metrics(line, report.metrics)

        for rule in rules:
            if evidence_counts.get(rule.rule_id, 0) >= max_evidence_per_rule:
                continue
            if rule.regex.search(line):
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

    if lp_path is not None:
        report.artifacts["lp"] = str(lp_path)
    if mps_path is not None:
        report.artifacts["mps"] = str(mps_path)

    report.diagnosis, report.next_actions = _collect_diagnosis(report.status, report.findings)
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
    }


def _print_report(report: Report) -> None:
    print("== PuLP Log Diagnostics ==")
    print(f"files: {', '.join(report.files)}")
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


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze PuLP and solver logs for actionable diagnostics.")
    parser.add_argument(
        "--log",
        action="append",
        required=True,
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
    log_paths = [Path(p) for p in args.log]
    missing = [str(p) for p in log_paths if not p.exists()]
    if missing:
        print("Missing log files:", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
        return 2

    report = analyze_logs(
        log_paths=log_paths,
        lp_path=Path(args.lp) if args.lp else None,
        mps_path=Path(args.mps) if args.mps else None,
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
