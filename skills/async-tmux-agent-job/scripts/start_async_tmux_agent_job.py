#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid


SAFE_JOB_ID = re.compile(r"^[A-Za-z0-9_.-]+$")


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


def run_tmux(args: list[str], *, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["tmux", *args],
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def verify_tmux_target(target_pane: str) -> str:
    result = run_tmux(["display-message", "-p", "-t", target_pane, "#{pane_id}"], check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"tmux target not found: {target_pane}")
    return result.stdout.strip()


def default_completion_prompt(metadata: dict) -> str:
    title = metadata.get("title") or metadata["job_id"]
    continuation_task = metadata.get("continuation_task", "").strip()
    parts = [
        f"Async tmux job finished: {title}",
        f"Run directory: {metadata['run_dir']}",
        f"Command: {metadata['command_display']}",
    ]
    if continuation_task:
        parts.append(f"Original task to continue:\n{continuation_task}")
    else:
        parts.append("Continue the user's original task from this tmux pane session.")
    parts.extend(
        [
            (
                "Inspect metadata.json, stdout.log, stderr.log, exit_code, and any relevant output artifacts under "
                "or referenced by the run directory. Determine whether the run succeeded, failed, timed out, or "
                "produced inconclusive results. Then continue the original task from the evidence. Do not stop at "
                "a result summary when there is a clear next implementation or verification step."
            ),
            "Do not repeat a long-running command synchronously. If another long run is required, use the async-tmux-agent-job workflow again.",
        ]
    )
    return "\n\n".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a command asynchronously and paste a completion prompt back into the current tmux pane."
    )
    parser.add_argument("--monitor", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--metadata", help=argparse.SUPPRESS)
    parser.add_argument("--job-id", help="Stable job id. Defaults to async-<UTC timestamp>-<short uuid>.")
    parser.add_argument("--title", default="", help="Human-readable title stored in metadata and completion prompt.")
    parser.add_argument("--cwd", default=os.getcwd(), help="Working directory for the command.")
    parser.add_argument("--runs-dir", default=".async-tmux-agent-jobs", help="Directory for metadata and logs.")
    parser.add_argument(
        "--target-pane",
        default=os.environ.get("TMUX_PANE", ""),
        help="tmux pane to paste the completion prompt into. Defaults to TMUX_PANE.",
    )
    parser.add_argument(
        "--continuation-task",
        default="",
        help="Concise description of the user's original objective and what the agent should continue after inspection.",
    )
    parser.add_argument("--completion-prompt", help="Custom prompt pasted into the target pane after command completion.")
    parser.add_argument(
        "--submit-delay",
        type=float,
        default=1.0,
        help="Seconds to wait between paste-buffer and submit key. The target TUI may need time to process bracketed paste.",
    )
    parser.add_argument("--submit-key", default="C-m", help="tmux key sent after paste-buffer to submit the prompt.")
    parser.add_argument("--shell", action="store_true", help="Treat the command as one shell string.")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run, after --.")
    return parser.parse_args()


def normalize_command(raw_command: list[str]) -> list[str]:
    command = list(raw_command)
    if command and command[0] == "--":
        command = command[1:]
    return command


def paste_prompt(target_pane: str, prompt: str, job_id: str, submit_delay: float, submit_key: str) -> None:
    buffer_name = f"async-tmux-agent-job-{job_id}"
    run_tmux(["load-buffer", "-b", buffer_name, "-"], input_text=prompt)
    run_tmux(["paste-buffer", "-d", "-b", buffer_name, "-t", target_pane])
    if submit_delay > 0:
        time.sleep(submit_delay)
    run_tmux(["send-keys", "-t", target_pane, submit_key])


def start(args: argparse.Namespace) -> int:
    if shutil.which("tmux") is None:
        print("error: tmux was not found in PATH", file=sys.stderr)
        return 127

    command = normalize_command(args.command)
    if not command:
        print("error: command is required after --", file=sys.stderr)
        return 2
    if args.shell and len(command) != 1:
        print("error: --shell requires a single command string after --", file=sys.stderr)
        return 2
    if not args.target_pane:
        print("error: no tmux target pane. Run from inside tmux or pass --target-pane.", file=sys.stderr)
        return 2

    job_id = args.job_id or f"async-{dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    if not SAFE_JOB_ID.fullmatch(job_id):
        print("error: --job-id must contain only letters, digits, '.', '_', or '-'", file=sys.stderr)
        return 2

    try:
        target_pane = verify_tmux_target(args.target_pane)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    cwd = Path(args.cwd).expanduser().resolve()
    if not cwd.exists():
        print(f"error: cwd does not exist: {cwd}", file=sys.stderr)
        return 2

    runs_dir = Path(args.runs_dir).expanduser()
    if not runs_dir.is_absolute():
        runs_dir = cwd / runs_dir
    run_dir = (runs_dir / job_id).resolve()
    if run_dir.exists():
        print(f"error: run directory already exists: {run_dir}", file=sys.stderr)
        return 2
    run_dir.mkdir(parents=True)

    metadata = {
        "job_id": job_id,
        "title": args.title,
        "status": "starting",
        "cwd": str(cwd),
        "run_dir": str(run_dir),
        "target_pane": target_pane,
        "command": command,
        "command_display": command[0] if args.shell else shell_join(command),
        "shell": args.shell,
        "continuation_task": args.continuation_task,
        "submit_delay": args.submit_delay,
        "submit_key": args.submit_key,
        "started_at": utc_now(),
        "paths": {
            "metadata": str(run_dir / "metadata.json"),
            "stdout": str(run_dir / "stdout.log"),
            "stderr": str(run_dir / "stderr.log"),
            "monitor": str(run_dir / "monitor.log"),
            "exit_code": str(run_dir / "exit_code"),
        },
    }
    if args.completion_prompt:
        metadata["completion_prompt"] = args.completion_prompt
    metadata_path = run_dir / "metadata.json"
    atomic_write_json(metadata_path, metadata)

    monitor_log = open(run_dir / "monitor.log", "a")
    monitor_cmd = [sys.executable, str(Path(__file__).resolve()), "--monitor", "--metadata", str(metadata_path)]
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
    atomic_write_json(metadata_path, metadata)

    print(f"started async tmux agent job: {job_id}")
    print(f"target_pane: {target_pane}")
    print(f"metadata: {metadata_path}")
    print(f"stdout: {run_dir / 'stdout.log'}")
    print(f"stderr: {run_dir / 'stderr.log'}")
    print(f"monitor_pid: {process.pid}")
    print("completion: prompt will be pasted back into this tmux pane when the command finishes")
    return 0


def monitor(metadata_path: Path) -> int:
    metadata = load_metadata(metadata_path)
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

    prompt = metadata.get("completion_prompt") or default_completion_prompt(metadata)
    try:
        paste_prompt(
            metadata["target_pane"],
            prompt,
            metadata["job_id"],
            metadata["submit_delay"],
            metadata["submit_key"],
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        metadata["paste_status"] = "failed"
        metadata["paste_error"] = str(exc)
    else:
        metadata["paste_status"] = "succeeded"
        metadata["pasted_at"] = utc_now()
    metadata["status"] = f"{metadata['command_status']}_paste_{metadata['paste_status']}"
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
