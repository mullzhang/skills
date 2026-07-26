---
name: kanary-transcribe-media
description: Transcribe one user-specified MP4 or WAV with the Kanary skill, save Kanary's full JSON beside the source, and render a summarized, timestamped Markdown transcript beside it. Use when a user asks to transcribe a local .mp4 or .wav file into sibling Markdown and JSON files while preserving the source media.
---

# Kanary Transcribe Media

Create two sibling files for one source media file:

- `<source-stem>.transcript.json`: Kanary's unmodified full transcript JSON
- `<source-stem>.transcript.md`: timestamped Markdown rendered from that JSON

Never modify the source MP4 or WAV.

## Sample

Use `assets/sample.wav` for a smoke test and `assets/sample.transcript.md` as the expected summarized Markdown example. Copy the WAV to a writable temporary directory before invoking this skill so the sibling JSON and Markdown outputs do not modify the bundled assets directory.

## Workflow

1. Accept exactly one existing `.mp4` or `.wav` path. Reject other extensions instead of inferring support.
2. Resolve the source to an absolute path and derive both output paths in its directory.
3. Show the exact JSON and Markdown paths and obtain confirmation before writing. This satisfies the Kanary skill's `transcribe --out` destination confirmation requirement.
4. If either output already exists, stop and obtain explicit overwrite approval. Remove only the approved output files before continuing; never overwrite silently.
5. Create a task-specific temporary directory for the summary and any normalized audio. Prepare the transcription input:
   - For WAV, use the source directly.
   - For MP4, create a task-specific temporary directory outside the source directory. Extract a 16 kHz mono PCM WAV with:

     ```sh
     uv run --with imageio-ffmpeg python <skill-dir>/scripts/extract_mp4_audio.py <source.mp4> <temporary.wav>
     ```

     The script reads the MP4 and writes only the temporary WAV. If `uv` needs network access to obtain `imageio-ffmpeg`, request the required approval rather than selecting another converter.
6. Invoke `$kanary`: read the installed Kanary `SKILL.md` completely and follow it for status checks, sandbox escalation, plan limits, error handling, and ephemeral transcription. Run top-level transcription without importing into the recordings library:

   ```sh
   kanary transcribe <wav-input> --out <source-stem>.transcript.json
   ```

   Keep stderr visible. Project the receipt with `jq` instead of loading the full transcript into context.
7. Generate a concise summary from the transcript text after Kanary succeeds:
   - Project only timestamp, channel, and text from `transcript.segments` with `jq`.
   - Summarize in the transcript's language using one to seven factual bullets, scaled to the recording length.
   - Prioritize key points, decisions, next actions, and unresolved questions when present.
   - Do not invent speaker names or attribute statements to named speakers when the transcript lacks diarization.
   - For a transcript too large to summarize in one pass, summarize successive time windows and synthesize those window summaries.
   - Save only the bullet list, without a heading, as a temporary UTF-8 Markdown file.
8. Render Markdown with the summary body:

   ```sh
   python <skill-dir>/scripts/render_transcript_markdown.py <source-media> <transcript.json> <summary.md> <transcript.md>
   ```

9. Verify all of the following before handoff:
   - both outputs are regular files in the source directory
   - JSON contains numeric `duration` and a `transcript.segments` array
   - the Markdown renderer reports the same segment count as the JSON
   - Markdown contains a non-empty `## Summary` before `## Transcript`
   - when the JSON has segments, Markdown contains its first and last timestamped segments
10. Remove only the task-specific temporary directory. Keep both sibling outputs.
11. Report the Markdown path, JSON path, duration, segment count, diagnostic count, and that the source media was not modified.

## Failure Rules

- Follow the Kanary skill exactly for sandbox, IPC, and Pro/plan failures.
- If MP4 extraction, Kanary transcription, summary generation, or Markdown rendering fails, stop and report the failed stage and stderr.
- Do not create Markdown from partial or plan-limited JSON.
- Do not delete a successfully created JSON file merely because Markdown rendering failed.
