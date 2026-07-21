#!/usr/bin/env python3
"""Copy selected review documents, exporting Google Workspace shortcuts when needed."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


WORKSPACE_EXPORTS = {
    ".gdoc": [
        (".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        (".md", "text/markdown"),
        (".txt", "text/plain"),
    ],
    ".gsheet": [
        (".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ],
    ".gslides": [
        (".pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
    ],
}


@dataclass(frozen=True)
class PlannedCopy:
    source: str
    destination: str
    action: str
    size: int | None


def read_selection(paths_file: Path, inline_paths: list[str]) -> list[str]:
    paths: list[str] = []
    if paths_file:
        for line in paths_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                paths.append(stripped)
    paths.extend(inline_paths)
    return paths


def resolve_source(root: Path, requested: str) -> Path:
    requested_path = Path(requested).expanduser()
    if requested_path.is_absolute():
        source = requested_path.resolve()
    else:
        clean = requested_path.as_posix()
        if clean.startswith("./"):
            clean = clean[2:]
        source = (root / clean).resolve()

    try:
        source.relative_to(root)
    except ValueError as error:
        raise ValueError(f"selected path escapes source root: {requested}") from error
    if not source.is_file():
        raise FileNotFoundError(f"selected path is not a file: {requested}")
    return source


def output_paths(source: Path, root: Path, destination_root: Path, flat: bool) -> list[tuple[Path, str | None, str | None]]:
    relative = source.relative_to(root)
    parent = destination_root if flat else destination_root / relative.parent
    if source.suffix.casefold() not in WORKSPACE_EXPORTS:
        return [(parent / source.name, None, None)]
    return [
        (parent / f"{source.stem}{out_ext}", out_ext, mime_type)
        for out_ext, mime_type in WORKSPACE_EXPORTS[source.suffix.casefold()]
    ]


def load_workspace_shortcut(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Workspace shortcut is not valid JSON metadata: {path}") from error

    doc_id = data.get("doc_id") or data.get("file_id") or data.get("id")
    if not doc_id:
        raise ValueError(f"Workspace shortcut has no doc_id/file_id/id: {path}")
    result = {"fileId": doc_id}
    if data.get("resource_key"):
        result["resourceKey"] = data["resource_key"]
    return result


def export_workspace_file(
    source: Path,
    destination: Path,
    out_ext: str,
    mime_type: str,
    gws_binary: str,
    dry_run: bool,
) -> PlannedCopy:
    metadata = load_workspace_shortcut(source)
    params = {
        "fileId": metadata["fileId"],
        "mimeType": mime_type,
        "supportsAllDrives": True,
    }
    if "resourceKey" in metadata:
        params["resourceKey"] = metadata["resourceKey"]

    if dry_run:
        return PlannedCopy(str(source), str(destination), f"export{source.suffix}->{out_ext}", None)

    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        gws_binary,
        "drive",
        "files",
        "export",
        "--params",
        json.dumps(params, ensure_ascii=False),
        "-o",
        destination.name,
    ]
    completed = subprocess.run(
        command,
        cwd=destination.parent,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "unknown export failure"
        raise RuntimeError(f"failed to export {source}: {message}")
    return PlannedCopy(
        str(source),
        str(destination),
        f"export{source.suffix}->{out_ext}",
        destination.stat().st_size,
    )


def copy_file(source: Path, destination: Path, dry_run: bool) -> PlannedCopy:
    if dry_run:
        return PlannedCopy(str(source), str(destination), "copy", source.stat().st_size)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return PlannedCopy(str(source), str(destination), "copy", destination.stat().st_size)


def build_plan(
    root: Path,
    destination_root: Path,
    selected: list[str],
    flat: bool,
) -> list[tuple[Path, Path, str | None, str | None]]:
    plan: list[tuple[Path, Path, str | None, str | None]] = []
    seen_destinations: dict[Path, Path] = {}
    for requested in selected:
        source = resolve_source(root, requested)
        for destination, out_ext, mime_type in output_paths(source, root, destination_root, flat):
            if destination in seen_destinations:
                raise ValueError(
                    f"multiple selected files map to the same destination: {destination} "
                    f"({seen_destinations[destination]} and {source})"
                )
            seen_destinations[destination] = source
            plan.append((source, destination, out_ext, mime_type))
    return plan


def execute_plan(
    plan: list[tuple[Path, Path, str | None, str | None]],
    gws_binary: str,
    dry_run: bool,
    overwrite: bool,
) -> list[PlannedCopy]:
    if not overwrite:
        existing = [destination for _, destination, _, _ in plan if destination.exists()]
        if existing:
            formatted = "\n".join(str(path) for path in existing)
            raise FileExistsError(f"destination exists; rerun with --overwrite only after user approval:\n{formatted}")

    results: list[PlannedCopy] = []
    for source, destination, out_ext, mime_type in plan:
        if mime_type is not None and out_ext is not None:
            results.append(export_workspace_file(source, destination, out_ext, mime_type, gws_binary, dry_run))
        else:
            results.append(copy_file(source, destination, dry_run))
    return results


def print_results(results: list[PlannedCopy], as_json: bool) -> None:
    if as_json:
        print(json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2))
        return
    print("| Action | Size | Source | Destination |")
    print("|---|---:|---|---|")
    for result in results:
        size = "" if result.size is None else str(result.size)
        print(f"| {result.action} | {size} | `{result.source}` | `{result.destination}` |")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Source folder")
    parser.add_argument("destination", type=Path, help="Destination folder")
    parser.add_argument("--paths-file", type=Path, required=True, help="Newline-delimited selected paths")
    parser.add_argument("--path", action="append", default=[], help="Additional selected path; may repeat")
    parser.add_argument("--flat", action="store_true", help="Do not preserve source subdirectories")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without writing")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing destination files")
    parser.add_argument("--json", action="store_true", help="Emit JSON results")
    parser.add_argument("--gws-binary", default="gws", help="Google Workspace CLI binary")
    args = parser.parse_args()

    root = args.source.expanduser().resolve()
    destination_root = args.destination.expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"source is not a directory: {root}")

    selected = read_selection(args.paths_file, args.path)
    if not selected:
        raise SystemExit("no selected paths provided")

    plan = build_plan(root, destination_root, selected, args.flat)
    results = execute_plan(plan, args.gws_binary, args.dry_run, args.overwrite)
    print_results(results, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
