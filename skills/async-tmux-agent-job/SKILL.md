---
name: async-tmux-agent-job
description: Use when an interactive terminal agent is running inside tmux and needs to start a long-running command asynchronously, return control to the current conversation, then paste a completion prompt back into the same tmux pane so the same visible agent session continues after the command finishes. Use for experiments, benchmarks, tests, data processing, or other command jobs where same-pane continuation is more important than non-interactive session resume.
---

# Async Tmux Agent Job

Use this skill to run a long command in the background and continue the same visible tmux pane when the command finishes.

This skill does not create a new tmux window or pane. It captures the current tmux pane, starts a detached monitor process, and later pastes a follow-up prompt into that same pane.

## Decision Rule

Use this workflow when all are true:

- An interactive terminal agent is running inside tmux.
- The user wants the current visible agent session to continue after a long command finishes.
- The command can run non-interactively once started.
- Logs and output artifacts are enough for the agent to inspect after completion.

Do not use it when the agent is not running inside tmux, the current pane is not expected to be idle after launch, the command requires live prompts, or creating a separate pane/window is explicitly desired.

## Workflow

1. Make any setup or code changes required before the long command.
2. Choose a stable `job_id`, for example `async-20260613-benchmark` or `delayed-experiment`.
3. Write a concise `continuation_task` that captures the user's original objective and what the agent should do after inspecting the command result.
4. Build the exact command as an argv list. Avoid shell strings unless shell features are necessary.
5. If running from a sandbox, request escalation before launching. tmux socket access often fails inside sandboxed tool execution.
6. Run `scripts/start_async_tmux_agent_job.py` from the current tmux-pane agent session.
7. Verify that the launcher printed the target pane, metadata path, stdout/stderr paths, and monitor pid.
8. Return immediately. Do not poll logs, capture the pane, sleep, or wait for completion.

After step 7, stop. When the command finishes, the monitor pastes a completion prompt into the same tmux pane, waits briefly for the target TUI to process the pasted block, and sends the submit key. The current agent session then receives the result-inspection request like a user follow-up.

## Quick Start

From the target repository root:

```bash
ASYNC_TMUX_SCRIPT="<skill-dir>/scripts/start_async_tmux_agent_job.py"

python "$ASYNC_TMUX_SCRIPT" \
  --job-id delayed-experiment \
  --title "Delayed experiment" \
  --continuation-task "Use the delayed experiment result to continue the user's original request: inspect the logs and artifacts, decide success or failure, and take the next clear step." \
  -- \
  ./run_delayed_experiment.sh
```

For commands that need shell syntax:

```bash
python "$ASYNC_TMUX_SCRIPT" \
  --job-id benchmark-pipeline \
  --title "Benchmark pipeline" \
  --continuation-task "Use the benchmark output to continue the requested performance investigation." \
  --shell \
  -- \
  'set -euo pipefail; make data && uv run python benchmarks/run.py'
```

## Launcher Behavior

The launcher:

- Uses `TMUX_PANE` as the default target pane.
- Verifies the pane exists before starting the background monitor.
- Starts the command in a detached monitor process.
- Writes `.async-tmux-agent-jobs/<job_id>/metadata.json`.
- Captures command stdout/stderr to `.async-tmux-agent-jobs/<job_id>/stdout.log` and `stderr.log`.
- Writes `.async-tmux-agent-jobs/<job_id>/exit_code` after completion.
- Uses `tmux load-buffer`, `paste-buffer`, a short `--submit-delay`, and `send-keys C-m` to paste and submit the completion prompt back into the original pane.

No new tmux window or pane is created.

## Completion Prompt Requirements

The completion prompt should tell the agent to:

- Read `metadata.json`, `stdout.log`, `stderr.log`, `exit_code`, and relevant output artifacts.
- Decide whether the run succeeded, failed, timed out, or produced inconclusive results.
- Continue the user's original implementation, debugging, experiment, or verification work from the evidence.
- Take the next clear action without waiting for the user when the evidence makes that action obvious.
- Avoid starting another long synchronous wait; use this skill again for follow-up long runs.

## Operational Rules

- Prefer the current `TMUX_PANE`; pass `--target-pane` only when the current environment cannot provide it.
- Prefer explicit `--continuation-task "..."` over relying on generic conversation context.
- Never create a new tmux window or pane unless the user explicitly asks for that different workflow.
- Run the launcher outside sandboxed tool execution when tmux reports socket permission errors.
- Keep the default `--submit-delay 1.0` unless real testing shows the target TUI needs a different value.
- Do not send secrets through `--continuation-task` or `--completion-prompt`; prompts are visible and persisted in metadata.
- If the command may finish before the launching agent turn returns to idle, do not use this workflow; the pasted completion prompt can collide with active TUI output.
- If the launcher fails before printing `started async tmux agent job`, fix the setup or report the failure; do not claim the job is running.
