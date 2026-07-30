#!/usr/bin/env python3
"""Split a PCM WAV into overlapping, Kanary-safe WAV chunks."""

from __future__ import annotations

import argparse
import json
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--chunk-seconds", type=float, default=4200)
    parser.add_argument("--overlap-seconds", type=float, default=300)
    return parser.parse_args()


def wav_duration(source: Path) -> float:
    try:
        with wave.open(str(source), "rb") as reader:
            frame_rate = reader.getframerate()
            if frame_rate <= 0:
                raise ValueError("WAV has no frame rate")
            return reader.getnframes() / frame_rate
    except (wave.Error, ValueError) as error:
        raise SystemExit(f"source must be a readable PCM WAV: {source}: {error}") from error


def planned_chunks(duration: float, chunk_seconds: float, overlap_seconds: float) -> list[tuple[float, float]]:
    chunks: list[tuple[float, float]] = []
    start = 0.0
    while start < duration:
        end = min(start + chunk_seconds, duration)
        chunks.append((start, end))
        if end == duration:
            break
        start = end - overlap_seconds
    return chunks


def main() -> None:
    args = parse_args()
    source = args.source.resolve(strict=True)
    output_dir = args.output_dir.resolve()
    manifest = args.manifest.resolve()

    if not source.is_file() or source.suffix.lower() != ".wav":
        raise SystemExit(f"source must be an existing WAV file: {source}")
    if args.chunk_seconds <= 0 or args.overlap_seconds < 0 or args.overlap_seconds >= args.chunk_seconds:
        raise SystemExit("require chunk-seconds > overlap-seconds >= 0")
    if output_dir.exists() and not output_dir.is_dir():
        raise SystemExit(f"output_dir is not a directory: {output_dir}")
    if manifest.exists():
        raise SystemExit(f"refusing to overwrite manifest: {manifest}")

    duration = wav_duration(source)
    chunks = planned_chunks(duration, args.chunk_seconds, args.overlap_seconds)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = [output_dir / f"chunk_{index:02d}.wav" for index in range(1, len(chunks) + 1)]
    existing = [path for path in output_paths if path.exists()]
    if existing:
        raise SystemExit(f"refusing to overwrite chunk: {existing[0]}")

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    records: list[dict[str, float | int | str]] = []
    for index, ((start, end), output) in enumerate(zip(chunks, output_paths, strict=True), start=1):
        command = [
            ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-n",
            "-ss",
            f"{start:.6f}",
            "-t",
            f"{end - start:.6f}",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
        subprocess.run(command, check=True)
        records.append(
            {
                "index": index,
                "path": str(output),
                "source_start_seconds": start,
                "source_end_seconds": end,
            }
        )

    payload = {
        "source_path": str(source),
        "source_duration": duration,
        "chunk_seconds": args.chunk_seconds,
        "overlap_seconds": args.overlap_seconds,
        "chunks": records,
    }
    manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
