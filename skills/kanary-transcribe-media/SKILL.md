---
name: kanary-transcribe-media
description: Transcribe one user-specified MP4, M4A, or WAV with the Kanary skill, save full transcript JSON beside the source, and render a summarized, timestamped Markdown transcript beside it. For recordings exceeding Kanary's plan limit, split the WAV into overlapping chunks, retain the raw JSON for every chunk, and render one deduplicated Markdown transcript. Use when a user asks to transcribe a local .mp4, .m4a, or .wav file while preserving the source media.
---

# Kanary Transcribe Media

For a recording within Kanary's plan limit, create two sibling files:

- `<source-stem>.transcript.json`: Kanary's unmodified full transcript JSON
- `<source-stem>.transcript.md`: timestamped Markdown rendered from that JSON

Never modify the source MP4, M4A, or WAV.

For a recording that requires splitting, retain one unmodified Kanary JSON per
chunk and create one integrated Markdown transcript:

- `<source-stem>.part01.transcript.json`, `<source-stem>.part02.transcript.json`, ...
- `<source-stem>.transcript.md`

Do not create `<source-stem>.transcript.json` for a split recording: it would
not be an unmodified Kanary response.

## Sample

Use `assets/sample.wav` for a smoke test and `assets/sample.transcript.md` as the expected summarized Markdown example. Copy the WAV to a writable temporary directory before invoking this skill so the sibling JSON and Markdown outputs do not modify the bundled assets directory.

## Workflow

1. Accept exactly one existing `.mp4`, `.m4a`, or `.wav` path. Reject other extensions instead of inferring support.
2. Resolve the source to an absolute path and derive both output paths in its directory.
3. Show the exact JSON and Markdown paths and obtain confirmation before writing. This satisfies the Kanary skill's `transcribe --out` destination confirmation requirement.
4. If either output already exists, stop and obtain explicit overwrite approval. Remove only the approved output files before continuing; never overwrite silently.
5. Create a task-specific temporary directory for the summary and any normalized audio. Prepare the transcription input:
   - For WAV, use the source directly.
   - For MP4 or M4A, create a task-specific temporary directory outside the source directory. Extract a 16 kHz mono PCM WAV with:

     ```sh
     uv run --with imageio-ffmpeg python <skill-dir>/scripts/extract_mp4_audio.py <source-media> <temporary.wav>
     ```

     The script reads the MP4 or M4A and writes only the temporary WAV. If `uv` needs network access to obtain `imageio-ffmpeg`, request the required approval rather than selecting another converter.
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

## Long recordings

When the source duration exceeds Kanary's plan limit, or top-level transcription
reports a Pro/plan duration error, use this workflow instead of producing a
partial transcript. Keep stderr visible and never summarize a plan-limited
response.

1. Derive the numbered raw JSON paths and integrated Markdown path. Show every
   path and obtain confirmation before writing. Check each path for an existing
   file and obtain explicit overwrite approval if any exists.
2. Create a task-specific temporary directory outside the source directory.
   Normalize an MP4 or M4A to a temporary WAV as in the standard workflow. For
   a WAV, use it as the splitter input.
3. Split the WAV into chunks of at most 70 minutes with a five-minute overlap:

   ```sh
   uv run --with imageio-ffmpeg python <skill-dir>/scripts/split_wav_for_kanary.py \
     <wav-input> <temporary-dir>/chunks --manifest <temporary-dir>/chunks.json \
     --chunk-seconds 4200 --overlap-seconds 300
   ```

   The script creates only temporary PCM WAV files and a manifest. It refuses
   to overwrite either. Keep the manifest: it records the source-time offsets
   needed to merge transcript timestamps.
4. Transcribe every temporary chunk with top-level `kanary transcribe`. Write
   each raw response to its confirmed sibling part JSON path. Project each
   receipt with `jq`. If any chunk fails or is plan-limited, stop; keep the raw
   JSON files that already succeeded and do not create the integrated Markdown.
5. Merge the chunk JSON files only in the temporary directory. The merger shifts
   timestamps to the original recording timeline, takes the earlier chunk in an
   overlap, and clips a boundary-crossing segment rather than dropping it:

   ```sh
   python <skill-dir>/scripts/merge_chunk_transcripts.py \
     <temporary-dir>/chunks.json <temporary-dir>/merged.transcript.json \
     <source-stem>.part01.transcript.json <source-stem>.part02.transcript.json ...
   ```

   The merged JSON is an intermediate artifact, not a Kanary-original JSON and
   must not be kept beside the source.
6. Project timestamp, channel, and text from the merged JSON. Generate the
   summary as in the standard workflow, then render the integrated Markdown:

   ```sh
   python <skill-dir>/scripts/render_transcript_markdown.py \
     <source-media> <temporary-dir>/merged.transcript.json \
     <temporary-dir>/summary.md <source-stem>.transcript.md
   ```

7. Verify every part JSON and the Markdown are regular sibling files. Verify
   each raw JSON has numeric `duration` and `transcript.segments`; verify the
   Markdown segment count equals the merged-transcript receipt; verify the
   non-empty `## Summary` precedes `## Transcript`; and verify it contains the
   first and last merged timestamped segments.
8. Remove only the task-specific temporary directory. Report the overlap,
   individual raw JSON paths, integrated Markdown path, source duration, raw
   segment and diagnostic totals, merged segment count, and that the source was
   not modified.

## Failure Rules

- Follow the Kanary skill exactly for sandbox, IPC, and Pro/plan failures.
- If media extraction, Kanary transcription, summary generation, or Markdown rendering fails, stop and report the failed stage and stderr.
- Do not create Markdown from partial or plan-limited JSON.
- Do not delete a successfully created JSON file merely because Markdown rendering failed.
