#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import uuid


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def atomic_write_json(path: Path, data: dict) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    tmp_path.replace(path)


def load_metadata(path: Path) -> dict:
    return json.loads(path.read_text())


def shell_join(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def default_resume_prompt(metadata: dict) -> str:
    run_dir = metadata["run_dir"]
    command_display = metadata["command_display"]
    title = metadata.get("title") or metadata["run_id"]
    continuation_task = metadata.get("continuation_task", "").strip()
    parts = [
        f"Long-running async Codex job finished: {title}",
        f"Run directory: {run_dir}",
        f"Command: {command_display}",
    ]
    if continuation_task:
        parts.append(f"Original task to continue:\n{continuation_task}")
    else:
        parts.append("Continue the user's original task from the resumed session context.")
    parts.extend(
        [
            (
                "Inspect metadata.json, stdout.log, stderr.log, exit_code, and any relevant output artifacts under "
                "or referenced by the run directory. Determine whether the run succeeded, failed, timed out, or "
                "produced inconclusive results. Then continue the original implementation, debugging, experiment, "
                "or verification task from the evidence. Do not stop at a result summary when there is a clear next "
                "implementation or validation step."
            ),
            (
                "Do not repeat a long-running command synchronously. If another long run is required, use the "
                "async-codex-job workflow again."
            ),
        ]
    )
    return "\n\n".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Start a long-running command outside Codex's wait loop and append a resumed "
            "inspection turn to the persisted Codex session when it finishes."
        )
    )
    parser.add_argument("--monitor", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--metadata", help=argparse.SUPPRESS)
    parser.add_argument("--run-id", help="Stable run id. Defaults to async-<UTC timestamp>-<short uuid>.")
    parser.add_argument("--title", default="", help="Human-readable run title stored in metadata and resume prompt.")
    parser.add_argument("--runs-dir", default=".codex-async-runs", help="Directory for run records.")
    parser.add_argument("--cwd", default=os.getcwd(), help="Working directory for the command.")
    parser.add_argument(
        "--resume-session",
        default=os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") or "",
        help="Codex session/thread id passed to `codex exec resume`. Defaults to CODEX_THREAD_ID or CODEX_SESSION_ID.",
    )
    parser.add_argument(
        "--continuation-task",
        default="",
        help="Concise description of the user's original objective and what Codex should continue after inspection.",
    )
    parser.add_argument("--resume-prompt", help="Custom prompt sent to Codex after command completion.")
    parser.add_argument("--no-resume", action="store_true", help="Run the job without calling Codex after completion.")
    parser.add_argument(
        "--allow-sandboxed-resume",
        action="store_true",
        help="Allow resume-enabled launch from inside CODEX_SANDBOX. This is usually unreliable.",
    )
    parser.add_argument("--codex-bin", default="codex", help="Codex CLI binary.")
    parser.add_argument("--shell", action="store_true", help="Treat the command as one shell string.")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run, after --.")
    return parser.parse_args()


def normalize_command(raw_command: list[str]) -> list[str]:
    command = list(raw_command)
    if command and command[0] == "--":
        command = command[1:]
    return command


def start(args: argparse.Namespace) -> int:
    command = normalize_command(args.command)
    if not command:
        print("error: command is required after --", file=sys.stderr)
        return 2
    if args.shell and len(command) != 1:
        print("error: --shell requires a single command string after --", file=sys.stderr)
        return 2
    if not args.no_resume and not args.resume_session:
        print(
            "error: no Codex session id found. Pass --resume-session or set CODEX_THREAD_ID/CODEX_SESSION_ID, "
            "or use --no-resume.",
            file=sys.stderr,
        )
        return 2
    if not args.no_resume and os.environ.get("CODEX_SANDBOX") and not args.allow_sandboxed_resume:
        print(
            "error: resume-enabled async jobs must be launched outside Codex's sandbox. "
            "Rerun this launcher with escalated permissions, or pass --allow-sandboxed-resume to accept that "
            "the detached `codex exec resume` step may fail when writing Codex state.",
            file=sys.stderr,
        )
        return 75

    cwd = Path(args.cwd).expanduser().resolve()
    if not cwd.exists():
        print(f"error: cwd does not exist: {cwd}", file=sys.stderr)
        return 2

    run_id = args.run_id or f"async-{dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    if "/" in run_id or run_id in {"", ".", ".."}:
        print("error: --run-id must be a single path segment", file=sys.stderr)
        return 2

    runs_dir = Path(args.runs_dir).expanduser()
    if not runs_dir.is_absolute():
        runs_dir = cwd / runs_dir
    run_dir = (runs_dir / run_id).resolve()
    if run_dir.exists():
        print(f"error: run directory already exists: {run_dir}", file=sys.stderr)
        return 2
    run_dir.mkdir(parents=True)

    metadata = {
        "run_id": run_id,
        "title": args.title,
        "status": "starting",
        "cwd": str(cwd),
        "run_dir": str(run_dir),
        "command": command,
        "command_display": command[0] if args.shell else shell_join(command),
        "shell": args.shell,
        "started_at": utc_now(),
        "resume_session": args.resume_session,
        "continuation_task": args.continuation_task,
        "no_resume": args.no_resume,
        "codex_bin": args.codex_bin,
        "paths": {
            "metadata": str(run_dir / "metadata.json"),
            "stdout": str(run_dir / "stdout.log"),
            "stderr": str(run_dir / "stderr.log"),
            "monitor": str(run_dir / "monitor.log"),
            "exit_code": str(run_dir / "exit_code"),
            "codex_events": str(run_dir / "codex-events.log"),
            "codex_summary": str(run_dir / "codex-summary.md"),
        },
    }
    if args.resume_prompt:
        metadata["resume_prompt"] = args.resume_prompt
    atomic_write_json(run_dir / "metadata.json", metadata)

    monitor_log = open(run_dir / "monitor.log", "a")
    monitor_cmd = [sys.executable, str(Path(__file__).resolve()), "--monitor", "--metadata", str(run_dir / "metadata.json")]
    process = subprocess.Popen(
        monitor_cmd,
        cwd=str(cwd),
        stdin=subprocess.DEVNULL,
        stdout=monitor_log,
        stderr=monitor_log,
        start_new_session=True,
        close_fds=True,
    )

    metadata["status"] = "monitoring"
    metadata["monitor_pid"] = process.pid
    metadata["monitor_started_at"] = utc_now()
    atomic_write_json(run_dir / "metadata.json", metadata)

    print(f"started async Codex job: {run_id}")
    print(f"run_dir: {run_dir}")
    print(f"metadata: {run_dir / 'metadata.json'}")
    print(f"monitor_pid: {process.pid}")
    print(f"resume_session: {'(disabled)' if args.no_resume else args.resume_session}")
    return 0


def monitor(metadata_path: Path) -> int:
    metadata = load_metadata(metadata_path)
    run_dir = Path(metadata["run_dir"])
    paths = {key: Path(value) for key, value in metadata["paths"].items()}

    metadata["status"] = "running"
    metadata["command_started_at"] = utc_now()
    atomic_write_json(metadata_path, metadata)

    with open(paths["stdout"], "wb") as stdout, open(paths["stderr"], "wb") as stderr:
        try:
            if metadata["shell"]:
                process = subprocess.Popen(
                    metadata["command"][0],
                    shell=True,
                    cwd=metadata["cwd"],
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=stderr,
                    start_new_session=True,
                )
            else:
                process = subprocess.Popen(
                    metadata["command"],
                    cwd=metadata["cwd"],
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=stderr,
                    start_new_session=True,
                )
        except OSError as exc:
            stderr.write(f"failed to launch command: {exc}\n".encode())
            exit_code = 127
            metadata["command_status"] = "launch_failed"
        else:
            metadata["pid"] = process.pid
            atomic_write_json(metadata_path, metadata)
            exit_code = process.wait()
            metadata["command_status"] = "succeeded" if exit_code == 0 else "failed"

    paths["exit_code"].write_text(f"{exit_code}\n")
    metadata["exit_code"] = exit_code
    metadata["finished_at"] = utc_now()
    metadata["status"] = metadata["command_status"]
    atomic_write_json(metadata_path, metadata)

    if metadata.get("no_resume"):
        return exit_code

    prompt = metadata.get("resume_prompt") or default_resume_prompt(metadata)
    codex_cmd = [
        metadata.get("codex_bin") or "codex",
        "exec",
        "resume",
        metadata["resume_session"],
        prompt,
        "-o",
        str(paths["codex_summary"]),
    ]

    with open(paths["codex_events"], "wb") as events:
        events.write((f"$ {shell_join(codex_cmd)}\n\n").encode())
        events.flush()
        try:
            resume = subprocess.run(
                codex_cmd,
                cwd=metadata["cwd"],
                stdin=subprocess.DEVNULL,
                stdout=events,
                stderr=subprocess.STDOUT,
                check=False,
            )
            resume_returncode = resume.returncode
        except OSError as exc:
            events.write(f"failed to launch codex resume: {exc}\n".encode())
            resume_returncode = 127

    metadata["resume_exit_code"] = resume_returncode
    metadata["resume_finished_at"] = utc_now()
    metadata["status"] = "resume_succeeded" if resume_returncode == 0 else "resume_failed"
    atomic_write_json(metadata_path, metadata)
    return exit_code


def main() -> int:
    args = parse_args()
    if args.monitor:
        if not args.metadata:
            print("error: --metadata is required in monitor mode", file=sys.stderr)
            return 2
        return monitor(Path(args.metadata))
    return start(args)


if __name__ == "__main__":
    raise SystemExit(main())
