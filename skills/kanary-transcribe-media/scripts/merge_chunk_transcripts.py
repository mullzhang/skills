#!/usr/bin/env python3
"""Merge overlapping Kanary transcript chunks onto the original timeline."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("transcripts", nargs="+", type=Path)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise SystemExit(f"JSON object required: {path}")
    return value


def transcript_parts(data: dict[str, Any], path: Path) -> tuple[list[dict[str, Any]], list[Any]]:
    transcript = data.get("transcript")
    if not isinstance(transcript, dict):
        raise SystemExit(f"missing transcript object: {path}")
    segments = transcript.get("segments")
    diagnostics = transcript.get("diagnostics")
    if not isinstance(segments, list) or not isinstance(diagnostics, list):
        raise SystemExit(f"missing transcript segments or diagnostics: {path}")
    return segments, diagnostics


def numeric(value: Any, field: str, path: Path) -> float:
    if not isinstance(value, (int, float)):
        raise SystemExit(f"{field} must be numeric: {path}")
    return float(value)


def main() -> None:
    args = parse_args()
    manifest_path = args.manifest.resolve(strict=True)
    output = args.output.resolve()
    transcript_paths = [path.resolve(strict=True) for path in args.transcripts]
    if output.suffix.lower() != ".json":
        raise SystemExit(f"output must use the .json extension: {output}")
    if output.exists():
        raise SystemExit(f"refusing to overwrite output: {output}")

    manifest = load_json(manifest_path)
    chunks = manifest.get("chunks")
    source_duration = manifest.get("source_duration")
    if not isinstance(chunks, list) or len(chunks) != len(transcript_paths):
        raise SystemExit("manifest chunks must match transcript count")
    source_duration = numeric(source_duration, "source_duration", manifest_path)

    raw_transcripts = [load_json(path) for path in transcript_paths]
    merged_segments: list[dict[str, Any]] = []
    merged_diagnostics: list[Any] = []
    covered_until = 0.0
    dropped_overlap_segments = 0

    for index, (chunk, raw, path) in enumerate(zip(chunks, raw_transcripts, transcript_paths, strict=True)):
        if not isinstance(chunk, dict):
            raise SystemExit(f"invalid chunk at index {index}")
        chunk_start = numeric(chunk.get("source_start_seconds"), "source_start_seconds", manifest_path)
        chunk_end = numeric(chunk.get("source_end_seconds"), "source_end_seconds", manifest_path)
        if chunk_end <= chunk_start:
            raise SystemExit(f"non-positive chunk duration at index {index}")
        segments, diagnostics = transcript_parts(raw, path)
        merged_diagnostics.extend(diagnostics)
        for segment in segments:
            if not isinstance(segment, dict):
                raise SystemExit(f"invalid segment in {path}")
            start = numeric(segment.get("start_seconds"), "segment start_seconds", path) + chunk_start
            end = numeric(segment.get("end_seconds"), "segment end_seconds", path) + chunk_start
            if end <= covered_until:
                dropped_overlap_segments += 1
                continue
            merged = copy.deepcopy(segment)
            merged["start_seconds"] = max(start, covered_until)
            merged["end_seconds"] = end
            merged_segments.append(merged)
        covered_until = max(covered_until, chunk_end)

    result = copy.deepcopy(raw_transcripts[0])
    result["duration"] = source_duration
    transcript = result.get("transcript")
    assert isinstance(transcript, dict)
    transcript["segments"] = merged_segments
    transcript["diagnostics"] = merged_diagnostics
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out_path": str(output),
                "duration": source_duration,
                "segments": len(merged_segments),
                "diagnostics": len(merged_diagnostics),
                "dropped_overlap_segments": dropped_overlap_segments,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
