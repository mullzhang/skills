#!/usr/bin/env python3
"""Extract a normalized WAV from MP4 or M4A media without modifying the source."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import imageio_ffmpeg


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = args.source.resolve(strict=True)
    output = args.output.resolve()

    if not source.is_file() or source.suffix.lower() not in {".m4a", ".mp4"}:
        raise SystemExit(f"source must be an existing MP4 or M4A file: {source}")
    if output.suffix.lower() != ".wav":
        raise SystemExit(f"output must use the .wav extension: {output}")
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {output}")

    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-hide_banner",
        "-nostdin",
        "-n",
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

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        output.unlink(missing_ok=True)
        raise

    print(
        json.dumps(
            {"source_path": str(source), "out_path": str(output)},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
