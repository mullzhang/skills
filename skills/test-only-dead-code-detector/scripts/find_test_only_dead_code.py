#!/usr/bin/env python3
"""Detect test-only dead code candidates by diffing two Vulture runs."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Iterable

FINDING_RE = re.compile(
    r"^(?P<path>.*?):(?P<line>\d+): unused (?P<kind>.+?) '(?P<name>.+?)' "
    r"\((?P<confidence>\d+)% confidence(?:, (?P<size>\d+) line(?:s)?)?\)$"
)
SUCCESS_CODES = {0, 3}


@dataclass(frozen=True)
class Finding:
    raw: str
    path: str | None = None
    line: int | None = None
    symbol_kind: str | None = None
    symbol_name: str | None = None
    confidence: int | None = None
    size: int | None = None

    def key(self) -> str:
        if self.path is None or self.line is None:
            return f"raw::{self.raw}"
        return f"{self.path}:{self.line}:{self.symbol_kind}:{self.symbol_name}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run vulture twice and report symbols that are unused in production-only "
            "scan but become used when tests are included."
        ),
    )
    parser.add_argument(
        "--vulture-bin",
        default="vulture",
        help="Path to vulture executable. Default: vulture",
    )
    parser.add_argument(
        "--prod-path",
        action="append",
        default=[],
        help="Production path to analyze. Repeatable. Default: src",
    )
    parser.add_argument(
        "--test-path",
        action="append",
        default=[],
        help="Test path to analyze in second pass. Repeatable. Default: tests",
    )
    parser.add_argument(
        "--config",
        help="Vulture config file path (e.g. pyproject.toml).",
    )
    parser.add_argument(
        "--exclude",
        help="Comma-separated patterns for --exclude.",
    )
    parser.add_argument(
        "--ignore-names",
        help="Comma-separated patterns for --ignore-names.",
    )
    parser.add_argument(
        "--ignore-decorators",
        help="Comma-separated patterns for --ignore-decorators.",
    )
    parser.add_argument(
        "--min-confidence",
        type=int,
        help="Value for --min-confidence.",
    )
    parser.add_argument(
        "--sort-by-size",
        action="store_true",
        help="Forward --sort-by-size to both runs.",
    )
    parser.add_argument(
        "--verbose-vulture",
        action="store_true",
        help="Forward --verbose to both runs.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=200,
        help="Maximum findings to print per section. Default: 200",
    )
    parser.add_argument(
        "--json-output",
        help="Optional JSON output path.",
    )
    parser.add_argument(
        "--fail-on-test-only",
        action="store_true",
        help="Exit with 1 when test-only candidates are found.",
    )
    parser.add_argument(
        "--fail-on-unused-with-tests",
        action="store_true",
        help="Exit with 1 when findings remain unused even with tests.",
    )
    return parser.parse_args()


def dedupe_in_order(items: Iterable[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped


def parse_finding(line: str) -> Finding:
    match = FINDING_RE.match(line.strip())
    if not match:
        return Finding(raw=line.strip())

    size_text = match.group("size")
    return Finding(
        raw=line.strip(),
        path=match.group("path"),
        line=int(match.group("line")),
        symbol_kind=match.group("kind"),
        symbol_name=match.group("name"),
        confidence=int(match.group("confidence")),
        size=int(size_text) if size_text else None,
    )


def parse_findings(lines: Iterable[str]) -> list[Finding]:
    return [parse_finding(line) for line in lines if line.strip()]


def finding_sort_key(finding: Finding) -> tuple[str, int, str, str, str]:
    return (
        finding.path or "",
        finding.line or 0,
        finding.symbol_kind or "",
        finding.symbol_name or "",
        finding.raw,
    )


def build_lookup(findings: Iterable[Finding]) -> dict[str, Finding]:
    return {finding.key(): finding for finding in findings}


def run_vulture(vulture_bin: str, common_flags: list[str], paths: list[str]) -> dict[str, object]:
    command = [vulture_bin, *common_flags, *paths]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"vulture executable not found: {vulture_bin}") from exc

    stdout_lines = [line for line in completed.stdout.splitlines() if line.strip()]
    stderr_lines = [line for line in completed.stderr.splitlines() if line.strip()]
    if completed.returncode not in SUCCESS_CODES:
        stderr_text = "\n".join(stderr_lines) or "(no stderr)"
        raise RuntimeError(
            f"vulture failed with exit code {completed.returncode}:\n{stderr_text}"
        )

    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout_lines": stdout_lines,
        "stderr_lines": stderr_lines,
    }


def print_section(title: str, findings: list[Finding], max_items: int) -> None:
    print()
    print(f"[{title}]")
    if not findings:
        print("(none)")
        return

    for finding in findings[:max_items]:
        print(finding.raw)

    remaining = len(findings) - max_items
    if remaining > 0:
        print(f"... ({remaining} more)")


def serialize_finding(finding: Finding) -> dict[str, object]:
    data = asdict(finding)
    data["key"] = finding.key()
    return data


def build_common_flags(args: argparse.Namespace) -> list[str]:
    flags: list[str] = []
    if args.config:
        flags.extend(["--config", args.config])
    if args.exclude:
        flags.extend(["--exclude", args.exclude])
    if args.ignore_names:
        flags.extend(["--ignore-names", args.ignore_names])
    if args.ignore_decorators:
        flags.extend(["--ignore-decorators", args.ignore_decorators])
    if args.min_confidence is not None:
        flags.extend(["--min-confidence", str(args.min_confidence)])
    if args.sort_by_size:
        flags.append("--sort-by-size")
    if args.verbose_vulture:
        flags.append("--verbose")
    return flags


def main() -> int:
    args = parse_args()

    prod_paths = dedupe_in_order(args.prod_path or ["src"])
    test_paths = dedupe_in_order(args.test_path or ["tests"])
    combined_paths = dedupe_in_order([*prod_paths, *test_paths])
    common_flags = build_common_flags(args)

    prod_run = run_vulture(args.vulture_bin, common_flags, prod_paths)
    with_tests_run = run_vulture(args.vulture_bin, common_flags, combined_paths)

    prod_findings = parse_findings(prod_run["stdout_lines"])
    with_tests_findings = parse_findings(with_tests_run["stdout_lines"])

    prod_lookup = build_lookup(prod_findings)
    with_tests_lookup = build_lookup(with_tests_findings)

    test_only_candidates = sorted(
        (prod_lookup[key] for key in set(prod_lookup) - set(with_tests_lookup)),
        key=finding_sort_key,
    )
    unused_even_with_tests = sorted(
        with_tests_lookup.values(),
        key=finding_sort_key,
    )
    only_in_with_tests_scan = sorted(
        (with_tests_lookup[key] for key in set(with_tests_lookup) - set(prod_lookup)),
        key=finding_sort_key,
    )

    print("=== Double-pass Vulture Report ===")
    print(f"prod-only command : {shlex.join(prod_run['command'])}")
    print(f"with-tests command: {shlex.join(with_tests_run['command'])}")
    print(f"prod paths        : {', '.join(prod_paths)}")
    print(f"test paths        : {', '.join(test_paths)}")
    print(
        "exit codes        : "
        f"prod-only={prod_run['returncode']}, with-tests={with_tests_run['returncode']}"
    )
    print(f"unused(prod-only) : {len(prod_findings)}")
    print(f"unused(with-tests): {len(with_tests_findings)}")
    print(f"test-only         : {len(test_only_candidates)}")
    print(f"still-unused      : {len(unused_even_with_tests)}")
    print(f"only-in-with-tests: {len(only_in_with_tests_scan)}")

    print_section("TEST-ONLY CANDIDATES", test_only_candidates, args.max_items)
    print_section("UNUSED EVEN WITH TESTS", unused_even_with_tests, args.max_items)
    print_section("ONLY IN WITH-TESTS SCAN", only_in_with_tests_scan, args.max_items)

    if args.json_output:
        output_path = Path(args.json_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "metadata": {
                "prod_only_command": prod_run["command"],
                "with_tests_command": with_tests_run["command"],
                "prod_paths": prod_paths,
                "test_paths": test_paths,
                "exit_codes": {
                    "prod_only": prod_run["returncode"],
                    "with_tests": with_tests_run["returncode"],
                },
            },
            "counts": {
                "unused_prod_only": len(prod_findings),
                "unused_with_tests": len(with_tests_findings),
                "test_only_candidates": len(test_only_candidates),
                "still_unused_with_tests": len(unused_even_with_tests),
                "only_in_with_tests_scan": len(only_in_with_tests_scan),
            },
            "test_only_candidates": [
                serialize_finding(finding) for finding in test_only_candidates
            ],
            "unused_even_with_tests": [
                serialize_finding(finding) for finding in unused_even_with_tests
            ],
            "only_in_with_tests_scan": [
                serialize_finding(finding) for finding in only_in_with_tests_scan
            ],
        }
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print()
        print(f"JSON report written to: {output_path}")

    should_fail = False
    if args.fail_on_test_only and test_only_candidates:
        should_fail = True
    if args.fail_on_unused_with_tests and unused_even_with_tests:
        should_fail = True

    return 1 if should_fail else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        raise SystemExit(2)
