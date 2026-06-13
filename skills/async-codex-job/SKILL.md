---
name: async-codex-job
description: Use when Codex is asked to implement code and run experiments, benchmarks, training, simulations, optimization, data processing, or other long-running commands that may take many minutes or hours. Launch the command outside Codex's active wait loop, persist logs and metadata, return control to the user, and arrange for Codex CLI to append a resumed turn that inspects results and continues the user's original task after completion.
---

# Async Codex Job

Use this skill when a requested implementation or investigation requires a long-running command and waiting inside the current Codex turn would waste the session.

## Decision Rule

Use the async handoff when all are true:

- The command is expected to take more than about 10 minutes, or its duration is uncertain.
- The command can run non-interactively once started.
- Logs and output artifacts are enough for Codex to inspect results later.
- A Codex session id is available through `CODEX_THREAD_ID`, `CODEX_SESSION_ID`, or an explicit user-provided id.

Do not use it when the command is quick, requires live prompts, needs repeated approvals, or the user explicitly asked Codex to wait.

## Workflow

1. Make the implementation or setup changes needed before the long run.
2. Choose a stable `run_id` such as `exp-001`, `train-20260613`, or `benchmark-baseline`.
3. Write a concise `continuation_task` that captures the user's original objective and the next action Codex should take after inspecting the run. This is Codex's responsibility; do not ask the user to restate it.
4. Build the exact command as an argv list. Avoid shell strings unless shell features are necessary.
5. If automatic resume is enabled and you are running from Codex's sandbox, request escalation and start `scripts/start_async_codex_job.py` outside the sandbox. The launcher refuses sandboxed resume by default because the later detached `codex exec resume` needs to write Codex state under `~/.codex`.
6. Verify that the launcher printed the run directory, monitor pid, and metadata path.
7. Return to the user immediately with the command, run directory, and a clear statement that Codex is not waiting for completion.
8. After the command finishes, the monitor calls `codex exec resume <session_id> <prompt>` and asks Codex to inspect the saved artifacts.

After step 6, stop. Do not poll the process, sleep, tail logs, read `metadata.json`, call `write_stdin`, or wait for the run to finish in the launching turn. Those actions defeat the purpose of this skill. The resumed Codex turn is responsible for inspecting results and continuing the original task after completion.

Important limitation: `codex exec resume` appends work to Codex's persisted session state; it does not force an already-open Codex App window or Codex CLI TUI to live-refresh. The user may need to reload/restart the App or leave and re-enter the CLI session with `codex resume --last` to see the appended resumed turn. Do not claim that the current visible UI will automatically wake up.

## Defaults

When the user does not specify these values, choose them without asking:

- Generate `run_id` as `async-<UTC timestamp>-<short command label>`, for example `async-20260613T091500Z-train`.
- Use `.codex-async-runs/<run_id>/artifacts` as the default artifact or output directory for commands that need one.
- Enable automatic persisted-session resume by default with `CODEX_THREAD_ID` or `CODEX_SESSION_ID`.
- Pass `--continuation-task` with a concise summary of the user's original objective and expected next step after the run.
- Use `--no-resume` only when the user explicitly asks not to resume, or when no session id is available.
- If the target command accepts an output directory argument, pass the default artifact directory explicitly. If it does not, do not invent command-specific flags; rely on stdout/stderr and existing output behavior.

## Quick Start

From the target repository root:

```bash
ASYNC_SCRIPT="${CODEX_HOME:-$HOME/.codex}/skills/async-codex-job/scripts/start_async_codex_job.py"

python "$ASYNC_SCRIPT" \
  --run-id exp-001 \
  --title "Evaluate new ranking implementation" \
  --resume-session "${CODEX_THREAD_ID:-${CODEX_SESSION_ID:-}}" \
  --continuation-task "Use the evaluation results to finish the requested ranking change: fix failures if needed, rerun only short checks, and report the final state." \
  -- \
  uv run python experiments/run_eval.py --config configs/eval.toml
```

If `CODEX_THREAD_ID` and `CODEX_SESSION_ID` are both empty, stop and get an explicit session id instead of guessing. Do not use `codex exec resume --last` unless the user explicitly accepts the risk of resuming the wrong session.

For commands that genuinely need shell syntax:

```bash
python "$ASYNC_SCRIPT" \
  --run-id exp-002 \
  --title "Pipeline benchmark" \
  --resume-session "$CODEX_THREAD_ID" \
  --continuation-task "Use the pipeline benchmark result to continue the requested performance investigation and implement or report the next evidence-backed step." \
  --shell \
  -- \
  'set -euo pipefail; make data && uv run python benchmarks/run.py | tee benchmark.log'
```

## Generated Files

Each run writes to `.codex-async-runs/<run_id>/` by default:

- `metadata.json`: command, cwd, pid, session id, timestamps, status, and resume result.
- `stdout.log`: command stdout.
- `stderr.log`: command stderr.
- `monitor.log`: launcher and monitor events.
- `exit_code`: command exit code after completion.
- `codex-events.log`: stdout/stderr from the `codex exec resume` call.
- `codex-summary.md`: output file requested from the resumed Codex run. This is the most reliable place to inspect the result when the App or CLI display has not refreshed yet.

## Resume Prompt Requirements

The completion prompt should tell Codex to:

- Read `metadata.json`, `stdout.log`, `stderr.log`, `exit_code`, and relevant output artifacts.
- Decide whether the run succeeded, failed, timed out, or produced inconclusive results.
- Continue the user's original implementation, debugging, experiment, or verification work from the evidence.
- Take the next clear action without waiting for the user when the evidence makes that action obvious.
- Avoid starting another long synchronous wait; use this skill again for follow-up long runs.
- Ask the user only when progress depends on a real decision or external permission.

## Operational Rules

- Prefer explicit `--resume-session "$CODEX_THREAD_ID"` or `--resume-session "$CODEX_SESSION_ID"`.
- Prefer explicit `--continuation-task "..."` over relying on generic resumed-session context.
- For resume-enabled jobs started by Codex, run the launcher with escalated permissions so the detached monitor can later run `codex exec resume` outside the sandbox.
- After the launcher returns `started async Codex job`, do not call `write_stdin`, `sleep`, `tail`, `cat`, `sed`, or any other command to inspect progress or wait for completion. Give the user the run directory and end the turn.
- In the launch response, state that completion will be appended to the persisted session and summarized in `codex-summary.md`; do not promise live display in the currently open App or CLI.
- The only acceptable launching-turn follow-up is to handle a launcher failure before the monitor starts.
- Keep the first resumed step mostly read-only: inspect logs, diagnose, summarize, then choose the next action.
- Store run outputs under the repository when they are part of the experiment record; use `/tmp` only for disposable checks.
- Do not put secrets into the command title, run id, or resume prompt. They are persisted in metadata.
- If the launcher fails before starting the monitor, fix the setup immediately instead of claiming the job is running.
- If the command succeeds but `codex exec resume` fails, treat `metadata.json` and `codex-events.log` as evidence. Report `status`, `command_status`, `exit_code`, `resume_exit_code`, and the resume error before deciding whether the environment or the experiment failed.
